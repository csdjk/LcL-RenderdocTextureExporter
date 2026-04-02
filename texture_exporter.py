###############################################################################
# The MIT License (MIT)
#
# Copyright (c) 2021-2023 Baldur Karlsson
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
###############################################################################
import os
import renderdoc as rd
from typing import List, Optional

class TextureExporter:
    def __init__(self, capture_ctx):
        self.capture_ctx = capture_ctx
        self.open_directory = os.path.expanduser("~/Pictures")
        self.texture_count = 0
    

    
    def get_open_directory(self):
        self.open_directory = self.capture_ctx.Extensions().OpenDirectoryName(
            "Save Texture",
            self.open_directory,
        )
        if not self.open_directory:
            return None

        return self.open_directory
    
    def texture_has_slice_face(self, tex: rd.ResourceDescription):
        return tex.arraysize > 1 or tex.depth > 1

    def texture_has_mip_map(self, tex: rd.ResourceDescription):
        return not (tex.mips == 1 and tex.msSamp <= 1)
    
    def save_texture(self, resource_id, controller, folder_name, tex_name=""):
        texsave = rd.TextureSave()

        texsave.resourceId = resource_id
        if texsave.resourceId == rd.ResourceId.Null():
            return False

        resource_desc: rd.ResourceDescription = self.capture_ctx.GetResource(resource_id)
        texture: rd.TextureDescription = self.capture_ctx.GetTexture(resource_id)
        # 小于4x4的纹理不导出,一般都是空白纹理
        if texture.width <= 4 and texture.height <= 4:
            return False

        print(texture.format.Name())
        print(resource_desc.name)
        resource_id_str = str(int(resource_id))

        # filename = f"{tex_name}_{resource_id_str}"
        filename = f"{tex_name}"

        texsave.mip = 0
        texsave.slice.depth = 0
        texsave.alpha = rd.AlphaMapping.Preserve

        tex_format = ".tga"
        texsave.destType = rd.FileType.TGA
        if texture.format.compType == rd.CompType.Float:
            texsave.destType = rd.FileType.EXR
            tex_format = ".exr"

        folder_path = f"{self.open_directory}/{folder_name}"

        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        if self.texture_has_slice_face(texture):
            if texture.cubemap:
                faces = ["X+", "X-", "Y+", "Y-", "Z+", "Z-"]
                for i in range(texture.arraysize):
                    texsave.slice.sliceIndex = i
                    out_tex_path = f"{folder_path}/{filename}_{faces[i]}{tex_format}"
                    controller.SaveTexture(texsave, out_tex_path)
            else:
                for i in range(texture.depth):
                    texsave.slice.sliceIndex = i
                    out_tex_path = f"{folder_path}/{filename}_{i}{tex_format}"
                    controller.SaveTexture(texsave, out_tex_path)

        else:
            texsave.slice.sliceIndex = 0
            out_tex_path = f"{folder_path}/{filename}{tex_format}"
            controller.SaveTexture(texsave, out_tex_path)

        self.texture_count += 1
        return True
    
    def build_slot_name_map(self, state: rd.PipeState) -> dict:
        """
        构建 (reg, space) -> (slot_index, shader_var_name) 的映射表，
        对应 Inputs 面板中的 'FS {slot} {varName}' 标签。
        """
        slot_map = {}
        refl: rd.ShaderReflection = state.GetShaderReflection(rd.ShaderStage.Fragment)
        mapping: rd.ShaderBindpointMapping = state.GetBindpointMapping(rd.ShaderStage.Fragment)

        if refl is None or mapping is None:
            return slot_map

        bind_points: List[rd.Bindpoint] = mapping.readOnlyResources

        for res in refl.readOnlyResources:
            res: rd.ShaderResource
            bp_idx = res.bindPoint
            if bp_idx < 0 or bp_idx >= len(bind_points):
                continue
            bp: rd.Bindpoint = bind_points[bp_idx]
            if not bp.used:
                continue
            # 以 (reg, space) 为 key，方便后面用 used_descriptor 查找
            slot_map[(bp.bind, bp.arraySize)] = (bp_idx, res.name)

        return slot_map

    def bound_resource_name(self, state: rd.PipeState, bind_point):
        refl: rd.ShaderReflection = state.GetShaderReflection(rd.ShaderStage.Fragment)
        mapping: rd.ShaderBindpointMapping = state.GetBindpointMapping(
            rd.ShaderStage.Fragment
        )
        map_list: List[rd.Bindpoint] = mapping.readOnlyResources

        try:
            idx = map_list.index(bind_point)
        except:
            print(f"not found bindPoint:{bind_point.bind}")
            return ""

        for res in refl.readOnlyResources:
            res: rd.ShaderResource
            if res.bindPoint == idx:
                print(f"{res.name}: bindPoint:{bind_point.bind}")
                return res.name

        return ""

    # 导出当前Draw的所有Texture
    def save_current_draw_textures(self, controller: rd.ReplayController):
        self.texture_count = 0

        event_id = str(int(self.capture_ctx.CurSelectedEvent()))
        state: rd.PipeState = controller.GetPipelineState()

        # 通过 ShaderReflection 构建 slot索引 -> shader变量名 映射
        # refl.readOnlyResources 的枚举顺序与 Pipeline State 面板 Textures/Slot 列表一致
        refl: rd.ShaderReflection = state.GetShaderReflection(rd.ShaderStage.Fragment)
        # slot_idx -> var_name，直接用枚举索引，不依赖 bindPoint 字段
        slot_var_map = {}
        if refl is not None:
            for slot_idx, res in enumerate(refl.readOnlyResources):
                res: rd.ShaderResource
                slot_var_map[slot_idx] = res.name
                print(f"ShaderResource: slot={slot_idx}, name={res.name}")

        # 获取片元着色器绑定的资源列表（顺序对应 Inputs 面板从左到右）
        used_descriptor_list: List[rd.UsedDescriptor] = state.GetReadOnlyResources(
            rd.ShaderStage.Fragment
        )
        for slot_idx, used_descriptor in enumerate(used_descriptor_list):
            # v 1.35+
            descriptor = used_descriptor.descriptor
            var_name = slot_var_map.get(slot_idx, "")
            slot_name = var_name if var_name else f"FS{slot_idx}"
            self.save_texture(descriptor.resource, controller, event_id, slot_name)

            # 低版本
            # name = self.bound_resource_name(state, sample.bindPoint)
            # for boundResource in sample.resources:
            #     boundResource: rd.BoundResource
            #     if not self.save_texture(boundResource.resourceId, controller, event_id, name):
            #         break
                
        count = self.texture_count
        save_dir = self.open_directory
        export_folder = f"{save_dir}/{event_id}"

        def on_export_done():
            self.capture_ctx.Extensions().MessageDialog(
                f"Export Complete, Total {count} textures: {export_folder}",
                "Export Texture",
            )
            # 打开导出目录
            import subprocess
            subprocess.Popen(f'explorer "{os.path.normpath(export_folder)}"')

        # UI 操作必须在主线程调用，否则会死锁
        self.capture_ctx.Extensions().RunInUIThread(on_export_done)
