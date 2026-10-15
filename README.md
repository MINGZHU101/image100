# image100 · 电商商品视觉

面向中小电商卖家 / 运营的「自然语言电商修图工作台」。

当前版本：**v2.0.0（资产与会话）** — 上传商品图、创建编辑会话、Konva 画布显示图片。

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python 3.13、FastAPI、SQLAlchemy(async)、Alembic、asyncpg、redis、Pillow |
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
```

## 启动后端

```bash
cd backend
pip install -e .

# 首次或拉取新迁移后：升级数据库表结构
python -m alembic upgrade head

uvicorn app.main:app --reload --host 0.0.0.0 --port 7302
```

验收：

```bash
curl http://127.0.0.1:7302/api/health
```

期望（全部连通时）：

```json
{"status":"ok","postgres":"ok","redis":"ok","storage":"ok"}
```

上传示例：

```bash
curl -F "file=@demo.jpg" http://127.0.0.1:7302/api/assets
```

API 文档：http://127.0.0.1:7302/api/docs

## 启动前端

```bash
cd frontend
npm install
npm run dev
```

浏览器打开：http://127.0.0.1:7301/  

1. 点击「上传商品图并开始修图」  
2. 自动创建会话并进入编辑器  
3. 画布显示商品图（滚轮缩放、拖拽平移）

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
│   ├── migrations/       # Alembic
│   └── app/
├── frontend/
└── docs/
```

v2 **未包含**：修图工具、Worker、SSE、Agent（见 `docs/电商商品视觉生产_v2交付说明.md`）。

## 版本计划（摘要）

v1 骨架 → **v2 商品图（当前）** → v3 手动修图 → v4 Agent → … → v8 部署验收

分支建议：`version2`，标签：`v2.0.0`
