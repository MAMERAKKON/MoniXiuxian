"""转世传承池仓储"""
from typing import Optional, List, Dict, Any
from copy import deepcopy

from .base import BaseRepository
from ..storage import JSONStorage, TimestampConverter
from ...domain.models.reincarnation import ReincarnationPool


class ReincarnationRepository(BaseRepository[ReincarnationPool]):
    """转世传承池仓储"""
    
    def __init__(self, storage: JSONStorage):
        """
        初始化转世传承池仓储
        
        Args:
            storage: JSON存储管理器
        """
        super().__init__(storage, "reincarnation_pool.json")
    
    def get_by_id(self, user_id: str) -> Optional[ReincarnationPool]:
        """根据用户ID获取传承池"""
        return self.get_reincarnation_pool(user_id)
    
    def save(self, entity: ReincarnationPool) -> None:
        """保存传承池"""
        pool_dict = self._to_dict(entity)
        self.storage.set(self.filename, entity.user_id, pool_dict)
    
    def delete(self, user_id: str) -> None:
        """删除传承池"""
        self.storage.delete(self.filename, user_id)
    
    def exists(self, user_id: str) -> bool:
        """检查传承池是否存在"""
        return self.storage.exists(self.filename, user_id)
    
    def get_reincarnation_pool(self, user_id: str) -> Optional[ReincarnationPool]:
        """获取传承池"""
        data = self.storage.get(self.filename, user_id)
        if not data:
            return None
        return self._to_domain(data)
    
    def create_reincarnation_pool(self, user_id: str) -> ReincarnationPool:
        """创建传承池"""
        pool = ReincarnationPool(user_id=user_id)
        self.save(pool)
        return pool
    
    def update_reincarnation_pool(self, pool: ReincarnationPool) -> None:
        """更新传承池"""
        self.save(pool)
    
    def add_to_life_pool(self, user_id: str, prop_key: str, value: float) -> ReincarnationPool:
        """
        添加传承到本世池
        
        Args:
            user_id: 用户ID
            prop_key: 属性名（如 'attack_percent', 'hp_flat'）
            value: 添加的值
            
        Returns:
            更新后的传承池
        """
        pool = self.get_reincarnation_pool(user_id)
        if not pool:
            pool = self.create_reincarnation_pool(user_id)
        
        pool.add_to_life_pool(prop_key, value)
        self.save(pool)
        return pool
    
    def merge_to_permanent(self, user_id: str, extra_bonus: Optional[Dict[str, float]] = None) -> ReincarnationPool:
        """
        将本世池合并到永久池（轮回时调用）
        
        Args:
            user_id: 用户ID
            extra_bonus: 额外奖励（如境界奖励）
            
        Returns:
            更新后的传承池
        """
        pool = self.get_reincarnation_pool(user_id)
        if not pool:
            pool = self.create_reincarnation_pool(user_id)
        
        pool.merge_to_permanent(extra_bonus)
        self.save(pool)
        return pool
    
    def get_permanent_pool(self, user_id: str) -> Dict[str, float]:
        """获取永久池"""
        pool = self.get_reincarnation_pool(user_id)
        if not pool:
            return {}
        return pool.get_total_bonus()
    
    def get_life_pool(self, user_id: str) -> Dict[str, float]:
        """获取本世池"""
        pool = self.get_reincarnation_pool(user_id)
        if not pool:
            return {}
        return pool.get_life_pool()
    
    def get_reincarnation_count(self, user_id: str) -> int:
        """获取转世次数"""
        pool = self.get_reincarnation_pool(user_id)
        if not pool:
            return 0
        return pool.get_reincarnation_count()

    def set_retained_assets(self, user_id: str, assets: Dict[str, Dict[str, int]]) -> None:
        pool = self.get_reincarnation_pool(user_id)
        if not pool:
            pool = self.create_reincarnation_pool(user_id)
        pool.retained_assets = deepcopy(assets or {})
        self.save(pool)

    def consume_retained_assets(self, user_id: str) -> Dict[str, Dict[str, int]]:
        pool = self.get_reincarnation_pool(user_id)
        if not pool or not pool.retained_assets:
            return {}
        assets = deepcopy(pool.retained_assets)
        pool.retained_assets = {}
        self.save(pool)
        return assets
    
    def get_ranking(self, limit: int = 10) -> List[tuple]:
        """
        获取传承排行榜（按总加成排序）
        
        Returns:
            List of (user_id, total_percent, reincarnation_count)
        """
        results = self.storage.query(
            self.filename,
            sort_key=lambda data: sum([
                data.get("reincarnation_pool", {}).get("attack_percent", 0.0),
                data.get("reincarnation_pool", {}).get("hp_percent", 0.0),
                data.get("reincarnation_pool", {}).get("crit_rate_percent", 0.0),
            ]),
            reverse=True,
            limit=limit
        )
        
        ranking = []
        for data in results:
            user_id = data["user_id"]
            pool = data.get("reincarnation_pool", {})
            total = sum([
                pool.get("attack_percent", 0.0),
                pool.get("hp_percent", 0.0),
                pool.get("mp_percent", 0.0),
                pool.get("defense_percent", 0.0),
                pool.get("crit_rate_percent", 0.0),
                pool.get("crit_damage_percent", 0.0),
            ])
            count = data.get("reincarnation_count", 0)
            ranking.append((user_id, total, count))
        
        return ranking
    
    def _to_domain(self, data: Dict[str, Any]) -> ReincarnationPool:
        """转换为领域模型"""
        return ReincarnationPool(
            user_id=data["user_id"],
            reincarnation_pool=data.get("reincarnation_pool", {
                "hp_percent": 0.0,
                "attack_percent": 0.0,
                "mp_percent": 0.0,
                "defense_percent": 0.0,
                "crit_rate_percent": 0.0,
                "crit_damage_percent": 0.0,
                "hp_flat": 0.0,
                "attack_flat": 0.0,
                "mp_flat": 0.0,
                "defense_flat": 0.0
            }),
            current_life_pool=data.get("current_life_pool", {
                "hp_percent": 0.0,
                "attack_percent": 0.0,
                "mp_percent": 0.0,
                "defense_percent": 0.0,
                "crit_rate_percent": 0.0,
                "crit_damage_percent": 0.0,
                "hp_flat": 0.0,
                "attack_flat": 0.0,
                "mp_flat": 0.0,
                "defense_flat": 0.0
            }),
            reincarnation_count=data.get("reincarnation_count", 0),
            last_reincarnation_time=TimestampConverter.from_iso8601(data.get("last_reincarnation_time"))
            ,retained_assets=data.get("retained_assets", {})
            ,bounty_merit=int(data.get("bounty_merit", 0) or 0)
            ,bounty_exchange_counts={
                "crit_rate_percent": int(data.get("bounty_exchange_counts", {}).get("crit_rate_percent", 0) or 0),
                "crit_damage_percent": int(data.get("bounty_exchange_counts", {}).get("crit_damage_percent", 0) or 0),
            }
        )
    
    def _to_dict(self, pool: ReincarnationPool) -> Dict[str, Any]:
        """转换为字典数据"""
        return {
            "user_id": pool.user_id,
            "reincarnation_pool": pool.reincarnation_pool,
            "current_life_pool": pool.current_life_pool,
            "reincarnation_count": pool.reincarnation_count,
            "last_reincarnation_time": TimestampConverter.to_iso8601(pool.last_reincarnation_time)
            ,"retained_assets": pool.retained_assets
            ,"bounty_merit": int(pool.bounty_merit)
            ,"bounty_exchange_counts": pool.bounty_exchange_counts
        }
