"""自定义异常"""


class XiuxianException(Exception):
    """修仙插件基础异常"""
    def __init__(self, message: str = "发生错误"):
        self.message = message
        super().__init__(self.message)


# BusinessException 作为 XiuxianException 的别名，用于业务逻辑异常
class BusinessException(XiuxianException):
    """业务异常 - 用于一般业务逻辑错误"""
    pass


# GameException 作为 XiuxianException 的别名，用于游戏逻辑异常
class GameException(XiuxianException):
    """游戏异常 - 用于游戏逻辑错误"""
    pass


class PlayerNotFoundException(XiuxianException):
    """玩家不存在异常"""
    def __init__(self, user_id: str):
        super().__init__(f"玩家 {user_id} 不存在")
        self.user_id = user_id


class PlayerAlreadyExistsException(XiuxianException):
    """玩家已存在异常"""
    def __init__(self, user_id: str):
        super().__init__(f"玩家 {user_id} 已存在")
        self.user_id = user_id


class InvalidStateException(XiuxianException):
    """状态无效异常"""
    def __init__(self, current_state: str, required_state: str):
        super().__init__(f"当前状态 {current_state} 无法执行此操作，需要状态: {required_state}")
        self.current_state = current_state
        self.required_state = required_state


class InsufficientResourcesException(XiuxianException):
    """资源不足异常"""
    def __init__(self, resource_type: str, required: int, current: int):
        super().__init__(f"{resource_type}不足，需要 {required}，当前 {current}")
        self.resource_type = resource_type
        self.required = required
        self.current = current


class ItemNotFoundException(XiuxianException):
    """物品不存在异常"""
    def __init__(self, item_id: str):
        super().__init__(f"物品 {item_id} 不存在")
        self.item_id = item_id


class CooldownNotReadyException(XiuxianException):
    """冷却未就绪异常"""
    def __init__(self, action: str, remaining_seconds: int):
        super().__init__(f"{action} 冷却中，还需 {remaining_seconds} 秒")
        self.action = action
        self.remaining_seconds = remaining_seconds


class InvalidParameterException(XiuxianException):
    """参数无效异常"""
    def __init__(self, parameter: str, reason: str):
        super().__init__(f"参数 {parameter} 无效: {reason}")
        self.parameter = parameter
        self.reason = reason


class BreakthroughFailedException(XiuxianException):
    """突破失败异常"""
    def __init__(self, reason: str = "突破失败"):
        super().__init__(reason)


class SectNotFoundException(XiuxianException):
    """宗门不存在异常"""
    def __init__(self, sect_id: str):
        super().__init__(f"宗门 {sect_id} 不存在")
        self.sect_id = sect_id


class SectFullException(XiuxianException):
    """宗门已满异常"""
    def __init__(self, sect_name: str):
        super().__init__(f"宗门 {sect_name} 已满员")
        self.sect_name = sect_name


class AlreadyInSectException(XiuxianException):
    """已在宗门异常"""
    def __init__(self, sect_name: str):
        super().__init__(f"你已经在宗门 {sect_name} 中")
        self.sect_name = sect_name


class NotInSectException(XiuxianException):
    """不在宗门异常"""
    def __init__(self):
        super().__init__("你还未加入任何宗门")


class DatabaseException(XiuxianException):
    """数据库异常"""
    def __init__(self, message: str):
        super().__init__(f"数据库错误: {message}")


class ConfigurationException(XiuxianException):
    """配置异常"""
    def __init__(self, message: str):
        super().__init__(f"配置错误: {message}")


# ============================================================================
# 存储层异常
# ============================================================================

class StorageException(XiuxianException):
    """存储层异常基类"""
    def __init__(self, message: str):
        super().__init__(f"存储错误: {message}")


class FileReadException(StorageException):
    """文件读取异常"""
    def __init__(self, message: str):
        super().__init__(f"文件读取失败: {message}")


class FileWriteException(StorageException):
    """文件写入异常"""
    def __init__(self, message: str):
        super().__init__(f"文件写入失败: {message}")


class FileLockException(StorageException):
    """文件锁异常"""
    def __init__(self, message: str):
        super().__init__(f"文件锁错误: {message}")


class DataValidationException(StorageException):
    """数据验证异常"""
    def __init__(self, message: str):
        super().__init__(f"数据验证失败: {message}")
