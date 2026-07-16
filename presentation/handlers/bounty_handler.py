"""悬赏命令处理器"""
from typing import AsyncGenerator
from astrbot.api.event import AstrMessageEvent

from ...application.services.bounty_service import BountyService
from ...core.exceptions import GameException


class BountyHandler:
    """悬赏命令处理器"""
    
    def __init__(self, bounty_service: BountyService):
        self.bounty_service = bounty_service
    
    async def handle_bounty_list(self, event: AstrMessageEvent) -> AsyncGenerator:
        """处理悬赏列表命令"""
        try:
            user_id = event.get_sender_id()
            bounties = self.bounty_service.get_bounty_list(user_id)
            
            if not bounties:
                yield event.plain_result("暂无可用的悬赏任务")
                return
            
            # 构建悬赏列表
            lines = ["📜 悬赏令 · 今日委托", "━━━━━━━━━━━━━━━"]
            
            for b in bounties:
                reward = b.reward
                time_limit_min = b.time_limit // 60
                lines.append(
                    f"[{b.id}] {b.name}（{b.difficulty_name}·{b.category}）\n"
                    f"  - 目标：完成 {b.count} 次 | 时限：{time_limit_min} 分钟\n"
                    f"  - 奖励：{reward['stone']:,} 灵石 + {reward['exp']:,} 修为\n"
                    f"  - 说明：{b.description}"
                )
            
            lines.append("━━━━━━━━━━━━━━━")
            lines.append("💡 使用【接取悬赏 <编号>】接取任务")
            
            yield event.plain_result("\n".join(lines))
            
        except GameException as e:
            yield event.plain_result(str(e))
        except Exception as e:
            yield event.plain_result(f"查询悬赏列表失败：{e}")
    
    async def handle_accept_bounty(self, event: AstrMessageEvent, bounty_id: str = "") -> AsyncGenerator:
        """处理接取悬赏命令"""
        try:
            user_id = event.get_sender_id()
            
            # 解析悬赏ID
            if not bounty_id:
                yield event.plain_result("❌ 请指定悬赏编号，例如：接取悬赏 1")
                return
            
            try:
                bounty_id_int = int(bounty_id)
            except ValueError:
                yield event.plain_result("❌ 悬赏编号必须是数字")
                return
            
            result = self.bounty_service.accept_bounty(user_id, bounty_id_int)
            yield event.plain_result(result)
            
        except GameException as e:
            yield event.plain_result(str(e))
        except Exception as e:
            yield event.plain_result(f"接取悬赏失败：{e}")
    
    async def handle_bounty_status(self, event: AstrMessageEvent) -> AsyncGenerator:
        """处理悬赏状态命令"""
        try:
            user_id = event.get_sender_id()
            result = self.bounty_service.check_bounty_status(user_id)
            yield event.plain_result(result)
            
        except GameException as e:
            yield event.plain_result(str(e))
        except Exception as e:
            yield event.plain_result(f"查询悬赏状态失败：{e}")
    
    async def handle_complete_bounty(self, event: AstrMessageEvent) -> AsyncGenerator:
        """处理完成悬赏命令"""
        try:
            user_id = event.get_sender_id()
            result = self.bounty_service.complete_bounty(user_id)
            yield event.plain_result(result)
            
        except GameException as e:
            yield event.plain_result(str(e))
        except Exception as e:
            yield event.plain_result(f"完成悬赏失败：{e}")
    
    async def handle_abandon_bounty(self, event: AstrMessageEvent) -> AsyncGenerator:
        """处理放弃悬赏命令"""
        try:
            user_id = event.get_sender_id()
            result = self.bounty_service.abandon_bounty(user_id)
            yield event.plain_result(result)
            
        except GameException as e:
            yield event.plain_result(str(e))
        except Exception as e:
            yield event.plain_result(f"放弃悬赏失败：{e}")
