from enum import Enum
from typing import Optional


class ErrorCode(Enum):
    SUCCESS = (0, "ok")

    PARAMS_ERROR = (40000, "请求参数错误")
    NOT_LOGIN_ERROR = (40100, "未登录")
    NO_AUTH_ERROR = (40101, "无权限")
    NOT_FOUND_ERROR = (40400, "请求数据不存在")
    FORBIDDEN_ERROR = (40300, "禁止访问")
    SYSTEM_ERROR = (50000, "系统内部异常")
    OPERATION_ERROR = (50001, "操作失败")

    USER_NOT_EXIST = (40401, "用户不存在")
    USER_ALREADY_EXIST = (40402, "用户已存在")
    PASSWORD_ERROR = (40103, "密码错误")

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message


class BusinessException(Exception):
    def __init__(self, error_code: ErrorCode, message: Optional[str] = None):
        self.error_code = error_code
        self.message = message or error_code.message
        super().__init__(self.message)


def throw_if(condition: bool, error_code: ErrorCode, message: Optional[str] = None):
    if condition:
        raise BusinessException(error_code, message)


def throw_if_not(condition: bool, error_code: ErrorCode, message: Optional[str] = None):
    if not condition:
        raise BusinessException(error_code, message)
