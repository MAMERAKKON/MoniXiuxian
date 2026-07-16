"""传承系统服务"""
import random
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
    
    def get_impart_info(self, user_id: str) -> Tuple[bool, str]:
        """获取传承信息"""
        permanent_pool = self.reincarnation_repo.get_permanent_pool(user_id)
        life_pool = self.reincarnation_repo.get_life_pool(user_id)
        reincarnation_count = self.reincarnation_repo.get_reincarnation_count(user_id)
        
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
        lines.append("💡 使用【传承挑战 @目标】挑战他人夺取传承")
        lines.append("💡 传承越高，偷取效率越低（衰减机制）")
        lines.append("💡 轮回转世时本世池自动合并到永久池")
        
        return True, "\n".join(lines)
    
    async def challenge_impart(self, attacker_id: str, defender_id: str) -> Tuple[bool, str]:
        """发起传承挑战"""
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
        
        # 检查防守者是否有传承
        defender_permanent = self.reincarnation_repo.get_permanent_pool(defender_id)
        defender_life = self.reincarnation_repo.get_life_pool(defender_id)
        if not any(v > 0 for v in defender_permanent.values()) and not any(v > 0 for v in defender_life.values()):
            return False, "❌ 对方没有任何传承可以偷取"
        
        attacker_stats = await self.combat_service.prepare_combat_stats(attacker_id)
        defender_stats = await self.combat_service.prepare_combat_stats(defender_id)
        if not attacker_stats or not defender_stats:
            return False, "❌ 战斗属性生成失败，请稍后重试"

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
    
    def _apply_steal(self, attacker_id: str, defender_id: str) -> str:
        """应用偷取逻辑（无上限 + 衰减）"""
        # 获取防守者的传承
        defender_life = self.reincarnation_repo.get_life_pool(defender_id)
        defender_permanent = self.reincarnation_repo.get_permanent_pool(defender_id)
        
        # 找出对方有值的属性
        available_keys = []
        for key, config in self.PROP_CONFIG.items():
            total = defender_life.get(key, 0.0) + defender_permanent.get(key, 0.0)
            if total > 0.001:
                available_keys.append(key)
        
        if not available_keys:
            return "❌ 对方没有任何传承可以偷取"
        
        # 从可用属性中加权随机选择
        total_weight = sum(self.PROP_CONFIG[key]['weight'] for key in available_keys)
        roll = random.randint(1, total_weight)
        cumulative = 0
        selected_key = available_keys[0]
        for key in available_keys:
            cumulative += self.PROP_CONFIG[key]['weight']
            if roll <= cumulative:
                selected_key = key
                break
        
        config = self.PROP_CONFIG[selected_key]
        
        # 计算攻击者该属性的当前值（永久池 + 本世池）
        attacker_pool = self.reincarnation_repo.get_reincarnation_pool(attacker_id)
        if not attacker_pool:
            attacker_pool = self.reincarnation_repo.create_reincarnation_pool(attacker_id)
        attacker_current = (
            attacker_pool.reincarnation_pool.get(selected_key, 0.0) +
            attacker_pool.current_life_pool.get(selected_key, 0.0)
        )
        
        # 计算基础偷取量
        base_steal = random.uniform(*config['steal_range'])
        
        # ⭐ 应用衰减：传承越高，偷取效率越低
        effective_steal = self._get_effective_steal(attacker_current, base_steal)
        
        # 获取防守者该属性的具体值
        life_value = defender_life.get(selected_key, 0.0)
        permanent_value = defender_permanent.get(selected_key, 0.0)
        available_to_steal = life_value + permanent_value
        
        # 计算失败者损失（胜利者获得的 70%-90%）
        loss_ratio = random.uniform(0.3, 0.5)
        defender_loss_amount = effective_steal * loss_ratio
        # 不能超过对方拥有量
        defender_loss_amount = min(defender_loss_amount, available_to_steal)
        
        # 从本世池扣除
        life_to_remove = min(defender_loss_amount, life_value)
        if life_to_remove > 0:
            defender_pool = self.reincarnation_repo.get_reincarnation_pool(defender_id)
            if defender_pool:
                defender_pool.current_life_pool[selected_key] = life_value - life_to_remove
                self.reincarnation_repo.save(defender_pool)
        
        # 如果还不够，从永久池扣除
        permanent_to_remove = defender_loss_amount - life_to_remove
        if permanent_to_remove > 0 and permanent_value > 0:
            defender_pool = self.reincarnation_repo.get_reincarnation_pool(defender_id)
            if defender_pool:
                current_permanent = defender_pool.reincarnation_pool.get(selected_key, 0.0)
                defender_pool.reincarnation_pool[selected_key] = max(0, current_permanent - permanent_to_remove)
                self.reincarnation_repo.save(defender_pool)
        
        # 攻击者获得（存入本世池）
        actual_steal = min(effective_steal, available_to_steal)
        attacker_pool.add_to_life_pool(selected_key, actual_steal)
        self.reincarnation_repo.save(attacker_pool)
        
        # 计算显示值
        defender_loss = life_to_remove + permanent_to_remove
        dissipated = effective_steal - defender_loss
        
        # 获取攻击者当前总加成
        attacker_pool_after = self.reincarnation_repo.get_reincarnation_pool(attacker_id)
        life_after = attacker_pool_after.current_life_pool.get(selected_key, 0.0)
        permanent_after = attacker_pool_after.reincarnation_pool.get(selected_key, 0.0)
        total_after = life_after + permanent_after
        
        unit = "%" if config['is_percent'] else ""
        display_gain = actual_steal * 100 if config['is_percent'] else defender_loss_amount
        display_total = total_after * 100 if config['is_percent'] else total_after
        display_loss = defender_loss * 100 if config['is_percent'] else defender_loss
        display_attacker_current = attacker_current * 100 if config['is_percent'] else attacker_current
        
        return (
            f"🎉 传承挑战胜利！\n"
            f"━━━━━━━━━━━━━━━\n"
            f"偷取【{config['label']}】：+{display_gain:.1f}{unit}\n"
            f"（当前传承值 {display_attacker_current:.1f}{unit}，衰减后实际获得）\n"
            f"对手损失：-{display_loss:.1f}{unit}\n"
            f"当前【{config['label']}】总加成：{display_total:.1f}{unit}\n"
            f"（其中 {dissipated:.2f}{unit if config['is_percent'] else ''} 消散于天地间）"
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
