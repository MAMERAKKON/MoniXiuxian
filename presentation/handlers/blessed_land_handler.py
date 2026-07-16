"""洞天福地命令处理器"""
from typing import AsyncGenerator
from astrbot.api.event import AstrMessageEvent

from ...application.services.blessed_land_service import BlessedLandService
from ...core.exceptions import GameException


class BlessedLandHandler:
    """洞天福地命令处理器"""
    
    def __init__(self, blessed_land_service: BlessedLandService):
        self.blessed_land_service = blessed_land_service
    
    async def handle_blessed_land_info(self, event: AstrMessageEvent) -> AsyncGenerator:
        """处理查看洞天信息命令"""
        try:
            user_id = event.get_sender_id()
            
            try:
                # 获取洞天信息
                info = self.blessed_land_service.get_blessed_land_info(user_id)
                
                msg_lines = [
                    f"🏔️ {info.land_name} (Lv.{info.level})",
                    "━━━━━━━━━━━━━━━",
                    f"修炼加成：+{info.exp_bonus:.1%}",
                    f"每小时产出：{info.gold_per_hour} 灵石",
                    "━━━━━━━━━━━━━━━",
                    f"待收取：约 {info.pending_gold:,} 灵石",
                    "━━━━━━━━━━━━━━━",
                ]
                
                if info.can_upgrade:
                    msg_lines.append(f"💡 升级洞天 (费用: {info.upgrade_cost:,}灵石) | 洞天收取")
                else:
                    msg_lines.append(f"💡 洞天收取 | 已达最高等级({info.max_level})")
                
                yield event.plain_result("\n".join(msg_lines))
                
            except GameException as e:
                if "你还没有洞天" in str(e):
                    # 显示购买信息
                    msg = (
                        "🏔️ 洞天福地\n"
                        "━━━━━━━━━━━━━━━\n"
                        "你还没有洞天！\n\n"
                        "可购买的洞天：\n"
                        "  1. 小洞天 - 10,000灵石\n"
                        "  2. 中洞天 - 50,000灵石\n"
                        "  3. 大洞天 - 200,000灵石\n"
                        "  4. 福地 - 500,000灵石\n"
                        "  5. 洞天福地 - 1,000,000灵石\n\n"
                        "💡 使用 购买洞天 <编号>"
                    )
                    yield event.plain_result(msg)
                else:
                    raise
            
        except GameException as e:
            yield event.plain_result(str(e))
        except Exception as e:
            yield event.plain_result(f"查询洞天信息失败：{e}")
    
    async def handle_purchase(self, event: AstrMessageEvent, land_type: str = "") -> AsyncGenerator:
        """处理购买洞天命令"""
        try:
            user_id = event.get_sender_id()
            
            # 解析洞天类型
            if not land_type:
                yield event.plain_result("❌ 请输入洞天类型，例如：购买洞天 1")
                return
            
            try:
                land_type_int = int(land_type)
            except ValueError:
                yield event.plain_result("❌ 洞天类型必须是数字（1-5）")
                return
            
            result = self.blessed_land_service.purchase_blessed_land(user_id, land_type_int)
            yield event.plain_result(result)
            
        except GameException as e:
            yield event.plain_result(str(e))
        except Exception as e:
            yield event.plain_result(f"购买洞天失败：{e}")
    
    async def handle_upgrade(self, event: AstrMessageEvent) -> AsyncGenerator:
        """处理升级洞天命令"""
        try:
            user_id = event.get_sender_id()
            result = self.blessed_land_service.upgrade_blessed_land(user_id)
            yield event.plain_result(result)
            
        except GameException as e:
            yield event.plain_result(str(e))
        except Exception as e:
            yield event.plain_result(f"升级洞天失败：{e}")
    
    async def handle_collect(self, event: AstrMessageEvent) -> AsyncGenerator:
        """处理收取洞天产出命令"""
        try:
            user_id = event.get_sender_id()
            result = self.blessed_land_service.collect_income(user_id)
            yield event.plain_result(result)
            
        except GameException as e:
            yield event.plain_result(str(e))
        except Exception as e:
            yield event.plain_result(f"收取洞天产出失败：{e}")
