# v8 API 对照表（原仓前端 ↔ image100 后端）

> 策略：优先前端改调；必要时本仓增加兼容路由。未实现能力返回占位/501，不假装完成。

| 原仓调用 | 本仓处理 | 状态 |
|----------|----------|------|
| `POST /api/auth/login\|register\|logout`，`GET /me` | 演示鉴权桩（Cookie + demo/demo123） | 已对齐 |
| `POST /api/assets` | 返回原仓 Asset 形状（`url`） | 已对齐 |
| `GET /api/assets`、`/library` | 列表 / 简易分组 | 已对齐 |
| `GET /api/assets/{id}/file` | local/COS 统一 `storage.get` | 已对齐 |
| `POST/GET /api/sessions` | 兼容 `current_asset_id`；详情补 LayerDocument | 已对齐 |
| `POST /api/sessions/{id}/tools` `{tool,params}` | 兼容入口 → 入队；回 `{run,session}` | 已对齐 |
| `POST .../tools/{name}` | 本仓原入口仍保留 | 保留 |
| `GET /api/runs/{id}` | 工具运行 **或** 文生图 | 已对齐 |
| `GET /api/events/{id}` | SSE progress/completed/error | 已对齐（前端改路径） |
| `POST /api/generations` | 接受 `ratio`；回 Run 形状 | 已对齐 |
| `.../messages` | 别名转发本仓 Agent | 已对齐 |
| 选区 `selection` / `prepare` | 笔刷→本仓 brush + mask 资产；点选 501 | 部分 |
| `undo` / `redo` | 501 | 顺延 |
| `POST .../exports` | 扁平 PNG（非 zip） | 降级对齐 |
| `/batches`、`marketing` 工具 | 前端占位页 | 顺延 |
| COS `STORAGE_BACKEND=cos` | CosStorage | 已实现 |

本仓 Registry 工具：`adjust_image`、`adjust_region`、`remove_background`、`flip_layer`、`split_layers`。
