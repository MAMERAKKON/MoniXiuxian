"""天地灵眼领域模型"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SpiritEyeType(Enum):
    """灵眼类型枚举"""
    LOWER = 1  # 下品灵眼
    MIDDLE = 2  # 中品灵眼
    UPPER = 3  # 上品灵眼
    SUPREME = 4  # 极品灵眼


@dataclass
class SpiritEye:
    """天地灵眼"""
    eye_id: int  # 灵眼ID
    eye_type: int  # 灵眼类型
    eye_name: str  # 灵眼名称
    exp_per_hour: int  # 每小时修为产出
    spawn_time: int  # 生成时间
    owner_id: Optional[str]  # 拥有者ID
    owner_name: Optional[str]  # 拥有者名称
    claim_time: Optional[int]  # 占领时间
    last_collect_time: int  # 上次收取时间
    
    def is_available(self) -> bool:
        """检查是否可占领"""
        return self.owner_id is None
    
    def is_owned_by(self, user_id: str) -> bool:
        """检查是否被指定用户占领"""
        return self.owner_id == user_id
    
    def can_collect(self, current_time: int, min_interval: int = 3600) -> bool:
        """检查是否可以收取"""
        if not self.owner_id or self.last_collect_time == 0:
            return False
        return current_time - self.last_collect_time >= min_interval
    
    def calculate_exp(self, current_time: int, max_hours: int = 24) -> tuple[int, int]:
        """
        计算可收取的修为
        
        Returns:
            (hours, exp) - 小时数和修为
        """
        if not self.owner_id or self.last_collect_time == 0:
            return 0, 0
        
        hours = (current_time - self.last_collect_time) // 3600
        hours = min(hours, max_hours)  # 最多累积24小时
        exp = hours * self.exp_per_hour
        
        return hours, exp


@dataclass
class SpiritEyeInfo:
    """灵眼信息（用于显示）"""
    eye_id: int  # 灵眼ID
    eye_type: int  # 灵眼类型
    eye_name: str  # 灵眼名称
    exp_per_hour: int  # 每小时修为产出
    owner_id: Optional[str]  # 拥有者ID
    owner_name: Optional[str]  # 拥有者名称
    claim_time: Optional[int]  # 占领时间
    pending_hours: int  # 待收取小时数
    pending_exp: int  # 待收取修为
    is_available: bool  # 是否可占领
