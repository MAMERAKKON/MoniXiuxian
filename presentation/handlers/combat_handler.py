"""战斗命令处理器。"""
import re
from typing import Optional

from astrbot.api.event import AstrMessageEvent
from astrbot.api.message_components import At

from ...application.services.combat_service import CombatService
from ...core.exceptions import InvalidStateException, PlayerNotFoundException
from ..decorators import require_player


class CombatHandler:
    """处理切磋、决斗及战斗记录命令。"""

    def __init__(self, combat_service: CombatService, player_service):
        self.combat_service = combat_service
        self.player_service = player_service

    @staticmethod
    def _component_target(component) -> Optional[str]:
        """兼容不同消息适配器的At目标字段。"""
        for attr in ("qq", "target", "uin", "user_id"):
            candidate = getattr(component, attr, None)
            if candidate is not None and str(candidate).strip():
                return str(candidate).strip().lstrip("@")
        return None

    async def _get_target_id(self, event: AstrMessageEvent, arg: str) -> Optional[str]:
        """
        提取目标ID。

        不再依赖“命令文本必须出现在At组件之前”，避免适配器拆分、删除或
        重排消息组件时偶发找不到目标。
        """
        arg_text = str(arg or "").strip()
        numeric_match = re.fullmatch(r"@?(\d+)", arg_text)
        if numeric_match:
            return numeric_match.group(1)

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

        # 先取真正的At组件，再使用鸭子类型兼容少数适配器的自定义At类。
        components = [component for component in message_chain if isinstance(component, At)]
        components.extend(
            component for component in message_chain
            if not isinstance(component, At)
            and component.__class__.__name__.lower() in {"at", "mention"}
        )
        for component in components:
            target_id = self._component_target(component)
            if target_id and target_id not in excluded_ids:
                return target_id
        return None

    async def _handle_pvp(
        self,
        event: AstrMessageEvent,
        player,
        target: str,
        command_name: str,
        combat_type: str
    ):
        """切磋与决斗共用的命令流程。"""
        user_id = str(event.get_sender_id())
        target_id = await self._get_target_id(event, target)

        if not target_id:
            yield event.plain_result(
                f"❌ 请指定{command_name}目标\n"
                f"💡 使用方法：{command_name} @对方 或 {command_name} [对方ID]"
            )
            return
        if user_id == target_id:
            yield event.plain_result(f"❌ 不能和自己{command_name}")
            return

        try:
            can_fight, remaining = await self.combat_service.check_combat_cooldown(
                user_id,
                combat_type
            )
            if not can_fight:
                yield event.plain_result(f"❌ {command_name}冷却中，还需 {remaining} 秒")
                return

            if combat_type == "duel":
                result = await self.combat_service.execute_duel(user_id, target_id)
            else:
                result = await self.combat_service.execute_spar(user_id, target_id)
            yield event.plain_result("\n".join(result.combat_log))

        except PlayerNotFoundException:
            yield event.plain_result("❌ 你还未踏入修仙之路")
        except InvalidStateException as exc:
            yield event.plain_result(f"❌ {exc}")
        except ValueError as exc:
            yield event.plain_result(f"❌ {exc}")
        except Exception as exc:
            yield event.plain_result(f"❌ {command_name}失败：{exc}")

    @require_player
    async def handle_spar(self, event: AstrMessageEvent, player, target: str = ""):
        """处理无损切磋。"""
        async for result in self._handle_pvp(
            event, player, target, "切磋", "spar"
        ):
            yield result

    @require_player
    async def handle_duel(self, event: AstrMessageEvent, player, target: str = ""):
        """处理决斗；当前规则与切磋完全一致。"""
        async for result in self._handle_pvp(
            event, player, target, "决斗", "duel"
        ):
            yield result

    @require_player
    async def handle_combat_log(self, event: AstrMessageEvent, player):
        """处理查看战斗记录命令。"""
        yield event.plain_result("⚠️ 战斗记录功能开发中...")
