"""战斗领域模型"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class CombatStats:
    """
    战斗属性
    
    用于战斗计算的玩家/Boss属性快照
    """
    user_id: str
    name: str  # 道号或Boss名称
    hp: int  # 当前气血
    max_hp: int  # 最大气血
    mp: int  # 当前真元
    max_mp: int  # 最大真元
    atk: int  # 攻击力
    defense: int = 0  # 主防御力（兼容旧调用）
    crit_rate: float = 0.0  # 会心率（百分比，0-100）
    exp: int = 0  # 修为（用于计算基础属性）
    damage_type: str = "physical"  # physical / magic
    physical_defense: int = 0
    magic_defense: int = 0
    crit_damage: float = 1.5  # 暴击伤害倍率
    damage_reduction_percent: float = 0.0  # Boss等单位的固定百分比减伤
    
    def is_alive(self) -> bool:
        """检查是否存活"""
        return self.hp > 0
    
    def take_damage(self, damage: int) -> int:
        """
        受到伤害
        
        Args:
            damage: 伤害值
            
        Returns:
            实际受到的伤害
        """
        actual_damage = min(damage, self.hp)
        self.hp = max(0, self.hp - damage)
        return actual_damage

    def get_defense_against(self, damage_type: str) -> int:
        """根据伤害类型返回对应防御。"""
        if damage_type == "magic":
            return max(0, self.magic_defense)
        return max(0, self.physical_defense)
    
    def restore_hp(self, amount: int) -> int:
        """
        恢复气血
        
        Args:
            amount: 恢复量
            
        Returns:
            实际恢复量
        """
        actual_restore = min(amount, self.max_hp - self.hp)
        self.hp = min(self.max_hp, self.hp + amount)
        return actual_restore


@dataclass
class CombatTurn:
    """
    战斗回合记录
    
    记录单个回合的攻击信息
    """
    round_num: int  # 回合数
    attacker_name: str  # 攻击者名称
    defender_name: str  # 防御者名称
    damage: int  # 造成的伤害
    is_crit: bool  # 是否暴击
    defender_hp_remaining: int  # 防御者剩余HP
    
    def to_log_message(self) -> str:
        """转换为战斗日志消息"""
        if self.is_crit:
            return f"{self.attacker_name} 发起会心一击，造成 {self.damage} 点伤害！"
        else:
            return f"{self.attacker_name} 发起攻击，造成 {self.damage} 点伤害"


@dataclass
class CombatResult:
    """
    战斗结果
    
    包含战斗的完整结果信息
    """
    winner_id: Optional[str]  # 获胜者ID，None表示平局
    winner_name: str  # 获胜者名称
    combat_log: list[str]  # 战斗日志
    rounds: int  # 战斗回合数
    
    # 玩家1最终状态
    player1_final_hp: int
    player1_final_mp: int
    
    # 玩家2最终状态（如果是PvP）
    player2_final_hp: Optional[int] = None
    player2_final_mp: Optional[int] = None
    
    # Boss最终状态（如果是PvE）
    boss_final_hp: Optional[int] = None
    
    # 奖励（如果有）
    gold_reward: int = 0
    exp_reward: int = 0
    
    def is_victory(self, user_id: str) -> bool:
        """检查指定玩家是否获胜"""
        return self.winner_id == user_id
    
    def is_draw(self) -> bool:
        """检查是否平局"""
        return self.winner_id is None


@dataclass
class CombatCooldown:
    """
    战斗冷却信息
    
    记录玩家的战斗冷却时间
    """
    user_id: str
    last_duel_time: int = 0  # 上次决斗时间（秒）
    last_spar_time: int = 0  # 上次切磋时间（秒）
    
    def can_duel(self, current_time: int, cooldown_seconds: int) -> bool:
        """检查是否可以决斗"""
        return (current_time - self.last_duel_time) >= cooldown_seconds
    
    def can_spar(self, current_time: int, cooldown_seconds: int) -> bool:
        """检查是否可以切磋"""
        return (current_time - self.last_spar_time) >= cooldown_seconds
    
    def get_duel_remaining(self, current_time: int, cooldown_seconds: int) -> int:
        """获取决斗剩余冷却时间（秒）"""
        elapsed = current_time - self.last_duel_time
        return max(0, cooldown_seconds - elapsed)
    
    def get_spar_remaining(self, current_time: int, cooldown_seconds: int) -> int:
        """获取切磋剩余冷却时间（秒）"""
        elapsed = current_time - self.last_spar_time
        return max(0, cooldown_seconds - elapsed)
