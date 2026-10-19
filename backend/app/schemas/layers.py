"""图层 PATCH 请求体。"""

from pydantic import BaseModel, Field


class LayerPatchItem(BaseModel):
    id: str
    visible: bool | None = None


class LayersPatchIn(BaseModel):
    """更新图层可见性与当前选中层。"""

    layers: list[LayerPatchItem] = Field(default_factory=list)
    active_layer_id: str | None = None
