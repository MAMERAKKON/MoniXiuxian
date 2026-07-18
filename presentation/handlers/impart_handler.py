"""传承命令处理器"""
import re
from astrbot.api.event import AstrMessageEvent
from astrbot.api.message_components import At

from ...application.services.impart_service import ImpartService


class ImpartHandler:
    """传承命令处理器"""
    
    def __init__(self, impart_service: ImpartService):
        self.impart_service = impart_service
    
    async def handle_impart_info(self, event: AstrMessageEvent):
        """查看传承信息"""
        user_id = str(event.get_sender_id())
        success, msg = self.impart_service.get_impart_info(user_id)
        yield event.plain_result(msg)
    
    async def handle_impart_challenge(self, event: AstrMessageEvent, target_info: str = ""):
        """发起传承挑战"""
        user_id = str(event.get_sender_id())
        
        # 解析目标
        target_id = self._extract_user_id(target_info, event)
        if not target_id:
            yield event.plain_result(
                "⚔️ 传承挑战\n"
                "━━━━━━━━━━━━━━━\n"
                "争夺对方的传承加成！\n"
                "胜利：随机夺取一项传承\n"
                "失败：损失1%修为\n"
                "━━━━━━━━━━━━━━━\n"
                "💡 用法：传承挑战 @某人 或 传承挑战 对方ID"
            )
            return
        
        success, msg = await self.impart_service.challenge_impart(user_id, target_id)
        yield event.plain_result(msg)
    
    async def handle_impart_ranking(self, event: AstrMessageEvent):
        """传承排行榜"""
        success, msg = self.impart_service.get_ranking(10)
        yield event.plain_result(msg)
    
    def _extract_user_id(self, msg: str, event: AstrMessageEvent) -> str:
        """从文本或真实At组件中提取用户ID。"""
        msg = str(msg or "")

        # 兼容“小豆传承挑战 123456789”等唤醒前缀场景：
        # 部分适配器不会把命令后的数字参数传入 target_info。
        if not msg.strip():
            full_text = ""
            if hasattr(event, "message_str"):
                full_text = str(event.message_str or "")
            elif hasattr(event, "get_message_str"):
                try:
                    full_text = str(event.get_message_str() or "")
                except Exception:
                    full_text = ""
            command_match = re.search(r"传承挑战\s+(.+)", full_text)
            if command_match:
                msg = command_match.group(1).strip()

        # 匹配 @xxx 或纯数字
        at_match = re.search(r'\[CQ:at,qq=(\d+)\]', msg)
        if at_match:
            return at_match.group(1)
        
        # 纯数字 ID 模式：传承挑战 <用户ID>
        num_match = re.search(r'(\d{5,12})', msg)
        if num_match:
            return num_match.group(1)

        excluded_ids = {str(event.get_sender_id())}
        for method_name in ("get_self_id", "get_bot_id"):
            method = getattr(event, method_name, None)
            if callable(method):
                try:
                    value = method()
                    if value is not None:
                        excluded_ids.add(str(value))
                except Exception:
                    pass

        message_chain = []
        if getattr(event, "message_obj", None):
            message_chain = getattr(event.message_obj, "message", []) or []
        for component in message_chain:
            if not isinstance(component, At) and component.__class__.__name__.lower() not in {"at", "mention"}:
                continue
            for attr in ("qq", "target", "uin", "user_id"):
                candidate = getattr(component, attr, None)
                if candidate is None:
                    continue
                target_id = str(candidate).strip().lstrip("@")
                if target_id and target_id not in excluded_ids:
                    return target_id

        return ""
