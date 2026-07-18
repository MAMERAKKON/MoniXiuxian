"""玩家命令处理器"""
import time
from astrbot.api.event import AstrMessageEvent
from astrbot.api.message_components import At
from astrbot.api import logger

from ...application.services.player_service import PlayerService
from ...core.exceptions import (
    PlayerAlreadyExistsException,
    InvalidParameterException
)
from ...domain.enums import CultivationType, PlayerState
from ...utils.spirit_root_generator import SpiritRootGenerator
from ..decorators import require_player
from ..formatters import PlayerFormatter


class PlayerHandler:
    """玩家命令处理器"""
    
    def __init__(
        self,
        player_service: PlayerService,
        spirit_root_generator: SpiritRootGenerator,
        container=None
    ):
        self.player_service = player_service
        self.spirit_root_generator = spirit_root_generator
        self.container = container
    
    async def handle_create_player(
        self,
        event: AstrMessageEvent,
        cultivation_type: str = ""
    ):
        """处理创建角色命令"""
        user_id = event.get_sender_id()
        
        if not cultivation_type or cultivation_type.strip() == "":
            help_msg = PlayerFormatter.format_create_help()
            yield event.plain_result(help_msg)
            return
        
        cultivation_type = cultivation_type.strip()
        try:
            cult_type = CultivationType.from_string(cultivation_type)
        except ValueError:
            yield event.plain_result("❌ 职业选择错误！请选择「灵修」或「体修」。")
            return
        
        try:
            sender_name = event.get_sender_name()
            player = self.player_service.create_player(user_id, cult_type, sender_name)
            
            root_name = player.spiritual_root.replace("灵根", "")
            from ...utils.spirit_root_generator import SpiritRootGenerator
            description = SpiritRootGenerator.ROOT_DESCRIPTIONS.get(
                root_name,
                "【未知】神秘的灵根"
            )
            
            from ...domain.value_objects import SpiritRootInfo
            temp_root_info = SpiritRootInfo(
                name=root_name,
                speed_multiplier=1.0,
                description=description
            )
            
            message = PlayerFormatter.format_create_success(
                player,
                temp_root_info,
                sender_name
            )
            
            yield event.plain_result(message)
            
        except PlayerAlreadyExistsException:
            yield event.plain_result("❌ 道友，你已踏入仙途，无需重复此举。")
        except Exception as e:
            yield event.plain_result(f"❌ 创建角色失败：{str(e)}")
    
    @require_player
    async def handle_player_info(self, event: AstrMessageEvent, player):
        """处理查看信息命令"""
        try:
            level_name = self.player_service.get_level_name(player)
            required_exp = self.player_service.get_required_exp(player)
            
            from ...application.services.equipment_service import EquipmentService
            from ...infrastructure.repositories.equipment_repo import EquipmentRepository
            from ...infrastructure.repositories.storage_ring_repo import StorageRingRepository
            
            equipment_repo = EquipmentRepository(
                self.player_service.player_repo.storage,
                self.container.config_manager().config_dir
            )
            storage_ring_repo = StorageRingRepository(self.player_service.player_repo.storage)
            
            equipment_service = EquipmentService(
                equipment_repo,
                self.player_service.player_repo,
                storage_ring_repo
            )
            equipment_bonuses = equipment_service.get_equipment_bonuses(player.user_id)
            # 信息面板预览全局修为倍率：灵根 ×（心得/功法与洞天）。
            # 目前只调整显示，不改变实际闭关结算。
            technique_land_bonus = self.player_service.player_repo.get_experience_bonus(
                player.user_id
            )
            root_name = player.spiritual_root.replace("灵根", "")
            root_multiplier = self.spirit_root_generator.get_root_speed_by_name(root_name)
            equipment_bonuses.exp_multiplier = root_multiplier * (1.0 + technique_land_bonus) - 1.0
            equipment_bonuses.root_multiplier = root_multiplier
            equipment_bonuses.technique_land_bonus = technique_land_bonus
            
            combat_power = player.calculate_power()
            combat_power += (
                equipment_bonuses.magic_damage +
                equipment_bonuses.physical_damage +
                equipment_bonuses.magic_defense +
                equipment_bonuses.physical_defense +
                equipment_bonuses.mental_power // 10
            )
            
            sect_name = "无宗门"
            position_name = "散修"
            if player.sect_id and self.container:
                sect = self.container.sect_repository().get_by_id(player.sect_id)
                if sect:
                    sect_name = sect.name
                position_names = {0: "宗主", 1: "长老", 2: "亲传弟子", 3: "内门弟子", 4: "外门弟子"}
                position_name = position_names.get(player.sect_position, "宗门成员")

            inheritance_info = {"count": 0, "permanent": {}, "current": {}, "bounty_merit": 0}
            reward_tier, reward = self._calculate_realm_reward(player.level_index)
            inheritance_info["reward_tier"] = reward_tier or "炼气期不结算"
            inheritance_info["reward"] = reward
            if self.container:
                pool = self.container.reincarnation_repository().get_reincarnation_pool(player.user_id)
                if pool:
                    inheritance_info["count"] = pool.reincarnation_count
                    inheritance_info["permanent"] = {
                        k: v for k, v in pool.reincarnation_pool.items() if v > 0
                    }
                    inheritance_info["current"] = {
                        k: v for k, v in pool.current_life_pool.items() if v > 0
                    }
                    inheritance_info["bounty_merit"] = pool.bounty_merit
            
            message = PlayerFormatter.format_player_info(
                player,
                level_name,
                required_exp,
                combat_power,
                sect_name,
                position_name,
                equipment_bonuses,
                inheritance_info
            )
            
            yield event.plain_result(message)
            
        except Exception as e:
            yield event.plain_result(f"❌ 查看信息失败：{str(e)}")
    
    @require_player
    async def handle_check_in(self, event: AstrMessageEvent, player):
        """处理签到命令"""
        try:
            reward_gold = self.player_service.check_in(player)
            message = PlayerFormatter.format_check_in_success(
                reward_gold,
                player.gold
            )
            yield event.plain_result(message)
            
        except ValueError as e:
            yield event.plain_result(f"❌ {str(e)}\n请明日再来。")
        except Exception as e:
            yield event.plain_result(f"❌ 签到失败：{str(e)}")
    
    @require_player
    async def handle_change_nickname(
        self,
        event: AstrMessageEvent,
        player,
        new_nickname: str = ""
    ):
        """处理改道号命令"""
        if not new_nickname or new_nickname.strip() == "":
            yield event.plain_result(
                "❌ 请提供新道号\n"
                "💡 使用方法：改道号 新的道号"
            )
            return
        
        try:
            self.player_service.change_nickname(player, new_nickname)
            message = PlayerFormatter.format_nickname_changed(new_nickname)
            yield event.plain_result(message)
            
        except InvalidParameterException as e:
            yield event.plain_result(f"❌ {e.message}")
        except Exception as e:
            yield event.plain_result(f"❌ 修改道号失败：{str(e)}")

    def _calculate_realm_reward(self, level_index: int):
        """
        根据当前境界计算转世传承奖励
        
        Returns:
            (档位名称, 奖励字典)
        """
        # 炼气期（0-9）无奖励，防止刷属性
        if level_index <= 9:
            return None, {}
        
        # 档位配置：境界下限, 档位名称, 奖励
        TIERS = [
            (31, "渡劫", {"attack_percent": 0.35, "hp_percent": 0.35, "defense_percent": 0.18, "crit_rate_percent": 0.05, "crit_damage_percent": 0.12, "hp_flat": 5000, "attack_flat": 1000, "defense_flat": 500, "mp_flat": 5000}),
            (28, "大乘", {"attack_percent": 0.24, "hp_percent": 0.24, "defense_percent": 0.12, "crit_rate_percent": 0.035, "crit_damage_percent": 0.07, "hp_flat": 2500, "attack_flat": 500, "defense_flat": 250, "mp_flat": 2500}),
            (25, "合体", {"attack_percent": 0.18, "hp_percent": 0.18, "defense_percent": 0.09, "crit_rate_percent": 0.025, "hp_flat": 1000, "attack_flat": 200, "defense_flat": 100, "mp_flat": 1000}),
            (22, "炼虚", {"attack_percent": 0.14, "hp_percent": 0.14, "defense_percent": 0.07, "crit_rate_percent": 0.015, "hp_flat": 500, "attack_flat": 100, "defense_flat": 50, "mp_flat": 500}),
            (19, "化神", {"attack_percent": 0.10, "hp_percent": 0.10, "defense_percent": 0.05, "crit_rate_percent": 0.01, "hp_flat": 200, "attack_flat": 40, "defense_flat": 20, "mp_flat": 200}),
            (16, "元婴", {"attack_percent": 0.07, "hp_percent": 0.07, "defense_percent": 0.035, "hp_flat": 80, "attack_flat": 15, "defense_flat": 8, "mp_flat": 80}),
            (13, "金丹", {"attack_percent": 0.04, "hp_percent": 0.04, "defense_percent": 0.02, "hp_flat": 30, "attack_flat": 5, "defense_flat": 3, "mp_flat": 30}),
            (10, "筑基", {"attack_percent": 0.02, "hp_percent": 0.02, "hp_flat": 10, "attack_flat": 2, "defense_flat": 1, "mp_flat": 10}),
        ]
        
        for min_level, tier_name, reward in TIERS:
            if level_index >= min_level:
                logger.info(f"【轮回】玩家达到「{tier_name}」档位（境界索引{level_index}），获得传承奖励")
                return tier_name, reward
        
        return None, {}

    async def handle_rebirth(
        self,
        event: AstrMessageEvent,
        confirm_text: str = ""
    ):
        """
        处理轮回转世命令
        """
        user_id = event.get_sender_id()
        
        # 检查玩家是否存在
        player = self.player_service.get_player(user_id)
        if not player:
            yield event.plain_result(
                "❌ 你还未踏入修仙之路！\n"
                "💡 发送「我要修仙」开始你的修仙之旅"
            )
            return
        
        # 检查60秒冷却
        current_time = int(time.time())
        cooldown_key = f"rebirth_cooldown_{user_id}"
        
        config_repo = None
        try:
            if self.container:
                from ...infrastructure.repositories.system_config_repo import SystemConfigRepository
                config_repo = SystemConfigRepository(self.container.json_storage())
            
            last_rebirth_str = config_repo.get_config(cooldown_key) if config_repo else None
            if last_rebirth_str:
                last_rebirth_time = int(last_rebirth_str)
                cooldown_seconds = 60
                
                if current_time - last_rebirth_time < cooldown_seconds:
                    remaining = cooldown_seconds - (current_time - last_rebirth_time)
                    yield event.plain_result(
                        f"❌ 轮回转世冷却中！\n"
                        f"还需等待：{remaining}秒"
                    )
                    return
        except Exception:
            pass
        
        # 检查玩家状态
        if player.state != PlayerState.IDLE:
            yield event.plain_result(
                "❌ 你当前正在进行其他活动，无法轮回转世！\n"
                "请先完成当前活动（闭关/历练/秘境等）"
            )
            return
        
        # 检查是否有贷款
        try:
            bank_repo = None
            if self.container:
                from ...infrastructure.repositories.bank_repo import BankRepository
                bank_repo = BankRepository(self.container.json_storage())
            
            active_loans = bank_repo.get_active_loans(user_id) if bank_repo else []
            if active_loans:
                yield event.plain_result(
                    "❌ 你还有未还清的贷款，无法轮回转世！\n"
                    "请先使用「还款」命令还清所有贷款"
                )
                return
        except Exception:
            pass
        
        # 如果没有提供确认文本，显示警告
        if not confirm_text or confirm_text.strip() != "确认":
            yield event.plain_result(
                "⚠️ 轮回转世将删除当前角色的所有数据，并无法撤回！\n"
                "限制：每60秒只能轮回一次，且必须在空闲状态、无贷款时使用。\n"
                "━━━━━━━━━━━━━━━\n"
                "若你已做好准备，请发送：\n"
                "轮回转世 确认"
            )
            return
        
        # ===== 转世轮回：传承池合并 + 境界奖励 =====
        reincarnation_info = ""
        realm_reward_info = ""
        
        try:
            if self.container:
                reincarnation_repo = self.container.reincarnation_repository()
                reincarnation_data = reincarnation_repo.get_reincarnation_pool(user_id)
                is_first_reincarnation = reincarnation_data is None
                if reincarnation_data is None:
                    reincarnation_data = reincarnation_repo.create_reincarnation_pool(user_id)

                has_life_pool = any(v > 0 for v in reincarnation_data.current_life_pool.values())
                tier_name, realm_bonus = self._calculate_realm_reward(player.level_index)

                # 每次轮回只在这里合并一次并计数一次。
                # 百分比由领域模型按“每世乘算”合并，固定值仍然加算。
                reincarnation_data.merge_to_permanent(realm_bonus)
                reincarnation_data.last_reincarnation_time = current_time
                reincarnation_repo.save(reincarnation_data)

                if has_life_pool:
                    reincarnation_info = "✅ 本世传承已按乘算并入永久池"
                elif is_first_reincarnation:
                    reincarnation_info = "ℹ️ 首次转世，永久传承池已创建"
                else:
                    reincarnation_info = "ℹ️ 本世没有额外传承，已结算境界奖励"

                if realm_bonus:
                    label_map = {
                        "attack_percent": "攻击",
                        "hp_percent": "HP",
                        "defense_percent": "防御",
                        "crit_rate_percent": "暴击率",
                        "crit_damage_percent": "爆伤",
                        "hp_flat": "HP白值",
                        "attack_flat": "攻击白值",
                        "defense_flat": "防御白值",
                        "mp_flat": "神识白值"
                    }
                    reward_lines = []
                    for key, value in realm_bonus.items():
                        label = label_map.get(key, key)
                        if key.endswith("_percent"):
                            reward_lines.append(f"  · {label}: +{value*100:.1f}%")
                        else:
                            reward_lines.append(f"  · {label}: +{int(value):,}")
                    realm_reward_info = f"\n【{tier_name}·转世】\n" + "\n".join(reward_lines)
                    logger.info(f"【轮回】玩家 {user_id} 达成{tier_name}，获得境界奖励")
                elif player.level_index <= 9:
                    realm_reward_info = "\n【凡尘·转世】\n炼气期轮回无奖励，请提升境界再转世"
                            
        except Exception as e:
            logger.error(f"【轮回】传承池处理失败: {e}")
            reincarnation_info = "❌ 传承池处理失败，请稍后重试"
        
        # 执行删除
        try:
            # 先记录特殊道具与历练修炼心得，待新角色创建时自动放回储物戒。
            retained_assets = {}
            if self.container:
                retained_assets = self.player_service.capture_reincarnation_assets(user_id)
                liquidation_value = int(retained_assets.get("liquidation_value", 0) or 0)
                if liquidation_value > 0:
                    from ...infrastructure.repositories.bank_repo import BankRepository
                    bank_repo = BankRepository(self.container.json_storage())
                    account = bank_repo.get_bank_account(user_id)
                    current_balance = account.balance if account else 0
                    now = int(time.time())
                    last_interest_time = (
                        account.last_interest_time if account else now
                    )
                    bank_repo.create_or_update_bank_account(
                        user_id,
                        current_balance + liquidation_value,
                        last_interest_time,
                    )
            self.player_service.delete_player(user_id)
            
            try:
                if config_repo:
                    config_repo.set_config(cooldown_key, str(current_time))
            except Exception:
                pass
            
            yield event.plain_result(
                f"💀 你选择了轮回转世，旧生一切化为尘埃。\n"
                f"━━━━━━━━━━━━━━━\n"
                f"【转世轮回】\n"
                f"{reincarnation_info}\n"
                f"{realm_reward_info}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"可立即使用「我要修仙」重新踏上仙途。\n"
                f"（60秒内不可再次轮回；新生角色享有8小时轮回庇护，"
                f"主动发起传承挑战将立即解除）"
            )
            
        except Exception as e:
            yield event.plain_result(f"❌ 轮回转世失败：{str(e)}")

    async def handle_admin_add_gold(
        self,
        event: AstrMessageEvent,
        args: str = ""
    ):
        """处理管理员增加灵石命令"""
        user_id = str(event.get_sender_id())
        
        if not self.container:
            yield event.plain_result("❌ 系统错误：容器未初始化")
            return
        
        config_manager = self.container.config_manager()
        admin_list = config_manager.settings.access_control.admins
        
        if not admin_list or user_id not in admin_list:
            yield event.plain_result("❌ 权限不足！\n💡 此命令仅限管理员使用")
            return
        
        if not args or args.strip() == "":
            yield event.plain_result(
                "❌ 参数错误！\n"
                "💡 使用方法：增加灵石 数量 @用户\n"
                "示例：增加灵石 10000 @张三"
            )
            return
        
        try:
            parts = args.strip().split()
            if len(parts) < 1:
                yield event.plain_result("❌ 参数不足！\n💡 使用方法：增加灵石 数量 @用户")
                return
            
            try:
                amount = int(parts[0])
                if amount <= 0:
                    yield event.plain_result("❌ 数量必须大于0！")
                    return
            except ValueError:
                yield event.plain_result("❌ 数量必须是有效的数字！")
                return
            
            target_user_id = None
            
            if len(parts) >= 2:
                cleaned = parts[1].strip().lstrip("@")
                if cleaned.isdigit():
                    target_user_id = cleaned
            
            if not target_user_id:
                message_chain = []
                if hasattr(event, "message_obj") and event.message_obj:
                    message_chain = getattr(event.message_obj, "message", []) or []
                
                found_command = False
                for component in message_chain:
                    if hasattr(component, "text"):
                        text = getattr(component, "text", "")
                        if "增加灵石" in text:
                            found_command = True
                            import re
                            match = re.search(r'增加灵石\s+\d+\s+(\d+)', text)
                            if match:
                                target_user_id = match.group(1)
                                break
                            continue
                    
                    if found_command and isinstance(component, At):
                        candidate = None
                        for attr in ("qq", "target", "uin", "user_id"):
                            candidate = getattr(component, attr, None)
                            if candidate:
                                break
                        if candidate:
                            target_user_id = str(candidate).lstrip("@")
                            break
            
            if not target_user_id:
                yield event.plain_result(
                    "❌ 未找到目标用户！\n"
                    "💡 使用方法：增加灵石 数量 @用户 或 增加灵石 数量 用户ID"
                )
                return
            
            target_player = self.player_service.get_player(target_user_id)
            if not target_player:
                yield event.plain_result(f"❌ 目标用户（{target_user_id}）还未踏入修仙之路！")
                return
            
            old_gold = target_player.gold
            target_player.gold += amount
            self.player_service.player_repo.save(target_player)
            
            yield event.plain_result(
                "✅ 灵石增加成功！\n"
                "━━━━━━━━━━━━━━━\n"
                f"目标用户：{target_player.nickname}\n"
                f"增加数量：{amount:,} 灵石\n"
                f"原有灵石：{old_gold:,}\n"
                f"当前灵石：{target_player.gold:,}"
            )
            
        except Exception as e:
            yield event.plain_result(f"❌ 增加灵石失败：{str(e)}")

    async def handle_become_god(self, event: AstrMessageEvent):
        """处理专属成神指令。"""
        user_id = str(event.get_sender_id())
        try:
            player = self.player_service.become_god(user_id)
            level_data = self.container.config_manager().get_level_data(
                player.cultivation_type.value
            )
            realm_name = level_data[player.level_index].get(
                "name",
                level_data[player.level_index].get("level_name", "最高境界")
            )
            yield event.plain_result(
                "🌌 成神仪式完成！\n"
                "━━━━━━━━━━━━━━━\n"
                f"境界：{realm_name}\n"
                f"修为：{player.experience:,}\n"
                "其余核心数值：114,514\n"
                "━━━━━━━━━━━━━━━\n"
                "天命已定，诸界皆在掌中。"
            )
        except PermissionError:
            # 不向其他用户暴露专属指令的具体归属。
            yield event.plain_result("❌ 你无法承受此等天命。")
        except Exception as e:
            yield event.plain_result(f"❌ 成神失败：{str(e)}")

    async def handle_admin_reduce_gold(
        self,
        event: AstrMessageEvent,
        args: str = ""
    ):
        """处理管理员减少灵石命令"""
        user_id = str(event.get_sender_id())
        
        if not self.container:
            yield event.plain_result("❌ 系统错误：容器未初始化")
            return
        
        config_manager = self.container.config_manager()
        admin_list = config_manager.settings.access_control.admins
        
        if not admin_list or user_id not in admin_list:
            yield event.plain_result("❌ 权限不足！\n💡 此命令仅限管理员使用")
            return
        
        if not args or args.strip() == "":
            yield event.plain_result(
                "❌ 参数错误！\n"
                "💡 使用方法：减少灵石 数量 @用户\n"
                "示例：减少灵石 10000 @张三"
            )
            return
        
        try:
            parts = args.strip().split()
            if len(parts) < 1:
                yield event.plain_result("❌ 参数不足！\n💡 使用方法：减少灵石 数量 @用户")
                return
            
            try:
                amount = int(parts[0])
                if amount <= 0:
                    yield event.plain_result("❌ 数量必须大于0！")
                    return
            except ValueError:
                yield event.plain_result("❌ 数量必须是有效的数字！")
                return
            
            target_user_id = None
            
            if len(parts) >= 2:
                cleaned = parts[1].strip().lstrip("@")
                if cleaned.isdigit():
                    target_user_id = cleaned
            
            if not target_user_id:
                message_chain = []
                if hasattr(event, "message_obj") and event.message_obj:
                    message_chain = getattr(event.message_obj, "message", []) or []
                
                found_command = False
                for component in message_chain:
                    if hasattr(component, "text"):
                        text = getattr(component, "text", "")
                        if "减少灵石" in text:
                            found_command = True
                            import re
                            match = re.search(r'减少灵石\s+\d+\s+(\d+)', text)
                            if match:
                                target_user_id = match.group(1)
                                break
                            continue
                    
                    if found_command and isinstance(component, At):
                        candidate = None
                        for attr in ("qq", "target", "uin", "user_id"):
                            candidate = getattr(component, attr, None)
                            if candidate:
                                break
                        if candidate:
                            target_user_id = str(candidate).lstrip("@")
                            break
            
            if not target_user_id:
                yield event.plain_result(
                    "❌ 未找到目标用户！\n"
                    "💡 使用方法：减少灵石 数量 @用户 或 减少灵石 数量 用户ID"
                )
                return
            
            target_player = self.player_service.get_player(target_user_id)
            if not target_player:
                yield event.plain_result(f"❌ 目标用户（{target_user_id}）还未踏入修仙之路！")
                return
            
            old_gold = target_player.gold
            target_player.gold = max(0, target_player.gold - amount)
            actual_reduced = old_gold - target_player.gold
            self.player_service.player_repo.save(target_player)
            
            result_msg = "✅ 灵石减少成功！\n" + "━━━━━━━━━━━━━━━\n"
            result_msg += f"目标用户：{target_player.nickname}\n"
            result_msg += f"减少数量：{actual_reduced:,} 灵石\n"
            result_msg += f"原有灵石：{old_gold:,}\n"
            result_msg += f"当前灵石：{target_player.gold:,}"
            
            if actual_reduced < amount:
                result_msg += f"\n\n⚠️ 注意：目标用户灵石不足，实际减少 {actual_reduced:,} 灵石"
            
            yield event.plain_result(result_msg)
            
        except Exception as e:
            yield event.plain_result(f"❌ 减少灵石失败：{str(e)}")

    async def handle_admin_change_spirit_root(
        self,
        event: AstrMessageEvent,
        args: str = ""
    ):
        """处理管理员修改灵根命令"""
        user_id = str(event.get_sender_id())
        
        if not self.container:
            yield event.plain_result("❌ 系统错误：容器未初始化")
            return
        
        config_manager = self.container.config_manager()
        admin_list = config_manager.settings.access_control.admins
        
        if not admin_list or user_id not in admin_list:
            yield event.plain_result("❌ 权限不足！\n💡 此命令仅限管理员使用")
            return
        
        if not args or args.strip() == "":
            yield event.plain_result(
                "❌ 参数错误！\n"
                "💡 使用方法：修改灵根 灵根类型 @用户\n"
                "示例：修改灵根 天金灵根 @张三"
            )
            return
        
        try:
            parts = args.strip().split()
            if len(parts) < 1:
                yield event.plain_result("❌ 参数不足！\n💡 使用方法：修改灵根 灵根类型 @用户")
                return
            
            spirit_root = parts[0].strip()
            if not spirit_root.endswith("灵根"):
                spirit_root = spirit_root + "灵根"
            
            target_user_id = None
            
            if len(parts) >= 2:
                cleaned = parts[1].strip().lstrip("@")
                if cleaned.isdigit():
                    target_user_id = cleaned
            
            if not target_user_id:
                message_chain = []
                if hasattr(event, "message_obj") and event.message_obj:
                    message_chain = getattr(event.message_obj, "message", []) or []
                
                found_command = False
                for component in message_chain:
                    if hasattr(component, "text"):
                        text = getattr(component, "text", "")
                        if "修改灵根" in text:
                            found_command = True
                            import re
                            match = re.search(r'修改灵根\s+\S+\s+(\d+)', text)
                            if match:
                                target_user_id = match.group(1)
                                break
                            continue
                    
                    if found_command and isinstance(component, At):
                        candidate = None
                        for attr in ("qq", "target", "uin", "user_id"):
                            candidate = getattr(component, attr, None)
                            if candidate:
                                break
                        if candidate:
                            target_user_id = str(candidate).lstrip("@")
                            break
            
            if not target_user_id:
                yield event.plain_result(
                    "❌ 未找到目标用户！\n"
                    "💡 使用方法：修改灵根 灵根类型 @用户 或 修改灵根 灵根类型 用户ID"
                )
                return
            
            target_player = self.player_service.get_player(target_user_id)
            if not target_player:
                yield event.plain_result(f"❌ 目标用户（{target_user_id}）还未踏入修仙之路！")
                return
            
            old_root = target_player.spiritual_root
            target_player.spiritual_root = spirit_root
            self.player_service.player_repo.save(target_player)
            
            yield event.plain_result(
                "✅ 灵根修改成功！\n"
                "━━━━━━━━━━━━━━━\n"
                f"目标用户：{target_player.nickname}\n"
                f"原有灵根：{old_root}\n"
                f"当前灵根：{target_player.spiritual_root}"
            )
            
        except Exception as e:
            yield event.plain_result(f"❌ 修改灵根失败：{str(e)}")

    async def handle_admin_add_experience(
        self,
        event: AstrMessageEvent,
        args: str = ""
    ):
        """处理管理员增加修为命令"""
        user_id = str(event.get_sender_id())
        
        if not self.container:
            yield event.plain_result("❌ 系统错误：容器未初始化")
            return
        
        config_manager = self.container.config_manager()
        admin_list = config_manager.settings.access_control.admins
        
        if not admin_list or user_id not in admin_list:
            yield event.plain_result("❌ 权限不足！\n💡 此命令仅限管理员使用")
            return
        
        if not args or args.strip() == "":
            yield event.plain_result(
                "❌ 参数错误！\n"
                "💡 使用方法：增加修为 数量 @用户\n"
                "示例：增加修为 100000 @张三"
            )
            return
        
        try:
            parts = args.strip().split()
            if len(parts) < 1:
                yield event.plain_result("❌ 参数不足！\n💡 使用方法：增加修为 数量 @用户")
                return
            
            try:
                amount = int(parts[0])
                if amount <= 0:
                    yield event.plain_result("❌ 数量必须大于0！")
                    return
            except ValueError:
                yield event.plain_result("❌ 数量必须是有效的数字！")
                return
            
            target_user_id = None
            
            if len(parts) >= 2:
                cleaned = parts[1].strip().lstrip("@")
                if cleaned.isdigit():
                    target_user_id = cleaned
            
            if not target_user_id:
                message_chain = []
                if hasattr(event, "message_obj") and event.message_obj:
                    message_chain = getattr(event.message_obj, "message", []) or []
                
                found_command = False
                for component in message_chain:
                    if hasattr(component, "text"):
                        text = getattr(component, "text", "")
                        if "增加修为" in text:
                            found_command = True
                            import re
                            match = re.search(r'增加修为\s+\d+\s+(\d+)', text)
                            if match:
                                target_user_id = match.group(1)
                                break
                            continue
                    
                    if found_command and isinstance(component, At):
                        candidate = None
                        for attr in ("qq", "target", "uin", "user_id"):
                            candidate = getattr(component, attr, None)
                            if candidate:
                                break
                        if candidate:
                            target_user_id = str(candidate).lstrip("@")
                            break
            
            if not target_user_id:
                yield event.plain_result(
                    "❌ 未找到目标用户！\n"
                    "💡 使用方法：增加修为 数量 @用户 或 增加修为 数量 用户ID"
                )
                return
            
            target_player = self.player_service.get_player(target_user_id)
            if not target_player:
                yield event.plain_result(f"❌ 目标用户（{target_user_id}）还未踏入修仙之路！")
                return
            
            old_exp = target_player.experience
            target_player.experience += amount
            self.player_service.player_repo.save(target_player)
            
            yield event.plain_result(
                "✅ 修为增加成功！\n"
                "━━━━━━━━━━━━━━━\n"
                f"目标用户：{target_player.nickname}\n"
                f"增加数量：{amount:,} 修为\n"
                f"原有修为：{old_exp:,}\n"
                f"当前修为：{target_player.experience:,}"
            )
            
        except Exception as e:
            yield event.plain_result(f"❌ 增加修为失败：{str(e)}")

    async def handle_admin_change_sect_position(
        self,
        event: AstrMessageEvent,
        args: str = ""
    ):
        """处理管理员修改宗门岗位命令"""
        user_id = str(event.get_sender_id())
        
        if not self.container:
            yield event.plain_result("❌ 系统错误：容器未初始化")
            return
        
        config_manager = self.container.config_manager()
        admin_list = config_manager.settings.access_control.admins
        
        if not admin_list or user_id not in admin_list:
            yield event.plain_result("❌ 权限不足！\n💡 此命令仅限管理员使用")
            return
        
        if not args or args.strip() == "":
            yield event.plain_result(
                "❌ 参数错误！\n"
                "💡 使用方法：修改宗门岗位 岗位ID @用户\n"
                "示例：修改宗门岗位 0 @张三\n"
                "━━━━━━━━━━━━━━━\n"
                "岗位ID说明：\n"
                "• 0 - 宗主\n"
                "• 1 - 长老\n"
                "• 2 - 亲传弟子\n"
                "• 3 - 内门弟子\n"
                "• 4 - 外门弟子"
            )
            return
        
        try:
            parts = args.strip().split()
            if len(parts) < 1:
                yield event.plain_result("❌ 参数不足！\n💡 使用方法：修改宗门岗位 岗位ID @用户")
                return
            
            try:
                position_id = int(parts[0])
                if position_id < 0 or position_id > 4:
                    yield event.plain_result("❌ 岗位ID必须在0-4之间！")
                    return
            except ValueError:
                yield event.plain_result("❌ 岗位ID必须是有效的数字（0-4）！")
                return
            
            position_names = {0: "宗主", 1: "长老", 2: "亲传弟子", 3: "内门弟子", 4: "外门弟子"}
            
            target_user_id = None
            
            if len(parts) >= 2:
                cleaned = parts[1].strip().lstrip("@")
                if cleaned.isdigit():
                    target_user_id = cleaned
            
            if not target_user_id:
                message_chain = []
                if hasattr(event, "message_obj") and event.message_obj:
                    message_chain = getattr(event.message_obj, "message", []) or []
                
                found_command = False
                for component in message_chain:
                    if hasattr(component, "text"):
                        text = getattr(component, "text", "")
                        if "修改宗门岗位" in text:
                            found_command = True
                            import re
                            match = re.search(r'修改宗门岗位\s+\d+\s+(\d+)', text)
                            if match:
                                target_user_id = match.group(1)
                                break
                            continue
                    
                    if found_command and isinstance(component, At):
                        candidate = None
                        for attr in ("qq", "target", "uin", "user_id"):
                            candidate = getattr(component, attr, None)
                            if candidate:
                                break
                        if candidate:
                            target_user_id = str(candidate).lstrip("@")
                            break
            
            if not target_user_id:
                yield event.plain_result(
                    "❌ 未找到目标用户！\n"
                    "💡 使用方法：修改宗门岗位 岗位ID @用户 或 修改宗门岗位 岗位ID 用户ID"
                )
                return
            
            target_player = self.player_service.get_player(target_user_id)
            if not target_player:
                yield event.plain_result(f"❌ 目标用户（{target_user_id}）还未踏入修仙之路！")
                return
            
            if not target_player.sect_id or target_player.sect_id == 0:
                yield event.plain_result(f"❌ 目标用户（{target_player.nickname}）还未加入任何宗门！")
                return
            
            old_position = target_player.sect_position if target_player.sect_position is not None else 4
            old_position_name = position_names.get(old_position, "未知")
            
            target_player.sect_position = position_id
            self.player_service.player_repo.save(target_player)
            
            yield event.plain_result(
                "✅ 宗门岗位修改成功！\n"
                "━━━━━━━━━━━━━━━\n"
                f"目标用户：{target_player.nickname}\n"
                f"原有岗位：{old_position_name}\n"
                f"当前岗位：{position_names[position_id]}"
            )
            
        except Exception as e:
            yield event.plain_result(f"❌ 修改宗门岗位失败：{str(e)}")

    async def handle_admin_add_item(
        self,
        event: AstrMessageEvent,
        args: str = ""
    ):
        """处理管理员增加道具命令"""
        user_id = str(event.get_sender_id())
        
        if not self.container:
            yield event.plain_result("❌ 系统错误：容器未初始化")
            return
        
        config_manager = self.container.config_manager()
        admin_list = config_manager.settings.access_control.admins
        
        if not admin_list or user_id not in admin_list:
            yield event.plain_result("❌ 权限不足！\n💡 此命令仅限管理员使用")
            return
        
        if not args or args.strip() == "":
            yield event.plain_result(
                "❌ 参数错误！\n"
                "💡 使用方法：增加道具 道具名称 数量 @用户\n"
                "示例：增加道具 灵草 10 @张三"
            )
            return
        
        try:
            # 处理完整消息提取
            full_text = ""
            if hasattr(event, "message_str"):
                full_text = event.message_str
            elif hasattr(event, "get_message_str"):
                full_text = event.get_message_str()
            
            if full_text and "增加道具" in full_text:
                import re
                match = re.search(r'增加道具\s+(.+)', full_text)
                if match:
                    args = match.group(1).strip()
            
            parts = args.strip().split()
            
            if len(parts) < 3:
                yield event.plain_result(
                    "❌ 参数不足！\n"
                    "💡 使用方法：增加道具 道具名称 数量 @用户 或 增加道具 道具名称 数量 用户ID"
                )
                return
            
            item_name = parts[0]
            
            try:
                count = int(parts[1])
                if count <= 0:
                    yield event.plain_result("❌ 数量必须大于0！")
                    return
            except ValueError:
                yield event.plain_result("❌ 数量必须是有效的数字！")
                return
            
            target_user_id = None
            cleaned = parts[2].strip().lstrip("@")
            if cleaned.isdigit():
                target_user_id = cleaned
            
            if not target_user_id:
                message_chain = []
                if hasattr(event, "message_obj") and event.message_obj:
                    message_chain = getattr(event.message_obj, "message", []) or []
                
                found_command = False
                for component in message_chain:
                    if hasattr(component, "text"):
                        text = getattr(component, "text", "")
                        if "增加道具" in text:
                            found_command = True
                            import re
                            match = re.search(r'增加道具\s+\S+\s+\d+\s+(\d+)', text)
                            if match:
                                target_user_id = match.group(1)
                                break
                            continue
                    
                    if found_command and isinstance(component, At):
                        candidate = None
                        for attr in ("qq", "target", "uin", "user_id"):
                            candidate = getattr(component, attr, None)
                            if candidate:
                                break
                        if candidate:
                            target_user_id = str(candidate).lstrip("@")
                            break
            
            if not target_user_id:
                yield event.plain_result(
                    "❌ 未找到目标用户！\n"
                    "💡 使用方法：增加道具 道具名称 数量 @用户 或 增加道具 道具名称 数量 用户ID"
                )
                return
            
            target_player = self.player_service.get_player(target_user_id)
            if not target_player:
                yield event.plain_result(f"❌ 目标用户（{target_user_id}）还未踏入修仙之路！")
                return
            
            storage_ring_service = self.container.storage_ring_service()
            success, message = storage_ring_service.store_item(
                target_user_id,
                item_name,
                count,
                silent=True
            )
            
            if success:
                ring_info = storage_ring_service.get_storage_ring_info(target_user_id)
                item_count = storage_ring_service.get_item_count(target_user_id, item_name)
                
                yield event.plain_result(
                    "✅ 道具增加成功！\n"
                    "━━━━━━━━━━━━━━━\n"
                    f"目标用户：{target_player.nickname}\n"
                    f"道具名称：{item_name}\n"
                    f"增加数量：{count}\n"
                    f"当前拥有：{item_count}\n"
                    f"储物戒：{ring_info['name']}（{ring_info['used']}/{ring_info['capacity']}格）"
                )
            else:
                yield event.plain_result(f"❌ 增加道具失败：{message}")
            
        except Exception as e:
            yield event.plain_result(f"❌ 增加道具失败：{str(e)}")

    async def handle_admin_distribute_group_item(
        self,
        event: AstrMessageEvent,
        args: str = "",
    ):
        """管理员向当前QQ群内所有已建档玩家发放道具。"""
        user_id = str(event.get_sender_id())
        if not self.container:
            yield event.plain_result("❌ 系统错误：容器未初始化")
            return

        admin_list = self.container.config_manager().settings.access_control.admins
        if not admin_list or user_id not in admin_list:
            yield event.plain_result("❌ 权限不足：此命令仅限管理员使用")
            return

        # 兼容“小豆黑幕发放 大番茄 1”等带唤醒前缀的完整消息；
        # 部分适配器不会把命令后的文本自动传入 args。
        full_text = ""
        if hasattr(event, "message_str"):
            full_text = str(event.message_str or "")
        elif hasattr(event, "get_message_str"):
            try:
                full_text = str(event.get_message_str() or "")
            except Exception:
                full_text = ""
        if full_text and "黑幕发放" in full_text:
            import re
            match = re.search(r"黑幕发放\s+(.+)", full_text)
            if match:
                args = match.group(1).strip()

        parts = str(args or "").strip().split()
        if len(parts) < 2:
            yield event.plain_result("用法：黑幕发放 <道具名称> <数量>")
            return
        item_name = parts[0]
        try:
            count = int(parts[1])
        except ValueError:
            yield event.plain_result("❌ 数量必须是整数")
            return
        if count <= 0:
            yield event.plain_result("❌ 数量必须大于 0")
            return

        group_id = str(event.get_group_id() or "").strip()
        if not group_id:
            yield event.plain_result("❌ 黑幕发放只能在群聊中使用")
            return

        bot = getattr(event, "bot", None)
        if bot is None:
            yield event.plain_result("❌ 当前平台不支持读取群成员列表")
            return

        try:
            member_result = await bot.call_action(
                "get_group_member_list",
                group_id=int(group_id),
            )
            if isinstance(member_result, dict):
                member_result = member_result.get("data", member_result.get("members", []))
            member_ids = {
                str(member.get("user_id", member.get("uin")))
                for member in (member_result or [])
                if isinstance(member, dict) and member.get("user_id", member.get("uin")) is not None
            }
        except Exception as e:
            yield event.plain_result(f"❌ 获取群成员列表失败：{e}")
            return

        storage_ring_service = self.container.storage_ring_service()
        players = self.player_service.player_repo.get_all_players()
        targets = [player for player in players if str(player.user_id) in member_ids]
        if not targets:
            yield event.plain_result("当前群内没有已创建修仙档案的玩家")
            return

        success_count = 0
        failed_count = 0
        for player in targets:
            success, _ = storage_ring_service.store_item(
                player.user_id,
                item_name,
                count,
                silent=True,
            )
            if success:
                success_count += 1
            else:
                failed_count += 1

        yield event.plain_result(
            "🕶️ 黑幕发放完成\n"
            f"道具：{item_name}\n数量：{count}\n"
            f"当前群已建档玩家：{len(targets)} 人\n"
            f"成功：{success_count} 人｜失败：{failed_count} 人"
        )
