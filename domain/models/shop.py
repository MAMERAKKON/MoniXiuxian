"""
商店领域模型

定义商店、商品等核心概念。
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime


@dataclass
class ShopItem:
    """商店商品"""
    
    id: str  # 商品ID
    name: str  # 商品名称
    item_type: str  # 商品类型
    rank: str  # 品级
    original_price: int  # 原价
    discount: float  # 折扣（0.8-1.2）
    price: int  # 实际售价
    stock: int  # 库存
    data: Dict  # 原始配置数据
    
    def is_available(self) -> bool:
        """是否有库存"""
        return self.stock > 0
    
    def decrease_stock(self, quantity: int = 1) -> bool:
        """
        减少库存
        
        Args:
            quantity: 减少数量
            
        Returns:
            是否成功
        """
        if self.stock >= quantity:
            self.stock -= quantity
            return True
        return False


@dataclass
class Shop:
    """商店（阁楼）"""
    
    shop_id: str  # 商店ID（pill_pavilion, weapon_pavilion, treasure_pavilion）
    name: str  # 商店名称
    items: List[ShopItem] = field(default_factory=list)  # 商品列表
    last_refresh_time: int = 0  # 上次刷新时间戳
    refresh_interval_hours: int = 6  # 刷新间隔（小时）
    
    def should_refresh(self, current_time: int) -> bool:
        """
        是否需要刷新
        
        Args:
            current_time: 当前时间戳
            
        Returns:
            是否需要刷新
        """
        if self.refresh_interval_hours <= 0:
            return False
        elapsed = current_time - self.last_refresh_time
        return elapsed >= (self.refresh_interval_hours * 3600)
    
    def get_remaining_refresh_time(self, current_time: int) -> int:
        """
        获取距离下次刷新的剩余时间（秒）
        
        Args:
            current_time: 当前时间戳
            
        Returns:
            剩余秒数
        """
        if self.refresh_interval_hours <= 0:
            return 0
        elapsed = current_time - self.last_refresh_time
        total_seconds = self.refresh_interval_hours * 3600
        remaining = total_seconds - elapsed
        return max(0, remaining)
    
    def find_item_by_name(self, name: str) -> Optional[ShopItem]:
        """
        根据名称查找商品
        
        Args:
            name: 商品名称
            
        Returns:
            商品对象，如果不存在则返回None
        """
        for item in self.items:
            if item.name == name and item.is_available():
                return item
        return None
    
    def get_available_items(self) -> List[ShopItem]:
        """获取所有有库存的商品"""
        return [item for item in self.items if item.is_available()]
