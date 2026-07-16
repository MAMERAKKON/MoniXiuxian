"""
装备领域模型

定义装备相关的领域模型，包括武器、防具、功法等。
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
from ..enums import ItemType, ItemRarity


@dataclass
class EquipmentStats:
    """装备属性加成"""
    magic_damage: int = 0  # 法攻
    physical_damage: int = 0  # 物攻
    magic_defense: int = 0  # 法防
    physical_defense: int = 0  # 物防
    mental_power: int = 0  # 神念
    max_hp: int = 0  # 气血上限
    spiritual_qi: int = 0  # 灵气
    exp_multiplier: float = 0.0  # 修炼倍率
    
    # 旧版兼容字段
    attack: int = 0  # 攻击力（旧版）
    defense: int = 0  # 防御力（旧版）
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "magic_damage": self.magic_damage,
            "physical_damage": self.physical_damage,
            "magic_defense": self.magic_defense,
            "physical_defense": self.physical_defense,
            "mental_power": self.mental_power,
            "max_hp": self.max_hp,
            "spiritual_qi": self.spiritual_qi,
            "exp_multiplier": self.exp_multiplier,
            "attack": self.attack,
            "defense": self.defense,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EquipmentStats":
        """从字典创建"""
        return cls(
            magic_damage=data.get("magic_damage", 0),
            physical_damage=data.get("physical_damage", 0),
            magic_defense=data.get("magic_defense", 0),
            physical_defense=data.get("physical_defense", 0),
            mental_power=data.get("mental_power", 0),
            max_hp=data.get("max_hp", 0),
            spiritual_qi=data.get("spiritual_qi", 0),
            exp_multiplier=data.get("exp_multiplier", 0.0),
            attack=data.get("attack", 0),
            defense=data.get("defense", 0),
        )


@dataclass
class Equipment:
    """装备领域模型"""
    id: str  # 装备ID
    name: str  # 装备名称
    type: ItemType  # 装备类型
    rank: ItemRarity  # 装备品阶
    description: str  # 装备描述
    required_level_index: int  # 需求等级索引
    stats: EquipmentStats  # 属性加成
    price: int  # 价格
    
    # 武器特有属性
    weapon_category: Optional[str] = None  # 武器类别（剑、刀、枪等）
    
    # 旧版兼容字段
    subtype: Optional[str] = None  # 子类型（武器、防具、饰品）
    equip_effects: Optional[Dict[str, Any]] = None  # 装备效果（旧版）
    
    def __post_init__(self):
        """初始化后处理"""
        # 如果有旧版装备效果，转换为新版属性
        if self.equip_effects:
            if "attack" in self.equip_effects:
                self.stats.attack = self.equip_effects["attack"]
            if "defense" in self.equip_effects:
                self.stats.defense = self.equip_effects["defense"]
            if "max_hp" in self.equip_effects:
                self.stats.max_hp = self.equip_effects["max_hp"]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = {
            "id": self.id,
            "name": self.name,
            "type": self.type.value if isinstance(self.type, ItemType) else self.type,
            "rank": self.rank.value if isinstance(self.rank, ItemRarity) else self.rank,
            "description": self.description,
            "required_level_index": self.required_level_index,
            "stats": self.stats.to_dict(),
            "price": self.price,
        }
        
        if self.weapon_category:
            data["weapon_category"] = self.weapon_category
        if self.subtype:
            data["subtype"] = self.subtype
        if self.equip_effects:
            data["equip_effects"] = self.equip_effects
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Equipment":
        """从字典创建"""
        # 处理类型
        item_type = data.get("type", "")
        if isinstance(item_type, str):
            # 尝试从ItemType枚举中获取
            try:
                item_type = ItemType(item_type)
            except ValueError:
                # 如果不在枚举中，保持字符串
                pass
        
        # 处理品阶
        rank = data.get("rank", "凡品")
        if isinstance(rank, str):
            try:
                rank = ItemRarity(rank)
            except ValueError:
                rank = ItemRarity.COMMON
        
        # 处理属性加成
        stats_data = {}
        
        # 新版属性字段
        for field in ["magic_damage", "physical_damage", "magic_defense", 
                     "physical_defense", "mental_power", "max_hp", 
                     "spiritual_qi", "exp_multiplier"]:
            if field in data:
                stats_data[field] = data[field]
        
        # 旧版装备效果
        equip_effects = data.get("equip_effects", {})
        if equip_effects:
            stats_data["attack"] = equip_effects.get("attack", 0)
            stats_data["defense"] = equip_effects.get("defense", 0)
            stats_data["max_hp"] = equip_effects.get("max_hp", 0)
        
        stats = EquipmentStats.from_dict(stats_data)
        
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            type=item_type,
            rank=rank,
            description=data.get("description", ""),
            required_level_index=data.get("required_level_index", 0),
            stats=stats,
            price=data.get("price", 0),
            weapon_category=data.get("weapon_category"),
            subtype=data.get("subtype"),
            equip_effects=equip_effects if equip_effects else None,
        )


@dataclass
class EquippedItems:
    """已装备物品"""
    weapon: Optional[Equipment] = None  # 武器
    armor: Optional[Equipment] = None  # 防具
    main_technique: Optional[Equipment] = None  # 主功法
    techniques: list[Equipment] = None  # 副功法列表（最多3个）
    
    def __post_init__(self):
        """初始化后处理"""
        if self.techniques is None:
            self.techniques = []
    
    def get_total_stats(self) -> EquipmentStats:
        """获取所有装备的总属性加成"""
        total = EquipmentStats()
        
        for equipment in [self.weapon, self.armor, self.main_technique] + self.techniques:
            if equipment:
                total.magic_damage += equipment.stats.magic_damage
                total.physical_damage += equipment.stats.physical_damage
                total.magic_defense += equipment.stats.magic_defense
                total.physical_defense += equipment.stats.physical_defense
                total.mental_power += equipment.stats.mental_power
                total.max_hp += equipment.stats.max_hp
                total.spiritual_qi += equipment.stats.spiritual_qi
                total.exp_multiplier += equipment.stats.exp_multiplier
                total.attack += equipment.stats.attack
                total.defense += equipment.stats.defense
        
        return total
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "weapon": self.weapon.to_dict() if self.weapon else None,
            "armor": self.armor.to_dict() if self.armor else None,
            "main_technique": self.main_technique.to_dict() if self.main_technique else None,
            "techniques": [t.to_dict() for t in self.techniques],
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EquippedItems":
        """从字典创建"""
        return cls(
            weapon=Equipment.from_dict(data["weapon"]) if data.get("weapon") else None,
            armor=Equipment.from_dict(data["armor"]) if data.get("armor") else None,
            main_technique=Equipment.from_dict(data["main_technique"]) if data.get("main_technique") else None,
            techniques=[Equipment.from_dict(t) for t in data.get("techniques", [])],
        )
