"""
悬赏仓储层
"""
from typing import Optional, Dict, Any

from .base import BaseRepository
from ..storage import JSONStorage, TimestampConverter
from ...domain.models.bounty import BountyTask


class BountyRepository(BaseRepository[BountyTask]):
    """悬赏仓储"""
    
    def __init__(self, storage: JSONStorage):
        """
        初始化悬赏仓储
        
        Args:
            storage: JSON存储管理器
        """
        super().__init__(storage, "bounty_tasks.json")
        self.cooldown_filename = "bounty_cooldowns.json"
    
    def get_by_id(self, user_id: str) -> Optional[BountyTask]:
        """根据用户ID获取悬赏任务"""
        return self.get_active_bounty(user_id)
    
    def save(self, entity: BountyTask) -> None:
        """保存悬赏任务"""
        task_dict = self._to_dict(entity)
        self.storage.set(self.filename, entity.user_id, task_dict)
    
    def delete(self, user_id: str) -> None:
        """删除悬赏任务"""
        self.storage.delete(self.filename, user_id)
    
    def exists(self, user_id: str) -> bool:
        """检查悬赏任务是否存在"""
        return self.storage.exists(self.filename, user_id)
    
    def get_active_bounty(self, user_id: str) -> Optional[BountyTask]:
        """
        获取进行中的悬赏
        
        Args:
            user_id: 用户ID
            
        Returns:
            悬赏任务，如果没有则返回None
        """
        data = self.storage.get(self.filename, user_id)
        
        if not data or data.get("status") != 1:
            return None
        
        return self._to_domain(data)
    
    def create_task(self, task: BountyTask):
        """
        创建悬赏任务
        
        Args:
            task: 悬赏任务
        """
        task_dict = self._to_dict(task)
        self.storage.set(self.filename, task.user_id, task_dict)
    
    def update_task_status(self, user_id: str, status: int):
        """
        更新任务状态
        
        Args:
            user_id: 用户ID
            status: 状态
        """
        data = self.storage.get(self.filename, user_id)
        if data and data.get("status") == 1:
            data["status"] = status
            self.storage.set(self.filename, user_id, data)
    
    def update_progress(self, user_id: str, progress: int):
        """
        更新任务进度
        
        Args:
            user_id: 用户ID
            progress: 进度
        """
        data = self.storage.get(self.filename, user_id)
        if data and data.get("status") == 1:
            data["current_progress"] = progress
            self.storage.set(self.filename, user_id, data)
    
    def get_abandon_cooldown(self, user_id: str) -> Optional[int]:
        """
        获取放弃冷却时间
        
        Args:
            user_id: 用户ID
            
        Returns:
            冷却结束时间戳，如果没有则返回None
        """
        data = self.storage.get(self.cooldown_filename, user_id)
        
        if data:
            try:
                # 从 ISO 8601 转换为 Unix 时间戳
                return TimestampConverter.from_iso8601(data.get("cooldown_time"))
            except:
                return None
        return None
    
    def set_abandon_cooldown(self, user_id: str, cooldown_time: int):
        """
        设置放弃冷却时间
        
        Args:
            user_id: 用户ID
            cooldown_time: 冷却结束时间戳
        """
        cooldown_data = {
            "user_id": user_id,
            "cooldown_time": TimestampConverter.to_iso8601(cooldown_time)
        }
        self.storage.set(self.cooldown_filename, user_id, cooldown_data)
    
    def _to_domain(self, data: Dict[str, Any]) -> BountyTask:
        """转换为领域模型"""
        return BountyTask(
            user_id=data["user_id"],
            bounty_id=data["bounty_id"],
            bounty_name=data["bounty_name"],
            target_type=data["target_type"],
            target_count=data["target_count"],
            current_progress=data["current_progress"],
            rewards=data["rewards"],
            start_time=TimestampConverter.from_iso8601(data["start_time"]),
            expire_time=TimestampConverter.from_iso8601(data["expire_time"]),
            status=data["status"]
        )
    
    def _to_dict(self, task: BountyTask) -> Dict[str, Any]:
        """转换为字典数据"""
        return {
            "user_id": task.user_id,
            "bounty_id": task.bounty_id,
            "bounty_name": task.bounty_name,
            "target_type": task.target_type,
            "target_count": task.target_count,
            "current_progress": task.current_progress,
            "rewards": task.rewards,
            "start_time": TimestampConverter.to_iso8601(task.start_time),
            "expire_time": TimestampConverter.to_iso8601(task.expire_time),
            "status": task.status
        }
