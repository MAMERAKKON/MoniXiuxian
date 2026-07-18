"""玩家间灵石转账服务。"""

import math

from ...core.constants import ECONOMY_OWNER_ID
from ...core.exceptions import BusinessException
from ...infrastructure.repositories.player_repo import PlayerRepository


class TransferService:
    """处理玩家间转账及统一服务费。"""

    FEE_RATE = 0.0025  # 0.25%

    def __init__(self, player_repo: PlayerRepository):
        self.player_repo = player_repo

    def transfer(self, sender_id: str, receiver_id: str, amount: int) -> str:
        sender_id = str(sender_id).strip()
        receiver_id = str(receiver_id).strip()
        if not receiver_id:
            raise BusinessException("请指定收款人 ID")
        if sender_id == receiver_id:
            raise BusinessException("不能给自己转账")
        if amount <= 0:
            raise BusinessException("转账金额必须大于 0")

        sender = self.player_repo.get_by_id(sender_id)
        receiver = self.player_repo.get_by_id(receiver_id)
        if not sender:
            raise BusinessException("付款方玩家不存在")
        if not receiver:
            raise BusinessException("收款方玩家不存在")

        # 灵石为整数，向上取整确保 0.25% 不会因小额转账变成零费用。
        fee = max(1, math.ceil(amount * self.FEE_RATE))
        total = amount + fee
        if sender.gold < total:
            raise BusinessException(
                f"灵石不足，需要转账 {amount:,} + 手续费 {fee:,}，"
                f"共 {total:,} 灵石；当前仅有 {sender.gold:,} 灵石"
            )

        sender.gold -= total
        receiver.gold += amount
        self.player_repo.save(sender)
        self.player_repo.save(receiver)
        self.player_repo.add_gold(ECONOMY_OWNER_ID, fee)

        return (
            f"✅ 转账成功\n"
            f"收款人：{receiver.nickname}\n"
            f"转账金额：{amount:,} 灵石\n"
            f"服务费（0.25%）：{fee:,} 灵石\n"
            f"剩余灵石：{sender.gold:,}"
        )
