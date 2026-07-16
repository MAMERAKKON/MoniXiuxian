"""双修系统领域模型"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class DualCultivationCooldown:
    """双修冷却"""
    user_id: str
    last_dual_time: int  # 上次双修时间戳


@dataclass
class DualCultivationRequest:
    """双修请求"""
    id: int
    from_id: str
    from_name: str
    target_id: str
    created_at: int
    expires_at: int
    
    def is_expired(self, current_time: int) -> bool:
        """检查请求是否过期"""
        return current_time > self.expires_at
