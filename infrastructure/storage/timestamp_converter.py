"""
时间戳转换工具

本模块提供 Unix 时间戳与 ISO 8601 格式字符串之间的转换功能。
用于在 JSON 存储中统一时间戳格式，提高可读性和互操作性。

主要特性：
- 支持 Unix 时间戳（整数秒）与 ISO 8601 字符串的双向转换
- 统一使用 UTC 时区，避免时区混淆
- 自动处理 None 值和边界情况
- 支持多种 ISO 8601 格式（'Z' 后缀和 '+00:00' 后缀）

使用示例：
    >>> from infrastructure.storage.timestamp_converter import TimestampConverter
    >>> import time
    >>> 
    >>> # 获取当前时间戳
    >>> current_time = int(time.time())
    >>> 
    >>> # 转换为 ISO 8601 字符串
    >>> iso_string = TimestampConverter.to_iso8601(current_time)
    >>> print(iso_string)
    2024-01-15T10:30:00Z
    >>> 
    >>> # 转换回 Unix 时间戳
    >>> timestamp = TimestampConverter.from_iso8601(iso_string)
    >>> print(timestamp == current_time)
    True
    >>> 
    >>> # 处理 None 值
    >>> TimestampConverter.to_iso8601(None)
    None
    >>> TimestampConverter.from_iso8601(None)
    None

在 Repository 中的使用：
    >>> # 保存时转换为 ISO 8601
    >>> data = {
    ...     "user_id": "user_001",
    ...     "created_at": TimestampConverter.to_iso8601(player.created_at),
    ...     "updated_at": TimestampConverter.to_iso8601(player.updated_at)
    ... }
    >>> storage.set("players.json", "user_001", data)
    >>> 
    >>> # 读取时转换回 Unix 时间戳
    >>> loaded_data = storage.get("players.json", "user_001")
    >>> created_at = TimestampConverter.from_iso8601(loaded_data["created_at"])
    >>> updated_at = TimestampConverter.from_iso8601(loaded_data["updated_at"])

注意事项：
- 所有时间戳都使用 UTC 时区
- 输入为 0 的时间戳会被视为 None
- ISO 8601 字符串格式：YYYY-MM-DDTHH:MM:SSZ
- 转换过程中可能会有 1 秒的精度损失（由于浮点数转整数）
"""
from datetime import datetime, timezone
from typing import Optional


class TimestampConverter:
    """时间戳转换工具
    
    提供 Unix 时间戳与 ISO 8601 格式字符串之间的转换功能。
    所有时间戳使用 UTC 时区。
    """
    
    @staticmethod
    def to_iso8601(timestamp: Optional[int]) -> Optional[str]:
        """
        将 Unix 时间戳转换为 ISO 8601 字符串
        
        Args:
            timestamp: Unix 时间戳（秒），可以为 None
            
        Returns:
            ISO 8601 格式字符串（例如：2024-01-15T10:30:00Z），
            如果输入为 None 或 0 则返回 None
            
        Examples:
            >>> TimestampConverter.to_iso8601(1705318200)
            '2024-01-15T10:30:00Z'
            >>> TimestampConverter.to_iso8601(None)
            None
            >>> TimestampConverter.to_iso8601(0)
            None
        """
        if timestamp is None or timestamp == 0:
            return None
        
        # 将 Unix 时间戳转换为 UTC datetime
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        
        # 转换为 ISO 8601 格式，使用 'Z' 表示 UTC
        return dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    @staticmethod
    def from_iso8601(iso_string: Optional[str]) -> Optional[int]:
        """
        将 ISO 8601 字符串转换为 Unix 时间戳
        
        Args:
            iso_string: ISO 8601 格式字符串，可以为 None
            
        Returns:
            Unix 时间戳（秒），如果输入为 None 则返回 None
            
        Examples:
            >>> TimestampConverter.from_iso8601('2024-01-15T10:30:00Z')
            1705318200
            >>> TimestampConverter.from_iso8601('2024-01-15T10:30:00+00:00')
            1705318200
            >>> TimestampConverter.from_iso8601(None)
            None
        """
        if iso_string is None:
            return None
        
        # 处理 'Z' 后缀（表示 UTC）
        if iso_string.endswith('Z'):
            iso_string = iso_string[:-1] + '+00:00'
        
        # 解析 ISO 8601 字符串
        dt = datetime.fromisoformat(iso_string)
        
        # 转换为 Unix 时间戳
        return int(dt.timestamp())
