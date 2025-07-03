import sys
import os
import renderdoc
from typing import Set, Optional
from typing import Dict
rd = renderdoc
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

# 输出资源类型常量
OUTPUT_RESOURCE_USAGES = [
    ResourceUsage.ColorTarget,
    ResourceUsage.DepthStencilTarget,
]


def get_filename_without_extension( path):
    base_name = os.path.basename(path)  # 获取文件名，包含扩展名
    file_name, extension = os.path.splitext(base_name)  # 分割文件名和扩展名
    return file_name

class ActionData:
    def __init__(self, action):
        self.action = action
        self.actionId: int = action.actionId
        self.eventId: int = action.eventId
        self.flags = action.flags
        self.numIndices: int = action.numIndices
        self.meshNum: float = action.numIndices / 3 if action.flags & rd.ActionFlags.Drawcall and action.flags & rd.ActionFlags.Indexed else 0
        self.inputsTextures: Set[TextureData] = set()
        self.outputsTextures: Set[TextureData] = set()

class TextureData:
    def __init__(self, resource_id, texture: rd.TextureDescription):
        self.resourceId = resource_id
        self.texture = texture
        self.width = texture.width
        self.height = texture.height
        self.format = texture.format
        self.creationFlags = texture.creationFlags
        self.arraysize = texture.arraysize
        self.depth = texture.depth
        self.mips = texture.mips
        self.msSamp = texture.msSamp

class ControllerDataStats:
    def __init__(self, controller, ctx):
        self.ctx = ctx
        self.eventid_action_map : Dict[int, ActionData] = {}    # eventId -> ActionData
        self.actionid_action_map : Dict[int, ActionData] = {}  # actionId -> ActionData
        self._collect(controller)

    def _collect(self, controller):
        # 收集eventId到Action的映射
        def collect_actions(actions):
            for action in actions:
                actionData = ActionData(action)
                self.eventid_action_map[action.eventId] = actionData
                self.actionid_action_map[action.actionId] = actionData
                if hasattr(action, 'children'):
                    collect_actions(action.children)
        collect_actions(controller.GetRootActions())

        # 收集纹理资源的输入输出使用情况，直接添加到对应的 ActionData
        resources = controller.GetResources()
        for res in resources:
            if res.type == renderdoc.ResourceType.Texture:
                usages = controller.GetUsage(res.resourceId)
                texture_desc = self.ctx.GetTexture(res.resourceId)
                texture_data = TextureData(res.resourceId, texture_desc)
                for usage in usages:
                    eid = usage.eventId
                    actionData = self.eventid_action_map.get(eid)
                    if not actionData:
                        continue
                    # 输入纹理
                    if usage.usage in INPUT_RESOURCE_USAGES:
                        actionData.inputsTextures.add(texture_data)
                    # 输出纹理
                    if usage.usage in OUTPUT_RESOURCE_USAGES:
                        actionData.outputsTextures.add(texture_data)

    def get_action_by_actionid(self, action_id) -> Optional[ActionData]:
        """根据 actionId 获取对应的 ActionData 对象"""
        return self.actionid_action_map.get(action_id, None)

    def get_action_by_eventid(self, event_id) -> Optional[ActionData]:
        """根据 eventId 获取对应的 ActionData 对象"""
        return self.eventid_action_map.get(event_id, None)

    def get_event_id(self, action_id):
        """根据 actionId 获取对应的 eventId"""
        action = self.actionid_action_map.get(action_id, None)
        return action.eventId if action else None

    def get_action_id(self, event_id):
        """根据 eventId 获取对应的 actionId"""
        action = self.eventid_action_map.get(event_id, None)
        return action.actionId if action else None

    def get_inputs_by_eventid(self, event_id):
        """获取指定 event_id 的输入纹理资源ID列表"""
        action = self.eventid_action_map.get(event_id)
        return list(action.inputsTextures) if action else []

    def get_inputs_by_actionid(self, action_id):
        """获取指定 action_id 的输入纹理资源ID列表"""
        action = self.actionid_action_map.get(action_id)
        return list(action.inputsTextures) if action else []

    def get_outputs_by_eventid(self, event_id):
        """获取指定 event_id 的输出纹理资源ID列表"""
        action = self.eventid_action_map.get(event_id)
        return list(action.outputsTextures) if action else []

    def get_outputs_by_actionid(self, action_id):
        """获取指定 action_id 的输出纹理资源ID列表"""
        action = self.actionid_action_map.get(action_id)
        return list(action.outputsTextures) if action else []

    def get_inputs_in_range(self, start_event_id, end_event_id):
        """获取指定 event_id 范围内的所有输入纹理资源ID集合"""
        result = set()
        for eid in range(start_event_id, end_event_id + 1):
            action = self.eventid_action_map.get(eid)
            if action:
                result.update(action.inputsTextures)
        return list(result)
    
    def get_inputs_in_range_by_actionid(self, start_action_id, end_action_id):
        """获取指定 action_id 范围内的所有输入纹理资源ID集合"""
        start_event_id = self.get_event_id(start_action_id)
        end_event_id = self.get_event_id(end_action_id)
        if start_event_id is None or end_event_id is None:
            return []
        return self.get_inputs_in_range(start_event_id, end_event_id)

    def get_outputs_in_range(self, start_event_id, end_event_id):
        """获取指定 event_id 范围内的所有输出纹理资源ID集合"""
        result = set()
        for eid in range(start_event_id, end_event_id + 1):
            action = self.eventid_action_map.get(eid)
            if action:
                result.update(action.outputsTextures)
        return list(result)

    def get_outputs_in_range_by_actionid(self, start_action_id, end_action_id):
        """获取指定 action_id 范围内的所有输出纹理资源ID集合"""
        start_event_id = self.get_event_id(start_action_id)
        end_event_id = self.get_event_id(end_action_id)
        if start_event_id is None or end_event_id is None:
            return []
        return self.get_outputs_in_range(start_event_id, end_event_id)

    def count_texture_resolutions_in_range_by_actionid(self, start_action_id, end_action_id, isOutput=False):
        """
        统计指定 action_id 范围内所有输入或输出纹理的不同分辨率数量，并按分辨率从大到小排序（去重）
        :param start_action_id: 起始 action_id
        :param end_action_id: 结束 action_id
        :param isOutput: True 统计输出纹理，False 统计输入纹理
        :return: list [((width, height), 数量), ...]，按分辨率从大到小排序
        """
        if isOutput:
            textures = self.get_outputs_in_range_by_actionid(start_action_id, end_action_id)
        else:
            textures = self.get_inputs_in_range_by_actionid(start_action_id, end_action_id)
        # 去重
        unique_textures = set(textures)
        res_counter = {}
        for tex in unique_textures:
            key = (tex.width, tex.height)
            res_counter[key] = res_counter.get(key, 0) + 1
        # 按分辨率面积从大到小排序
        sorted_list = sorted(res_counter.items(), key=lambda x: x[0][0] * x[0][1], reverse=True)
        return sorted_list
    
    def get_meshnum_in_range_by_actionid(self, start_action_id, end_action_id):
        """获取指定 action_id 范围内所有 Action 的 meshNum 总和"""
        start_event_id = self.get_event_id(start_action_id)
        end_event_id = self.get_event_id(end_action_id)
        if start_event_id is None or end_event_id is None:
            return 0
        total = 0
        for eid in range(start_event_id, end_event_id + 1):
            action = self.eventid_action_map.get(eid)
            if action:
                total += action.meshNum
        return total



    def print_stats(self):
        """打印所有事件的输入输出纹理统计"""
        for eid in sorted(self.eventid_action_map.keys()):
            action = self.eventid_action_map[eid]
            input_resids = [str(rid) for rid in action.inputsTextures]
            output_resids = [str(rid) for rid in action.outputsTextures]
            print(
                f"eventId {eid} Inputs: {len(input_resids)} {input_resids} | Outputs: {len(output_resids)} {output_resids}"
            )

