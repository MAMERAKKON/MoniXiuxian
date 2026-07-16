"""排行榜命令处理器"""
from astrbot.api.event import AstrMessageEvent

from ...application.services.ranking_service import RankingService
from ...infrastructure.repositories.player_repo import PlayerRepository


class RankingHandler:
    """排行榜命令处理器"""
    
    def __init__(self, ranking_service: RankingService, player_repo: PlayerRepository):
        self.ranking_service = ranking_service
        self.player_repo = player_repo
    
    async def handle_rank_level(self, event: AstrMessageEvent):
        """境界排行"""
        success, msg = self.ranking_service.get_level_ranking()
        yield event.plain_result(msg)
    
    async def handle_rank_power(self, event: AstrMessageEvent):
        """战力排行"""
        success, msg = self.ranking_service.get_power_ranking()
        yield event.plain_result(msg)
    
    async def handle_rank_wealth(self, event: AstrMessageEvent):
        """财富排行"""
        success, msg = self.ranking_service.get_wealth_ranking()
        yield event.plain_result(msg)
    
    async def handle_rank_sect(self, event: AstrMessageEvent):
        """宗门排行"""
        success, msg = self.ranking_service.get_sect_ranking()
        yield event.plain_result(msg)
    
    async def handle_rank_deposit(self, event: AstrMessageEvent):
        """存款排行"""
        success, msg = self.ranking_service.get_deposit_ranking()
        yield event.plain_result(msg)
    
    async def handle_rank_sect_contribution(self, event: AstrMessageEvent):
        """宗门贡献排行（当前所在宗门）"""
        user_id = str(event.get_sender_id())
        player = self.player_repo.get_player(user_id)
        
        if not player:
            yield event.plain_result("❌ 你还未踏入修仙之路，请先发送「我要修仙」开始修行。")
            return
        
        if not player.sect_id or player.sect_id == "":
            yield event.plain_result("❌ 你尚未加入任何宗门，无法查看宗门贡献排行。")
            return
        
        success, msg = self.ranking_service.get_contribution_ranking(player.sect_id)
        yield event.plain_result(msg)
