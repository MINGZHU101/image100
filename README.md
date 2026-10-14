# image100 · 电商商品视觉

面向中小电商卖家 / 运营的「自然语言电商修图工作台」。

当前版本：**v1.0.0（脚手架）** — FastAPI + React 可启动，健康检查对接虚拟机 PostgreSQL / Redis。

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python 3.13、FastAPI、SQLAlchemy(async)、asyncpg、redis |
| 前端 | React 19、Vite、TypeScript、react-router-dom |
| 中间件 | 虚拟机 Docker：PostgreSQL `7311`、Redis `7312` |

## 前置条件

- Windows 本机开发；中间件已在虚拟机部署（示例 IP：`192.168.137.128`）
- Conda 环境 `image100`（Python 3.13+）
- Node.js 18+（推荐 20+）
- 虚拟机防火墙已放行 `7311` / `7312`，本机可 `Test-NetConnection`

## 配置环境变量

```bash
# 在项目根目录
copy .env.example .env
```

默认连接串（Windows → 虚拟机）：

```env
DATABASE_URL=postgresql+asyncpg://retouch:retouch_dev@192.168.137.128:7311/retouch
REDIS_URL=redis://192.168.137.128:7312/0
API_PORT=7302
CORS_ORIGINS=http://localhost:7301,http://127.0.0.1:7301
```

若虚拟机 IP 变更，请同步修改 `.env`。

## 启动后端

```bash
cd backend
# 使用 conda 环境 image100
pip install -e .

uvicorn app.main:app --reload --host 0.0.0.0 --port 7302
```

验收：

```bash
curl http://127.0.0.1:7302/api/health
```

期望（全部连通时）：

```json
{"status":"ok","postgres":"ok","redis":"ok"}
```

某一依赖不通时对应字段为 `"error"`，整体 `status` 为 `"degraded"`（HTTP 仍为 200）。  
API 文档：http://127.0.0.1:7302/api/docs

## 启动前端

```bash
cd frontend
npm install
npm run dev
```

浏览器打开：http://127.0.0.1:7301/  
开发代理会将 `/api` 转到后端 `7302`。落地页会展示 postgres / redis 状态。

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
├── .env.example          # 环境变量模板
├── backend/              # FastAPI
│   └── app/
├── frontend/             # React + Vite
└── docs/                 # 规划与部署文档
```

v1 **未包含**：上传、画布、Agent、Worker 等（见 `docs/电商商品视觉生产_版本规划与v1交付说明.md`）。

## 版本计划（摘要）

v1 骨架 → v2 商品图 → v3 手动修图 → v4 Agent → … → v8 部署验收
