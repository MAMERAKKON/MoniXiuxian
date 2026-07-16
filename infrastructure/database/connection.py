"""数据库连接管理"""
from pathlib import Path
from typing import Optional
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session

from ...core.exceptions import DatabaseException


class DatabaseConnection:
    """数据库连接管理器"""
    
    def __init__(self, db_path: str, echo: bool = False):
        """
        初始化数据库连接
        
        Args:
            db_path: 数据库文件路径
            echo: 是否打印 SQL 语句
        """
        self.db_path = Path(db_path)
        self.echo = echo
        
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None
    
    @property
    def engine(self) -> Engine:
        """获取数据库引擎"""
        if self._engine is None:
            self._create_engine()
        return self._engine
    
    @property
    def session_factory(self) -> sessionmaker:
        """获取会话工厂"""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.engine,
                expire_on_commit=False
            )
        return self._session_factory
    
    def _create_engine(self):
        """创建数据库引擎"""
        try:
            # 确保数据库目录存在
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 创建引擎
            db_url = f"sqlite:///{self.db_path}"
            self._engine = create_engine(
                db_url,
                echo=self.echo,
                pool_pre_ping=True,  # 连接池预检查
                connect_args={
                    "check_same_thread": False,  # SQLite 多线程支持
                    "timeout": 30  # 30秒超时，避免长时间锁定
                }
            )
            
            # 启用 SQLite 外键约束
            @event.listens_for(Engine, "connect")
            def set_sqlite_pragma(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
            
        except Exception as e:
            raise DatabaseException(f"创建数据库引擎失败: {e}")
    
    def create_session(self) -> Session:
        """创建新的数据库会话"""
        return self.session_factory()
    
    def initialize(self):
        """初始化数据库（创建表）"""
        from .schema import Base
        try:
            Base.metadata.create_all(self.engine)
        except Exception as e:
            raise DatabaseException(f"初始化数据库失败: {e}")
    
    def close(self):
        """关闭数据库连接"""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None
