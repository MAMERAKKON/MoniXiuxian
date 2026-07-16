"""洞天福地领域模型"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class BlessedLandType(Enum):
    """洞天类型枚举"""
    SMALL = 1  # 小洞天
    MEDIUM = 2  # 中洞天
    LARGE = 3  # 大洞天
    BLESSED = 4  # 福地
    HEAVEN = 5  # 洞天福地


@dataclass
class BlessedLand:
    """洞天福地"""
    id: int  # ID
    user_id: str  # 用户ID
    land_type: int  # 洞天类型
    land_name: str  # 洞天名称
    level: int = 1  # 等级
    exp_bonus: float = 0.0  # 修为加成
    gold_per_hour: int = 0  # 每小时灵石产出
    last_collect_time: int = 0  # 上次收取时间
    
    def can_collect(self, current_time: int, min_interval: int = 3600) -> bool:
        """检查是否可以收取"""
        if self.last_collect_time == 0:
            return True
        return current_time - self.last_collect_time >= min_interval
    
    def calculate_income(self, current_time: int, max_hours: int = 24) -> tuple[int, int]:
        """
        计算可收取的收益
        
        Returns:
            (hours, gold) - 小时数和灵石数
        """
        if self.last_collect_time == 0:
            return 0, 0
        
        hours = (current_time - self.last_collect_time) // 3600
        hours = min(hours, max_hours)  # 最多累积24小时
        gold = hours * self.gold_per_hour
        
        return hours, gold


@dataclass
class BlessedLandInfo:
    """洞天福地信息（用于显示）"""
    land_type: int  # 洞天类型
    land_name: str  # 洞天名称
    level: int  # 等级
    exp_bonus: float  # 修为加成
    gold_per_hour: int  # 每小时灵石产出
    last_collect_time: int  # 上次收取时间
    pending_hours: int  # 待收取小时数
    pending_gold: int  # 待收取灵石
    max_level: int  # 最大等级
    upgrade_cost: int  # 升级费用
    can_upgrade: bool  # 是否可升级
