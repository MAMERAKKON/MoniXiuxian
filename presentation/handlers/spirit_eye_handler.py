"""天地灵眼命令处理器"""
from typing import AsyncGenerator
from astrbot.api.event import AstrMessageEvent

from ...application.services.spirit_eye_service import SpiritEyeService
from ...core.exceptions import GameException
from ..decorators import require_admin


class SpiritEyeHandler:
    """天地灵眼命令处理器"""
    
    def __init__(self, spirit_eye_service: SpiritEyeService):
        self.spirit_eye_service = spirit_eye_service
    
    async def handle_spirit_eye_info(self, event: AstrMessageEvent) -> AsyncGenerator:
        """查看灵眼信息"""
        try:
            user_id = event.get_sender_id()
            my_eye, available_eyes = self.spirit_eye_service.get_spirit_eye_info(user_id)
            
            lines = ["👁️ 天地灵眼", "━━━━━━━━━━━━━━━"]
            
            if my_eye:
                lines.append(f"【我的灵眼】{my_eye.eye_name}")
                lines.append(f"每小时：+{my_eye.exp_per_hour:,} 修为")
                if my_eye.pending_hours > 0:
                    lines.append(f"待收取：约 +{my_eye.pending_exp:,} 修为")
                lines.append("")
            
            if available_eyes:
                lines.append("【可抢占的灵眼】")
                for eye in available_eyes[:5]:
                    lines.append(f"  [{eye.eye_id}] {eye.eye_name} (+{eye.exp_per_hour:,}/时)")
                lines.append("")
                lines.append("💡 抢占灵眼 <ID>")
            else:
                lines.append("当前没有无主灵眼。")
            
            yield event.plain_result("\n".join(lines))
            
        except GameException as e:
            yield event.plain_result(str(e))
        except Exception as e:
            yield event.plain_result(f"获取灵眼信息失败：{e}")
    
    async def handle_claim(self, event: AstrMessageEvent, eye_id: str) -> AsyncGenerator:
        """抢占灵眼"""
        try:
            if not eye_id or not eye_id.isdigit():
                yield event.plain_result("请指定要抢占的灵眼ID，例如：抢占灵眼 1")
                return
            
            user_id = event.get_sender_id()
            result = self.spirit_eye_service.claim_spirit_eye(user_id, int(eye_id))
            yield event.plain_result(result)
            
        except GameException as e:
            yield event.plain_result(str(e))
        except Exception as e:
            yield event.plain_result(f"抢占灵眼失败：{e}")
    
    async def handle_collect(self, event: AstrMessageEvent) -> AsyncGenerator:
        """收取灵眼收益"""
        try:
            user_id = event.get_sender_id()
            result = self.spirit_eye_service.collect_spirit_eye(user_id)
            yield event.plain_result(result)
            
        except GameException as e:
            yield event.plain_result(str(e))
        except Exception as e:
            yield event.plain_result(f"收取灵眼失败：{e}")
    
    async def handle_release(self, event: AstrMessageEvent) -> AsyncGenerator:
        """释放灵眼"""
        try:
            user_id = event.get_sender_id()
            result = self.spirit_eye_service.release_spirit_eye(user_id)
            yield event.plain_result(result)
            
        except GameException as e:
            yield event.plain_result(str(e))
        except Exception as e:
            yield event.plain_result(f"释放灵眼失败：{e}")
    
    # ⭐ ===== 新增：管理员命令 =====
    @require_admin
    async def handle_spawn_spirit_eye(self, event: AstrMessageEvent) -> AsyncGenerator:
        """处理生成灵眼命令（管理员）"""
        try:
            # 生成灵眼
            result = self.spirit_eye_service.spawn_spirit_eye()
            
            lines = [
                "👁️ 天地灵眼生成",
                "━━━━━━━━━━━━━━━",
                "",
                f"✨ {result}",
                "",
                "💡 使用【灵眼信息】查看所有灵眼",
                "💡 使用【抢占灵眼 ID】抢占灵眼"
            ]
            
            yield event.plain_result("\n".join(lines))
            
        except GameException as e:
            yield event.plain_result(str(e))
        except Exception as e:
            yield event.plain_result(f"生成灵眼失败：{e}")