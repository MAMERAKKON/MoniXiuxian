"""领域工厂"""
import random
from typing import Optional

from .models.player import Player
from .enums import CultivationType, PlayerState
from .value_objects import SpiritRootInfo


class PlayerFactory:
    """玩家工厂 - 负责创建玩家实例"""
    
    @staticmethod
    def create_new_player(
        user_id: str,
        cultivation_type: CultivationType,
        spirit_root: SpiritRootInfo,
        initial_gold: int = 100,
        user_name: Optional[str] = None
    ) -> Player:
        """
        创建新玩家
        
        Args:
            user_id: 用户ID
            cultivation_type: 修炼类型
            spirit_root: 灵根信息
            initial_gold: 初始灵石
            user_name: 用户名（QQ昵称），如果提供则使用，否则使用默认格式
            
        Returns:
            玩家实例
            
        Raises:
            ValueError: 如果修炼类型无效
        """
        # 校验修炼类型
        if cultivation_type not in [CultivationType.SPIRITUAL, CultivationType.PHYSICAL]:
            raise ValueError(f"无效的修炼类型: {cultivation_type}")
        
        # 生成灵根显示名称
        root_display_name = spirit_root.get_display_name()
        
        # 确定昵称：优先使用提供的用户名，否则使用默认格式
        nickname = user_name if user_name else f"道友{user_id[:6]}"
        
        if cultivation_type == CultivationType.SPIRITUAL:
            # 灵修初始数据
            # 寿命：100
            # 灵气：100-1000
            # 法伤：5-100
            # 物伤：5
            # 法防：0
            # 物防：5
            # 精神力：100-500
            spiritual_qi = random.randint(100, 1000)
            
            return Player(
                user_id=user_id,
                nickname=nickname,
                cultivation_type=cultivation_type,
                spiritual_root=root_display_name,
                level_index=0,
                experience=0,
                gold=initial_gold,
                state=PlayerState.IDLE,
                
                # 灵修属性
                spiritual_qi=spiritual_qi,
                max_spiritual_qi=spiritual_qi,
                blood_qi=0,
                max_blood_qi=0,
                
                # 通用属性
                lifespan=100,
                mental_power=random.randint(100, 500),
                
                # 战斗属性
                magic_damage=random.randint(5, 100),
                physical_damage=5,
                magic_defense=0,
                physical_defense=5,
                
                # 炼丹职业
                alchemy_level=0,
                alchemy_exp=0
            )
        else:  # 体修
            # 体修初始数据
            # 寿命：50-100
            # 气血：100-500
            # 法伤：0
            # 物伤：100-500
            # 法防：38-150（削弱25%）
            # 物防：100-500
            # 精神力：100-500
            blood_qi = random.randint(100, 500)
            
            return Player(
                user_id=user_id,
                nickname=nickname,
                cultivation_type=cultivation_type,
                spiritual_root=root_display_name,
                level_index=0,
                experience=0,
                gold=initial_gold,
                state=PlayerState.IDLE,
                
                # 体修属性
                spiritual_qi=0,
                max_spiritual_qi=0,
                blood_qi=blood_qi,
                max_blood_qi=blood_qi,
                
                # 通用属性
                lifespan=random.randint(50, 100),
                mental_power=random.randint(100, 500),
                
                # 战斗属性
                magic_damage=0,
                physical_damage=random.randint(100, 500),
                magic_defense=random.randint(38, 150),  # 削弱25%：原50-200
                physical_defense=random.randint(100, 500),
                
                # 炼丹职业
                alchemy_level=0,
                alchemy_exp=0
            )
