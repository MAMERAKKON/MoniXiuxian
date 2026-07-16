"""灵田领域模型"""
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class HerbType(Enum):
    """灵草类型枚举"""
    SPIRIT_GRASS = "灵草"  # 1小时
    BLOOD_GRASS = "血灵草"  # 2小时
    ICE_HEART = "冰心草"  # 4小时
    FLAME_FLOWER = "火焰花"  # 8小时
    NINE_LEAF = "九叶灵芝"  # 24小时


@dataclass
class Crop:
    """作物"""
    name: str  # 灵草名称
    plant_time: int  # 种植时间
    mature_time: int  # 成熟时间
    wither_time: int  # 枯萎时间（成熟后48小时）
    slot: int  # 槽位
    
    def is_mature(self, current_time: int) -> bool:
        """检查是否成熟"""
        return current_time >= self.mature_time
    
    def is_withered(self, current_time: int) -> bool:
        """检查是否枯萎"""
        return current_time >= self.wither_time
    
    def get_status(self, current_time: int) -> str:
        """获取状态"""
        if self.is_withered(current_time):
            return "已枯萎"
        elif self.is_mature(current_time):
            return "可收获"
        else:
            remaining = (self.mature_time - current_time) // 3600
            return f"{remaining}小时后成熟"


@dataclass
class SpiritFarm:
    """灵田"""
    id: int  # ID
    user_id: str  # 用户ID
    level: int  # 等级
    crops: List[Crop]  # 作物列表
    
    def get_max_slots(self) -> int:
        """获取最大槽位数"""
        slots_by_level = {1: 3, 2: 5, 3: 8, 4: 12, 5: 20}
        return slots_by_level.get(self.level, 3)
    
    def get_available_slots(self) -> int:
        """获取可用槽位数"""
        return self.get_max_slots() - len(self.crops)
    
    def has_available_slot(self) -> bool:
        """检查是否有可用槽位"""
        return self.get_available_slots() > 0


@dataclass
class SpiritFarmInfo:
    """灵田信息（用于显示）"""
    level: int  # 等级
    max_slots: int  # 最大槽位
    used_slots: int  # 已用槽位
    crops: List[Crop]  # 作物列表
    upgrade_cost: int  # 升级费用
    can_upgrade: bool  # 是否可升级
