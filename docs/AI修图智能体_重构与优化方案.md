# AI 修图智能体 — 重构与优化方案

> **文档版本**：v1.0  
> **编写日期**：2026-10-13  
> **原项目**：[yuyuanweb/ai-picture-editor](https://github.com/yuyuanweb/ai-picture-editor)（React 19 + FastAPI + LangChain + LangGraph + Konva）  
> **目标项目代号**：`image100`（工作区：`R:\a0707\PyCharm\image100`）  
> **部署目标**：CentOS（VMware 虚拟机 `node101`，磁盘路径 `R:\a0707\xuniji\node101`）+ Docker Compose  

---

## 0. 文档说明

本文档回答三件事：

1. **为什么重构、改什么、不改什么**  
2. **每一层（前端 / 后端 / Agent / 中间件 / Docker）具体怎么做**  
3. **按什么顺序分期交付，哪些功能可以砍掉或延后**

配套文档见同目录：`基于React与LangGraph的AI修图智能体平台项目需求.md`。

---

## 1. 原项目现状摘要

### 1.1 产品定位

原项目是一套 **AI Agent 驱动的图片编辑全栈应用**：用户用自然语言描述修图意图，后端 Agent 规划多步工具调用，前端画布实时展示结果。覆盖文生图、画布编辑、智能抠图、区域编辑、图层拆分、多步计划等人机协作能力。

### 1.2 原技术栈

| 层级 | 原技术 | 说明 |
|------|--------|------|
| 前端 | React 19 + Vite + TypeScript + react-konva + Zustand + TanStack Query + Tailwind | 专业级 Canvas 编辑器 |
| 后端 | Python 3.13 + FastAPI + SQLAlchemy(async) + Alembic | REST + SSE |
| 智能体 | LangChain（模型/工具签名）+ LangGraph（规划图） | 计划 → 校验 → 人确认 → 执行 |
| 异步 | ARQ + Redis Pub/Sub + SSE | 耗时任务与进度推送 |
| 存储 | PostgreSQL + Redis + MinIO(S3) | 业务 / 缓存消息 / 图片对象 |
| 图像 | Pillow + rembg + OpenCV + RapidOCR；AI 侧 DashScope（可 mock） | Provider 抽象可切换 |
| 部署 | Docker 多阶段构建 + compose profile `deploy` | 前后端同源托管 |

### 1.3 原核心模块（业务）

1. AI 文生图（四宫格候选 + SSE 进度）  
2. 专业画布编辑器（缩放平移、图层、撤销重做、前后对比）  
3. 自然语言驱动修图（Agent 对话）  
4. 约 21 种编辑工具（UI 与 Agent 共享 ToolRegistry）  
5. SAM 智能点选 + 笔刷选区  
6. 局部消除 / 局部替换  
7. 图层拆分（主体/背景/OCR 文字）  
8. 多步计划校验、拓扑排序、人机确认  
9. 营销图、批量处理（扩展模块）

### 1.4 原 Agent 架构要点（需保留思想）

原 `backend/app/agent/graph.py` 采用 **精简 LangGraph**：

```
START → plan（LLM 产出 tool_calls）→ verify（服务端校验计划）→ END
```

- **LangChain**：接入规划模型、绑定工具 schema  
- **LangGraph**：编排「规划 → 校验」状态机；真正执行工具在服务层/Worker，不在图里盲目自动连跑  
- **ToolRegistry**：一处注册，UI 按钮与 Agent 共用  
- **人机协作**：复杂计划先展示给用户确认，再按依赖执行  

重构时 **保留这套「计划—校验—确认—执行」心智模型**，不要改成不可控的全自动无限循环 Agent。

### 1.5 原项目问题与重构动机

| 问题 | 影响 | 本方案应对 |
|------|------|------------|
| 前端沿用 React，但模块过多、耦合偏重 | 一期难交付、虚拟机难跑 | **保留 React 栈**，按期精简页面与交互 |
| 功能面过大（SAM、营销图、批量、完整图层拆分等） | 一期难以完整交付 | 分期 + 明确砍减清单 |
| 本地/虚拟机部署路径未针对 CentOS 写清 | 上线摩擦大 | 专章写 Docker on CentOS |
| 文档偏教程营销，缺「怎么分步重构」工程文档 | 落地顺序不清 | 本文 + 需求分析文档 |

---

## 2. 重构目标与原则

### 2.1 目标

1. **前端**：默认沿用原版 **React 19 + Vite + TypeScript + react-konva + Zustand**，不做 Vue 重写；按期精简功能与页面。  
2. **后端**：继续 **Python 3.13 + FastAPI**；结构可参考原项目分层，按需精简。  
3. **智能体**：**以 LangGraph 为主、LangChain 为辅**（选型见第 4 章）。  
4. **部署**：最终在 **CentOS Docker** 上一键或近一键启动；开发可在 Windows 本机，生产镜像在 `node101` 运行。  
5. **交付策略**：**先骨架、再主链路、再增强**；能简化则简化，保证每期可演示、可验收。

### 2.2 原则

- **行为兼容优先**：核心业务流（上传/生图 → 编辑会话 → Agent 计划 → 工具执行 → SSE 刷新画布）语义对齐原项目，接口可渐进演进。  
- **共享工具注册表**：UI 与 Agent 绝不维护两套工具定义。  
- **Mock 优先**：无 API Key 也能跑通全流程（`IMAGE_PROVIDER=mock`）。  
- **异步边界清晰**：>1s 的图像/模型任务进队列；API 进程只做编排与推送。  
- **可部署性从第一期就考虑**：目录、环境变量、compose 与 CentOS 约束同步设计。

### 2.3 非目标（明确不做或延后）

见第 8 章「简化与砍减清单」。一期不追求「功能数量追上原教程」，追求「主链路可演示 + 架构正确」。

---

## 3. 目标技术栈（重构后）

### 3.1 前端（容器 / 本地 Node）

| 组件 | 选型 | 说明 |
|------|------|------|
| 框架 | **React 19** + TypeScript | 与原项目一致，降低迁移成本 |
| 构建 | Vite + TypeScript | 对齐原工程化 |
| 路由 | React Router | 落地页 / 创作 / 编辑器 / 登录 |
| 状态 | Zustand | 与原项目一致 |
| 请求 | TanStack React Query + 自封装 SSE | 与原项目一致 |
| 画布 | **react-konva** + konva | 保留原画布方案 |
| UI | 自研编辑器布局 + 轻量组件 | 不强行引入重型 UI 库 |
| 样式 | Tailwind CSS | 与原项目一致 |

### 3.2 后端（Python 3.13）

| 组件 | 选型 | 说明 |
|------|------|------|
| Web | FastAPI + Uvicorn | 保留 |
| 校验/配置 | Pydantic v2 + pydantic-settings | 保留 |
| ORM | SQLAlchemy 2.0 asyncio + Alembic | 保留 |
| DB | PostgreSQL 16/17 | 业务数据、图层 JSONB |
| 缓存/队列 | Redis 7 + ARQ（或 Celery，优先 ARQ 与原一致） | 任务与 Pub/Sub |
| 对象存储 | MinIO（S3 API） | 图片资产 |
| 图像本地 | Pillow；抠图 rembg（可选依赖） | 重模型可二期 |
| AI Provider | 抽象接口：`mock` / `dashscope`（可扩 OpenAI 兼容） | 配置切换 |
| Agent | **LangGraph + langchain-core + langchain-openai** | 见第 4 章 |
| 认证 | JWT（HttpOnly Cookie 或 Bearer，一期可简化） | 二期再加强 |

### 3.3 运维与部署

| 组件 | 选型 |
|------|------|
| 编排 | Docker Compose v2 |
| 反向代理（可选） | Nginx（前端静态 + `/api` 反代） |
| 宿主机 | CentOS 7/8/Stream（`node101` 虚拟机） |
| 镜像构建 | 多阶段：前端 build → 后端镜像内嵌静态资源；或前后端分容器 |

### 3.4 推荐仓库目录（目标结构）

```text
image100/
├── docs/                          # 方案与需求文档（本目录）
├── frontend/                      # React 应用（沿用原栈）
│   ├── src/
│   │   ├── api/                   # REST / SSE 封装
│   │   ├── assets/
│   │   ├── components/
│   │   │   ├── editor/            # 画布、工具栏、对话、图层面板
│   │   │   └── common/
│   │   ├── hooks/
│   │   ├── pages/
│   │   ├── layouts/
│   │   ├── stores/                # Zustand
│   │   ├── lib/
│   │   └── types/
│   ├── package.json
│   └── vite.config.ts
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── routers/               # auth, assets, sessions, runs, events, health
│   │   ├── schemas/
│   │   ├── models/
│   │   ├── services/
│   │   ├── tools/                 # ToolRegistry + 各工具实现
│   │   ├── agent/                 # LangGraph 图、LLM、计划校验
│   │   ├── providers/             # mock / dashscope
│   │   ├── edits/                 # 像素/文档/分割等图像管线（按期引入）
│   │   ├── tasks/                 # ARQ 任务
│   │   └── worker.py
│   ├── migrations/
│   ├── tests/
│   ├── pyproject.toml             # uv / pip 均可，建议 uv
│   └── .env.example
├── deploy/
│   ├── docker-compose.yml
│   ├── Dockerfile                 # 或前后端各一份
│   └── nginx.conf                 # 可选
├── scripts/                       # CentOS 初始化、健康检查脚本
├── .env.example
└── README.md
```

---

## 4. 智能体框架选型：LangChain vs LangGraph

### 4.1 结论（直接采用）

| 角色 | 框架 | 原因 |
|------|------|------|
| **编排主框架** | **LangGraph** | 修图是「有状态、多步、需校验、可中断确认」的工作流，图/状态机比自由 ReAct 循环更可控 |
| **模型与工具绑定** | **LangChain（langchain-core / langchain-openai）** | 消息类型、ChatModel、tool schema、与 DashScope OpenAI 兼容端点对接成熟 |
| **不单独再上** | AutoGen / CrewAI / Semantic Kernel 等 | 本项目是单领域工具 Agent + 人机确认，多框架会增加学习与部署成本 |

**一句话**：用 **LangGraph 管流程，用 LangChain 管模型与工具描述**——与原项目一致，也是本场景更合适的组合。

### 4.2 为什么不是「只用 LangChain Agent」

- 原业务需要：**产出结构化计划 → 服务端校验 → 用户确认 → 再执行**。  
- 纯 `create_react_agent` 容易「边想边调工具」，难做计划卡片与拓扑依赖。  
- LangGraph 的节点边界清晰：`plan` / `verify` /（二期可加）`execute_step` / `ask_human`。

### 4.3 目标 Agent 图（一期最小集）

```text
                    ┌─────────────┐
                    │   START     │
                    └──────┬──────┘
                           ▼
                    ┌─────────────┐
                    │    plan     │  LLM + 工具 schema → tool_calls
                    └──────┬──────┘
                           ▼
                    ┌─────────────┐
                    │   verify    │  ToolRegistry 存在性 / 参数 / 依赖 / 环检测
                    └──────┬──────┘
                           ▼
                    ┌─────────────┐
                    │    END      │  返回 reply + plan（尚未执行）
                    └─────────────┘
         用户确认后由 SessionService / Worker 按拓扑执行工具
```

### 4.4 二期可增强的图节点（可选）

- `clarify`：参数不足时向用户追问（一期尽量用画布上下文补参，少追问）  
- `execute`：低风险单步工具自动执行；多步仍需确认  
- `reflect`：执行失败后有限次重规划（严格限制调用次数，防烧钱）

### 4.5 工具注册表设计（必须先做）

每个工具统一描述：

```text
tool_id / name
label（中文展示名）
description（给 LLM）
params_schema（JSON Schema / Pydantic）
risk_level: low | medium | high
executor: async (ctx, params) -> ToolResult
ui_exposed: bool          # 是否出现在工具栏
agent_exposed: bool       # 是否绑给规划模型
```

一期工具建议（从原 21 种砍到可交付子集，见第 8 章）。

---

## 5. 分模块重构说明（怎么做）

### 5.1 后端分层怎么重构

保持原清晰分层，避免「路由里写业务」：

| 层 | 职责 | 重构要点 |
|----|------|----------|
| routers | HTTP/SSE 入口 | 薄控制器；统一错误码与响应包装 |
| schemas | 入参出参 | Pydantic；前后端字段命名表固化一份 OpenAPI |
| services | 会话、资产、Agent 编排、导出 | 事务边界在此 |
| tools | 工具定义与执行 | **UI/Agent 唯一真相源** |
| agent | LangGraph + LLM | 只负责规划与校验，不直接改像素 |
| providers | 云端生图/编辑/对话 | mock 与真实实现同接口 |
| edits | 像素级算法 | 可按工具逐步迁入，勿一期堆满 |
| tasks/worker | 异步执行 | 进度事件写 Redis，SSE 订阅 |
| models + migrations | 表结构 | 一期表：users / assets / edit_sessions / tool_runs / agent_runs（可再砍 users） |

**优化点**：

1. 配置集中 `Settings`，禁止散落 `os.getenv`。  
2. Provider 工厂：`get_image_provider()` / `get_planner()`。  
3. 所有耗时工具统一 `enqueue → run_id → SSE events`。  
4. 计划校验逻辑独立模块（`agent/plan.py`），单测覆盖环检测与缺参。

### 5.2 前端怎么在 React 上做精简重构

**默认不换框架**：以原 `frontend/` 的 React 结构为底，按分期删减页面与能力，而不是整仓重写。

| 原结构 | 本方案处理 |
|--------|------------|
| `hooks/useXxx` | 保留；未用到的 hook 随功能砍减删除 |
| Zustand stores | 保留 |
| react-konva `Stage/Layer/Image` | 保留；一期先保证显示/缩放/刷新 |
| React Query | 保留 |
| React Router | 保留；未启用的路由可先去掉 |
| 营销/批量等页面 | 一期不进主路径，代码可暂留或移出 |

**编辑器页面拆分（一期）**：

1. `EditorPage`：布局壳  
2. `CanvasStage`：视口缩放平移、图像层渲染  
3. `EditorToolbar`：手动工具入口  
4. `AgentConversation` + `MessageComposer`：自然语言  
5. `SessionSidebar`：会话列表（可极简）  
6. `LayerPanel`：**一期可只做单图层/双图层**，完整多图层拖到二期  

**SSE**：沿用/封装 `useEventStream(runId)`（或原 `useRun` 一类 hook），统一处理 `progress / step_done / error / completed`。

### 5.3 数据流（核心业务）怎么落地

**自然语言修图主链路**：

```text
用户输入指令
  → POST /sessions/{id}/agent/runs
  → AgentService 组装画布 context
  → LangGraph plan+verify
  → 返回 plan 卡片（前端展示）
  → 用户确认 POST .../confirm
  → 按拓扑排序依次 enqueue 工具
  → Worker 执行 → 更新 session 文档/资源
  → Redis Pub/Sub → SSE → 前端刷新画布
```

**文生图链路（可二期，建议一期后半做）**：

```text
提示词 → 异步 generation 任务 → 四宫格候选资产 → 选中进入编辑会话
```

### 5.4 存储与中间件

| 组件 | 用途 | CentOS Docker 注意 |
|------|------|-------------------|
| PostgreSQL | 用户、会话、历史、图层 JSON | 数据卷持久化；时区 UTC |
| Redis | ARQ 队列、Pub/Sub、短期缓存 | 持久化可选 AOF |
| MinIO | 原图/结果图/遮罩 | 需配置 `S3_PUBLIC_ENDPOINT` 为虚拟机可达 IP |

一期若资源紧张，可 **暂用本地磁盘存储替代 MinIO**（接口仍走 Storage 抽象），二期再切 MinIO——见简化清单。

### 5.5 认证

| 阶段 | 方案 |
|------|------|
| 一期 | 可选：固定开发用户 / 极简注册登录；编辑器可不强制登录（本地 demo） |
| 二期 | JWT Cookie（对齐原项目）+ 资产归属隔离 |
| 三期 | 角色权限、分享链接 |

---

## 6. CentOS（node101）Docker 部署方案

### 6.1 环境假设

- 宿主机：VMware 虚拟机 `node101`（磁盘文件位于 `R:\a0707\xuniji\node101`）  
- 访客系统：CentOS  
- 已安装或待安装：Docker Engine + Docker Compose Plugin  
- 代码同步方式（任选）：`git clone` / `scp` / 共享文件夹  

### 6.2 目标运行拓扑

```text
[浏览器] → :8080 Nginx(可选) ─┬→ 静态 React dist
                              └→ /api → FastAPI :7302
                                         ├→ PostgreSQL
                                         ├→ Redis ←→ ARQ Worker
                                         └→ MinIO :9000
```

最小可运行（无 Nginx）：浏览器直连 `http://<centos-ip>:7302`（API 托管前端静态资源）。

### 6.3 compose 服务清单（目标）

| Service | 镜像/构建 | 端口（示例） |
|---------|-----------|--------------|
| postgres | postgres:17-alpine | 7311→5432 |
| redis | redis:7-alpine | 7312→6379 |
| minio | minio/minio | 7313→9000, 7314→9001 |
| api | 本地 Dockerfile | 7302 |
| worker | 同镜像不同 command | 无主机端口 |
| frontend（开发期可选） | node 构建 / nginx | 7301 或 80 |

生产建议：`docker compose --profile deploy up -d --build`。

### 6.4 CentOS 上需要提前做的事（文档级清单）

1. 安装 Docker（注意 CentOS 7 与 8/Stream 源不同；优先官方文档）。  
2. 配置镜像加速（国内环境）。  
3. 开放防火墙端口：`7302`（应用）、`7313`（若浏览器直读 MinIO 签名 URL）。  
4. 修改 `.env`：`JWT_SECRET`、`S3_PUBLIC_ENDPOINT=http://<虚拟机IP>:7313`、`DASHSCOPE_API_KEY`（可空，用 mock）。  
5. 首次：`alembic upgrade head`。  
6. 健康检查：`GET /api/health` 中 db/redis/s3 均为 ok。  

### 6.5 与 Windows 开发机的分工

| 环境 | 用途 |
|------|------|
| Windows + PyCharm（`image100`） | 日常编码、单测、前端热更新 |
| CentOS Docker（node101） | 集成验证、接近生产的部署验收 |

**不要**在 Windows 上假设路径与 Linux 容器内路径一致；所有路径用环境变量与容器卷。

### 6.6 资源与性能简化建议（虚拟机友好）

- 一期关闭本地重模型（SAM 全量、超分大模型）；抠图可用 rembg 轻量或 mock。  
- Worker 并发设为 1～2，避免 CentOS 虚拟机内存打满。  
- PostgreSQL / Redis / MinIO 均用官方小镜像 + 限制 `deploy.resources`（可选）。

---

## 7. 分期实施计划（先写哪部分、再写哪部分）

> 原则：**每一期结束都必须能演示一条完整闭环**，而不是「半成品模块堆砌」。

### 第 0 期：工程脚手架（约 2～3 天）

**目标**：仓库可启动，健康检查通过。

| 任务 | 细节 |
|------|------|
| 初始化 monorepo 目录 | 按第 3.4 节 |
| 后端最小 FastAPI | `/api/health`、配置加载、CORS |
| 前端 React 空壳/精简壳 | 路由：Home / Editor 占位页 |
| docker-compose | 先起 postgres + redis（MinIO 可延后） |
| 文档 | README 本地启动 10 行命令 |

**验收**：本机 `uvicorn` + `npm run dev` 可访问；compose 中间件 healthy。

---

### 第 1 期：资产与编辑会话主数据（约 4～6 天）

**目标**：上传图片 → 创建编辑会话 → 画布显示图片。

| 任务 | 细节 |
|------|------|
| 存储抽象 | 本地磁盘 or MinIO，接口统一 |
| Asset API | 上传、列表、获取 URL |
| Session API | 创建、获取当前文档（单图层即可） |
| 前端画布 | react-konva 显示一张图；缩放平移 |
| DB 迁移 | assets、edit_sessions |

**简化**：不做登录；不做多图层；不做撤销栈持久化。

**验收**：上传一张图进入编辑器并拖动画布。

---

### 第 2 期：工具注册表 + 手动工具（约 5～7 天）

**目标**：工具栏可调用 4～6 个真实/本地工具，异步进度可见。

**建议优先工具**：

1. `adjust_image`（亮度/对比度/饱和度，Pillow）  
2. `remove_background`（rembg 或 mock）  
3. `crop_canvas` / `flip_layer` / `rotate_layer`（几何类）  
4. `export_image`（导出当前结果）

| 任务 | 细节 |
|------|------|
| ToolRegistry | 元数据 + executor |
| ARQ Worker | 执行工具、写 tool_runs |
| SSE | 进度与完成事件 |
| 前端 | 工具栏 + 进度条 + 完成后刷新 |

**验收**：点击「抠图/调色」，画布更新；无真实 AI Key 时 mock 也可。

---

### 第 3 期：LangGraph Agent 自然语言修图（约 5～8 天）

**目标**：一句话生成计划 → 校验 → 确认 → 执行。

| 任务 | 细节 |
|------|------|
| LLM Provider | mock 规划器（规则/固定 JSON）+ dashscope 真实规划 |
| LangGraph | plan → verify |
| 计划卡片 UI | 展示步骤、确认/取消 |
| 上下文组装 | 画布尺寸、当前工具、是否已有选区（一期可无选区） |
| 单测 | 校验器、环检测、未知工具 |

**验收**：输入「提高一点亮度并抠图」→ 出现两步计划 → 确认后依次完成。

---

### 第 4 期：文生图入口（约 3～5 天）

**目标**：创作页提示词 → 异步出图（mock 四张色块亦可）→ 进入编辑器。

**简化**：真实四宫格美观度不抠；先打通状态机。

---

### 第 5 期：选区与局部编辑（约 5～8 天）

**目标**：矩形/笔刷选区 + 局部调整；SAM 点选作为增强。

| 优先级 | 能力 |
|--------|------|
| P0 | 矩形选区 + 选区内 adjust |
| P1 | 笔刷 mask |
| P2 | SAM / 智能点选（模型体积大，虚拟机慎用） |
| P2 | 局部 inpaint / replace（依赖云端编辑模型） |

---

### 第 6 期：图层系统增强（约 5～8 天）

**目标**：主体/背景拆分；图层面板显隐、排序、简单变换。

**简化**：OCR 文字层、提升物体为图层可放到第 7 期。

---

### 第 7 期：部署硬化与 CentOS 验收（约 3～5 天）

| 任务 | 细节 |
|------|------|
| 多阶段 Dockerfile | 前端 build 打进 api 或独立 nginx |
| compose profile deploy | api + worker + 中间件 |
| `.env` 生产检查清单 | 密钥、公网/局域网 Endpoint |
| 在 node101 上完整拉起 | 浏览器从宿主机访问虚拟机 IP |
| 基础压测/日志 | `docker compose logs`、磁盘卷备份说明 |

---

### 第 8 期（可选增强）

- 营销图、批量处理  
- 完整 21 工具对齐  
- JWT 强化、用户空间隔离  
- Agent 失败重规划、评测集（原 `app/eval`）  
- 前后对比滑杆、完善撤销重做  

---

## 8. 简化与砍减清单（强烈建议一期执行）

| 原能力 | 一期建议 | 理由 |
|--------|----------|------|
| 21 种工具全量 | **先做 4～8 种** | 注册表设计对了，后续只是加插件 |
| SAM 智能点选 | **延后** | 模型与依赖重，虚拟机不友好 |
| OCR 文字层 | **延后** | 非主链路 |
| 营销图 / 批量 | **延后** | 独立业务页，不影响 Agent 故事线 |
| 完整多图层文档模型 | **先单图层** | 先跑通 Agent+工具 |
| 拓扑排序复杂依赖 | **先线性依赖（后一步依赖前一步）** | 覆盖 80% 自然语言指令 |
| MinIO | **可先本地存储** | 减一个容器，接口预留 |
| 登录注册 | **可延后** | demo 用默认用户 |
| 评测集 / 像素差分 | **三期** | 有主链路后再做回归 |
| LangSmith | **不做** | 本地日志即可 |
| 多 Agent 角色扮演 | **不做** | 本项目是「工具型单 Agent + 计划图」，不是法律多角色 |

---

## 9. API 草案（一期需冻结的最小集合）

> 路径前缀统一 `/api`。字段名在实现时以 OpenAPI 为准，此处定范围。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | db/redis/storage 状态 |
| POST | `/assets` | 上传图片 |
| GET | `/assets` | 列表 |
| POST | `/sessions` | 从 asset 创建编辑会话 |
| GET | `/sessions/{id}` | 会话详情（含文档） |
| POST | `/sessions/{id}/tools/{tool_name}` | 手动调用工具 |
| POST | `/sessions/{id}/agent/runs` | 提交自然语言，返回 plan |
| POST | `/sessions/{id}/agent/runs/{run_id}/confirm` | 确认执行计划 |
| GET | `/events/{run_id}` | SSE 进度 |
| POST | `/generations` | （第 4 期）文生图 |

---

## 10. 测试与质量策略

| 阶段 | 测试重点 |
|------|----------|
| 一期 | API 集成测（mock provider）、健康检查 |
| 二期 | ToolRegistry 单测、调色/几何结果冒烟 |
| 三期 | 计划校验单测、Agent mock 规划回归 |
| 部署期 | compose 冷启动、重启后数据仍在、跨机器访问 MinIO URL |

前端：关键路径手工验收清单即可；E2E（Playwright）放到增强期。

---

## 11. 风险与对策

| 风险 | 对策 |
|------|------|
| 画布交互范围过大 | 一期只保证显示/缩放/刷新；复杂选区二期 |
| CentOS 老旧导致 Docker 安装难 | 文档提供 Stream/8 优先；必要时升级访客系统 |
| 虚拟机内存不足 | 关 SAM；Worker 单并发；用 mock provider |
| DashScope 费用/额度 | 默认 mock；CI 永不打真实 Key |
| 范围膨胀 | 严格按第 7 章分期；新增需求进第 8 期池 |
| 前后端联调字段不一致 | 尽早生成 OpenAPI，前端用类型生成或手写 `types/api.ts` |

---

## 12. 里程碑与验收总表

| 里程碑 | 可演示内容 | 部署要求 |
|--------|------------|----------|
| M0 | 空壳 + health | 本机 |
| M1 | 上传 + 画布显示 | 本机 |
| M2 | 手动工具 + SSE | 本机 compose 中间件 |
| M3 | 自然语言计划→确认→执行 | 本机 |
| M4 | 文生图进编辑器 | 本机 |
| M5 | 选区局部编辑 | 本机 |
| M6 | 图层拆分基础 | 本机 |
| M7 | CentOS Docker 全量拉起 | **node101 验收** |

---

## 13. 下一步立即执行的工作（文档之后的第一刀代码）

1. 初始化/同步 `frontend/`（Vite + React 19 + TS + react-konva + Zustand）与 `backend/`（FastAPI + pyproject）。  
2. 添加 `deploy/docker-compose.yml`（postgres + redis）。  
3. 实现 `GET /api/health`。  
4. 前端首页显示「image100 / AI 修图智能体」并代理到后端。  
5. 再进入第 1 期资产上传。  

**在上述脚手架完成前，不要并行开发 SAM、营销图、批量处理。**

---

## 14. 附录：原仓库关键路径对照（便于对照阅读源码）

| 原路径 | 重构对应 |
|--------|----------|
| `frontend/src/**` (React) | 同栈保留，按期精简 |
| `backend/app/agent/graph.py` | 同名思想保留，可微调节点 |
| `backend/app/tools/*` | 保留注册表模式，削减数量 |
| `backend/app/providers/*` | 保留 mock/dashscope |
| `backend/app/routers/sessions.py` | 拆薄，逻辑下沉 services |
| `docker-compose.yml` | `deploy/docker-compose.yml`，增 CentOS 说明 |

---

## 15. 文档维护

| 变更类型 | 更新本文哪些章节 |
|----------|------------------|
| 增删工具 | 第 4.5、第 8、第 7 期计划 |
| 换模型厂商 | 第 3.2、第 5.1 Provider |
| 部署端口变更 | 第 6、README |
| 分期调整 | 第 7、第 12 |

需求分析的业务侧描述以《基于React与LangGraph的AI修图智能体平台项目需求》为准；**工程落地顺序以本文为准**。
