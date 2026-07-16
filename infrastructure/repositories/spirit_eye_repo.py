"""天地灵眼仓储"""
from typing import Optional, List, Dict, Any

from .base import BaseRepository
from ..storage import JSONStorage, TimestampConverter
from ...domain.models.spirit_eye import SpiritEye


class SpiritEyeRepository(BaseRepository[SpiritEye]):
    """天地灵眼仓储"""
    
    def __init__(self, storage: JSONStorage):
        """
        初始化天地灵眼仓储
        
        Args:
            storage: JSON存储管理器
        """
        super().__init__(storage, "spirit_eyes.json")
    
    def get_by_id(self, eye_id: str) -> Optional[SpiritEye]:
        """根据ID获取灵眼"""
        return self.get_spirit_eye(int(eye_id))
    
    def save(self, entity: SpiritEye) -> None:
        """保存灵眼"""
        eye_dict = self._to_dict(entity)
        self.storage.set(self.filename, str(entity.eye_id), eye_dict)
    
    def delete(self, eye_id: str) -> None:
        """删除灵眼"""
        self.storage.delete(self.filename, eye_id)
    
    def exists(self, eye_id: str) -> bool:
        """检查灵眼是否存在"""
        return self.storage.exists(self.filename, eye_id)
    
    def get_spirit_eye(self, eye_id: int) -> Optional[SpiritEye]:
        """获取灵眼"""
        data = self.storage.get(self.filename, str(eye_id))
        
        if not data:
            return None
        
        return self._to_domain(data)
    
    def get_user_spirit_eye(self, user_id: str) -> Optional[SpiritEye]:
        """获取用户占领的灵眼"""
        results = self.storage.query(
            self.filename,
            filter_fn=lambda data: data.get("owner_id") == user_id
        )
        
        if not results:
            return None
        
        return self._to_domain(results[0])
    
    def get_available_spirit_eyes(self) -> List[SpiritEye]:
        """获取所有可占领的灵眼"""
        results = self.storage.query(
            self.filename,
            filter_fn=lambda data: data.get("owner_id") is None
        )
        
        return [self._to_domain(data) for data in results]
    
    def get_all_spirit_eyes(self) -> List[SpiritEye]:
        """获取所有灵眼"""
        results = self.storage.query(self.filename)
        return [self._to_domain(data) for data in results]
    
    def create_spirit_eye(
        self,
        eye_type: int,
        eye_name: str,
        exp_per_hour: int,
        spawn_time: int
    ) -> int:
        """创建灵眼"""
        # 生成新的 eye_id
        all_data = self.storage.load(self.filename)
        if all_data:
            max_id = max(int(eid) for eid in all_data.keys())
            new_id = max_id + 1
        else:
            new_id = 1
        
        eye_data = {
            "eye_id": new_id,
            "eye_type": eye_type,
            "eye_name": eye_name,
            "exp_per_hour": exp_per_hour,
            "spawn_time": TimestampConverter.to_iso8601(spawn_time),
            "owner_id": None,
            "owner_name": None,
            "claim_time": None,
            "last_collect_time": TimestampConverter.to_iso8601(0)
        }
        
        self.storage.set(self.filename, str(new_id), eye_data)
        return new_id
    
    def claim_spirit_eye(
        self,
        eye_id: int,
        user_id: str,
        user_name: str,
        claim_time: int
    ) -> bool:
        """占领灵眼（原子操作）"""
        data = self.storage.get(self.filename, str(eye_id))
        
        if not data or data.get("owner_id") is not None:
            return False
        
        data["owner_id"] = user_id
        data["owner_name"] = user_name
        data["claim_time"] = TimestampConverter.to_iso8601(claim_time)
        data["last_collect_time"] = TimestampConverter.to_iso8601(claim_time)
        
        self.storage.set(self.filename, str(eye_id), data)
        return True
    
    def release_spirit_eye(self, eye_id: int):
        """释放灵眼"""
        data = self.storage.get(self.filename, str(eye_id))
        if not data:
            return
        
        data["owner_id"] = None
        data["owner_name"] = None
        data["claim_time"] = None
        data["last_collect_time"] = TimestampConverter.to_iso8601(0)
        
        self.storage.set(self.filename, str(eye_id), data)
    
    def update_collect_time(self, eye_id: int, collect_time: int):
        """更新收取时间"""
        data = self.storage.get(self.filename, str(eye_id))
        if not data:
            return
        
        data["last_collect_time"] = TimestampConverter.to_iso8601(collect_time)
        self.storage.set(self.filename, str(eye_id), data)
    
    def _to_domain(self, data: Dict[str, Any]) -> SpiritEye:
        """转换为领域模型"""
        return SpiritEye(
            eye_id=data["eye_id"],
            eye_type=data["eye_type"],
            eye_name=data["eye_name"],
            exp_per_hour=data["exp_per_hour"],
            spawn_time=TimestampConverter.from_iso8601(data["spawn_time"]),
            owner_id=data.get("owner_id"),
            owner_name=data.get("owner_name"),
            claim_time=TimestampConverter.from_iso8601(data.get("claim_time")) if data.get("claim_time") else None,
            last_collect_time=TimestampConverter.from_iso8601(data["last_collect_time"])
        )
    
    def _to_dict(self, eye: SpiritEye) -> Dict[str, Any]:
        """转换为字典数据"""
        return {
            "eye_id": eye.eye_id,
            "eye_type": eye.eye_type,
            "eye_name": eye.eye_name,
            "exp_per_hour": eye.exp_per_hour,
            "spawn_time": TimestampConverter.to_iso8601(eye.spawn_time),
            "owner_id": eye.owner_id,
            "owner_name": eye.owner_name,
            "claim_time": TimestampConverter.to_iso8601(eye.claim_time) if eye.claim_time else None,
            "last_collect_time": TimestampConverter.to_iso8601(eye.last_collect_time)
        }
