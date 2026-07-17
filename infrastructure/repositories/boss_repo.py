"""Boss仓储"""
import time
from typing import Optional, Dict, Any

from .base import BaseRepository
from ..storage import JSONStorage, TimestampConverter
from ...domain.models.boss import Boss


class BossRepository(BaseRepository[Boss]):
    """Boss仓储"""

    SYSTEM_FILENAME = "boss_system.json"
    
    def __init__(self, storage: JSONStorage):
        """
        初始化Boss仓储
        
        Args:
            storage: JSON存储管理器
        """
        super().__init__(storage, "bosses.json")
    
    def get_by_id(self, boss_id: str) -> Optional[Boss]:
        """根据ID获取Boss"""
        return self.get_boss_by_id(int(boss_id))
    
    def save(self, entity: Boss) -> None:
        """保存Boss（创建或更新）"""
        boss_dict = self._to_dict(entity)
        self.storage.set(self.filename, str(entity.boss_id), boss_dict)
    
    def delete(self, boss_id: str) -> None:
        """删除Boss"""
        self.storage.delete(self.filename, boss_id)
    
    def exists(self, boss_id: str) -> bool:
        """检查Boss是否存在"""
        return self.storage.exists(self.filename, boss_id)
    
    def get_active_boss(self) -> Optional[Boss]:
        """获取当前存活的Boss"""
        results = self.storage.query(
            self.filename,
            filter_fn=lambda data: data.get("status") == 1
        )
        
        if not results:
            return None
        
        return self._to_domain(results[0])
    
    def get_boss_by_id(self, boss_id: int) -> Optional[Boss]:
        """根据ID获取Boss"""
        data = self.storage.get(self.filename, str(boss_id))
        
        if not data:
            return None
        
        return self._to_domain(data)
    
    def create_boss(self, boss: Boss) -> int:
        """创建Boss"""
        # 生成新的 boss_id
        all_data = self.storage.load(self.filename)
        if all_data:
            max_id = max(int(bid) for bid in all_data.keys())
            new_id = max_id + 1
        else:
            new_id = 1
        
        boss.boss_id = new_id
        
        # 保存
        boss_dict = self._to_dict(boss)
        self.storage.set(self.filename, str(new_id), boss_dict)
        
        return new_id
    
    def update_boss(self, boss: Boss) -> None:
        """更新Boss"""
        boss_dict = self._to_dict(boss)
        self.storage.set(self.filename, str(boss.boss_id), boss_dict)
    
    def defeat_boss(self, boss_id: int) -> None:
        """标记Boss为已击败"""
        data = self.storage.get(self.filename, str(boss_id))
        if data:
            data["status"] = 0
            self.storage.set(self.filename, str(boss_id), data)

    def has_any_boss(self) -> bool:
        """是否存在过Boss记录。"""
        return bool(self.storage.load(self.filename))

    def get_next_spawn_time(self) -> int:
        """获取下一只Boss的预定生成时间。"""
        data = self.storage.get(self.SYSTEM_FILENAME, "global") or {}
        value = data.get("next_spawn_time")
        if not value:
            return 0
        if isinstance(value, (int, float)):
            return int(value)
        return TimestampConverter.from_iso8601(value) or 0

    def set_next_spawn_time(self, spawn_time: int) -> None:
        """持久化下一只Boss的预定生成时间。"""
        self.storage.set(
            self.SYSTEM_FILENAME,
            "global",
            {"next_spawn_time": TimestampConverter.to_iso8601(spawn_time)}
        )

    def clear_next_spawn_time(self) -> None:
        """清除已经完成的生成计划。"""
        if self.storage.exists(self.SYSTEM_FILENAME, "global"):
            self.storage.delete(self.SYSTEM_FILENAME, "global")
    
    def _to_domain(self, data: Dict[str, Any]) -> Boss:
        """转换为领域模型"""
        return Boss(
            boss_id=data["boss_id"],
            boss_name=data["boss_name"],
            boss_level=data["boss_level"],
            hp=data["hp"],
            max_hp=data["max_hp"],
            atk=data["atk"],
            defense=data["defense"],
            stone_reward=data["stone_reward"],
            create_time=TimestampConverter.from_iso8601(data["create_time"]),
            status=data["status"],
            boss_type=str(data.get("boss_type", "blood_sea")),
            damage_type=(
                data.get("damage_type")
                if data.get("damage_type") in {"physical", "magic"}
                else "physical"
            ),
            exp_reward=int(data.get("exp_reward", data.get("stone_reward", 0) * 3)),
            reference_power=int(data.get("reference_power", 0)),
            target_participants=int(data.get("target_participants", 1)),
            damage_records={
                str(user_id): int(damage)
                for user_id, damage in data.get("damage_records", {}).items()
            },
            participant_names={
                str(user_id): str(name)
                for user_id, name in data.get("participant_names", {}).items()
            },
            last_regen_time=(
                TimestampConverter.from_iso8601(data.get("last_regen_time"))
                or int(time.time())
            ),
            regen_remainder=float(data.get("regen_remainder", 0.0))
        )
    
    def _to_dict(self, boss: Boss) -> Dict[str, Any]:
        """转换为字典数据"""
        return {
            "boss_id": boss.boss_id,
            "boss_name": boss.boss_name,
            "boss_level": boss.boss_level,
            "hp": boss.hp,
            "max_hp": boss.max_hp,
            "atk": boss.atk,
            "defense": boss.defense,
            "stone_reward": boss.stone_reward,
            "create_time": TimestampConverter.to_iso8601(boss.create_time),
            "status": boss.status,
            "boss_type": boss.boss_type,
            "damage_type": boss.damage_type,
            "exp_reward": boss.exp_reward,
            "reference_power": boss.reference_power,
            "target_participants": boss.target_participants,
            "damage_records": boss.damage_records,
            "participant_names": boss.participant_names,
            "last_regen_time": TimestampConverter.to_iso8601(boss.last_regen_time),
            "regen_remainder": boss.regen_remainder
        }
