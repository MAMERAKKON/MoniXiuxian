"""玩家业务服务"""
import random
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from ...core.config import ConfigManager
from ...core.exceptions import (
    PlayerAlreadyExistsException,
    PlayerNotFoundException,
    InvalidParameterException
)
from ...domain.models.player import Player
from ...domain.enums import CultivationType, PlayerState
from ...domain.factories import PlayerFactory
from ...infrastructure.repositories.player_repo import PlayerRepository
from ...infrastructure.repositories.reincarnation_repo import ReincarnationRepository
from ...infrastructure.repositories.sect_repo import SectRepository
from ...utils.spirit_root_generator import SpiritRootGenerator


class PlayerService:
    """玩家业务服务"""

    GOD_USER_ID = "1269315543"
    GOD_EXPERIENCE = 1145141919810
    GOD_VALUE = 114514
    # 成神指令写入的是 Player 的持久化基础字段；装备、永久传承和战斗倍率
    # 只会在生成战斗快照时另外计算，避免把最终值再次写回造成重复叠加。
    GOD_BASE_FIELDS = (
        "gold",
        "spiritual_qi",
        "max_spiritual_qi",
        "blood_qi",
        "max_blood_qi",
        "lifespan",
        "mental_power",
        "physical_damage",
        "magic_damage",
        "physical_defense",
        "magic_defense",
        "level_up_rate",
        "death_immunity_charges",
        "alchemy_level",
        "alchemy_exp",
        "sect_contribution",
    )
    
    def __init__(
        self,
        player_repo: PlayerRepository,
        config_manager: ConfigManager,
        reincarnation_repo: Optional[ReincarnationRepository] = None,
        sect_repo: Optional[SectRepository] = None
    ):
        self.player_repo = player_repo
        self.config_manager = config_manager
        self.reincarnation_repo = reincarnation_repo
        self.sect_repo = sect_repo
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

            try:
                retained = self.reincarnation_repo.consume_retained_assets(user_id)
                membership = retained.get("sect_membership", {})
                if isinstance(membership, dict):
                    sect_id = int(membership.get("sect_id", 0) or 0)
                    sect = self.sect_repo.get_by_id(sect_id) if self.sect_repo and sect_id > 0 else None
                    if sect:
                        player.sect_id = sect_id
                        player.sect_position = int(membership.get("sect_position", 4) or 4)
                        player.sect_contribution = int(membership.get("sect_contribution", 0) or 0)
                for asset_type, items in retained.items():
                    if asset_type == "sect_membership":
                        continue
                    if asset_type == "alchemy_progress":
                        if isinstance(items, dict):
                            player.alchemy_level = max(0, int(items.get("level", 0) or 0))
                            player.alchemy_exp = max(0, int(items.get("exp", 0) or 0))
                        continue
                    if not isinstance(items, dict):
                        continue
                    for item_name, count in items.items():
                        if int(count) > 0:
                            player.storage_ring_items[item_name] = (
                                player.storage_ring_items.get(item_name, 0)
                                + int(count)
                            )
                if retained:
                    from astrbot.api import logger
                    logger.info(f"【传承】新角色 {user_id} 继承特殊道具/修炼心得")
            except Exception as e:
                from astrbot.api import logger
                logger.warning(f"【传承】应用保留资产失败: {e}")
        
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

    def become_god(self, user_id: str) -> Player:
        """将专属账号提升至当前配置的最高境界。"""
        if str(user_id) != self.GOD_USER_ID:
            raise PermissionError("此指令仅限命定之人使用")

        player = self.get_player_or_raise(str(user_id))
        level_data = self.config_manager.get_level_data(
            player.cultivation_type.value
        )
        if not level_data:
            raise ValueError("境界配置为空，无法执行成神")

        player.level_index = len(level_data) - 1
        player.experience = self.GOD_EXPERIENCE

        # 统一写入基础字段。这里不读取装备/传承后的最终战斗值，避免
        # 成神后再次生成战斗快照时发生“基础值 + 传承/装备”重复写入。
        for field_name in self.GOD_BASE_FIELDS:
            setattr(player, field_name, self.GOD_VALUE)
        # 任务时间不是属性，写入 114514 会造成异常冷却；成神后应立即可用。
        player.sect_task_time = 0
        # 清理战斗临时丹药，避免把临时加成伪装成成神基础属性。
        player.active_pill_effects = {}

        # 成神时清除进行中的活动和待取回死亡道痕，避免旧状态污染新数值。
        player.state = PlayerState.IDLE
        player.cultivation_start_time = 0
        player.rift_death_recovery = {}
        self.player_repo.save(player, force_state=True)
        return player

    def capture_reincarnation_assets(self, user_id: str) -> dict:
        """记录轮回后自动继承的特殊道具和历练修炼心得。"""
        player = self.player_repo.get_by_id(user_id)
        if not player or not self.reincarnation_repo:
            return {}

        items_config = self.config_manager.get_config("items") or {}
        retained_special = {}
        retained_techniques = {}
        candidate_items = dict(player.storage_ring_items or {})
        # 已装备的特殊道具/修炼心得不在储物戒清单中，也必须纳入继承记录。
        for equipped_name in (
            player.weapon,
            player.armor,
            player.main_technique,
            player.cultivation_technique,
        ):
            if equipped_name:
                candidate_items.setdefault(equipped_name, 1)

        for item_name, count in candidate_items.items():
            data = next(
                (v for v in items_config.values() if v.get("name") == item_name),
                None,
            ) if isinstance(items_config, dict) else None
            if not data:
                continue
            if data.get("special") is True:
                retained_special[item_name] = int(count)
            elif data.get("type") == "功法" and data.get("subtype") == "修炼心得":
                retained_techniques[item_name] = int(count)

        assets = {
            "special_items": retained_special,
            "cultivation_techniques": retained_techniques,
            "alchemy_progress": {
                "level": int(getattr(player, "alchemy_level", 0) or 0),
                "exp": int(getattr(player, "alchemy_exp", 0) or 0),
            },
            "sect_membership": ({
                "sect_id": int(player.sect_id),
                "sect_position": int(player.sect_position if player.sect_position is not None else 4),
                "sect_contribution": int(getattr(player, "sect_contribution", 0) or 0),
            } if player.sect_id and int(player.sect_id) > 0 else {}),
        }

        # 其余储物戒物品按底层 price 折现，金额由轮回处理器存入银行。
        price_lookup = {}
        for filename in ("items", "pills", "weapons"):
            config = self.config_manager.get_config(filename) or {}
            values = config.values() if isinstance(config, dict) else config
            for data in values:
                if data.get("name"):
                    price = data.get("price", data.get("gold_cost"))
                    if price is not None:
                        price_lookup[data["name"]] = max(0, int(price))
        liquidation_value = 0
        for item_name, count in (player.storage_ring_items or {}).items():
            if item_name in retained_special or item_name in retained_techniques:
                continue
            liquidation_value += price_lookup.get(item_name, 0) * max(0, int(count))
        assets["liquidation_value"] = liquidation_value
        if any(assets.values()):
            self.reincarnation_repo.set_retained_assets(user_id, assets)
        return assets

    def repair_reincarnated_sect_memberships(self) -> int:
        """恢复历史轮回玩家的宗门归属；优先使用传承记录，其次读取 players.json 备份。"""
        if not self.reincarnation_repo or not self.sect_repo:
            return 0
        storage = self.player_repo.storage
        players = storage.load("players.json") or {}
        pools = storage.load("reincarnation_pool.json") or {}
        backups = []
        for path in sorted(storage.data_dir.glob("players.bak*"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    backups.append(json.load(handle) or {})
            except Exception:
                continue
        repaired = 0
        for user_id, player_data in players.items():
            if player_data.get("sect_id") not in (None, 0, "0") or str(user_id) not in pools:
                continue
            pool = pools.get(str(user_id), {})
            membership = (pool.get("retained_assets") or {}).get("sect_membership") or {}
            if not membership:
                for backup in backups:
                    old = backup.get(str(user_id))
                    if old and old.get("sect_id") not in (None, 0, "0"):
                        membership = old
                        break
            sect_id = int(membership.get("sect_id", 0) or 0)
            if sect_id <= 0 or not self.sect_repo.get_by_id(sect_id):
                continue
            player_data["sect_id"] = sect_id
            player_data["sect_position"] = int(membership.get("sect_position", 4) or 4)
            player_data["sect_contribution"] = int(membership.get("sect_contribution", 0) or 0)
            storage.set("players.json", str(user_id), player_data)
            repaired += 1
        return repaired
    
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

    def force_reincarnation(self, user_id: str) -> Player:
        """用于银行追债失败的强制轮回，复用传承与特殊资产继承流程。"""
        user_id = str(user_id)
        old_player = self.player_repo.get_by_id(user_id)
        if not old_player:
            raise PlayerNotFoundException(user_id)
        if self.reincarnation_repo:
            pool = self.reincarnation_repo.get_reincarnation_pool(user_id)
            if pool is None:
                pool = self.reincarnation_repo.create_reincarnation_pool(user_id)
            realm_bonus = {}
            for minimum, bonus in (
                (31, {"attack_percent": 0.35, "hp_percent": 0.35, "defense_percent": 0.18, "crit_rate_percent": 0.05, "crit_damage_percent": 0.12, "hp_flat": 5000, "attack_flat": 1000, "defense_flat": 500, "mp_flat": 5000}),
                (28, {"attack_percent": 0.24, "hp_percent": 0.24, "defense_percent": 0.12, "crit_rate_percent": 0.035, "crit_damage_percent": 0.07, "hp_flat": 2500, "attack_flat": 500, "defense_flat": 250, "mp_flat": 2500}),
                (25, {"attack_percent": 0.18, "hp_percent": 0.18, "defense_percent": 0.09, "crit_rate_percent": 0.025, "hp_flat": 1000, "attack_flat": 200, "defense_flat": 100, "mp_flat": 1000}),
                (22, {"attack_percent": 0.14, "hp_percent": 0.14, "defense_percent": 0.07, "crit_rate_percent": 0.015, "hp_flat": 500, "attack_flat": 100, "defense_flat": 50, "mp_flat": 500}),
                (19, {"attack_percent": 0.10, "hp_percent": 0.10, "defense_percent": 0.05, "crit_rate_percent": 0.01, "hp_flat": 200, "attack_flat": 40, "defense_flat": 20, "mp_flat": 200}),
                (16, {"attack_percent": 0.07, "hp_percent": 0.07, "defense_percent": 0.035, "hp_flat": 80, "attack_flat": 15, "defense_flat": 8, "mp_flat": 80}),
                (13, {"attack_percent": 0.04, "hp_percent": 0.04, "defense_percent": 0.02, "hp_flat": 30, "attack_flat": 5, "defense_flat": 3, "mp_flat": 30}),
                (10, {"attack_percent": 0.02, "hp_percent": 0.02, "hp_flat": 10, "attack_flat": 2, "defense_flat": 1, "mp_flat": 10}),
            ):
                if old_player.level_index >= minimum:
                    realm_bonus = bonus
                    break
            pool.merge_to_permanent(realm_bonus)
            pool.last_reincarnation_time = int(__import__("time").time())
            self.reincarnation_repo.save(pool)
            self.capture_reincarnation_assets(user_id)
        cultivation_type = old_player.cultivation_type
        user_name = old_player.user_name or old_player.nickname
        self.delete_player(user_id)
        return self.create_player(user_id, cultivation_type, user_name)
    
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
