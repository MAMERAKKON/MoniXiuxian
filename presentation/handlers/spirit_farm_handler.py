"""灵田命令处理器"""
import time
from typing import AsyncGenerator
from astrbot.api.event import AstrMessageEvent

from ...application.services.spirit_farm_service import SpiritFarmService
from ...core.exceptions import GameException


class SpiritFarmHandler:
    """灵田命令处理器"""
    
    def __init__(self, spirit_farm_service: SpiritFarmService):
        self.spirit_farm_service = spirit_farm_service
    
    async def handle_farm_info(self, event: AstrMessageEvent) -> AsyncGenerator:
        """处理查看灵田信息命令"""
        try:
            user_id = event.get_sender_id()
            
            try:
                # 获取灵田信息
                info = self.spirit_farm_service.get_farm_info(user_id)
                
                now = int(time.time())
                lines = [
                    f"🌾 我的灵田 (Lv.{info.level})",
                    "━━━━━━━━━━━━━━━",
                    f"种植格数：{info.used_slots}/{info.max_slots}",
                    ""
                ]
                
                if info.crops:
                    lines.append("【种植中】")
                    for i, crop in enumerate(info.crops, 1):
                        status = crop.get_status(now)
                        lines.append(f"  {i}. {crop.name} - {status}")
                else:
                    lines.append("（空）")
                
                lines.append("")
                if info.can_upgrade:
                    lines.append(f"💡 种植 <灵草名> | 收获 | 升级灵田 (费用: {info.upgrade_cost:,}灵石)")
                else:
                    lines.append("💡 种植 <灵草名> | 收获 | 已达最高等级")
                
                yield event.plain_result("\n".join(lines))
                
            except GameException as e:
                if "你还没有灵田" in str(e):
                    # 显示开垦信息
                    msg = (
                        "🌾 灵田系统\n"
                        "━━━━━━━━━━━━━━━\n"
                        "你还没有灵田！\n"
                        "开垦费用：10,000 灵石\n\n"
                        "💡 使用 开垦灵田"
                    )
                    yield event.plain_result(msg)
                else:
                    raise
            
        except GameException as e:
            yield event.plain_result(str(e))
        except Exception as e:
            yield event.plain_result(f"查询灵田信息失败：{e}")
    
    async def handle_create_farm(self, event: AstrMessageEvent) -> AsyncGenerator:
        """处理开垦灵田命令"""
        try:
            user_id = event.get_sender_id()
            result = self.spirit_farm_service.create_farm(user_id)
            yield event.plain_result(result)
            
        except GameException as e:
            yield event.plain_result(str(e))
        except Exception as e:
            yield event.plain_result(f"开垦灵田失败：{e}")
    
    async def handle_plant(self, event: AstrMessageEvent, herb_name: str = "") -> AsyncGenerator:
        """处理种植命令"""
        try:
            user_id = event.get_sender_id()
            
            # 检查参数
            if not herb_name:
                herbs_list = "、".join(self.spirit_farm_service.SPIRIT_HERBS.keys())
                yield event.plain_result(f"❌ 请输入灵草名称\n可种植：{herbs_list}\n例如：种植 灵草")
                return
            
            result = self.spirit_farm_service.plant_herb(user_id, herb_name)
            yield event.plain_result(result)
            
        except GameException as e:
            yield event.plain_result(str(e))
        except Exception as e:
            yield event.plain_result(f"种植失败：{e}")
    
    async def handle_harvest(self, event: AstrMessageEvent) -> AsyncGenerator:
        """处理收获命令"""
        try:
            user_id = event.get_sender_id()
            result = self.spirit_farm_service.harvest(user_id)
            yield event.plain_result(result)
            
        except GameException as e:
            yield event.plain_result(str(e))
        except Exception as e:
            yield event.plain_result(f"收获失败：{e}")
    
    async def handle_upgrade_farm(self, event: AstrMessageEvent) -> AsyncGenerator:
        """处理升级灵田命令"""
        try:
            user_id = event.get_sender_id()
            result = self.spirit_farm_service.upgrade_farm(user_id)
            yield event.plain_result(result)
            
        except GameException as e:
            yield event.plain_result(str(e))
        except Exception as e:
            yield event.plain_result(f"升级灵田失败：{e}")
