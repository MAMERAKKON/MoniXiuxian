"""Boss命令处理器"""
import time
from typing import AsyncGenerator
from astrbot.api.event import AstrMessageEvent

from ...application.services.boss_service import BossService
from ...core.exceptions import GameException
from ...core.config import ConfigManager
from ..decorators import require_admin


class BossHandler:
    """Boss命令处理器"""
    
    def __init__(self, boss_service: BossService, config_manager: ConfigManager):
        self.boss_service = boss_service
        self.config_manager = config_manager

    @staticmethod
    def _format_remaining(target_time: int) -> str:
        remaining = max(0, int(target_time) - int(time.time()))
        hours, remainder = divmod(remaining, 3600)
        minutes = remainder // 60
        if hours:
            return f"约{hours}小时{minutes}分钟"
        return f"约{max(1, minutes)}分钟"

    @staticmethod
    def _damage_type_name(damage_type: str) -> str:
        return "魔法" if damage_type == "magic" else "物理"

    @staticmethod
    def _template_values(realm: dict, template: dict) -> dict:
        """计算固定境界套用Boss模板后的公开数值。"""
        return {
            "hp": max(300, int(round(realm["hp"] * template["hp_mult"]))),
            "atk": max(5, int(round(realm["atk"] * template["atk_mult"]))),
            "defense": max(0, min(35, int(realm["defense"] + template["defense_add"]))),
            "exp": max(1000, int(round(realm["exp"] * template["reward_mult"]))),
            "stone": max(500, int(round(realm["stone"] * template["reward_mult"]))),
        }

    def _format_codex_overview(self) -> str:
        total_weight = sum(template["weight"] for template in self.boss_service.BOSS_TEMPLATES)
        lines = [
            "📕 世界Boss图鉴",
            "━━━━━━━━━━━━━━━",
            "自然降临境界：炼气 / 筑基 / 金丹 / 元婴",
            "标准规模：约3名同境界玩家",
            "",
        ]
        for template in self.boss_service.BOSS_TEMPLATES:
            chance = template["weight"] / total_weight * 100 if total_weight else 0
            lines.append(
                f"· {template['name']}｜{self._damage_type_name(template['damage_type'])}"
                f"｜出现约{chance:g}%｜奖励×{template['reward_mult']:.2g}"
            )
        lines.extend([
            "",
            "查询Boss：Boss图鉴 <Boss名称>",
            "查询境界：Boss图鉴 <炼气/筑基/金丹/元婴>",
        ])
        return "\n".join(lines)

    def _format_template_codex(self, template: dict) -> str:
        lines = [
            f"📕 Boss图鉴·{template['name']}",
            "━━━━━━━━━━━━━━━",
            f"伤害类型：{self._damage_type_name(template['damage_type'])}",
            f"出现权重：{template['weight']}%",
            f"奖励倍率：×{template['reward_mult']:.2g}",
            f"特性：{template['description']}",
            "",
            "【境界数值】",
        ]
        for realm in self.boss_service.REALM_CONFIGS:
            values = self._template_values(realm, template)
            lines.append(
                f"{realm['name']}｜HP {values['hp']:,}｜ATK {values['atk']:,}"
                f"｜减伤 {values['defense']}%｜修为 {values['exp']:,}"
                f"｜灵石 {values['stone']:,}"
            )

        lines.extend(["", "【可能掉落】"])
        for item in self.boss_service.BOSS_DROP_TABLES.get(template["id"], []):
            min_realm = self.boss_service.REALM_CONFIGS[
                min(len(self.boss_service.REALM_CONFIGS) - 1, int(item.get("min_realm", 0)))
            ]["name"]
            lines.append(f"· {item['name']}（{min_realm}起）")
        lines.append("掉落由每位参与者独立判定，伤害排名会影响概率。")
        return "\n".join(lines)

    def _format_realm_codex(self, realm: dict) -> str:
        lines = [
            f"📕 Boss图鉴·{realm['name']}境",
            "━━━━━━━━━━━━━━━",
            f"自然出现权重：{realm['weight']}%",
            "",
        ]
        for template in self.boss_service.BOSS_TEMPLATES:
            values = self._template_values(realm, template)
            lines.append(
                f"{template['name']}｜HP {values['hp']:,}｜ATK {values['atk']:,}"
                f"｜{self._damage_type_name(template['damage_type'])}"
                f"｜减伤 {values['defense']}%"
            )
        return "\n".join(lines)

    async def handle_boss_codex(
        self,
        event: AstrMessageEvent,
        query: str = "",
    ) -> AsyncGenerator:
        """查看Boss总览、指定Boss或指定境界的固定数据。"""
        try:
            query = str(query or "").strip()
            if not query:
                yield event.plain_result(self._format_codex_overview())
                return

            normalized_realm = query.removesuffix("境").removesuffix("期")
            realm = next(
                (
                    realm for realm in self.boss_service.REALM_CONFIGS
                    if realm["name"] == normalized_realm
                ),
                None,
            )
            if realm:
                yield event.plain_result(self._format_realm_codex(realm))
                return

            template = next(
                (
                    template for template in self.boss_service.BOSS_TEMPLATES
                    if (
                        query == template["name"]
                        or query in template["name"]
                        or template["name"] in query
                    )
                ),
                None,
            )
            if template:
                yield event.plain_result(self._format_template_codex(template))
                return

            names = "、".join(
                template["name"] for template in self.boss_service.BOSS_TEMPLATES
            )
            yield event.plain_result(
                f"图鉴中未找到【{query}】\n"
                f"可查询Boss：{names}\n"
                "也可以查询：炼气、筑基、金丹、元婴"
            )
        except Exception as e:
            yield event.plain_result(f"查询Boss图鉴失败：{e}")
    
    async def handle_boss_info(self, event: AstrMessageEvent) -> AsyncGenerator:
        """处理查看Boss信息命令"""
        try:
            boss = self.boss_service.get_active_boss()
            
            if not boss:
                next_spawn_time = self.boss_service.ensure_spawn_schedule()
                yield event.plain_result(
                    "🌫️ 当前没有世界Boss\n"
                    f"下一只预计在{self._format_remaining(next_spawn_time)}内降临。"
                )
                return
            
            hp_percent = boss.get_hp_percent()
            
            lines = [
                "👹 当前Boss",
                "━━━━━━━━━━━━━━━",
                f"名称：{boss.boss_name}",
                f"境界：{boss.boss_level}",
                "",
                f"HP：{boss.hp:,}/{boss.max_hp:,} ({hp_percent:.1f}%)",
                f"ATK：{boss.atk:,}",
                f"伤害类型：{self._damage_type_name(boss.damage_type)}",
                f"防御：{boss.defense}%减伤",
                "",
                f"修为奖池：{boss.exp_reward:,}",
                f"灵石奖池：{boss.stone_reward:,}",
                f"标准讨伐规模：{boss.target_participants}名同境界玩家",
                f"脱战回血：每小时{self.boss_service.BOSS_REGEN_RATE_PER_HOUR * 100:.0f}%",
                "",
                "使用【挑战Boss】来挑战！"
            ]

            damage_ranking = sorted(
                boss.damage_records.items(),
                key=lambda item: item[1],
                reverse=True,
            )
            if damage_ranking:
                lines.extend(["", "📊 当前伤害榜"])
                for rank, (user_id, damage) in enumerate(damage_ranking[:5], start=1):
                    name = boss.participant_names.get(user_id, f"道友{user_id[:6]}")
                    lines.append(f"{rank}. {name}：{damage:,}")
            
            yield event.plain_result("\n".join(lines))
            
        except GameException as e:
            yield event.plain_result(str(e))
        except Exception as e:
            yield event.plain_result(f"查询Boss信息失败：{e}")
    
    async def handle_challenge_boss(self, event: AstrMessageEvent) -> AsyncGenerator:
        """处理挑战Boss命令"""
        try:
            user_id = event.get_sender_id()
            
            # 获取Boss信息
            boss = self.boss_service.get_active_boss()
            if not boss:
                yield event.plain_result("当前没有Boss")
                return
            
            # 挑战Boss
            result = await self.boss_service.challenge_boss(user_id)
            
            # 构建战斗日志
            combat_log_text = "\n".join(result.combat_log)
            
            # 构建结果消息
            if result.boss_defeated:
                # 玩家胜利
                lines = [
                    combat_log_text,
                    "",
                    "🎉 挑战成功！",
                    "━━━━━━━━━━━━━━━",
                    f"你成功击败了『{boss.boss_name}』！",
                    "",
                    f"战斗回合数：{result.rounds}",
                    f"本次伤害：{result.damage_dealt:,}",
                    f"累计伤害：{result.cumulative_damage:,}",
                    f"获得修为：{result.exp_reward:,}",
                    f"获得灵石：{result.stone_reward:,}",
                ]
                
                # 物品奖励
                if result.items_gained:
                    item_lines = []
                    for item_name, count in result.items_gained:
                        item_lines.append(f"  · {item_name} x{count}")
                    lines.append("\n📦 获得物品：\n" + "\n".join(item_lines))

                if result.reward_distribution:
                    lines.append("\n🏆 击杀分账（按累计伤害权重）")
                    for reward in result.reward_distribution[:10]:
                        lines.append(
                            f"{reward['rank']}. {reward['name']}｜"
                            f"伤害 {reward['damage']:,}｜"
                            f"修为 {reward['exp']:,}｜灵石 {reward['gold']:,}"
                        )

                if result.next_spawn_time:
                    lines.append(
                        "\n🌫️ 下一只Boss将在"
                        f"{self._format_remaining(result.next_spawn_time)}内随机降临"
                    )
                
                lines.append(f"\n你的HP：{result.player_final_hp:,}")
            else:
                # 单次未能击杀；奖励统一保留到Boss死亡时分配。
                lines = [
                    combat_log_text,
                    "",
                    "⚔️ 本次讨伐结束",
                    "━━━━━━━━━━━━━━━",
                    f"『{boss.boss_name}』仍未被击杀。",
                    "",
                    f"战斗回合数：{result.rounds}",
                    f"本次伤害：{result.damage_dealt:,}",
                    f"累计伤害：{result.cumulative_damage:,}",
                    "奖励将在Boss被击杀时统一按累计伤害结算。",
                    "",
                    f"你的剩余血量：{result.player_final_hp:,}",
                    f"{boss.boss_name} 剩余HP：{result.boss_final_hp:,}/{boss.max_hp:,}"
                ]
            
            yield event.plain_result("\n".join(lines))
            
        except GameException as e:
            yield event.plain_result(str(e))
        except Exception as e:
            yield event.plain_result(f"挑战Boss失败：{e}")
    
    @require_admin
    async def handle_spawn_boss(self, event: AstrMessageEvent) -> AsyncGenerator:
        """处理生成Boss命令（管理员）"""
        try:
            # 生成Boss
            boss = self.boss_service.auto_spawn_boss()
            
            lines = [
                "👹 Boss降临",
                "━━━━━━━━━━━━━━━",
                "",
                f"{boss.boss_name}降临世间！",
                "",
                f"境界：{boss.boss_level}",
                f"HP：{boss.max_hp:,}",
                f"ATK：{boss.atk:,}",
                f"伤害类型：{self._damage_type_name(boss.damage_type)}",
                f"防御：{boss.defense}%减伤",
                f"修为奖池：{boss.exp_reward:,}",
                f"灵石奖池：{boss.stone_reward:,}",
                f"标准讨伐规模：{boss.target_participants}名同境界玩家",
                "",
                "快来挑战吧！"
            ]
            
            yield event.plain_result("\n".join(lines))
            
        except GameException as e:
            yield event.plain_result(str(e))
        except Exception as e:
            yield event.plain_result(f"生成Boss失败：{e}")
