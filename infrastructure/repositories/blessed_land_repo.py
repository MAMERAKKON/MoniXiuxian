"""洞天福地仓储"""
from typing import Optional, Dict, Any

from .base import BaseRepository
from ..storage import JSONStorage, TimestampConverter
from ...domain.models.blessed_land import BlessedLand


class BlessedLandRepository(BaseRepository[BlessedLand]):
    """洞天福地仓储"""
    
    def __init__(self, storage: JSONStorage):
        """
        初始化洞天福地仓储
        
        Args:
            storage: JSON存储管理器
        """
        super().__init__(storage, "blessed_lands.json")
    
    def get_by_id(self, user_id: str) -> Optional[BlessedLand]:
        """根据用户ID获取洞天福地"""
        return self.get_blessed_land(user_id)
    
    def save(self, entity: BlessedLand) -> None:
        """保存洞天福地"""
        land_dict = self._to_dict(entity)
        self.storage.set(self.filename, entity.user_id, land_dict)
    
    def delete(self, user_id: str) -> None:
        """删除洞天福地"""
        self.storage.delete(self.filename, user_id)
    
    def exists(self, user_id: str) -> bool:
        """检查洞天福地是否存在"""
        return self.storage.exists(self.filename, user_id)
    
    def get_blessed_land(self, user_id: str) -> Optional[BlessedLand]:
        """获取洞天福地"""
        data = self.storage.get(self.filename, user_id)
        
        if not data:
            return None
        
        return self._to_domain(data)
    
    def create_blessed_land(
        self,
        user_id: str,
        land_type: int,
        land_name: str,
        exp_bonus: float,
        gold_per_hour: int
    ) -> int:
        """创建洞天福地"""
        # 生成新的 ID
        all_data = self.storage.load(self.filename)
        if all_data:
            max_id = max(int(data.get("id", 0)) for data in all_data.values())
            new_id = max_id + 1
        else:
            new_id = 1
        
        land_data = {
            "id": new_id,
            "user_id": user_id,
            "land_type": land_type,
            "land_name": land_name,
            "level": 1,
            "exp_bonus": exp_bonus,
            "gold_per_hour": gold_per_hour,
            "last_collect_time": TimestampConverter.to_iso8601(0)
        }
        
        self.storage.set(self.filename, user_id, land_data)
        return new_id
    
    def update_blessed_land(
        self,
        user_id: str,
        land_type: Optional[int] = None,
        land_name: Optional[str] = None,
        level: Optional[int] = None,
        exp_bonus: Optional[float] = None,
        gold_per_hour: Optional[int] = None,
        last_collect_time: Optional[int] = None
    ):
        """更新洞天福地"""
        data = self.storage.get(self.filename, user_id)
        if not data:
            return
        
        if land_type is not None:
            data["land_type"] = land_type
        if land_name is not None:
            data["land_name"] = land_name
        if level is not None:
            data["level"] = level
        if exp_bonus is not None:
            data["exp_bonus"] = exp_bonus
        if gold_per_hour is not None:
            data["gold_per_hour"] = gold_per_hour
        if last_collect_time is not None:
            data["last_collect_time"] = TimestampConverter.to_iso8601(last_collect_time)
        
        self.storage.set(self.filename, user_id, data)
    
    def _to_domain(self, data: Dict[str, Any]) -> BlessedLand:
        """转换为领域模型"""
        return BlessedLand(
            id=data["id"],
            user_id=data["user_id"],
            land_type=data["land_type"],
            land_name=data["land_name"],
            level=data["level"],
            exp_bonus=data["exp_bonus"],
            gold_per_hour=data["gold_per_hour"],
            last_collect_time=TimestampConverter.from_iso8601(data["last_collect_time"])
        )
    
    def _to_dict(self, land: BlessedLand) -> Dict[str, Any]:
        """转换为字典数据"""
        return {
            "id": land.id,
            "user_id": land.user_id,
            "land_type": land.land_type,
            "land_name": land.land_name,
            "level": land.level,
            "exp_bonus": land.exp_bonus,
            "gold_per_hour": land.gold_per_hour,
            "last_collect_time": TimestampConverter.to_iso8601(land.last_collect_time)
        }
