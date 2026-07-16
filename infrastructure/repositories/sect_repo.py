"""
宗门仓储层

处理宗门数据的持久化。
"""
from typing import Optional, List, Dict, Any

from ...domain.models.sect import Sect, SectMember, SectPosition
from ..storage import JSONStorage, TimestampConverter


class SectRepository:
    """宗门仓储"""
    
    def __init__(self, storage: JSONStorage):
        """
        初始化宗门仓储
        
        Args:
            storage: JSON 存储管理器
        """
        self.storage = storage
        self.filename = "sects.json"
        self.players_filename = "players.json"
    
    def get_by_id(self, sect_id: int) -> Optional[Sect]:
        """
        根据ID获取宗门
        
        Args:
            sect_id: 宗门ID
            
        Returns:
            宗门对象，如果不存在则返回None
        """
        data = self.storage.get(self.filename, str(sect_id))
        if data is None:
            return None
        return self._to_domain(data)
    
    def get_sect(self, sect_id: int) -> Optional[Sect]:
        """
        根据ID获取宗门（别名方法）
        
        Args:
            sect_id: 宗门ID
            
        Returns:
            宗门对象，如果不存在则返回None
        """
        return self.get_by_id(sect_id)
    
    def get_by_name(self, name: str) -> Optional[Sect]:
        """
        根据名称获取宗门
        
        Args:
            name: 宗门名称
            
        Returns:
            宗门对象，如果不存在则返回None
        """
        results = self.storage.query(
            self.filename,
            filter_fn=lambda x: x.get('name') == name,
            limit=1
        )
        
        if not results:
            return None
        
        return self._to_domain(results[0])
    
    def create(self, sect: Sect) -> int:
        """
        创建宗门
        
        Args:
            sect: 宗门对象
            
        Returns:
            宗门ID
        """
        # 生成新的宗门ID
        all_sects = self.storage.query(self.filename)
        if all_sects:
            max_id = max(int(s.get('sect_id', 0)) for s in all_sects)
            new_id = max_id + 1
        else:
            new_id = 1
        
        # 设置新ID
        sect.sect_id = new_id
        
        # 保存
        data = self._to_dict(sect)
        self.storage.set(self.filename, str(new_id), data)
        
        return new_id
    
    def update(self, sect: Sect) -> None:
        """
        更新宗门
        
        Args:
            sect: 宗门对象
        """
        data = self._to_dict(sect)
        self.storage.set(self.filename, str(sect.sect_id), data)
    
    def delete(self, sect_id: int) -> None:
        """
        删除宗门
        
        Args:
            sect_id: 宗门ID
        """
        self.storage.delete(self.filename, str(sect_id))
    
    def get_all(self, limit: int = 100) -> List[Sect]:
        """
        获取所有宗门
        
        Args:
            limit: 限制数量
            
        Returns:
            宗门列表
        """
        results = self.storage.query(
            self.filename,
            sort_key=lambda x: x.get('scale', 0),
            reverse=True,
            limit=limit
        )
        
        return [self._to_domain(data) for data in results]
    
    def get_all_sects(self, limit: int = 100) -> List[Sect]:
        """
        获取所有宗门（别名方法）
        
        Args:
            limit: 限制数量
            
        Returns:
            宗门列表
        """
        return self.get_all(limit)
    
    def get_members(self, sect_id: int) -> List[SectMember]:
        """
        获取宗门成员列表
        
        Args:
            sect_id: 宗门ID
            
        Returns:
            成员列表
        """
        # 查询所有玩家，找到属于该宗门的成员
        all_players = self.storage.query(
            self.players_filename,
            filter_fn=lambda x: x.get('sect_id') == sect_id
        )
        
        result = []
        for player_data in all_players:
            position_value = player_data.get('sect_position', 4)
            if position_value is None:
                position_value = 4
            
            result.append(SectMember(
                user_id=player_data['user_id'],
                user_name=player_data.get('nickname', player_data['user_id']),
                position=SectPosition(position_value),
                contribution=0,  # 暂时固定为0，后续可以从player表读取
                level_index=player_data.get('level_index', 0)
            ))
        
        return result
    
    def get_sect_members(self, sect_id: int) -> List[SectMember]:
        """
        获取宗门成员列表（别名方法）
        
        Args:
            sect_id: 宗门ID
            
        Returns:
            成员列表
        """
        return self.get_members(sect_id)
    
    def get_member_count(self, sect_id: int) -> int:
        """
        获取宗门成员数量
        
        Args:
            sect_id: 宗门ID
            
        Returns:
            成员数量
        """
        members = self.storage.query(
            self.players_filename,
            filter_fn=lambda x: x.get('sect_id') == sect_id
        )
        return len(members)
    
    def update_player_sect(
        self, 
        user_id: str, 
        sect_id: int, 
        position: SectPosition
    ) -> None:
        """
        更新玩家宗门信息
        
        Args:
            user_id: 用户ID
            sect_id: 宗门ID（0表示无宗门）
            position: 职位
        """
        player_data = self.storage.get(self.players_filename, user_id)
        
        if player_data:
            if sect_id > 0:
                player_data['sect_id'] = sect_id
                player_data['sect_position'] = position.value
            else:
                player_data['sect_id'] = None
                player_data['sect_position'] = None
            
            self.storage.set(self.players_filename, user_id, player_data)
    
    def _to_domain(self, data: Dict[str, Any]) -> Sect:
        """
        将字典数据转换为领域对象
        
        Args:
            data: 字典数据
            
        Returns:
            Sect 对象
        """
        # 转换时间戳
        created_at = TimestampConverter.from_iso8601(data.get('created_at'))
        if created_at is None:
            created_at = 0
        
        return Sect(
            sect_id=data['sect_id'],
            name=data['name'],
            leader_id=data['leader_id'],
            scale=data.get('scale', 0),
            funds=data.get('funds', 0),
            materials=data.get('materials', 0),
            elixir_room_level=data.get('elixir_room_level', 0),
            created_at=created_at
        )
    
    def _to_dict(self, sect: Sect) -> Dict[str, Any]:
        """
        将领域对象转换为字典数据
        
        Args:
            sect: Sect 对象
            
        Returns:
            字典数据
        """
        return {
            'sect_id': sect.sect_id,
            'name': sect.name,
            'leader_id': sect.leader_id,
            'scale': sect.scale,
            'funds': sect.funds,
            'materials': sect.materials,
            'elixir_room_level': sect.elixir_room_level,
            'created_at': TimestampConverter.to_iso8601(sect.created_at)
        }
