"""
悬赏领域模型
"""
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class Bounty:
    """悬赏"""
    id: int
    name: str
    category: str
    difficulty: str
    difficulty_name: str
    description: str
    count: int
    reward: Dict[str, int]
    time_limit: int
    progress_tags: List[str]
    item_table: str


@dataclass
class BountyTask:
    """悬赏任务"""
    user_id: str
    bounty_id: int
    bounty_name: str
    target_type: str
    target_count: int
    current_progress: int
    rewards: str  # JSON string
    start_time: int
    expire_time: int
    status: int  # 0=已取消, 1=进行中, 2=已完成, 3=已超时
