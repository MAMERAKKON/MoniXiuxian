"""传承系统服务"""
import asyncio
import random
import time
from datetime import datetime
from typing import Tuple, Optional, List, Dict

from ...infrastructure.repositories.impart_repo import ImpartRepository
from ...infrastructure.repositories.player_repo import PlayerRepository
from ...infrastructure.repositories.reincarnation_repo import ReincarnationRepository
from ...domain.models.impart import ImpartInfo
from ...core.config import ConfigManager
from ...domain.enums import PlayerState
from .combat_service import CombatService


class ImpartService:
    """传承服务 - 无上限永久池 + 衰减机制"""

    CHALLENGE_COOLDOWN_SECONDS = 30
    REINCARNATION_PROTECTION_SECONDS = 8 * 60 * 60
    DAILY_PROPERTY_LOSS_RATIO = 0.30
    
    # 传承属性配置（无上限，由衰减控制）
    PROP_CONFIG = {
        # ===== 百分比加成 =====
        'hp_percent': {
            'steal_range': (0.003, 0.008),
            'label': 'HP%',
            'weight': 20,
            'is_percent': True
        },
        'attack_percent': {
            'steal_range': (0.003, 0.008),
            'label': '攻击%',
            'weight': 20,
            'is_percent': True
        },
        'mp_percent': {
            'steal_range': (0.003, 0.008),
            'label': 'MP%',
            'weight': 15,
            'is_percent': True
        },
        'defense_percent': {
            'steal_range': (0.003, 0.008),
            'label': '防御%',
            'weight': 15,
            'is_percent': True
        },
        'crit_rate_percent': {
            'steal_range': (0.002, 0.005),
            'label': '暴击率',
            'weight': 6,
            'is_percent': True
        },
        'crit_damage_percent': {
            'steal_range': (0.003, 0.008),
            'label': '爆伤',
            'weight': 4,
            'is_percent': True
        },
        # ===== 白值加成 =====
        'hp_flat': {
            'steal_range': (3, 8),
            'label': 'HP(白)',
            'weight': 10,
            'is_percent': False
        },
        'attack_flat': {
            'steal_range': (2, 5),
            'label': '攻击(白)',
            'weight': 10,
            'is_percent': False
        },
        'mp_flat': {
            'steal_range': (3, 8),
            'label': 'MP(白)',
            'weight': 8,
            'is_percent': False
        },
        'defense_flat': {
            'steal_range': (2, 5),
            'label': '防御(白)',
            'weight': 8,
            'is_percent': False
        },
    }
    
    # 衰减阈值配置
    DECAY_CONFIG = [
        (0.5, 1.0),   # 0-50%：全额
        (1.0, 0.7),   # 50-100%：70%
        (2.0, 0.5),   # 100-200%：50%
        (5.0, 0.3),   # 200-500%：30%
        (float('inf'), 0.1),  # 500%+：10%
    ]
    
    def __init__(
        self,
        impart_repo: ImpartRepository,
        player_repo: PlayerRepository,
        reincarnation_repo: ReincarnationRepository,
        config_manager: ConfigManager,
        combat_service: CombatService
    ):
        self.impart_repo = impart_repo
        self.player_repo = player_repo
        self.reincarnation_repo = reincarnation_repo
        self.config_manager = config_manager
        self.combat_service = combat_service
        self._settlement_lock = asyncio.Lock()
    
    def _get_effective_steal(self, current_value: float, base_steal: float) -> float:
        """
        根据当前传承值计算实际偷取量（衰减）
        
        Args:
            current_value: 攻击者当前该属性的传承值
            base_steal: 基础偷取量
            
        Returns:
            实际偷取量
        """
        for threshold, multiplier in self.DECAY_CONFIG:
            if current_value < threshold:
                return base_steal * multiplier
        return base_steal * 0.1  # 兜底

    @staticmethod
    def _combine_pool_value(permanent: float, life: float, is_percent: bool) -> float:
        """按正式轮回口径计算永久池与本世池的实际总加成。"""
        permanent = max(0.0, float(permanent))
        life = max(0.0, float(life))
        if is_percent:
            return (1.0 + permanent) * (1.0 + life) - 1.0
        return permanent + life

    @staticmethod
    def _date_key() -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def _get_protection_remaining(self, user_id: str, now: Optional[int] = None) -> int:
        pool = self.reincarnation_repo.get_reincarnation_pool(str(user_id))
        if not pool or not pool.last_reincarnation_time:
            return 0
        elapsed = (now or int(time.time())) - int(pool.last_reincarnation_time)
        return max(0, self.REINCARNATION_PROTECTION_SECONDS - max(0, elapsed))

    def _break_reincarnation_protection(self, user_id: str) -> None:
        """主动开打传承挑战时立即放弃本轮轮回庇护。"""
        pool = self.reincarnation_repo.get_reincarnation_pool(str(user_id))
        if pool and pool.last_reincarnation_time:
            pool.last_reincarnation_time = None
            self.reincarnation_repo.save(pool)

    @staticmethod
    def _format_duration(seconds: int) -> str:
        hours, remainder = divmod(max(0, int(seconds)), 3600)
        minutes = (remainder + 59) // 60
        if hours:
            return f"{hours}小时{minutes}分钟"
        return f"{max(1, minutes)}分钟"

    def _get_daily_loss_status(
        self,
        user_id: str,
        prop_key: str,
        permanent_value: float,
        life_value: float,
        is_percent: bool
    ) -> Tuple[float, float, float]:
        """返回（剩余额度、已损失、每日上限），全部使用实际显示加成口径。"""
        current_total = self._combine_pool_value(
            permanent_value,
            life_value,
            is_percent
        )
        losses = self.impart_repo.get_daily_theft_losses(
            str(user_id),
            self._date_key()
        )
        already_lost = max(0.0, float(losses.get(prop_key, 0.0)))
        daily_base = current_total + already_lost
        daily_limit = daily_base * self.DAILY_PROPERTY_LOSS_RATIO
        return (
            max(0.0, daily_limit - already_lost),
            already_lost,
            daily_limit
        )

    def _get_stealable_keys(
        self,
        user_id: str,
        permanent_pool: Dict[str, float],
        life_pool: Dict[str, float]
    ) -> List[str]:
        keys = []
        for key, config in self.PROP_CONFIG.items():
            permanent_value = permanent_pool.get(key, 0.0)
            life_value = life_pool.get(key, 0.0)
            total = self._combine_pool_value(
                permanent_value,
                life_value,
                config["is_percent"]
            )
            remaining, _, _ = self._get_daily_loss_status(
                user_id,
                key,
                permanent_value,
                life_value,
                config["is_percent"]
            )
            if total > 0.001 and remaining > 1e-9:
                keys.append(key)
        return keys
    
    def get_impart_info(self, user_id: str) -> Tuple[bool, str]:
        """获取传承信息"""
        permanent_pool = self.reincarnation_repo.get_permanent_pool(user_id)
        life_pool = self.reincarnation_repo.get_life_pool(user_id)
        reincarnation_count = self.reincarnation_repo.get_reincarnation_count(user_id)
        protection_remaining = self._get_protection_remaining(user_id)
        
        lines = [
            "✨ 传承信息",
            "━━━━━━━━━━━━━━━",
            "",
            f"转世次数：{reincarnation_count}",
            "",
            "【永久传承池】（所有角色生效，无上限）",
        ]
        
        for key, config in self.PROP_CONFIG.items():
            value = permanent_pool.get(key, 0.0)
            if value > 0:
                unit = "%" if config['is_percent'] else ""
                display_value = value * 100 if config['is_percent'] else value
                lines.append(f"  {config['label']}：+{display_value:.1f}{unit}")
        
        if not any(v > 0 for v in permanent_pool.values()):
            lines.append("  暂无永久传承")
        
        lines.append("")
        lines.append("【本世传承池】（轮回后合并到永久池）")
        
        for key, config in self.PROP_CONFIG.items():
            value = life_pool.get(key, 0.0)
            if value > 0:
                unit = "%" if config['is_percent'] else ""
                display_value = value * 100 if config['is_percent'] else value
                lines.append(f"  {config['label']}：+{display_value:.1f}{unit}")
        
        if not any(v > 0 for v in life_pool.values()):
            lines.append("  暂无本世传承")
        
        lines.append("")
        if protection_remaining > 0:
            lines.append(
                "🛡️ 轮回庇护：剩余"
                f"{self._format_duration(protection_remaining)}"
                "（主动发起传承挑战将立即解除）"
            )
        lines.append("💡 使用【传承挑战 @目标】挑战他人夺取传承")
        lines.append("💡 传承越高，偷取效率越低（衰减机制）")
        lines.append("💡 轮回转世时本世池自动合并到永久池")
        
        return True, "\n".join(lines)
    
    async def challenge_impart(self, attacker_id: str, defender_id: str) -> Tuple[bool, str]:
        """发起传承挑战"""
        attacker_id = str(attacker_id)
        defender_id = str(defender_id)
        if attacker_id == defender_id:
            return False, "❌ 不能挑战自己。"
        
        attacker = self.player_repo.get_player(attacker_id)
        defender = self.player_repo.get_player(defender_id)
        
        if not attacker or not defender:
            return False, "❌ 对方还未踏入修仙之路。"
        
        if attacker.state != PlayerState.IDLE:
            return False, "❌ 你当前正忙，无法发起传承挑战"
        if defender.state != PlayerState.IDLE:
            return False, "❌ 对方当前正忙，无法接受传承挑战"

        protection_remaining = self._get_protection_remaining(
            defender_id,
            int(time.time())
        )
        if protection_remaining > 0:
            return False, (
                "🛡️ 对方正受轮回庇护，暂时无法被传承挑战。\n"
                f"剩余时间：{self._format_duration(protection_remaining)}"
            )

        current_time = int(time.time())
        last_challenge_time = self.impart_repo.get_challenge_cooldown_time(
            attacker_id
        )
        elapsed = current_time - last_challenge_time
        if last_challenge_time > 0 and elapsed < self.CHALLENGE_COOLDOWN_SECONDS:
            remaining = self.CHALLENGE_COOLDOWN_SECONDS - max(0, elapsed)
            return False, f"⏳ 传承挑战冷却中，还需等待 {remaining} 秒。"
        
        # 检查防守者是否有传承
        defender_permanent = self.reincarnation_repo.get_permanent_pool(defender_id)
        defender_life = self.reincarnation_repo.get_life_pool(defender_id)
        if not any(v > 0 for v in defender_permanent.values()) and not any(v > 0 for v in defender_life.values()):
            return False, "❌ 对方没有任何传承可以偷取"

        if not self._get_stealable_keys(
            defender_id,
            defender_permanent,
            defender_life
        ):
            return False, "🛡️ 对方今日各项传承均已达到30%抽取上限。"

        # 在首次异步等待前预占冷却，防止同一玩家双发消息同时开战。
        self.impart_repo.set_challenge_cooldown_time(attacker_id, current_time)

        attacker_stats = await self.combat_service.prepare_combat_stats(attacker_id)
        defender_stats = await self.combat_service.prepare_combat_stats(defender_id)
        if not attacker_stats or not defender_stats:
            self.impart_repo.clear_challenge_cooldown(attacker_id)
            return False, "❌ 战斗属性生成失败，请稍后重试"

        self._break_reincarnation_protection(attacker_id)

        combat_log, _ = self.combat_service.run_round_combat(
            attacker_stats,
            defender_stats,
            max_rounds=10,
            randomize_first=True
        )

        if not defender_stats.is_alive():
            attacker_wins = True
        elif not attacker_stats.is_alive():
            attacker_wins = False
        else:
            attacker_ratio = attacker_stats.hp / attacker_stats.max_hp
            defender_ratio = defender_stats.hp / defender_stats.max_hp
            attacker_wins = attacker_ratio >= defender_ratio

        combat_text = "\n".join(combat_log)
        
        if attacker_wins:
            async with self._settlement_lock:
                result_msg = self._apply_steal(attacker_id, defender_id)
            return True, f"{combat_text}\n\n{result_msg}"
        else:
            exp_loss = int(attacker.experience * 0.01)
            attacker.experience = max(0, attacker.experience - exp_loss)
            self.player_repo.save(attacker)
            return True, (
                f"{combat_text}\n\n"
                f"💀 传承挑战失败...\n"
                f"━━━━━━━━━━━━━━━\n"
                f"对手：{defender.nickname or defender_id[:8]}\n"
                f"损失修为：-{exp_loss:,}\n"
            )
    
    def _deduct_display_loss(
        self,
        pool,
        prop_key: str,
        desired_loss: float,
        is_percent: bool
    ) -> float:
        """优先扣本世池，并保证扣除量等于乘算后实际显示损失。"""
        permanent = max(0.0, float(pool.reincarnation_pool.get(prop_key, 0.0)))
        life = max(0.0, float(pool.current_life_pool.get(prop_key, 0.0)))
        before = self._combine_pool_value(permanent, life, is_percent)
        desired_loss = min(max(0.0, desired_loss), before)

        if is_percent:
            # 本世因子每减少1点，会使总加成减少 (1 + 永久池) 点。
            life_reduction = min(life, desired_loss / (1.0 + permanent))
            life_after = max(0.0, life - life_reduction)
            after_life = self._combine_pool_value(permanent, life_after, True)
            remaining_loss = max(0.0, desired_loss - (before - after_life))

            # 本世池耗尽后，再从永久总因子中扣除剩余实际损失。
            permanent_reduction = min(
                permanent,
                remaining_loss / (1.0 + life_after)
            )
            permanent_after = max(0.0, permanent - permanent_reduction)
        else:
            life_reduction = min(life, desired_loss)
            life_after = max(0.0, life - life_reduction)
            permanent_reduction = min(permanent, desired_loss - life_reduction)
            permanent_after = max(0.0, permanent - permanent_reduction)

        pool.current_life_pool[prop_key] = life_after
        pool.reincarnation_pool[prop_key] = permanent_after
        after = self._combine_pool_value(permanent_after, life_after, is_percent)
        return max(0.0, before - after)

    def _apply_steal(self, attacker_id: str, defender_id: str) -> str:
        """按乘算口径、每日保护额度和微量增发规则结算传承转移。"""
        defender_pool = self.reincarnation_repo.get_reincarnation_pool(defender_id)
        if not defender_pool:
            return "❌ 对方没有任何传承可以偷取"

        available_keys = self._get_stealable_keys(
            defender_id,
            defender_pool.reincarnation_pool,
            defender_pool.current_life_pool
        )
        if not available_keys:
            return "🛡️ 对方今日各项传承均已达到30%抽取上限。"

        total_weight = sum(self.PROP_CONFIG[key]["weight"] for key in available_keys)
        roll = random.randint(1, total_weight)
        cumulative = 0
        selected_key = available_keys[0]
        for key in available_keys:
            cumulative += self.PROP_CONFIG[key]["weight"]
            if roll <= cumulative:
                selected_key = key
                break

        config = self.PROP_CONFIG[selected_key]
        is_percent = config["is_percent"]
        attacker_pool = self.reincarnation_repo.get_reincarnation_pool(attacker_id)
        if not attacker_pool:
            attacker_pool = self.reincarnation_repo.create_reincarnation_pool(attacker_id)

        attacker_permanent = attacker_pool.reincarnation_pool.get(selected_key, 0.0)
        attacker_life = attacker_pool.current_life_pool.get(selected_key, 0.0)
        attacker_current = self._combine_pool_value(
            attacker_permanent,
            attacker_life,
            is_percent
        )
        base_steal = random.uniform(*config["steal_range"])
        intended_loss = self._get_effective_steal(attacker_current, base_steal)

        defender_permanent = defender_pool.reincarnation_pool.get(selected_key, 0.0)
        defender_life = defender_pool.current_life_pool.get(selected_key, 0.0)
        daily_remaining, _, daily_limit = self._get_daily_loss_status(
            defender_id,
            selected_key,
            defender_permanent,
            defender_life,
            is_percent
        )
        actual_loss = self._deduct_display_loss(
            defender_pool,
            selected_key,
            min(intended_loss, daily_remaining),
            is_percent
        )
        if actual_loss <= 1e-12:
            return "🛡️ 对方该项传承今日已达到30%抽取上限。"

        # 胜者获得量为败者实际损失的105%-115%，维持战斗激励并微量增发。
        transfer_efficiency = random.uniform(1.05, 1.15)
        actual_gain = actual_loss * transfer_efficiency
        if is_percent:
            # 换算为攻击者本世因子，使乘算后的实际增益恰好等于actual_gain。
            life_increment = actual_gain / (1.0 + max(0.0, attacker_permanent))
        else:
            life_increment = actual_gain
        attacker_pool.add_to_life_pool(selected_key, life_increment)

        self.reincarnation_repo.save(defender_pool)
        self.reincarnation_repo.save(attacker_pool)
        daily_total_loss = self.impart_repo.add_daily_theft_loss(
            defender_id,
            self._date_key(),
            selected_key,
            actual_loss
        )

        attacker_total_after = self._combine_pool_value(
            attacker_pool.reincarnation_pool.get(selected_key, 0.0),
            attacker_pool.current_life_pool.get(selected_key, 0.0),
            is_percent
        )
        world_gift = max(0.0, actual_gain - actual_loss)
        unit = "%" if is_percent else ""
        scale = 100.0 if is_percent else 1.0
        quota_usage = min(100.0, daily_total_loss / daily_limit * 100.0) if daily_limit > 0 else 100.0

        return (
            f"🎉 传承挑战胜利！\n"
            f"━━━━━━━━━━━━━━━\n"
            f"夺得【{config['label']}】：+{actual_gain * scale:.2f}{unit}\n"
            f"对手实际损失：-{actual_loss * scale:.2f}{unit}\n"
            f"天地馈赠：+{world_gift * scale:.2f}{unit}\n"
            f"当前【{config['label']}】总加成：{attacker_total_after * scale:.2f}{unit}\n"
            f"对手今日该属性抽取额度：{quota_usage:.1f}%/100%"
        )
    
    def get_ranking(self, limit: int = 10) -> Tuple[bool, str]:
        """获取传承排行榜"""
        rankings = self.reincarnation_repo.get_ranking(limit)
        
        if not rankings:
            return False, "📊 传承排行榜暂无数据。"
        
        lines = ["🏆 传承排行榜\n━━━━━━━━━━━━━━━"]
        for i, (user_id, total_percent, count) in enumerate(rankings, 1):
            player = self.player_repo.get_player(user_id)
            name = player.nickname if player and player.nickname else user_id[:8]
            lines.append(f"{i}. {name} - 总加成+{total_percent:.1%} (转世{count}次)")
        lines.append("━━━━━━━━━━━━━━━")
        lines.append("💡 使用【传承挑战 @目标】夺取传承")
        
        return True, "\n".join(lines)
