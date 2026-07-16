"""数据库迁移工具"""
import sqlite3
from pathlib import Path
from typing import Optional


class MigrationManager:
    """数据库迁移管理器"""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
    
    def apply_migrations(self):
        """应用所有待执行的迁移"""
        if not self.db_path.exists():
            # 新数据库，不需要迁移
            return
        
        conn = sqlite3.connect(str(self.db_path))
        try:
            # 检查并添加 cultivation_start_time 字段
            self._add_cultivation_start_time_if_missing(conn)
            conn.commit()
        finally:
            conn.close()
    
    def _add_cultivation_start_time_if_missing(self, conn: sqlite3.Connection):
        """添加 cultivation_start_time 字段（如果不存在）"""
        cursor = conn.cursor()
        
        # 检查字段是否存在
        cursor.execute("PRAGMA table_info(players)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'cultivation_start_time' not in columns:
            print("添加 cultivation_start_time 字段...")
            cursor.execute("""
                ALTER TABLE players 
                ADD COLUMN cultivation_start_time INTEGER NOT NULL DEFAULT 0
            """)
            print("✓ cultivation_start_time 字段已添加")
