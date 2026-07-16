"""灵根生成器"""
import random
from typing import Dict, List, Tuple

from ..core.config import ConfigManager
from ..domain.value_objects import SpiritRootInfo


class SpiritRootGenerator:
    """灵根生成器 - 负责随机生成灵根"""
    
    # 灵根池定义（按权重类别）
    ROOT_POOLS = {
        "PSEUDO": ["伪"],
        "QUAD": ["金木水火", "金木水土", "金木火土", "金水火土", "木水火土"],
        "TRI": ["金木水", "金木火", "金木土", "金水火", "金水土", "金火土", 
                "木水火", "木水土", "木火土", "水火土"],
        "DUAL": ["金木", "金水", "金火", "金土", "木水", "木火", "木土", 
                 "水火", "水土", "火土"],
        "WUXING": ["金", "木", "水", "火", "土"],
        "VARIANT": ["雷", "冰", "风", "暗", "光"],
        "HEAVENLY": ["天金", "天木", "天水", "天火", "天土", "天雷"],
        "LEGENDARY": ["阴阳", "融合"],
        "MYTHIC": ["混沌"],
        "DIVINE_BODY": ["先天道体", "神圣体质"]
    }
    
    # 灵根描述
    ROOT_DESCRIPTIONS = {
        "伪": "【废柴】资质低劣，修炼如龟速",
        
        # 四灵根
        "金木水火": "【凡品】四灵根杂乱，资质平庸",
        "金木水土": "【凡品】四灵根杂乱，资质平庸",
        "金木火土": "【凡品】四灵根杂乱，资质平庸",
        "金水火土": "【凡品】四灵根杂乱，资质平庸",
        "木水火土": "【凡品】四灵根杂乱，资质平庸",
        
        # 三灵根
        "金木水": "【凡品】三灵根较杂，资质一般",
        "金木火": "【凡品】三灵根较杂，资质一般",
        "金木土": "【凡品】三灵根较杂，资质一般",
        "金水火": "【凡品】三灵根较杂，资质一般",
        "金水土": "【凡品】三灵根较杂，资质一般",
        "金火土": "【凡品】三灵根较杂，资质一般",
        "木水火": "【凡品】三灵根较杂，资质一般",
        "木水土": "【凡品】三灵根较杂，资质一般",
        "木火土": "【凡品】三灵根较杂，资质一般",
        "水火土": "【凡品】三灵根较杂，资质一般",
        
        # 双灵根
        "金木": "【良品】双灵根，较为常见",
        "金水": "【良品】双灵根，较为常见",
        "金火": "【良品】双灵根，较为常见",
        "金土": "【良品】双灵根，较为常见",
        "木水": "【良品】双灵根，较为常见",
        "木火": "【良品】双灵根，较为常见",
        "木土": "【良品】双灵根，较为常见",
        "水火": "【良品】双灵根，较为常见",
        "水土": "【良品】双灵根，较为常见",
        "火土": "【良品】双灵根，较为常见",
        
        # 五行单灵根
        "金": "【上品】金之精华，锋锐无双",
        "木": "【上品】木之生机，生生不息",
        "水": "【上品】水之灵韵，柔中带刚",
        "火": "【上品】火之烈焰，霸道无匹",
        "土": "【上品】土之厚重，稳如磐石",
        
        # 变异灵根
        "雷": "【稀有】天地雷霆，毁灭之力",
        "冰": "【稀有】极寒冰封，万物凝固",
        "风": "【稀有】疾风骤雨，来去无踪",
        "暗": "【稀有】幽暗深邃，诡异莫测",
        "光": "【稀有】神圣光明，普照万物",
        
        # 天灵根
        "天金": "【极品】天选之子，金之极致",
        "天木": "【极品】天选之子，木之极致",
        "天水": "【极品】天选之子，水之极致",
        "天火": "【极品】天选之子，火之极致",
        "天土": "【极品】天选之子，土之极致",
        "天雷": "【极品】天选之子，雷之极致",
        
        # 传说级
        "阴阳": "【传说】阴阳调和，造化玄机",
        "融合": "【传说】五行融合，万法归一",
        
        # 神话级
        "混沌": "【神话】混沌初开，包罗万象",
        
        # 禁忌级
        "先天道体": "【禁忌】天生道体，与天地同寿",
        "神圣体质": "【禁忌】神之后裔，天赋异禀"
    }
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
    
    def generate_random_root(self) -> SpiritRootInfo:
        """
        基于权重随机生成灵根
        
        Returns:
            灵根信息
        """
        settings = self.config_manager.settings
        weights = settings.spirit_root_weights
        speeds = settings.spirit_root_speeds
        
        # 构建权重池
        weight_pool: List[Tuple[str, str]] = []
        
        # 伪灵根
        weight_pool.extend([("PSEUDO", root) for root in self.ROOT_POOLS["PSEUDO"]] * weights.pseudo_root_weight)
        
        # 四灵根
        weight_pool.extend([("QUAD", root) for root in self.ROOT_POOLS["QUAD"]] * weights.quad_root_weight)
        
        # 三灵根
        weight_pool.extend([("TRI", root) for root in self.ROOT_POOLS["TRI"]] * weights.tri_root_weight)
        
        # 双灵根
        weight_pool.extend([("DUAL", root) for root in self.ROOT_POOLS["DUAL"]] * weights.dual_root_weight)
        
        # 五行单灵根
        weight_pool.extend([("WUXING", root) for root in self.ROOT_POOLS["WUXING"]] * weights.wuxing_root_weight)
        
        # 变异灵根
        weight_pool.extend([("VARIANT", root) for root in self.ROOT_POOLS["VARIANT"]] * weights.variant_root_weight)
        
        # 天灵根
        weight_pool.extend([("HEAVENLY", root) for root in self.ROOT_POOLS["HEAVENLY"]] * weights.heavenly_root_weight)
        
        # 传说级
        weight_pool.extend([("LEGENDARY", root) for root in self.ROOT_POOLS["LEGENDARY"]] * weights.legendary_root_weight)
        
        # 神话级
        weight_pool.extend([("MYTHIC", root) for root in self.ROOT_POOLS["MYTHIC"]] * weights.mythic_root_weight)
        
        # 禁忌级体质
        weight_pool.extend([("DIVINE_BODY", root) for root in self.ROOT_POOLS["DIVINE_BODY"]] * weights.divine_body_weight)
        
        if not weight_pool:
            # 兜底方案：默认返回金灵根
            return SpiritRootInfo(
                name="金",
                speed_multiplier=speeds.wuxing_root_speed,
                description=self.ROOT_DESCRIPTIONS["金"]
            )
        
        # 随机选择
        category, root_name = random.choice(weight_pool)
        
        # 获取速度倍率
        speed_multiplier = self._get_speed_multiplier(category, root_name, speeds)
        
        # 获取描述
        description = self.ROOT_DESCRIPTIONS.get(root_name, "【未知】神秘的灵根")
        
        return SpiritRootInfo(
            name=root_name,
            speed_multiplier=speed_multiplier,
            description=description
        )
    
    def _get_speed_multiplier(self, category: str, root_name: str, speeds) -> float:
        """获取灵根速度倍率"""
        if category == "PSEUDO":
            return speeds.pseudo_root_speed
        elif category == "QUAD":
            return speeds.quad_root_speed
        elif category == "TRI":
            return speeds.tri_root_speed
        elif category == "DUAL":
            return speeds.dual_root_speed
        elif category == "WUXING":
            return speeds.wuxing_root_speed
        elif category == "VARIANT":
            # 根据具体灵根返回对应速度
            if root_name == "雷":
                return speeds.thunder_root_speed
            elif root_name == "冰":
                return speeds.ice_root_speed
            elif root_name == "风":
                return speeds.wind_root_speed
            elif root_name == "暗":
                return speeds.dark_root_speed
            elif root_name == "光":
                return speeds.light_root_speed
            return speeds.thunder_root_speed  # 默认
        elif category == "HEAVENLY":
            return speeds.heavenly_root_speed
        elif category == "LEGENDARY":
            if root_name == "阴阳":
                return speeds.yin_yang_root_speed
            elif root_name == "融合":
                return speeds.fusion_root_speed
            return speeds.yin_yang_root_speed  # 默认
        elif category == "MYTHIC":
            return speeds.chaos_root_speed
        elif category == "DIVINE_BODY":
            if root_name == "先天道体":
                return speeds.innate_body_speed
            elif root_name == "神圣体质":
                return speeds.divine_body_speed
            return speeds.innate_body_speed  # 默认
        else:
            return 1.0
    
    def get_root_speed_by_name(self, root_name: str) -> float:
        """
        根据灵根名称获取速度倍率
        
        Args:
            root_name: 灵根名称（不含"灵根"后缀）
            
        Returns:
            速度倍率
        """
        # 去掉"灵根"后缀
        root_name = root_name.replace("灵根", "")
        
        speeds = self.config_manager.settings.spirit_root_speeds
        
        # 查找灵根所属类别
        for category, roots in self.ROOT_POOLS.items():
            if root_name in roots:
                return self._get_speed_multiplier(category, root_name, speeds)
        
        # 默认返回1.0
        return 1.0
