"""世界Boss生命周期、战斗与奖励服务。"""
import asyncio
import random
import time
from typing import List, Tuple, Optional

from ...core.config import ConfigManager
from ...core.exceptions import GameException
from ...domain.models.boss import Boss, BossBattleResult
from ...domain.models.combat import CombatStats
from ...domain.enums import CultivationType, PlayerState
from ...infrastructure.repositories.player_repo import PlayerRepository
from ...infrastructure.repositories.boss_repo import BossRepository
from ...infrastructure.repositories.storage_ring_repo import StorageRingRepository
from .combat_service import CombatService


class BossService:
    """负责固定模板Boss生成、脱战回血、累计伤害和击杀分账。"""

    BOSS_MAX_ROUNDS = 50
    MIN_RESPAWN_SECONDS = 300
    # 为分钟级轮询预留60秒，保证实际降临仍不超过击杀后3小时。
    MAX_RESPAWN_SECONDS = 3 * 60 * 60 - 60
    BOSS_REGEN_RATE_PER_HOUR = 0.10

    # 境界与数值完全固定，不读取玩家数量、战力或活跃度。
    REALM_CONFIGS = [
        {"name": "炼气", "weight": 40, "hp": 5_000, "atk": 150,
         "defense": 3, "exp": 10_000, "stone": 2_500, "drop_chance": 35.0},
        {"name": "筑基", "weight": 30, "hp": 15_000, "atk": 450,
         "defense": 5, "exp": 50_000, "stone": 12_500, "drop_chance": 42.0},
        {"name": "金丹", "weight": 20, "hp": 45_000, "atk": 1_200,
         "defense": 8, "exp": 200_000, "stone": 50_000, "drop_chance": 50.0},
        {"name": "元婴", "weight": 10, "hp": 140_000, "atk": 3_000,
         "defense": 10, "exp": 800_000, "stone": 200_000, "drop_chance": 58.0},
    ]

    # HP倍率已结合攻击压缩输出回合的影响校准；元婴档以三名标准玩家各战一场为基准。
    BOSS_TEMPLATES = [
        {"id": "blood_sea", "name": "血海妖皇", "weight": 25,
         "hp_mult": 1.00, "atk_mult": 1.00, "defense_add": 0,
         "reward_mult": 1.00, "damage_type": "physical", "drop_bonus": 0.0,
         "description": "攻守均衡的标准妖皇，适合作为同境界讨伐基准。"},
        {"id": "mountain_ape", "name": "山岳古猿", "weight": 20,
         "hp_mult": 1.25, "atk_mult": 0.80, "defense_add": 4,
         "reward_mult": 1.10, "damage_type": "physical", "drop_bonus": 2.0,
         "description": "血厚攻低的持久型Boss，能让修士获得更多输出回合。"},
        {"id": "thunder_beast", "name": "九霄雷兽", "weight": 20,
         "hp_mult": 0.72, "atk_mult": 1.30, "defense_add": -3,
         "reward_mult": 1.10, "damage_type": "magic", "drop_bonus": 3.0,
         "description": "以九霄雷法速战速决，生命较低但魔法爆发极高。"},
        {"id": "frost_dragon", "name": "玄冥冰蛟", "weight": 15,
         "hp_mult": 1.10, "atk_mult": 0.90, "defense_add": 7,
         "reward_mult": 1.20, "damage_type": "magic", "drop_bonus": 5.0,
         "description": "玄冰护体、减伤极高，以持续冰法消耗挑战者。"},
        {"id": "fire_demon", "name": "业火魔君", "weight": 15,
         "hp_mult": 0.79, "atk_mult": 1.20, "defense_add": 2,
         "reward_mult": 1.20, "damage_type": "magic", "drop_bonus": 5.0,
         "description": "驾驭业火的进攻型魔君，以高额魔法伤害压缩战斗时间。"},
        {"id": "star_beast", "name": "星陨巨兽", "weight": 5,
         "hp_mult": 0.93, "atk_mult": 1.15, "defense_add": 5,
         "reward_mult": 1.50, "damage_type": "physical", "drop_bonus": 10.0,
         "description": "低概率降临的稀有巨兽，强度、奖池与稀有掉落均更高。"},
    ]

    # min_realm: 0炼气、1筑基、2金丹、3元婴。
    BOSS_DROP_TABLES = {
        "blood_sea": [
            {"name": "妖兽精血", "weight": 45, "min": 1, "max": 3, "min_realm": 0},
            {"name": "灵兽内丹", "weight": 35, "min": 1, "max": 2, "min_realm": 1},
            {"name": "太古龙血草", "weight": 20, "min": 1, "max": 1, "min_realm": 3},
        ],
        "mountain_ape": [
            {"name": "玄铁", "weight": 45, "min": 2, "max": 5, "min_realm": 0},
            {"name": "星辰陨铁", "weight": 30, "min": 1, "max": 2, "min_realm": 1},
            {"name": "龙骨髓", "weight": 20, "min": 1, "max": 1, "min_realm": 2},
            {"name": "古代法器", "weight": 5, "min": 1, "max": 1, "min_realm": 3},
        ],
        "thunder_beast": [
            {"name": "星辰石", "weight": 50, "min": 1, "max": 3, "min_realm": 0},
            {"name": "天材地宝", "weight": 30, "min": 1, "max": 2, "min_realm": 1},
            {"name": "雷劫神木", "weight": 20, "min": 1, "max": 1, "min_realm": 2},
        ],
        "frost_dragon": [
            {"name": "冰魄草", "weight": 45, "min": 1, "max": 3, "min_realm": 0},
            {"name": "玄冰之核", "weight": 35, "min": 1, "max": 2, "min_realm": 1},
            {"name": "太阴神草", "weight": 15, "min": 1, "max": 1, "min_realm": 2},
            {"name": "寒霜剑", "weight": 5, "min": 1, "max": 1, "min_realm": 3},
        ],
        "fire_demon": [
            {"name": "火灵芝", "weight": 40, "min": 1, "max": 3, "min_realm": 0},
            {"name": "凤凰草", "weight": 30, "min": 1, "max": 2, "min_realm": 1},
            {"name": "业火红莲", "weight": 20, "min": 1, "max": 1, "min_realm": 2},
            {"name": "焚天诀残篇", "weight": 10, "min": 1, "max": 1, "min_realm": 3},
        ],
        "star_beast": [
            {"name": "星辰石", "weight": 40, "min": 2, "max": 5, "min_realm": 0},
            {"name": "星辰陨铁", "weight": 30, "min": 1, "max": 3, "min_realm": 1},
            {"name": "天材地宝", "weight": 20, "min": 1, "max": 2, "min_realm": 1},
            {"name": "古代法器", "weight": 8, "min": 1, "max": 1, "min_realm": 2},
            {"name": "混沌神石", "weight": 2, "min": 1, "max": 1, "min_realm": 3},
        ],
    }

    def __init__(
        self,
        player_repo: PlayerRepository,
        boss_repo: BossRepository,
        storage_ring_repo: StorageRingRepository,
        config_manager: ConfigManager,
        combat_service: CombatService,
    ):
        self.player_repo = player_repo
        self.boss_repo = boss_repo
        self.storage_ring_repo = storage_ring_repo
        self.config_manager = config_manager
        self.combat_service = combat_service
        # 同一插件实例内的Boss挑战串行结算，防止并发重复击杀和重复发奖。
        self._battle_lock = asyncio.Lock()

    @staticmethod
    def _weighted_choice(options: list[dict]) -> dict:
        """按weight从固定配置中抽取一项。"""
        total_weight = sum(max(0, int(option.get("weight", 0))) for option in options)
        if total_weight <= 0:
            return options[0]
        roll = random.uniform(0, total_weight)
        current = 0.0
        for option in options:
            current += max(0, int(option.get("weight", 0)))
            if roll <= current:
                return option
        return options[-1]

    def _get_realm_index(self, boss: Boss) -> int:
        return next(
            (
                index for index, realm in enumerate(self.REALM_CONFIGS)
                if realm["name"] == boss.boss_level
            ),
            0,
        )

    def _get_template(self, boss_type: str) -> dict:
        return next(
            (
                template for template in self.BOSS_TEMPLATES
                if template["id"] == boss_type
            ),
            self.BOSS_TEMPLATES[0],
        )

    def get_active_boss(self) -> Optional[Boss]:
        """获取当前Boss，并结算其脱战期间的缓慢回血。"""
        boss = self.boss_repo.get_active_boss()
        if boss:
            self._apply_boss_regeneration(boss)
        return boss

    def _apply_boss_regeneration(self, boss: Boss, now: Optional[int] = None) -> int:
        """按每小时10%最大生命连续结算Boss脱战回血。"""
        if boss.hp <= 0 or boss.hp >= boss.max_hp:
            boss.last_regen_time = now or int(time.time())
            boss.regen_remainder = 0.0
            return 0

        current_time = now or int(time.time())
        last_time = boss.last_regen_time or boss.create_time or current_time
        elapsed = max(0, current_time - last_time)
        if elapsed <= 0:
            return 0

        regen_points = (
            boss.max_hp
            * self.BOSS_REGEN_RATE_PER_HOUR
            * elapsed
            / 3600.0
            + boss.regen_remainder
        )
        healed = min(boss.max_hp - boss.hp, int(regen_points))
        boss.regen_remainder = 0.0 if boss.hp + healed >= boss.max_hp else regen_points - healed
        boss.last_regen_time = current_time
        if healed > 0:
            boss.hp += healed
        self.boss_repo.update_boss(boss)
        return healed

    def spawn_boss(self, level_config: Optional[dict] = None) -> Boss:
        """从固定境界与常规模板中随机生成Boss。"""
        existing_boss = self.boss_repo.get_active_boss()
        if existing_boss:
            raise GameException(f"当前已有Boss『{existing_boss.boss_name}』存在！")

        selected_level = level_config or self._weighted_choice(self.REALM_CONFIGS)
        template = self._weighted_choice(self.BOSS_TEMPLATES)
        max_hp = max(300, int(round(selected_level["hp"] * template["hp_mult"])))
        atk = max(5, int(round(selected_level["atk"] * template["atk_mult"])))
        damage_reduction = max(
            0,
            min(35, int(selected_level["defense"] + template["defense_add"])),
        )
        exp_reward = max(
            1000,
            int(round(selected_level["exp"] * template["reward_mult"])),
        )
        stone_reward = max(
            500,
            int(round(selected_level["stone"] * template["reward_mult"])),
        )
        now = int(time.time())
        boss = Boss(
            boss_id=0,
            boss_name=template["name"] + f"·{selected_level['name']}境",
            boss_level=selected_level["name"],
            hp=max_hp,
            max_hp=max_hp,
            atk=max(1, atk),
            defense=damage_reduction,
            stone_reward=stone_reward,
            create_time=now,
            status=1,
            boss_type=template["id"],
            damage_type=template["damage_type"],
            exp_reward=exp_reward,
            reference_power=0,
            target_participants=3,
            last_regen_time=now,
        )
        boss.boss_id = self.boss_repo.create_boss(boss)
        self.boss_repo.clear_next_spawn_time()
        return boss

    def schedule_next_spawn(self, defeated_at: Optional[int] = None) -> int:
        """击杀后安排5分钟至3小时内随机重生，并持久化时间。"""
        base_time = defeated_at or int(time.time())
        spawn_time = base_time + random.randint(
            self.MIN_RESPAWN_SECONDS,
            self.MAX_RESPAWN_SECONDS,
        )
        self.boss_repo.set_next_spawn_time(spawn_time)
        return spawn_time

    def ensure_spawn_schedule(self) -> int:
        """兼容旧数据：无Boss且无计划时补建一次随机生成计划。"""
        if self.boss_repo.get_active_boss():
            return 0
        spawn_time = self.boss_repo.get_next_spawn_time()
        return spawn_time or self.schedule_next_spawn()

    def get_next_spawn_time(self) -> int:
        return self.boss_repo.get_next_spawn_time()

    def try_spawn_due_boss(self, now: Optional[int] = None) -> Optional[Boss]:
        """供分钟级定时任务调用；只有预定时间到达才生成。"""
        if self.boss_repo.get_active_boss():
            self.boss_repo.clear_next_spawn_time()
            return None
        current_time = now or int(time.time())
        spawn_time = self.ensure_spawn_schedule()
        if spawn_time > current_time:
            return None
        return self.spawn_boss()

    def auto_spawn_boss(self) -> Boss:
        """管理员立即生成一只随机常规Boss。"""
        return self.spawn_boss()

    def _roll_weighted_item(self, drop_table: list[dict]) -> Tuple[str, int]:
        total_weight = sum(item["weight"] for item in drop_table)
        roll = random.uniform(0, total_weight)
        current_weight = 0.0
        for item in drop_table:
            current_weight += item["weight"]
            if roll <= current_weight:
                return item["name"], random.randint(item["min"], item["max"])
        item = drop_table[-1]
        return item["name"], random.randint(item["min"], item["max"])

    def _roll_participant_drop(
        self,
        boss: Boss,
        rank: int,
        damage_share: float,
        average_share: float,
    ) -> List[Tuple[str, int]]:
        """每位参与者独立投掷；名次和高于平均伤害会提高概率。"""
        realm_index = self._get_realm_index(boss)
        realm = self.REALM_CONFIGS[realm_index]
        template = self._get_template(boss.boss_type)
        drop_table = [
            item for item in self.BOSS_DROP_TABLES.get(
                boss.boss_type,
                self.BOSS_DROP_TABLES["blood_sea"],
            )
            if int(item.get("min_realm", 0)) <= realm_index
        ]
        if not drop_table:
            return []
        base_chance = float(realm["drop_chance"]) + float(template["drop_bonus"])
        rank_bonus = {1: 15.0, 2: 10.0, 3: 6.0}.get(rank, 0.0)
        if average_share > 0:
            performance_bonus = max(
                -5.0,
                min(5.0, (damage_share / average_share - 1.0) * 5.0),
            )
        else:
            performance_bonus = 0.0
        drop_chance = max(10.0, min(85.0, base_chance + rank_bonus + performance_bonus))
        if random.random() * 100 >= drop_chance:
            return []
        return [self._roll_weighted_item(drop_table)]

    @staticmethod
    def _allocate_pool(pool: int, weights: dict[str, float], ranking: list[str]) -> dict[str, int]:
        allocations = {
            user_id: int(pool * weights[user_id])
            for user_id in ranking
        }
        remainder = max(0, pool - sum(allocations.values()))
        for user_id in ranking[:remainder]:
            allocations[user_id] += 1
        return allocations

    def _settle_boss_rewards(self, boss: Boss) -> list[dict]:
        """10%平均参与权重 + 90%伤害权重，再作±3%轻微浮动。"""
        damage_records = {
            user_id: max(0, int(damage))
            for user_id, damage in boss.damage_records.items()
            if int(damage) > 0
        }
        if not damage_records:
            return []

        ranking = sorted(
            damage_records,
            key=lambda user_id: damage_records[user_id],
            reverse=True,
        )
        total_damage = sum(damage_records.values())
        participant_count = len(ranking)
        average_share = 1.0 / participant_count
        raw_weights = {}
        for user_id in ranking:
            damage_share = damage_records[user_id] / total_damage
            fair_weight = 0.10 * average_share + 0.90 * damage_share
            raw_weights[user_id] = fair_weight * random.uniform(0.97, 1.03)
        weight_total = sum(raw_weights.values())
        weights = {
            user_id: raw_weights[user_id] / weight_total
            for user_id in ranking
        }

        exp_allocations = self._allocate_pool(boss.exp_reward, weights, ranking)
        gold_allocations = self._allocate_pool(boss.stone_reward, weights, ranking)
        distributions = []
        for rank, user_id in enumerate(ranking, start=1):
            damage_share = damage_records[user_id] / total_damage
            items = self._roll_participant_drop(
                boss,
                rank,
                damage_share,
                average_share,
            )
            player = self.player_repo.get_by_id(user_id)
            if player:
                actual_exp = self.player_repo.add_experience(
                    user_id,
                    exp_allocations[user_id]
                )
                self.player_repo.add_gold(user_id, gold_allocations[user_id])
                for item_name, count in items:
                    self.storage_ring_repo.add_item(user_id, item_name, count)
            else:
                actual_exp = 0
            distributions.append({
                "user_id": user_id,
                "name": boss.participant_names.get(user_id, f"道友{user_id[:6]}"),
                "rank": rank,
                "damage": damage_records[user_id],
                "weight": weights[user_id],
                "exp": actual_exp,
                "gold": gold_allocations[user_id],
                "items": items,
            })
        return distributions

    async def challenge_boss(self, user_id: str) -> BossBattleResult:
        """挑战Boss；无挑战冷却，但保留玩家真实伤势。"""
        user_id = str(user_id)
        async with self._battle_lock:
            player = self.player_repo.get_player(user_id)
            if not player:
                raise GameException("你还未踏入修仙之路")
            boss = self.get_active_boss()
            if not boss:
                raise GameException("当前没有Boss")
            if player.state != PlayerState.IDLE:
                raise GameException("你当前正忙，无法挑战Boss")

            if player.cultivation_type == CultivationType.PHYSICAL:
                current_player_hp = player.blood_qi
            else:
                current_player_hp = player.spiritual_qi
            if current_player_hp <= 0:
                raise GameException("你当前气血不足，请先服用回血丹药")

            player_stats = await self.combat_service.prepare_combat_stats(
                user_id,
                use_current_hp=True,
            )
            if not player_stats:
                raise GameException("你还未踏入修仙之路")

            starting_boss_hp = boss.hp
            starting_battle_hp = player_stats.hp
            boss_stats = CombatStats(
                user_id=f"boss:{boss.boss_id}",
                name=boss.boss_name,
                hp=max(0, boss.hp),
                max_hp=max(1, boss.max_hp),
                mp=0,
                max_mp=0,
                atk=max(1, boss.atk),
                defense=0,
                crit_rate=30.0,
                damage_type=(
                    boss.damage_type
                    if boss.damage_type in {"physical", "magic"}
                    else "physical"
                ),
                physical_defense=0,
                magic_defense=0,
                crit_damage=1.5,
                damage_reduction_percent=max(0.0, min(100.0, float(boss.defense))),
            )
            combat_log, rounds = self.combat_service.run_round_combat(
                player_stats,
                boss_stats,
                max_rounds=self.BOSS_MAX_ROUNDS,
                randomize_first=False,
            )
            boss_hp = max(0, boss_stats.hp)
            damage_dealt = max(0, starting_boss_hp - boss_hp)
            boss.damage_records[user_id] = boss.damage_records.get(user_id, 0) + damage_dealt
            boss.participant_names[user_id] = (
                player.user_name or player.nickname or f"道友{user_id[:6]}"
            )
            cumulative_damage = boss.damage_records[user_id]
            boss.hp = boss_hp
            boss.last_regen_time = int(time.time())
            boss_defeated = boss_hp <= 0

            reward_distribution = []
            next_spawn_time = 0
            if boss_defeated:
                boss.status = 0
                self.boss_repo.update_boss(boss)
            else:
                self.boss_repo.update_boss(boss)

            # Boss战继续产生真实伤势：战败保留1点，击杀时保存实际剩余血量。
            if boss_defeated:
                damage_taken = max(0, starting_battle_hp - player_stats.hp)
                persistent_hp = max(1, current_player_hp - damage_taken)
            else:
                persistent_hp = 1
            if player.cultivation_type == CultivationType.PHYSICAL:
                player.blood_qi = min(player.max_blood_qi, persistent_hp)
            else:
                player.spiritual_qi = min(player.max_spiritual_qi, persistent_hp)
            self.player_repo.save(player)

            # 先保存当前玩家伤势，再统一发奖，避免旧Player对象覆盖其奖励。
            if boss_defeated:
                reward_distribution = self._settle_boss_rewards(boss)
                next_spawn_time = self.schedule_next_spawn(boss.last_regen_time)

            personal_reward = next(
                (
                    reward for reward in reward_distribution
                    if reward["user_id"] == user_id
                ),
                None,
            )
            return BossBattleResult(
                success=boss_defeated,
                winner_id=user_id if boss_defeated else str(boss.boss_id),
                rounds=rounds,
                player_final_hp=persistent_hp,
                player_final_mp=player_stats.mp,
                boss_final_hp=boss_hp,
                stone_reward=personal_reward["gold"] if personal_reward else 0,
                items_gained=personal_reward["items"] if personal_reward else [],
                combat_log=combat_log,
                boss_defeated=boss_defeated,
                damage_dealt=damage_dealt,
                cumulative_damage=cumulative_damage,
                exp_reward=personal_reward["exp"] if personal_reward else 0,
                reward_distribution=reward_distribution,
                next_spawn_time=next_spawn_time,
            )
