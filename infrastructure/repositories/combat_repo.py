"""战斗仓储层"""
import time
from typing import Optional, Dict, Any, List

from .base import BaseRepository
from ..storage import JSONStorage, TimestampConverter
from ...domain.models.combat import CombatCooldown


class CombatRepository(BaseRepository[CombatCooldown]):
    """战斗仓储"""
    
    def __init__(self, storage: JSONStorage):
        """
        初始化战斗仓储
        
        Args:
            storage: JSON存储管理器
        """
        super().__init__(storage, "combat_cooldowns.json")
        self.logs_filename = "combat_logs.json"
    
    def get_by_id(self, user_id: str) -> Optional[CombatCooldown]:
        """根据用户ID获取战斗冷却信息"""
        return self.get_combat_cooldown(user_id)
    
    def save(self, entity: CombatCooldown) -> None:
        """保存战斗冷却信息"""
        cooldown_dict = self._to_dict(entity)
        self.storage.set(self.filename, entity.user_id, cooldown_dict)
    
    def delete(self, user_id: str) -> None:
        """删除战斗冷却信息"""
        self.storage.delete(self.filename, user_id)
    
    def exists(self, user_id: str) -> bool:
        """检查战斗冷却信息是否存在"""
        return self.storage.exists(self.filename, user_id)
    
    def save_combat_log(
        self,
        attacker_id: str,
        defender_id: Optional[str],
        combat_type: str,
        winner_id: Optional[str],
        combat_log: str,
        gold_reward: int = 0,
        exp_reward: int = 0
    ) -> int:
        """
        保存战斗日志
        
        Args:
            attacker_id: 攻击者ID
            defender_id: 防御者ID（可能是玩家或Boss）
            combat_type: 战斗类型（spar/duel/boss）
            winner_id: 获胜者ID
            combat_log: 战斗日志（JSON字符串）
            gold_reward: 灵石奖励
            exp_reward: 修为奖励
            
        Returns:
            战斗日志ID
        """
        # 生成新的日志ID
        all_logs = self.storage.load(self.logs_filename)
        if all_logs:
            max_id = max(int(lid) for lid in all_logs.keys())
            new_id = max_id + 1
        else:
            new_id = 1
        
        log_data = {
            "id": new_id,
            "attacker_id": attacker_id,
            "defender_id": defender_id,
            "combat_type": combat_type,
            "winner_id": winner_id,
            "combat_log": combat_log,
            "gold_reward": gold_reward,
            "exp_reward": exp_reward,
            "created_at": TimestampConverter.to_iso8601(int(time.time()))
        }
        
        self.storage.set(self.logs_filename, str(new_id), log_data)
        return new_id
    
    def get_combat_cooldown(self, user_id: str) -> Optional[CombatCooldown]:
        """
        获取战斗冷却信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            战斗冷却信息，如果不存在返回None
        """
        data = self.storage.get(self.filename, user_id)
        
        if data is None:
            return None
        
        return self._to_domain(data)
    
    def update_duel_cooldown(self, user_id: str, timestamp: int):
        """
        更新决斗冷却时间
        
        Args:
            user_id: 用户ID
            timestamp: 时间戳
        """
        data = self.storage.get(self.filename, user_id)
        
        if data:
            data["last_duel_time"] = TimestampConverter.to_iso8601(timestamp)
        else:
            data = {
                "user_id": user_id,
                "last_duel_time": TimestampConverter.to_iso8601(timestamp),
                "last_spar_time": TimestampConverter.to_iso8601(0)
            }
        
        self.storage.set(self.filename, user_id, data)
    
    def update_spar_cooldown(self, user_id: str, timestamp: int):
        """
        更新切磋冷却时间
        
        Args:
            user_id: 用户ID
            timestamp: 时间戳
        """
        data = self.storage.get(self.filename, user_id)
        
        if data:
            data["last_spar_time"] = TimestampConverter.to_iso8601(timestamp)
        else:
            data = {
                "user_id": user_id,
                "last_duel_time": TimestampConverter.to_iso8601(0),
                "last_spar_time": TimestampConverter.to_iso8601(timestamp)
            }
        
        self.storage.set(self.filename, user_id, data)
    
    def get_recent_combat_logs(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[dict]:
        """
        获取最近的战斗日志
        
        Args:
            user_id: 用户ID
            limit: 返回数量限制
            
        Returns:
            战斗日志列表
        """
        results = self.storage.query(
            self.logs_filename,
            filter_fn=lambda data: (
                data.get("attacker_id") == user_id or
                data.get("defender_id") == user_id
            ),
            sort_key=lambda data: data.get("created_at", ""),
            reverse=True,
            limit=limit
        )
        
        logs = []
        for data in results:
            logs.append({
                'id': data['id'],
                'attacker_id': data['attacker_id'],
                'defender_id': data.get('defender_id'),
                'combat_type': data['combat_type'],
                'winner_id': data.get('winner_id'),
                'combat_log': data['combat_log'],
                'gold_reward': data.get('gold_reward', 0),
                'exp_reward': data.get('exp_reward', 0),
                'created_at': TimestampConverter.from_iso8601(data['created_at'])
            })
        
        return logs
    
    def _to_domain(self, data: Dict[str, Any]) -> CombatCooldown:
        """转换为领域模型"""
        return CombatCooldown(
            user_id=data["user_id"],
            last_duel_time=TimestampConverter.from_iso8601(data.get("last_duel_time", TimestampConverter.to_iso8601(0))),
            last_spar_time=TimestampConverter.from_iso8601(data.get("last_spar_time", TimestampConverter.to_iso8601(0)))
        )
    
    def _to_dict(self, cooldown: CombatCooldown) -> Dict[str, Any]:
        """转换为字典数据"""
        return {
            "user_id": cooldown.user_id,
            "last_duel_time": TimestampConverter.to_iso8601(cooldown.last_duel_time),
            "last_spar_time": TimestampConverter.to_iso8601(cooldown.last_spar_time)
        }
