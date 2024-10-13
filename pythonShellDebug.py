from functools import partial
import os
import renderdoc
import qrenderdoc as qrd
import renderdoc as rd
from typing import List, Optional

rd = renderdoc
ResourceDescription = rd.ResourceDescription
TextureDescription = rd.ResourceDescription

captureCtx = None
openDirectory = None
textureCount = 0


def get_filename_without_extension(path):
    base_name = os.path.basename(path)  # 获取文件名，包含扩展名
    file_name, extension = os.path.splitext(base_name)  # 分割文件名和扩展名
    return file_name


def get_open_directory():
    global openDirectory
    openDirectory = captureCtx.Extensions().OpenDirectoryName(
        "Save Texture",
        openDirectory,
    )
    if not openDirectory:
        return None

    return openDirectory


def textureHasSliceFace(tex: TextureDescription):
    return tex.arraysize > 1 or tex.depth > 1


def textureHasMipMap(tex: TextureDescription):
    return not (tex.mips == 1 and tex.msSamp <= 1)


def SaveTexture(resourceId, controller, folderName, texName=""):
    texsave = rd.TextureSave()

    texsave.resourceId = resourceId
    if texsave.resourceId == rd.ResourceId.Null():
        return False

    resourceDesc: rd.ResourceDescription = captureCtx.GetResource(resourceId)
    texture: rd.TextureDescription = captureCtx.GetTexture(resourceId)
    # 小于4x4的纹理不导出,一般都是空白纹理
    if texture.width <= 4 and texture.height <= 4:
        return False

    # print(texture.format.Name())
    # print(resourceDesc.name)
    resourceIdStr = str(int(resourceId))

    # filename = f"{texName}_{resourceIdStr}"
    filename = f"{texName}"

    texsave.mip = 0
    texsave.slice.depth = 0
    texsave.alpha = rd.AlphaMapping.Preserve

    texFormat = ".tga"
    texsave.destType = rd.FileType.TGA
    if texture.format.compType == rd.CompType.Float:
        texsave.destType = rd.FileType.EXR
        texFormat = ".exr"

    folderPath = f"{openDirectory}/{folderName}"

    if not os.path.exists(folderPath):
        os.makedirs(folderPath)

    if textureHasSliceFace(texture):
        if texture.cubemap:
            faces = ["X+", "X-", "Y+", "Y-", "Z+", "Z-"]
            for i in range(texture.arraysize):
                texsave.slice.sliceIndex = i
                outTexPath = f"{folderPath}/{filename}_{faces[i]}{texFormat}"
                controller.SaveTexture(texsave, outTexPath)
        else:
            for i in range(texture.depth):
                texsave.slice.sliceIndex = i
                outTexPath = f"{folderPath}/{filename}_{i}{texFormat}"
                controller.SaveTexture(texsave, outTexPath)

    else:
        texsave.slice.sliceIndex = 0
        outTexPath = f"{folderPath}/{filename}{texFormat}"
        print(f"outTexPath:{ outTexPath}")
        controller.SaveTexture(texsave, outTexPath)

    global textureCount
    textureCount += 1
    return True


def BoundResourceName(state: rd.PipeState, bindPoint):

    refl: rd.ShaderReflection = state.GetShaderReflection(rd.ShaderStage.Fragment)
    mapping: rd.ShaderBindpointMapping = state.GetBindpointMapping(
        rd.ShaderStage.Fragment
    )
    map_list: List[rd.Bindpoint] = mapping.readOnlyResources

    try:
        idx = map_list.index(bindPoint)
    except:
        print(f"not found bindPoint:{ bindPoint.bind}")
        return ""

    for res in refl.readOnlyResources:
        res: rd.ShaderResource
        if res.bindPoint == idx:
            print(f"{res.name}: bindPoint:{ bindPoint.bind}")
            return res.name

    return ""


# 导出当前Draw的所有Texture
def save_tex(controller: rd.ReplayController):  # type: ignore
    global textureCount
    textureCount = 0

    eventID = str(int(captureCtx.CurSelectedEvent()))
    state: rd.PipeState = controller.GetPipelineState()

    # # 获取片元着色器的资源
    useDescriptorList: List[rd.UsedDescriptor] = state.GetReadOnlyResources(
        rd.ShaderStage.Fragment
    )
    
    for useDescriptor in useDescriptorList:
        # v 1.35+ 
        descriptor = useDescriptor.descriptor
        # print(descriptor)
        # print(f"sample: { descriptor.resource}-----------------------")
        # name = BoundResourceName(state, sample.bindPoint)
        name = str(int(descriptor.resource))
        SaveTexture(descriptor.resource, controller, eventID, name)
        
        # 低版本
        # for boundResource in sample.resources:
        #     boundResource: rd.BoundResource  # type: ignore
        #     if not SaveTexture(boundResource.resourceId, controller, eventID, name):
        #         break
            
    captureCtx.Extensions().MessageDialog(
        f"Export Complete,Total {textureCount} textures:{openDirectory}",
        "Export Texture",
    )


def texture_callback(ctx: qrd.CaptureContext, data):
    if ctx is None:
        ctx.Extensions().MessageDialog("captureCtx is None", "Export Texture")
        return
    get_open_directory()
    ctx.Replay().AsyncInvoke("", save_tex)


# 导出所有Texture
def save_all_tex(controller: rd.ReplayController):
    name = captureCtx.GetCaptureFilename()
    name = get_filename_without_extension(name)

    global textureCount
    textureCount = 0
    for tex in captureCtx.GetTextures():
        tex: rd.TextureDescription
        if not SaveTexture(tex.resourceId, controller, name):
            break
    captureCtx.Extensions().MessageDialog(
        f"Export successful,A total of {textureCount}:{openDirectory}", "Export Texture"
    )


def texture_all_callback(ctx: qrd.CaptureContext, data):
    if ctx is None:
        ctx.Extensions().MessageDialog("captureCtx is None", "Export Texture")
        return
    get_open_directory()
    ctx.Replay().AsyncInvoke("", save_all_tex)


# ==========================================================
def register(version: str, ctx: qrd.CaptureContext):
    global captureCtx
    captureCtx = ctx
    global openDirectory
    openDirectory = os.path.expanduser("~/Pictures")
    # ctx.Extensions().RegisterPanelMenu(
    #     qrd.PanelMenu.TextureViewer, ["Export Texture Test"], texture_callback
    # )
    # ctx.Extensions().RegisterPanelMenu(
    #     qrd.PanelMenu.TextureViewer, ["Export Texture All"], texture_all_callback
    # )

    # texture_callback(ctx, None)
    texture_all_callback(ctx, None)


if "pyrenderdoc" in globals():
    register(None, pyrenderdoc)