# 用法示例
# stats = ControllerDataStats(controller)
# stats.print_stats()
# print(stats.get_inputs_by_eventid(100))
# print(stats.get_outputs_in_range(100, 110))


class TextureSaver:
    """
    纹理导出工具类，封装了导出单个纹理的核心逻辑。
    """
    open_directory = None 

    @staticmethod
    def is_renderbuffer(texture):
        """判断一个纹理是否为渲染缓冲区（ColorTarget 或 DepthTarget）"""
        if texture is None:
            return False
        flags = texture.creationFlags
        return (flags & rd.TextureCategory.ColorTarget) != 0 or (flags & rd.TextureCategory.DepthTarget) != 0

    @staticmethod
    def texture_has_slice_face(tex: rd.ResourceDescription):
        return tex.arraysize > 1 or tex.depth > 1

    @staticmethod
    def texture_has_mip_map(tex: rd.ResourceDescription):
        return not (tex.mips == 1 and tex.msSamp <= 1)

    @staticmethod
    def save_texture(capture_ctx, controller, resource_id, folder_name, tex_name="",export_rebuffer=False):
        texsave = rd.TextureSave()
        texsave.resourceId = resource_id
        if texsave.resourceId == rd.ResourceId.Null():
            return False

        resource_desc: rd.ResourceDescription = capture_ctx.GetResource(resource_id)
        texture: rd.TextureDescription = capture_ctx.GetTexture(resource_id)
        
        # 根据export_rebuffer参数判断是否导出renderbuffer
        if not export_rebuffer and TextureSaver.is_renderbuffer(texture):
            return False
        
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

        # 使用类变量 open_directory
        print(f"open_directory {TextureSaver.open_directory}")
        if TextureSaver.open_directory:
            folder_path = os.path.join(TextureSaver.open_directory, folder_name)
        else:
            folder_path = os.path.join(
                capture_ctx.open_directory if hasattr(capture_ctx, "open_directory") else os.path.expanduser("~/Pictures"),
                folder_name,
            )
            
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        if TextureSaver.texture_has_slice_face(texture):
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

        return True

    @staticmethod
    def export_all_textures(capture_ctx, controller, folder_name):
        """
        导出所有纹理到指定目录
        :param capture_ctx: RenderDoc CaptureContext 实例
        :param controller: RenderDoc 控制器实例
        :param folder_name: 导出目录名称
        :return: 导出成功的纹理数量
        """
        resources = controller.GetResources()
        texture_count = 0
        for res in resources:
            if res.type == rd.ResourceType.Texture:
                textureid = res.resourceId
                
                # 只导出输入资源类型的纹理
                usages = controller.GetUsage(textureid)
                for usage in usages:
                    if usage.usage in INPUT_RESOURCE_USAGES:
                        if TextureSaver.save_texture(capture_ctx, controller, textureid, folder_name, str(int(textureid))):
                            texture_count += 1
                        break
        return texture_count