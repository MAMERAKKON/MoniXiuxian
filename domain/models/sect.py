"""
宗门领域模型

定义宗门、宗门成员等核心概念。
"""
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class SectPosition(Enum):
    """宗门职位"""
    LEADER = 0  # 宗主
    ELDER = 1  # 长老
    CORE_DISCIPLE = 2  # 亲传弟子
    INNER_DISCIPLE = 3  # 内门弟子
    OUTER_DISCIPLE = 4  # 外门弟子
    
    @property
    def display_name(self) -> str:
        """显示名称"""
        names = {
            SectPosition.LEADER: "宗主",
            SectPosition.ELDER: "长老",
            SectPosition.CORE_DISCIPLE: "亲传弟子",
            SectPosition.INNER_DISCIPLE: "内门弟子",
            SectPosition.OUTER_DISCIPLE: "外门弟子",
        }
        return names.get(self, "未知")


@dataclass
class SectMember:
    """宗门成员"""
    user_id: str
    user_name: str
    position: SectPosition
    contribution: int
    level_index: int
    
    def can_kick_others(self) -> bool:
        """是否有踢人权限"""
        return self.position in [SectPosition.LEADER, SectPosition.ELDER]
    
    def can_change_position(self) -> bool:
        """是否有变更职位权限"""
        return self.position == SectPosition.LEADER


@dataclass
class Sect:
    """宗门"""
    sect_id: int
    name: str
    leader_id: str
    scale: int  # 建设度
    funds: int  # 宗门灵石
    materials: int  # 宗门资材
    elixir_room_level: int  # 丹房等级
    created_at: int
    
    def can_accept_members(self, current_count: int, max_members: int = 50) -> bool:
        """是否可以接受新成员"""
        return current_count < max_members
    
    def add_donation(self, stone_amount: int) -> int:
        """
        添加捐献
        
        Args:
            stone_amount: 灵石数量
            
        Returns:
            增加的建设度
        """
        # 1灵石 = 10建设度
        scale_gain = stone_amount * 10
        self.scale += scale_gain
        self.funds += stone_amount
        return scale_gain
