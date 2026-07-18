"""历练服务"""
import json
import random
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from ...core.config import ConfigManager
from ...core.exceptions import GameException
from ...domain.models.adventure import AdventureRoute, AdventureEvent, AdventureResult
from ...domain.enums import PlayerState, CultivationType
from ...infrastructure.repositories.player_repo import PlayerRepository
from ...infrastructure.repositories.reincarnation_repo import ReincarnationRepository
from ...infrastructure.repositories.storage_ring_repo import StorageRingRepository


class AdventureService:
    """历练服务"""

    ADVENTURE_FRAGMENT_TABLE = [
        {"name": "长春功残篇", "weight": 12},
        {"name": "御风诀残篇", "weight": 12},
        {"name": "不动明王经残篇", "weight": 8},
        {"name": "北冥神功残篇", "weight": 6},
        {"name": "九阳神功残篇", "weight": 4},
        {"name": "山野吐纳心得碎片", "weight": 12},
        {"name": "云游悟道录碎片", "weight": 10},
        {"name": "猎魔淬心诀碎片", "weight": 8},
        {"name": "生死悟道经碎片", "weight": 6},
    ]

    ATTRIBUTE_LABELS = {
        "hp_flat": "HP白值",
        "attack_flat": "攻击白值",
        "mp_flat": "MP白值",
        "defense_flat": "防御白值",
    }
    
    def __init__(
        self,
        player_repo: PlayerRepository,
        storage_ring_repo: StorageRingRepository,
        config_manager: ConfigManager,
        bounty_repo=None,
        reincarnation_repo: Optional[ReincarnationRepository] = None
    ):
        self.player_repo = player_repo
        self.storage_ring_repo = storage_ring_repo
        self.config_manager = config_manager
        self.bounty_repo = bounty_repo  # 保存悬赏仓储引用
        self.reincarnation_repo = reincarnation_repo
        self.routes: Dict[str, Dict] = {}  # 存储原始路线配置
        self.route_alias_index: Dict[str, str] = {}  # 别名索引
        self.event_groups: Dict[str, List[Dict]] = {}  # 事件组
        self.drop_tables: Dict[str, List[Dict]] = {}  # 掉落表
        self._load_routes()
    
    def _load_routes(self):
        """加载历练路线配置"""
        config_dir = self.config_manager.config_dir
        config_file = config_dir / "adventure_config.json"
        
        if not config_file.exists():
            raise GameException("历练配置文件不存在")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 加载路线
        for route_data in data.get("routes", []):
            key = route_data["key"]
            self.routes[key] = route_data
            
            # 添加别名映射
            aliases = set(route_data.get("aliases", []))
            aliases.add(key)
            aliases.add(route_data["name"])
            
            for alias in aliases:
                self.route_alias_index[alias.lower()] = key
        
        # 加载事件组
        self.event_groups = data.get("event_groups", {})
        
        # 加载掉落表
        self.drop_tables = data.get("drop_tables", {})
    
    def get_route_overview(self) -> List[Dict]:
        """获取路线概览"""
        overview = []
        for route in self.routes.values():
            overview.append({
                "key": route["key"],
                "name": route["name"],
                "risk": route.get("risk", "未知"),
                "duration": route.get("duration", 0),
                "min_level": route.get("min_level", 0),
                "base_success_rate": route.get("success_rate", 80),
                "description": route.get("description", ""),
                "aliases": route.get("aliases", []),
                "attribute_chance": route.get("attribute_reward", {}).get(
                    "chance",
                    0
                ),
                "cultivation_drop_chance": route.get(
                    "cultivation_drop",
                    {}
                ).get(
                    "chance",
                    0
                ),
                "cultivation_drop_names": [
                    item.get("name")
                    for item in route.get("cultivation_drop", {}).get("items", [])
                    if item.get("name")
                ],
                "fragment_drop_chance": route.get(
                    "cultivation_drop",
                    {}
                ).get(
                    "fragment_chance",
                    10
                ),
                "technique_drop_chance": route.get("cultivation_drop", {}).get("complete_chance", 0)
            })
        return overview
    
    def start_adventure(self, user_id: str, route_name: str) -> str:
        """开始历练"""
        # 获取玩家
        player = self.player_repo.get_player(user_id)
        if not player:
            raise GameException("你还未踏入修仙之路")
        
        # 检查状态
        if player.state != PlayerState.IDLE:
            raise GameException("你当前无法开始历练")
        
        # 查找路线（通过别名索引）
        route_key = self.route_alias_index.get(route_name.lower())
        if not route_key:
            raise GameException(f"未找到历练路线：{route_name}")
        
        route = self.routes.get(route_key)
        if not route:
            raise GameException(f"未找到历练路线：{route_name}")
        
        # 检查境界要求
        min_level = route.get("min_level", 0)
        if player.level_index < min_level:
            raise GameException(f"你的境界还不足以踏上这条路线（需要境界 ≥ {min_level}）")

        # 气血/灵气低于 50% 时不能开始历练。
        if player.get_health_percentage() < 0.5:
            raise GameException("当前气血/灵气低于 50%，无法开始历练，请先恢复状态")
        
        success_rate = self._calculate_success_rate(player.level_index, route)

        # 更新玩家状态
        start_time = int(time.time())
        duration = route.get("duration", 3600)
        end_time = start_time + duration
        
        extra_data = {
            "route_key": route_key,
            "route_name": route["name"],
            "start_time": start_time,
            "end_time": end_time,
            "success_rate": success_rate,
        }
        
        self.player_repo.update_player_state(
            user_id,
            state=PlayerState.ADVENTURING,
            extra_data=json.dumps(extra_data)
        )
        
        # 格式化时间
        hours = duration // 3600
        minutes = (duration % 3600) // 60
        time_str = f"{hours}小时{minutes}分钟" if hours > 0 else f"{minutes}分钟"
        
        # 构建提示信息
        lines = [
            f"✨ 你选择了「{route['name']}」——{route.get('description', '未知冒险')}",
            f"路线风险：{route.get('risk', '未知')} | 历练时长：{time_str}",
            f"本次成功率：{success_rate:.1f}%（失败不会扣除修为和灵石，但会降至 1 点生命资源）"
        ]
        
        if min_level > 0:
            lines.append(f"建议境界：{min_level} 阶以上")
        
        fatigue = route.get("fatigue_cooldown", 0)
        if fatigue:
            lines.append(f"（该路线完成后需要休整 {fatigue // 60} 分钟）")
        
        return "\n".join(lines)
    
    def check_adventure_status(self, user_id: str) -> str:
        """检查历练状态"""
        player = self.player_repo.get_player(user_id)
        if not player:
            raise GameException("你还未踏入修仙之路")
        
        if player.state != PlayerState.ADVENTURING:
            raise GameException("你当前没有进行历练")
        
        # 解析状态数据
        state_data = self.player_repo.get_player_state(user_id)
        if not state_data or not state_data.extra_data:
            raise GameException("历练数据异常")
        
        extra_data = json.loads(state_data.extra_data)
        route_name = extra_data.get("route_name", "未知")
        end_time = extra_data.get("end_time", 0)
        
        current_time = int(time.time())
        remaining = end_time - current_time
        
        if remaining <= 0:
            return f"你的【{route_name}】历练已完成\n请使用【完成历练】命令领取奖励"
        
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        time_str = f"{hours}小时{minutes}分钟" if hours > 0 else f"{minutes}分钟"
        
        return f"你正在进行【{route_name}】历练\n剩余时间：{time_str}"
    
    def finish_adventure(self, user_id: str) -> AdventureResult:
        """完成历练"""
        player = self.player_repo.get_player(user_id)
        if not player:
            raise GameException("你还未踏入修仙之路")
        
        if player.state != PlayerState.ADVENTURING:
            raise GameException("你当前没有进行历练")
        
        # 解析状态数据
        state_data = self.player_repo.get_player_state(user_id)
        if not state_data or not state_data.extra_data:
            raise GameException("历练数据异常")
        
        extra_data = json.loads(state_data.extra_data)
        route_key = extra_data.get("route_key")
        end_time = extra_data.get("end_time", 0)
        
        # 检查是否完成
        current_time = int(time.time())
        if current_time < end_time:
            remaining = end_time - current_time
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            time_str = f"{hours}小时{minutes}分钟" if hours > 0 else f"{minutes}分钟"
            raise GameException(f"历练尚未完成，还需要 {time_str}")
        
        # 获取路线
        route = self.routes.get(route_key)
        if not route:
            raise GameException("历练路线数据异常")

        # 历练和秘境一样进行成功率判定；失败不扣修为或灵石，但保留 1 点生命资源。
        success_rate = max(
            0.0,
            min(100.0, float(extra_data.get("success_rate", self._calculate_success_rate(player.level_index, route))))
        )
        if random.random() * 100 >= success_rate:
            if player.cultivation_type == CultivationType.SPIRITUAL:
                player.spiritual_qi = 1
            else:
                player.blood_qi = 1
            self.player_repo.save(player)
            self.player_repo.update_player_state(user_id, state=PlayerState.IDLE, extra_data=None)
            return AdventureResult(
                success=False,
                gold_gained=0,
                exp_gained=0,
                items_gained=[],
                event_type="adventure_failure",
                event_description=(
                    f"💀 你在『{route.get('name', '历练')}』中遭遇失败！"
                    f"（成功率：{success_rate:.0f}%）\n"
                    "本次未扣除修为和灵石，但气血/灵气已降至 1 点。"
                ),
                fatigue_cost=0,
            )
        
        # 计算奖励
        result = self._calculate_rewards(player, route)
        
        # 发放奖励
        # 获取玩家并更新
        player = self.player_repo.get_by_id(user_id)
        if not player:
            raise BusinessException("玩家不存在")
        
        # 更新金币和修为
        result.exp_gained = self.player_repo.calculate_experience_reward(
            user_id,
            result.exp_gained
        )
        player.add_gold(result.gold_gained)
        player.add_experience(result.exp_gained)

        # 历练白值进入本世传承池，轮回时再合并到永久池。
        if result.attribute_gained and self.reincarnation_repo:
            self.reincarnation_repo.add_to_life_pool(
                user_id,
                result.attribute_gained["key"],
                result.attribute_gained["value"]
            )
        
        # 发放物品
        synthesis_messages = []
        for item in result.items_gained:
            item_name = item["name"]
            item_count = item["count"]
            
            # 所有物品（包括丹药）都存入储物戒
            if item_name in player.storage_ring_items:
                player.storage_ring_items[item_name] += item_count
            else:
                player.storage_ring_items[item_name] = item_count
            
            # 检查是否触发功法残篇合成
            for technique_name, config in self.storage_ring_repo.TECHNIQUE_SYNTHESIS.items():
                fragment_name = config["fragment"]
                required_count = config["required"]
                
                if item_name == fragment_name:
                    current_count = player.storage_ring_items.get(fragment_name, 0)
                    
                    if current_count >= required_count:
                        # 消耗残篇
                        player.storage_ring_items[fragment_name] = current_count - required_count
                        if player.storage_ring_items[fragment_name] == 0:
                            del player.storage_ring_items[fragment_name]
                        
                        # 添加完整功法
                        player.storage_ring_items[technique_name] = player.storage_ring_items.get(technique_name, 0) + 1
                        
                        # 获取功法品质
                        tier = config.get("tier", "未知")
                        synthesis_messages.append(f"✨ 恭喜！你集齐了残篇，自动合成了【{tier}】功法《{technique_name}》！")
                        break
        
        # 保存玩家（包含所有更新）
        self.player_repo.save(player)
        
        # 如果有合成信息，添加到结果描述中
        if synthesis_messages:
            result.event_description += "\n\n" + "\n".join(synthesis_messages)
        
        # 重置状态
        self.player_repo.update_player_state(user_id, state=PlayerState.IDLE, extra_data=None)
        
        # 更新悬赏进度
        if self.bounty_repo:
            try:
                result.bounty_progress_gained = self._update_bounty_progress(
                    user_id,
                    route,
                    result
                )
            except Exception as e:
                # 悬赏更新失败不影响历练完成
                pass
        
        return result
    
    def cancel_adventure(self, user_id: str) -> str:
        """
        放弃历练（无奖励）
        
        Args:
            user_id: 用户ID
            
        Returns:
            结果消息
            
        Raises:
            GameException: 各种异常
        """
        player = self.player_repo.get_player(user_id)
        if not player:
            raise GameException("你还未踏入修仙之路")
        
        if player.state != PlayerState.ADVENTURING:
            raise GameException("你当前没有进行历练")
        
        # 解析状态数据
        state_data = self.player_repo.get_player_state(user_id)
        if not state_data or not state_data.extra_data:
            raise GameException("历练数据异常")
        
        extra_data = json.loads(state_data.extra_data)
        route_name = extra_data.get("route_name", "未知")
        
        # 重置状态（无奖励）
        self.player_repo.update_player_state(user_id, state=PlayerState.IDLE, extra_data=None)
        
        return f"🚫 你放弃了【{route_name}】历练\n所有进度和奖励已清空"
    
    def _calculate_success_rate(self, player_level: int, route: Dict) -> float:
        """按路线基础值、境界差和随机波动计算本次历练成功率。"""
        base_rate = float(route.get("success_rate", 80.0))
        min_level = int(route.get("min_level", 0))
        level_diff = player_level - min_level
        # 高于推荐境界略微提高，低于推荐境界明显降低；再叠加每次独立的随机波动。
        if level_diff >= 2:
            return 100.0
        level_adjust = level_diff * 5.0
        random_adjust = random.uniform(-3.0, 3.0)
        return max(20.0, min(95.0, base_rate + level_adjust + random_adjust))

    def _trigger_route_event(self, route: Dict) -> Dict:
        """触发路线事件"""
        event_weights = route.get("event_weights", {})
        if not event_weights:
            # 默认标准事件
            group_key = "standard"
        else:
            # 按权重随机选择事件组
            total_weight = sum(max(0, w) for w in event_weights.values())
            if total_weight == 0:
                group_key = "standard"
            else:
                rand = random.randint(1, total_weight)
                cumulative = 0
                group_key = "standard"
                
                for key, weight in event_weights.items():
                    cumulative += max(0, weight)
                    if rand <= cumulative:
                        group_key = key
                        break
        
        # 从事件组中随机选择一个事件
        group = self.event_groups.get(group_key, [])
        if not group:
            # 默认事件
            return {
                "key": "default",
                "name": "平稳推进",
                "desc": "历练过程顺风顺水，按部就班地完成既定目标。",
                "exp_mult": 1.0,
                "gold_mult": 1.0,
                "item_chance": 0.35,
                "bonus_progress": 0
            }
        
        return random.choice(group)
    
    def _calculate_rewards(self, player, route: Dict) -> AdventureResult:
        """计算历练奖励"""
        # 基础奖励（按分钟计算）
        duration_minutes = route.get("duration", 3600) // 60
        base_exp_per_min = route.get("base_exp_per_min", 45)
        base_gold_per_min = route.get("base_gold_per_min", 10)
        
        base_exp = duration_minutes * base_exp_per_min
        base_gold = duration_minutes * base_gold_per_min
        
        # 境界加成
        level_bonus_exp = player.level_index * route.get("level_bonus_exp", 12)
        level_bonus_gold = player.level_index * route.get("level_bonus_gold", 3)
        
        # 完成奖励
        completion_bonus = route.get("completion_bonus", {})
        completion_exp = completion_bonus.get("exp", 0)
        completion_gold = completion_bonus.get("gold", 0)
        
        # 总基础奖励
        total_exp = base_exp + level_bonus_exp + completion_exp
        total_gold = base_gold + level_bonus_gold + completion_gold
        
        # 触发随机事件
        event = self._trigger_route_event(route)
        event_type = event.get("key")
        event_description = event.get("desc")
        exp_multiplier = event.get("exp_mult", 1.0)
        gold_multiplier = event.get("gold_mult", 1.0)
        item_chance = event.get("item_chance", 0.35) / 100.0  # 转换为小数
        
        # 应用事件倍率
        final_exp = max(0, int(total_exp * exp_multiplier))
        final_gold = max(0, int(total_gold * gold_multiplier))
        
        # 随机掉落物品
        items_gained = []
        if random.random() <= item_chance:
            drop_tier = route.get("drop_tier", "low")
            drop_table = self.drop_tables.get(drop_tier, [])
            
            if drop_table:
                # 按权重选择掉落物品
                total_weight = sum(drop.get("weight", 1) for drop in drop_table)
                rand_weight = random.uniform(0, total_weight)
                cumulative_weight = 0.0
                
                for drop_data in drop_table:
                    cumulative_weight += drop_data.get("weight", 1)
                    if rand_weight <= cumulative_weight:
                        min_count = drop_data.get("min", 1)
                        max_count = drop_data.get("max", 1)
                        count = random.randint(min_count, max_count)
                        # 检查是否为类别物品（需要二级掉落）
                        item_name = self._resolve_item_category(drop_data["name"], drop_tier)
                        items_gained.append({
                            "name": item_name,
                            "count": count
                        })
                        break

        for cultivation_item in self._roll_cultivation_drop(route):
            items_gained.append({"name": cultivation_item, "count": 1})

        attribute_gained = self._roll_attribute_reward(route)
        
        return AdventureResult(
            success=True,
            gold_gained=final_gold,
            exp_gained=final_exp,
            items_gained=items_gained,
            event_type=event_type,
            event_description=event_description,
            fatigue_cost=0,
            attribute_gained=attribute_gained,
            event_bonus_progress=max(0, int(event.get("bonus_progress", 0)))
        )

    def _roll_attribute_reward(self, route: Dict) -> Optional[Dict[str, object]]:
        """按路线配置随机生成一项本世白值奖励。"""
        reward_config = route.get("attribute_reward", {})
        if not reward_config:
            return None

        ranges = reward_config.get("ranges", {})
        available = [
            key for key, value_range in ranges.items()
            if key in self.ATTRIBUTE_LABELS
            and isinstance(value_range, list)
            and len(value_range) == 2
            and float(value_range[1]) > 0
        ]
        if not available:
            return None

        key = random.choice(available)
        minimum, maximum = map(float, ranges[key])
        value = round(random.uniform(minimum, maximum), 2)
        if value <= 0:
            return None
        return {
            "key": key,
            "label": self.ATTRIBUTE_LABELS[key],
            "value": value,
        }

    def _roll_cultivation_drop(self, route: Dict) -> List[str]:
        """分别判定完整功法、修炼心得，以及共享碎片池。"""
        rewards: List[str] = []
        drop_config = route.get("cultivation_drop", {})

        # 完整功法保留低概率直落，优先于碎片判定。
        complete_items = [
            item for item in drop_config.get("complete_items", [])
            if item.get("name")
            and "心得" not in str(item.get("name"))
            and "残篇" not in str(item.get("name"))
            and float(item.get("weight", 0)) > 0
        ]
        complete_chance = float(drop_config.get("complete_chance", 0))
        if complete_items and random.random() * 100 < complete_chance:
            total_weight = sum(float(item["weight"]) for item in complete_items)
            roll = random.uniform(0, total_weight)
            cumulative = 0.0
            for item in complete_items:
                cumulative += float(item["weight"])
                if roll <= cumulative:
                    rewards.append(str(item["name"]))
                    break

        # 该路线对应的修炼心得，掉落率随历练强度降低。
        items = [
            item for item in drop_config.get("items", [])
            if item.get("name") and float(item.get("weight", 0)) > 0
        ]
        if items and random.random() * 100 <= float(drop_config.get("chance", 0)):
            total_weight = sum(float(item["weight"]) for item in items)
            roll = random.uniform(0, total_weight)
            cumulative = 0.0
            for item in items:
                cumulative += float(item["weight"])
                if roll <= cumulative:
                    rewards.append(str(item["name"]))
                    break

        # 功法残篇与心得碎片共享一次 10% 判定，成功后只掉其中一种。
        if random.random() * 100 <= float(drop_config.get("fragment_chance", 10.0)):
            total_weight = sum(float(item["weight"]) for item in self.ADVENTURE_FRAGMENT_TABLE)
            roll = random.uniform(0, total_weight)
            cumulative = 0.0
            for item in self.ADVENTURE_FRAGMENT_TABLE:
                cumulative += float(item["weight"])
                if roll <= cumulative:
                    rewards.append(item["name"])
                    break

        return rewards
    
    def _update_bounty_progress(
        self,
        user_id: str,
        route: Dict,
        result: AdventureResult
    ) -> int:
        """更新悬赏进度"""
        # 获取路线的悬赏标签
        bounty_tag = route.get("bounty_tag")
        if not bounty_tag:
            return 0
        
        # 获取进行中的悬赏任务
        active_bounty = self.bounty_repo.get_active_bounty(user_id)
        if not active_bounty:
            return 0
        
        # 检查任务是否已过期
        if int(time.time()) > active_bounty.expire_time:
            return 0
        
        # 检查标签是否匹配（从配置加载悬赏模板）
        try:
            import json
            from pathlib import Path
            config_file = self.config_manager.config_dir / "bounty_templates.json"
            if not config_file.exists():
                return 0
            
            with open(config_file, 'r', encoding='utf-8') as f:
                bounty_config = json.load(f)
            
            templates = bounty_config.get("templates", [])
            template = next((t for t in templates if t["id"] == active_bounty.bounty_id), None)
            
            if not template:
                return 0
            
            progress_tags = template.get("progress_tags", [])
            if bounty_tag not in progress_tags:
                return 0
            
            # 计算进度增加量
            base_progress = route.get("bounty_progress", 1)
            progress_to_add = base_progress + result.event_bonus_progress
            
            # 更新进度
            new_progress = min(
                active_bounty.current_progress + progress_to_add,
                active_bounty.target_count
            )
            
            self.bounty_repo.update_progress(user_id, new_progress)
            return max(0, new_progress - active_bounty.current_progress)
            
        except Exception:
            # 静默失败
            return 0
    
    def _resolve_item_category(self, item_name: str, drop_tier: str) -> str:
        """
        解析物品类别，如果是类别物品则进行二级掉落
        
        Args:
            item_name: 物品名称（可能是类别）
            drop_tier: 掉落等级（low/mid/high）
            
        Returns:
            具体的物品名称
        """
        # 检查是否为"珍品"类别（包含所有珍品级物品）
        if item_name == "珍品":
            return self._roll_treasure_item()
        
        # 其他物品直接返回
        return item_name
    
    def _is_pill_item(self, item_name: str) -> bool:
        """检查物品是否为丹药"""
        # 简单判断：包含"丹"字的为丹药
        return "丹" in item_name
    
    def _roll_treasure_item(self) -> str:
        """
        从珍品类别中随机选择一种物品
        
        珍品包含：
        - 功法残篇（凡品和珍品功法）
        - 珍品级天材地宝
        - 珍品级炼器材料
        - 珍品级法器
        
        Returns:
            珍品物品名称
        """
        # 珍品掉落表：包含所有珍品级物品
        treasure_items = [
            # 功法残篇（权重较高）
            {"name": "长春功残篇", "weight": 20},
            {"name": "御风诀残篇", "weight": 20},
            {"name": "不动明王经残篇", "weight": 10},
            {"name": "北冥神功残篇", "weight": 8},
            {"name": "九阳神功残篇", "weight": 5},
            
            # 珍品级天材地宝
            {"name": "千年灵芝", "weight": 12},
            {"name": "九转仙草", "weight": 10},
            {"name": "龙血果", "weight": 8},
            {"name": "凤凰羽", "weight": 6},
            {"name": "玄冰莲", "weight": 5},
            
            # 珍品级炼器材料
            {"name": "紫金沙", "weight": 10},
            {"name": "星辉晶砂", "weight": 8},
            {"name": "赤炎石", "weight": 8},
            {"name": "月光粉尘", "weight": 6},
            
            # 珍品级法器
            {"name": "烈阳刀", "weight": 5},
            {"name": "月华袍", "weight": 5},
            {"name": "镇魂幡", "weight": 4}
        ]
        
        # 加权随机选择
        total_weight = sum(item["weight"] for item in treasure_items)
        roll = random.randint(1, total_weight)
        
        current_weight = 0
        for item in treasure_items:
            current_weight += item["weight"]
            if roll <= current_weight:
                return item["name"]
        
        # 兜底：返回第一个
        return treasure_items[0]["name"]
