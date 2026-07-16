"""炼丹配方数据模型"""
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class Recipe:
    """炼丹配方数据类"""
    id: str
    pill_id: str
    name: str
    rank: str
    level_required: int
    materials: Dict[str, int]
    success_rate: int
    cost: int
    
    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "id": self.id,
            "pill_id": self.pill_id,
            "name": self.name,
            "rank": self.rank,
            "level_required": self.level_required,
            "materials": self.materials,
            "success_rate": self.success_rate,
            "cost": self.cost
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Recipe':
        """从字典反序列化"""
        return cls(
            id=data["id"],
            pill_id=data["pill_id"],
            name=data["name"],
            rank=data["rank"],
            level_required=data["level_required"],
            materials=data["materials"],
            success_rate=data["success_rate"],
            cost=data["cost"]
        )
    
    def __eq__(self, other) -> bool:
        """相等性比较"""
        if not isinstance(other, Recipe):
            return False
        return (
            self.id == other.id and
            self.pill_id == other.pill_id and
            self.name == other.name and
            self.rank == other.rank and
            self.level_required == other.level_required and
            self.materials == other.materials and
            self.success_rate == other.success_rate and
            self.cost == other.cost
        )
