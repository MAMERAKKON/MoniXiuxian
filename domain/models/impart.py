"""传承系统领域模型"""
from dataclasses import dataclass


@dataclass
class ImpartInfo:
    """传承信息"""
    user_id: str
    impart_hp_per: float = 0.0  # HP加成百分比
    impart_mp_per: float = 0.0  # MP加成百分比
    impart_atk_per: float = 0.0  # 攻击加成百分比
    impart_know_per: float = 0.0  # 会心加成百分比
    impart_burst_per: float = 0.0  # 爆伤加成百分比
    impart_mix_exp: int = 0  # 混合经验
    
    def get_total_bonus(self) -> float:
        """获取总加成"""
        return (self.impart_hp_per + self.impart_mp_per + 
                self.impart_atk_per + self.impart_know_per + 
                self.impart_burst_per)
