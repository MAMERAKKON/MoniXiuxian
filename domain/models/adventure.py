"""历练领域模型"""
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from enum import Enum


class AdventureEventType(Enum):
    """历练事件类型"""
    SAFE = "safe"  # 安全事件
    STANDARD = "standard"  # 标准事件
    RISKY = "risky"  # 危险事件
    DISASTER = "disaster"  # 灾难事件


@dataclass
class AdventureRoute:
    """历练路线"""
    key: str  # 路线标识
    name: str  # 路线名称
    risk: str  # 风险等级
    duration: int  # 持续时间（秒）
    base_gold: int  # 基础灵石奖励
    base_exp: int  # 基础修为奖励
    fatigue_cost: int  # 疲劳消耗
    events: List[Dict[str, Any]]  # 事件列表
    drops: List[Dict[str, Any]]  # 掉落物品列表
    aliases: List[str]  # 路线别名


@dataclass
class AdventureEvent:
    """历练事件"""
    type: str  # 事件类型
    description: str  # 事件描述
    gold_multiplier: float  # 灵石倍率
    exp_multiplier: float  # 修为倍率
    probability: float  # 发生概率


@dataclass
class AdventureResult:
    """历练结果"""
    success: bool  # 是否成功
    gold_gained: int  # 获得灵石
    exp_gained: int  # 获得修为
    items_gained: List[Dict[str, Any]]  # 获得物品
    event_type: Optional[str]  # 触发的事件类型
    event_description: Optional[str]  # 事件描述
    fatigue_cost: int  # 疲劳消耗
