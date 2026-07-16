"""会话管理"""
from contextlib import contextmanager
from typing import Generator
from sqlalchemy.orm import Session

from .connection import DatabaseConnection


class SessionManager:
    """会话管理器"""
    
    def __init__(self, db_connection: DatabaseConnection):
        """
        初始化会话管理器
        
        Args:
            db_connection: 数据库连接
        """
        self.db_connection = db_connection
    
    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """
        提供事务性会话上下文
        
        使用示例:
            with session_manager.session_scope() as session:
                # 执行数据库操作
                session.add(obj)
                # 自动提交或回滚
        """
        session = self.db_connection.create_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_session(self) -> Session:
        """
        获取新会话（需要手动管理）
        
        Returns:
            数据库会话
        """
        return self.db_connection.create_session()
