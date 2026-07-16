"""统一玩家战斗业务服务。"""
import json
import random
import time
from typing import Optional, Tuple

from ...core.config import ConfigManager
from ...domain.enums import CultivationType, PlayerState
from ...domain.models.combat import CombatResult, CombatStats
from ...domain.models.player import Player
from ...infrastructure.repositories.combat_repo import CombatRepository
from ...infrastructure.repositories.player_repo import PlayerRepository
from ...infrastructure.repositories.reincarnation_repo import ReincarnationRepository


class CombatService:
    """生成统一战斗快照并执行无损玩家对战。"""

    SPAR_COOLDOWN = 60
    DUEL_COOLDOWN = 60
    MAX_ROUNDS = 20
    BASE_CRIT_DAMAGE = 1.5

    def __init__(
        self,
        player_repo: PlayerRepository,
        combat_repo: CombatRepository,
        config_manager: ConfigManager,
        reincarnation_repo: Optional[ReincarnationRepository] = None
    ):
        self.player_repo = player_repo
        self.combat_repo = combat_repo
        self.config_manager = config_manager
        self.reincarnation_repo = reincarnation_repo

    def _get_equipment_bonuses(self, user_id: str):
        """读取玩家所有已装备物品的合计属性。"""
        from .equipment_service import EquipmentService
        from ...infrastructure.repositories.equipment_repo import EquipmentRepository
        from ...infrastructure.repositories.storage_ring_repo import StorageRingRepository

        equipment_repo = EquipmentRepository(
            self.player_repo.storage,
            self.config_manager.config_dir
        )
        storage_ring_repo = StorageRingRepository(self.player_repo.storage)
        equipment_service = EquipmentService(
            equipment_repo,
            self.player_repo,
            storage_ring_repo
        )
        return equipment_service.get_equipment_bonuses(user_id)

    def _get_crit_bonuses(self, user_id: str) -> Tuple[float, float]:
        """
        获取永久传承中的暴击率和爆伤。

        HP、攻击和防御传承已经写入当前 Player 属性，不能在这里再次叠加；
        暴击字段没有写入 Player，因此在生成战斗快照时读取。
        """
        if not self.reincarnation_repo:
            return 0.0, 0.0
        try:
            pool = self.reincarnation_repo.get_permanent_pool(user_id)
            return (
                max(0.0, float(pool.get("crit_rate_percent", 0.0)) * 100.0),
                max(0.0, float(pool.get("crit_damage_percent", 0.0)))
            )
        except Exception:
            return 0.0, 0.0

    async def prepare_combat_stats(
        self,
        user_id: str,
        use_current_hp: bool = False
    ) -> Optional[CombatStats]:
        """
        根据玩家真实属性、修炼类型和装备生成战斗快照。

        use_current_hp=False 用于无损模式，每场以满血快照开始；
        use_current_hp=True 用于Boss等持久伤势模式，以当前气血/灵气入场。
        """
        user_id = str(user_id)
        player = self.player_repo.get_by_id(user_id)
        if not player:
            return None

        equipment = self._get_equipment_bonuses(user_id)
        crit_rate, crit_damage_bonus = self._get_crit_bonuses(user_id)

        if player.cultivation_type == CultivationType.PHYSICAL:
            base_current_hp = player.blood_qi
            base_max_hp = player.max_blood_qi
            atk = player.physical_damage + equipment.physical_damage
            damage_type = "physical"
        else:
            base_current_hp = player.spiritual_qi
            base_max_hp = player.max_spiritual_qi
            atk = player.magic_damage + equipment.magic_damage
            damage_type = "magic"

        max_hp = max(100, int(base_max_hp + equipment.max_hp))
        if use_current_hp:
            hp = max(1, min(max_hp, int(base_current_hp + equipment.max_hp)))
        else:
            hp = max_hp

        physical_defense = player.physical_defense + equipment.physical_defense
        magic_defense = player.magic_defense + equipment.magic_defense
        primary_defense = (
            physical_defense if player.cultivation_type == CultivationType.PHYSICAL
            else magic_defense
        )
        mp = player.mental_power + equipment.mental_power

        return CombatStats(
            user_id=user_id,
            name=player.nickname or f"道友{user_id[:6]}",
            hp=hp,
            max_hp=max_hp,
            mp=max(0, int(mp)),
            max_mp=max(0, int(mp)),
            atk=max(1, int(atk)),
            defense=max(0, int(primary_defense)),
            crit_rate=min(100.0, crit_rate),
            exp=player.experience,
            damage_type=damage_type,
            physical_defense=max(0, int(physical_defense)),
            magic_defense=max(0, int(magic_defense)),
            crit_damage=max(1.0, self.BASE_CRIT_DAMAGE + crit_damage_bonus)
        )

    @staticmethod
    def calculate_turn_attack(
        base_atk: int,
        crit_rate: float = 0.0,
        crit_damage: float = 1.5,
        atk_buff: float = 0.0
    ) -> Tuple[bool, int]:
        """计算单次攻击；0% 暴击率绝不会暴击。"""
        damage = int(base_atk * random.uniform(0.95, 1.05) * (1.0 + atk_buff))
        normalized_crit_rate = min(100.0, max(0.0, float(crit_rate)))
        is_crit = random.random() < normalized_crit_rate / 100.0
        if is_crit:
            damage = int(damage * max(1.0, crit_damage))
        return is_crit, max(1, damage)

    @staticmethod
    def apply_damage_reduction(damage: int, defense: int = 0) -> int:
        """
        按攻防相对值减伤，适配后期指数增长的属性。

        旧公式 defense / (defense + 100) 会让高境界防御接近100%减伤；
        新公式在攻防相等时减伤50%，并始终至少造成1点伤害。
        """
        damage = max(1, int(damage))
        defense = max(0, int(defense))
        if defense == 0:
            return damage
        final_damage = int(damage * damage / (damage + defense))
        return max(1, final_damage)

    @staticmethod
    def _state_name(player: Player) -> str:
        state = player.state
        return state.value if isinstance(state, PlayerState) else str(state)

    def _validate_combatants(self, attacker_id: str, defender_id: str) -> Tuple[Player, Player]:
        """统一检查玩家存在、自战和活动状态。"""
        attacker_id = str(attacker_id)
        defender_id = str(defender_id)
        if attacker_id == defender_id:
            raise ValueError("不能挑战自己")

        attacker = self.player_repo.get_by_id(attacker_id)
        defender = self.player_repo.get_by_id(defender_id)
        if not attacker:
            raise ValueError("发起者还未踏入修仙之路")
        if not defender:
            raise ValueError("对方还未踏入修仙之路")
        if attacker.state != PlayerState.IDLE:
            raise ValueError(f"你当前处于「{self._state_name(attacker)}」状态，无法战斗")
        if defender.state != PlayerState.IDLE:
            raise ValueError(f"对方当前处于「{self._state_name(defender)}」状态，无法战斗")
        return attacker, defender

    async def check_combat_cooldown(
        self,
        user_id: str,
        combat_type: str
    ) -> Tuple[bool, int]:
        """检查共用PvP冷却；切磋和决斗当前不能交替绕过60秒限制。"""
        cooldown = self.combat_repo.get_combat_cooldown(str(user_id))
        if not cooldown:
            return True, 0

        current_time = int(time.time())
        return (
            cooldown.can_spar(current_time, self.SPAR_COOLDOWN),
            cooldown.get_spar_remaining(current_time, self.SPAR_COOLDOWN)
        )

    async def update_combat_cooldown(self, user_id: str, combat_type: str) -> None:
        """更新发起者的共用PvP冷却。"""
        current_time = int(time.time())
        self.combat_repo.update_spar_cooldown(str(user_id), current_time)

    @staticmethod
    def _format_attack(attacker: CombatStats, defender: CombatStats) -> Tuple[str, bool]:
        is_crit, raw_damage = CombatService.calculate_turn_attack(
            attacker.atk,
            attacker.crit_rate,
            attacker.crit_damage
        )
        defense = defender.get_defense_against(attacker.damage_type)
        damage = CombatService.apply_damage_reduction(raw_damage, defense)
        reduction_percent = min(
            100.0,
            max(0.0, float(defender.damage_reduction_percent))
        )
        if reduction_percent > 0:
            damage = max(1, int(damage * (1.0 - reduction_percent / 100.0)))
        defender.take_damage(damage)
        crit_mark = "【暴击】" if is_crit else ""
        return (
            f"{attacker.name}{crit_mark}造成{damage:,}伤害，"
            f"{defender.name}剩余{defender.hp:,}",
            is_crit
        )

    def run_round_combat(
        self,
        player1: CombatStats,
        player2: CombatStats,
        max_rounds: int,
        randomize_first: bool = True
    ) -> Tuple[list[str], int]:
        """执行通用回合战斗并原地更新双方快照，不处理模式结算。"""
        def format_stats(combatant: CombatStats) -> str:
            line = (
                f"{combatant.name}：HP {combatant.hp:,}/{combatant.max_hp:,}｜"
                f"攻击 {combatant.atk:,}｜物防 {combatant.physical_defense:,}｜"
                f"法防 {combatant.magic_defense:,}"
            )
            if combatant.damage_reduction_percent > 0:
                line += f"｜固定减伤 {combatant.damage_reduction_percent:g}%"
            return line

        combat_log = [
            "⚔️ ━━━━ 战斗开始 ━━━━",
            f"{player1.name} VS {player2.name}",
            format_stats(player1),
            format_stats(player2)
        ]

        if randomize_first and random.random() >= 0.5:
            first, second = player2, player1
        else:
            first, second = player1, player2
        combat_log.append(f"先手：{first.name}")

        round_num = 0
        while player1.is_alive() and player2.is_alive() and round_num < max_rounds:
            round_num += 1
            round_messages = []

            attack_message, _ = self._format_attack(first, second)
            round_messages.append(attack_message)
            if second.is_alive():
                counter_message, _ = self._format_attack(second, first)
                round_messages.append(counter_message)

            combat_log.append(f"第{round_num}回合｜" + "；".join(round_messages))

        return combat_log, round_num

    def player_vs_player(
        self,
        player1: CombatStats,
        player2: CombatStats,
        combat_type: str = "spar"
    ) -> CombatResult:
        """执行统一无损PvP；combat_type目前只用于记录命令名称。"""
        combat_log, round_num = self.run_round_combat(
            player1,
            player2,
            self.MAX_ROUNDS,
            randomize_first=True
        )

        if player1.is_alive() and not player2.is_alive():
            winner_id, winner_name = player1.user_id, player1.name
        elif player2.is_alive() and not player1.is_alive():
            winner_id, winner_name = player2.user_id, player2.name
        else:
            # 达到回合上限后按剩余生命比例判定，比例完全相同才平局。
            player1_ratio = player1.hp / player1.max_hp
            player2_ratio = player2.hp / player2.max_hp
            if abs(player1_ratio - player2_ratio) < 1e-9:
                winner_id, winner_name = None, "平局"
            elif player1_ratio > player2_ratio:
                winner_id, winner_name = player1.user_id, player1.name
            else:
                winner_id, winner_name = player2.user_id, player2.name

        if winner_id is None:
            combat_log.append("🤝 ━━━━ 战斗平局 ━━━━")
        else:
            combat_log.append(f"🏆 ━━━━ {winner_name}胜利 ━━━━")
        combat_log.append("本次战斗为无损切磋，不消耗角色属性。")

        return CombatResult(
            winner_id=winner_id,
            winner_name=winner_name,
            combat_log=combat_log,
            rounds=round_num,
            player1_final_hp=player1.max_hp,
            player1_final_mp=player1.max_mp,
            player2_final_hp=player2.max_hp,
            player2_final_mp=player2.max_mp
        )

    async def _execute_pvp(
        self,
        attacker_id: str,
        defender_id: str,
        combat_type: str
    ) -> CombatResult:
        """切磋与决斗共用的无损执行流程。"""
        attacker_id = str(attacker_id)
        defender_id = str(defender_id)
        self._validate_combatants(attacker_id, defender_id)

        attacker_stats = await self.prepare_combat_stats(attacker_id)
        defender_stats = await self.prepare_combat_stats(defender_id)
        if not attacker_stats or not defender_stats:
            raise ValueError("玩家不存在")

        result = self.player_vs_player(attacker_stats, defender_stats, combat_type)
        self.combat_repo.save_combat_log(
            attacker_id=attacker_id,
            defender_id=defender_id,
            combat_type=combat_type,
            winner_id=result.winner_id,
            combat_log=json.dumps(result.combat_log, ensure_ascii=False)
        )
        await self.update_combat_cooldown(attacker_id, combat_type)
        return result

    async def execute_spar(self, attacker_id: str, defender_id: str) -> CombatResult:
        """执行无损切磋。"""
        return await self._execute_pvp(attacker_id, defender_id, "spar")

    async def execute_duel(self, attacker_id: str, defender_id: str) -> CombatResult:
        """暂时与切磋完全一致，仅保留 duel 日志类型。"""
        return await self._execute_pvp(attacker_id, defender_id, "duel")
