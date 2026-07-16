"""Boss仓储"""
from typing import Optional, Dict, Any

from .base import BaseRepository
from ..storage import JSONStorage, TimestampConverter
from ...domain.models.boss import Boss


class BossRepository(BaseRepository[Boss]):
    """Boss仓储"""
    
    def __init__(self, storage: JSONStorage):
        """
        初始化Boss仓储
        
        Args:
            storage: JSON存储管理器
        """
        super().__init__(storage, "bosses.json")
    
    def get_by_id(self, boss_id: str) -> Optional[Boss]:
        """根据ID获取Boss"""
        return self.get_boss_by_id(int(boss_id))
    
    def save(self, entity: Boss) -> None:
        """保存Boss（创建或更新）"""
        boss_dict = self._to_dict(entity)
        self.storage.set(self.filename, str(entity.boss_id), boss_dict)
    
    def delete(self, boss_id: str) -> None:
        """删除Boss"""
        self.storage.delete(self.filename, boss_id)
    
    def exists(self, boss_id: str) -> bool:
        """检查Boss是否存在"""
        return self.storage.exists(self.filename, boss_id)
    
    def get_active_boss(self) -> Optional[Boss]:
        """获取当前存活的Boss"""
        results = self.storage.query(
            self.filename,
            filter_fn=lambda data: data.get("status") == 1
        )
        
        if not results:
            return None
        
        return self._to_domain(results[0])
    
    def get_boss_by_id(self, boss_id: int) -> Optional[Boss]:
        """根据ID获取Boss"""
        data = self.storage.get(self.filename, str(boss_id))
        
        if not data:
            return None
        
        return self._to_domain(data)
    
    def create_boss(self, boss: Boss) -> int:
        """创建Boss"""
        # 生成新的 boss_id
        all_data = self.storage.load(self.filename)
        if all_data:
            max_id = max(int(bid) for bid in all_data.keys())
            new_id = max_id + 1
        else:
            new_id = 1
        
        boss.boss_id = new_id
        
        # 保存
        boss_dict = self._to_dict(boss)
        self.storage.set(self.filename, str(new_id), boss_dict)
        
        return new_id
    
    def update_boss(self, boss: Boss) -> None:
        """更新Boss"""
        boss_dict = self._to_dict(boss)
        self.storage.set(self.filename, str(boss.boss_id), boss_dict)
    
    def defeat_boss(self, boss_id: int) -> None:
        """标记Boss为已击败"""
        data = self.storage.get(self.filename, str(boss_id))
        if data:
            data["status"] = 0
            self.storage.set(self.filename, str(boss_id), data)
    
    def _to_domain(self, data: Dict[str, Any]) -> Boss:
        """转换为领域模型"""
        return Boss(
            boss_id=data["boss_id"],
            boss_name=data["boss_name"],
            boss_level=data["boss_level"],
            hp=data["hp"],
            max_hp=data["max_hp"],
            atk=data["atk"],
            defense=data["defense"],
            stone_reward=data["stone_reward"],
            create_time=TimestampConverter.from_iso8601(data["create_time"]),
            status=data["status"]
        )
    
    def _to_dict(self, boss: Boss) -> Dict[str, Any]:
        """转换为字典数据"""
        return {
            "boss_id": boss.boss_id,
            "boss_name": boss.boss_name,
            "boss_level": boss.boss_level,
            "hp": boss.hp,
            "max_hp": boss.max_hp,
            "atk": boss.atk,
            "defense": boss.defense,
            "stone_reward": boss.stone_reward,
            "create_time": TimestampConverter.to_iso8601(boss.create_time),
            "status": boss.status
        }
