"""洞天福地服务"""
import time
from typing import Optional

from ...core.config import ConfigManager
from ...core.exceptions import GameException
from ...domain.models.blessed_land import BlessedLand, BlessedLandInfo
from ...infrastructure.repositories.player_repo import PlayerRepository
from ...infrastructure.repositories.blessed_land_repo import BlessedLandRepository


class BlessedLandService:
    """洞天福地服务"""
    
    # 洞天进化路线
    BLESSED_LAND_EVOLUTION = {
        1: {"name": "小洞天", "next": 2, "price": 10000, "exp_bonus": 0.05, "gold_per_hour": 100},
        2: {"name": "中洞天", "next": 3, "price": 25000, "exp_bonus": 0.10, "gold_per_hour": 500},
        3: {"name": "大洞天", "next": 4, "price": 100000, "exp_bonus": 0.20, "gold_per_hour": 2000},
        4: {"name": "福地", "next": 5, "price": 250000, "exp_bonus": 0.30, "gold_per_hour": 5000},
        5: {"name": "洞天福地", "next": None, "price": 500000, "exp_bonus": 0.50, "gold_per_hour": 10000},
    }
    
    # 洞天福地后的递增参数（类型 5 的继续升级）
    HEAVEN_UPGRADE = {
        "base_price": 1000000,
        "price_increment": 500000,  # 每次 +50万
        "gold_per_hour_increment": 1000,  # 每次 +1000
        "exp_bonus_increment": 0.05,  # 每次 +5%
        "max_extra_level": 50,  # 最多额外升50级
    }
    
    def __init__(
        self,
        player_repo: PlayerRepository,
        blessed_land_repo: BlessedLandRepository,
        config_manager: ConfigManager
    ):
        self.player_repo = player_repo
        self.blessed_land_repo = blessed_land_repo
        self.config_manager = config_manager
    
    def get_blessed_land_info(self, user_id: str) -> BlessedLandInfo:
        """获取洞天信息"""
        player = self.player_repo.get_player(user_id)
        if not player:
            raise GameException("你还未踏入修仙之路")
        
        land = self.blessed_land_repo.get_blessed_land(user_id)
        if not land:
            raise GameException("你还没有洞天")
        
        now = int(time.time())
        pending_hours, pending_gold = land.calculate_income(now)
        
        # 计算升级信息
        upgrade_cost = self._calculate_upgrade_cost(land)
        can_upgrade = upgrade_cost is not None
        
        return BlessedLandInfo(
            land_type=land.land_type,
            land_name=land.land_name,
            level=land.level or 1,
            exp_bonus=land.exp_bonus,
            gold_per_hour=land.gold_per_hour,
            last_collect_time=land.last_collect_time,
            pending_hours=pending_hours,
            pending_gold=pending_gold,
            max_level=999,  # 无上限
            upgrade_cost=upgrade_cost or 0,
            can_upgrade=can_upgrade
        )
    
    def _calculate_upgrade_cost(self, land: BlessedLand) -> Optional[int]:
        """
        计算升级费用
        
        Returns:
            升级费用，如果不能升级则返回 None
        """
        # 如果是洞天福地 (type=5)，继续升级
        if land.land_type == 5:
            # 计算已经额外升级的次数
            extra_level = (land.level or 1) - 1
            if extra_level >= self.HEAVEN_UPGRADE["max_extra_level"]:
                return None
            return self.HEAVEN_UPGRADE["base_price"] + (extra_level * self.HEAVEN_UPGRADE["price_increment"])
        
        # 其他类型，检查是否有下一阶
        next_type = self.BLESSED_LAND_EVOLUTION.get(land.land_type, {}).get("next")
        if next_type is None:
            return None
        
        next_config = self.BLESSED_LAND_EVOLUTION.get(next_type)
        if not next_config:
            return None
        
        return next_config["price"]
    
    def purchase_blessed_land(self, user_id: str, land_type: int) -> str:
        """购买洞天"""
        if land_type not in self.BLESSED_LAND_EVOLUTION:
            raise GameException("❌ 无效的洞天类型。可选：1-小洞天 2-中洞天 3-大洞天 4-福地 5-洞天福地")
        
        player = self.player_repo.get_player(user_id)
        if not player:
            raise GameException("你还未踏入修仙之路")
        
        existing = self.blessed_land_repo.get_blessed_land(user_id)
        if existing:
            raise GameException(f"❌ 你已拥有【{existing.land_name}】，请升级而非重新购买")
        
        config = self.BLESSED_LAND_EVOLUTION[land_type]
        price = config["price"]
        
        if player.gold < price:
            raise GameException(f"❌ 灵石不足！购买{config['name']}需要 {price:,} 灵石")
        
        self.player_repo.add_gold(user_id, -price)
        
        now = int(time.time())
        self.blessed_land_repo.create_blessed_land(
            user_id=user_id,
            land_type=land_type,
            land_name=config["name"],
            exp_bonus=config["exp_bonus"],
            gold_per_hour=config["gold_per_hour"]
        )
        self.blessed_land_repo.update_blessed_land(user_id, last_collect_time=now)
        
        return (
            f"✨ 恭喜获得【{config['name']}】！\n"
            f"━━━━━━━━━━━━━━━\n"
            f"修炼加成：+{config['exp_bonus']:.0%}\n"
            f"每小时产出：{config['gold_per_hour']} 灵石\n"
            f"━━━━━━━━━━━━━━━\n"
            f"使用 洞天收取 领取产出"
        )
    
    def upgrade_blessed_land(self, user_id: str) -> str:
        """升级洞天"""
        player = self.player_repo.get_player(user_id)
        if not player:
            raise GameException("你还未踏入修仙之路")
        
        land = self.blessed_land_repo.get_blessed_land(user_id)
        if not land:
            raise GameException("❌ 你还没有洞天！")
        
        # 计算升级费用
        upgrade_cost = self._calculate_upgrade_cost(land)
        if upgrade_cost is None:
            raise GameException(f"❌ 你的{land.land_name}已达最高阶！")
        
        if player.gold < upgrade_cost:
            raise GameException(f"❌ 灵石不足！升级需要 {upgrade_cost:,} 灵石")
        
        self.player_repo.add_gold(user_id, -upgrade_cost)
        
        # 检查是否是洞天福地 (type=5) 的额外升级
        if land.land_type == 5:
            # 洞天福地内升级（数值递增）
            new_level = (land.level or 1) + 1
            new_exp_bonus = land.exp_bonus + self.HEAVEN_UPGRADE["exp_bonus_increment"]
            new_gold_per_hour = land.gold_per_hour + self.HEAVEN_UPGRADE["gold_per_hour_increment"]
            
            self.blessed_land_repo.update_blessed_land(
                user_id=user_id,
                level=new_level,
                exp_bonus=new_exp_bonus,
                gold_per_hour=new_gold_per_hour
            )
            
            extra_level = new_level - 1
            return (
                f"🎉 {land.land_name}升级到 Lv.{new_level}！\n"
                f"━━━━━━━━━━━━━━━\n"
                f"修炼加成：+{new_exp_bonus:.1%}\n"
                f"每小时产出：{new_gold_per_hour} 灵石\n"
                f"花费：{upgrade_cost:,} 灵石\n"
                f"━━━━━━━━━━━━━━━\n"
                f"额外强化次数：{extra_level}"
            )
        
        # 进化到下一阶洞天
        next_type = self.BLESSED_LAND_EVOLUTION[land.land_type]["next"]
        next_config = self.BLESSED_LAND_EVOLUTION[next_type]
        
        self.blessed_land_repo.update_blessed_land(
            user_id=user_id,
            land_type=next_type,
            land_name=next_config["name"],
            level=1,
            exp_bonus=next_config["exp_bonus"],
            gold_per_hour=next_config["gold_per_hour"]
        )
        
        return (
            f"🎉 {land.land_name}进化成为【{next_config['name']}】！\n"
            f"━━━━━━━━━━━━━━━\n"
            f"修炼加成：+{next_config['exp_bonus']:.0%}\n"
            f"每小时产出：{next_config['gold_per_hour']} 灵石\n"
            f"花费：{upgrade_cost:,} 灵石"
        )
    
    def collect_income(self, user_id: str) -> str:
        """收取洞天产出"""
        player = self.player_repo.get_player(user_id)
        if not player:
            raise GameException("你还未踏入修仙之路")
        
        land = self.blessed_land_repo.get_blessed_land(user_id)
        if not land:
            raise GameException("❌ 你还没有洞天！")
        
        now = int(time.time())
        
        if not land.can_collect(now):
            remaining = int(3600 - (now - land.last_collect_time))
            minutes = remaining // 60
            raise GameException(f"❌ 收取冷却中，还需 {minutes} 分钟")
        
        hours, gold_income = land.calculate_income(now)
        
        if hours == 0:
            raise GameException("❌ 暂无可收取的产出")
        
        # 修为收益（基于修炼加成）
        exp_income = int(player.experience * land.exp_bonus * hours * 0.01)
        # 限制单次最大修为收益，防止爆炸
        max_exp_per_hour = 50000
        exp_income = min(exp_income, max_exp_per_hour * hours)
        
        self.player_repo.add_gold(user_id, gold_income)
        self.player_repo.add_experience(user_id, exp_income)
        self.blessed_land_repo.update_blessed_land(user_id, last_collect_time=now)
        
        player = self.player_repo.get_player(user_id)
        
        return (
            f"✅ 洞天收取成功！\n"
            f"━━━━━━━━━━━━━━━\n"
            f"累计时长：{hours} 小时\n"
            f"获得灵石：+{gold_income:,}\n"
            f"获得修为：+{exp_income:,}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"当前灵石：{player.gold:,}"
        )