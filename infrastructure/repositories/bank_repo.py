"""银行仓储"""
from typing import Optional, List, Dict, Any

from .base import BaseRepository
from ..storage import JSONStorage, TimestampConverter
from ...domain.models.bank import BankAccount, Loan


class BankRepository(BaseRepository[BankAccount]):
    """银行仓储"""
    
    def __init__(self, storage: JSONStorage):
        """
        初始化银行仓储
        
        Args:
            storage: JSON存储管理器
        """
        super().__init__(storage, "bank_accounts.json")
        self.loans_filename = "loans.json"
    
    def get_by_id(self, user_id: str) -> Optional[BankAccount]:
        """根据用户ID获取银行账户"""
        return self.get_bank_account(user_id)
    
    def save(self, entity: BankAccount) -> None:
        """保存银行账户"""
        account_dict = self._to_dict(entity)
        self.storage.set(self.filename, entity.user_id, account_dict)
    
    def delete(self, user_id: str) -> None:
        """删除银行账户"""
        self.storage.delete(self.filename, user_id)
    
    def exists(self, user_id: str) -> bool:
        """检查银行账户是否存在"""
        return self.storage.exists(self.filename, user_id)
    
    # ===== 银行账户相关 =====
    
    def get_bank_account(self, user_id: str) -> Optional[BankAccount]:
        """获取银行账户"""
        data = self.storage.get(self.filename, user_id)
        
        if not data:
            return None
        
        return BankAccount(
            user_id=data["user_id"],
            balance=data["balance"],
            last_interest_time=TimestampConverter.from_iso8601(data["last_interest_time"])
        )
    
    def create_or_update_bank_account(self, user_id: str, balance: int, last_interest_time: int):
        """创建或更新银行账户"""
        account_data = {
            "user_id": user_id,
            "balance": balance,
            "last_interest_time": TimestampConverter.to_iso8601(last_interest_time)
        }
        self.storage.set(self.filename, user_id, account_data)
    
    # ===== 贷款相关 =====
    
    def get_active_loan(self, user_id: str) -> Optional[Loan]:
        """获取进行中的贷款"""
        results = self.storage.query(
            self.loans_filename,
            filter_fn=lambda data: data.get("user_id") == user_id and data.get("status") == 1
        )
        
        if not results:
            return None
        
        return self._loan_to_domain(results[0])
    
    def create_loan(self, user_id: str, principal: int, interest_rate: float,
                    borrowed_at: int, due_at: int, loan_type: str) -> int:
        """创建贷款"""
        # 生成新的贷款ID
        all_loans = self.storage.load(self.loans_filename)
        if all_loans:
            max_id = max(int(lid) for lid in all_loans.keys())
            new_id = max_id + 1
        else:
            new_id = 1
        
        loan_data = {
            "id": new_id,
            "user_id": user_id,
            "principal": principal,
            "interest_rate": interest_rate,
            "borrowed_at": TimestampConverter.to_iso8601(borrowed_at),
            "due_at": TimestampConverter.to_iso8601(due_at),
            "loan_type": loan_type,
            "status": 1
        }
        
        self.storage.set(self.loans_filename, str(new_id), loan_data)
        return new_id
    
    def close_loan(self, loan_id: int):
        """关闭贷款（还清）"""
        data = self.storage.get(self.loans_filename, str(loan_id))
        if data:
            data["status"] = 2
            self.storage.set(self.loans_filename, str(loan_id), data)
    
    def mark_loan_overdue(self, loan_id: int):
        """标记贷款逾期"""
        data = self.storage.get(self.loans_filename, str(loan_id))
        if data:
            data["status"] = 3
            self.storage.set(self.loans_filename, str(loan_id), data)
    
    def get_overdue_loans(self, current_time: int) -> List[Loan]:
        """获取所有逾期贷款"""
        current_time_iso = TimestampConverter.to_iso8601(current_time)
        
        results = self.storage.query(
            self.loans_filename,
            filter_fn=lambda data: (
                data.get("status") == 1 and 
                data.get("due_at") and 
                data.get("due_at") < current_time_iso
            )
        )
        
        return [self._loan_to_domain(data) for data in results]
    
    # ===== 排行榜相关 =====
    
    def get_deposit_ranking(self, limit: int = 10) -> List[dict]:
        """获取存款排行榜"""
        results = self.storage.query(
            self.filename,
            sort_key=lambda data: data.get("balance", 0),
            reverse=True,
            limit=limit
        )
        
        return [
            {
                "user_id": data["user_id"],
                "balance": data["balance"]
            }
            for data in results
        ]
    
    # ===== 辅助方法 =====
    
    def _to_domain(self, data: Dict[str, Any]) -> BankAccount:
        """转换为领域模型"""
        return BankAccount(
            user_id=data["user_id"],
            balance=data["balance"],
            last_interest_time=TimestampConverter.from_iso8601(data["last_interest_time"])
        )
    
    def _to_dict(self, account: BankAccount) -> Dict[str, Any]:
        """转换为字典数据"""
        return {
            "user_id": account.user_id,
            "balance": account.balance,
            "last_interest_time": TimestampConverter.to_iso8601(account.last_interest_time)
        }
    
    def _loan_to_domain(self, data: Dict[str, Any]) -> Loan:
        """转换为领域模型"""
        return Loan(
            id=data["id"],
            user_id=data["user_id"],
            principal=data["principal"],
            interest_rate=data["interest_rate"],
            borrowed_at=TimestampConverter.from_iso8601(data["borrowed_at"]),
            due_at=TimestampConverter.from_iso8601(data["due_at"]),
            loan_type=data["loan_type"],
            status=data["status"]
        )
