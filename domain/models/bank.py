"""银行领域模型"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class LoanStatus(Enum):
    """贷款状态枚举"""
    ACTIVE = 1  # 进行中
    REPAID = 2  # 已还清
    OVERDUE = 3  # 已逾期


class LoanType(Enum):
    """贷款类型枚举"""
    NORMAL = "normal"  # 普通贷款
    BREAKTHROUGH = "breakthrough"  # 突破贷款


@dataclass
class BankAccount:
    """银行账户"""
    user_id: str  # 用户ID
    balance: int  # 余额
    last_interest_time: int  # 上次计息时间
    
    def has_balance(self) -> bool:
        """检查是否有余额"""
        return self.balance > 0


@dataclass
class Loan:
    """贷款"""
    id: int  # 贷款ID
    user_id: str  # 用户ID
    principal: int  # 本金
    interest_rate: float  # 日利率
    borrowed_at: int  # 借款时间
    due_at: int  # 到期时间
    loan_type: str  # 贷款类型
    status: int  # 状态
    
    def is_active(self) -> bool:
        """检查贷款是否进行中"""
        return self.status == LoanStatus.ACTIVE.value
    
    def is_overdue(self, current_time: int) -> bool:
        """检查是否逾期"""
        return self.is_active() and current_time > self.due_at
    
    def calculate_interest(self, current_time: int) -> int:
        """计算利息"""
        if not self.is_active():
            return 0
        
        days_borrowed = max(1, (current_time - self.borrowed_at) // 86400)
        interest = int(self.principal * self.interest_rate * days_borrowed)
        return interest
    
    def calculate_total_due(self, current_time: int) -> int:
        """计算应还总额"""
        interest = self.calculate_interest(current_time)
        return self.principal + interest


@dataclass
class BankInfo:
    """银行信息（用于显示）"""
    balance: int  # 余额
    last_interest_time: int  # 上次计息时间
    pending_interest: int  # 待领利息
    loan: Optional[Loan]  # 当前贷款
    
    def has_loan(self) -> bool:
        """检查是否有贷款"""
        return self.loan is not None and self.loan.is_active()


@dataclass
class LoanInfo:
    """贷款详情（用于显示）"""
    id: int  # 贷款ID
    user_id: str  # 用户ID
    principal: int  # 本金
    interest_rate: float  # 日利率
    borrowed_at: int  # 借款时间
    due_at: int  # 到期时间
    loan_type: str  # 贷款类型
    status: int  # 状态
    days_borrowed: int  # 已借天数
    days_remaining: int  # 剩余天数
    current_interest: int  # 当前利息
    total_due: int  # 应还总额
    is_overdue: bool  # 是否逾期
