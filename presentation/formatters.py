"""输出格式化工具"""
from typing import Dict, Any

from ..domain.models.player import Player
from ..domain.enums import CultivationType
from ..domain.value_objects import SpiritRootInfo


class PlayerFormatter:
    """玩家信息格式化器"""
    
    @staticmethod
    def format_create_success(
        player: Player,
        spirit_root_info: SpiritRootInfo,
        sender_name: str
    ) -> str:
        """
        格式化创建角色成功消息
        
        Args:
            player: 玩家对象
            spirit_root_info: 灵根信息
            sender_name: 发送者名称
            
        Returns:
            格式化的消息
        """
        return (
            f"🎉 恭喜道友 {sender_name} 踏上仙途！\n"
            f"━━━━━━━━━━━━━━━\n"
            f"修炼方式：【{player.cultivation_type.value}】\n"
            f"灵根：【{player.spiritual_root}】\n"
            f"评价：{spirit_root_info.description}\n"
            f"启动资金：{player.gold} 灵石\n"
            f"━━━━━━━━━━━━━━━\n"
            f"⚠️ 修仙有风险，突破需谨慎！\n"
            f"突破失败或生命值归零会导致\n"
            f"身死道消，所有数据清除！\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💡 发送「我的信息」查看状态"
        )
    
    @staticmethod
    def format_create_help() -> str:
        """格式化创建角色帮助消息"""
        return (
            "🌟 欢迎踏入修仙之路！\n"
            "━━━━━━━━━━━━━━━\n"
            "请选择你的修炼方式：\n\n"
            "【灵修】以灵气为主，法术攻击\n"
            "• 寿命：100\n"
            "• 灵气：100-1000\n"
            "• 法伤：5-100\n"
            "• 物伤：5\n"
            "• 法防：0\n"
            "• 物防：5\n"
            "• 精神力：100-500\n\n"
            "【体修】以气血为主，肉身强横\n"
            "• 寿命：50-100\n"
            "• 气血：100-500\n"
            "• 法伤：0\n"
            "• 物伤：100-500\n"
            "• 法防：50-200\n"
            "• 物防：100-500\n"
            "• 精神力：100-500\n"
            "━━━━━━━━━━━━━━━\n"
            "⚠️ 修仙风险警告 ⚠️\n"
            "• 突破失败有概率走火入魔身死道消\n"
            "• 生命值归零也会导致死亡\n"
            "• 死亡后所有数据清除，需重新入仙途\n"
            "━━━━━━━━━━━━━━━\n"
            f"💡 使用方法：\n"
            f"  我要修仙 灵修\n"
            f"  我要修仙 体修"
        )
    
    @staticmethod
    def format_player_info(
        player: Player,
        level_name: str,
        required_exp: int,
        combat_power: int,
        sect_name: str = "无宗门",
        position_name: str = "散修",
        equipment_bonuses = None,
        inheritance_info: dict = None
    ) -> str:
        """
        格式化玩家信息
        
        Args:
            player: 玩家对象
            level_name: 境界名称
            required_exp: 突破所需修为
            combat_power: 战力
            sect_name: 宗门名称
            position_name: 职位名称
            equipment_bonuses: 装备属性加成
            
        Returns:
            格式化的消息
        """
        dao_hao = player.user_name if player.user_name else player.nickname
        
        # 突破加成
        breakthrough_rate = f"+{player.level_up_rate}%" if player.level_up_rate > 0 else "0%"
        
        # 装备信息
        weapon_name = player.weapon if player.weapon else "无"
        armor_name = player.armor if player.armor else "无"
        technique_name = player.main_technique if player.main_technique else "无"
        cultivation_technique_name = (
            player.cultivation_technique
            if player.cultivation_technique else "无"
        )
        exp_bonus_percent = (
            equipment_bonuses.exp_multiplier * 100
            if equipment_bonuses else 0
        )
        
        # 计算总属性（基础属性 + 装备加成）
        pill_totals = {}
        for pill_effect in (getattr(player, "active_pill_effects", {}) or {}).values():
            if isinstance(pill_effect, dict):
                for key, value in pill_effect.items():
                    pill_totals[key] = pill_totals.get(key, 0) + int(value or 0)
        pill_attack = pill_totals.get("add_attack", 0)
        pill_defense = pill_totals.get("add_defense", 0)
        pill_mental = pill_totals.get("add_mental_power", 0)
        is_spiritual = player.cultivation_type == CultivationType.SPIRITUAL
        pill_magic_attack = pill_attack if is_spiritual else 0
        pill_physical_attack = pill_attack if not is_spiritual else 0
        pill_magic_defense = pill_defense if is_spiritual else 0
        pill_physical_defense = pill_defense if not is_spiritual else 0

        def detail(total, base, equipment, pill):
            return f"{total:,}（基础{base:,}+装备{equipment:,}+丹药{pill:,}）"

        if equipment_bonuses:
            total_magic_damage = player.magic_damage + equipment_bonuses.magic_damage
            total_physical_damage = player.physical_damage + equipment_bonuses.physical_damage
            total_magic_defense = player.magic_defense + equipment_bonuses.magic_defense
            total_physical_defense = player.physical_defense + equipment_bonuses.physical_defense
            total_mental_power = player.mental_power + equipment_bonuses.mental_power
        else:
            total_magic_damage = player.magic_damage
            total_physical_damage = player.physical_damage
            total_magic_defense = player.magic_defense
            total_physical_defense = player.physical_defense
            total_mental_power = player.mental_power

        speed = player.calculate_speed(
            getattr(equipment_bonuses, "speed", 0) if equipment_bonuses else 0
        )

        permanent = (inheritance_info or {}).get("permanent", {})
        crit_rate = min(100.0, max(0.0, float(permanent.get("crit_rate_percent", 0.0)) * 100.0))
        crit_damage_bonus = max(0.0, float(permanent.get("crit_damage_percent", 0.0)))
        crit_damage = 150.0 + crit_damage_bonus * 100.0
        penetration = min(30.0, crit_rate * 0.15 + (crit_damage - 150.0) * 0.10) if is_spiritual else 0.0
        boss_weight = (1.0 if is_spiritual else 2.0) + (
            float(getattr(equipment_bonuses, "target_weight", 0.0) or 0.0)
            if equipment_bonuses else 0.0
        )
        total_max_resource = (
            (player.max_spiritual_qi if is_spiritual else player.max_blood_qi)
            + (getattr(equipment_bonuses, "max_hp", 0) if equipment_bonuses else 0)
        )
        total_current_resource = min(
            total_max_resource,
            (player.spiritual_qi if is_spiritual else player.blood_qi)
            + (getattr(equipment_bonuses, "max_hp", 0) if equipment_bonuses else 0),
        )
        root_multiplier = float(getattr(equipment_bonuses, "root_multiplier", 1.0) or 1.0)
        technique_land_bonus = float(getattr(equipment_bonuses, "technique_land_bonus", 0.0) or 0.0)
        eq = lambda name: int(getattr(equipment_bonuses, name, 0) or 0) if equipment_bonuses else 0
        eq_float = lambda name: float(getattr(equipment_bonuses, name, 0.0) or 0.0) if equipment_bonuses else 0.0
        attack_label = "法伤" if is_spiritual else "物伤"
        attack_value = total_magic_damage if is_spiritual else total_physical_damage
        attack_equipment = eq("magic_damage") if is_spiritual else eq("physical_damage")
        attack_pill = pill_magic_attack if is_spiritual else pill_physical_attack
        defense_label = "法防" if is_spiritual else "物防"
        defense_value = total_magic_defense if is_spiritual else total_physical_defense
        defense_equipment = eq("magic_defense") if is_spiritual else eq("physical_defense")
        defense_pill = pill_magic_defense if is_spiritual else pill_physical_defense
        hp_pill = pill_totals.get("add_max_hp", 0) + pill_totals.get("add_spiritual_power", 0)
        hp_percent = float(permanent.get("hp_percent", 0.0) or 0.0)
        hp_flat = int(permanent.get("hp_flat", 0) or 0)
        attack_percent = float(permanent.get("attack_percent", 0.0) or 0.0)
        attack_flat = int(permanent.get("attack_flat", 0) or 0)
        defense_percent = float(permanent.get("defense_percent", 0.0) or 0.0)
        defense_flat = int(permanent.get("defense_flat", 0) or 0)
        mp_percent = float(permanent.get("mp_percent", 0.0) or 0.0)
        mp_flat = int(permanent.get("mp_flat", 0) or 0)
        base_resource = max(0, int(((player.max_spiritual_qi if is_spiritual else player.max_blood_qi) - hp_pill - hp_flat) / max(1.0, 1.0 + hp_percent)))
        base_mp = max(0, int((player.mental_power - pill_mental - mp_flat) / max(1.0, 1.0 + mp_percent)))
        base_attack = max(0, int((attack_value - attack_equipment - attack_pill - attack_flat) / max(1.0, 1.0 + attack_percent)))
        base_defense = max(0, int((defense_value - defense_equipment - defense_pill - defense_flat) / max(1.0, 1.0 + defense_percent)))
        base_magic_attack = max(0, int((player.magic_damage - pill_magic_attack - attack_flat) / max(1.0, 1.0 + attack_percent)))
        base_physical_attack = max(0, int((player.physical_damage - pill_physical_attack - attack_flat) / max(1.0, 1.0 + attack_percent)))
        base_magic_defense = max(0, int((player.magic_defense - pill_magic_defense - defense_flat) / max(1.0, 1.0 + defense_percent)))
        base_physical_defense = max(0, int((player.physical_defense - pill_physical_defense - defense_flat) / max(1.0, 1.0 + defense_percent)))
        experience_multiplier = root_multiplier * (1.0 + technique_land_bonus)
        exp_display_percent = (experience_multiplier - 1.0) * 100.0
        
        exp_display = (
            "已达最高境界"
            if int(required_exp or 0) <= 0
            else f"{int(player.experience):,}/{int(required_exp):,}"
        )

        msg = (
            f"📋 道友 {dao_hao} 的信息\n"
            f"━━━━━━━━━━━━━━━\n"
            f"\n"
            f"【基本信息】\n"
            f"  道号：{dao_hao}\n"
            f"  境界：{level_name}\n"
            f"  修为：{exp_display}\n"
            f"  灵石：{player.gold:,}\n"
            f"  战力：{combat_power:,}\n"
            f"  灵根：{player.spiritual_root}\n"
            f"  突破加成：{breakthrough_rate}\n"
            f"  储物戒：{player.storage_ring}（{sum(player.storage_ring_items.values())} 件）\n"
            f"\n"
            f"【修炼属性】\n"
            f"  修炼方式：{player.cultivation_type.value}\n"
            f"  状态：{player.state.value}\n"
            f"  寿命：{player.lifespan}\n"
            f"  精神力：{total_mental_power}\n"
            f"  速度：{speed:,.0f}\n"
            f"  炼丹等级：{player.alchemy_level}（经验 {player.alchemy_exp:,}）"
        )
        
        # 显示装备加成
        if equipment_bonuses and equipment_bonuses.mental_power > 0:
            msg += f"（基础{player.mental_power - pill_mental:,}+装备{equipment_bonuses.mental_power:,}+丹药{pill_mental:,}）"
        msg += "\n"
        
        # 根据修炼类型添加不同属性
        if player.cultivation_type == CultivationType.SPIRITUAL:
            msg += f"  灵气：{player.spiritual_qi}/{player.max_spiritual_qi}\n"
            msg += f"  法伤：{total_magic_damage}"
            if equipment_bonuses and equipment_bonuses.magic_damage > 0:
                msg += f"({player.magic_damage}+{equipment_bonuses.magic_damage})"
            msg += f"\n  物伤：{total_physical_damage}"
            if equipment_bonuses and equipment_bonuses.physical_damage > 0:
                msg += f"({player.physical_damage}+{equipment_bonuses.physical_damage})"
            msg += f"\n  法防：{total_magic_defense}"
            if equipment_bonuses and equipment_bonuses.magic_defense > 0:
                msg += f"({player.magic_defense}+{equipment_bonuses.magic_defense})"
            msg += f"\n  物防：{total_physical_defense}"
            if equipment_bonuses and equipment_bonuses.physical_defense > 0:
                msg += f"({player.physical_defense}+{equipment_bonuses.physical_defense})"
            msg += "\n"
        else:  # 体修
            msg += f"  气血：{player.blood_qi}/{player.max_blood_qi}\n"
            msg += f"  物伤：{total_physical_damage}"
            if equipment_bonuses and equipment_bonuses.physical_damage > 0:
                msg += f"({player.physical_damage}+{equipment_bonuses.physical_damage})"
            msg += f"\n  法伤：{total_magic_damage}"
            if equipment_bonuses and equipment_bonuses.magic_damage > 0:
                msg += f"({player.magic_damage}+{equipment_bonuses.magic_damage})"
            msg += f"\n  物防：{total_physical_defense}"
            if equipment_bonuses and equipment_bonuses.physical_defense > 0:
                msg += f"({player.physical_defense}+{equipment_bonuses.physical_defense})"
            msg += f"\n  法防：{total_magic_defense}"
            if equipment_bonuses and equipment_bonuses.magic_defense > 0:
                msg += f"({player.magic_defense}+{equipment_bonuses.magic_defense})"
            msg += "\n"
        
        msg += (
            "\n【最终战斗属性】\n"
            f"  {'灵气' if is_spiritual else '气血'}：{total_current_resource:,}/{total_max_resource:,}\n"
            f"  {'灵气' if is_spiritual else '气血'}构成：{base_resource:,}×(1+永久传承{hp_percent:.1%})+固定{hp_flat:,}+装备{eq('max_hp'):,}+丹药{hp_pill:,}={total_max_resource:,}\n"
            f"  最终法伤：{total_magic_damage:,}\n"
            f"  最终物伤：{total_physical_damage:,}\n"
            f"  最终法防：{total_magic_defense:,}\n"
            f"  最终物防：{total_physical_defense:,}\n"
            f"  战斗MP（精神力）：{total_mental_power:,}\n"
            f"  精神力构成：{base_mp:,}×(1+永久传承{mp_percent:.1%})+固定{mp_flat:,}+装备{eq('mental_power'):,}+丹药{pill_mental:,}={total_mental_power:,}\n"
            f"  法伤构成：{base_magic_attack:,}×(1+永久传承{attack_percent:.1%})+固定{attack_flat:,}+装备{eq('magic_damage'):,}+丹药{pill_magic_attack:,}={total_magic_damage:,}\n"
            f"  物伤构成：{base_physical_attack:,}×(1+永久传承{attack_percent:.1%})+固定{attack_flat:,}+装备{eq('physical_damage'):,}+丹药{pill_physical_attack:,}={total_physical_damage:,}\n"
            f"  法防构成：{base_magic_defense:,}×(1+永久传承{defense_percent:.1%})+固定{defense_flat:,}+装备{eq('magic_defense'):,}+丹药{pill_magic_defense:,}={total_magic_defense:,}\n"
            f"  物防构成：{base_physical_defense:,}×(1+永久传承{defense_percent:.1%})+固定{defense_flat:,}+装备{eq('physical_defense'):,}+丹药{pill_physical_defense:,}={total_physical_defense:,}\n"
            f"  速度：{speed:,.0f}\n"
            f"  暴击率：{crit_rate:.1f}%\n"
            f"  暴击伤害：{crit_damage:.1f}%\n"
            f"  双属性穿透：{penetration:.2f}%\n"
            f"  Boss吸引权重：{boss_weight:.2f}\n"
            f"  修为获取倍率：灵根{root_multiplier:.2f} × 心得/功法与洞天{1.0 + technique_land_bonus:.4f} = {experience_multiplier:.4f}（+{exp_display_percent:.1f}%）\n"
            f"\n"
            f"【装备信息】\n"
            f"  主修功法：{technique_name}\n"
            f"  修炼心得：{cultivation_technique_name}\n"
            f"  修为倍率构成：灵根×心得/功法×洞天（当前显示为全局预览）\n"
            f"  装备属性合计：法伤+{eq('magic_damage')}、物伤+{eq('physical_damage')}、法防+{eq('magic_defense')}、物防+{eq('physical_defense')}、精神力+{eq('mental_power')}、气血上限+{eq('max_hp')}、速度+{eq('speed')}、Boss吸引权重{eq_float('target_weight'):+.2f}\n"
            f"  法器：{weapon_name}\n"
            f"  防具：{armor_name}\n"
            f"\n"
            f"【宗门信息】\n"
            f"  所在宗门：{sect_name}\n"
            f"  宗门职位：{position_name}\n"
            f"  宗门贡献：{player.sect_contribution:,}\n"
            f"━━━━━━━━━━━━━━━"
        )

        inheritance_info = inheritance_info or {}

        def format_inheritance(values: dict) -> str:
            labels = {
                "hp_percent": "生命百分比",
                "attack_percent": "攻击百分比",
                "defense_percent": "防御百分比",
                "crit_rate_percent": "暴击率",
                "crit_damage_percent": "暴击伤害",
                "hp_flat": "生命固定值",
                "attack_flat": "攻击固定值",
                "mp_flat": "灵气/气血固定值",
                "defense_flat": "防御固定值",
            }
            formatted = []
            for key, value in values.items():
                label = labels.get(key, key)
                if key.endswith("_percent"):
                    formatted.append(f"{label}+{float(value):.1%}")
                else:
                    formatted.append(f"{label}+{float(value):,.2f}")
            return "\n    ".join(formatted) or "无"

        msg += (
            "\n\n【传承信息】\n"
            f"  转世次数：{inheritance_info.get('count', 0)}\n"
            "  永久传承（已结算）：\n"
            f"    {format_inheritance(inheritance_info.get('permanent', {}))}\n"
            "  本世传承（待轮回结算）：\n"
            f"    {format_inheritance(inheritance_info.get('current', {}))}\n"
            f"  当前境界预计轮回奖励：{inheritance_info.get('reward_tier', '无')}\n"
            f"    {format_inheritance(inheritance_info.get('reward', {}))}\n"
            f"  悬赏战功：{inheritance_info.get('bounty_merit', 0)}点"
        )
        
        if getattr(player, "active_pill_effects", None):
            msg += "\n\n【当前丹药增益】\n"
            for pill_name, effects in player.active_pill_effects.items():
                details = []
                for key, value in effects.items():
                    label = {
                        "add_attack": "攻击",
                        "add_defense": "防御",
                        "add_max_hp": "气血/灵气上限",
                        "add_spiritual_power": "气血/灵气上限",
                        "add_mental_power": "精神力",
                        "add_breakthrough_bonus": "突破成功率",
                    }.get(key, key)
                    amount = float(value) * 100 if key == "add_breakthrough_bonus" else value
                    suffix = "%" if key == "add_breakthrough_bonus" else ""
                    details.append(f"{label}+{amount:g}{suffix}")
                msg += f"  {pill_name}：" + "、".join(details) + "（战斗后清除）\n"
        return msg
    
    @staticmethod
    def format_check_in_success(reward_gold: int, total_gold: int) -> str:
        """
        格式化签到成功消息
        
        Args:
            reward_gold: 获得的灵石
            total_gold: 当前总灵石
            
        Returns:
            格式化的消息
        """
        return (
            "✅ 签到成功！\n"
            "━━━━━━━━━━━━━━━\n"
            f"💰 获得灵石：{reward_gold}\n"
            f"💎 当前灵石：{total_gold}\n"
            "━━━━━━━━━━━━━━━\n"
            "明日再来，莫要忘记哦~"
        )
    
    @staticmethod
    def format_nickname_changed(new_nickname: str) -> str:
        """
        格式化改道号成功消息
        
        Args:
            new_nickname: 新道号
            
        Returns:
            格式化的消息
        """
        return (
            "✅ 道号修改成功！\n"
            "━━━━━━━━━━━━━━━\n"
            f"新道号：{new_nickname}\n"
            "━━━━━━━━━━━━━━━\n"
            "从此江湖上多了一个响亮的名号！"
        )


