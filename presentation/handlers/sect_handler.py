"""
宗门命令处理器

处理宗门相关的命令。
"""
from typing import AsyncGenerator

from astrbot.api.event import AstrMessageEvent

from ...application.services.sect_service import SectService
from ...core.exceptions import BusinessException
from ..decorators import require_player


class SectHandler:
    """宗门命令处理器"""
    
    def __init__(self, sect_service: SectService, player_service):
        """
        初始化宗门命令处理器
        
        Args:
            sect_service: 宗门服务
            player_service: 玩家服务
        """
        self.sect_service = sect_service
        self.player_service = player_service
    
    @require_player
    async def handle_create_sect(
        self, 
        event: AstrMessageEvent,
        player,
        sect_name: str = ""
    ) -> AsyncGenerator[str, None]:
        """
        处理创建宗门命令
        
        Args:
            event: 消息事件
            sect_name: 宗门名称
            
        Yields:
            响应消息
        """
        user_id = event.get_sender_id()
        
        if not sect_name or sect_name.strip() == "":
            yield event.plain_result("请指定宗门名称，例如：创建宗门 天道宗")
            return
        
        try:
            success, message = self.sect_service.create_sect(
                user_id, 
                sect_name.strip(),
                required_stone=10000,
                required_level=3
            )
            yield event.plain_result(message)
        except BusinessException as e:
            yield event.plain_result(f"❌ {str(e)}")
        except Exception as e:
            yield event.plain_result(f"❌ 系统错误：{str(e)}")
    
    @require_player
    async def handle_join_sect(
        self, 
        event: AstrMessageEvent,
        player,
        sect_name: str = ""
    ) -> AsyncGenerator[str, None]:
        """
        处理加入宗门命令
        
        Args:
            event: 消息事件
            sect_name: 宗门名称
            
        Yields:
            响应消息
        """
        user_id = event.get_sender_id()
        
        if not sect_name or sect_name.strip() == "":
            yield event.plain_result("请指定宗门名称，例如：加入宗门 天道宗")
            return
        
        try:
            success, message = self.sect_service.join_sect(user_id, sect_name.strip())
            yield event.plain_result(message)
        except BusinessException as e:
            yield event.plain_result(f"❌ {str(e)}")
        except Exception as e:
            yield event.plain_result(f"❌ 系统错误：{str(e)}")
    
    @require_player
    async def handle_leave_sect(
        self, 
        event: AstrMessageEvent,
        player
    ) -> AsyncGenerator[str, None]:
        """
        处理退出宗门命令
        
        Args:
            event: 消息事件
            
        Yields:
            响应消息
        """
        user_id = event.get_sender_id()
        
        try:
            success, message = self.sect_service.leave_sect(user_id)
            yield event.plain_result(message)
        except BusinessException as e:
            yield event.plain_result(f"❌ {str(e)}")
        except Exception as e:
            yield event.plain_result(f"❌ 系统错误：{str(e)}")
    
    @require_player
    async def handle_sect_info(
        self, 
        event: AstrMessageEvent,
        player
    ) -> AsyncGenerator[str, None]:
        """
        处理查看宗门信息命令
        
        Args:
            event: 消息事件
            
        Yields:
            响应消息
        """
        user_id = event.get_sender_id()
        
        try:
            success, message, _ = self.sect_service.get_sect_info(user_id)
            yield event.plain_result(message)
        except BusinessException as e:
            yield event.plain_result(f"❌ {str(e)}")
        except Exception as e:
            yield event.plain_result(f"❌ 系统错误：{str(e)}")
    
    async def handle_sect_list(
        self, 
        event: AstrMessageEvent
    ) -> AsyncGenerator[str, None]:
        """
        处理查看宗门列表命令
        
        Args:
            event: 消息事件
            
        Yields:
            响应消息
        """
        try:
            success, message = self.sect_service.list_all_sects(limit=10)
            yield event.plain_result(message)
        except Exception as e:
            yield event.plain_result(f"❌ 系统错误：{str(e)}")
    
    @require_player
    async def handle_donate(
        self, 
        event: AstrMessageEvent,
        player,
        amount: str = ""
    ) -> AsyncGenerator[str, None]:
        """
        处理宗门捐献命令
        
        Args:
            event: 消息事件
            amount: 捐献数量
            
        Yields:
            响应消息
        """
        user_id = event.get_sender_id()
        
        if not amount or amount.strip() == "":
            yield event.plain_result("请指定捐献数量，例如：宗门捐献 1000")
            return
        
        try:
            stone_amount = int(amount.strip())
        except ValueError:
            yield event.plain_result("❌ 捐献数量必须是数字")
            return
        
        try:
            success, message = self.sect_service.donate_to_sect(user_id, stone_amount)
            yield event.plain_result(message)
        except BusinessException as e:
            yield event.plain_result(f"❌ {str(e)}")
        except Exception as e:
            yield event.plain_result(f"❌ 系统错误：{str(e)}")
    
    @require_player
    async def handle_change_position(
        self, 
        event: AstrMessageEvent,
        player,
        args: str = ""
    ) -> AsyncGenerator[str, None]:
        """
        处理变更职位命令
        
        Args:
            event: 消息事件
            args: 参数（目标ID 职位）
            
        Yields:
            响应消息
        """
        user_id = event.get_sender_id()
        
        if not args or args.strip() == "":
            yield event.plain_result(
                "请指定目标和职位，例如：变更职位 @用户 1\n"
                "职位：0=宗主 1=长老 2=亲传弟子 3=内门弟子 4=外门弟子"
            )
            return
        
        # 解析参数
        parts = args.strip().split()
        if len(parts) < 2:
            yield event.plain_result("❌ 参数不足，格式：变更职位 <目标ID> <职位>")
            return
        
        target_id = parts[0]
        try:
            new_position = int(parts[1])
        except ValueError:
            yield event.plain_result("❌ 职位必须是数字（0-4）")
            return
        
        try:
            success, message = self.sect_service.change_position(
                user_id, target_id, new_position
            )
            yield event.plain_result(message)
        except BusinessException as e:
            yield event.plain_result(f"❌ {str(e)}")
        except Exception as e:
            yield event.plain_result(f"❌ 系统错误：{str(e)}")
    
    @require_player
    async def handle_transfer_ownership(
        self, 
        event: AstrMessageEvent,
        player,
        target_id: str = ""
    ) -> AsyncGenerator[str, None]:
        """
        处理宗主传位命令
        
        Args:
            event: 消息事件
            target_id: 目标用户ID
            
        Yields:
            响应消息
        """
        user_id = event.get_sender_id()
        
        if not target_id or target_id.strip() == "":
            yield event.plain_result("请指定传位目标，例如：宗主传位 @用户")
            return
        
        try:
            success, message = self.sect_service.transfer_ownership(
                user_id, target_id.strip()
            )
            yield event.plain_result(message)
        except BusinessException as e:
            yield event.plain_result(f"❌ {str(e)}")
        except Exception as e:
            yield event.plain_result(f"❌ 系统错误：{str(e)}")
    
    @require_player
    async def handle_kick_member(
        self, 
        event: AstrMessageEvent,
        player,
        target_id: str = ""
    ) -> AsyncGenerator[str, None]:
        """
        处理踢出成员命令
        
        Args:
            event: 消息事件
            target_id: 目标用户ID
            
        Yields:
            响应消息
        """
        user_id = event.get_sender_id()
        
        if not target_id or target_id.strip() == "":
            yield event.plain_result("请指定要踢出的成员，例如：踢出成员 @用户")
            return
        
        try:
            success, message = self.sect_service.kick_member(
                user_id, target_id.strip()
            )
            yield event.plain_result(message)
        except BusinessException as e:
            yield event.plain_result(f"❌ {str(e)}")
        except Exception as e:
            yield event.plain_result(f"❌ 系统错误：{str(e)}")

    @require_player
    async def handle_sect_task(
        self, 
        event: AstrMessageEvent,
        player
    ) -> AsyncGenerator[str, None]:
        """
        处理宗门任务命令
        
        Args:
            event: 消息事件
            
        Yields:
            响应消息
        """
        user_id = event.get_sender_id()
        
        try:
            success, message = self.sect_service.perform_sect_task(user_id)
            yield event.plain_result(message)
        except BusinessException as e:
            yield event.plain_result(f"❌ {str(e)}")
        except Exception as e:
            yield event.plain_result(f"❌ 系统错误：{str(e)}")
            
    @require_player
    async def handle_disband_sect(
        self,
        event: AstrMessageEvent,
        player
    ) -> AsyncGenerator[str, None]:
        """
        处理解散宗门命令（仅限宗主）
        
        Args:
            event: 消息事件
            
        Yields:
            响应消息
        """
        user_id = event.get_sender_id()
        
        try:
            success, message = self.sect_service.disband_sect(user_id)
            yield event.plain_result(message)
        except BusinessException as e:
            yield event.plain_result(f"❌ {str(e)}")
        except Exception as e:
            yield event.plain_result(f"❌ 系统错误：{str(e)}")
