"""灵田服务"""
import time
from typing import List, Dict

from ...core.config import ConfigManager
from ...core.exceptions import GameException
from ...domain.models.spirit_farm import SpiritFarm, SpiritFarmInfo, Crop
from ...infrastructure.repositories.player_repo import PlayerRepository
from ...infrastructure.repositories.spirit_farm_repo import SpiritFarmRepository
from ...infrastructure.repositories.storage_ring_repo import StorageRingRepository


class SpiritFarmService:
    """灵田服务"""
    
    # 灵草配置 (wither_time: 成熟后枯萎时间，默认48小时)
    SPIRIT_HERBS = {
        "灵草": {"grow_time": 3600, "exp_yield": 500, "gold_yield": 100, "wither_time": 172800},
        "血灵草": {"grow_time": 7200, "exp_yield": 1500, "gold_yield": 300, "wither_time": 172800},
        "冰心草": {"grow_time": 14400, "exp_yield": 4000, "gold_yield": 800, "wither_time": 172800},
        "火焰花": {"grow_time": 28800, "exp_yield": 10000, "gold_yield": 2000, "wither_time": 172800},
        "九叶灵芝": {"grow_time": 86400, "exp_yield": 30000, "gold_yield": 6000, "wither_time": 172800},
    }
    
    # 灵田等级配置
    FARM_LEVELS = {
        1: {"slots": 3, "upgrade_cost": 5000},
        2: {"slots": 5, "upgrade_cost": 15000},
        3: {"slots": 8, "upgrade_cost": 50000},
        4: {"slots": 12, "upgrade_cost": 150000},
        5: {"slots": 20, "upgrade_cost": 0},  # 最高级
    }
    
    def __init__(
        self,
        player_repo: PlayerRepository,
        spirit_farm_repo: SpiritFarmRepository,
        storage_ring_repo: StorageRingRepository,
        config_manager: ConfigManager
    ):
        self.player_repo = player_repo
        self.spirit_farm_repo = spirit_farm_repo
        self.storage_ring_repo = storage_ring_repo
        self.config_manager = config_manager
    
    def get_farm_info(self, user_id: str) -> SpiritFarmInfo:
        """获取灵田信息"""
        # 获取玩家
        player = self.player_repo.get_player(user_id)
        if not player:
            raise GameException("你还未踏入修仙之路")
        
        # 获取灵田
        farm = self.spirit_farm_repo.get_spirit_farm(user_id)
        if not farm:
            raise GameException("你还没有灵田")
        
        # 获取配置
        level_config = self.FARM_LEVELS.get(farm.level, self.FARM_LEVELS[1])
        max_slots = level_config["slots"]
        can_upgrade = farm.level < 5
        upgrade_cost = level_config.get("upgrade_cost", 0) if can_upgrade else 0
        
        return SpiritFarmInfo(
            level=farm.level,
            max_slots=max_slots,
            used_slots=len(farm.crops),
            crops=farm.crops,
            upgrade_cost=upgrade_cost,
            can_upgrade=can_upgrade
        )
    
    def create_farm(self, user_id: str) -> str:
        """开垦灵田"""
        # 获取玩家
        player = self.player_repo.get_player(user_id)
        if not player:
            raise GameException("你还未踏入修仙之路")
        
        # 检查是否已有灵田
        existing = self.spirit_farm_repo.get_spirit_farm(user_id)
        if existing:
            raise GameException("❌ 你已经拥有灵田了！")
        
        cost = 10000
        if player.gold < cost:
            raise GameException(f"❌ 开垦灵田需要 {cost:,} 灵石")
        
        # 扣除灵石
        self.player_repo.add_gold(user_id, -cost)
        
        # 创建灵田
        self.spirit_farm_repo.create_spirit_farm(user_id)
        
        return (
            "🌱 灵田开垦成功！\n"
            "━━━━━━━━━━━━━━━\n"
            "灵田等级：Lv.1\n"
            "种植格数：3\n"
            "━━━━━━━━━━━━━━━\n"
            "可种植：灵草、血灵草、冰心草..."
        )
    
    def plant_herb(self, user_id: str, herb_name: str) -> str:
        """种植灵草"""
        if herb_name not in self.SPIRIT_HERBS:
            herbs_list = "、".join(self.SPIRIT_HERBS.keys())
            raise GameException(f"❌ 未知的灵草。可种植：{herbs_list}")
        
        # 获取玩家
        player = self.player_repo.get_player(user_id)
        if not player:
            raise GameException("你还未踏入修仙之路")
        
        # 获取灵田
        farm = self.spirit_farm_repo.get_spirit_farm(user_id)
        if not farm:
            raise GameException("❌ 你还没有灵田！使用 开垦灵田")
        
        # 检查槽位
        if not farm.has_available_slot():
            max_slots = farm.get_max_slots()
            raise GameException(f"❌ 灵田已满！最多种植 {max_slots} 株")
        
        # 种植
        herb_config = self.SPIRIT_HERBS[herb_name]
        plant_time = int(time.time())
        mature_time = plant_time + herb_config["grow_time"]
        wither_time = mature_time + herb_config["wither_time"]
        
        # 找到下一个可用槽位
        used_slots = [c.slot for c in farm.crops]
        next_slot = 1
        while next_slot in used_slots:
            next_slot += 1
        
        new_crop = Crop(
            name=herb_name,
            plant_time=plant_time,
            mature_time=mature_time,
            wither_time=wither_time,
            slot=next_slot
        )
        
        farm.crops.append(new_crop)
        self.spirit_farm_repo.update_crops(user_id, farm.crops)
        
        grow_hours = herb_config["grow_time"] // 3600
        return (
            f"🌱 成功种植【{herb_name}】！\n"
            f"成熟时间：约 {grow_hours} 小时\n"
            f"当前种植：{len(farm.crops)}/{farm.get_max_slots()}"
        )
    
    def harvest(self, user_id: str) -> str:
        """收获灵草"""
        # 获取玩家
        player = self.player_repo.get_player(user_id)
        if not player:
            raise GameException("你还未踏入修仙之路")
        
        # 获取灵田
        farm = self.spirit_farm_repo.get_spirit_farm(user_id)
        if not farm:
            raise GameException("❌ 你还没有灵田！")
        
        if not farm.crops:
            raise GameException("❌ 灵田里没有种植任何灵草")
        
        now = int(time.time())
        mature_crops = []
        withered_crops = []
        remaining_crops = []
        
        for crop in farm.crops:
            if crop.is_withered(now):
                withered_crops.append(crop)
            elif crop.is_mature(now):
                mature_crops.append(crop)
            else:
                remaining_crops.append(crop)
        
        if not mature_crops and not withered_crops:
            raise GameException("❌ 没有成熟的灵草可以收获")
        
        # 计算奖励（只有成熟未枯萎的才有收益）
        total_exp = 0
        total_gold = 0
        harvest_details = []
        herb_counts: Dict[str, int] = {}
        
        for crop in mature_crops:
            herb_name = crop.name
            herb_config = self.SPIRIT_HERBS.get(herb_name, self.SPIRIT_HERBS["灵草"])
            total_exp += herb_config["exp_yield"]
            total_gold += herb_config["gold_yield"]
            harvest_details.append(herb_name)
            herb_counts[herb_name] = herb_counts.get(herb_name, 0) + 1
        
        # 应用奖励
        if total_exp > 0:
            self.player_repo.add_experience(user_id, total_exp)
        if total_gold > 0:
            self.player_repo.add_gold(user_id, total_gold)
        
        # 将灵草存入储物戒
        stored_items = []
        for herb_name, count in herb_counts.items():
            try:
                self.storage_ring_repo.add_item(user_id, herb_name, count)
                stored_items.append(f"{herb_name}×{count}")
            except GameException:
                stored_items.append(f"{herb_name}×{count}（储物戒已满，丢失）")
        
        # 更新灵田
        self.spirit_farm_repo.update_crops(user_id, remaining_crops)
        
        # 构建返回消息
        msg_lines = ["🌾 收获结果", "━━━━━━━━━━━━━━━"]
        
        if harvest_details:
            msg_lines.append(f"收获：{', '.join(harvest_details)}")
            msg_lines.append(f"获得修为：+{total_exp:,}")
            msg_lines.append(f"获得灵石：+{total_gold:,}")
            if stored_items:
                msg_lines.append("📦 存入储物戒：")
                for item in stored_items:
                    msg_lines.append(f"  {item}")
        
        if withered_crops:
            withered_names = [c.name for c in withered_crops]
            msg_lines.append(f"💀 枯萎清除：{', '.join(withered_names)}（共{len(withered_crops)}株）")
        
        msg_lines.append("━━━━━━━━━━━━━━━")
        msg_lines.append(f"剩余种植：{len(remaining_crops)} 株")
        
        return "\n".join(msg_lines)
    
    def upgrade_farm(self, user_id: str) -> str:
        """升级灵田"""
        # 获取玩家
        player = self.player_repo.get_player(user_id)
        if not player:
            raise GameException("你还未踏入修仙之路")
        
        # 获取灵田
        farm = self.spirit_farm_repo.get_spirit_farm(user_id)
        if not farm:
            raise GameException("❌ 你还没有灵田！")
        
        if farm.level >= 5:
            raise GameException("❌ 灵田已达最高等级！")
        
        level_config = self.FARM_LEVELS.get(farm.level, self.FARM_LEVELS[1])
        cost = level_config["upgrade_cost"]
        
        if player.gold < cost:
            raise GameException(f"❌ 升级需要 {cost:,} 灵石")
        
        # 扣除灵石
        self.player_repo.add_gold(user_id, -cost)
        
        # 升级
        new_level = farm.level + 1
        self.spirit_farm_repo.update_level(user_id, new_level)
        
        new_slots = self.FARM_LEVELS[new_level]["slots"]
        return f"🎉 灵田升级到 Lv.{new_level}！格数增加到 {new_slots}"
