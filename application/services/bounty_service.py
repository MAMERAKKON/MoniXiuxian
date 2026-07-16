"""
悬赏服务层

处理悬赏任务相关的业务逻辑。
"""
import json
import random
import time
from typing import List, Dict, Optional, Tuple

from ...domain.models.bounty import Bounty, BountyTask
from ...infrastructure.repositories.bounty_repo import BountyRepository
from ...infrastructure.repositories.player_repo import PlayerRepository
from ...infrastructure.repositories.storage_ring_repo import StorageRingRepository
from ...core.config import ConfigManager
from ...core.exceptions import BusinessException


class BountyService:
    """悬赏服务"""
    
    BOUNTY_CACHE_DURATION = 600  # 任务列表缓存10分钟
    
    def __init__(
        self,
        bounty_repo: BountyRepository,
        player_repo: PlayerRepository,
        storage_ring_repo: StorageRingRepository,
        config_manager: ConfigManager,
    ):
        """
        初始化悬赏服务
        
        Args:
            bounty_repo: 悬赏仓储
            player_repo: 玩家仓储
            storage_ring_repo: 储物戒仓储
            config_manager: 配置管理器
        """
        self.bounty_repo = bounty_repo
        self.player_repo = player_repo
        self.storage_ring_repo = storage_ring_repo
        self.config_manager = config_manager
        self._bounty_cache: Dict[str, Dict] = {}
        
        # 加载配置
        self._load_config()
    
    def _load_config(self):
        """加载悬赏配置"""
        try:
            config = self.config_manager.load_json_config("bounty_templates.json")
            self.difficulties = config.get("difficulties", {})
            self.templates = config.get("templates", [])
            self.item_tables = config.get("item_tables", {})
            
            # 构建索引
            self.templates_by_id = {t["id"]: t for t in self.templates}
            self.templates_by_diff = {}
            for t in self.templates:
                diff = t.get("difficulty", "easy")
                if diff not in self.templates_by_diff:
                    self.templates_by_diff[diff] = []
                self.templates_by_diff[diff].append(t)
        except Exception as e:
            # 使用默认配置
            self.difficulties = {
                "easy": {"name": "F级", "stone_scale": 1.0, "exp_scale": 1.0, "min_level": 0}
            }
            self.templates = [
                {
                    "id": 1,
                    "name": "击退妖兽",
                    "difficulty": "easy",
                    "category": "巡山",
                    "progress_tags": ["adventure_scout"],
                    "min_target": 3,
                    "max_target": 5,
                    "time_limit": 3600,
                    "reward": {"stone": 300, "exp": 2500},
                    "item_table": "hunt",
                    "description": "驱逐骚扰山门的妖兽。"
                }
            ]
            self.item_tables = {
                "hunt": [
                    {"name": "灵兽毛皮", "weight": 40, "min": 1, "max": 3},
                    {"name": "妖兽精血", "weight": 30, "min": 1, "max": 2}
                ]
            }
            self.templates_by_id = {1: self.templates[0]}
            self.templates_by_diff = {"easy": self.templates}
    
    def get_bounty_list(self, user_id: str) -> List[Bounty]:
        """
        获取悬赏列表
        
        Args:
            user_id: 用户ID
            
        Returns:
            悬赏列表
        """
        # 检查缓存
        cached = self._get_cached_bounties(user_id)
        if cached:
            return cached
        
        # 获取玩家
        player = self.player_repo.get_by_id(user_id)
        if not player:
            raise BusinessException("玩家不存在")
        
        # 根据玩家等级生成悬赏
        plan = self._get_difficulty_plan(player.level_index)
        bounties = []
        
        for diff in plan:
            bounty = self._build_bounty(diff, player)
            if bounty:
                bounties.append(bounty)
        
        # 缓存
        self._set_cached_bounties(user_id, bounties)
        
        return bounties
    
    def _get_cached_bounties(self, user_id: str) -> Optional[List[Bounty]]:
        """获取缓存的悬赏列表"""
        cache = self._bounty_cache.get(user_id)
        if cache and cache["expire_time"] > int(time.time()):
            return cache["bounties"]
        return None
    
    def _set_cached_bounties(self, user_id: str, bounties: List[Bounty]):
        """设置缓存的悬赏列表"""
        self._bounty_cache[user_id] = {
            "bounties": bounties,
            "expire_time": int(time.time()) + self.BOUNTY_CACHE_DURATION
        }
    
    def _get_difficulty_plan(self, level_index: int) -> List[str]:
        """根据玩家等级获取难度计划"""
        plan = ["easy", "normal"]
        if level_index >= 7:
            plan.append("hard")
        if level_index >= 12:
            plan.append("elite")
        return [diff for diff in plan if diff in self.difficulties]
    
    def _build_bounty(self, difficulty: str, player) -> Optional[Bounty]:
        """构建悬赏对象"""
        template = self._pick_template(difficulty)
        if not template:
            return None
        
        diff_cfg = self.difficulties.get(difficulty, {})
        target = random.randint(template.get("min_target", 1), template.get("max_target", 1))
        reward = self._calculate_reward(template, diff_cfg, player, target)
        time_limit = template.get("time_limit", 3600)
        
        return Bounty(
            id=template["id"],
            name=template["name"],
            category=template.get("category", "任务"),
            difficulty=difficulty,
            difficulty_name=diff_cfg.get("name", difficulty),
            description=template.get("description", ""),
            count=target,
            reward=reward,
            time_limit=time_limit,
            progress_tags=template.get("progress_tags", []),
            item_table=template.get("item_table", "gather")
        )
    
    def _pick_template(self, difficulty: str) -> Optional[dict]:
        """随机选择一个模板"""
        templates = self.templates_by_diff.get(difficulty)
        if not templates:
            return None
        
        total = sum(max(1, t.get("weight", 1)) for t in templates)
        roll = random.randint(1, total)
        upto = 0
        
        for t in templates:
            upto += max(1, t.get("weight", 1))
            if roll <= upto:
                return t
        
        return templates[0]
    
    def _calculate_reward(self, template: dict, diff_cfg: dict, player, target: int) -> Dict[str, int]:
        """计算奖励"""
        base_reward = template.get("reward", {"stone": 200, "exp": 2000})
        stone = base_reward.get("stone", 0)
        exp = base_reward.get("exp", 0)
        
        # 等级加成
        level_bonus = 1 + max(0, player.level_index - 3) * 0.06
        # 进度因子
        progress_factor = max(1, target) / max(1, template.get("min_target", 1))
        # 难度系数
        stone_scale = diff_cfg.get("stone_scale", 1.0)
        exp_scale = diff_cfg.get("exp_scale", 1.0)
        
        final_stone = int(stone * stone_scale * progress_factor * level_bonus)
        final_exp = int(exp * exp_scale * progress_factor * level_bonus)
        
        return {"stone": final_stone, "exp": final_exp}
    
    def accept_bounty(self, user_id: str, bounty_id: int) -> str:
        """
        接取悬赏
        
        Args:
            user_id: 用户ID
            bounty_id: 悬赏ID
            
        Returns:
            结果消息
        """
        if bounty_id <= 0:
            raise BusinessException("无效的悬赏编号")
        
        # 检查模板是否存在
        template = self.templates_by_id.get(bounty_id)
        if not template:
            raise BusinessException("该悬赏已失效，请刷新列表")
        
        # 检查缓存中的悬赏
        cached_bounties = self._get_cached_bounties(user_id)
        cached = None
        if cached_bounties:
            cached = next((b for b in cached_bounties if b.id == bounty_id), None)
        
        if not cached:
            raise BusinessException("⚠️ 悬赏列表已刷新，请先发送【悬赏令】重新查看后再接取")
        
        # 检查是否已有进行中的悬赏
        active = self.bounty_repo.get_active_bounty(user_id)
        if active:
            raise BusinessException(f"你已有进行中的悬赏：{active.bounty_name}，请先完成或放弃")
        
        # 检查放弃冷却
        cd_time = self.bounty_repo.get_abandon_cooldown(user_id)
        now = int(time.time())
        if cd_time and now < cd_time:
            remaining = (cd_time - now) // 60 or 1
            raise BusinessException(f"你刚放弃过悬赏，还需等待 {remaining} 分钟才能再次接取")
        
        # 创建任务
        expire_time = now + cached.time_limit
        task = BountyTask(
            user_id=user_id,
            bounty_id=bounty_id,
            bounty_name=cached.name,
            target_type=cached.category,
            target_count=cached.count,
            current_progress=0,
            rewards=json.dumps(cached.reward, ensure_ascii=False),
            start_time=now,
            expire_time=expire_time,
            status=1  # 进行中
        )
        
        self.bounty_repo.create_task(task)
        
        return (
            f"🎯 接取悬赏成功！\n"
            f"任务：{cached.name}（{cached.difficulty_name}）\n"
            f"目标：完成 {cached.count} 次\n"
            f"奖励：{cached.reward['stone']:,} 灵石 + {cached.reward['exp']:,} 修为\n"
            f"时限：{cached.time_limit // 60} 分钟"
        )
    
    def check_bounty_status(self, user_id: str) -> str:
        """
        检查悬赏状态
        
        Args:
            user_id: 用户ID
            
        Returns:
            状态消息
        """
        active = self.bounty_repo.get_active_bounty(user_id)
        if not active:
            return "你当前没有进行中的悬赏任务。\n使用【悬赏令】查看可接取的任务。"
        
        rewards = json.loads(active.rewards)
        remaining = max(0, active.expire_time - int(time.time()))
        
        return (
            f"📜 当前悬赏\n"
            f"━━━━━━━━━━━━━━━\n"
            f"任务：{active.bounty_name}\n"
            f"进度：{active.current_progress}/{active.target_count}\n"
            f"奖励：{rewards.get('stone', 0):,} 灵石 + {rewards.get('exp', 0):,} 修为\n"
            f"剩余时间：{remaining // 60} 分钟\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💡 完成后使用【完成悬赏】领取奖励"
        )
    
    def complete_bounty(self, user_id: str) -> str:
        """
        完成悬赏
        
        Args:
            user_id: 用户ID
            
        Returns:
            结果消息
        """
        active = self.bounty_repo.get_active_bounty(user_id)
        if not active:
            raise BusinessException("你当前没有进行中的悬赏任务")
        
        # 检查是否超时
        if int(time.time()) > active.expire_time:
            self.bounty_repo.update_task_status(user_id, 0)  # 取消
            raise BusinessException("悬赏任务已超时，自动取消")
        
        # 检查进度
        if active.current_progress < active.target_count:
            raise BusinessException(
                f"❌ 任务尚未完成！\n"
                f"任务：{active.bounty_name}\n"
                f"进度：{active.current_progress}/{active.target_count}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"💡 通过历练或秘境推进悬赏进度"
            )
        
        # 发放奖励
        rewards = json.loads(active.rewards)
        stone_reward = rewards.get("stone", 0)
        exp_reward = rewards.get("exp", 0)
        
        player = self.player_repo.get_by_id(user_id)
        if not player:
            raise BusinessException("玩家不存在")
        
        player.gold += stone_reward
        player.experience += exp_reward
        self.player_repo.save(player)
        
        # 更新任务状态
        self.bounty_repo.update_task_status(user_id, 2)  # 已完成
        
        # TODO: 物品奖励
        
        return (
            f"✅ 悬赏完成！\n"
            f"任务：{active.bounty_name}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"获得灵石：+{stone_reward:,}\n"
            f"获得修为：+{exp_reward:,}"
        )
    
    def abandon_bounty(self, user_id: str) -> str:
        """
        放弃悬赏
        
        Args:
            user_id: 用户ID
            
        Returns:
            结果消息
        """
        active = self.bounty_repo.get_active_bounty(user_id)
        if not active:
            raise BusinessException("你当前没有进行中的悬赏任务")
        
        # 取消任务
        self.bounty_repo.update_task_status(user_id, 0)
        
        # 设置冷却
        abandon_cooldown = int(time.time()) + 1800  # 30分钟
        self.bounty_repo.set_abandon_cooldown(user_id, abandon_cooldown)
        
        return f"已放弃悬赏：{active.bounty_name}\n⚠️ 30分钟内无法接取新悬赏"
