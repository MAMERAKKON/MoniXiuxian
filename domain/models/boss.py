"""Boss领域模型"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple, Optional


class BossStatus(Enum):
    """Boss状态枚举"""
    ALIVE = 1  # 存活
    DEFEATED = 0  # 已击败


class BossLevel(Enum):
    """Boss等级枚举"""
    LIANQI = "炼气"
    ZHUJI = "筑基"
    JINDAN = "金丹"
    YUANYING = "元婴"
    HUASHEN = "化神"
    LIANXU = "炼虚"
    HETI = "合体"
    DACHENG = "大乘"


@dataclass
class Boss:
    """Boss模型"""
    boss_id: int
    boss_name: str  # Boss名称
    boss_level: str  # Boss境界（炼气、筑基等）
    hp: int  # 当前HP
    max_hp: int  # 最大HP
    atk: int  # 攻击力
    defense: int  # 防御力（减伤百分比）
    stone_reward: int  # 灵石奖励
    create_time: int  # 创建时间戳
    status: int  # 状态（1=存活，0=已击败）
    boss_type: str = "blood_sea"  # Boss模板ID
    damage_type: str = "physical"  # physical / magic
    exp_reward: int = 0  # 全服参与者共享的修为奖池
    reference_power: int = 0  # 兼容旧存档，固定模板不再使用
    target_participants: int = 3  # 固定模板的标准讨伐人数
    damage_records: dict[str, int] = field(default_factory=dict)
    participant_names: dict[str, str] = field(default_factory=dict)
    last_regen_time: int = 0  # 上次结算Boss脱战回血的时间
    regen_remainder: float = 0.0  # 不足1点的回血余数
    
    def is_alive(self) -> bool:
        """检查Boss是否存活"""
        return self.status == BossStatus.ALIVE.value and self.hp > 0
    
    def get_hp_percent(self) -> float:
        """获取HP百分比"""
        if self.max_hp <= 0:
            return 0.0
        return (self.hp / self.max_hp) * 100
    
    def take_damage(self, damage: int) -> int:
        """受到伤害"""
        actual_damage = max(0, damage)
        self.hp = max(0, self.hp - actual_damage)
        if self.hp == 0:
            self.status = BossStatus.DEFEATED.value
        return actual_damage


@dataclass
class BossLevelConfig:
    """Boss等级配置"""
    name: str  # 境界名称
    level_index: int  # 境界索引
    hp_mult: float  # HP倍率
    atk_mult: float  # 攻击倍率
    reward_mult: float  # 奖励倍率


@dataclass
class BossBattleResult:
    """Boss战斗结果"""
    success: bool  # 是否胜利
    winner_id: str  # 胜利者ID
    rounds: int  # 战斗回合数
    player_final_hp: int  # 玩家最终HP
    player_final_mp: int  # 玩家最终MP
    boss_final_hp: int  # Boss最终HP
    stone_reward: int  # 灵石奖励
    items_gained: List[Tuple[str, int]]  # 获得的物品 [(物品名, 数量), ...]
    combat_log: List[str]  # 战斗日志
    boss_defeated: bool  # Boss是否被击败
    damage_dealt: int = 0  # 本次对Boss造成的实际伤害
    cumulative_damage: int = 0  # 本Boss期间的个人累计伤害
    exp_reward: int = 0  # 本次击杀结算中个人获得的修为
    reward_distribution: list[dict] = field(default_factory=list)
    next_spawn_time: int = 0
