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

        # 获取片元着色器的资源
        used_descriptor_list: List[rd.UsedDescriptor] = state.GetReadOnlyResources(
            rd.ShaderStage.Fragment
        )
        for used_descriptor in used_descriptor_list:
            # v 1.35+ 
            descriptor = used_descriptor.descriptor
            name = str(int(descriptor.resource))
            self.save_texture(descriptor.resource, controller, event_id, name)
            
            # 低版本
            # name = self.bound_resource_name(state, sample.bindPoint)
            # for boundResource in sample.resources:
            #     boundResource: rd.BoundResource
            #     if not self.save_texture(boundResource.resourceId, controller, event_id, name):
            #         break
                
        self.capture_ctx.Extensions().MessageDialog(
            f"Export Complete,Total {self.texture_count} textures:{self.open_directory}",
            "Export Texture",
        )
