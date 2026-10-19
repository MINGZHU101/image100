"""图层文档约定：常量与解析（精简版，无 transform/文字层）。"""

from typing import Any

LAYER_MAIN_ID = "layer_main"
LAYER_BACKGROUND_ID = "layer_background"
LAYER_SUBJECT_ID = "layer_subject"


def already_split(document: dict[str, Any] | None) -> bool:
    """是否已拆成背景 + 主体。"""
    layers = (document or {}).get("layers") or []
    ids = {str(layer.get("id")) for layer in layers}
    return LAYER_BACKGROUND_ID in ids and LAYER_SUBJECT_ID in ids


def resolve_target_layer(document: dict[str, Any] | None) -> dict[str, Any]:
    """
    解析当前编辑目标层：
    优先 active_layer_id；否则取最上层可见层；再否则取最上层。
    """
    doc = document or {}
    layers = list(doc.get("layers") or [])
    if not layers:
        raise ValueError("会话无图层")

    active_id = doc.get("active_layer_id")
    if active_id:
        for layer in layers:
            if str(layer.get("id")) == str(active_id):
                return dict(layer)

    # 自顶向下找可见层
    for layer in reversed(layers):
        if layer.get("visible", True):
            return dict(layer)
    return dict(layers[-1])


def build_split_layers(
    *,
    background_asset_id: str,
    background_key: str,
    subject_asset_id: str,
    subject_key: str,
) -> list[dict[str, Any]]:
    """拆层后的标准两层（自下而上）。"""
    return [
        {
            "id": LAYER_BACKGROUND_ID,
            "name": "背景",
            "asset_id": background_asset_id,
            "asset_key": background_key,
            "visible": True,
            "locked": True,
        },
        {
            "id": LAYER_SUBJECT_ID,
            "name": "主体",
            "asset_id": subject_asset_id,
            "asset_key": subject_key,
            "visible": True,
            "locked": False,
        },
    ]
