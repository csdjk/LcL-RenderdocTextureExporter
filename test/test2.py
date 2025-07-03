import qrenderdoc as qrd
import renderdoc as rd
from typing import Optional
import renderdoc
import os


class TextureSaver:
    """
    纹理导出工具类，封装了导出单个纹理的核心逻辑。
    """
    def __init__(self, capture_ctx, open_directory=None):
        self.capture_ctx = capture_ctx
        self.open_directory = open_directory or os.path.expanduser("~/Pictures")
        self.texture_count = 0

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

        filename = f"{tex_name}"
        texsave.mip = 0
        texsave.slice.depth = 0
        texsave.alpha = rd.AlphaMapping.Preserve

        tex_format = ".tga"
        texsave.destType = rd.FileType.TGA
        if texture.format.compType == rd.CompType.Float:
            texsave.destType = rd.FileType.EXR
            tex_format = ".exr"

        folder_path = os.path.join(self.open_directory, folder_name)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        if self.texture_has_slice_face(texture):
            if texture.cubemap:
                faces = ["X+", "X-", "Y+", "Y-", "Z+", "Z-"]
                for i in range(texture.arraysize):
                    texsave.slice.sliceIndex = i
                    out_tex_path = os.path.join(folder_path, f"{filename}_{faces[i]}{tex_format}")
                    controller.SaveTexture(texsave, out_tex_path)
            else:
                for i in range(texture.depth):
                    texsave.slice.sliceIndex = i
                    out_tex_path = os.path.join(folder_path, f"{filename}_{i}{tex_format}")
                    controller.SaveTexture(texsave, out_tex_path)
        else:
            texsave.slice.sliceIndex = 0
            out_tex_path = os.path.join(folder_path, f"{filename}{tex_format}")
            controller.SaveTexture(texsave, out_tex_path)

        self.texture_count += 1
        return True

ResourceUsage = rd.ResourceUsage
# 输入资源类型常量
INPUT_RESOURCE_USAGES = [
    ResourceUsage.VS_Resource,
    ResourceUsage.PS_Resource,
    ResourceUsage.CS_Resource,
    ResourceUsage.HS_Resource,
    ResourceUsage.DS_Resource,
    ResourceUsage.GS_Resource,
    ResourceUsage.TS_Resource,
    ResourceUsage.MS_Resource,
    ResourceUsage.All_Resource,
]


def sampleCode(controller):
    resources = controller.GetResources()
     # 选择导出目录
    open_dir = pyrenderdoc.Extensions().OpenDirectoryName("选择导出目录", os.path.expanduser("~/Pictures"))
    if not open_dir:
        return

    saver = TextureSaver(pyrenderdoc, open_dir)
    folder_name = f"Action"
    count = 0
    for res in resources:
        
        if res.type == renderdoc.ResourceType.Texture:
            textureid = res.resourceId
            usages = controller.GetUsage(res.resourceId)
            test = False
            for usage in usages:
                if usage.usage in INPUT_RESOURCE_USAGES:
                    test = True
                    break
            if not test:
                continue
            if saver.save_texture(textureid, controller, folder_name, int(textureid)):
                print(f"Texture ID: {textureid}")
        
if 'pyrenderdoc' in globals():
	pyrenderdoc.Replay().BlockInvoke(sampleCode)