"""储物戒仓储层"""
import json
import time
from typing import Optional, Dict, List, Tuple

from ..storage import JSONStorage, TimestampConverter


class StorageRingRepository:
    """储物戒仓储"""
    
    # 功法残篇合成配置
    TECHNIQUE_SYNTHESIS = {
        # 凡品功法 - 5个残篇合成
        "长春功": {"fragment": "长春功残篇", "required": 5, "tier": "凡品"},
        "御风诀": {"fragment": "御风诀残篇", "required": 5, "tier": "凡品"},
        # 珍品功法 - 10个残篇合成
        "不动明王经": {"fragment": "不动明王经残篇", "required": 10, "tier": "珍品"},
        "北冥神功": {"fragment": "北冥神功残篇", "required": 10, "tier": "珍品"},
        "九阳神功": {"fragment": "九阳神功残篇", "required": 10, "tier": "珍品"},
        # 圣品/帝品功法 - 15个残篇合成
        "焚天诀": {"fragment": "焚天诀残篇", "required": 15, "tier": "圣品"},
        "道经": {"fragment": "道经残篇", "required": 15, "tier": "帝品"},
        "吞天魔功": {"fragment": "吞天魔功残篇", "required": 15, "tier": "圣品"},
        "他化自在大法": {"fragment": "他化自在大法残篇", "required": 15, "tier": "圣品"},
    }
    
    def __init__(self, storage: JSONStorage):
        """
        初始化储物戒仓储
        
        Args:
            storage: JSON存储管理器
        """
        self.storage = storage
        self.players_filename = "players.json"
        self.gifts_filename = "pending_gifts.json"
    
    def get_storage_ring_items(self, user_id: str) -> Dict[str, int]:
        """获取储物戒物品"""
        player_data = self.storage.get(self.players_filename, user_id)
        if not player_data or not player_data.get("storage_ring_items"):
            return {}
        
        try:
            items = player_data.get("storage_ring_items", {})
            if isinstance(items, str):
                return json.loads(items)
            return items
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def get_item_count(self, user_id: str, item_name: str) -> int:
        """
        获取指定物品的数量
        
        Args:
            user_id: 用户ID
            item_name: 物品名称
            
        Returns:
            物品数量
        """
        items = self.get_storage_ring_items(user_id)
        return items.get(item_name, 0)
    
    def has_item(self, user_id: str, item_name: str, count: int = 1) -> bool:
        """
        检查是否拥有指定数量的物品
        
        Args:
            user_id: 用户ID
            item_name: 物品名称
            count: 需要的数量
            
        Returns:
            是否拥有足够数量的物品
        """
        current_count = self.get_item_count(user_id, item_name)
        return current_count >= count
    
    def add_item(self, user_id: str, item_name: str, count: int = 1) -> Tuple[bool, Optional[str]]:
        """
        添加物品到储物戒，自动检测功法残篇合成
        
        Args:
            user_id: 用户ID
            item_name: 物品名称
            count: 数量
            
        Returns:
            (是否触发合成, 合成的功法名称)
        """
        items = self.get_storage_ring_items(user_id)
        items[item_name] = items.get(item_name, 0) + count
        
        # 检查是否为功法残篇，并尝试合成
        synthesized_technique = None
        for technique_name, config in self.TECHNIQUE_SYNTHESIS.items():
            fragment_name = config["fragment"]
            required_count = config["required"]
            
            # 如果添加的是这个功法的残篇
            if item_name == fragment_name:
                current_count = items.get(fragment_name, 0)
                
                # 检查是否可以合成
                if current_count >= required_count:
                    # 消耗残篇
                    items[fragment_name] = current_count - required_count
                    if items[fragment_name] == 0:
                        del items[fragment_name]
                    
                    # 添加完整功法
                    items[technique_name] = items.get(technique_name, 0) + 1
                    synthesized_technique = technique_name
                    break
        
        self.set_storage_ring_items(user_id, items)
        
        return (synthesized_technique is not None, synthesized_technique)
    
    def remove_item(self, user_id: str, item_name: str, count: int = 1) -> bool:
        """
        从储物戒移除物品
        
        Args:
            user_id: 用户ID
            item_name: 物品名称
            count: 数量
            
        Returns:
            是否成功移除
        """
        items = self.get_storage_ring_items(user_id)
        current_count = items.get(item_name, 0)
        
        if current_count < count:
            return False
        
        if current_count == count:
            del items[item_name]
        else:
            items[item_name] = current_count - count
        
        self.set_storage_ring_items(user_id, items)
        return True
    
    def set_storage_ring_items(self, user_id: str, items: Dict[str, int]) -> None:
        """设置储物戒物品"""
        player_data = self.storage.get(self.players_filename, user_id)
        if player_data:
            player_data["storage_ring_items"] = items
            player_data["updated_at"] = TimestampConverter.to_iso8601(int(time.time()))
            self.storage.set(self.players_filename, user_id, player_data)
    
    def get_storage_ring_name(self, user_id: str) -> str:
        """获取储物戒名称"""
        player_data = self.storage.get(self.players_filename, user_id)
        return player_data.get("storage_ring", "基础储物戒") if player_data else "基础储物戒"
    
    def set_storage_ring_name(self, user_id: str, ring_name: str) -> None:
        """设置储物戒名称"""
        player_data = self.storage.get(self.players_filename, user_id)
        if player_data:
            player_data["storage_ring"] = ring_name
            player_data["updated_at"] = TimestampConverter.to_iso8601(int(time.time()))
            self.storage.set(self.players_filename, user_id, player_data)
    
    # ===== 赠予系统 =====
    
    def create_pending_gift(
        self,
        receiver_id: str,
        sender_id: str,
        sender_name: str,
        item_name: str,
        count: int,
        expires_hours: int = 24
    ) -> int:
        """创建待处理赠予"""
        current_time = int(time.time())
        expires_at = current_time + (expires_hours * 3600)
        
        # 生成新的礼物ID
        all_gifts = self.storage.load(self.gifts_filename)
        if all_gifts:
            max_id = max(int(gid) for gid in all_gifts.keys())
            new_id = max_id + 1
        else:
            new_id = 1
        
        gift_data = {
            "id": new_id,
            "receiver_id": receiver_id,
            "sender_id": sender_id,
            "sender_name": sender_name,
            "item_name": item_name,
            "count": count,
            "created_at": TimestampConverter.to_iso8601(current_time),
            "expires_at": TimestampConverter.to_iso8601(expires_at)
        }
        
        self.storage.set(self.gifts_filename, str(new_id), gift_data)
        return new_id
    
    def get_pending_gift(self, receiver_id: str) -> Optional[Dict]:
        """获取待处理赠予（最早的一个）"""
        current_time = int(time.time())
        current_time_iso = TimestampConverter.to_iso8601(current_time)
        
        # 先删除过期的赠予
        all_gifts = self.storage.load(self.gifts_filename)
        for gift_id, gift_data in list(all_gifts.items()):
            if gift_data.get("expires_at") and gift_data.get("expires_at") < current_time_iso:
                self.storage.delete(self.gifts_filename, gift_id)
        
        # 获取最早的待处理赠予
        results = self.storage.query(
            self.gifts_filename,
            filter_fn=lambda data: data.get("receiver_id") == receiver_id,
            sort_key=lambda data: data.get("created_at", "")
        )
        
        if not results:
            return None
        
        gift_data = results[0]
        return {
            "id": gift_data["id"],
            "receiver_id": gift_data["receiver_id"],
            "sender_id": gift_data["sender_id"],
            "sender_name": gift_data["sender_name"],
            "item_name": gift_data["item_name"],
            "count": gift_data["count"],
            "created_at": TimestampConverter.from_iso8601(gift_data["created_at"]),
            "expires_at": TimestampConverter.from_iso8601(gift_data["expires_at"])
        }
    
    def delete_pending_gift(self, gift_id: int) -> None:
        """删除待处理赠予"""
        self.storage.delete(self.gifts_filename, str(gift_id))
    
    def cleanup_expired_gifts(self) -> int:
        """清理过期赠予，返回清理数量"""
        current_time = int(time.time())
        current_time_iso = TimestampConverter.to_iso8601(current_time)
        
        all_gifts = self.storage.load(self.gifts_filename)
        count = 0
        
        for gift_id, gift_data in list(all_gifts.items()):
            if gift_data.get("expires_at") and gift_data.get("expires_at") < current_time_iso:
                self.storage.delete(self.gifts_filename, gift_id)
                count += 1
        
        return count
