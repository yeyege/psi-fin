"""业务异常 — 携带 HTTP 状态码，由全局异常处理器统一转为响应"""


class BusinessError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status
