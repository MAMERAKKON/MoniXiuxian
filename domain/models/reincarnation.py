"""转世传承领域模型 - 无上限版本"""
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class ReincarnationPool:
    """转世传承池（无上限）"""

    PERCENT_KEYS = {
        "hp_percent",
        "attack_percent",
        "mp_percent",
        "defense_percent",
        "crit_rate_percent",
        "crit_damage_percent"
    }
    
    user_id: str
    
    # 永久传承池（无上限，衰减控制增长）
    reincarnation_pool: Dict[str, float] = field(default_factory=lambda: {
        "hp_percent": 0.0,
        "attack_percent": 0.0,
        "mp_percent": 0.0,
        "defense_percent": 0.0,
        "crit_rate_percent": 0.0,
        "crit_damage_percent": 0.0,
        "hp_flat": 0.0,
        "attack_flat": 0.0,
        "mp_flat": 0.0,
        "defense_flat": 0.0
    })
    
    # 本世传承池
    current_life_pool: Dict[str, float] = field(default_factory=lambda: {
        "hp_percent": 0.0,
        "attack_percent": 0.0,
        "mp_percent": 0.0,
        "defense_percent": 0.0,
        "crit_rate_percent": 0.0,
        "crit_damage_percent": 0.0,
        "hp_flat": 0.0,
        "attack_flat": 0.0,
        "mp_flat": 0.0,
        "defense_flat": 0.0
    })
    
    reincarnation_count: int = 0
    last_reincarnation_time: Optional[int] = None
    
    def add_to_life_pool(self, prop_key: str, value: float) -> float:
        """添加传承到本世池"""
        if prop_key not in self.current_life_pool:
            self.current_life_pool[prop_key] = 0.0
        self.current_life_pool[prop_key] += value
        return self.current_life_pool[prop_key]
    
    def merge_to_permanent(self, extra_bonus: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        """
        将本世池与境界奖励作为“这一世”的收获合并到永久池。

        百分比按世乘算：新总加成 = (1 + 旧总加成) * (1 + 本世加成) - 1。
        固定数值仍然加算，避免固定属性也随轮回指数膨胀。
        """
        life_bonus: Dict[str, float] = {}

        for key, value in self.current_life_pool.items():
            if value > 0:
                life_bonus[key] = life_bonus.get(key, 0.0) + value

        if extra_bonus:
            for key, value in extra_bonus.items():
                if value > 0:
                    life_bonus[key] = life_bonus.get(key, 0.0) + value

        for key, value in life_bonus.items():
            current = self.reincarnation_pool.get(key, 0.0)
            if key in self.PERCENT_KEYS:
                self.reincarnation_pool[key] = (1.0 + current) * (1.0 + value) - 1.0
            else:
                self.reincarnation_pool[key] = current + value
        
        for key in self.current_life_pool:
            self.current_life_pool[key] = 0.0
        
        self.reincarnation_count += 1
        return self.reincarnation_pool
    
    def get_total_bonus(self) -> Dict[str, float]:
        """获取永久池总加成"""
        return self.reincarnation_pool.copy()
    
    def get_life_pool(self) -> Dict[str, float]:
        """获取本世池"""
        return self.current_life_pool.copy()
    
    def get_reincarnation_count(self) -> int:
        """获取转世次数"""
        return self.reincarnation_count


@dataclass
class ReincarnationBonus:
    """传承加成数据（用于战斗计算）"""
    
    hp_percent: float = 0.0
    attack_percent: float = 0.0
    mp_percent: float = 0.0
    defense_percent: float = 0.0
    crit_rate_percent: float = 0.0
    crit_damage_percent: float = 0.0
    hp_flat: float = 0.0
    attack_flat: float = 0.0
    mp_flat: float = 0.0
    defense_flat: float = 0.0
    
    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> "ReincarnationBonus":
        """从字典创建"""
        return cls(
            hp_percent=data.get("hp_percent", 0.0),
            attack_percent=data.get("attack_percent", 0.0),
            mp_percent=data.get("mp_percent", 0.0),
            defense_percent=data.get("defense_percent", 0.0),
            crit_rate_percent=data.get("crit_rate_percent", 0.0),
            crit_damage_percent=data.get("crit_damage_percent", 0.0),
            hp_flat=data.get("hp_flat", 0.0),
            attack_flat=data.get("attack_flat", 0.0),
            mp_flat=data.get("mp_flat", 0.0),
            defense_flat=data.get("defense_flat", 0.0)
        )
    
    def apply_to(self, base_value: float, percent_key: str, flat_key: str) -> int:
        """
        应用加成到基础值
        
        Args:
            base_value: 基础值
            percent_key: 百分比属性名
            flat_key: 白值属性名
            
        Returns:
            加成后的值
        """
        percent = getattr(self, percent_key, 0.0)
        flat = getattr(self, flat_key, 0.0)
        return int(base_value * (1 + percent) + flat)
