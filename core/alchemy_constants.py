"""炼丹系统常量定义"""
from typing import Dict, List, Tuple

# 品质等级映射
RANK_LEVELS: Dict[str, Dict[str, Tuple[int, int]]] = {
    "凡品": {"level_range": (0, 2), "success_rate_range": (85, 95)},
    "灵品": {"level_range": (3, 5), "success_rate_range": (75, 85)},
    "珍品": {"level_range": (3, 5), "success_rate_range": (75, 85)},
    "圣品": {"level_range": (6, 8), "success_rate_range": (65, 75)},
    "帝品": {"level_range": (9, 11), "success_rate_range": (55, 65)},
    "道品": {"level_range": (12, 14), "success_rate_range": (45, 55)},
    "仙品": {"level_range": (15, 17), "success_rate_range": (35, 45)},
    "神品": {"level_range": (18, 20), "success_rate_range": (25, 35)}
}

# 材料分类（按品质）
MATERIALS_BY_RANK: Dict[str, List[Dict[str, any]]] = {
    "凡品": [
        {"name": "灵草", "price": 200},
        {"name": "精铁", "price": 100},
        {"name": "灵石碎片", "price": 50}
    ],
    "珍品": [
        {"name": "玄铁", "price": 800},
        {"name": "灵兽毛皮", "price": 600},
        {"name": "星辰石", "price": 1200},
        {"name": "灵兽内丹", "price": 2000},
        {"name": "紫金沙", "price": 1500},
        {"name": "千年人参", "price": 3000},
        {"name": "魔核碎片", "price": 1200},
        {"name": "幽魂草", "price": 1100},
        {"name": "赤炎石", "price": 1800},
        {"name": "亡者之息", "price": 1300},
        {"name": "精密齿轮", "price": 2200},
        {"name": "星辉晶砂", "price": 4200},
        {"name": "忘川花", "price": 3600}
    ],
    "圣品": [
        {"name": "玄冰之核", "price": 8000},
        {"name": "月光粉尘", "price": 7500},
        {"name": "龙骨髓", "price": 12000}
    ]
}

# 材料主题映射（根据丹药效果选择材料）
MATERIAL_THEMES: Dict[str, List[str]] = {
    "疗伤": ["千年人参", "灵草", "龙骨髓"],
    "修为": ["灵兽内丹", "星辰石", "星辉晶砂"],
    "气血": ["千年人参", "龙骨髓", "灵草"],
    "灵力": ["灵兽内丹", "星辰石", "玄铁"],
    "精神": ["幽魂草", "月光粉尘", "忘川花"],
    "防御": ["玄铁", "龙骨髓", "灵兽毛皮"],
    "攻击": ["赤炎石", "魔核碎片", "紫金沙"],
    "突破": ["灵兽内丹", "千年人参", "龙骨髓", "玄冰之核"],
    "火属性": ["赤炎石", "灵草"],
    "冰属性": ["玄冰之核", "忘川花"],
    "死亡": ["亡者之息", "幽魂草", "忘川花"],
    "机械": ["精密齿轮", "玄铁", "紫金沙"]
}

# 有效的品质等级列表
VALID_RANKS: List[str] = ["凡品", "灵品", "珍品", "圣品", "帝品", "道品", "仙品", "神品"]

# 经济平衡参数
COST_RATIO_MIN: float = 1.1  # 成本最小比率（售价的110%）
COST_RATIO_MAX: float = 1.3  # 成本最大比率（售价的130%）
