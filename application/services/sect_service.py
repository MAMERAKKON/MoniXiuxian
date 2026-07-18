"""
宗门服务层

处理宗门相关的业务逻辑。
"""
import time
import random
from typing import Tuple, Optional, Dict, List, Any

from ...domain.models.sect import Sect, SectMember, SectPosition
from ...domain.models.player import Player
from ...infrastructure.repositories.sect_repo import SectRepository
from ...infrastructure.repositories.player_repo import PlayerRepository
from ...core.config import ConfigManager
from ...core.constants import GameConstants
from ...core.exceptions import BusinessException


class SectService:
    """宗门服务 - 重构版"""

    # ==================== 常量定义 ====================
    SECT_NAME_MIN_LENGTH = 2
    SECT_NAME_MAX_LENGTH = 12
    SECT_NAME_FORBIDDEN = ["管理员", "系统", "官方", "GM", "admin"]

    SECT_CREATE_REQUIRED_LEVEL = 3
    SECT_CREATE_REQUIRED_STONE = 10000
    SECT_MAX_MEMBERS = 50

    SECT_INITIAL_SCALE = 100
    SECT_INITIAL_MATERIALS = 100

    DONATION_RATE = 10  # 1灵石 = 10建设度
    TASK_COOLDOWN_SECONDS = 3600  # 1小时

    # ==================== 初始化 ====================

    def __init__(
        self,
        sect_repo: SectRepository,
        player_repo: PlayerRepository,
        config_manager: ConfigManager,
    ):
        self.sect_repo = sect_repo
        self.player_repo = player_repo
        self.config_manager = config_manager

    # ==================== 私有辅助方法 ====================

    def _get_player(self, user_id: str) -> Player:
        """获取玩家，不存在则抛出异常"""
        player = self.player_repo.get_by_id(user_id)
        if not player:
            raise BusinessException("玩家不存在")
        return player

    def _get_sect(self, sect_id: int) -> Sect:
        """获取宗门，不存在则抛出异常"""
        sect = self.sect_repo.get_by_id(sect_id)
        if not sect:
            raise BusinessException("宗门不存在")
        return sect

    def _get_player_sect(self, user_id: str) -> Tuple[Player, Sect]:
        """获取玩家及其所在宗门"""
        player = self._get_player(user_id)
        if not player.sect_id or player.sect_id == 0:
            raise BusinessException("你还未加入任何宗门")
        sect = self._get_sect(player.sect_id)
        return player, sect

    def _get_position(self, player: Player, sect: Sect) -> SectPosition:
        """
        获取玩家在宗门中的职位
        优先使用 leader_id 反推宗主身份，避免数据不一致
        """
        # 如果玩家是宗主，直接返回宗主
        if player.user_id == sect.leader_id:
            return SectPosition.LEADER

        # 否则从 player.sect_position 读取
        if player.sect_position is not None:
            try:
                return SectPosition(int(player.sect_position))
            except (ValueError, TypeError):
                pass

        # 默认外门弟子
        return SectPosition.OUTER_DISCIPLE

    def _has_permission(
        self, operator: Player, sect: Sect, required: SectPosition
    ) -> bool:
        """
        检查操作者是否有指定权限
        权限等级：宗主(0) > 长老(1) > 亲传(2) > 内门(3) > 外门(4)
        """
        op_position = self._get_position(operator, sect)
        return op_position.value <= required.value

    def _is_member_of_sect(self, player: Player, sect: Sect) -> bool:
        """检查玩家是否属于该宗门"""
        return player.sect_id == sect.sect_id

    def _validate_sect_name(self, name: str) -> Tuple[bool, str]:
        """验证宗门名称"""
        if len(name) < self.SECT_NAME_MIN_LENGTH or len(name) > self.SECT_NAME_MAX_LENGTH:
            return False, f"宗门名称长度需在{self.SECT_NAME_MIN_LENGTH}-{self.SECT_NAME_MAX_LENGTH}字之间"

        for forbidden in self.SECT_NAME_FORBIDDEN:
            if forbidden.lower() in name.lower():
                return False, "宗门名称包含禁用词汇"

        return True, ""

    def _add_contribution(self, player: Player, amount: int) -> None:
        """
        增加玩家宗门贡献度
        兼容旧数据（如果字段不存在则忽略）
        """
        try:
            if not hasattr(player, 'sect_contribution'):
                # 如果 Player 模型没有该字段，尝试动态添加
                setattr(player, 'sect_contribution', 0)
            player.sect_contribution = getattr(player, 'sect_contribution', 0) + amount
        except AttributeError:
            # 如果无法添加，记录日志但不阻止操作
            # 这种情况下贡献度只记录到宗门，不记录到玩家
            pass

    def _get_contribution(self, player: Player) -> int:
        """获取玩家宗门贡献度"""
        try:
            return getattr(player, 'sect_contribution', 0)
        except AttributeError:
            return 0

    # ==================== 宗门管理 ====================

    def create_sect(
        self,
        user_id: str,
        sect_name: str,
        required_stone: int = None,
        required_level: int = None
    ) -> Tuple[bool, str]:
        """
        创建宗门

        Args:
            user_id: 用户ID
            sect_name: 宗门名称
            required_stone: 需求灵石（默认使用常量）
            required_level: 需求境界等级（默认使用常量）

        Returns:
            (是否成功, 消息)
        """
        if required_stone is None:
            required_stone = self.SECT_CREATE_REQUIRED_STONE
        if required_level is None:
            required_level = self.SECT_CREATE_REQUIRED_LEVEL

        # 1. 获取玩家
        player = self._get_player(user_id)

        # 2. 检查是否已有宗门
        if player.sect_id and player.sect_id != 0:
            raise BusinessException("你已经加入了宗门，无法创建新宗门")

        # 3. 检查境界
        if player.level_index < required_level:
            raise BusinessException(f"创建宗门需要达到境界等级 {required_level}")

        # 4. 检查灵石
        if player.gold < required_stone:
            raise BusinessException(f"创建宗门需要 {required_stone} 灵石")

        # 5. 验证宗门名称
        valid, error = self._validate_sect_name(sect_name)
        if not valid:
            raise BusinessException(error)

        # 6. 检查宗门名称是否重复
        existing_sect = self.sect_repo.get_by_name(sect_name)
        if existing_sect:
            raise BusinessException(f"宗门名称『{sect_name}』已被使用")

        # 7. 扣除灵石（持久化）
        player.gold -= required_stone
        self.player_repo.save(player)

        # 8. 创建宗门
        new_sect = Sect(
            sect_id=0,
            name=sect_name,
            leader_id=user_id,
            scale=self.SECT_INITIAL_SCALE,
            funds=0,
            materials=self.SECT_INITIAL_MATERIALS,
            elixir_room_level=0,
            created_at=int(time.time())
        )
        sect_id = self.sect_repo.create(new_sect)

        # 9. 更新玩家宗门信息
        self.sect_repo.update_player_sect(user_id, sect_id, SectPosition.LEADER)

        # 10. 重新加载玩家以刷新状态
        player = self._get_player(user_id)

        return True, f"✨ 恭喜！你成功创建了宗门『{sect_name}』，成为一代宗主！"

    def join_sect(self, user_id: str, sect_name: str) -> Tuple[bool, str]:
        """
        加入宗门（无条件加入）
        """
        # 1. 获取玩家
        player = self._get_player(user_id)

        # 2. 检查是否已有宗门
        if player.sect_id and player.sect_id != 0:
            raise BusinessException("你已经加入了宗门！请先退出当前宗门")

        # 3. 查找宗门
        sect = self.sect_repo.get_by_name(sect_name)
        if not sect:
            raise BusinessException(f"未找到宗门『{sect_name}』")

        # 4. 检查宗门是否已满
        member_count = self.sect_repo.get_member_count(sect.sect_id)
        if not sect.can_accept_members(member_count, self.SECT_MAX_MEMBERS):
            raise BusinessException(f"宗门成员已满（上限{self.SECT_MAX_MEMBERS}人）")

        # 5. 加入宗门（默认为外门弟子）
        position = (
            SectPosition.LEADER
            if str(sect.leader_id) == str(user_id)
            else SectPosition.OUTER_DISCIPLE
        )
        self.sect_repo.update_player_sect(user_id, sect.sect_id, position)

        # 6. 重新加载玩家以刷新状态
        player = self._get_player(user_id)

        return True, f"✨ 你成功加入了宗门『{sect.name}』，成为外门弟子！"

    def leave_sect(self, user_id: str) -> Tuple[bool, str]:
        """
        退出宗门
        如果是宗主且宗门只剩一人，允许解散
        """
        # 1. 获取玩家及其宗门
        player, sect = self._get_player_sect(user_id)

        # 2. 检查是否为宗主
        if player.user_id == sect.leader_id:
            # 检查宗门是否只有宗主一人
            member_count = self.sect_repo.get_member_count(sect.sect_id)
            if member_count > 1:
                raise BusinessException("宗主无法直接退出宗门！请先传位或解散宗门")
            # 只有宗主一人，自动解散
            sect_name = sect.name
            self.sect_repo.delete(sect.sect_id)
            self.sect_repo.update_player_sect(user_id, 0, SectPosition.OUTER_DISCIPLE)
            return True, f"✨ 宗门『{sect_name}』已解散（仅剩宗主一人）"

        # 3. 普通成员退出
        sect_name = sect.name
        self.sect_repo.update_player_sect(user_id, 0, SectPosition.OUTER_DISCIPLE)

        return True, f"✨ 你已退出宗门『{sect_name}』！"

    def disband_sect(self, user_id: str) -> Tuple[bool, str]:
        """
        解散宗门（仅限宗主）
        """
        # 1. 获取玩家及其宗门
        player, sect = self._get_player_sect(user_id)

        # 2. 检查是否为宗主
        if player.user_id != sect.leader_id:
            raise BusinessException("只有宗主才能解散宗门")

        # 3. 检查宗门是否还有其他成员（仅提醒，不阻止）
        member_count = self.sect_repo.get_member_count(sect.sect_id)
        sect_name = sect.name

        # 4. 获取所有成员并清空他们的宗门信息
        members = self.sect_repo.get_members(sect.sect_id)
        for member in members:
            self.sect_repo.update_player_sect(member.user_id, 0, SectPosition.OUTER_DISCIPLE)

        # 5. 删除宗门
        self.sect_repo.delete(sect.sect_id)

        return True, f"✨ 宗门『{sect_name}』已解散！{member_count}名成员已恢复自由身。"

    # ==================== 宗门捐献 ====================

    def donate_to_sect(self, user_id: str, stone_amount: int) -> Tuple[bool, str]:
        """
        宗门捐献
        1灵石 = 10建设度 + 1贡献度
        """
        # 1. 获取玩家及其宗门
        player, sect = self._get_player_sect(user_id)

        # 2. 验证数量
        if stone_amount <= 0:
            raise BusinessException("捐献数量必须大于0")

        if player.gold < stone_amount:
            raise BusinessException(f"你的灵石不足！当前拥有 {player.gold} 灵石")

        # 3. 扣除灵石
        player.gold -= stone_amount
        self.player_repo.save(player)

        # 4. 更新宗门
        scale_gained = sect.add_donation(stone_amount)
        self.sect_repo.update(sect)

        # 5. 记录玩家贡献度
        contribution_gained = stone_amount  # 1:1
        self._add_contribution(player, contribution_gained)
        self.player_repo.save(player)

        return True, (
            f"✨ 捐献成功！\n"
            f"消耗 {stone_amount} 灵石\n"
            f"宗门获得 {scale_gained} 建设度\n"
            f"获得 {contribution_gained} 贡献度"
        )

    # ==================== 宗门任务 ====================

    def perform_sect_task(self, user_id: str) -> Tuple[bool, str]:
        """
        执行宗门任务（1小时冷却）
        奖励：10-30贡献度，宗门资材+贡献度*10
        """
        # 1. 获取玩家及其宗门
        player, sect = self._get_player_sect(user_id)

        # 2. 检查冷却（使用玩家数据存储）
        current_time = int(time.time())
        last_task_time = getattr(player, 'sect_task_time', 0)

        if last_task_time > 0:
            elapsed = current_time - last_task_time
            if elapsed < self.TASK_COOLDOWN_SECONDS:
                remaining = self.TASK_COOLDOWN_SECONDS - elapsed
                remaining_minutes = remaining // 60
                raise BusinessException(f"宗门任务冷却中！还需 {remaining_minutes} 分钟")

        # 3. 执行任务
        contribution_gain = random.randint(10, 30)
        materials_gain = contribution_gain * 10

        # 4. 更新宗门资材
        sect.materials += materials_gain
        self.sect_repo.update(sect)

        # 5. 记录玩家贡献度和任务时间
        self._add_contribution(player, contribution_gain)
        player.sect_task_time = current_time
        self.player_repo.save(player)

        return True, (
            f"✨ 完成宗门任务！\n"
            f"获得贡献：{contribution_gain}\n"
            f"宗门资材：+{materials_gain}"
        )

    # ==================== 宗门信息 ====================

    def get_sect_info(self, user_id: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        获取宗门信息
        """
        # 1. 获取玩家及其宗门
        player, sect = self._get_player_sect(user_id)

        # 2. 获取成员数量
        member_count = self.sect_repo.get_member_count(sect.sect_id)

        # 3. 获取职位（使用 leader_id 反推）
        position = self._get_position(player, sect)

        # 4. 获取宗主信息
        owner = self.player_repo.get_by_id(sect.leader_id)
        owner_name = owner.nickname if owner and owner.nickname else sect.leader_id

        # 5. 获取成员列表（前10人）
        members = self.sect_repo.get_members(sect.sect_id)
        member_list = []
        for m in members[:10]:
            p = self.player_repo.get_by_id(m.user_id)
            member_list.append({
                "name": p.nickname if p and p.nickname else m.user_id,
                "position": m.position.display_name,
                "contribution": self._get_contribution(p) if p else 0
            })

        # 6. 构建消息
        info_msg = f"""🏛️ 宗门信息
━━━━━━━━━━━━━━━

宗门名称：{sect.name}
宗主：{owner_name}
建设度：{sect.scale}
宗门灵石：{sect.funds}
宗门资材：{sect.materials}
丹房等级：{sect.elixir_room_level}
成员数量：{member_count}人

你的职位：{position.display_name}
你的贡献：{self._get_contribution(player)}"""

        # 添加成员列表
        if member_list:
            info_msg += "\n\n📋 成员列表（前10人）："
            for idx, m in enumerate(member_list, 1):
                info_msg += f"\n  {idx}. {m['name']}（{m['position']}）贡献：{m['contribution']}"

        sect_data = {
            "sect": sect,
            "player_position": position,
            "member_count": member_count,
            "members": member_list
        }

        return True, info_msg, sect_data

    def list_all_sects(self, limit: int = 10) -> Tuple[bool, str]:
        """
        获取所有宗门列表（按建设度排序）
        """
        sects = self.sect_repo.get_all(limit=limit)

        if not sects:
            return False, "❌ 当前还没有任何宗门！"

        lines = ["🏛️ 宗门列表", "━━━━━━━━━━━━━━━", ""]

        for idx, sect in enumerate(sects, 1):
            owner = self.player_repo.get_by_id(sect.leader_id)
            owner_name = owner.nickname if owner and owner.nickname else "未知"
            member_count = self.sect_repo.get_member_count(sect.sect_id)

            lines.append(f"{idx}. 【{sect.name}】")
            lines.append(f"   宗主：{owner_name}")
            lines.append(f"   建设度：{sect.scale} | 成员：{member_count}人")
            lines.append("")

        return True, "\n".join(lines)

    def get_member_list(self, user_id: str, limit: int = 20) -> Tuple[bool, str, List[Dict]]:
        """
        获取宗门成员列表
        """
        # 1. 获取玩家及其宗门
        player, sect = self._get_player_sect(user_id)

        # 2. 获取成员列表
        members = self.sect_repo.get_members(sect.sect_id)

        if not members:
            return True, "📋 宗门暂无成员", []

        # 3. 按职位排序（宗主优先）
        position_order = {
            SectPosition.LEADER: 0,
            SectPosition.ELDER: 1,
            SectPosition.CORE_DISCIPLE: 2,
            SectPosition.INNER_DISCIPLE: 3,
            SectPosition.OUTER_DISCIPLE: 4,
        }
        members.sort(key=lambda m: position_order.get(m.position, 999))

        # 4. 构建结果
        result = []
        for m in members[:limit]:
            p = self.player_repo.get_by_id(m.user_id)
            result.append({
                "user_id": m.user_id,
                "name": p.nickname if p and p.nickname else m.user_id,
                "position": m.position.display_name,
                "position_value": m.position.value,
                "contribution": self._get_contribution(p) if p else 0,
                "level": p.level_index if p else 0
            })

        return True, f"📋 宗门『{sect.name}』成员列表（共{len(members)}人）", result

    # ==================== 职位管理 ====================

    def change_position(
        self,
        operator_id: str,
        target_id: str,
        new_position: int
    ) -> Tuple[bool, str]:
        """
        变更宗门职位（仅限宗主）
        """
        # 1. 获取操作者
        operator = self._get_player(operator_id)

        # 2. 检查操作者是否有宗门
        if not operator.sect_id or operator.sect_id == 0:
            raise BusinessException("你还未加入宗门")

        # 3. 获取宗门
        sect = self._get_sect(operator.sect_id)

        # 4. 检查操作者是否为宗主
        if operator.user_id != sect.leader_id:
            raise BusinessException("只有宗主才能变更职位")

        # 5. 检查目标用户
        target = self._get_player(target_id)
        if target.user_id == operator.user_id:
            raise BusinessException("无法变更自己的职位")

        if target.sect_id != sect.sect_id:
            raise BusinessException("目标用户不在你的宗门")

        # 6. 验证新职位
        try:
            new_pos = SectPosition(new_position)
        except ValueError:
            raise BusinessException("无效的职位！职位范围：0（宗主）- 4（外门弟子）")

        if new_pos == SectPosition.LEADER:
            raise BusinessException("无法直接任命宗主！请使用传位功能")

        # 7. 变更职位
        self.sect_repo.update_player_sect(target_id, sect.sect_id, new_pos)

        target_name = target.nickname if target.nickname else target_id

        return True, f"✨ 已将 {target_name} 的职位变更为：{new_pos.display_name}"

    def transfer_ownership(
        self,
        current_owner_id: str,
        new_owner_id: str
    ) -> Tuple[bool, str]:
        """
        宗主传位
        """
        # 1. 获取当前宗主
        current_owner = self._get_player(current_owner_id)

        # 2. 检查是否有宗门
        if not current_owner.sect_id or current_owner.sect_id == 0:
            raise BusinessException("你还未加入宗门")

        # 3. 获取宗门
        sect = self._get_sect(current_owner.sect_id)

        # 4. 检查是否为宗主
        if current_owner.user_id != sect.leader_id:
            raise BusinessException("你不是宗主")

        # 5. 检查新宗主
        new_owner = self._get_player(new_owner_id)
        if new_owner.user_id == current_owner.user_id:
            raise BusinessException("无法传位给自己")

        if new_owner.sect_id != sect.sect_id:
            raise BusinessException("目标用户不在你的宗门")

        # 6. 执行传位（事务性操作）
        # 先更新宗门 leader_id
        sect.leader_id = new_owner_id
        self.sect_repo.update(sect)

        # 再更新职位
        self.sect_repo.update_player_sect(new_owner_id, sect.sect_id, SectPosition.LEADER)
        self.sect_repo.update_player_sect(current_owner_id, sect.sect_id, SectPosition.ELDER)

        new_owner_name = new_owner.nickname if new_owner.nickname else new_owner_id

        return True, f"✨ 宗主之位已传给 {new_owner_name}！你现在是长老。"

    # ==================== 成员管理 ====================

    def kick_member(self, operator_id: str, target_id: str) -> Tuple[bool, str]:
        """
        踢出宗门成员
        - 宗主可踢出任何人（除自己）
        - 长老只能踢外门弟子
        """
        # 1. 获取操作者
        operator = self._get_player(operator_id)

        # 2. 检查操作者是否有宗门
        if not operator.sect_id or operator.sect_id == 0:
            raise BusinessException("你还未加入宗门")

        # 3. 获取宗门
        sect = self._get_sect(operator.sect_id)

        # 4. 检查操作者权限
        operator_pos = self._get_position(operator, sect)

        if operator_pos not in [SectPosition.LEADER, SectPosition.ELDER]:
            raise BusinessException("只有宗主和长老才能踢出成员")

        # 5. 检查目标用户
        target = self._get_player(target_id)
        if target.user_id == operator.user_id:
            raise BusinessException("无法踢出自己")

        if target.sect_id != sect.sect_id:
            raise BusinessException("目标用户不在你的宗门")

        # 6. 检查目标职位
        target_pos = self._get_position(target, sect)

        # 宗主不能被踢
        if target_pos == SectPosition.LEADER:
            raise BusinessException("无法踢出宗主")

        # 长老只能踢外门弟子
        if operator_pos == SectPosition.ELDER and target_pos != SectPosition.OUTER_DISCIPLE:
            raise BusinessException("长老只能踢出外门弟子")

        # 7. 执行踢出
        target_name = target.nickname if target.nickname else target_id
        self.sect_repo.update_player_sect(target_id, 0, SectPosition.OUTER_DISCIPLE)

        return True, f"✨ 已将 {target_name} 踢出宗门！"
