"""历练命令处理器"""
from typing import AsyncGenerator
from astrbot.api.event import AstrMessageEvent
from astrbot.api.message_components import Plain

from ...application.services.adventure_service import AdventureService
from ...core.exceptions import GameException


class AdventureHandler:
    """历练命令处理器"""
    
    def __init__(self, adventure_service: AdventureService):
        self.adventure_service = adventure_service
    
    async def handle_adventure_info(self, event: AstrMessageEvent) -> AsyncGenerator:
        """处理历练信息命令"""
        try:
            routes = self.adventure_service.get_route_overview()
            player = self.adventure_service.player_repo.get_player(event.get_sender_id())
            
            if not routes:
                yield event.plain_result("暂无可用的历练路线")
                return
            
            # 构建路线列表
            lines = ["📖 历练列表", "━━━━━━━━━━━━━━━"]
            
            for route in routes:
                duration = route["duration"] // 60
                success_rate = (
                    self.adventure_service._calculate_success_rate(player.level_index, self.adventure_service.routes[route["key"]])
                    if player else route["base_success_rate"]
                )
                lines.append(
                    f"\n【{route['name']}】"
                    f"\n- 时长：{duration}分钟｜风险：{route['risk']}"
                    f"\n- 本次成功率：{success_rate:.1f}%｜推荐境界：{route['min_level']}"
                    f"\n- 完整功法掉落率：{route['technique_drop_chance']}%"
                    f"\n- 修炼心得：{ '、'.join(route['cultivation_drop_names']) }"
                    f"\n- 修炼心得掉落率：{route['cultivation_drop_chance']}%"
                    f"\n- 功法与心得碎片掉落率：{route['fragment_drop_chance']}%（随机一种）"
                )
            
            lines.append(
                "\n💡 指令用法：\n"
                "  /开始历练 <路线名> → 开始\n"
                "  /历练状态 → 查看进度\n"
                "  /完成历练 → 领取奖励"
            )
            lines.append("━━━━━━━━━━━━━━━")
            
            yield event.plain_result("\n".join(lines))
            
        except GameException as e:
            yield event.plain_result(str(e))
        except Exception as e:
            yield event.plain_result(f"查询历练信息失败：{e}")
    
    async def handle_start_adventure(self, event: AstrMessageEvent, route_name: str = "") -> AsyncGenerator:
        """处理开始历练命令"""
        try:
            user_id = event.get_sender_id()
            
            if not route_name:
                yield event.plain_result("请指定历练路线\n使用【历练信息】查看可用路线")
                return
            
            result = self.adventure_service.start_adventure(user_id, route_name)
            yield event.plain_result(result)
            
        except GameException as e:
            yield event.plain_result(str(e))
        except Exception as e:
            yield event.plain_result(f"开始历练失败：{e}")
    
    async def handle_adventure_status(self, event: AstrMessageEvent) -> AsyncGenerator:
        """处理历练状态命令"""
        try:
            user_id = event.get_sender_id()
            result = self.adventure_service.check_adventure_status(user_id)
            yield event.plain_result(result)
            
        except GameException as e:
            yield event.plain_result(str(e))
        except Exception as e:
            yield event.plain_result(f"查询历练状态失败：{e}")
    
    async def handle_complete_adventure(self, event: AstrMessageEvent) -> AsyncGenerator:
        """处理完成历练命令"""
        try:
            user_id = event.get_sender_id()
            result = self.adventure_service.finish_adventure(user_id)
            
            # 直接从 adventure_service 的 player_repo 获取玩家信息
            player = self.adventure_service.player_repo.get_player(user_id)
            
            # 构建结果消息（模仿旧代码格式）
            lines = [
                f"🚶 历练归来",
                "━━━━━━━━━━━━━━━"
            ]
            
            # 事件描述
            if result.event_description:
                lines.append(f"{result.event_description}\n")

            if not result.success:
                lines.append("本次历练失败，未获得任何奖励。")
                if player:
                    lines.append(f"当前气血/灵气：1")
                yield event.plain_result("\n".join(lines))
                return
            
            # 奖励信息
            lines.append(f"获得修为：+{result.exp_gained:,}")
            lines.append(f"获得灵石：+{result.gold_gained:,}")
            
            # 物品
            if result.items_gained:
                item_lines = []
                for item in result.items_gained:
                    item_lines.append(f"  · {item['name']} x{item['count']}")
                lines.append(f"\n📦 获得物品：\n" + "\n".join(item_lines))

            if result.attribute_gained:
                lines.append(
                    "\n✨ 历练感悟："
                    f"{result.attribute_gained['label']} "
                    f"+{result.attribute_gained['value']:.2f}（已存入本世传承池）"
                )

            if result.bounty_progress_gained > 0:
                lines.append(
                    f"\n📜 悬赏进度：+{result.bounty_progress_gained}"
                )
            
            # 当前状态
            lines.append("\n━━━━━━━━━━━━━━━")
            if player:
                lines.append(f"当前修为：{player.experience:,}")
                lines.append(f"当前灵石：{player.gold:,}")
            
            # 休整提示
            if result.fatigue_cost > 0:
                fatigue_minutes = result.fatigue_cost // 60
                lines.append(f"\n⏳ 该路线休整：{fatigue_minutes} 分钟")
            
            yield event.plain_result("\n".join(lines))
            
        except GameException as e:
            yield event.plain_result(str(e))
        except Exception as e:
            yield event.plain_result(f"完成历练失败：{e}")
    
    async def handle_cancel_adventure(self, event: AstrMessageEvent) -> AsyncGenerator:
        """处理放弃历练命令"""
        try:
            user_id = event.get_sender_id()
            result = self.adventure_service.cancel_adventure(user_id)
            yield event.plain_result(result)
            
        except GameException as e:
            yield event.plain_result(str(e))
        except Exception as e:
            yield event.plain_result(f"放弃历练失败：{e}")
