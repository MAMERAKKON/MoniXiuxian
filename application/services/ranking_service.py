"""排行榜系统服务"""
from typing import Tuple, List

from ...infrastructure.repositories.player_repo import PlayerRepository
from ...infrastructure.repositories.sect_repo import SectRepository
from ...infrastructure.repositories.bank_repo import BankRepository
from ...core.config import ConfigManager


class RankingService:
    """排行榜服务"""
    
    def __init__(
        self,
        player_repo: PlayerRepository,
        sect_repo: SectRepository,
        bank_repo: BankRepository,
        config_manager: ConfigManager
    ):
        self.player_repo = player_repo
        self.sect_repo = sect_repo
        self.bank_repo = bank_repo
        self.config_manager = config_manager
    
    def get_level_ranking(self, limit: int = 10) -> Tuple[bool, str]:
        """境界排行榜"""
        all_players = self.player_repo.get_all_players()
        
        if not all_players:
            return False, "❌ 暂无数据！"
        
        # 按修为排序
        sorted_players = sorted(all_players, key=lambda p: p.experience, reverse=True)[:limit]
        
        msg = "📊 境界排行榜\n"
        msg += "━━━━━━━━━━━━━━━\n"
        
        for idx, player in enumerate(sorted_players, 1):
            name = player.nickname or player.user_id[:8]
            # 获取修炼类型的值（枚举转字符串）
            cult_type = player.cultivation_type.value if hasattr(player.cultivation_type, 'value') else str(player.cultivation_type)
            level_name = self._get_level_name(player.level_index, cult_type)
            msg += f"{idx}. {name}\n"
            msg += f"   境界：{level_name} | 修为：{player.experience:,}\n\n"
        
        return True, msg
    
    def get_power_ranking(self, limit: int = 10) -> Tuple[bool, str]:
        """战力排行榜"""
        all_players = self.player_repo.get_all_players()
        
        if not all_players:
            return False, "❌ 暂无数据！"
        
        # 计算战力
        player_power = []
        for player in all_players:
            # 战力 = 物伤 + 法伤 + 物防 + 法防 + 精神力/10
            combat_power = (
                player.physical_damage + player.magic_damage +
                player.physical_defense + player.magic_defense +
                player.mental_power // 10
            )
            player_power.append((player, combat_power))
        
        # 按战力排序
        sorted_players = sorted(player_power, key=lambda x: x[1], reverse=True)[:limit]
        
        msg = "📊 战力排行榜\n"
        msg += "━━━━━━━━━━━━━━━\n"
        
        for idx, (player, power) in enumerate(sorted_players, 1):
            name = player.nickname or player.user_id[:8]
            # 获取修炼类型的值
            cult_type = player.cultivation_type.value if hasattr(player.cultivation_type, 'value') else str(player.cultivation_type)
            # 显示主要攻击属性
            if cult_type == "体修":
                main_atk = player.physical_damage
                atk_label = "物伤"
            else:
                main_atk = player.magic_damage
                atk_label = "法伤"
            msg += f"{idx}. {name}\n"
            msg += f"   战力：{power:,} | {atk_label}：{main_atk:,}\n\n"
        
        return True, msg
    
    def get_wealth_ranking(self, limit: int = 10) -> Tuple[bool, str]:
        """财富排行榜（灵石）"""
        all_players = self.player_repo.get_all_players()
        
        if not all_players:
            return False, "❌ 暂无数据！"
        
        # 按灵石排序
        sorted_players = sorted(all_players, key=lambda p: p.gold, reverse=True)[:limit]
        
        msg = "📊 财富排行榜\n"
        msg += "━━━━━━━━━━━━━━━\n"
        
        for idx, player in enumerate(sorted_players, 1):
            name = player.nickname or player.user_id[:8]
            msg += f"{idx}. {name}\n"
            msg += f"   灵石：{player.gold:,}\n\n"
        
        return True, msg
    
    def get_sect_ranking(self, limit: int = 10) -> Tuple[bool, str]:
        """宗门排行榜（建设度）"""
        all_sects = self.sect_repo.get_all_sects()
        
        if not all_sects:
            return False, "❌ 暂无宗门数据！"
        
        # 按建设度排序
        top_sects = sorted(all_sects, key=lambda s: s.funds, reverse=True)[:limit]
        
        msg = "📊 宗门排行榜\n"
        msg += "━━━━━━━━━━━━━━━\n"
        
        for idx, sect in enumerate(top_sects, 1):
            owner = self.player_repo.get_player(sect.leader_id)
            owner_name = owner.nickname if owner and owner.nickname else sect.leader_id[:8]
            members = self.sect_repo.get_sect_members(sect.sect_id)
            
            msg += f"{idx}. 【{sect.name}】\n"
            msg += f"   宗主：{owner_name}\n"
            msg += f"   建设度：{sect.funds:,} | 成员：{len(members)}人\n\n"
        
        return True, msg
    
    def get_deposit_ranking(self, limit: int = 10) -> Tuple[bool, str]:
        """存款排行榜（银行存款）"""
        rankings = self.bank_repo.get_deposit_ranking(limit)
        
        if not rankings:
            return False, "❌ 暂无存款数据！"
        
        msg = "📊 存款排行榜\n"
        msg += "━━━━━━━━━━━━━━━\n"
        
        for idx, item in enumerate(rankings, 1):
            user_id = item["user_id"]
            balance = item["balance"]
            player = self.player_repo.get_player(user_id)
            name = player.nickname if player and player.nickname else user_id[:8]
            msg += f"{idx}. {name}\n"
            msg += f"   存款：{balance:,} 灵石\n\n"
        
        return True, msg
    
    def get_contribution_ranking(self, sect_id: str, limit: int = 10) -> Tuple[bool, str]:
        """宗门贡献度排行榜"""
        sect = self.sect_repo.get_sect(sect_id)
        if not sect:
            return False, "❌ 宗门不存在！"
        
        members = self.sect_repo.get_sect_members(sect_id)
        
        if not members:
            return False, "❌ 宗门暂无成员！"
        
        # 按贡献度排序（这里简化处理，实际应该有贡献度字段）
        # 暂时按加入时间排序
        sorted_members = members[:limit]
        
        msg = f"📊 {sect.name} 贡献排行\n"
        msg += f"━━━━━━━━━━━━━━━\n"
        
        position_map = {
            "leader": "宗主",
            "elder": "长老",
            "inner": "内门",
            "outer": "外门"
        }
        
        for idx, member in enumerate(sorted_members, 1):
            name = member.nickname or member.user_id[:8]
            position_name = position_map.get(member.sect_position, "成员")
            msg += f"{idx}. {name} ({position_name})\n"
            # 暂时显示修为作为贡献度
            msg += f"   修为：{member.experience:,}\n\n"
        
        return True, msg
    
    def _get_level_name(self, level_index: int, cultivation_type: str) -> str:
        """获取境界名称"""
        # 使用 get_level_data 方法获取境界数据
        level_data = self.config_manager.get_level_data(cultivation_type)
        
        if 0 <= level_index < len(level_data):
            level_info = level_data[level_index]
            # 尝试多个可能的键名
            return level_info.get("name") or level_info.get("level_name", "未知境界")
        return "未知境界"
