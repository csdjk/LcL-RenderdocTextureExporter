
import qrenderdoc as qrd
import renderdoc as rd
from typing import Optional
# from PyQt5.QtGui import QImage, QPixmap
# from PyQt5.QtWidgets import QLabel

textureid = rd.ResourceId.Null()
controller_g: Optional[rd.ReplayController] = None

class DrawcallStatisticsWindow(qrd.CaptureViewer):
    def __init__(self, ctx: qrd.CaptureContext, version: str):
        super().__init__()

        self.mqt: qrd.MiniQtHelper = ctx.Extensions().GetMiniQtHelper()

        self.ctx = ctx
        self.version = version
        self.topWindow = self.mqt.CreateToplevelWidget("Breadcrumbs", lambda c, w, d: window_closed())

        vert = self.mqt.CreateVerticalContainer()
        self.mqt.AddWidget(self.topWindow, vert)

        # 范围输入UI
        range_container = self.mqt.CreateHorizontalContainer()
        self.mqt.AddWidget(vert, range_container)


        self.start_label = self.mqt.CreateLabel()
        self.mqt.SetWidgetText(self.start_label, "Start EventId:")
        self.mqt.AddWidget(range_container, self.start_label)
        self.start_spin = self.mqt.CreateTextBox(True, self.on_range_changed)
        self.mqt.AddWidget(range_container, self.start_spin)

        self.end_label = self.mqt.CreateLabel()
        self.mqt.SetWidgetText(self.end_label, "End EventId:")
        self.mqt.AddWidget(range_container, self.end_label)
        self.end_spin = self.mqt.CreateTextBox(True, self.on_range_changed)
        self.mqt.AddWidget(range_container, self.end_spin)


        self.breadcrumbs = self.mqt.CreateLabel()
        self.mqt.AddWidget(vert, self.breadcrumbs)

        self.show_texture_button = self.mqt.CreateButton(self.on_show_images_clicked)
        self.mqt.SetWidgetText(self.show_texture_button, "Show Texture")
        self.mqt.AddWidget(vert, self.show_texture_button)


        # ctx.Replay().BlockInvoke(self._init_data)
        ctx.AddCaptureViewer(self)

        
    def draw_texture_thumbnail(self,controller: rd.ReplayController, texture_id: rd.ResourceId, texture_window):
        # 设置缩略图的大小
        thumbnail_width = 128
        thumbnail_height = 128
        print(f"Texture ID: {texture_id}")
        
        # 创建一个输出对象
        # output = controller.CreateOutput(rd.CreateHeadlessWindowingData(thumbnail_width, thumbnail_height), rd.ReplayOutputType.Texture)
        # 调用 DrawThumbnail 获取 RGBA8 字节数据
        # img_data = output.DrawThumbnail(thumbnail_width, thumbnail_height, texture_id, rd.Subresource(), rd.CompType.Typeless)
        
        # img_data = controller.GetTextureData(texture_id, rd.Subresource(0,0,0))

        # label = self.mqt.CreateLabel()
        # # 设置图像数据到标签
        # self.mqt.SetLabelImage(label, img_data, thumbnail_width, thumbnail_height, False)
        # self.mqt.AddWidget(texture_window, label)
        

    def on_show_images_clicked(self, *args, **kwargs):
        texture_window = self.mqt.CreateToplevelWidget("Texture Display", lambda c, w, d: None)

        if controller_g is None:
            self.mqt.MessageDialog("Replay controller not initialized.", "Error")
            return

        pipe: rd.PipeState = controller_g.GetPipelineState()
        resources = pipe.GetReadOnlyResources(rd.ShaderStage.Fragment)

        if not resources:
            self.mqt.MessageDialog("No read-only resources found.", "Error")
            return

        # 创建一个水平容器用于放置所有缩略图
        hbox = self.mqt.CreateHorizontalContainer()
        self.mqt.AddWidget(texture_window, hbox)

        for i, used_desc in enumerate(resources):
            tex_id = used_desc.descriptor.resource
            if tex_id == rd.ResourceId.Null():
                continue
            # 绘制缩略图并添加到容器
            self.draw_texture_thumbnail(controller_g, tex_id, hbox)

        self.mqt.ShowWidgetAsDialog(texture_window)

        
        
    def on_range_changed(self, *args, **kwargs):
        try:
            start = int(self.mqt.GetWidgetText(self.start_spin))
        except Exception:
            start = 0
        try:
            end = int(self.mqt.GetWidgetText(self.end_spin))
        except Exception:
            end = 0
        self.update_range_statistics(start, end)

    def update_range_statistics(self, start, end):
        # 这里实现你需要的逻辑，比如统计action范围等
        msg = f"当前范围: {start} - {end}"
        self.mqt.SetWidgetText(self.breadcrumbs, msg)

    def OnCaptureLoaded(self):
        print("Capture loaded")

    def OnCaptureClosed(self):
        print("Capture closed")
        
    def OnSelectedEventChanged(self, event):
        pass

    def OnEventChanged(self, event):
        action = self.ctx.GetAction(event)
        print(f"OnEventChanged: {action.actionId} {action.eventId}")


cur_window: Optional[DrawcallStatisticsWindow] = None


def window_closed():
    global cur_window

    if cur_window is not None:
        cur_window.ctx.RemoveCaptureViewer(cur_window)

    cur_window = None


def window_callback(ctx: qrd.CaptureContext, data):
    global cur_window

    if cur_window is None:
        cur_window = DrawcallStatisticsWindow(ctx, "1.0")
        if ctx.HasEventBrowser():
            ctx.AddDockWindow(cur_window.topWindow, qrd.DockReference.TopOf, ctx.GetEventBrowser().Widget(), 0.1)
        else:
            ctx.AddDockWindow(cur_window.topWindow, qrd.DockReference.MainToolArea, None)

    ctx.RaiseDockWindow(cur_window.topWindow)


def sampleCode(controller):
    global controller_g
    controller_g = controller
    window_callback(pyrenderdoc, None)
    resources = controller.GetResources()
    global textureid
    for res in resources:
        if res.type == renderdoc.ResourceType.Texture:
            textureid = res.resourceId
            img_data = controller.GetTextureData(textureid, rd.Subresource(0,0,0))
            
            print(f"Texture ID: {textureid}")
            print(img_data)
            return
        

if 'pyrenderdoc' in globals():
	pyrenderdoc.Replay().BlockInvoke(sampleCode)