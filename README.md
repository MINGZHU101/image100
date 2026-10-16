# image100 · 电商商品视觉

面向中小电商卖家 / 运营的「自然语言电商修图工作台」。

当前版本：**v3.0.0（工具 + Worker + SSE）** — 工具栏修图、异步执行、进度推送、画布刷新、导出。

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python 3.13、FastAPI、SQLAlchemy(async)、Alembic、asyncpg、redis、Pillow、**ARQ** |
| 前端 | React 19、Vite、TypeScript、react-router-dom、Konva |
| 中间件 | 虚拟机 Docker：PostgreSQL `7311`、Redis `7312` |
| 存储 | 本地磁盘 `./data`（后续可切腾讯云 COS） |

## 前置条件

- Windows 本机开发；中间件已在虚拟机部署（示例 IP：`192.168.137.128`）
- Conda 环境 `image100`（Python 3.13+）
- Node.js 18+（推荐 20+）
- 虚拟机防火墙已放行 `7311` / `7312`

## 配置环境变量

```bash
# 在项目根目录
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
```

## 启动（v3 需要三个进程）

> **重要**：只开 API 不开 Worker 时，工具任务会一直停在 `queued`。

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

验收：

```bash
curl http://127.0.0.1:7302/api/health
curl http://127.0.0.1:7302/api/tools
```

浏览器：http://127.0.0.1:7301/

1. 上传商品图并进入编辑器  
2. 点「提亮 / 去背景 / 水平翻转」→ 进度条走动 → 画布更新  
3. 点「导出」下载当前主图层

API 文档：http://127.0.0.1:7302/api/docs

## 端口一览

| 服务 | 端口 |
|------|------|
| 前端 Vite | 7301 |
| 后端 FastAPI | 7302 |
| PostgreSQL（虚拟机宿主机） | 7311 |
| Redis（虚拟机宿主机） | 7312 |

## 目录说明

```text
image100/
├── .env.example
├── data/                 # 本地图片（gitignore）
├── backend/
│   ├── migrations/       # Alembic（含 tool_runs）
│   └── app/
│       ├── tools/        # ToolRegistry
│       ├── edits/        # 像素算法
│       ├── tasks/        # ARQ 任务
│       ├── worker.py
│       ├── queue.py
│       └── events.py
├── frontend/
└── docs/
```

v3 **未包含**：LangGraph / 计划卡片 / Agent（见 v4）、文生图、选区、完整图层面板。

## 版本计划（摘要）

v1 骨架 → v2 商品图 → **v3 手动修图（当前）** → v4 Agent → … → v8 部署验收

分支建议：`version3`，标签：`v3.0.0`
