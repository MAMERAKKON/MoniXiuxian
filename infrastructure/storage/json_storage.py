"""
JSON 文件存储管理器

本模块提供基于 JSON 文件的数据存储解决方案，用于替代 SQLite 数据库。
主要特性：
- 每个实体类型使用独立的 JSON 文件
- 支持并发安全的文件读写（使用文件锁）
- 提供内存缓存以提高查询性能
- 支持原子写入和自动备份恢复
- 统一的时间戳格式（ISO 8601）

使用示例：
    >>> from pathlib import Path
    >>> from infrastructure.storage.json_storage import JSONStorage
    >>> 
    >>> # 创建存储实例
    >>> storage = JSONStorage(
    ...     data_dir=Path("data/json"),
    ...     enable_cache=True,
    ...     lock_timeout=30,
    ...     max_backups=3
    ... )
    >>> 
    >>> # 保存数据
    >>> data = {
    ...     "user_001": {"name": "张三", "level": 10},
    ...     "user_002": {"name": "李四", "level": 20}
    ... }
    >>> storage.save("players.json", data)
    >>> 
    >>> # 读取数据
    >>> loaded_data = storage.load("players.json")
    >>> 
    >>> # 获取单个实体
    >>> user = storage.get("players.json", "user_001")
    >>> 
    >>> # 设置单个实体
    >>> storage.set("players.json", "user_003", {"name": "王五", "level": 15})
    >>> 
    >>> # 查询数据
    >>> top_players = storage.query(
    ...     "players.json",
    ...     sort_key=lambda x: x["level"],
    ...     reverse=True,
    ...     limit=10
    ... )

注意事项：
- 所有时间戳字段应使用 TimestampConverter 进行转换
- 实体 ID 必须是非空字符串
- 实体数据必须是非空字典
- 文件操作会自动创建备份（最多保留 max_backups 个）
- 并发写入时会自动使用文件锁保护数据完整性
"""
import json
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List
from filelock import FileLock, Timeout

from astrbot.api import logger

from ...core.exceptions import (
    StorageException,
    FileReadException,
    FileWriteException,
    FileLockException,
    DataValidationException
)


