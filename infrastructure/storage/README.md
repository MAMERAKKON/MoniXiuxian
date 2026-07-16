# JSON 存储系统

## 概述

JSON 存储系统是修仙插件 V3 的数据持久化解决方案，用于替代 SQLite 数据库。它提供了简单、可靠、高性能的数据存储功能。

## 主要特性

### 1. 文件组织
- 每个实体类型使用独立的 JSON 文件
- 文件存储在 `data/json/` 目录下
- 文件格式：`{entity_type}.json`（例如：`players.json`、`sects.json`）

### 2. 数据结构
所有 JSON 文件使用统一的结构：
```json
{
  "entity_id_1": {
    "field1": "value1",
    "field2": "value2",
    ...
  },
  "entity_id_2": {
    ...
  }
}
```

### 3. 并发安全
- 使用文件锁（filelock）防止并发写入冲突
- 支持多线程安全访问
- 自动处理锁超时（默认 30 秒）

### 4. 数据保护
- 原子写入：先写临时文件，再重命名
- 自动备份：每次写入前创建 `.bak` 备份文件
- 备份恢复：JSON 解析失败时自动从备份恢复
- 备份管理：最多保留 3 个备份文件

### 5. 性能优化
- 内存缓存：减少文件 I/O 操作
- 增量更新：只更新变化的实体
- 查询优化：支持过滤、排序、限制

### 6. 时间戳标准化
- 统一使用 ISO 8601 格式存储时间戳
- 自动转换 Unix 时间戳 ↔ ISO 8601 字符串
- 所有时间戳使用 UTC 时区

## 使用指南

### 基本使用

#### 1. 创建存储实例

```python
from pathlib import Path
from infrastructure.storage.json_storage import JSONStorage

# 创建存储实例
storage = JSONStorage(
    data_dir=Path("data/json"),  # 数据目录
    enable_cache=True,            # 启用缓存
    lock_timeout=30,              # 锁超时（秒）
    max_backups=3                 # 最大备份数
)
```

#### 2. 保存数据

```python
# 保存整个文件
data = {
    "user_001": {"name": "张三", "level": 10},
    "user_002": {"name": "李四", "level": 20}
}
storage.save("players.json", data)

# 保存单个实体
storage.set("players.json", "user_003", {"name": "王五", "level": 15})
```

#### 3. 读取数据

```python
# 读取整个文件
all_players = storage.load("players.json")

# 读取单个实体
player = storage.get("players.json", "user_001")

# 检查实体是否存在
exists = storage.exists("players.json", "user_001")
```

#### 4. 删除数据

```python
# 删除单个实体
storage.delete("players.json", "user_001")
```

#### 5. 查询数据

```python
# 查询所有数据
all_players = storage.query("players.json")

# 过滤查询
high_level_players = storage.query(
    "players.json",
    filter_fn=lambda x: x["level"] > 15
)

# 排序查询
top_players = storage.query(
    "players.json",
    sort_key=lambda x: x["level"],
    reverse=True,
    limit=10
)

# 多字段排序
top_by_level_and_exp = storage.query(
    "players.json",
    sort_key=lambda x: (x["level"], x["experience"]),
    reverse=True
)
```

### 在 Repository 中使用

#### 1. 创建 Repository

```python
from infrastructure.storage.json_storage import JSONStorage
from infrastructure.storage.timestamp_converter import TimestampConverter
from infrastructure.repositories.base import BaseRepository

class PlayerRepository(BaseRepository[Player]):
    def __init__(self, storage: JSONStorage):
        super().__init__(storage, "players.json")
    
    def _to_domain(self, data: Dict[str, Any]) -> Player:
        """将字典转换为领域对象"""
        # 转换时间戳
        created_at = TimestampConverter.from_iso8601(data.get('created_at'))
        updated_at = TimestampConverter.from_iso8601(data.get('updated_at'))
        
        return Player(
            user_id=data['user_id'],
            nickname=data['nickname'],
            level=data['level'],
            created_at=created_at or 0,
            updated_at=updated_at or 0
        )
    
    def _to_dict(self, player: Player) -> Dict[str, Any]:
        """将领域对象转换为字典"""
        return {
            'user_id': player.user_id,
            'nickname': player.nickname,
            'level': player.level,
            'created_at': TimestampConverter.to_iso8601(player.created_at),
            'updated_at': TimestampConverter.to_iso8601(player.updated_at)
        }
```

#### 2. 使用 Repository

```python
# 创建 Repository
repo = PlayerRepository(storage)

# 保存玩家
player = Player(user_id="user_001", nickname="测试玩家", level=10)
repo.save(player)

# 读取玩家
loaded_player = repo.get_by_id("user_001")

# 更新玩家
loaded_player.level = 20
repo.save(loaded_player)

# 删除玩家
repo.delete("user_001")
```

### 时间戳处理

#### 1. 保存时转换

