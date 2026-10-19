# v9 API 对照表（增量，相对 v8）

| 能力 | 路径 / 工具名 | 状态 |
|------|---------------|------|
| 历史列表 | `GET /sessions/{id}/history` | 已实现 |
| 撤销 / 重做 | `POST .../undo` `.../redo` | 已实现 |
| `crop_canvas` | tools | 本地裁剪 |
| `upscale_image` | tools | 本地 Lanczos |
| `replace_background` | tools | mock |
| `expand_canvas` | tools | 本地扩画布 |
| `erase_region` / `replace_region` | tools | 本地/mock |
| `promote_object_to_layer` | tools | 选区成层 |
| 图层变换 | move/scale/rotate/opacity/reorder/text | document 写入 |
| 点选 | `POST .../selection` points | mock 椭圆选区 |
| `generate_marketing` / `prepare_delivery_sizes` | tools | mock/本地 |
| 批量 | `POST/GET /batches` | 简化：已注册工具子集 |
| Docker | — | **不做** |

完整 v8 基线见 `v8_API对照表.md`。
