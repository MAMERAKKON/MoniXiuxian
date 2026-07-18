"""秘境命令处理器"""
from typing import AsyncGenerator
from astrbot.api.event import AstrMessageEvent

from ...application.services.rift_service import RiftService
from ...core.exceptions import GameException


class RiftHandler:
    """秘境命令处理器"""
    
    def __init__(self, rift_service: RiftService):
        self.rift_service = rift_service
    
    async def handle_rift_list(self, event: AstrMessageEvent) -> AsyncGenerator:
        """处理秘境列表命令"""
        try:
            rifts = self.rift_service.get_all_rifts()
            
            if not rifts:
                yield event.plain_result("暂无可用的秘境")
                return
            
            # 获取玩家境界（用于显示死亡率）
            user_id = event.get_sender_id()
            player = self.rift_service.player_repo.get_player(user_id)
            player_level = player.level_index if player else 0
            
            # 构建秘境列表
            lines = ["🌌 秘境列表", "━━━━━━━━━━━━━━━"]
            
            # 按等级分组
            rifts_by_level = {}
            for rift in rifts:
                level = rift.rift_level
                if level not in rifts_by_level:
                    rifts_by_level[level] = []
                rifts_by_level[level].append(rift)
            
            # 显示秘境
            level_names = {1: "低级秘境", 2: "中级秘境", 3: "高级秘境"}
            for level in sorted(rifts_by_level.keys()):
                lines.append(f"\n【{level_names.get(level, f'等级{level}')}】")
                for rift in rifts_by_level[level]:
                    # 从 rift_service 的 config_manager 获取境界名称
                    config_mgr = self.rift_service.config_manager
                    level_data = config_mgr.level_data
                    required_level_name = level_data[rift.required_level].get("name", f"境界{rift.required_level}") if rift.required_level < len(level_data) else f"境界{rift.required_level}"
                    recommended_level_name = level_data[rift.recommended_level].get("name", f"境界{rift.recommended_level}") if rift.recommended_level < len(level_data) else f"境界{rift.recommended_level}"
                    
                    # 计算当前玩家的死亡率
                    death_rate = self.rift_service._calculate_death_rate(player_level, rift) if player else 0
                    death_rate_str = f"{death_rate:.1f}%" if death_rate > 0 else "0%"
                    
                    gold_min = int(rift.gold_reward_min * self.rift_service.RIFT_GOLD_REWARD_MULTIPLIER)
                    gold_max = int(rift.gold_reward_max * self.rift_service.RIFT_GOLD_REWARD_MULTIPLIER)
                    lines.append(
                        f"· ID {rift.rift_id}: {rift.rift_name}"
                        f"\n  - 最低境界：{required_level_name}"
                        f"\n  - 推荐境界：{recommended_level_name}"
                        f"\n  - 你的死亡率：{death_rate_str}"
                        f"\n  - 修为奖励：{rift.exp_reward_min:,} ~ {rift.exp_reward_max:,}"
                        f"\n  - 灵石奖励：{gold_min:,} ~ {gold_max:,}"
                    )
                    if rift.description:
                        lines.append(f"  - 说明：{rift.description}")
            
            lines.append(
                "\n💡 指令用法：\n"
                "  /探索秘境 <ID> → 开始探索\n"
                "  /完成探索 → 领取奖励\n"
                "  /退出秘境 → 放弃探索"
            )
            lines.append("━━━━━━━━━━━━━━━")
            
            yield event.plain_result("\n".join(lines))
            
        except GameException as e:
            yield event.plain_result(str(e))
        except Exception as e:
            yield event.plain_result(f"查询秘境列表失败：{e}")
    
    async def handle_enter_rift(self, event: AstrMessageEvent, rift_id: str = "") -> AsyncGenerator:
        """处理探索秘境命令"""
        try:
            user_id = event.get_sender_id()
            
            if not rift_id:
                yield event.plain_result("请指定秘境ID\n使用【秘境列表】查看可用秘境")
                return
            
            # 转换为整数
            try:
                rift_id_int = int(rift_id)
            except ValueError:
                yield event.plain_result("秘境ID必须是数字")
                return
            
            result = self.rift_service.enter_rift(user_id, rift_id_int)
            yield event.plain_result(result)
            
        except GameException as e:
            yield event.plain_result(str(e))
        except Exception as e:
            yield event.plain_result(f"进入秘境失败：{e}")
    
    async def handle_finish_exploration(self, event: AstrMessageEvent) -> AsyncGenerator:
        """处理完成探索命令"""
        try:
            user_id = event.get_sender_id()
            result = self.rift_service.finish_exploration(user_id)
            
            # 直接从 rift_service 的 player_repo 获取玩家信息
            player = self.rift_service.player_repo.get_player(user_id)
            
            # 检查是否死亡
            if result.death_occurred:
                lines = [
                    f"💀 秘境探索失败",
                    "━━━━━━━━━━━━━━━",
                    f"秘境：{result.rift_name}\n",
                    f"⚠️ {result.event_description}\n"
                ]
                
                if result.death_penalty:
                    lines.append(f"💔 死亡惩罚：")
                    lines.append(f"  · 损失修为：-{result.death_penalty['exp_lost']:,}")
                    lines.append(f"  · 损失灵石：-{result.death_penalty['gold_lost']:,}")
                    lines.append("  · 下次成功完成同一秘境可取回本次全部损失")
                    lines.append("  · 若取回前再次死于秘境，本次损失将被新记录覆盖")
                
                lines.append("\n━━━━━━━━━━━━━━━")
                if player:
                    lines.append(f"当前修为：{player.experience:,}")
                    lines.append(f"当前灵石：{player.gold:,}")
                
                yield event.plain_result("\n".join(lines))
                return
            
            # 构建成功结果消息
            lines = [
                f"🌌 秘境探索完成",
                "━━━━━━━━━━━━━━━",
                f"秘境：{result.rift_name}\n"
            ]
            
            # 事件描述
            if result.event_description:
                lines.append(f"{result.event_description}\n")
            
            # 奖励信息
            lines.append(f"获得修为：+{result.exp_gained:,}")
            lines.append(f"获得灵石：+{result.gold_gained:,}")

            if result.recovered_exp > 0 or result.recovered_gold > 0:
                lines.append("\n🧭 寻回上次死亡遗失：")
                lines.append(f"  · 修为：+{result.recovered_exp:,}")
                lines.append(f"  · 灵石：+{result.recovered_gold:,}")
            
            # 物品
            if result.items_gained:
                item_lines = []
                for item_name, count in result.items_gained:
                    item_lines.append(f"  · {item_name} x{count}")
                lines.append(f"\n📦 获得物品：\n" + "\n".join(item_lines))
            
            # 当前状态
            lines.append("\n━━━━━━━━━━━━━━━")
            if player:
                lines.append(f"当前修为：{player.experience:,}")
                lines.append(f"当前灵石：{player.gold:,}")
            
            yield event.plain_result("\n".join(lines))
            
        except GameException as e:
            yield event.plain_result(str(e))
        except Exception as e:
            yield event.plain_result(f"完成探索失败：{e}")
    
    async def handle_exit_rift(self, event: AstrMessageEvent) -> AsyncGenerator:
        """处理退出秘境命令"""
        try:
            user_id = event.get_sender_id()
            result = self.rift_service.exit_rift(user_id)
            yield event.plain_result(result)
            
        except GameException as e:
            yield event.plain_result(str(e))
        except Exception as e:
            yield event.plain_result(f"退出秘境失败：{e}")
