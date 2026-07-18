"""储物戒命令处理器"""
from astrbot.api.event import AstrMessageEvent
from astrbot.api.all import At, Plain

from ...application.services.storage_ring_service import StorageRingService
from ...application.services.player_service import PlayerService
from ..decorators import require_player


class StorageRingHandler:
    """储物戒命令处理器"""
    
    def __init__(
        self,
        storage_ring_service: StorageRingService,
        player_service: PlayerService
    ):
        self.storage_ring_service = storage_ring_service
        self.player_service = player_service
    
    @require_player
    async def handle_storage_ring(self, event: AstrMessageEvent, player):
        """显示储物戒信息"""
        user_id = event.get_sender_id()
        display_name = event.get_sender_name()
        
        # 获取储物戒信息
        ring_info = self.storage_ring_service.get_storage_ring_info(user_id)
        
        lines = [
            f"=== {display_name} 的储物戒 ===\n",
            f"【{ring_info['name']}】（{ring_info['rank']}）\n",
            f"{ring_info['description']}\n",
            f"\n容量：{ring_info['used']}/{ring_info['capacity']}格\n",
            f"━━━━━━━━━━━━━━━\n",
        ]
        
        # 按分类显示存储的物品
        items = ring_info['items']
        if items:
            categorized = self.storage_ring_service.categorize_items(items)
            for category, cat_items in categorized.items():
                if cat_items:
                    lines.append(f"【{category}】\n")
                    for item_name, count in cat_items:
                        # 获取参考价格
                        ref_price = self.storage_ring_service.get_reference_price(item_name)
                        
                        if count > 1:
                            if ref_price:
                                lines.append(f"  · {item_name}×{count} (参考价:{ref_price})\n")
                            else:
                                lines.append(f"  · {item_name}×{count}\n")
                        else:
                            if ref_price:
                                lines.append(f"  · {item_name} (参考价:{ref_price})\n")
                            else:
                                lines.append(f"  · {item_name}\n")
        else:
            lines.append("【存储物品】空\n")
        
        # 空间警告
        warning = self.storage_ring_service.get_space_warning(user_id)
        if warning:
            lines.append(f"\n{warning}\n")
        
        lines.append(f"\n{'=' * 28}\n")
        lines.append(f"查看：小豆查看物品 物品名\n")
        lines.append(f"搜索：搜索物品 关键词\n")
        lines.append(f"升级：升级储物戒")
        
        yield event.plain_result("".join(lines))
    
    @require_player
    async def handle_discard_item(self, event: AstrMessageEvent, player, args: str = ""):
        """丢弃储物戒中的物品"""
        user_id = event.get_sender_id()
        
        if not args or args.strip() == "":
            yield event.plain_result(
                f"请指定要丢弃的物品\n"
                f"用法：丢弃 物品名 [数量]\n"
                f"示例：丢弃 精铁 5\n"
                f"⚠️ 丢弃的物品将永久销毁！"
            )
            return
        
        args = args.strip()
        parts = args.rsplit(" ", 1)
        
        # 解析物品名和数量
        if len(parts) == 2 and parts[1].isdigit():
            item_name = parts[0]
            count = int(parts[1])
        else:
            item_name = args
            count = 1
        
        if count <= 0:
            yield event.plain_result("数量必须大于0")
            return
        
        # 丢弃物品
        success, message = self.storage_ring_service.discard_item(user_id, item_name, count)
        
        if success:
            yield event.plain_result(f"🗑️ {message}")
        else:
            yield event.plain_result(f"❌ {message}")
    
    @require_player
    async def handle_gift_item(self, event: AstrMessageEvent, player, args: str = ""):
        """赠予物品给其他玩家"""
        user_id = event.get_sender_id()
        sender_name = event.get_sender_name()
        
        target_id = None
        item_name = None
        count = 1
        
        # 从消息链中提取 At 组件和 Plain 文本
        text_parts = []
        at_target = None
        message_chain = event.message_obj.message if hasattr(event, 'message_obj') and event.message_obj else []
        
        # 第一步：提取 At 目标和纯文本
        for comp in message_chain:
            if isinstance(comp, At):
                # 提取 At 目标
                for attr in ("qq", "target", "uin", "user_id"):
                    candidate = getattr(comp, attr, None)
                    if candidate:
                        at_target = str(candidate).lstrip("@")
                        break
            elif isinstance(comp, Plain):
                text_parts.append(comp.text)
        
        # 合并纯文本
        full_text = "".join(text_parts).strip()
        
        # 第二步：从文本中提取"赠予"后面的内容
        after_command = ""
        if "赠予" in full_text:
            # 找到"赠予"的位置，取后面的内容
            idx = full_text.find("赠予")
            after_command = full_text[idx + 2:].strip()
        else:
            # 如果没有"赠予"，可能整个文本就是内容（兼容旧格式）
            after_command = full_text
        
        # 第三步：如果通过 At 组件没有获取到 target_id，尝试从 after_command 解析
        if not at_target and after_command:
            # 尝试解析 @QQ号 或 纯QQ号
            import re
            # 匹配 @数字 或 纯数字（5位以上）
            at_match = re.search(r'@?(\d{5,})', after_command)
            if at_match:
                at_target = at_match.group(1)
                # 从 after_command 中移除 QQ号 部分
                after_command = re.sub(r'@?\d{5,}\s*', '', after_command).strip()
        
        # 第四步：从 after_command 中解析物品名和数量
        if after_command:
            # 尝试解析 "物品名 数量" 格式
            parts = after_command.rsplit(" ", 1)
            if len(parts) == 2 and parts[1].isdigit():
                item_name = parts[0].strip()
                count = int(parts[1])
            else:
                # 尝试解析 "物品名×数量" 格式
                import re
                mul_match = re.match(r'(.+?)\s*[×xX*]\s*(\d+)', after_command)
                if mul_match:
                    item_name = mul_match.group(1).strip()
                    count = int(mul_match.group(2))
                else:
                    item_name = after_command.strip()
                    count = 1
        
        # 第五步：验证必要参数
        if not at_target:
            yield event.plain_result(
                f"❌ 请指定赠予对象\n"
                f"用法：赠予 @某人 物品名 [数量]\n"
                f"或：赠予 QQ号 物品名 [数量]\n"
                f"示例：赠予 @张三 固基丹 5\n"
                f"示例：赠予 123456789 精铁 3"
            )
            return
        
        if not item_name:
            yield event.plain_result(
                f"❌ 请指定要赠予的物品名称\n"
                f"用法：赠予 @某人 物品名 [数量]\n"
                f"示例：赠予 @张三 固基丹 5"
            )
            return
        
        if count <= 0:
            yield event.plain_result("❌ 数量必须大于0")
            return
        
        # 第六步：检查是否赠予给自己
        if at_target == user_id:
            yield event.plain_result("❌ 不能赠予物品给自己")
            return
        
        # 第七步：执行赠予
        success, message = self.storage_ring_service.gift_item(
            sender_id=user_id,
            sender_name=sender_name,
            receiver_id=at_target,
            item_name=item_name,
            count=count
        )
        
        if success:
            yield event.plain_result(message)
        else:
            yield event.plain_result(f"❌ {message}")    

    @require_player
    async def handle_upgrade_ring(self, event: AstrMessageEvent, player):
        """升级储物戒（自动升级到下一级）"""
        user_id = event.get_sender_id()
        
        # 直接升级到下一级
        success, message = self.storage_ring_service.upgrade_ring(user_id)
        
        if success:
            yield event.plain_result(message)
        else:
            yield event.plain_result(f"❌ {message}")
    
    @require_player
    async def handle_search_item(self, event: AstrMessageEvent, player, keyword: str = ""):
        """搜索储物戒中的物品"""
        user_id = event.get_sender_id()
        
        if not keyword or keyword.strip() == "":
            yield event.plain_result(
                f"请指定搜索关键词\n"
                f"用法：搜索物品 关键词\n"
                f"示例：搜索物品 灵草"
            )
            return
        
        keyword = keyword.strip().lower()
        items = self.storage_ring_service.storage_ring_repo.get_storage_ring_items(user_id)
        
        # 模糊搜索
        matched = []
        for item_name, count in items.items():
            if keyword in item_name.lower():
                matched.append((item_name, count))
        
        if not matched:
            yield event.plain_result(f"未找到包含「{keyword}」的物品")
            return
        
        lines = [f"=== 搜索结果：{keyword} ===\n"]
        for item_name, count in matched:
            # 获取参考价格
            ref_price = self.storage_ring_service.get_reference_price(item_name)
            if ref_price:
                lines.append(f"  · {item_name}×{count} (参考价:{ref_price})\n")
            else:
                lines.append(f"  · {item_name}×{count}\n")
        lines.append(f"\n共找到 {len(matched)} 种物品")
        
        yield event.plain_result("".join(lines))
    
    @require_player
    async def handle_view_item(self, event: AstrMessageEvent, player, item_name: str = ""):
        """查看物品百科，无需玩家持有该物品。"""
        user_id = event.get_sender_id()
        
        if not item_name or item_name.strip() == "":
            yield event.plain_result(
                "请指定要查看的物品名称\n"
                "用法：小豆查看物品 <物品名>\n"
                "示例：小豆查看物品 筑基丹"
            )
            return
        
        item_name = item_name.strip()
        
        # 持有数量仅用于附加显示，不再作为查询条件
        items = self.storage_ring_service.storage_ring_repo.get_storage_ring_items(user_id)
        count = items.get(item_name, 0)
        
        # 获取物品详细信息
        item_info = self.storage_ring_service.get_item_details(item_name)
        
        if not item_info:
            matches = self.storage_ring_service.search_item_catalog(item_name)
            if matches:
                lines = [
                    f"🔍 未找到完全匹配的【{item_name}】\n",
                    "你可能想查：\n",
                ]
                for match in matches:
                    rank = f"·{match['rank']}" if match.get('rank') else ""
                    lines.append(
                        f"  · {match['name']}"
                        f"（{match.get('type', '其他')}{rank}）\n"
                    )
                lines.append("\n请使用：小豆查看物品 <完整名称>")
                yield event.plain_result("".join(lines))
            else:
                yield event.plain_result(
                    f"❌ 物品百科中未找到【{item_name}】\n"
                    f"💡 请检查名称，或输入关键词获取候选项"
                )
            return
        
        # 格式化百科显示
        lines = [
            f"📖 物品百科·{item_info['name']}\n",
            "━━━━━━━\n",
        ]

        # 专属道具的百科字段使用马赛克展示，
        # 不修改 items.json 中的任何实际数据。
        is_mianmian_relic = (
            str(item_info.get('id')) == "999999"
            or item_info.get('name') == "面面舍利子"
        )

        if is_mianmian_relic:
            lines.append("ID：██████\n")
        elif item_info.get('id'):
            lines.append(f"ID：{item_info['id']}\n")
        
        if is_mianmian_relic:
            lines.append("品级：██\n")
        elif item_info.get('rank'):
            lines.append(f"品级：{item_info['rank']}\n")
        
        if is_mianmian_relic:
            lines.append("类型：██ / ██\n")
        elif item_info.get('type'):
            type_text = str(item_info['type'])
            if item_info.get('subtype'):
                type_text += f" / {item_info['subtype']}"
            lines.append(f"类型：{type_text}\n")
        
        if is_mianmian_relic:
            lines.append("参考价：████████\n")
        elif item_info.get('price') is not None:
            price = item_info['price']
            price_text = f"{price:,}" if isinstance(price, int) else str(price)
            lines.append(f"参考价：{price_text}灵石\n")

        if item_info.get("weapon_category"):
            lines.append(f"武器类别：{item_info['weapon_category']}\n")

        level_data = self.storage_ring_service.config_manager.get_level_data(
            player.cultivation_type.value
        )
        required_level = item_info.get('required_level_index')
        if is_mianmian_relic:
            lines.append("需求境界：████████\n")
        elif required_level is not None:
            if 0 <= required_level < len(level_data):
                required_name = level_data[required_level].get(
                    'name', f"境界索引{required_level}"
                )
                lines.append(f"需求境界：{required_name}\n")
            else:
                lines.append(f"需求境界：索引 {required_level}\n")

        target_level = item_info.get('target_level_index')
        if target_level is not None and 0 <= target_level < len(level_data):
            target_name = level_data[target_level].get(
                'name', f"境界索引{target_level}"
            )
            lines.append(f"适用突破：{target_name}\n")

        lines.append(f"当前持有：{count}\n")
        
        lines.append("━━━━━━━━━━━━━━━\n")
        
        # 显示效果
        if item_info.get('data'):
            effects = self.storage_ring_service.format_item_effects(item_info['data'])
            lines.append(f"效果：{effects}\n")
        else:
            lines.append("效果：无\n")
        
        # 显示介绍
        if item_info.get('description'):
            lines.append(f"介绍：{item_info['description']}\n")
        
        yield event.plain_result("".join(lines))