class JSONStorage:
    """
    JSON 文件存储管理器
    
    提供线程安全的 JSON 文件存储功能，支持缓存、备份和原子写入。
    
    Attributes:
        data_dir (Path): JSON 文件存储目录
        enable_cache (bool): 是否启用内存缓存
        lock_timeout (int): 文件锁超时时间（秒）
        max_backups (int): 最大备份文件数量
    
    Examples:
        >>> storage = JSONStorage(Path("data/json"))
        >>> storage.set("users.json", "user_001", {"name": "测试用户"})
        >>> user = storage.get("users.json", "user_001")
        >>> print(user["name"])
        测试用户
    """
    
    def __init__(self, data_dir: Path, enable_cache: bool = True, lock_timeout: int = 30, max_backups: int = 3):
        """
        初始化 JSON 存储
        
        Args:
            data_dir: JSON 文件存储目录
            enable_cache: 是否启用内存缓存
            lock_timeout: 文件锁超时时间（秒）
            max_backups: 最大备份文件数量
        """
        self.data_dir = Path(data_dir)
        self.enable_cache = enable_cache
        self.lock_timeout = lock_timeout
        self.max_backups = max_backups
        
        # 内存缓存：{filename: {entity_id: entity_data}}
        self._cache: Dict[str, Dict[str, Any]] = {}
        
        # 文件锁：{filename: FileLock}
        self._file_locks: Dict[str, FileLock] = {}
        
        # 确保数据目录存在
        self._ensure_data_dir()
    
    def _ensure_data_dir(self) -> None:
        """确保数据目录存在"""
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"【JSONStorage】数据目录已确保存在: {self.data_dir}")
        except Exception as e:
            error_msg = f"创建数据目录失败: {self.data_dir}, 错误: {e}"
            logger.error(f"【JSONStorage】{error_msg}")
            raise StorageException(error_msg)
    
    def _get_lock(self, filename: str) -> FileLock:
        """
        获取文件锁对象
        
        Args:
            filename: JSON 文件名
            
        Returns:
            文件锁对象
        """
        if filename not in self._file_locks:
            lock_path = self.data_dir / f"{filename}.lock"
            self._file_locks[filename] = FileLock(lock_path, timeout=self.lock_timeout)
        return self._file_locks[filename]
    
    def _get_filepath(self, filename: str) -> Path:
        """
        获取文件完整路径
        
        Args:
            filename: JSON 文件名
            
        Returns:
            文件完整路径
        """
        return self.data_dir / filename
    
    def _atomic_write(self, filepath: Path, data: Dict[str, Any]) -> None:
        """
        原子写入 JSON 文件
        
        1. 写入临时文件
        2. 创建备份文件
        3. 重命名临时文件为目标文件
        
        Args:
            filepath: 目标文件路径
            data: 要写入的数据
            
        Raises:
            FileWriteException: 写入失败
        """
        temp_path = filepath.with_suffix('.tmp')
        backup_path = filepath.with_suffix('.bak')
        
        logger.debug(f"【JSONStorage】开始原子写入: {filepath}")
        
        try:
            # 写入临时文件
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"【JSONStorage】临时文件写入成功: {temp_path}")
            
            # 如果目标文件存在，创建备份
            if filepath.exists():
                shutil.copy2(filepath, backup_path)
                logger.debug(f"【JSONStorage】备份文件已创建: {backup_path}")
                
                # 管理备份文件数量
                self._manage_backups(filepath)
            
            # 原子重命名
            temp_path.replace(filepath)
            logger.debug(f"【JSONStorage】原子写入完成: {filepath}")
            
        except Exception as e:
            # 清理临时文件
            if temp_path.exists():
                try:
                    temp_path.unlink()
                    logger.debug(f"【JSONStorage】已清理临时文件: {temp_path}")
                except:
                    pass
            error_msg = f"写入文件失败 (atomic_write 操作): {filepath}, 错误: {e}"
            logger.error(f"【JSONStorage】{error_msg}")
            raise FileWriteException(error_msg)
    
    def _manage_backups(self, filepath: Path) -> None:
        """
        管理备份文件数量，保留最近的 N 个备份
        
        Args:
            filepath: 原始文件路径
        """
        try:
            # 获取所有备份文件
            backup_pattern = f"{filepath.stem}.bak*"
            backup_files = sorted(
                self.data_dir.glob(backup_pattern),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            
            # 删除超出数量的备份
            for old_backup in backup_files[self.max_backups:]:
                try:
                    old_backup.unlink()
                except:
                    pass
        except Exception:
            # 备份管理失败不影响主流程
            pass
    
    def _try_restore_from_backup(self, filepath: Path) -> Optional[Dict[str, Any]]:
        """
        尝试从备份文件恢复数据
        
        Args:
            filepath: 原始文件路径
            
        Returns:
            恢复的数据，如果失败则返回 None
        """
        backup_path = filepath.with_suffix('.bak')
        
        if backup_path.exists():
            try:
                with open(backup_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        
        return None
    
    def load(self, filename: str) -> Dict[str, Any]:
        """
        加载 JSON 文件到内存
        
        Args:
            filename: JSON 文件名（例如：players.json）
            
        Returns:
            字典，键为实体 ID，值为实体数据
            
        Raises:
            FileReadException: 读取失败
        """
        logger.debug(f"【JSONStorage】开始加载文件: {filename}")
        filepath = self._get_filepath(filename)
        
        # 如果文件不存在，返回空字典
        if not filepath.exists():
            logger.debug(f"【JSONStorage】文件不存在，返回空字典: {filename}")
            return {}
        
        lock = self._get_lock(filename)
        
        try:
            with lock:
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # 验证数据格式
                    if not isinstance(data, dict):
                        error_msg = f"JSON 文件格式错误: {filename}, 期望字典类型"
                        logger.error(f"【JSONStorage】{error_msg}")
                        raise FileReadException(error_msg)
                    
                    # 更新缓存
                    if self.enable_cache:
                        self._cache[filename] = data.copy()
                    
                    logger.debug(f"【JSONStorage】成功加载文件: {filename}, 实体数量: {len(data)}")
                    return data
                    
                except json.JSONDecodeError as e:
                    # JSON 解析失败，尝试从备份恢复
                    logger.warning(f"【JSONStorage】JSON 解析失败: {filename}, 尝试从备份恢复")
                    backup_data = self._try_restore_from_backup(filepath)
                    if backup_data is not None:
                        # 恢复成功，更新缓存并返回
                        if self.enable_cache:
                            self._cache[filename] = backup_data.copy()
                        logger.info(f"【JSONStorage】成功从备份恢复: {filename}")
                        return backup_data
                    else:
                        error_msg = f"JSON 解析失败且无法从备份恢复: {filename}, 错误: {e}"
                        logger.error(f"【JSONStorage】{error_msg}")
                        raise FileReadException(error_msg)
                
        except Timeout:
            error_msg = f"获取文件锁超时 (load 操作): {filename}, 路径: {filepath}"
            logger.error(f"【JSONStorage】{error_msg}")
            raise FileLockException(error_msg)
        except (FileReadException, FileLockException):
            raise
        except Exception as e:
            error_msg = f"读取文件失败 (load 操作): {filename}, 路径: {filepath}, 错误: {e}"
            logger.error(f"【JSONStorage】{error_msg}")
            raise FileReadException(error_msg)
    
    def save(self, filename: str, data: Dict[str, Any]) -> None:
        """
        保存数据到 JSON 文件（原子写入）
        
        Args:
            filename: JSON 文件名
            data: 要保存的数据字典
            
        Raises:
            FileWriteException: 写入失败
        """
        logger.debug(f"【JSONStorage】开始保存文件: {filename}, 实体数量: {len(data)}")
        filepath = self._get_filepath(filename)
        lock = self._get_lock(filename)
        
        try:
            with lock:
                # 原子写入
                self._atomic_write(filepath, data)
                
                # 更新缓存
                if self.enable_cache:
                    self._cache[filename] = data.copy()
                
                logger.debug(f"【JSONStorage】成功保存文件: {filename}, 实体数量: {len(data)}")
                
        except Timeout:
            error_msg = f"获取文件锁超时 (save 操作): {filename}, 路径: {filepath}"
            logger.error(f"【JSONStorage】{error_msg}")
            raise FileLockException(error_msg)
        except (FileWriteException, FileLockException):
            raise
        except Exception as e:
            error_msg = f"保存文件失败 (save 操作): {filename}, 路径: {filepath}, 错误: {e}"
            logger.error(f"【JSONStorage】{error_msg}")
            raise FileWriteException(error_msg)
    
    def get(self, filename: str, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        获取单个实体数据
        
        Args:
            filename: JSON 文件名
            entity_id: 实体 ID
            
        Returns:
            实体数据字典，不存在则返回 None
        """
        logger.debug(f"【JSONStorage】获取实体: {filename}, ID: {entity_id}")
        
        # 优先从缓存读取
        if self.enable_cache and filename in self._cache:
            result = self._cache[filename].get(entity_id)
            logger.debug(f"【JSONStorage】从缓存获取实体: {filename}, ID: {entity_id}, 存在: {result is not None}")
            return result
        
        # 从文件加载
        data = self.load(filename)
        result = data.get(entity_id)
        logger.debug(f"【JSONStorage】从文件获取实体: {filename}, ID: {entity_id}, 存在: {result is not None}")
        return result
    
    def set(self, filename: str, entity_id: str, entity_data: Dict[str, Any]) -> None:
        """
        设置单个实体数据
        
        Args:
            filename: JSON 文件名
            entity_id: 实体 ID
            entity_data: 实体数据
            
        Raises:
            DataValidationException: 数据验证失败
        """
        logger.debug(f"【JSONStorage】开始设置实体: {filename}, ID: {entity_id}")
        
        # 验证数据
        self._validate_entity(entity_id, entity_data)
        
        # 加载现有数据
        data = self.load(filename) if not (self.enable_cache and filename in self._cache) else self._cache[filename].copy()
        
        # 更新实体
        data[entity_id] = entity_data
        
        logger.debug(f"【JSONStorage】设置实体: {filename}, ID: {entity_id}")
        
        # 保存
        self.save(filename, data)
    
    def delete(self, filename: str, entity_id: str) -> None:
        """
        删除单个实体
        
        Args:
            filename: JSON 文件名
            entity_id: 实体 ID
        """
        logger.debug(f"【JSONStorage】开始删除实体: {filename}, ID: {entity_id}")
        
        # 加载现有数据
        data = self.load(filename) if not (self.enable_cache and filename in self._cache) else self._cache[filename].copy()
        
        # 删除实体
        if entity_id in data:
            del data[entity_id]
            
            logger.debug(f"【JSONStorage】删除实体: {filename}, ID: {entity_id}")
            
            # 保存
            self.save(filename, data)
        else:
            logger.debug(f"【JSONStorage】实体不存在，跳过删除: {filename}, ID: {entity_id}")
    
    def exists(self, filename: str, entity_id: str) -> bool:
        """
        检查实体是否存在
        
        Args:
            filename: JSON 文件名
            entity_id: 实体 ID
            
        Returns:
            是否存在
        """
        logger.debug(f"【JSONStorage】检查实体是否存在: {filename}, ID: {entity_id}")
        
        # 优先从缓存检查
        if self.enable_cache and filename in self._cache:
            exists = entity_id in self._cache[filename]
            logger.debug(f"【JSONStorage】从缓存检查实体: {filename}, ID: {entity_id}, 存在: {exists}")
            return exists
        
        # 从文件加载
        data = self.load(filename)
        exists = entity_id in data
        logger.debug(f"【JSONStorage】从文件检查实体: {filename}, ID: {entity_id}, 存在: {exists}")
        return exists
    
    def query(
        self, 
        filename: str, 
        filter_fn: Optional[Callable[[Dict[str, Any]], bool]] = None,
        sort_key: Optional[Callable[[Dict[str, Any]], Any]] = None,
        reverse: bool = False,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        查询实体列表
        
        Args:
            filename: JSON 文件名
            filter_fn: 过滤函数，接收实体数据，返回是否保留
            sort_key: 排序键函数，接收实体数据，返回排序键
            reverse: 是否倒序
            limit: 限制返回数量
            
        Returns:
            实体数据列表
        """
        logger.debug(f"【JSONStorage】开始查询: {filename}, 过滤: {filter_fn is not None}, 排序: {sort_key is not None}, 倒序: {reverse}, 限制: {limit}")
        
        # 加载数据
        data = self.load(filename) if not (self.enable_cache and filename in self._cache) else self._cache[filename]
        
        # 转换为列表
        results = list(data.values())
        
        # 过滤
        if filter_fn:
            results = [item for item in results if filter_fn(item)]
            logger.debug(f"【JSONStorage】过滤后数量: {len(results)}")
        
        # 排序
        if sort_key:
            results.sort(key=sort_key, reverse=reverse)
            logger.debug(f"【JSONStorage】排序完成")
        
        # 限制数量
        if limit is not None and limit > 0:
            results = results[:limit]
            logger.debug(f"【JSONStorage】限制后数量: {len(results)}")
        
        logger.debug(f"【JSONStorage】查询完成: {filename}, 返回数量: {len(results)}")
        return results
    
    def reload_cache(self, filename: str) -> None:
        """
        重新加载缓存
        
        Args:
            filename: JSON 文件名
        """
        logger.debug(f"【JSONStorage】重新加载缓存: {filename}")
        
        if self.enable_cache:
            # 清除旧缓存
            if filename in self._cache:
                del self._cache[filename]
                logger.debug(f"【JSONStorage】已清除旧缓存: {filename}")
            
            # 重新加载
            self.load(filename)
            logger.debug(f"【JSONStorage】缓存重新加载完成: {filename}")
    
    def _validate_entity(self, entity_id: str, entity_data: Dict[str, Any]) -> None:
        """
        验证实体数据
        
        Args:
            entity_id: 实体 ID
            entity_data: 实体数据
            
        Raises:
            DataValidationException: 验证失败
        """
        logger.debug(f"【JSONStorage】验证实体数据: ID: {entity_id}")
        
        # 验证 ID 不为空
        if not entity_id or not isinstance(entity_id, str):
            error_msg = f"实体 ID 无效 (validate 操作): {entity_id}"
            logger.error(f"【JSONStorage】{error_msg}")
            raise DataValidationException(error_msg)
        
        # 验证数据是字典
        if not isinstance(entity_data, dict):
            error_msg = f"实体数据必须是字典类型 (validate 操作): ID: {entity_id}, 类型: {type(entity_data)}"
            logger.error(f"【JSONStorage】{error_msg}")
            raise DataValidationException(error_msg)
        
        # 验证数据不为空
        if not entity_data:
            error_msg = f"实体数据不能为空 (validate 操作): ID: {entity_id}"
            logger.error(f"【JSONStorage】{error_msg}")
            raise DataValidationException(error_msg)
        
        logger.debug(f"【JSONStorage】实体数据验证通过: ID: {entity_id}")
