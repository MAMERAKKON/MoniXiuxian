"""
炼丹服务层

处理炼丹相关的业务逻辑。
"""
import json
import math
import random
from typing import Optional, Tuple, Dict
from pathlib import Path

from ...domain.models.player import Player
from ...infrastructure.repositories.player_repo import PlayerRepository
from ...infrastructure.repositories.storage_ring_repo import StorageRingRepository
from ...core.config import ConfigManager
from ...core.exceptions import BusinessException
from .recipe_manager import RecipeManager
from ...domain.models.recipe import Recipe


class AlchemyService:
    """炼丹服务"""
    
    def __init__(
        self,
        player_repo: PlayerRepository,
        storage_ring_repo: StorageRingRepository,
        config_manager: ConfigManager,
    ):
        """
        初始化炼丹服务
        
        Args:
            player_repo: 玩家仓储
            storage_ring_repo: 储物戒仓储
            config_manager: 配置管理器
        """
        self.player_repo = player_repo
        self.storage_ring_repo = storage_ring_repo
        self.config_manager = config_manager
        
        # 初始化配方管理器
        try:
            self.recipe_manager = RecipeManager()
            self.recipe_manager.load_recipes()
        except Exception as e:
            print(f"警告：无法加载配方管理器: {e}")
            self.recipe_manager = None

        self._pill_prices = None

    def _get_pill_reference_price(self, pill_name: str) -> int:
        """从物品配置读取成品参考价，配置缺失时返回0。"""
        if self._pill_prices is None:
            self._pill_prices = {}
            items_path = Path(__file__).parent.parent.parent / "config" / "items.json"
            try:
                with open(items_path, "r", encoding="utf-8") as f:
                    items = json.load(f)
                for item in items.values():
                    name = item.get("name")
                    if name:
                        self._pill_prices[name] = int(item.get("price", 0) or 0)
            except (OSError, ValueError, TypeError):
                self._pill_prices = {}
        return int(self._pill_prices.get(pill_name, 0) or 0)

    @staticmethod
    def _target_cost_ratio(recipe: Recipe) -> float:
        """炼丹总成本目标占成品估价比例。"""
        name = str(recipe.name or "")
        if any(token in name for token in ("破境", "渡劫", "增益")):
            return 0.95
        if int(recipe.level_required or 0) >= 40:
            return 0.90
        if int(recipe.level_required or 0) >= 20:
            return 0.90
        return 0.85

    def _calculate_dynamic_craft_cost(self, recipe: Recipe, success_rate: float) -> int:
        """按成品估价和成功率计算动态炼制费，避免免费种子制造通胀。"""
        reference_price = self._get_pill_reference_price(recipe.name)
        if reference_price <= 0:
            return int(recipe.cost)
        expected_cost = math.ceil(
            reference_price
            * self._target_cost_ratio(recipe)
            * max(0.0, min(100.0, float(success_rate)))
            / 100.0
        )
        return max(int(recipe.cost), expected_cost)
    
    def get_recipe_by_pill_id(self, pill_id: str) -> Optional[Recipe]:
        """
        通过丹药ID获取配方
        
        Args:
            pill_id: 丹药ID
            
        Returns:
            配方对象，不存在则返回None
        """
        if not self.recipe_manager:
            return None
        return self.recipe_manager.get_recipe_by_pill_id(pill_id)
    
    def get_recipe_by_name(self, pill_name: str) -> Optional[Recipe]:
        """
        通过丹药名称获取配方
        
        Args:
            pill_name: 丹药名称
            
        Returns:
            配方对象，不存在则返回None
        """
        if not self.recipe_manager:
            return None
        return self.recipe_manager.get_recipe_by_name(pill_name)
    
    def craft_pill_by_name(self, user_id: str, pill_name: str, quantity: int = 1) -> Tuple[bool, str, Dict]:
        """
        通过丹药名称炼制丹药（支持批量）
        
        Args:
            user_id: 用户ID
            pill_name: 丹药名称
            quantity: 炼制数量
            
        Returns:
            (是否成功, 消息, 结果数据)
            
        Raises:
            BusinessException: 各种业务异常
        """
        # 获取玩家
        player = self.player_repo.get_by_id(user_id)
        if not player:
            raise BusinessException("玩家不存在")
        
        # 检查玩家状态
        if not player.can_cultivate():
            raise BusinessException(f"当前状态「{player.state.value}」无法炼丹")
        
        # 获取配方
        if not self.recipe_manager:
            raise BusinessException("配方系统未初始化")
        
        recipe = self.recipe_manager.get_recipe_by_name(pill_name)
        if not recipe:
            raise BusinessException(f"未找到【{pill_name}】的配方")
        
        # 检查炼丹等级要求
        if player.alchemy_level < recipe.level_required:
            raise BusinessException(
                f"炼制【{recipe.name}】需要炼丹等级 Lv.{recipe.level_required}（当前：Lv.{player.alchemy_level} {player.get_alchemy_title()}）"
            )
        
        # 检查材料与灵石（计算最多可炼制数量）
        material_limit = quantity
        for material_name, required_count in recipe.materials.items():
            current_count = self.storage_ring_repo.get_item_count(user_id, material_name)
            can_craft = current_count // required_count
            material_limit = min(material_limit, can_craft)
        
        if material_limit == 0:
            # 材料不足，显示缺少的材料
            missing_materials = []
            for material_name, required_count in recipe.materials.items():
                current_count = self.storage_ring_repo.get_item_count(user_id, material_name)
                if current_count < required_count:
                    missing_materials.append(
                        f"{material_name}（需要{required_count}，拥有{current_count}）"
                    )
            raise BusinessException(
                f"材料不足：\n" + "\n".join(missing_materials)
            )

        initial_success_rate = min(
            float(recipe.success_rate) + float(player.get_alchemy_success_bonus()),
            100.0,
        )
        dynamic_cost = self._calculate_dynamic_craft_cost(recipe, initial_success_rate)
        gold_limit = quantity
        if dynamic_cost > 0:
            gold_limit = player.gold // dynamic_cost
        if gold_limit == 0:
            raise BusinessException(
                f"灵石不足：炼制【{recipe.name}】每次需要{dynamic_cost:,}灵石，"
                f"当前拥有{player.gold:,}灵石"
            )
        
        # 实际炼制数量同时受材料和灵石限制
        actual_quantity = min(quantity, material_limit, gold_limit)
        total_gold_cost = dynamic_cost * actual_quantity
        if total_gold_cost > 0 and not player.consume_gold(total_gold_cost):
            raise BusinessException("扣除炼制费用失败，请稍后重试")
        
        # 批量炼制
        success_count = 0
        fail_count = 0
        total_exp = 0
        level_ups = []
        
        base_success_rate = recipe.success_rate
        
        for i in range(actual_quantity):
            # 计算成功率（每次都重新计算，因为等级可能提升）
            alchemy_bonus = player.get_alchemy_success_bonus()
            final_success_rate = min(base_success_rate + alchemy_bonus, 100)
            
            # 判断是否成功
            is_success = random.random() * 100 < final_success_rate
            
            # 消耗材料
            for material_name, required_count in recipe.materials.items():
                self.storage_ring_repo.remove_item(user_id, material_name, required_count)
            
            # 计算炼丹经验
            base_exp = self._calculate_alchemy_exp(recipe.rank)
            gained_exp = base_exp if is_success else base_exp // 3
            total_exp += gained_exp
            
            # 增加炼丹经验
            level_up = player.add_alchemy_exp(gained_exp)
            if level_up:
                level_ups.append(player.alchemy_level)
            
            if is_success:
                # 炼丹成功，添加丹药到储物戒
                self.storage_ring_repo.add_item(user_id, recipe.name, 1)
                success_count += 1
            else:
                fail_count += 1
        
        # 保存玩家数据
        self.player_repo.save(player)
        
        # 构建结果消息
        qty_display = f" x{actual_quantity}" if actual_quantity > 1 else ""
        result_data = {
            "pill_name": recipe.name,
            "quantity": actual_quantity,
            "success_count": success_count,
            "fail_count": fail_count,
            "alchemy_exp": total_exp,
            "level_ups": level_ups,
            "gold_cost": total_gold_cost
        }
        
        if actual_quantity == 1:
            # 单次炼制，使用原有格式
            alchemy_bonus = player.get_alchemy_success_bonus()
            final_success_rate = min(base_success_rate + alchemy_bonus, 100)
            
            level_up_msg = ""
            if level_ups:
                level_up_msg = f"\n\n🎊 炼丹等级提升！\n当前等级：Lv.{player.alchemy_level} {player.get_alchemy_title()}"
            
            if success_count > 0:
                message = f"""🎉 炼丹成功！

获得：【{recipe.name}】× 1
成功率：{final_success_rate}%
炼制费用：-{total_gold_cost:,}灵石
炼丹经验：+{total_exp}{level_up_msg}"""
            else:
                message = f"""💔 炼丹失败

丹药：【{recipe.name}】
成功率：{final_success_rate}%
炼制费用：-{total_gold_cost:,}灵石
炼丹经验：+{total_exp}（失败获得1/3经验）{level_up_msg}

💡 提升炼丹等级可以增加成功率！"""
        else:
            # 批量炼制
            level_up_msg = ""
            if level_ups:
                level_up_msg = f"\n🎊 炼丹等级提升：Lv.{level_ups[0]}"
                if len(level_ups) > 1:
                    level_up_msg += f" → Lv.{level_ups[-1]}"
                level_up_msg += f"\n当前：Lv.{player.alchemy_level} {player.get_alchemy_title()}"
            
            limitation_warning = ""
            if actual_quantity < quantity:
                reasons = []
                if material_limit < quantity:
                    reasons.append("材料")
                if gold_limit < quantity:
                    reasons.append("灵石")
                reason_text = "和".join(reasons) if reasons else "资源"
                limitation_warning = (
                    f"\n⚠️ {reason_text}不足，仅炼制了{actual_quantity}次"
                    f"（请求：{quantity}次）"
                )
            
            message = f"""🔥 批量炼丹完成！

━━━━━━━━━━━━━━━
丹药：【{recipe.name}】
炼制次数：{actual_quantity}
━━━━━━━━━━━━━━━
✅ 成功：{success_count}次
❌ 失败：{fail_count}次
💰 炼制费用：-{total_gold_cost:,}灵石
📈 炼丹经验：+{total_exp}{level_up_msg}{limitation_warning}

💡 成功率：{base_success_rate}% + 等级加成"""
        
        return success_count > 0, message, result_data
    
    def format_new_recipes(self, user_id: str) -> str:
        """
        格式化配方列表显示
        
        Args:
            user_id: 用户ID
            
        Returns:
            格式化后的字符串
            
        Raises:
            BusinessException: 玩家不存在或配方系统未初始化
        """
        # 获取玩家
        player = self.player_repo.get_by_id(user_id)
        if not player:
            raise BusinessException("玩家不存在")
        
        if not self.recipe_manager:
            raise BusinessException("配方系统未初始化")
        
        # 获取所有配方
        all_recipes = self.recipe_manager.get_all_recipes()
        
        # 筛选玩家可用的配方
        available_recipes = [
            recipe for recipe in all_recipes
            if player.alchemy_level >= recipe.level_required
        ]
        
        if not available_recipes:
            return f"❌ 你当前炼丹等级（Lv.{player.alchemy_level}）无法炼制任何丹药！\n💡 通过炼丹获得经验提升炼丹等级"
        
        # 按品质和等级排序
        rank_order = {"凡品": 0, "灵品": 1, "珍品": 2, "圣品": 3, "帝品": 4, "道品": 5, "仙品": 6, "神品": 7}
        available_recipes.sort(key=lambda r: (rank_order.get(r.rank, 99), r.level_required))
        
        # 获取炼丹职业信息
        alchemy_title = player.get_alchemy_title()
        alchemy_level = player.alchemy_level
        success_bonus = player.get_alchemy_success_bonus()
        
        lines = [
            "🔥 丹药配方",
            "━━━━━━━━━━━━━━━",
            f"炼丹职业：Lv.{alchemy_level} {alchemy_title}",
            f"成功率加成：+{success_bonus}%",
            ""
        ]
        
        for recipe in available_recipes:
            materials_str = "、".join([f"{k}×{v}" for k, v in recipe.materials.items()])
            
            lines.append(f"【{recipe.name}】({recipe.rank})")
            lines.append(f"  炼丹等级：Lv.{recipe.level_required}")
            lines.append(f"  材料：{materials_str}")
            lines.append(f"  成功率：{recipe.success_rate}%")
            preview_cost = self._calculate_dynamic_craft_cost(recipe, recipe.success_rate)
            lines.append(f"  炼制费用：约{preview_cost:,}灵石/次（随成功率动态变化）")
            
            # 获取丹药效果描述
            desc = self._get_pill_description(recipe.name)
            if desc:
                lines.append(f"  效果：{desc}")
            
            lines.append("")
        
        lines.append(f"共 {len(available_recipes)} 个可用配方")
        lines.append("💡 使用 炼丹 <丹药名称> 开始炼制")
        lines.append("💡 使用 查询配方 <丹药名称> 查看详情")
        lines.append("💡 圣品成丹仅在丹阁极低概率刷新，帝品及以上成丹不再刷新")
        lines.append("💡 提升炼丹等级可降低失败成本，并可将成丹放入坊市出售")
        
        return "\n".join(lines)

    def _get_pill_description(self, pill_name: str) -> str:
        """
        获取丹药效果描述
        
        Args:
            pill_name: 丹药名称
            
        Returns:
            丹药效果描述
        """
        # 从配置中获取丹药信息
        pills_config = self.config_manager.get_config("pills")
        items_config = self.config_manager.get_config("items")
        
        pill_data = None
        
        # 先从 pills.json 查找（突破丹药）
        if pills_config:
            # pills_config 可能是字典或列表
            if isinstance(pills_config, dict):
                # 如果是字典，直接通过名称查找
                pill_data = pills_config.get(pill_name)
            elif isinstance(pills_config, list):
                # 如果是列表，遍历查找
                for pill in pills_config:
                    if pill.get("name") == pill_name:
                        pill_data = pill
                        break
        
        # 如果没找到，从 items.json 查找（通用丹药）
        if not pill_data and items_config:
            # items_config 可能是字典或列表
            if isinstance(items_config, dict):
                # 如果是字典，遍历所有值查找
                for item in items_config.values():
                    if isinstance(item, dict) and item.get("name") == pill_name and item.get("type") == "丹药":
                        pill_data = item
                        break
            elif isinstance(items_config, list):
                # 如果是列表，遍历查找
                for item in items_config:
                    if item.get("name") == pill_name and item.get("type") == "丹药":
                        pill_data = item
                        break
        
        if not pill_data:
            return ""
        
        # 直接返回description字段
        return pill_data.get("description", "")

    def _calculate_alchemy_exp(self, pill_rank: str) -> int:
        """
        根据丹药品质计算炼丹经验
        
        Args:
            pill_rank: 丹药品质
            
        Returns:
            经验值
        """
        exp_map = {
            "凡品": 10,
            "灵品": 20,
            "珍品": 30,
            "圣品": 80,
            "帝品": 140,
            "道品": 240,
            "仙品": 400,
            "神品": 650
        }
        return exp_map.get(pill_rank, 10)
    
    def get_alchemy_info(self, user_id: str) -> str:
        """
        获取玩家炼丹职业信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            格式化的炼丹信息
            
        Raises:
            BusinessException: 玩家不存在
        """
        player = self.player_repo.get_by_id(user_id)
        if not player:
            raise BusinessException("玩家不存在")
        
        title = player.get_alchemy_title()
        level = player.alchemy_level
        exp = player.alchemy_exp
        required_exp = player.get_required_alchemy_exp()
        success_bonus = player.get_alchemy_success_bonus()
        
        # 计算下一级称号
        next_title = ""
        if level < 10:
            next_title = "初级炼丹师"
        elif level < 20:
            next_title = "中级炼丹师"
        elif level < 30:
            next_title = "高级炼丹师"
        elif level < 40:
            next_title = "炼丹大师"
        elif level < 50:
            next_title = "炼丹宗师"
        elif level < 60:
            next_title = "炼丹圣手"
        elif level < 70:
            next_title = "丹道真人"
        elif level < 80:
            next_title = "丹圣"
        elif level < 90:
            next_title = "丹帝"
        elif level < 100:
            next_title = "丹神"
        
        lines = [
            "🔥 炼丹职业信息",
            "━━━━━━━━━━━━━━━",
            f"当前称号：{title}",
            f"炼丹等级：Lv.{level}",
            f"炼丹经验：{exp}/{required_exp}",
            f"成功率加成：+{success_bonus}%",
            ""
        ]
        
        if next_title:
            next_level = (level // 10 + 1) * 10
            lines.append(f"下一称号：{next_title}（Lv.{next_level}）")
        else:
            lines.append("🎉 已达到最高称号！")
        
        lines.append("")
        lines.append("💡 通过炼丹获得经验提升等级")
        lines.append("💡 每级增加0.5%成功率加成")
        lines.append("💡 圣品成丹极少刷新，帝品及以上主要由炼丹获得")
        lines.append("💡 炼丹等级越高，成功率和成丹收益越高")
        
        return "\n".join(lines)
