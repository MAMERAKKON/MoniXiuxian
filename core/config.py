"""配置管理系统"""
import json
from pathlib import Path
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field

from astrbot.api import logger

from .exceptions import ConfigurationException


class AccessControlConfig(BaseModel):
    """访问控制配置"""
    whitelist_groups: List[str] = Field(default_factory=list)
    shop_managers: List[str] = Field(default_factory=list)
    boss_admins: List[str] = Field(default_factory=list)
    admins: List[str] = Field(default_factory=list)  # 全局管理员列表


class ValuesConfig(BaseModel):
    """核心数值配置"""
    initial_gold: int = 100
    base_exp_per_minute: int = 100
    check_in_gold_min: int = 50
    check_in_gold_max: int = 500
    breakthrough_death_probability: List[float] = Field(default_factory=lambda: [0.01, 0.1])
    pavilion_refresh_hours: int = 6
    pavilion_pill_count: int = 10
    pavilion_weapon_count: int = 10
    pavilion_treasure_count: int = 15
    shop_discount_min: float = 0.8
    shop_discount_max: float = 1.2
    shop_stock_divisor: int = 100


class SpiritRootSpeedsConfig(BaseModel):
    """灵根修炼速度倍率配置"""
    pseudo_root_speed: float = 0.5
    quad_root_speed: float = 0.6
    tri_root_speed: float = 0.75
    dual_root_speed: float = 0.9
    wuxing_root_speed: float = 1.0
    thunder_root_speed: float = 1.3
    ice_root_speed: float = 1.25
    wind_root_speed: float = 1.25
    dark_root_speed: float = 1.3
    light_root_speed: float = 1.3
    heavenly_root_speed: float = 1.5
    yin_yang_root_speed: float = 1.8
    fusion_root_speed: float = 1.8
    chaos_root_speed: float = 2.0
    innate_body_speed: float = 2.5
    divine_body_speed: float = 2.3


class SpiritRootWeightsConfig(BaseModel):
    """灵根抽取权重配置"""
    pseudo_root_weight: int = 1
    quad_root_weight: int = 10
    tri_root_weight: int = 30
    dual_root_weight: int = 100
    wuxing_root_weight: int = 200
    variant_root_weight: int = 20
    heavenly_root_weight: int = 5
    legendary_root_weight: int = 2
    mythic_root_weight: int = 1
    divine_body_weight: int = 1


class FilesConfig(BaseModel):
    """文件路径配置"""
    database_file: str = "astrbot_plugin_monixiuxianv3.db"


class DatabaseConfig(BaseModel):
    """数据库配置"""
    path: str = "astrbot_plugin_monixiuxianv3.db"
    echo: bool = False
    pool_size: int = 5
    max_overflow: int = 10


class JSONStorageConfig(BaseModel):
    """JSON 存储配置"""
    data_dir: str = "data/json"
    enable_cache: bool = True
    lock_timeout: int = 30
    max_backups: int = 3


