from functools import partial
import sys
import csv


import struct
import os
import renderdoc
import qrenderdoc as qrd
import renderdoc as rd
from typing import Optional

rd = renderdoc
ResourceDescription = rd.ResourceDescription
TextureDescription = rd.ResourceDescription

captureCtx = None
folderName = None


def textureHasSliceFace(tex: TextureDescription):
    return tex.arraysize > 1 or tex.depth > 1


def textureHasMipMap(tex: TextureDescription):
    return not (tex.mips == 1 and tex.msSamp <= 1)


def SaveTexture(resourceId, controller):
    texsave = rd.TextureSave()

    texsave.resourceId = resourceId
    if texsave.resourceId == rd.ResourceId.Null():
        return False

    resourceDesc: rd.ResourceDescription = captureCtx.GetResource(resourceId)
    texture: rd.TextureDescription = captureCtx.GetTexture(resourceId)

    eventID = captureCtx.CurSelectedEvent()
    resourceIdStr = str(int(resourceId))
    eventIDStr = str(int(eventID))

    filename = f"{resourceDesc.name}_{resourceIdStr}"

    texsave.mip = 0
    texsave.alpha = rd.AlphaMapping.Preserve
    texsave.destType = rd.FileType.TGA
    print(filename)
    folderPath = f"{folderName}/{eventIDStr}"

    if not os.path.exists(folderPath):
        os.makedirs(folderPath)

    # captureCtx.Extensions().MessageDialog(
    #     f"cubemap:{texture.arraysize},slice:{texture.depth}"
    # )

    if textureHasSliceFace(texture):
        if texture.cubemap:
            faces = ["X+", "X-", "Y+", "Y-", "Z+", "Z-"]
            texsave.slice.depth = 0
            for i in range(6):
                texsave.slice.sliceIndex = i
                outTexPath = f"{folderPath}/{filename}_{faces[i]}.tga"
                controller.SaveTexture(texsave, outTexPath)
        else:
            texsave.slice.sliceIndex = 0
            for i in range(texture.depth):
                texsave.slice.depth = i
                outTexPath = f"{folderPath}/{filename}_{i}.tga"
                controller.SaveTexture(texsave, outTexPath)

    else:
        texsave.slice.sliceIndex = 0
        texsave.slice.depth = 0
        outTexPath = f"{folderPath}/{filename}.tga"
        controller.SaveTexture(texsave, outTexPath)

    return True


def save_tex(controller: rd.ReplayController):
    print(folderName)
    state = controller.GetPipelineState()
    sampleList = state.GetReadOnlyResources(renderdoc.ShaderStage.Fragment)
    for sample in sampleList:
        for boundResource in sample.resources:
            if not SaveTexture(boundResource.resourceId, controller):
                break
    captureCtx.Extensions().MessageDialog(f"导出成功:{folderName}", "Export Texture")


def texture_callback(ctx: qrd.CaptureContext, data):
    if captureCtx is None:
        ctx.Extensions().MessageDialog("captureCtx is None", "Export Texture")
        return
    global folderName
    # ctx.Extensions().MessageDialog(f"导出{folderName}", "Export Texture")
    folderName = ctx.Extensions().OpenDirectoryName(
        "Save Texture",
        folderName,
    )
    if not folderName:
        return

    ctx.Replay().AsyncInvoke("", save_tex)


def biggestDraw(prevBiggest, d):
    ret = prevBiggest
    if ret == None or d.numIndices > ret.numIndices:
        ret = d

    for c in d.children:
        biggest = biggestDraw(ret, c)

        if biggest.numIndices > ret.numIndices:
            ret = biggest

    return ret


def save_all_tex(controller: rd.ReplayController):
    # draw = None
    # for d in controller.GetRootActions():
    #     draw = biggestDraw(draw, d)
    # print GetTextures size

    for tex in captureCtx.GetTextures():
        # print(tex.resourceId)
        if not SaveTexture(tex.resourceId, controller):
            break

    print(len(captureCtx.GetTextures()))
    # controller.SetFrameEvent(draw.eventId, True)
    # print(draw.eventId)
    # print(draw.numIndices)
    # state = controller.GetPipelineState()
    # sampleList = state.GetReadOnlyResources(renderdoc.ShaderStage.Fragment)
    # for sample in sampleList:
    #     for boundResource in sample.resources:
    #         if not SaveTexture(boundResource.resourceId, controller):
    #             break
    # captureCtx.Extensions().MessageDialog(f"导出成功:{folderName}", "Export Texture")


def texture_all_callback(ctx: qrd.CaptureContext, data):
    # if captureCtx is None:
    #     ctx.Extensions().MessageDialog("captureCtx is None", "Export Texture")
    #     return
    # global folderName
    # folderName = ctx.Extensions().OpenDirectoryName(
    #     "Save Texture",
    #     folderName,
    # )
    # if not folderName:
    #     return

    ctx.Replay().AsyncInvoke("", save_all_tex)


def register(version: str, ctx: qrd.CaptureContext):
    global captureCtx
    captureCtx = ctx
    global folderName
    folderName = os.path.expanduser("~/Pictures")
    # ctx.Extensions().RegisterPanelMenu(
    #     qrd.PanelMenu.TextureViewer, ["Export Texture Test"], texture_callback
    # )
    # ctx.Extensions().RegisterPanelMenu(
    #     qrd.PanelMenu.TextureViewer, ["Export Texture All"], texture_all_callback
    # )

    texture_all_callback(ctx, None)


if "pyrenderdoc" in globals():
    register(None, pyrenderdoc)
    # captureCtx = pyrenderdoc
    # folderName = os.path.expanduser("~/Pictures")
    # texture_callback(captureCtx, None)
