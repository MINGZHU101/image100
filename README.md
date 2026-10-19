# image100 · 电商商品视觉

面向中小电商卖家 / 运营的「自然语言电商修图工作台」。

当前版本：**v9（按前端补后端）** — 在 v8 前端上接通 undo/redo、编辑器缺口工具、营销图与批量；默认 COS；**不做 Docker**。

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python 3.13、FastAPI、SQLAlchemy(async)、Alembic、asyncpg、redis、Pillow、ARQ、LangGraph、**cos-python-sdk-v5** |
| 前端 | React 19、Vite、TypeScript、Tailwind、TanStack Query、Zustand、Konva（原仓 UI） |
| 中间件 | 虚拟机 Docker：PostgreSQL `7311`、Redis `7312` |
| 存储 | 默认腾讯云 COS（`STORAGE_BACKEND=cos`）；可改 `local` 回退 |

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
STORAGE_BACKEND=cos
COS_SECRET_ID=
COS_SECRET_KEY=
COS_REGION=ap-shanghai
COS_BUCKET=your-bucket-1250000000
# 本机回退：STORAGE_BACKEND=local 与 LOCAL_STORAGE_DIR=./data
# COS 四项获取：docs/腾讯云COS密钥与存储桶获取教程.md
```

演示登录：`demo` / `demo123`（登录页有一键按钮）。

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

1. 打开 http://127.0.0.1:7301/ → 登录页一键演示账号  
2. 创作页上传 / 文生图 → 进编辑器  
3. 提亮、去背、翻转、笔刷选区、拆层、Agent 规划确认  
4. 批量 / 营销图为占位页（后续版本）  
5. （可选）`.env` 切 `STORAGE_BACKEND=cos` 后上传一张图，桶内可见对象  

```bash
curl http://127.0.0.1:7302/api/health
curl http://127.0.0.1:7302/api/tools
```

API 文档：http://127.0.0.1:7302/api/docs  
接口对照：`docs/v8_API对照表.md`  
v8 交付说明：`docs/电商商品视觉生产_v8交付说明.md`  
v9 交付说明：`docs/电商商品视觉生产_v9交付说明.md`  
v9 完成总结：`docs/v9_第九版完成总结.md`

## 本仓已暴露工具（v9）

提亮/局部提亮、去背、翻转、拆层、裁剪、超分、换背景、扩图、消除/替换/成层、图层变换、营销图、投放尺寸等（见 `GET /api/tools`）。  
批量第一版仅支持已注册工具子集。
