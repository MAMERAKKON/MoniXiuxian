"""基础仓储"""
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, Dict, Any

from ..storage import JSONStorage

T = TypeVar('T')


class BaseRepository(ABC, Generic[T]):
    """
    基础仓储接口
    
    所有 Repository 的基类，提供统一的数据访问接口。
    使用 JSONStorage 作为底层存储。
    """
    
    def __init__(self, storage: JSONStorage, filename: str):
        """
        初始化仓储
        
        Args:
            storage: JSON 存储管理器
            filename: 对应的 JSON 文件名（例如：players.json）
        """
        self.storage = storage
        self.filename = filename
    
    @abstractmethod
    def get_by_id(self, id: str) -> Optional[T]:
        """
        根据 ID 获取实体
        
        Args:
            id: 实体 ID
            
        Returns:
            实体对象，不存在则返回 None
        """
        pass
    
    @abstractmethod
    def save(self, entity: T) -> None:
        """
        保存实体（创建或更新）
        
        Args:
            entity: 实体对象
        """
        pass
    
    @abstractmethod
    def delete(self, id: str) -> None:
        """
        删除实体
        
        Args:
            id: 实体 ID
        """
        pass
    
    @abstractmethod
    def exists(self, id: str) -> bool:
        """
        检查实体是否存在
        
        Args:
            id: 实体 ID
            
        Returns:
            是否存在
        """
        pass
    
    @abstractmethod
    def _to_domain(self, data: Dict[str, Any]) -> T:
        """
        将字典数据转换为领域对象
        
        Args:
            data: 字典数据
            
        Returns:
            领域对象
        """
        pass
    
    @abstractmethod
    def _to_dict(self, entity: T) -> Dict[str, Any]:
        """
        将领域对象转换为字典数据
        
        Args:
            entity: 领域对象
            
        Returns:
            字典数据
        """
        pass
