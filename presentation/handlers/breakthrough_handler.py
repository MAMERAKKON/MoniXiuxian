"""突破命令处理器"""
from astrbot.api.event import AstrMessageEvent

from ...application.services.breakthrough_service import BreakthroughService
from ...core.exceptions import InvalidStateException
from ...domain.enums import CultivationType
from ..decorators import require_player


class BreakthroughHandler:
    """突破命令处理器"""
    
    def __init__(self, breakthrough_service: BreakthroughService, player_service):
        self.breakthrough_service = breakthrough_service
        self.player_service = player_service
    
    @require_player
    async def handle_breakthrough_info(self, event: AstrMessageEvent, player):
        """
        处理突破信息命令
        
        Args:
            event: 消息事件
            player: 玩家对象（由装饰器注入）
        """
        try:
            display_name = event.get_sender_name()
            
            # 获取突破信息
            info = self.breakthrough_service.get_breakthrough_info(player)
            
            if not info["can_breakthrough"] and "最高境界" in info.get("message", ""):
                yield event.plain_result(info["message"])
                return
            
            # 构建信息显示
            exp_status = "✅ 满足" if info["exp_satisfied"] else "❌ 不足"
            
            message = (
                f"=== {display_name} 的突破信息 ===\n"
                f"当前境界：{info['current_level']}\n"
                f"下一境界：{info['next_level']}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"【突破条件】\n"
                f"所需修为：{info['required_exp']:,}\n"
                f"当前修为：{info['current_exp']:,}\n"
                f"修为状态：{exp_status}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"【突破成功率】\n"
                f"基础成功率：{info['base_success_rate']:.1%}\n"
                f"丹药突破加成：+{info.get('pill_bonus_rate', 0.0):.1%}\n"
                f"当前预计成功率：{info.get('preview_success_rate', info['base_success_rate']):.1%}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"【突破说明】\n"
                f"• 使用命令：突破\n"
            )
            
            if info["cultivation_type"] == CultivationType.PHYSICAL.value:
                message += (
                    f"• 突破成功：境界提升，肉身更强\n"
                    f"• 突破失败：损失10%修为，有概率死亡\n"
                    f"• 死亡后：所有数据清除，需重新入仙途\n"
                )
            else:
                message += (
                    f"• 突破成功：境界提升，实力大增\n"
                    f"• 突破失败：损失10%修为，有概率死亡\n"
                    f"• 死亡后：所有数据清除，需重新入仙途\n"
                )
            
            message += "=" * 28
            
            yield event.plain_result(message)
            
        except Exception as e:
            yield event.plain_result(f"❌ 查询突破信息失败：{str(e)}")
    
    @require_player
    async def handle_breakthrough(self, event: AstrMessageEvent, player, pill_name: str = ""):
        """
        处理突破命令
        
        Args:
            event: 消息事件
            player: 玩家对象（由装饰器注入）
            pill_name: 破境丹名称（可选）
        """
        try:
            # 清理丹药名称
            pill_name_clean = pill_name.strip() if pill_name else ""
            
            if pill_name_clean:
                yield event.plain_result(f"使用【{pill_name_clean}】进行突破...")
            else:
                yield event.plain_result("开始尝试突破...")
            
            # 执行突破，传递丹药名称
            result = self.breakthrough_service.execute_breakthrough(player, pill_name_clean if pill_name_clean else None)
            
            if result.success:
                # 突破成功
                gains = result.attribute_gains
                
                # 根据修炼类型生成不同的成功消息
                if player.cultivation_type == CultivationType.PHYSICAL.value:
                    message = (
                        f"✨ 突破成功！✨\n"
                        f"━━━━━━━━━━━━━━━\n"
                        f"{result.rate_info}\n"
                        f"━━━━━━━━━━━━━━━\n"
                        f"恭喜你从【{result.current_level}】突破至【{result.next_level}】！\n"
                        f"境界提升，肉身更加强横！\n"
                        f"\n【属性增长】\n"
                        f"寿命 +{gains['lifespan']}\n"
                        f"最大{gains['energy_name']} +{gains['energy']}\n"
                        f"物伤 +{gains['physical_damage']}\n"
                        f"物防 +{gains['physical_defense']}\n"
                        f"法防 +{gains['magic_defense']}\n"
                        f"精神力 +{gains['mental_power']}\n"
                        f"\n【当前属性】\n"
                        f"寿命：{player.lifespan}\n"
                        f"最大气血：{player.max_blood_qi}\n"
                        f"物伤：{player.physical_damage}\n"
                        f"物防：{player.physical_defense}\n"
                        f"法防：{player.magic_defense}\n"
                        f"精神力：{player.mental_power}"
                    )
                else:
                    message = (
                        f"✨ 突破成功！✨\n"
                        f"━━━━━━━━━━━━━━━\n"
                        f"{result.rate_info}\n"
                        f"━━━━━━━━━━━━━━━\n"
                        f"恭喜你从【{result.current_level}】突破至【{result.next_level}】！\n"
                        f"境界提升，实力大增！\n"
                        f"\n【属性增长】\n"
                        f"寿命 +{gains['lifespan']}\n"
                        f"最大{gains['energy_name']} +{gains['energy']}\n"
                        f"法伤 +{gains['magic_damage']}\n"
                        f"物伤 +{gains['physical_damage']}\n"
                        f"法防 +{gains['magic_defense']}\n"
                        f"物防 +{gains['physical_defense']}\n"
                        f"精神力 +{gains['mental_power']}\n"
                        f"\n【当前属性】\n"
                        f"寿命：{player.lifespan}\n"
                        f"最大灵气：{player.max_spiritual_qi}\n"
                        f"法伤：{player.magic_damage}\n"
                        f"物伤：{player.physical_damage}\n"
                        f"法防：{player.magic_defense}\n"
                        f"物防：{player.physical_defense}\n"
                        f"精神力：{player.mental_power}"
                    )
                
                yield event.plain_result(message)
            
            elif result.died:
                # 突破失败并死亡
                message = (
                    f"💀 突破失败，走火入魔！💀\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"{result.rate_info}\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"你在突破【{result.next_level}】时走火入魔，但得以保全性命...\n"
                    f"所有修为和灵石化为虚无\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"💡 若想改变灵根，可使用【轮回转世 确认】重新入道\n"
                    f"⚠️ 注意：轮回转世将删除当前角色数据，无法撤回！"
                )
                
                yield event.plain_result(message)
            
            else:
                # 突破失败但未死亡
                message = (
                    f"❌ 突破失败 ❌\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"{result.rate_info}\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"突破【{result.next_level}】失败，但幸运地保住了性命\n"
                    f"修为受损，损失了 {result.exp_loss:,} 点修为\n"
                    f"当前修为：{player.experience:,}\n"
                    f"请继续修炼，再接再厉！"
                )
                
                yield event.plain_result(message)
            
        except InvalidStateException as e:
            yield event.plain_result(f"❌ 当前状态「{e.current_state}」无法突破！")
        except ValueError as e:
            yield event.plain_result(f"❌ {str(e)}")
        except Exception as e:
            yield event.plain_result(f"❌ 突破失败：{str(e)}")
