"""
装备处理器

处理装备相关的命令。
"""
from typing import AsyncGenerator
from astrbot.api.event import AstrMessageEvent

from ...application.services.equipment_service import EquipmentService
from ...core.exceptions import BusinessException
from ..decorators import require_player


class EquipmentHandler:
    """装备处理器"""
    
    def __init__(self, equipment_service: EquipmentService, player_service):
        """
        初始化装备处理器
        
        Args:
            equipment_service: 装备服务
            player_service: 玩家服务
        """
        self.equipment_service = equipment_service
        self.player_service = player_service
    
    @require_player
    async def handle_show_equipment(self, event: AstrMessageEvent, player) -> AsyncGenerator[str, None]:
        """
        显示已装备的物品
        
        命令格式：我的装备
        """
        try:
            user_id = event.get_sender_id()
            
            # 获取已装备物品
            equipped_items = self.equipment_service.get_equipped_items(user_id)
            
            # 格式化输出
            message = self.equipment_service.format_equipped_items(equipped_items)
            
            yield event.plain_result(message)
            
        except BusinessException as e:
            yield event.plain_result(str(e))
        except Exception as e:
            yield event.plain_result(f"查看装备失败：{str(e)}")
    
    @require_player
    async def handle_equip_item(self, event: AstrMessageEvent, player, item_name: str = "") -> AsyncGenerator[str, None]:
        """
        装备物品
        
        命令格式：装备 <物品名称>
        """
        try:
            user_id = event.get_sender_id()
            
            # 检查参数
            if not item_name or item_name.strip() == "":
                yield event.plain_result("❌ 请指定要装备的物品名称\n💡 格式：装备 <物品名称>")
                return
            
            item_name = item_name.strip()
            
            # 装备物品
            equipment, old_equipment = self.equipment_service.equip_item(user_id, item_name)
            
            # 构建消息
            message_parts = [f"✅ 成功装备【{equipment.name}】"]
            
            if old_equipment:
                message_parts.append(f"卸下了【{old_equipment.name}】并放入储物戒")
            
            # 显示属性加成
            stats = self.equipment_service._format_stats(equipment.stats)
            if stats:
                message_parts.append(f"\n属性加成：{stats}")
            
            yield event.plain_result("\n".join(message_parts))
            
        except BusinessException as e:
            yield event.plain_result(f"❌ {str(e)}")
        except Exception as e:
            yield event.plain_result(f"❌ 装备失败：{str(e)}")
    
    @require_player
    async def handle_unequip_item(self, event: AstrMessageEvent, player, item_name: str = "") -> AsyncGenerator[str, None]:
        """
        卸下装备
        
        命令格式：
        - 卸下 <物品名称>
        - 卸下 武器
        - 卸下 防具
        - 卸下 主功法
        - 卸下 副功法
        """
        try:
            user_id = event.get_sender_id()
            
            # 检查参数
            if not item_name or item_name.strip() == "":
                yield event.plain_result("❌ 请指定要卸下的装备\n💡 格式：卸下 <物品名称> 或 卸下 <槽位>")
                return
            
            param = item_name.strip()
            
            # 确定是槽位还是物品名称
            slot_map = {
                "武器": "weapon",
                "防具": "armor",
                "主功法": "main_technique",
                "副功法": "technique",
            }
            
            if param in slot_map:
                # 按槽位卸下
                equipment = self.equipment_service.unequip_item(user_id, slot=slot_map[param])
            else:
                # 按名称卸下
                equipment = self.equipment_service.unequip_item(user_id, item_name=param)
            
            yield event.plain_result(f"✅ 成功卸下【{equipment.name}】并放入储物戒")
            
        except BusinessException as e:
            yield event.plain_result(f"❌ {str(e)}")
        except Exception as e:
            yield event.plain_result(f"❌ 卸下装备失败：{str(e)}")
