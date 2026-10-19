# image100 · 电商商品视觉

面向中小电商卖家 / 运营的「自然语言电商修图工作台」。

当前版本：**v6（选区 + 局部调色）** — 矩形/笔刷框选后，仅对选区内提亮。

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python 3.13、FastAPI、SQLAlchemy(async)、Alembic、asyncpg、redis、Pillow、ARQ、**LangGraph + langchain-core/openai** |
| 前端 | React 19、Vite、TypeScript、react-router-dom、Konva |
| 中间件 | 虚拟机 Docker：PostgreSQL `7311`、Redis `7312` |
| 存储 | 本地磁盘 `./data` |

## 配置环境变量

```bash
copy .env.example .env
```

关键项：

```env
DATABASE_URL=postgresql+asyncpg://retouch:retouch_dev@192.168.137.128:7311/retouch
REDIS_URL=redis://192.168.137.128:7312/0
API_PORT=7302
CORS_ORIGINS=http://localhost:7301,http://127.0.0.1:7301
STORAGE_BACKEND=local
LOCAL_STORAGE_DIR=./data
UPLOAD_MAX_BYTES=10485760
MATTING_PROVIDER=mock
PLANNER_PROVIDER=dashscope
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
PLANNER_MODEL=qwen-plus
IMAGE_PROVIDER=dashscope
TEXT_TO_IMAGE_MODEL=qwen-image-3.0-pro
# DASHSCOPE_API_KEY 建议放系统环境变量，勿提交仓库
```

## 启动（三个进程）

> 只开 API 不开 Worker 时：工具与「确认后的 Agent 计划」都会停在 queued。

```bash
# 终端 1：API
cd backend
pip install -e .
python -m alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 7302

# 终端 2：ARQ Worker
cd backend
python -m arq app.worker.WorkerSettings

# 终端 3：前端
cd frontend
npm install
npm run dev
```

## 验收路径

1. 打开 http://127.0.0.1:7301/ 上传商品图（或创作页生图进编辑器）
2. 工具栏左侧：**矩形选区** / **笔刷选区** / **清除选区**
3. 在画布上框选一块区域 → 点 **局部提亮** → 仅选区内变亮
4. 整图提亮 / 去背景 / 翻转 / 导出仍可用
5. （可选）Agent Mock：先框选，再输入「局部提亮一点」→ 计划卡片含 `adjust_region`

```bash
curl http://127.0.0.1:7302/api/health
curl http://127.0.0.1:7302/api/tools
```

API 文档：http://127.0.0.1:7302/api/docs

## v6 选区说明

- 选区写入会话 `document.selection`（`PATCH /api/sessions/{id}/selection`）
- 坐标相对画布 **0～1**；笔刷默认半径相对短边 `0.03`
- 工具 `adjust_region`：整图调色后按掩膜合成，选区外不变；成功后自动清空选区
- 选区模式下画布优先绘制选区；退出选区模式后可拖拽平移

## Agent 架构（v4）

- **③ Plan & Execute**：先产出计划，确认后再执行
- **⑦ Graph/Workflow**：LangGraph `plan → verify → END`
- **HITL**：PlanCard + REST confirm（图内不 interrupt）
- 执行复用 ToolRegistry + ARQ + SSE

## 端口

| 服务 | 端口 |
|------|------|
| 前端 Vite | 7301 |
| 后端 FastAPI | 7302 |
| PostgreSQL | 7311 |
| Redis | 7312 |

分支：`version6`，标签：`v6.0.0`
