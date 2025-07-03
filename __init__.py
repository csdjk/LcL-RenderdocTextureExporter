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
import qrenderdoc as qrd
from .texture_exporter import TextureExporter
from .drawcall_statistics import  window_callback
import os
from .utils import TextureSaver, get_filename_without_extension 

# 全局实例
texture_exporter = None


def texture_callback(ctx: qrd.CaptureContext, data):
    global texture_exporter

    if ctx is None:
        ctx.Extensions().MessageDialog("captureCtx is None", "Export Texture")
        return

    if texture_exporter.get_open_directory() is None:
        return

    ctx.Replay().AsyncInvoke("", texture_exporter.save_current_draw_textures)
    
def all_texture_callback(ctx: qrd.CaptureContext, data):
    open_dir = ctx.Extensions().OpenDirectoryName("选择导出目录", os.path.expanduser("~/Pictures"))
    if not open_dir:
        return
    TextureSaver.open_directory = open_dir  # 设置全局变量
    
    def do_export(controller):
        name = ctx.GetCaptureFilename()
        name = get_filename_without_extension(name)
    
        count = TextureSaver.export_all_textures(ctx, controller, name)
        ctx.Extensions().MessageDialog(f"导出完成，共导出 {count} 张纹理到：{os.path.join(open_dir, name)}", "导出纹理")
        
    ctx.Replay().AsyncInvoke("", do_export)


def register(version: str, ctx: qrd.CaptureContext):
    global texture_exporter
    texture_exporter = TextureExporter(ctx)

    # 注册菜单项
    ctx.Extensions().RegisterPanelMenu(
        qrd.PanelMenu.TextureViewer, ["Export Draw Texture"], texture_callback
    )
    ctx.Extensions().RegisterPanelMenu(
        qrd.PanelMenu.TextureViewer, ["Export All Texture"], all_texture_callback
    )
    
    ctx.Extensions().RegisterWindowMenu(
        qrd.WindowMenu.Window, ["DrawCall Statistics"], window_callback
    )


def unregister():
    print("Unregistering LcL Texture Exporter extension")
