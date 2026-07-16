"""双修系统仓储"""
import time
from typing import Optional, Dict, Any

from .base import BaseRepository
from ..storage import JSONStorage, TimestampConverter
from ...domain.models.dual_cultivation import DualCultivationCooldown, DualCultivationRequest


class DualCultivationRepository(BaseRepository[DualCultivationCooldown]):
    """双修仓储"""
    
    def __init__(self, storage: JSONStorage):
        """
        初始化双修仓储
        
        Args:
            storage: JSON存储管理器
        """
        super().__init__(storage, "dual_cultivation.json")
        self.requests_filename = "dual_cultivation_requests.json"
    
    def get_by_id(self, user_id: str) -> Optional[DualCultivationCooldown]:
        """根据用户ID获取冷却信息"""
        return self.get_cooldown(user_id)
    
    def save(self, entity: DualCultivationCooldown) -> None:
        """保存冷却信息"""
        cooldown_dict = self._to_dict(entity)
        self.storage.set(self.filename, entity.user_id, cooldown_dict)
    
    def delete(self, user_id: str) -> None:
        """删除冷却信息"""
        self.storage.delete(self.filename, user_id)
    
    def exists(self, user_id: str) -> bool:
        """检查冷却信息是否存在"""
        return self.storage.exists(self.filename, user_id)
    
    def get_cooldown(self, user_id: str) -> Optional[DualCultivationCooldown]:
        """获取冷却信息"""
        data = self.storage.get(self.filename, user_id)
        if not data:
            return None
        return self._to_domain(data)
    
    def set_cooldown(self, user_id: str, timestamp: int):
        """设置冷却时间"""
        cooldown_data = {
            "user_id": user_id,
            "last_dual_time": TimestampConverter.to_iso8601(timestamp)
        }
        self.storage.set(self.filename, user_id, cooldown_data)
    
    def create_request(self, from_id: str, from_name: str, target_id: str, expires_at: int) -> int:
        """创建双修请求"""
        now = int(time.time())
        
        # 删除目标的旧请求（通过查询找到并删除）
        all_requests = self.storage.load(self.requests_filename)
        for req_id, req_data in list(all_requests.items()):
            if req_data.get("target_id") == target_id:
                self.storage.delete(self.requests_filename, req_id)
        
        # 生成新的请求ID
        all_requests = self.storage.load(self.requests_filename)
        if all_requests:
            max_id = max(int(rid) for rid in all_requests.keys())
            new_id = max_id + 1
        else:
            new_id = 1
        
        # 创建新请求
        request_data = {
            "id": new_id,
            "from_id": from_id,
            "from_name": from_name,
            "target_id": target_id,
            "created_at": TimestampConverter.to_iso8601(now),
            "expires_at": TimestampConverter.to_iso8601(expires_at)
        }
        
        self.storage.set(self.requests_filename, str(new_id), request_data)
        return new_id
    
    def get_pending_request(self, target_id: str) -> Optional[DualCultivationRequest]:
        """获取待处理的请求"""
        now = int(time.time())
        now_iso = TimestampConverter.to_iso8601(now)
        
        # 清理过期请求
        all_requests = self.storage.load(self.requests_filename)
        for req_id, req_data in list(all_requests.items()):
            if req_data.get("expires_at") and req_data.get("expires_at") < now_iso:
                self.storage.delete(self.requests_filename, req_id)
        
        # 获取有效请求
        results = self.storage.query(
            self.requests_filename,
            filter_fn=lambda data: (
                data.get("target_id") == target_id and
                data.get("expires_at") and
                data.get("expires_at") > now_iso
            ),
            sort_key=lambda data: data.get("created_at", ""),
            reverse=True
        )
        
        if not results:
            return None
        
        data = results[0]
        return DualCultivationRequest(
            id=data["id"],
            from_id=data["from_id"],
            from_name=data["from_name"],
            target_id=data["target_id"],
            created_at=TimestampConverter.from_iso8601(data["created_at"]),
            expires_at=TimestampConverter.from_iso8601(data["expires_at"])
        )
    
    def delete_request(self, request_id: int):
        """删除请求"""
        self.storage.delete(self.requests_filename, str(request_id))
    
    def _to_domain(self, data: Dict[str, Any]) -> DualCultivationCooldown:
        """转换为领域模型"""
        return DualCultivationCooldown(
            user_id=data["user_id"],
            last_dual_time=TimestampConverter.from_iso8601(data["last_dual_time"])
        )
    
    def _to_dict(self, cooldown: DualCultivationCooldown) -> Dict[str, Any]:
        """转换为字典数据"""
        return {
            "user_id": cooldown.user_id,
            "last_dual_time": TimestampConverter.to_iso8601(cooldown.last_dual_time)
        }
