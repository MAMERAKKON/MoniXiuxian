"""
商店仓储层

处理商店数据的持久化。
"""
from typing import Optional, Tuple, List, Dict, Any

from ...domain.models.shop import Shop, ShopItem
from ..storage import JSONStorage, TimestampConverter


class ShopRepository:
    """商店仓储"""
    
    def __init__(self, storage: JSONStorage):
        """
        初始化商店仓储
        
        Args:
            storage: JSON 存储管理器
        """
        self.storage = storage
        self.filename = "shops.json"
    
    def get_shop_data(self, shop_id: str) -> Tuple[int, List[Dict]]:
        """
        获取商店数据
        
        Args:
            shop_id: 商店ID
            
        Returns:
            (上次刷新时间, 商品列表)
        """
        data = self.storage.get(self.filename, shop_id)
        
        if not data:
            return 0, []
        
        # 转换时间戳
        last_refresh_time = TimestampConverter.from_iso8601(data.get('last_refresh_time'))
        if last_refresh_time is None:
            last_refresh_time = 0
        
        items = data.get('items', [])
        
        return last_refresh_time, items
    
    def update_shop_data(self, shop_id: str, last_refresh_time: int, items: List[Dict]) -> None:
        """
        更新商店数据
        
        Args:
            shop_id: 商店ID
            last_refresh_time: 刷新时间
            items: 商品列表
        """
        data = {
            'shop_id': shop_id,
            'last_refresh_time': TimestampConverter.to_iso8601(last_refresh_time),
            'items': items
        }
        
        self.storage.set(self.filename, shop_id, data)
    
    def decrement_item_stock(
        self, 
        shop_id: str, 
        item_name: str, 
        quantity: int = 1
    ) -> Tuple[bool, int, int]:
        """
        减少商品库存
        
        Args:
            shop_id: 商店ID
            item_name: 商品名称
            quantity: 减少数量
            
        Returns:
            (是否成功, 减少的数量, 剩余库存)
        """
        last_refresh, items = self.get_shop_data(shop_id)
        
        for item in items:
            if item['name'] == item_name:
                current_stock = item.get('stock', 0)
                
                if current_stock < quantity:
                    return False, 0, current_stock
                
                item['stock'] = current_stock - quantity
                remaining = item['stock']
                
                # 更新数据库
                self.update_shop_data(shop_id, last_refresh, items)
                
                return True, quantity, remaining
        
        return False, 0, 0
