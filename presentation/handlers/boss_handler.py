"""Boss命令处理器"""
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
    
    async def handle_boss_info(self, event: AstrMessageEvent) -> AsyncGenerator:
        """处理查看Boss信息命令"""
        try:
            boss = self.boss_service.get_active_boss()
            
            if not boss:
                yield event.plain_result("当前没有Boss")
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
                f"防御：{boss.defense}%减伤",
                "",
                f"奖励：{boss.stone_reward:,}灵石",
                "",
                "使用【挑战Boss】来挑战！"
            ]
            
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
                    f"获得灵石：{result.stone_reward:,}",
                ]
                
                # 物品奖励
                if result.items_gained:
                    item_lines = []
                    for item_name, count in result.items_gained:
                        item_lines.append(f"  · {item_name} x{count}")
                    lines.append("\n📦 获得物品：\n" + "\n".join(item_lines))
                
                lines.append(f"\n你的HP：{result.player_final_hp:,}")
            else:
                # 玩家失败
                lines = [
                    combat_log_text,
                    "",
                    "💀 挑战失败",
                    "━━━━━━━━━━━━━━━",
                    f"你被『{boss.boss_name}』击败了！",
                    "",
                    f"战斗回合数：{result.rounds}",
                    f"安慰奖：{result.stone_reward:,}灵石",
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
                f"防御：{boss.defense}%减伤",
                f"奖励：{boss.stone_reward:,}灵石",
                "",
                "快来挑战吧！"
            ]
            
            yield event.plain_result("\n".join(lines))
            
        except GameException as e:
            yield event.plain_result(str(e))
        except Exception as e:
            yield event.plain_result(f"生成Boss失败：{e}")
