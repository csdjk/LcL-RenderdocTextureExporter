#   显示图片Demo（有Bug）
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
    
# 弹窗Demo
def top_widget(self, *args, **kwargs):
    texture_window = self.mqt.CreateToplevelWidget("Texture Display", lambda c, w, d: None)

    hbox = self.mqt.CreateHorizontalContainer()
    self.mqt.AddWidget(texture_window, hbox)
    self.mqt.ShowWidgetAsDialog(texture_window)