"""选区 JSON 形状：相对画布 0～1 归一化坐标。"""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class RectSelection(BaseModel):
    """矩形选区。"""

    type: Literal["rect"] = "rect"
    rect: dict[str, float]
    feather: float = Field(default=0.0, ge=0)

    @model_validator(mode="after")
    def validate_rect(self) -> "RectSelection":
        required = ("x", "y", "width", "height")
        for key in required:
            if key not in self.rect:
                raise ValueError(f"rect 缺少字段 {key}")
            value = float(self.rect[key])
            if not (0.0 <= value <= 1.0):
                raise ValueError(f"rect.{key} 须在 0～1")
            self.rect[key] = value
        if self.rect["width"] <= 0 or self.rect["height"] <= 0:
            raise ValueError("rect 宽高须大于 0")
        return self


class BrushSelection(BaseModel):
    """笔刷选区：多笔 stroke，点列为归一化坐标。"""

    type: Literal["brush"] = "brush"
    strokes: list[list[list[float]]] = Field(default_factory=list)
    brush_radius: float = Field(default=0.03, gt=0, le=0.5)
    feather: float = Field(default=0.0, ge=0)

    @model_validator(mode="after")
    def validate_strokes(self) -> "BrushSelection":
        if not self.strokes:
            raise ValueError("strokes 不能为空")
        cleaned: list[list[list[float]]] = []
        for stroke in self.strokes:
            points: list[list[float]] = []
            for point in stroke:
                if len(point) < 2:
                    raise ValueError("笔画点须含 x、y")
                x = float(point[0])
                y = float(point[1])
                if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
                    raise ValueError("笔画坐标须在 0～1")
                points.append([x, y])
            if points:
                cleaned.append(points)
        if not cleaned:
            raise ValueError("strokes 不能为空")
        self.strokes = cleaned
        return self


class SelectionPatchIn(BaseModel):
    """PATCH /sessions/{id}/selection 请求体。"""

    selection: RectSelection | BrushSelection | None = None

