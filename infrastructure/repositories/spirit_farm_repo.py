"""灵田仓储"""
import json
from typing import Optional, Dict, Any

from .base import BaseRepository
from ..storage import JSONStorage, TimestampConverter
from ...domain.models.spirit_farm import SpiritFarm, Crop


class SpiritFarmRepository(BaseRepository[SpiritFarm]):
    """灵田仓储"""
    
    def __init__(self, storage: JSONStorage):
        """
        初始化灵田仓储
        
        Args:
            storage: JSON存储管理器
        """
        super().__init__(storage, "spirit_farms.json")
    
    def get_by_id(self, user_id: str) -> Optional[SpiritFarm]:
        """根据用户ID获取灵田"""
        return self.get_spirit_farm(user_id)
    
    def save(self, entity: SpiritFarm) -> None:
        """保存灵田"""
        farm_dict = self._to_dict(entity)
        self.storage.set(self.filename, entity.user_id, farm_dict)
    
    def delete(self, user_id: str) -> None:
        """删除灵田"""
        self.storage.delete(self.filename, user_id)
    
    def exists(self, user_id: str) -> bool:
        """检查灵田是否存在"""
        return self.storage.exists(self.filename, user_id)
    
    def get_spirit_farm(self, user_id: str) -> Optional[SpiritFarm]:
        """获取灵田"""
        data = self.storage.get(self.filename, user_id)
        
        if not data:
            return None
        
        return self._to_domain(data)
    
    def create_spirit_farm(self, user_id: str) -> int:
        """创建灵田"""
        # 生成新的 ID
        all_data = self.storage.load(self.filename)
        if all_data:
            max_id = max(int(data.get("id", 0)) for data in all_data.values())
            new_id = max_id + 1
        else:
            new_id = 1
        
        farm_data = {
            "id": new_id,
            "user_id": user_id,
            "level": 1,
            "crops": []
        }
        
        self.storage.set(self.filename, user_id, farm_data)
        return new_id
    
    def update_crops(self, user_id: str, crops: list):
        """更新作物列表"""
        data = self.storage.get(self.filename, user_id)
        if not data:
            return
        
        # 转换作物列表为字典列表
        crops_data = [
            {
                'name': c.name,
                'plant_time': TimestampConverter.to_iso8601(c.plant_time),
                'mature_time': TimestampConverter.to_iso8601(c.mature_time),
                'wither_time': TimestampConverter.to_iso8601(c.wither_time),
                'slot': c.slot
            }
            for c in crops
        ]
        
        data["crops"] = crops_data
        self.storage.set(self.filename, user_id, data)
    
    def update_level(self, user_id: str, level: int):
        """更新灵田等级"""
        data = self.storage.get(self.filename, user_id)
        if not data:
            return
        
        data["level"] = level
        self.storage.set(self.filename, user_id, data)
    
    def _to_domain(self, data: Dict[str, Any]) -> SpiritFarm:
        """转换为领域模型"""
        # 解析作物列表
        crops_data = data.get("crops", [])
        crops = [
            Crop(
                name=c['name'],
                plant_time=TimestampConverter.from_iso8601(c['plant_time']),
                mature_time=TimestampConverter.from_iso8601(c['mature_time']),
                wither_time=TimestampConverter.from_iso8601(c['wither_time']),
                slot=c['slot']
            )
            for c in crops_data
        ]
        
        return SpiritFarm(
            id=data["id"],
            user_id=data["user_id"],
            level=data["level"],
            crops=crops
        )
    
    def _to_dict(self, farm: SpiritFarm) -> Dict[str, Any]:
        """转换为字典数据"""
        return {
            "id": farm.id,
            "user_id": farm.user_id,
            "level": farm.level,
            "crops": [
                {
                    'name': c.name,
                    'plant_time': TimestampConverter.to_iso8601(c.plant_time),
                    'mature_time': TimestampConverter.to_iso8601(c.mature_time),
                    'wither_time': TimestampConverter.to_iso8601(c.wither_time),
                    'slot': c.slot
                }
                for c in farm.crops
            ]
        }
