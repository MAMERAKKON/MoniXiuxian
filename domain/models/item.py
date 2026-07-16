"""物品领域模型"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
from ..enums import ItemType, ItemRarity


@dataclass
class Item:
    """物品领域模型"""
    item_id: str
    name: str
    item_type: ItemType
    rarity: ItemRarity
    description: str
    
    # 属性加成
    attributes: Dict[str, Any]
    
    # 价格
    buy_price: int
    sell_price: int
    
    # 使用限制
    required_level: int
    
    def can_be_stored_in_ring(self) -> bool:
        """检查是否可以存入储物戒"""
        # 丹药不能存入储物戒
        if self.item_type == ItemType.PILL:
            return False
        # 储物戒本身不能存入储物戒
        if self.item_type == ItemType.STORAGE_RING:
            return False
        return True
    
    def get_attribute(self, key: str, default: Any = None) -> Any:
        """获取属性值"""
        return self.attributes.get(key, default)


@dataclass
class StorageRing:
    """储物戒领域模型"""
    name: str
    rank: str
    description: str
    capacity: int
    required_level_index: int
    price: int
    
    def can_upgrade_from(self, current_capacity: int) -> bool:
        """检查是否可以从当前储物戒升级"""
        return self.capacity > current_capacity


@dataclass
class InventoryItem:
    """背包物品（带数量）"""
    item_id: str
    name: str
    quantity: int
    obtained_at: int
    
    def add_quantity(self, amount: int) -> None:
        """增加数量"""
        self.quantity += amount
    
    def remove_quantity(self, amount: int) -> bool:
        """减少数量，返回是否成功"""
        if amount > self.quantity:
            return False
        self.quantity -= amount
        return True
    
    def has_enough(self, amount: int) -> bool:
        """检查数量是否足够"""
        return self.quantity >= amount
