"""Recalculate alchemy output prices and shop availability.

The target list price is based on the expected crafting cost at the recipe's
minimum alchemy level.  Expected crafting cost is kept at roughly 70% of the
list price so player alchemists retain room for profit after market tax.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
TARGET_COST_RATIO = 0.70
RARE_SHOP_RANKS = {"帝品", "道品", "仙品", "神品"}
FEE_RATIOS = {
    "凡品": 0.25,
    "灵品": 0.30,
    "珍品": 0.35,
    "圣品": 0.40,
    "帝品": 0.45,
    "道品": 0.50,
    "仙品": 0.55,
    "神品": 0.60,
}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_json(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def round_price(value: float) -> int:
    """Round upward using progressively larger, player-friendly price steps."""
    if value < 100:
        step = 10
    elif value < 1_000:
        step = 50
    elif value < 10_000:
        step = 100
    elif value < 100_000:
        step = 1_000
    elif value < 1_000_000:
        step = 10_000
    elif value < 10_000_000:
        step = 100_000
    elif value < 100_000_000:
        step = 1_000_000
    elif value < 1_000_000_000:
        step = 10_000_000
    else:
        step = 100_000_000
    return int(math.ceil(value / step) * step)


def main() -> None:
    items_path = CONFIG_DIR / "items.json"
    pills_path = CONFIG_DIR / "pills.json"
    recipes_path = CONFIG_DIR / "alchemy_recipes.json"

    items = load_json(items_path)
    pills = load_json(pills_path)
    recipes = load_json(recipes_path)

    item_by_name = {item["name"]: item for item in items.values()}
    item_by_name.update({pill["name"]: pill for pill in pills})
    output_by_id = {str(item_id): item for item_id, item in items.items()}
    output_by_id.update({str(pill["id"]): pill for pill in pills})

    changes: list[tuple[str, int, int, int, int, int]] = []
    for recipe in recipes:
        output = output_by_id[str(recipe["pill_id"])]
        material_value = sum(
            int(item_by_name[name]["price"]) * int(amount)
            for name, amount in recipe["materials"].items()
        )
        rank = output.get("rank", recipe.get("rank"))

        # 费用以材料价值为锚点，避免后期出现费用高于材料数百倍的断层。
        # 回血丹保留额外灵石消耗以约束 Boss 战续航；突破丹也承担少量
        # 战略价值溢价。无论何种类型，费用都不超过材料价值的 75%。
        fee_ratio = FEE_RATIOS[rank]
        if output.get("effect", {}).get("add_hp", 0) > 0:
            fee_ratio += 0.15
        if output.get("subtype") == "breakthrough":
            fee_ratio += 0.10
        fee_ratio = min(fee_ratio, 0.75)
        old_fee = int(recipe["cost"])
        new_fee = round_price(material_value * fee_ratio)
        recipe["cost"] = new_fee

        minimum_success_rate = min(
            100.0,
            float(recipe["success_rate"]) + int(recipe["level_required"] * 0.5),
        ) / 100.0
        expected_cost = (material_value + new_fee) / minimum_success_rate
        new_price = round_price(expected_cost / TARGET_COST_RATIO)
        old_price = int(output["price"])
        output["price"] = new_price

        # 圣品仍是极低概率的商店彩蛋；帝品及以上成丹只由炼丹等玩法产出。
        old_weight = int(output.get("shop_weight", 0))
        if rank == "圣品" and old_weight > 0:
            output["shop_weight"] = min(old_weight, 20)
        elif rank in RARE_SHOP_RANKS:
            output["shop_weight"] = 0

        changes.append(
            (output["name"], old_fee, new_fee, old_price, new_price, output.get("shop_weight", 0))
        )

    save_json(items_path, items)
    save_json(pills_path, pills)
    save_json(recipes_path, recipes)

    print(f"Updated {len(changes)} alchemy outputs")
    for name, old_fee, new_fee, old_price, new_price, shop_weight in changes:
        print(
            f"{name}: fee {old_fee:,} -> {new_fee:,}; "
            f"price {old_price:,} -> {new_price:,}; shop_weight={shop_weight}"
        )


if __name__ == "__main__":
    main()
