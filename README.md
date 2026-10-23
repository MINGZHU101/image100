# image100 · 电商商品视觉工作台

面向中小电商卖家 / 运营的「自然语言电商修图工作台」：上传商品图、Agent 修图、文生图、文案生成、积分会员、工作台 RAG 客服与管理端。

**当前版本：v13**（分支 `version13`）

| 能力 | 说明 |
|------|------|
| 修图 Agent | LangChain 工具绑定 + LangGraph 规划校验；确认后后台串行执行 |
| 文生图 | 通义万相 2.0 / 3.0 可选 |
| 文案 | 分阶段 SSE；可看图理解卖点 |
| RAG 客服 | 加厚教程 FAQ；口语检索；悬浮球流式问答 |
| 会员积分 | 余额 / 积分、签到、邀请、幸运大转盘 |
| 批量 | 多图进度明细 + 打包下载 |
| 管理端 | 与用户端同色板；用户、流水、运营、转盘配置等 |
| 部署 | Docker Compose 一键；默认腾讯云 COS |

---

## 一键启动（虚拟机 Docker，推荐）

在项目根目录（含 `docker-compose.yml`）执行：

```bash
docker compose up -d --build
```

首次构建可能较久（Python 依赖含 Chroma 等）。完成后：

| 入口 | 地址 |
|------|------|
| 工作台前端 | http://\<虚拟机IP\>:7301/ |
| API 文档 | http://\<虚拟机IP\>:7302/api/docs |
| 健康检查 | http://\<虚拟机IP\>:7302/api/health |

**默认账号**

| 角色 | 账号 | 密码 |
|------|------|------|
| 演示用户 | `demo` | `demo123` |
| 管理员 | `admin` | `admin123456` |

**Compose 会拉起**

- `postgres`（宿主机 `7311`）
- `redis`（宿主机 `7312`）
- `api`（FastAPI `7302`，启动时自动 `alembic upgrade head`）
- `worker`（ARQ：工具 / Agent / 文生图任务）
- `web`（Nginx 静态前端，并把 `/api` 反代到 api）

默认使用 **腾讯云 COS**（`STORAGE_BACKEND=cos`）。请在 `.env` 填写 `COS_SECRET_ID` / `COS_SECRET_KEY` / `COS_REGION` / `COS_BUCKET`（见 `docs/腾讯云COS密钥与存储桶获取教程.md`）。需要本机磁盘时可改为 `STORAGE_BACKEND=local`（数据落在 volume `image100_data`）。

### 必填 / 可选环境变量

复制示例环境变量到项目根 `.env`（Compose 会自动读取用于变量替换）：

```bash
cp .env.example .env
# 编辑 .env，至少填入 COS 四项；建议再填：
# DASHSCOPE_API_KEY=sk-xxx
```

不填大模型 Key 时：Agent 可切 Mock；文生图 / RAG 向量化能力受限，但服务仍可启动。COS 未配置则上传与读图会失败。

若要从外网 IP 访问，可在 `.env` 增加：

```env
CORS_ORIGINS=http://你的虚拟机IP:7301,http://localhost:7301,http://127.0.0.1:7301
```

（同源走 Nginx `:7301` 时一般不必改 CORS。）

### 常用命令

```bash
docker compose ps
docker compose logs -f api worker web
docker compose down          # 停容器（保留数据卷）
docker compose down -v       # 停并清空数据库/本地文件卷（慎用）
```

防火墙请放行 **7301**（前端）、按需放行 **7302**（直连 API）。

---

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python 3.13、FastAPI、SQLAlchemy(async)、Alembic、ARQ、LangGraph、LangChain、Chroma |
| 前端 | React 19、Vite、TypeScript、Tailwind、TanStack Query、Zustand、Konva |
| 中间件 | PostgreSQL、Redis（Compose 内置；也可本机连虚拟机端口） |
| 存储 | Docker 默认腾讯云 COS；可改 `local` |

---

## 本机开发启动（可选）

不使用 Compose、本机连已有 Postgres/Redis 时：先配置环境，再一键起前后端。

```bash
cp .env.example .env
# 按本机/虚拟机地址改 DATABASE_URL、REDIS_URL

cd backend && pip install -e . && python -m alembic upgrade head && cd ..
cd frontend && npm install && cd ..
```

**一键启动（推荐）**：在项目根目录用当前 Python 环境执行：

```bash
python run.py
```

会同时拉起：

- API（`uvicorn`，端口 7302）
- ARQ Worker（Agent / 文生图 / 工具队列）
- 前端 Vite（端口 7301）

浏览器打开 http://127.0.0.1:7301/ ，按 `Ctrl+C` 结束全部子进程。

也可手动分三个终端启动（与 `run.py` 等价）：

```bash
# 终端 1：API
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 7302

# 终端 2：Worker
cd backend
python -m arq app.worker.WorkerSettings

# 终端 3：前端
cd frontend
npm run dev
```

> 只开 API 不开 Worker 时：工具与「确认后的 Agent 计划」会停在排队状态。  
> `run.py` **不会**启动 Postgres/Redis；请先保证虚拟机中间件或 Docker 数据库已可用。

---

## 验收建议

1. 打开前端 → 一键演示登录 `demo`  
2. 创作页上传 / 文生图 → 进编辑器  
3. Agent：「把图片翻转，然后提亮」→ 确认计划 → 看结果  
4. 文案页 / 客服悬浮球（有 Key 体验更完整）  
5. 管理端 `/admin`：`admin` / `admin123456`  

```bash
curl http://127.0.0.1:7302/api/health
```

---

## 文档索引

| 文档 | 说明 |
|------|------|
| `docs/电商商品视觉生产_v12交付说明.md` | v12 需求与交付 |
| `docs/v12_第十二版完成总结.md` | v12 完成总结 |
| `docs/LangChain_LangGraph_RAG说明.md` | Agent / RAG 技术说明 |
| `docs/项目面试逐字稿_Agent与RAG.md` | 面试口述稿 |
| `docs/电商商品视觉工作台使用教程.md` | RAG 知识源 / 使用说明 |
| `docs/腾讯云COS密钥与存储桶获取教程.md` | COS 配置 |

仓库：https://github.com/MINGZHU101/image100  

---

## 目录结构（Docker 相关）

```text
docker-compose.yml          # 一键编排
docker/
  Dockerfile.backend        # API + Worker
  Dockerfile.frontend       # Nginx + 静态资源
  nginx.conf
  entrypoint-backend.sh     # 等库 → 迁移 → 启动
backend/                    # FastAPI / ARQ / Alembic
frontend/                   # React
docs/                       # 交付与教程（镜像内含，供 RAG）
```
