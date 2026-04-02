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
import subprocess
import renderdoc as rd
from typing import List

from .utils import TextureSaver


class TextureExporter:
    def __init__(self, capture_ctx):
        self.capture_ctx = capture_ctx
        self.open_directory = os.path.expanduser("~/Pictures")

    def get_open_directory(self):
        selected = self.capture_ctx.Extensions().OpenDirectoryName(
            "Save Texture",
            self.open_directory,
        )
        if not selected:
            return None
        self.open_directory = selected
        return self.open_directory

    def _build_slot_var_map(self, state: rd.PipeState) -> dict:
        """
        通过 ShaderReflection 枚举顺序构建 slot_idx -> shader 变量名 的映射。
        refl.readOnlyResources 的枚举顺序与 GetReadOnlyResources 返回列表顺序一致。
        """
        slot_map = {}
        refl: rd.ShaderReflection = state.GetShaderReflection(rd.ShaderStage.Fragment)
        if refl is None:
            return slot_map
        for slot_idx, res in enumerate(refl.readOnlyResources):
            slot_map[slot_idx] = res.name
        return slot_map

    # 导出当前 DrawCall 绑定的所有 Fragment Shader 输入纹理
    def save_current_draw_textures(self, controller: rd.ReplayController):
        event_id = str(int(self.capture_ctx.CurSelectedEvent()))
        state: rd.PipeState = controller.GetPipelineState()

        # slot_idx -> shader 变量名（枚举顺序与 GetReadOnlyResources 一致）
        slot_var_map = self._build_slot_var_map(state)

        # 获取 Fragment Shader 绑定的所有只读资源
        used_descriptor_list: List[rd.UsedDescriptor] = state.GetReadOnlyResources(
            rd.ShaderStage.Fragment
        )

        folder_path = os.path.join(self.open_directory, event_id)

        # 检测重名：记录每个文件名出现的次数，重名时自动追加 _1/_2 后缀
        name_counter: dict = {}
        texture_count = 0

        for slot_idx, used_descriptor in enumerate(used_descriptor_list):
            descriptor = used_descriptor.descriptor
            var_name = slot_var_map.get(slot_idx, f"FS{slot_idx}")

            # 处理重名
            if var_name in name_counter:
                name_counter[var_name] += 1
                unique_name = f"{var_name}_{name_counter[var_name]}"
            else:
                name_counter[var_name] = 0
                unique_name = var_name

            if TextureSaver.save_texture(
                self.capture_ctx, controller,
                descriptor.resource, folder_path, unique_name
            ):
                texture_count += 1

        # 导出完成日志（不调用 MessageDialog，避免 Replay 线程死锁）
        print(f"[TextureExporter] Export Complete — EventID={event_id}, "
              f"Total={texture_count} textures -> {folder_path}")
        # 打开导出目录（非阻塞）
        subprocess.Popen(f'explorer "{os.path.normpath(folder_path)}"')