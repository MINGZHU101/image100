"""通用响应模型。"""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """健康检查响应：整体状态 + 各依赖探测结果。"""

    status: str = Field(description="ok 表示全部正常，degraded 表示有依赖异常")
    postgres: str = Field(description="ok 或 error")
    redis: str = Field(description="ok 或 error")
