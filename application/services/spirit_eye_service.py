"""天地灵眼服务"""
import time
import random
from typing import List, Optional

from ...core.config import ConfigManager
from ...core.exceptions import GameException
from ...domain.models.spirit_eye import SpiritEye, SpiritEyeInfo
from ...infrastructure.repositories.player_repo import PlayerRepository
from ...infrastructure.repositories.spirit_eye_repo import SpiritEyeRepository


class SpiritEyeService:
    """天地灵眼服务"""
    
    # 灵眼配置
    SPIRIT_EYE_TYPES = {
        1: {"name": "下品灵眼", "exp_per_hour": 500, "spawn_rate": 50},
        2: {"name": "中品灵眼", "exp_per_hour": 2000, "spawn_rate": 30},
        3: {"name": "上品灵眼", "exp_per_hour": 8000, "spawn_rate": 15},
        4: {"name": "极品灵眼", "exp_per_hour": 30000, "spawn_rate": 5},
    }
    
    def __init__(
        self,
        player_repo: PlayerRepository,
        spirit_eye_repo: SpiritEyeRepository,
        config_manager: ConfigManager
    ):
        self.player_repo = player_repo
        self.spirit_eye_repo = spirit_eye_repo
        self.config_manager = config_manager
    
    def spawn_spirit_eye(self) -> str:
        """生成新灵眼（定时调用）"""
        # 随机生成灵眼类型
        roll = random.randint(1, 100)
        eye_type = 1
        cumulative = 0
        for etype, config in self.SPIRIT_EYE_TYPES.items():
            cumulative += config["spawn_rate"]
            if roll <= cumulative:
                eye_type = etype
                break
        
        config = self.SPIRIT_EYE_TYPES[eye_type]
        now = int(time.time())
        
        eye_id = self.spirit_eye_repo.create_spirit_eye(
            eye_type=eye_type,
            eye_name=config["name"],
            exp_per_hour=config["exp_per_hour"],
            spawn_time=now
        )
        
        return f"天地间出现了一处【{config['name']}】(ID:{eye_id})！速来抢占！"
    
    def claim_spirit_eye(self, user_id: str, eye_id: int) -> str:
        """抢占灵眼（原子操作）"""
        # 获取玩家
        player = self.player_repo.get_player(user_id)
        if not player:
            raise GameException("你还未踏入修仙之路")
        
        # 检查是否已有灵眼
        existing = self.spirit_eye_repo.get_user_spirit_eye(user_id)
        if existing:
            raise GameException(f"❌ 你已占据【{existing.eye_name}】，无法再抢占")
        
        # 获取目标灵眼
        eye = self.spirit_eye_repo.get_spirit_eye(eye_id)
        if not eye:
            raise GameException("❌ 灵眼不存在")
        
        # 检查是否有主
        if not eye.is_available():
            raise GameException(f"❌ 此灵眼已被【{eye.owner_name or '某人'}】占据")
        
        # 抢占（原子操作）
        now = int(time.time())
        user_name = player.user_name or player.user_id[:8]
        success = self.spirit_eye_repo.claim_spirit_eye(eye_id, user_id, user_name, now)
        
        if not success:
            raise GameException("❌ 抢占失败，灵眼已被他人占据")
        
        return (
            f"✨ 成功抢占【{eye.eye_name}】！\n"
            f"每小时可获得 {eye.exp_per_hour:,} 修为！\n"
            f"使用 灵眼收取 领取收益"
        )
    
    def collect_spirit_eye(self, user_id: str) -> str:
        """收取灵眼收益"""
        # 获取玩家
        player = self.player_repo.get_player(user_id)
        if not player:
            raise GameException("你还未踏入修仙之路")
        
        # 获取灵眼
        eye = self.spirit_eye_repo.get_user_spirit_eye(user_id)
        if not eye:
            raise GameException("❌ 你还没有占据灵眼")
        
        now = int(time.time())
        
        # 检查冷却
        if not eye.can_collect(now):
            remaining = int(3600 - (now - eye.last_collect_time))
            minutes = remaining // 60
            raise GameException(f"❌ 收取冷却中，还需 {minutes} 分钟")
        
        # 计算收益
        hours, exp_income = eye.calculate_exp(now)
        
        if hours == 0 or exp_income == 0:
            raise GameException("❌ 暂无可收取的修为")
        
        # 增加修为
        self.player_repo.add_experience(user_id, exp_income)
        
        # 更新收取时间
        self.spirit_eye_repo.update_collect_time(eye.eye_id, now)
        
        return (
            f"✅ 灵眼收取成功！\n"
            f"━━━━━━━━━━━━━━━\n"
            f"【{eye.eye_name}】\n"
            f"累计时长：{hours} 小时\n"
            f"获得修为：+{exp_income:,}"
        )
    
    def release_spirit_eye(self, user_id: str) -> str:
        """释放灵眼"""
        # 获取玩家
        player = self.player_repo.get_player(user_id)
        if not player:
            raise GameException("你还未踏入修仙之路")
        
        # 获取灵眼
        eye = self.spirit_eye_repo.get_user_spirit_eye(user_id)
        if not eye:
            raise GameException("❌ 你没有占据灵眼")
        
        # 释放
        self.spirit_eye_repo.release_spirit_eye(eye.eye_id)
        
        return f"已释放【{eye.eye_name}】"
    
    def get_spirit_eye_info(self, user_id: str) -> tuple[Optional[SpiritEyeInfo], List[SpiritEyeInfo]]:
        """获取灵眼信息"""
        # 获取玩家
        player = self.player_repo.get_player(user_id)
        if not player:
            raise GameException("你还未踏入修仙之路")
        
        # 获取我的灵眼
        my_eye = self.spirit_eye_repo.get_user_spirit_eye(user_id)
        my_eye_info = None
        
        if my_eye:
            now = int(time.time())
            pending_hours, pending_exp = my_eye.calculate_exp(now)
            my_eye_info = SpiritEyeInfo(
                eye_id=my_eye.eye_id,
                eye_type=my_eye.eye_type,
                eye_name=my_eye.eye_name,
                exp_per_hour=my_eye.exp_per_hour,
                owner_id=my_eye.owner_id,
                owner_name=my_eye.owner_name,
                claim_time=my_eye.claim_time,
                pending_hours=pending_hours,
                pending_exp=pending_exp,
                is_available=False
            )
        
        # 获取可抢占的灵眼
        available_eyes = self.spirit_eye_repo.get_available_spirit_eyes()
        available_info = []
        
        for eye in available_eyes[:5]:  # 最多显示5个
            available_info.append(SpiritEyeInfo(
                eye_id=eye.eye_id,
                eye_type=eye.eye_type,
                eye_name=eye.eye_name,
                exp_per_hour=eye.exp_per_hour,
                owner_id=None,
                owner_name=None,
                claim_time=None,
                pending_hours=0,
                pending_exp=0,
                is_available=True
            ))
        
        return my_eye_info, available_info
