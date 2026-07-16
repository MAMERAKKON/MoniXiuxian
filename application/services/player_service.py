"""玩家业务服务"""
import random
from datetime import datetime
from typing import Optional

from ...core.config import ConfigManager
from ...core.exceptions import (
    PlayerAlreadyExistsException,
    PlayerNotFoundException,
    InvalidParameterException
)
from ...domain.models.player import Player
from ...domain.enums import CultivationType
from ...domain.factories import PlayerFactory
from ...infrastructure.repositories.player_repo import PlayerRepository
from ...infrastructure.repositories.reincarnation_repo import ReincarnationRepository
from ...utils.spirit_root_generator import SpiritRootGenerator


class PlayerService:
    """玩家业务服务"""
    
    def __init__(
        self,
        player_repo: PlayerRepository,
        config_manager: ConfigManager,
        reincarnation_repo: Optional[ReincarnationRepository] = None
    ):
        self.player_repo = player_repo
        self.config_manager = config_manager
        self.reincarnation_repo = reincarnation_repo
        self.spirit_root_generator = SpiritRootGenerator(config_manager)
    
    def _apply_reincarnation_bonus(self, player: Player, bonus: dict) -> Player:
        """
        应用转世传承加成到玩家属性
        
        Args:
            player: 玩家对象
            bonus: 永久池加成数据
            
        Returns:
            加成后的玩家对象
        """
        # 百分比加成
        if bonus.get("hp_percent", 0) > 0:
            if player.cultivation_type == CultivationType.PHYSICAL:
                player.max_blood_qi = int(player.max_blood_qi * (1 + bonus["hp_percent"]))
                player.blood_qi = player.max_blood_qi
            else:
                player.max_spiritual_qi = int(player.max_spiritual_qi * (1 + bonus["hp_percent"]))
                player.spiritual_qi = player.max_spiritual_qi
        
        if bonus.get("attack_percent", 0) > 0:
            if player.cultivation_type == CultivationType.PHYSICAL:
                player.physical_damage = int(player.physical_damage * (1 + bonus["attack_percent"]))
            else:
                player.magic_damage = int(player.magic_damage * (1 + bonus["attack_percent"]))
        
        if bonus.get("mp_percent", 0) > 0:
            player.mental_power = int(player.mental_power * (1 + bonus["mp_percent"]))
        
        if bonus.get("defense_percent", 0) > 0:
            if player.cultivation_type == CultivationType.PHYSICAL:
                player.physical_defense = int(player.physical_defense * (1 + bonus["defense_percent"]))
            else:
                player.magic_defense = int(player.magic_defense * (1 + bonus["defense_percent"]))
        
        # 白值加成
        if bonus.get("hp_flat", 0) > 0:
            if player.cultivation_type == CultivationType.PHYSICAL:
                player.max_blood_qi += int(bonus["hp_flat"])
                player.blood_qi = player.max_blood_qi
            else:
                player.max_spiritual_qi += int(bonus["hp_flat"])
                player.spiritual_qi = player.max_spiritual_qi
        
        if bonus.get("attack_flat", 0) > 0:
            if player.cultivation_type == CultivationType.PHYSICAL:
                player.physical_damage += int(bonus["attack_flat"])
            else:
                player.magic_damage += int(bonus["attack_flat"])
        
        if bonus.get("mp_flat", 0) > 0:
            player.mental_power += int(bonus["mp_flat"])
        
        if bonus.get("defense_flat", 0) > 0:
            if player.cultivation_type == CultivationType.PHYSICAL:
                player.physical_defense += int(bonus["defense_flat"])
            else:
                player.magic_defense += int(bonus["defense_flat"])
        
        return player
    
    def create_player(
        self,
        user_id: str,
        cultivation_type: CultivationType,
        user_name: Optional[str] = None
    ) -> Player:
        """
        创建玩家
        
        Args:
            user_id: 用户ID
            cultivation_type: 修炼类型
            user_name: 用户名（QQ昵称），如果提供则使用，否则使用默认格式
            
        Returns:
            创建的玩家对象
            
        Raises:
            PlayerAlreadyExistsException: 玩家已存在
        """
        # 检查是否已存在
        if self.player_repo.exists(user_id):
            raise PlayerAlreadyExistsException(user_id)
        
        # 生成灵根
        spirit_root = self.spirit_root_generator.generate_random_root()
        
        # 获取初始灵石配置
        initial_gold = self.config_manager.settings.values.initial_gold
        
        # 创建玩家
        player = PlayerFactory.create_new_player(
            user_id=user_id,
            cultivation_type=cultivation_type,
            spirit_root=spirit_root,
            initial_gold=initial_gold,
            user_name=user_name
        )
        
        # ⭐⭐⭐ 应用永久传承池加成 ⭐⭐⭐
        if self.reincarnation_repo:
            try:
                permanent_pool = self.reincarnation_repo.get_permanent_pool(user_id)
                if permanent_pool and any(v > 0 for v in permanent_pool.values()):
                    player = self._apply_reincarnation_bonus(player, permanent_pool)
                    
                    from astrbot.api import logger
                    total_value = sum(permanent_pool.values())
                    logger.info(f"【传承】新角色 {user_id} 继承永久池，总值 {total_value:.2f}")
            except Exception as e:
                from astrbot.api import logger
                logger.warning(f"【传承】应用永久池加成失败: {e}")
        
        # 保存
        self.player_repo.save(player)
        
        return player
    
    def get_player(self, user_id: str) -> Optional[Player]:
        """
        获取玩家
        
        Args:
            user_id: 用户ID
            
        Returns:
            玩家对象，不存在则返回None
        """
        return self.player_repo.get_by_id(user_id)
    
    def get_player_or_raise(self, user_id: str) -> Player:
        """
        获取玩家，不存在则抛出异常
        
        Args:
            user_id: 用户ID
            
        Returns:
            玩家对象
            
        Raises:
            PlayerNotFoundException: 玩家不存在
        """
        player = self.player_repo.get_by_id(user_id)
        if player is None:
            raise PlayerNotFoundException(user_id)
        return player
    
    def update_player(self, player: Player) -> None:
        """
        更新玩家
        
        Args:
            player: 玩家对象
        """
        self.player_repo.save(player)
    
    def check_in(self, player: Player) -> int:
        """
        每日签到
        
        Args:
            player: 玩家对象
            
        Returns:
            获得的灵石数量
            
        Raises:
            ValueError: 今日已签到
        """
        today = datetime.now().strftime("%Y-%m-%d")
        
        if player.last_check_in_date == today:
            raise ValueError("今日已经签到过了")
        
        settings = self.config_manager.settings.values
        gold_min = settings.check_in_gold_min
        gold_max = settings.check_in_gold_max
        
        if gold_min > gold_max:
            gold_min, gold_max = gold_max, gold_min
        
        reward_gold = random.randint(gold_min, gold_max)
        
        player.add_gold(reward_gold)
        player.last_check_in_date = today
        
        self.player_repo.save(player)
        
        return reward_gold
    
    def change_nickname(self, player: Player, new_nickname: str) -> None:
        """
        修改道号
        
        Args:
            player: 玩家对象
            new_nickname: 新道号
            
        Raises:
            InvalidParameterException: 道号无效
        """
        new_nickname = new_nickname.strip()
        
        if not new_nickname:
            raise InvalidParameterException("道号", "道号不能为空")
        
        if len(new_nickname) > 12:
            raise InvalidParameterException("道号", "道号长度不能超过12个字符")
        
        existing = self.player_repo.get_by_nickname(new_nickname)
        if existing and existing.user_id != player.user_id:
            raise InvalidParameterException("道号", "该道号已被其他道友使用")
        
        player.nickname = new_nickname
        player.user_name = new_nickname
        
        self.player_repo.save(player)
    
    def delete_player(self, user_id: str) -> None:
        """
        删除玩家（弃道重修）
        
        Args:
            user_id: 用户ID
        """
        self.player_repo.delete(user_id)
    
    def get_level_name(self, player: Player) -> str:
        """
        获取境界名称
        
        Args:
            player: 玩家对象
            
        Returns:
            境界名称
        """
        level_data = self.config_manager.get_level_data(player.cultivation_type.value)
        
        if 0 <= player.level_index < len(level_data):
            level_info = level_data[player.level_index]
            return level_info.get("name") or level_info.get("level_name", "未知境界")
        return "未知境界"
    
    def get_required_exp(self, player: Player) -> int:
        """
        获取突破所需修为
        
        Args:
            player: 玩家对象
            
        Returns:
            所需修为
        """
        level_data = self.config_manager.get_level_data(player.cultivation_type.value)
        
        if player.level_index + 1 < len(level_data):
            next_level = level_data[player.level_index + 1]
            return next_level.get("required_exp") or next_level.get("exp_needed", 0)
        return 0
