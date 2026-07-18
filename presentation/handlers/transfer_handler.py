"""转账命令处理器。"""

from typing import AsyncGenerator
import re

from astrbot.api.event import AstrMessageEvent
from astrbot.api.message_components import At

from ...application.services.transfer_service import TransferService


class TransferHandler:
    def __init__(self, transfer_service: TransferService):
        self.transfer_service = transfer_service

    @staticmethod
    def _at_target_id(component) -> str:
        for field in ("target", "qq", "user_id", "id"):
            value = getattr(component, field, None)
            if value is not None and str(value).strip():
                return str(value).strip().lstrip("@")
        return ""

    def _extract_at_target(self, event: AstrMessageEvent) -> str:
        message_obj = getattr(event, "message_obj", None)
        for component in getattr(message_obj, "message", []) or []:
            if isinstance(component, At) or component.__class__.__name__.lower() in {"at", "mention"}:
                target_id = self._at_target_id(component)
                if target_id and target_id != str(event.get_sender_id()):
                    return target_id
        return ""

    async def handle_transfer(
        self, event: AstrMessageEvent, args: str = ""
    ) -> AsyncGenerator[str, None]:
        parts = str(args or "").strip().split()
        target_id = self._extract_at_target(event)
        if not target_id and parts:
            # 保留数字 ID 兼容模式：转账 <收款人ID> <金额>
            target_id = parts[0].lstrip("@")
        # 部分 QQ 适配器会把 At 和文本拆开，优先从完整消息末尾提取金额。
        full_text = ""
        if hasattr(event, "message_str"):
            full_text = str(event.message_str or "")
        elif hasattr(event, "get_message_str"):
            try:
                full_text = str(event.get_message_str() or "")
            except Exception:
                full_text = ""
        amount_match = re.search(r"(\d+)\s*$", full_text)
        amount_text = amount_match.group(1) if amount_match else (parts[-1] if parts else "")
        if not target_id or not amount_text:
            yield event.plain_result("用法：转账 @收款人 金额（也支持：转账 <收款人ID> <金额>）")
            return
        try:
            amount = int(amount_text)
        except ValueError:
            yield event.plain_result("金额必须是整数")
            return

        try:
            sender_id = str(event.get_sender_id())
            result = self.transfer_service.transfer(sender_id, target_id, amount)
            yield event.plain_result(result)
        except Exception as exc:
            yield event.plain_result(f"❌ 转账失败：{exc}")