```python
from infrastructure.storage.timestamp_converter import TimestampConverter
import time

# 获取当前时间戳
current_time = int(time.time())

# 转换为 ISO 8601 字符串
iso_string = TimestampConverter.to_iso8601(current_time)

# 保存到 JSON
data = {
    "user_id": "user_001",
    "created_at": iso_string
}
storage.set("players.json", "user_001", data)
```

#### 2. 读取时转换

```python
# 从 JSON 读取
data = storage.get("players.json", "user_001")

# 转换回 Unix 时间戳
created_at = TimestampConverter.from_iso8601(data["created_at"])
```

## 配置选项

### 通过配置文件配置

在 `config.json` 中添加 JSON 存储配置：

```json
{
  "JSON_STORAGE": {
    "DATA_DIR": "data/json",
    "ENABLE_CACHE": true,
    "LOCK_TIMEOUT": 30,
    "MAX_BACKUPS": 3
  }
}
```

### 配置说明

| 配置项       | 类型    | 默认值      | 说明                 |
| ------------ | ------- | ----------- | -------------------- |
| DATA_DIR     | string  | "data/json" | JSON 文件存储目录    |
| ENABLE_CACHE | boolean | true        | 是否启用内存缓存     |
| LOCK_TIMEOUT | integer | 30          | 文件锁超时时间（秒） |
| MAX_BACKUPS  | integer | 3           | 最大备份文件数量     |

## 错误处理

### 异常类型

- `StorageException`: 存储层基础异常
- `FileReadException`: 文件读取失败
- `FileWriteException`: 文件写入失败
- `FileLockException`: 文件锁获取失败
- `DataValidationException`: 数据验证失败

### 错误处理示例

```python
from infrastructure.storage.json_storage import (
    JSONStorage,
    FileReadException,
    FileWriteException,
    FileLockException,
    DataValidationException
)

try:
    storage.set("players.json", "user_001", {"name": "测试"})
except DataValidationException as e:
    print(f"数据验证失败: {e}")
except FileWriteException as e:
    print(f"文件写入失败: {e}")
except FileLockException as e:
    print(f"文件锁获取失败: {e}")
except StorageException as e:
    print(f"存储错误: {e}")
```

## 最佳实践

### 1. 使用缓存

启用缓存可以显著提高查询性能：

```python
storage = JSONStorage(data_dir=Path("data/json"), enable_cache=True)
```

### 2. 合理设置锁超时

根据实际情况调整锁超时时间：
- 高并发场景：增加超时时间（如 60 秒）
- 低并发场景：使用默认值（30 秒）

### 3. 定期清理备份

虽然系统会自动管理备份文件，但建议定期检查备份目录：

```bash
# 查看备份文件
ls -la data/json/*.bak*
```

### 4. 监控日志

启用 DEBUG 日志级别以监控存储操作：

```python
import logging
logging.getLogger("infrastructure.storage").setLevel(logging.DEBUG)
```

### 5. 数据验证

在保存数据前进行验证：

```python
def validate_player_data(data):
    assert "user_id" in data, "缺少 user_id"
    assert "nickname" in data, "缺少 nickname"
    assert isinstance(data["level"], int), "level 必须是整数"

# 验证后保存
validate_player_data(player_data)
storage.set("players.json", player_data["user_id"], player_data)
```

## 性能考虑

### 1. 缓存策略

- 启用缓存后，读取操作直接从内存获取
- 写入操作会同时更新缓存和文件
- 适合读多写少的场景

### 2. 文件大小

- 单个 JSON 文件建议不超过 10MB
- 如果数据量过大，考虑分片存储

### 3. 并发性能

- 文件锁会影响并发写入性能
- 读取操作不受文件锁影响
- 适合中小规模并发场景

## 故障排查

### 问题：文件锁超时

**原因**：多个进程同时写入同一文件

**解决方案**：
1. 增加锁超时时间
2. 减少并发写入频率
3. 使用队列缓冲写入请求

### 问题：JSON 解析失败

**原因**：文件损坏或格式错误

**解决方案**：
1. 系统会自动尝试从备份恢复
2. 手动检查 `.bak` 备份文件
3. 如果备份也损坏，需要重建数据

### 问题：缓存不一致

**原因**：外部程序直接修改了 JSON 文件

**解决方案**：
```python
# 手动重新加载缓存
storage.reload_cache("players.json")
```

## 迁移指南

### 从 SQLite 迁移到 JSON

1. 导出 SQLite 数据
2. 转换为 JSON 格式
3. 使用 JSONStorage 导入数据

详细迁移步骤请参考 `MIGRATION.md`。

## 相关文档

- [设计文档](../../.kiro/specs/database-to-json-migration/design.md)
- [需求文档](../../.kiro/specs/database-to-json-migration/requirements.md)
- [任务列表](../../.kiro/specs/database-to-json-migration/tasks.md)

## 许可证

本项目采用 MIT 许可证。
