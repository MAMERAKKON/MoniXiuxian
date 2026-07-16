"""系统配置仓储"""
from typing import Optional, Dict, Any

from .base import BaseRepository
from ..storage import JSONStorage, TimestampConverter


class SystemConfigRepository(BaseRepository[Dict[str, str]]):
    """系统配置仓储"""
    
    def __init__(self, storage: JSONStorage):
        """
        初始化系统配置仓储
        
        Args:
            storage: JSON存储管理器
        """
        super().__init__(storage, "system_config.json")
    
    def get_by_id(self, key: str) -> Optional[Dict[str, str]]:
        """根据键获取配置"""
        value = self.get_config(key)
        if value is None:
            return None
        return {"key": key, "value": value}
    
    def save(self, entity: Dict[str, str]) -> None:
        """保存配置"""
        key = entity.get("key")
        value = entity.get("value")
        if key and value is not None:
            self.set_config(key, value)
    
    def delete(self, key: str) -> None:
        """删除配置"""
        self.delete_config(key)
    
    def exists(self, key: str) -> bool:
        """检查配置是否存在"""
        return self.storage.exists(self.filename, key)
    
    def get_config(self, key: str) -> Optional[str]:
        """
        获取配置值
        
        Args:
            key: 配置键
            
        Returns:
            配置值，不存在则返回None
        """
        data = self.storage.get(self.filename, key)
        if not data:
            return None
        return data.get("value")
    
    def set_config(self, key: str, value: str) -> None:
        """
        设置配置值
        
        Args:
            key: 配置键
            value: 配置值
        """
        import time
        
        config_data = {
            "key": key,
            "value": value,
            "updated_at": TimestampConverter.to_iso8601(int(time.time()))
        }
        
        self.storage.set(self.filename, key, config_data)
    
    def delete_config(self, key: str) -> None:
        """
        删除配置
        
        Args:
            key: 配置键
        """
        self.storage.delete(self.filename, key)
    
    def _to_domain(self, data: Dict[str, Any]) -> Dict[str, str]:
        """转换为领域模型"""
        return {
            "key": data["key"],
            "value": data["value"]
        }
    
    def _to_dict(self, entity: Dict[str, str]) -> Dict[str, Any]:
        """转换为字典数据"""
        import time
        return {
            "key": entity["key"],
            "value": entity["value"],
            "updated_at": TimestampConverter.to_iso8601(int(time.time()))
        }
