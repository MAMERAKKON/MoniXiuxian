"""Boss命令处理器"""
import time
from typing import AsyncGenerator
from astrbot.api.event import AstrMessageEvent
from astrbot.api import logger
from astrbot.api.message_components import At

from ...application.services.boss_service import BossService
from ...core.exceptions import GameException
from ...core.config import ConfigManager
from ..decorators import require_admin


class BossHandler:
    """Boss命令处理器"""
    
    def __init__(self, boss_service: BossService, config_manager: ConfigManager,
                 broadcast_callback=None):
        self.boss_service = boss_service
        self.config_manager = config_manager
        self.broadcast_callback = broadcast_callback

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
    def _format_white_bonus(white_bonus: dict) -> str:
        labels = {
            "physical_damage": "物伤",
            "magic_damage": "法伤",
            "physical_defense": "物防",
            "magic_defense": "法防",
            "mental_power": "精神力",
            "lifespan": "寿命",
        }
        return "、".join(
            f"{labels.get(key, key)}+{value:,}"
            for key, value in white_bonus.items()
        ) or "无"

    @staticmethod
    def _split_message(text: str, limit: int = 3500) -> list[str]:
        """按换行切分长战报，避免超过QQ单条消息长度。"""
        if len(text) <= limit:
            return [text]
        chunks, current = [], []
        current_len = 0
        for line in text.splitlines():
            line_len = len(line) + 1
            if current and current_len + line_len > limit:
                chunks.append("\n".join(current))
                current, current_len = [], 0
            if len(line) > limit:
                for start in range(0, len(line), limit):
                    chunks.append(line[start:start + limit])
                continue
            current.append(line)
            current_len += line_len
        if current:
            chunks.append("\n".join(current))
        return chunks

    @staticmethod
    def _at_target_id(component):
        for attr in ("qq", "target", "uin", "user_id"):
            value = getattr(component, attr, None)
            if value is not None and str(value).strip():
                return str(value).strip().lstrip("@")
        return None

    def _resolve_captain_id(self, event: AstrMessageEvent, captain_id: str) -> str:
        """兼容原有数字ID，也支持从消息中的 @ 提及提取队长QQ号。"""
        captain_id = str(captain_id or "").strip().lstrip("@")
        if captain_id.isdigit():
            return captain_id
        message_chain = []
        if getattr(event, "message_obj", None):
            message_chain = getattr(event.message_obj, "message", []) or []
        for component in message_chain:
            if isinstance(component, At) or component.__class__.__name__.lower() in {"at", "mention"}:
                target_id = self._at_target_id(component)
                if target_id and target_id != str(event.get_sender_id()):
                    return target_id
        return ""

    def _team_member_display(self, user_id: str) -> str:
        player = self.boss_service.player_repo.get_player(str(user_id))
        if not player:
            return f"未知道友｜境界未知｜战力 0"
        level_data = self.config_manager.get_level_data(
            player.cultivation_type.value
        ) or []
        if level_data and 0 <= player.level_index < len(level_data):
            level_name = level_data[player.level_index].get(
                "name",
                level_data[player.level_index].get("level_name", "未知境界"),
            )
        else:
            level_name = "未知境界"
        tao_name = player.user_name or player.nickname or f"道友{str(user_id)[:6]}"
        return f"{tao_name}｜{level_name}｜战力 {player.calculate_power():,}"

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
                    lines.append("\n🏆 击杀分账（按参与、有效伤害、承伤与吸引火力综合权重）")
                    for reward in result.reward_distribution[:10]:
                        white_bonus = self._format_white_bonus(reward.get("white_bonus", {}))
                        lines.append(
                            f"{reward['rank']}. {reward['name']}｜"
                            f"伤害 {reward['damage']:,}｜"
                            f"修为 {reward['exp']:,}｜灵石 {reward['gold']:,}｜白值 {white_bonus}"
                        )

                if result.next_spawn_time:
                    lines.append(
                        "\n🌫️ 下一只Boss将在"
                        f"{self._format_remaining(result.next_spawn_time)}内随机降临"
                    )
                if result.boss_promoted:
                    promoted_boss = self.boss_service.get_active_boss()
                    if promoted_boss and self.broadcast_callback:
                        try:
                            await self.broadcast_callback(
                                "👹 单人击杀触发 Boss 强化刷新！\n"
                                f"新 Boss：{promoted_boss.boss_name}\n"
                                f"境界：{promoted_boss.boss_level}｜"
                                f"HP：{promoted_boss.max_hp:,}｜"
                                f"{('魔法' if promoted_boss.damage_type == 'magic' else '物理')}伤害"
                            )
                        except Exception as broadcast_error:
                            logger.warning(f"强化 Boss 公告广播失败：{broadcast_error}")
                    lines.append(
                        "\n⚡ 由于本次为单人击杀，下一只更强 Boss 已立即降临："
                        f"「{result.boss_promoted_level}」境，满血等待挑战。"
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
            for chunk in self._split_message("\n".join(lines)):
                yield event.plain_result(chunk)
            
        except GameException as e:
            yield event.plain_result(str(e))
        except Exception as e:
            yield event.plain_result(f"挑战Boss失败：{e}")
    
    async def handle_create_boss_team(self, event: AstrMessageEvent) -> AsyncGenerator:
        try:
            captain_id = str(event.get_sender_id())
            members = self.boss_service.create_boss_team(captain_id)
            yield event.plain_result(
                "✅ 讨伐队创建成功！\n"
                f"队长：{self._team_member_display(captain_id)}\n"
                f"当前成员：{len(members)} 人（无人数上限）\n"
                "其他玩家可直接使用：加入讨伐队\n"
                "队长准备完成后使用【发起讨伐】，本次战斗结束后队伍自动解散。"
            )
        except Exception as e:
            yield event.plain_result(str(e))

    async def handle_join_boss_team(
        self, event: AstrMessageEvent, captain_id: str = ""
    ) -> AsyncGenerator:
        try:
            members = self.boss_service.join_boss_team(
                str(event.get_sender_id())
            )
            yield event.plain_result(f"✅ 加入讨伐队成功！当前队伍 {len(members)} 人。")
        except Exception as e:
            yield event.plain_result(str(e))

    async def handle_boss_team_info(self, event: AstrMessageEvent) -> AsyncGenerator:
        team = self.boss_service.get_boss_team(str(event.get_sender_id()))
        if not team:
            yield event.plain_result("你当前不在讨伐队中。")
            return
        captain_id, members = team
        member_lines = []
        for member_id in sorted(members):
            marker = "（队长）" if member_id == captain_id else ""
            member_lines.append(f"- {self._team_member_display(member_id)}{marker}")
        yield event.plain_result(
            f"⚔️ 讨伐队信息\n人数：{len(members)}（无人数上限）\n"
            "成员：\n" + "\n".join(member_lines)
            + "\n队长使用【发起讨伐】后，本次战斗结束即自动解散。"
        )

    async def handle_start_boss_team(self, event: AstrMessageEvent) -> AsyncGenerator:
        try:
            results = await self.boss_service.challenge_boss_team(
                str(event.get_sender_id())
            )
            if not results:
                yield event.plain_result("本次讨伐没有产生有效战斗。")
                return
            last = results[-1]
            reward_count = len(last.reward_distribution)
            lines = [
                "⚔️ Boss团战战报",
                "━━━━━━━━━━━━━━━",
                f"Boss：{last.combat_log[0].split('团战开始')[0].replace('⚔️ ', '') if last.combat_log else '未知'}",
                f"本次参战：{len(results)} 人｜战斗回合：{last.rounds}",
                f"本次造成伤害：{sum(r.damage_dealt for r in results):,}",
                f"本Boss累计贡献者：{reward_count} 人",
                "━━━━━━━━━━━━━━━",
                "【战斗过程】",
                "\n".join(last.combat_log[1:] if last.combat_log else []),
                "━━━━━━━━━━━━━━━",
            ]
            if last.boss_defeated:
                lines.append("✅ Boss 已被讨伐，奖励已按参与、有效伤害、承伤与吸引火力综合结算。")
                lines.append("额外掉落：按Boss难度系数 × 个人贡献系数独立判定，不改变修为、灵石和白值算法。")
                lines.append("【贡献与奖励】")
                for reward in last.reward_distribution:
                    white_bonus = self._format_white_bonus(reward.get("white_bonus", {}))
                    items = "、".join(
                        f"{name}×{count}" for name, count in reward.get("items", [])
                    ) or "无"
                    lines.append(
                        f"{reward['rank']}. {reward['name']}｜贡献 {reward.get('weight', 0) * 100:.1f}%\n"
                        f"  伤害 {reward.get('damage', 0):,}｜承伤 {reward.get('damage_taken', 0):,}｜"
                        f"吸引 {reward.get('target_count', 0)}次\n"
                        f"  修为 +{reward['exp']:,}｜灵石 +{reward['gold']:,}\n"
                        f"  白值 {white_bonus}｜掉落 {items}\n"
                        f"  额外掉落判定：{reward.get('extra_drop_rolls', 0)}次"
                    )
            else:
                lines.append("⚠️ Boss 尚未被击败，队伍已按规则自动解散。")
            for chunk in self._split_message("\n".join(lines)):
                yield event.plain_result(chunk)
        except Exception as e:
            yield event.plain_result(str(e))

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
            
            result = "\n".join(lines)
            try:
                if self.broadcast_callback:
                    await self.broadcast_callback(result)
                else:
                    from astrbot.api import broadcast
                    await broadcast(result)
            except Exception as broadcast_error:
                logger.warning(f"Boss公告广播失败：{broadcast_error}")
            yield event.plain_result(result)
            
        except GameException as e:
            yield event.plain_result(str(e))
        except Exception as e:
            yield event.plain_result(f"生成Boss失败：{e}")