class SpiritFieldFormatter:
    """灵田系统格式化器"""
    
    @staticmethod
    def format_field_status(
        capacity: int,
        used_count: int,
        plots: list,
        current_time: int
    ) -> str:
        """
        格式化灵田状态显示
        
        Args:
            capacity: 田地总容量
            used_count: 已使用田地数量
            plots: 田地列表
            current_time: 当前时间戳
            
        Returns:
            格式化的灵田状态消息
        """
        msg = (
            "🌾 灵田状态\n"
            "━━━━━━━━━━━━━━━\n"
            f"田地容量：{used_count}/{capacity}\n"
            "━━━━━━━━━━━━━━━\n"
        )
        
        for plot in plots:
            plot_num = plot.plot_id
            if plot.is_empty():
                msg += f"田地 {plot_num}：空闲 🟢\n"
            else:
                herb = plot.planted_herb
                status = herb.format_remaining_time(current_time)
                status_icon = "✅" if herb.is_mature(current_time) else "⏳"
                msg += (
                    f"田地 {plot_num}：{herb.herb_name}【{herb.herb_rank}】\n"
                    f"  状态：{status} {status_icon}\n"
                )
        
        msg += "━━━━━━━━━━━━━━━"
        return msg
    
    @staticmethod
    def format_seed_list(seeds: list, page: int = 1, page_size: int = 10) -> str:
        """
        格式化种子商店列表(含解锁标记)
        
        Args:
            seeds: 种子列表(HerbSeed对象)
            page: 当前页码
            page_size: 每页显示数量
            
        Returns:
            格式化的种子列表消息
        """
        total_seeds = len(seeds)
        total_pages = (total_seeds + page_size - 1) // page_size
        
        # 分页
        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, total_seeds)
        page_seeds = seeds[start_idx:end_idx]
        
        msg = (
            "🌱 种子商店\n"
            "━━━━━━━━━━━━━━━\n"
            f"第 {page}/{total_pages} 页\n"
            "━━━━━━━━━━━━━━━\n"
        )
        
        for seed in page_seeds:
            unlock_status = ""
            if seed.is_unlocked:
                unlock_status = " 🔓已解锁"
            else:
                progress = seed.get_unlock_progress()
                unlock_status = f" 📊{progress}"
            
            msg += (
                f"\n【{seed.herb_name}】{unlock_status}\n"
                f"  品级：{seed.herb_rank}\n"
                f"  价格：{seed.seed_price:,} 灵石\n"
                f"  成熟时间：{seed.get_grow_time_display()}\n"
            )
        
        msg += "\n━━━━━━━━━━━━━━━"
        return msg
    
    @staticmethod
    def format_plant_result(
        herb_name: str,
        herb_rank: str,
        plot_id: int,
        mature_time_display: str,
        is_unlocked: bool = False
    ) -> str:
        """
        格式化种植结果
        
        Args:
            herb_name: 药草名称
            herb_rank: 药草品级
            plot_id: 田地编号
            mature_time_display: 成熟时间显示
            is_unlocked: 是否使用了已解锁种子
            
        Returns:
            格式化的种植结果消息
        """
        unlock_msg = ""
        if is_unlocked:
            unlock_msg = f"✨ {herb_name}种子已解锁，自动给予种子进行种植\n"
        
        return (
            f"{unlock_msg}"
            f"✅ 种植成功！\n"
            "━━━━━━━━━━━━━━━\n"
            f"药草：{herb_name}【{herb_rank}】\n"
            f"田地：{plot_id}\n"
            f"成熟时间：{mature_time_display}\n"
            "━━━━━━━━━━━━━━━\n"
            "耐心等待，药草即将成熟~"
        )
    
    @staticmethod
    def format_harvest_result(
        harvested_herbs: list,
        total_count: int
    ) -> str:
        """
        格式化收获结果
        
        Args:
            harvested_herbs: 收获的药草列表 [(herb_name, herb_rank, amount), ...]
            total_count: 总收获数量
            
        Returns:
            格式化的收获结果消息
        """
        if not harvested_herbs:
            return (
                "❌ 没有可收获的药草\n"
                "━━━━━━━━━━━━━━━\n"
                "所有田地都还在生长中~"
            )
        
        msg = (
            "🎉 收获成功！\n"
            "━━━━━━━━━━━━━━━\n"
        )
        
        for herb_name, herb_rank, amount in harvested_herbs:
            msg += f"• {herb_name}【{herb_rank}】 x{amount}\n"
        
        msg += (
            "━━━━━━━━━━━━━━━\n"
            f"共收获 {total_count} 个药草材料\n"
            "已添加到储物袋中~"
        )
        
        return msg
    
    @staticmethod
    def format_upgrade_result(
        old_capacity: int,
        new_capacity: int,
        cost: int,
        remaining_gold: int
    ) -> str:
        """
        格式化灵田升级结果
        
        Args:
            old_capacity: 原容量
            new_capacity: 新容量
            cost: 升级费用
            remaining_gold: 剩余灵石
            
        Returns:
            格式化的升级结果消息
        """
        return (
            "✅ 灵田升级成功！\n"
            "━━━━━━━━━━━━━━━\n"
            f"田地容量：{old_capacity} → {new_capacity}\n"
            f"消耗灵石：{cost:,}\n"
            f"剩余灵石：{remaining_gold:,}\n"
            "━━━━━━━━━━━━━━━\n"
            "可以种植更多药草了~"
        )
    
    @staticmethod
    def format_seed_unlock_notification(
        seed_name: str,
        purchase_count: int
    ) -> str:
        """
        格式化种子解锁通知
        
        Args:
            seed_name: 种子名称
            purchase_count: 购买次数
            
        Returns:
            格式化的解锁通知消息
        """
        if purchase_count >= 5:
            return (
                f"🎉 恭喜！{seed_name}种子已永久解锁！\n"
                "以后种植时不再需要购买种子！"
            )
        else:
            return f"📊 {seed_name}解锁进度：{purchase_count}/5次购买"
    
    @staticmethod
    def format_buy_seed_result(
        seed_name: str,
        quantity: int,
        total_cost: int,
        remaining_gold: int,
        unlock_notification: str = ""
    ) -> str:
        """
        格式化购买种子结果
        
        Args:
            seed_name: 种子名称
            quantity: 购买数量
            total_cost: 总费用
            remaining_gold: 剩余灵石
            unlock_notification: 解锁通知消息
            
        Returns:
            格式化的购买结果消息
        """
        msg = (
            "✅ 购买成功！\n"
            "━━━━━━━━━━━━━━━\n"
            f"种子：{seed_name}\n"
            f"数量：{quantity}\n"
            f"消耗灵石：{total_cost:,}\n"
            f"剩余灵石：{remaining_gold:,}\n"
        )
        
        if unlock_notification:
            msg += "━━━━━━━━━━━━━━━\n"
            msg += unlock_notification + "\n"
        
        msg += "━━━━━━━━━━━━━━━"
        return msg
