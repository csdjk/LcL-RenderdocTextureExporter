import qrenderdoc as qrd
import renderdoc as rd
import os
from typing import Optional
import renderdoc
from .utils import ControllerDataStats,TextureSaver, get_filename_without_extension
ActionRange = (0, 10000) 
    
    
class DrawcallStatisticsWindow(qrd.CaptureViewer):
    def __init__(self, ctx: qrd.CaptureContext, version: str):
        super().__init__()


        self.mqt: qrd.MiniQtHelper = ctx.Extensions().GetMiniQtHelper()

        self.ctx = ctx
        self.version = version
        self.topWindow = self.mqt.CreateToplevelWidget(
            "Breadcrumbs", lambda c, w, d: window_closed()
        )

        self.vert = self.mqt.CreateVerticalContainer()
        self.mqt.AddWidget(self.topWindow, self.vert)

        # 范围输入UI
        range_container = self.mqt.CreateHorizontalContainer()
        self.mqt.AddWidget(self.vert, range_container)

        self.start_label = self.mqt.CreateLabel()
        self.mqt.SetWidgetText(self.start_label, "Start ActionID:")
        self.mqt.AddWidget(range_container, self.start_label)
        self.start_spin = self.mqt.CreateTextBox(True, self.on_range_changed)
        self.mqt.AddWidget(range_container, self.start_spin)

        self.end_label = self.mqt.CreateLabel()
        self.mqt.SetWidgetText(self.end_label, "End ActionID:")
        self.mqt.AddWidget(range_container, self.end_label)
        self.end_spin = self.mqt.CreateTextBox(True, self.on_range_changed)
        self.mqt.AddWidget(range_container, self.end_spin)

        self.breadcrumbs = self.mqt.CreateLabel()
        self.mqt.AddWidget(self.vert, self.breadcrumbs)


        self.show_texture_button = self.mqt.CreateButton(self.on_export_images_clicked)
        self.mqt.SetWidgetText(self.show_texture_button, "Export All Texture")
        self.mqt.AddWidget(self.vert, self.show_texture_button)
        
        ctx.AddCaptureViewer(self)
        
        ctx.Replay().BlockInvoke(self._init_data)
        
    def get_action_range(self):
        """获取当前范围的 Action ID"""
        try:
            start = int(self.mqt.GetWidgetText(self.start_spin))
        except Exception:
            start = ActionRange[0]
        try:
            end = int(self.mqt.GetWidgetText(self.end_spin))
        except Exception:
            end = ActionRange[1]
        return start, end
    
    def _init_data(self, controller):
        self.controller = controller
        self.stats = ControllerDataStats(controller,self.ctx)

    def on_range_changed(self, *args, **kwargs):
        start, end = self.get_action_range()
        self.update_range_statistics(start, end)

    def update_range_statistics(self, start, end):
        mesh_num = self.stats.get_meshnum_in_range_by_actionid(start, end)
        texture_num = len(self.stats.get_inputs_in_range_by_actionid(start, end))
        msg = f"面数: {mesh_num}     纹理数: {texture_num}     Drawcall数: {end-start+1}\n"
        self.mqt.SetWidgetText(self.breadcrumbs, msg)
        
        texture_resolutions = self.stats.count_texture_resolutions_in_range_by_actionid(start, end)
        msg += "纹理分辨率统计:\n"
        for res, count in texture_resolutions:
            msg += f"   {res}: {count}张\n"
        self.mqt.SetWidgetText(self.breadcrumbs, msg)

    def on_export_images_clicked(self, *args, **kwargs):
        start, end = self.get_action_range()
        textures = self.stats.get_inputs_in_range_by_actionid(start, end)
        if not textures:
            self.ctx.Extensions().MessageDialog("未找到可导出的纹理", "导出纹理")
            return

        open_dir = self.ctx.Extensions().OpenDirectoryName("选择导出目录", os.path.expanduser("~/Pictures"))
        if not open_dir:
            return

        TextureSaver.open_directory = open_dir  # 设置全局变量
        def do_export(controller):
            name = self.ctx.GetCaptureFilename()
            name = get_filename_without_extension(name)
            folder_name = f"{name}_{start}_{end}"
    
            for tex in textures:
                tex_id = tex.resourceId
                TextureSaver.save_texture(self.ctx, controller, tex_id, folder_name, str(int(tex_id)))
            self.ctx.Extensions().MessageDialog(f"导出完成，共导出 {len(textures)} 张纹理到：{TextureSaver.open_directory}", "导出纹理")

        self.ctx.Replay().AsyncInvoke("", do_export)

   
        
        
    def OnCaptureLoaded(self):
        self.mqt.SetWidgetText(self.breadcrumbs, "Breadcrumbs:")

    def OnCaptureClosed(self):
        self.mqt.SetWidgetText(self.breadcrumbs, "Breadcrumbs:")

    def OnSelectedEventChanged(self, event):
        pass

    def OnEventChanged(self, event):
        action = self.ctx.GetAction(event)
        # self.mqt.SetWidgetText(self.breadcrumbs, "OnEventChanged:"+ f" {action.actionId} {action.eventId}")
        
        
        # tex_id = self.stats.get_inputs_by_actionid(action.actionId)[0]
        # self.mqt.SetWidgetText(self.breadcrumbs, f"aa {tex_id}")
        
        # img_data = self.controller.GetTextureData(tex_id, rd.Subresource(0,0,0))
        # self.mqt.SetWidgetText(self.breadcrumbs, "OnEventChanged2:"+ f" {img_data}")
        
        # label = self.mqt.CreateLabel()
        # # 设置图像数据到标签
        # self.mqt.SetLabelImage(label, img_data, 128, 128, False)
        # # self.mqt.AddWidget(texture_window, label)
        # self.mqt.AddWidget(self.vert, label)
        
        


cur_window: Optional[DrawcallStatisticsWindow] = None


def window_closed():
    global cur_window

    if cur_window is not None:
        cur_window.ctx.RemoveCaptureViewer(cur_window)

    cur_window = None


def window_callback(ctx: qrd.CaptureContext, data):
    global cur_window

    if cur_window is None:
        cur_window = DrawcallStatisticsWindow(ctx, extiface_version)
        if ctx.HasEventBrowser():
            ctx.AddDockWindow(
                cur_window.topWindow,
                qrd.DockReference.TopOf,
                ctx.GetEventBrowser().Widget(),
                0.1,
            )
        else:
            ctx.AddDockWindow(
                cur_window.topWindow, qrd.DockReference.MainToolArea, None
            )

    ctx.RaiseDockWindow(cur_window.topWindow)


extiface_version = ""


def register(version: str, ctx: qrd.CaptureContext):
    global extiface_version
    extiface_version = version

    ctx.Extensions().RegisterWindowMenu(
        qrd.WindowMenu.Window, ["Extension Window"], window_callback
    )


def unregister():
    print("Unregistering my extension")
    global cur_window

    if cur_window is not None:
        cur_window.ctx.Extensions().GetMiniQtHelper().CloseToplevelWidget(
            cur_window.topWindow
        )
        cur_window = None
