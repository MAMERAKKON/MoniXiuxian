"""传承系统仓储"""
from typing import Optional, List, Dict, Any

from .base import BaseRepository
from ..storage import JSONStorage
from ...domain.models.impart import ImpartInfo


class ImpartRepository(BaseRepository[ImpartInfo]):
    """传承仓储"""

    COOLDOWN_FILENAME = "impart_cooldowns.json"
    THEFT_LIMIT_FILENAME = "impart_theft_limits.json"
    
    def __init__(self, storage: JSONStorage):
        """
        初始化传承仓储
        
        Args:
            storage: JSON存储管理器
        """
        super().__init__(storage, "impart_info.json")
    
    def get_by_id(self, user_id: str) -> Optional[ImpartInfo]:
        """根据用户ID获取传承信息"""
        return self.get_impart_info(user_id)
    
    def save(self, entity: ImpartInfo) -> None:
        """保存传承信息"""
        impart_dict = self._to_dict(entity)
        self.storage.set(self.filename, entity.user_id, impart_dict)
    
    def delete(self, user_id: str) -> None:
        """删除传承信息"""
        self.storage.delete(self.filename, user_id)
    
    def exists(self, user_id: str) -> bool:
        """检查传承信息是否存在"""
        return self.storage.exists(self.filename, user_id)
    
    def get_impart_info(self, user_id: str) -> Optional[ImpartInfo]:
        """获取传承信息"""
        data = self.storage.get(self.filename, user_id)
        if not data:
            return None
        return self._to_domain(data)
    
    def create_impart_info(self, user_id: str) -> ImpartInfo:
        """创建传承信息"""
        impart_info = ImpartInfo(user_id=user_id)
        self.save(impart_info)
        return impart_info
    
    def update_impart_info(self, impart_info: ImpartInfo):
        """更新传承信息"""
        self.save(impart_info)

    def get_challenge_cooldown_time(self, user_id: str) -> int:
        """获取玩家上次真正发起传承挑战的时间。"""
        data = self.storage.get(self.COOLDOWN_FILENAME, str(user_id)) or {}
        return int(data.get("last_challenge_time", 0) or 0)

    def set_challenge_cooldown_time(self, user_id: str, timestamp: int) -> None:
        """记录玩家传承挑战冷却起点。"""
        self.storage.set(
            self.COOLDOWN_FILENAME,
            str(user_id),
            {"last_challenge_time": int(timestamp)}
        )

    def clear_challenge_cooldown(self, user_id: str) -> None:
        """战斗未能建立时撤销预占的冷却。"""
        user_id = str(user_id)
        if self.storage.exists(self.COOLDOWN_FILENAME, user_id):
            self.storage.delete(self.COOLDOWN_FILENAME, user_id)

    def get_daily_theft_losses(self, user_id: str, date_key: str) -> Dict[str, float]:
        """获取指定玩家当日各属性已经被抽取的实际加成量。"""
        data = self.storage.get(self.THEFT_LIMIT_FILENAME, str(user_id)) or {}
        if data.get("date") != date_key:
            return {}
        return {
            str(key): max(0.0, float(value))
            for key, value in data.get("losses", {}).items()
        }

    def add_daily_theft_loss(
        self,
        user_id: str,
        date_key: str,
        prop_key: str,
        loss: float
    ) -> float:
        """累加当日某项传承的实际损失，并返回累计值。"""
        losses = self.get_daily_theft_losses(user_id, date_key)
        losses[prop_key] = losses.get(prop_key, 0.0) + max(0.0, float(loss))
        self.storage.set(
            self.THEFT_LIMIT_FILENAME,
            str(user_id),
            {"date": date_key, "losses": losses}
        )
        return losses[prop_key]
    
    def get_ranking(self, limit: int = 10) -> List[tuple]:
        """获取传承排行榜
        
        Returns:
            List of (user_id, impart_atk_per, total_per)
        """
        results = self.storage.query(
            self.filename,
            sort_key=lambda data: data.get("impart_atk_per", 0.0),
            reverse=True,
            limit=limit
        )
        
        ranking = []
        for data in results:
            user_id = data["user_id"]
            impart_atk_per = data.get("impart_atk_per", 0.0)
            total_per = (
                data.get("impart_hp_per", 0.0) +
                data.get("impart_mp_per", 0.0) +
                data.get("impart_atk_per", 0.0) +
                data.get("impart_know_per", 0.0) +
                data.get("impart_burst_per", 0.0)
            )
            ranking.append((user_id, impart_atk_per, total_per))
        
        return ranking
    
    def _to_domain(self, data: Dict[str, Any]) -> ImpartInfo:
        """转换为领域模型"""
        return ImpartInfo(
            user_id=data["user_id"],
            impart_hp_per=data.get("impart_hp_per", 0.0),
            impart_mp_per=data.get("impart_mp_per", 0.0),
            impart_atk_per=data.get("impart_atk_per", 0.0),
            impart_know_per=data.get("impart_know_per", 0.0),
            impart_burst_per=data.get("impart_burst_per", 0.0),
            impart_mix_exp=data.get("impart_mix_exp", 0)
        )
    
    def _to_dict(self, impart: ImpartInfo) -> Dict[str, Any]:
        """转换为字典数据"""
        return {
            "user_id": impart.user_id,
            "impart_hp_per": impart.impart_hp_per,
            "impart_mp_per": impart.impart_mp_per,
            "impart_atk_per": impart.impart_atk_per,
            "impart_know_per": impart.impart_know_per,
            "impart_burst_per": impart.impart_burst_per,
            "impart_mix_exp": impart.impart_mix_exp
        }
