# image100 · 电商商品视觉

面向中小电商卖家 / 运营的「自然语言电商修图工作台」。

当前版本：**v7（图层）** — 拆成背景/主体两层，图层面板显隐与选中后按层修图。

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

1. 打开 http://127.0.0.1:7301/ 上传商品图进编辑器  
2. 点 **拆层** → 左侧图层面板出现「背景」「主体」  
3. 点「隐」隐藏主体 → 画布只剩背景；再显示恢复  
4. 选中主体后点 **提亮** → 仅主体变亮  
5. 选区 / Agent / 导出仍可用（导出为可见层合成图）

```bash
curl http://127.0.0.1:7302/api/health
curl http://127.0.0.1:7302/api/tools
```

API 文档：http://127.0.0.1:7302/api/docs

## v7 图层说明

- 工具 `split_layers`：mock 去背 + 本地填洞，得到背景/主体两资产  
- `PATCH /api/sessions/{id}/layers`：更新可见性与 `active_layer_id`  
- 修图工具默认作用在当前选中层  
- 导出按可见层自下而上扁平化  

## 端口

| 服务 | 端口 |
|------|------|
| 前端 Vite | 7301 |
| 后端 FastAPI | 7302 |
| PostgreSQL | 7311 |
| Redis | 7312 |

分支：`version7`，标签：`v7.0.0`（打 tag 前以实际提交为准）
