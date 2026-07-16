"""值对象"""
from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class SpiritRootInfo:
    """灵根信息值对象"""
    name: str  # 灵根名称
    speed_multiplier: float  # 修炼速度倍率
    description: str  # 描述
    
    def get_display_name(self) -> str:
        """获取显示名称（带"灵根"后缀）"""
        if self.name.endswith("灵根") or self.name.endswith("道体") or self.name.endswith("体质"):
            return self.name
        return f"{self.name}灵根"


@dataclass(frozen=True)
class LevelInfo:
    """境界信息值对象"""
    index: int  # 境界索引
    name: str  # 境界名称
    realm: str  # 大境界名称
    layer: int  # 层数
    required_exp: int  # 所需修为
    breakthrough_exp: int  # 突破所需修为
    
    # 属性加成
    hp_bonus: int = 0
    mp_bonus: int = 0
    attack_bonus: int = 0
    defense_bonus: int = 0


@dataclass
class CultivationResult:
    """闭关结果值对象"""
    duration_minutes: int  # 闭关时长（分钟）
    gained_exp: int  # 获得的修为
    is_overtime: bool = False  # 是否超时
    max_minutes: int = 0  # 最大时长


@dataclass
class BreakthroughResult:
    """突破结果值对象"""
    success: bool  # 是否成功
    died: bool  # 是否死亡
    current_level: str  # 当前境界名称
    next_level: str  # 下一境界名称
    rate_info: str  # 成功率信息
    attribute_gains: dict  # 属性增长
    exp_loss: int = 0  # 修为损失（失败时）
