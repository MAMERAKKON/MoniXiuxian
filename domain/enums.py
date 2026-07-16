"""领域枚举类型"""
from enum import Enum


class CultivationType(str, Enum):
    """修炼类型"""
    SPIRITUAL = "灵修"  # 灵修
    PHYSICAL = "体修"  # 体修
    
    @classmethod
    def from_string(cls, value: str) -> "CultivationType":
        """从字符串转换"""
        value = value.strip()
        if value == "灵修":
            return cls.SPIRITUAL
        elif value == "体修":
            return cls.PHYSICAL
        else:
            raise ValueError(f"无效的修炼类型: {value}")


class PlayerState(str, Enum):
    """玩家状态"""
    IDLE = "空闲"  # 空闲
    CULTIVATING = "修炼中"  # 闭关中
    ADVENTURING = "历练中"  # 历练中
    IN_RIFT = "秘境探索中"  # 秘境探索中
    IN_COMBAT = "战斗中"  # 战斗中
    
    @classmethod
    def from_string(cls, value: str) -> "PlayerState":
        """
        从字符串转换为 PlayerState 枚举
        
        Args:
            value: 状态字符串值
            
        Returns:
            对应的 PlayerState 枚举
            
        Raises:
            ValueError: 当输入的状态值无效时
        """
        value = value.strip()
        for state in cls:
            if state.value == value:
                return state
        # 如果找不到匹配的状态，抛出异常
        valid_states = ", ".join([f"'{s.value}'" for s in cls])
        raise ValueError(f"无效的玩家状态: '{value}'。有效状态: {valid_states}")


class SpiritRootType(str, Enum):
    """灵根类型"""
    # 废灵根
    PSEUDO = "伪灵根"
    
    # 多灵根
    QUAD = "四灵根"
    TRI = "三灵根"
    DUAL = "双灵根"
    
    # 五行单灵根
    METAL = "金灵根"
    WOOD = "木灵根"
    WATER = "水灵根"
    FIRE = "火灵根"
    EARTH = "土灵根"
    
    # 变异灵根
    THUNDER = "雷灵根"
    ICE = "冰灵根"
    WIND = "风灵根"
    DARK = "暗灵根"
    LIGHT = "光灵根"
    
    # 天灵根
    HEAVENLY_METAL = "天金灵根"
    HEAVENLY_WOOD = "天木灵根"
    HEAVENLY_WATER = "天水灵根"
    HEAVENLY_FIRE = "天火灵根"
    HEAVENLY_EARTH = "天土灵根"
    
    # 传说级
    YIN_YANG = "阴阳灵根"
    FUSION = "融合灵根"
    
    # 神话级
    CHAOS = "混沌灵根"
    
    # 禁忌级体质
    INNATE_BODY = "先天道体"
    DIVINE_BODY = "神圣体质"


class ItemType(str, Enum):
    """物品类型"""
    WEAPON = "weapon"  # 武器/法器
    ARMOR = "armor"  # 防具
    MAIN_TECHNIQUE = "main_technique"  # 主修功法
    PILL = "pill"  # 丹药
    MATERIAL = "material"  # 材料
    STORAGE_RING = "storage_ring"  # 储物戒
    TREASURE = "treasure"  # 宝物


class ItemRarity(str, Enum):
    """物品稀有度"""
    COMMON = "普通"
    UNCOMMON = "优秀"
    RARE = "稀有"
    EPIC = "史诗"
    LEGENDARY = "传说"
    MYTHIC = "神话"


class SectPosition(int, Enum):
    """宗门职位"""
    LEADER = 0  # 宗主
    ELDER = 1  # 长老
    CORE_DISCIPLE = 2  # 亲传弟子
    INNER_DISCIPLE = 3  # 内门弟子
    OUTER_DISCIPLE = 4  # 外门弟子