class Settings(BaseModel):
    """全局配置"""
    access_control: AccessControlConfig = Field(default_factory=AccessControlConfig)
    values: ValuesConfig = Field(default_factory=ValuesConfig)
    spirit_root_speeds: SpiritRootSpeedsConfig = Field(default_factory=SpiritRootSpeedsConfig)
    spirit_root_weights: SpiritRootWeightsConfig = Field(default_factory=SpiritRootWeightsConfig)
    files: FilesConfig = Field(default_factory=FilesConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    json_storage: JSONStorageConfig = Field(default_factory=JSONStorageConfig)


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: Optional[Path] = None, astrbot_config: Optional[Dict] = None):
        """
        初始化配置管理器
        
        Args:
            config_dir: 配置文件目录，默认为 config/
            astrbot_config: AstrBot 配置字典
        """
        self.config_dir = config_dir or Path(__file__).parent.parent / "config"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self._astrbot_config = astrbot_config or {}
        self._settings: Optional[Settings] = None
        self._level_config: Optional[Dict] = None
        self._body_level_config: Optional[Dict] = None
        self._items_config: Optional[Dict] = None
        self._pills_config: Optional[Dict] = None
        self._weapons_config: Optional[Dict] = None
    
    @property
    def settings(self) -> Settings:
        """获取全局配置"""
        if self._settings is None:
            self._settings = self._load_settings()
        return self._settings
    
    def _load_settings(self) -> Settings:
        """加载全局配置（从 AstrBot 配置）"""
        try:
            # 从 AstrBot 配置中读取
            settings_data = {}
            
            # 调试日志：显示接收到的配置
            logger.info(f"【修仙V3】加载配置，AstrBot配置内容: {self._astrbot_config}")
            logger.info(f"【修仙V3】配置类型: {type(self._astrbot_config)}")
            
            # 如果 astrbot_config 本身就是配置字典，直接使用
            # AstrBot 传递的格式可能是: {"INITIAL_GOLD": 1000, ...} 而不是 {"VALUES": {"INITIAL_GOLD": 1000}}
            if isinstance(self._astrbot_config, dict):
                # 检查是否有嵌套的 VALUES 键
                if "VALUES" in self._astrbot_config:
                    # 有嵌套结构，按原逻辑处理
                    v = self._astrbot_config["VALUES"]
                else:
                    # 没有嵌套，直接使用顶层配置
                    v = self._astrbot_config
                
                initial_gold = v.get("INITIAL_GOLD", 100)
                logger.info(f"【修仙V3】从配置读取初始灵石: {initial_gold}")
                settings_data["values"] = {
                    "initial_gold": initial_gold,
                    "base_exp_per_minute": v.get("BASE_EXP_PER_MINUTE", 100),
                    "check_in_gold_min": v.get("CHECK_IN_GOLD_MIN", 50),
                    "check_in_gold_max": v.get("CHECK_IN_GOLD_MAX", 500),
                    "breakthrough_death_probability": v.get("BREAKTHROUGH_DEATH_PROBABILITY", [0.01, 0.1]),
                    "pavilion_refresh_hours": v.get("PAVILION_REFRESH_HOURS", 6),
                    "pavilion_pill_count": v.get("PAVILION_PILL_COUNT", 10),
                    "pavilion_weapon_count": v.get("PAVILION_WEAPON_COUNT", 10),
                    "pavilion_treasure_count": v.get("PAVILION_TREASURE_COUNT", 15),
                    "shop_discount_min": v.get("SHOP_DISCOUNT_MIN", 0.8),
                    "shop_discount_max": v.get("SHOP_DISCOUNT_MAX", 1.2),
                    "shop_stock_divisor": v.get("SHOP_STOCK_DIVISOR", 100)
                }
            
            # 访问控制
            if "ACCESS_CONTROL" in self._astrbot_config:
                ac = self._astrbot_config["ACCESS_CONTROL"]
                settings_data["access_control"] = {
                    "whitelist_groups": ac.get("WHITELIST_GROUPS", []),
                    "shop_managers": ac.get("SHOP_MANAGERS", []),
                    "boss_admins": ac.get("BOSS_ADMINS", []),
                    "admins": ac.get("ADMINS", [])
                }
            
            # 灵根速度
            if "SPIRIT_ROOT_SPEEDS" in self._astrbot_config:
                srs = self._astrbot_config["SPIRIT_ROOT_SPEEDS"]
                settings_data["spirit_root_speeds"] = {
                    "pseudo_root_speed": srs.get("PSEUDO_ROOT_SPEED", 0.5),
                    "quad_root_speed": srs.get("QUAD_ROOT_SPEED", 0.6),
                    "tri_root_speed": srs.get("TRI_ROOT_SPEED", 0.75),
                    "dual_root_speed": srs.get("DUAL_ROOT_SPEED", 0.9),
                    "wuxing_root_speed": srs.get("WUXING_ROOT_SPEED", 1.0),
                    "thunder_root_speed": srs.get("THUNDER_ROOT_SPEED", 1.3),
                    "ice_root_speed": srs.get("ICE_ROOT_SPEED", 1.25),
                    "wind_root_speed": srs.get("WIND_ROOT_SPEED", 1.25),
                    "dark_root_speed": srs.get("DARK_ROOT_SPEED", 1.3),
                    "light_root_speed": srs.get("LIGHT_ROOT_SPEED", 1.3),
                    "heavenly_root_speed": srs.get("HEAVENLY_ROOT_SPEED", 1.5),
                    "yin_yang_root_speed": srs.get("YIN_YANG_ROOT_SPEED", 1.8),
                    "fusion_root_speed": srs.get("FUSION_ROOT_SPEED", 1.8),
                    "chaos_root_speed": srs.get("CHAOS_ROOT_SPEED", 2.0),
                    "innate_body_speed": srs.get("INNATE_BODY_SPEED", 2.5),
                    "divine_body_speed": srs.get("DIVINE_BODY_SPEED", 2.3)
                }
            
            # 灵根权重
            if "SPIRIT_ROOT_WEIGHTS" in self._astrbot_config:
                srw = self._astrbot_config["SPIRIT_ROOT_WEIGHTS"]
                settings_data["spirit_root_weights"] = {
                    "pseudo_root_weight": srw.get("PSEUDO_ROOT_WEIGHT", 1),
                    "quad_root_weight": srw.get("QUAD_ROOT_WEIGHT", 10),
                    "tri_root_weight": srw.get("TRI_ROOT_WEIGHT", 30),
                    "dual_root_weight": srw.get("DUAL_ROOT_WEIGHT", 100),
                    "wuxing_root_weight": srw.get("WUXING_ROOT_WEIGHT", 200),
                    "variant_root_weight": srw.get("VARIANT_ROOT_WEIGHT", 20),
                    "heavenly_root_weight": srw.get("HEAVENLY_ROOT_WEIGHT", 5),
                    "legendary_root_weight": srw.get("LEGENDARY_ROOT_WEIGHT", 2),
                    "mythic_root_weight": srw.get("MYTHIC_ROOT_WEIGHT", 1),
                    "divine_body_weight": srw.get("DIVINE_BODY_WEIGHT", 1)
                }
            
            # 文件配置
            if "FILES" in self._astrbot_config:
                f = self._astrbot_config["FILES"]
                settings_data["files"] = {
                    "database_file": f.get("DATABASE_FILE", "astrbot_plugin_monixiuxianv3.db")
                }
            
            # JSON 存储配置
            if "JSON_STORAGE" in self._astrbot_config:
                js = self._astrbot_config["JSON_STORAGE"]
                settings_data["json_storage"] = {
                    "data_dir": js.get("DATA_DIR", "data/json"),
                    "enable_cache": js.get("ENABLE_CACHE", True),
                    "lock_timeout": js.get("LOCK_TIMEOUT", 30),
                    "max_backups": js.get("MAX_BACKUPS", 3)
                }
            
            result = Settings(**settings_data)
            logger.info(f"【修仙V3】配置加载完成，初始灵石设置为: {result.values.initial_gold}")
            return result
        except Exception as e:
            # 配置加载失败应该记录详细错误
            logger.error(f"【修仙V3】加载配置失败: {e}", exc_info=True)
            logger.warning("【修仙V3】使用默认配置")
            return Settings()
    
    # 允许加载的配置文件白名单
    ALLOWED_CONFIG_FILES = {
        "level_config.json",
        "body_level_config.json",
        "items.json",
        "weapons.json",
        "pills.json",
        "exp_pills.json",
        "utility_pills.json",
        "storage_rings.json",
        "adventure_config.json",
        "bounty_templates.json",
        "alchemy_recipes.json",
        "game_config.json"
    }
    
    def load_json_config(self, filename: str) -> Dict[str, Any]:
        """
        加载 JSON 配置文件
        
        Args:
            filename: 配置文件名（不含路径）
            
        Returns:
            配置字典
            
        Raises:
            ConfigurationException: 如果文件名不在白名单或文件不存在
        """
        # 白名单校验
        if filename not in self.ALLOWED_CONFIG_FILES:
            raise ConfigurationException(f"不允许加载的配置文件: {filename}")
        
        config_file = self.config_dir / filename
        
        if not config_file.exists():
            raise ConfigurationException(f"配置文件不存在: {filename}")
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise ConfigurationException(f"加载配置文件 {filename} 失败: {e}")
    
    def get_level_config(self) -> Dict[str, Any]:
        """获取境界配置"""
        if self._level_config is None:
            self._level_config = self.load_json_config("level_config.json")
        return self._level_config
    
    @property
    def level_data(self) -> list:
        """获取灵修境界数据列表"""
        config = self.get_level_config()
        # 如果配置是字典且包含 levels 键，返回 levels 列表
        if isinstance(config, dict) and "levels" in config:
            return config["levels"]
        # 否则假设配置本身就是列表
        return config if isinstance(config, list) else []
    
    @property
    def body_level_data(self) -> list:
        """获取体修境界数据列表"""
        if self._body_level_config is None:
            self._body_level_config = self.load_json_config("body_level_config.json")
        config = self._body_level_config
        # 如果配置是字典且包含 levels 键，返回 levels 列表
        if isinstance(config, dict) and "levels" in config:
            return config["levels"]
        # 否则假设配置本身就是列表
        return config if isinstance(config, list) else []
    
    def get_level_data(self, cultivation_type: str = "灵修") -> list:
        """
        根据修炼类型获取对应的境界数据
        
        Args:
            cultivation_type: 修炼类型（"灵修" 或 "体修"）
            
        Returns:
            境界数据列表
        """
        if cultivation_type == "体修":
            return self.body_level_data
        return self.level_data
    
    def get_items_config(self) -> Dict[str, Any]:
        """获取物品配置"""
        if self._items_config is None:
            config = self.load_json_config("items.json")
            # 如果配置是 {"items": [...]} 格式，提取 items 部分
            if isinstance(config, dict) and "items" in config:
                config = config["items"]
            
            # 如果是列表，转换为字典（以 id 或 name 为键）
            if isinstance(config, list):
                self._items_config = {item.get('id', item.get('name')): item for item in config}
            else:
                self._items_config = config if config else {}
        return self._items_config
    
    def get_pills_config(self) -> Dict[str, Any]:
        """获取丹药配置"""
        if self._pills_config is None:
            config = self.load_json_config("pills.json")
            # 如果配置是 {"pills": [...]} 格式，提取 pills 部分
            if isinstance(config, dict) and "pills" in config:
                config = config["pills"]
            
            # 如果是列表，转换为字典（以 id 或 name 为键）
            if isinstance(config, list):
                self._pills_config = {item.get('id', item.get('name')): item for item in config}
            else:
                self._pills_config = config if config else {}
        return self._pills_config
    
    def get_weapons_config(self) -> Dict[str, Any]:
        """获取武器配置"""
        if self._weapons_config is None:
            config = self.load_json_config("weapons.json")
            # 如果配置是 {"weapons": [...]} 格式，提取 weapons 部分
            if isinstance(config, dict) and "weapons" in config:
                config = config["weapons"]
            
            # 如果是列表，转换为字典（以 id 或 name 为键）
            if isinstance(config, list):
                self._weapons_config = {item.get('id', item.get('name')): item for item in config}
            else:
                self._weapons_config = config if config else {}
        return self._weapons_config
    
    def get_config(self, config_name: str) -> Dict[str, Any]:
        """
        通用配置获取方法
        
        Args:
            config_name: 配置名称（如 "pills", "weapons", "items" 等）
            
        Returns:
            配置字典
        """
        # 映射到具体的配置获取方法
        config_methods = {
            "pills": self.get_pills_config,
            "weapons": self.get_weapons_config,
            "items": self.get_items_config,
            "level_config": self.get_level_config,
        }
        
        if config_name in config_methods:
            return config_methods[config_name]()
        
        # 如果没有专门的方法，尝试直接加载 JSON 文件
        try:
            return self.load_json_config(f"{config_name}.json")
        except Exception:
            return {}
    
    def reload(self):
        """重新加载所有配置"""
        self._settings = None
        self._level_config = None
        self._body_level_config = None
        self._items_config = None
        self._pills_config = None
        self._weapons_config = None
