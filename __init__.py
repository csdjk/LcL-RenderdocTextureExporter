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
import renderdoc
import qrenderdoc as qrd
import renderdoc as rd
from typing import Optional

rd = renderdoc
ResourceDescription = rd.ResourceDescription
TextureDescription = rd.ResourceDescription

folderName = r"C:\Users\Administrator\Pictures\Renderdoc"
captureCtx = None


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

    filename = resourceDesc.name

    eventID = captureCtx.CurSelectedEvent()
    resourceIdStr = str(int(resourceId))
    eventIDStr = str(int(eventID))

    texsave.mip = 0
    texsave.alpha = rd.AlphaMapping.Preserve
    texsave.destType = rd.FileType.PNG

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
    state = controller.GetPipelineState()
    sampleList = state.GetReadOnlyResources(renderdoc.ShaderStage.Fragment)
    for sample in sampleList:
        for boundResource in sample.resources:
            if not SaveTexture(boundResource.resourceId, controller):
                break
    captureCtx.Extensions().MessageDialog(f"导出成功:{folderName}", "Extension message")


def texture_callback(ctx: qrd.CaptureContext, data):
    global captureCtx
    captureCtx = ctx
    global folderName
    folderName = os.path.expanduser("~/Pictures")

    folderName = captureCtx.Extensions().OpenDirectoryName(
        "Save Texture",
        folderName,
    )
    if not folderName:
        return

    ctx.Replay().AsyncInvoke("", save_tex)


def register(version: str, ctx: qrd.CaptureContext):
    ctx.Extensions().RegisterPanelMenu(
        qrd.PanelMenu.TextureViewer, ["Export All Texture"], texture_callback
    )


def unregister():
    print("Unregistering my extension")
