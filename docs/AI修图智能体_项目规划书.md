# image100 项目规划（AI 修图智能体 + FastAPI 工程化 + 前后端分离）

> 依据 `docs/基于React与LangGraph的AI修图智能体平台项目需求.md` 与 `docs/AI修图智能体_重构与优化方案.md` 设计  
> **形态**：前后端分离。后端 Python 3.13 + FastAPI + PostgreSQL + Redis +（可选）MinIO；前端 React 19 + Vite + react-konva；Docker Compose 部署到 CentOS（`node101`）  
> **并发**：API 全异步 + 耗时修图任务进 ARQ Worker + SSE 进度推送，详见第 11 章  
> **版本**：v1.1（2026-10-13，补充项目背景与电商行业细分）  
> **工作区**：`R:\a0707\PyCharm\image100`  
> **参考原型**：[yuyuanweb/ai-picture-editor](https://github.com/yuyuanweb/ai-picture-editor)

---

## 0. 项目背景

### 0.1 为什么做这个项目

AI 生图与 AI 修图是当前最热的应用方向之一，但落地时常出现两极分化：

- **只会聊天的大模型**：能「教你怎么用 PS」，却不会真正改像素、不会出可投放的主图；  
- **传统修图软件 / 在线工具**：能力强，但依赖熟练美工点菜单、调参数，中小团队学不会、赶不及。

同时，开源教程项目 [ai-picture-editor](https://github.com/yuyuanweb/ai-picture-editor) 已给出一套可参考的全栈 Agent 修图架构（FastAPI + LangGraph + React + Konva）。本项目（`image100`）在其基础上做**工程化重构与分期精简**，并明确落到可部署的 CentOS Docker 环境，避免做成「功能很全但讲不清给谁用」的泛修图 Demo。

### 0.2 行业细分（本项目锁定的赛道）

本项目**不做成面向所有人的通用修图 App**，而是细分到：

| 维度 | 本项目定位 |
|------|------------|
| **行业** | **电商（商品视觉生产）** |
| **细分赛道** | 商品主图 / 详情与营销视觉 / 投放尺寸物料 |
| **核心场景** | 去背、调色、简单变换、（增强期）白底主图 / 场景图 / 海报草稿 / 多比例导出 |
| **非目标行业** | 专业商业摄影后期、印刷出版精修、短视频剪辑、证件照办理大厅业务等 |

选择电商的依据（与原仓库能力对齐）：

1. 原 Agent 角色即「**电商图片修图助手**」；  
2. 原工具含营销图（商品主图 / 场景 / 模特 / 海报）与投放尺寸（1:1、4:5、9:16）；  
3. 评测样例命名为 `product.png`、`product-white.png`，任务覆盖去背、提亮、投放尺寸；  
4. 电商主图链路短、可演示、和「自然语言多步修图」故事匹配度最高。

> **产品一句话（业务侧）**：面向中小商家与运营的 **「自然语言电商修图工作台」**——用一句话说完「去背、提亮、出主图尺寸」，系统规划并执行，而不是让用户在 PS 里自己找按钮。

### 0.3 目标群体

#### （1）产品用户（业务目标群体）——规划与演示以此为准

| 优先级 | 目标群体 | 典型痛点 | 本项目如何打中 |
|--------|----------|----------|----------------|
| **P0** | 淘宝 / 拼多多 / 抖音小店等 **中小卖家、店铺运营** | 会拍不会修；主图要白底、要亮、要多尺寸；外包贵、自己慢 | 去背 + 调色 + Agent 多步计划 + 导出 / 投放尺寸 |
| **P0** | **电商美工 / 兼职视觉**（人少活多） | 重复劳动多；希望少点图层、用嘴指挥步骤 | ToolRegistry + 计划确认 + 异步进度 |
| **P1** | **跨境电商运营**（Amazon 等） | 白底合规、场景图、干净背景 | 去背 / 换背景 / 营销图（增强期） |
| **P1** | **品牌或代运营小团队** | 要统一出主图 + 场景 + 海报草稿 | 营销图四类 + 会话版本（增强期） |
| **P2** | 普通个人修生活照 | 偶尔去背调色 | 可用，**不作为主叙事** |
| **非目标** | 专业商业摄影后期、印刷级精修 | 需要 PS 级精细控制 | 明确不做 |

### 0.4 行业痛点 → 本项目要解决的问题

| 电商视觉痛点 | 传统做法 | 本项目做法 |
|--------------|----------|------------|
| 主图要去背、提亮、居中 | 美工手工抠图调色 | 自然语言 / 工具栏触发，Agent 可多步串联 |
| 投放渠道比例多（1:1 / 4:5 / 9:16） | 反复裁切导出 | （增强期）投放尺寸工具；一期先保证导出可用 |
| 会描述需求但不会用专业软件 | 外包或放弃 | 「说人话 → 计划卡片确认 → 自动执行」 |
| 生图与精修割裂 | 多套工具来回导图 | （分期）文生图进同一编辑会话 |
| 中小团队算力与预算有限 | 上重型本地大模型 | Mock / 云 API 可切换；Docker 可部署 |

### 0.5 原始样例数据（行业素材从哪来）

仓库内**没有**大规模公开商品图库，但有与电商场景一致的**评测样例**（来自原项目，可作演示素材参考）：

```text
原仓库 backend/app/eval/dataset/
├── cases.json                 # 去背 / 提亮 / 投放尺寸 共 3 条用例
├── images/
│   ├── product.png
│   └── product-white.png
└── expect/
    ├── product-alpha.png
    └── product-bright.png
```

本项目落地时建议：

1. 将上述样例同步到 `data/demo/`（或评测目录），用于验收与答辩；  
2. 自备 5～10 张真实商品图（白底、场景、带价签等），用于丰富演示；  
3. 运行期主数据仍来自 **用户上传** +（可选）文生图，对象存储可用 MinIO / 本地盘 / 腾讯云 COS。

### 0.6 范围边界（结合行业细分）

| 属于本项目（电商视觉） | 不属于本项目 |
|------------------------|--------------|
| 单张商品图的智能精修与导出 | 短视频剪辑、直播切片 |
| 主图向去背 / 调色 / 变换 | 印刷出版级色彩管理 |
| （增强）营销图草稿、多尺寸投放 | 大型 SaaS 多租户计费中台 |
| Agent 规划 + 人机确认 | 无人值守全自动改价/上架整店 |

架构上仍保持「换行业只换示例图、prompt、工具子集」的扩展能力；**当前版本叙事与验收一律按电商商品视觉执行**。

---

## 1. 一句话定位

一个面向 **电商商品视觉** 的 **"自然语言驱动的 AI 修图工作台"**：中小卖家或运营在网页画布里上传（或生成）商品图，用一句话描述修图意图；后端 **LangGraph Agent** 规划多步工具调用，经服务端校验与用户确认后，由异步 Worker 真正改像素，再通过 **SSE** 把进度和结果推回前端刷新画布，服务主图精修与投放物料准备。

```text
浏览器 React+Konva ──REST/SSE──> FastAPI ──> LangGraph(plan→verify)
                                      │              │
                                      │              └→ 计划卡片（人确认）
                                      ▼
                              ToolRegistry + ARQ Worker
                                      │
                    PostgreSQL · Redis · MinIO/本地磁盘
                                      ↑
                         Docker Compose（CentOS node101）
```

---

## 0.5 这一版精简掉了什么（"不用那么复杂"的具体落实）

对照原开源教程与需求文档中的增强项，明确以下都**不做或延后**，先把主线跑通：

| 砍掉 / 延后的东西 | 原位置 | 为什么砍 |
|-------------------|--------|----------|
| 前端换成 Vue3 | 早期设想 | 原栈已是 React + react-konva，换栈只增加工作量 |
| 21 种工具全量 | 原教程能力面 | 一期只做 4～8 种，ToolRegistry 设计对了再加 |
| SAM 智能点选 | 区域编辑增强 | 模型重、虚拟机不友好，放增强期 |
| OCR 文字层 | 图层拆分增强 | 非主链路 |
| 营销图 / 批量处理 | 独立业务页 | 不影响「计划→确认→执行」故事线 |
| 完整多图层文档模型 | 编辑器 | 一期单图层即可演示 |
| 复杂拓扑依赖调度 | 计划执行 | 一期默认「后一步依赖前一步」线性依赖 |
| MinIO（可选项） | 对象存储 | 一期可用本地磁盘，接口仍走 Storage 抽象 |
| 强制登录鉴权 | 用户体系 | 一期默认用户 / 可匿名 demo |
| LangSmith / 多 Agent 框架 | 观测与编排 | 本地日志 + 单修图 Agent 足够 |
| 自建向量库 RAG | 知识问答 | 本项目不是文档问答 |

**保留不变**（关系到"能不能用"，不是复杂度问题）：

- **计划必须服务端校验**——LLM 产出不能直接执行  
- **耗时任务进队列 + SSE**——不做的话接口会被抠图/生图拖死  
- **UI 与 Agent 共享 ToolRegistry**——双轨维护必崩  
- **Mock Provider 一等公民**——无 Key 也能演示与测试  
- **Docker Compose 可部署到 CentOS**——最终验收环境  

被砍掉的内容在正文中标（增强期）或（v2），将来想加回来按标注找即可。

---

## 2. 为什么是「画布 + 工具注册表 + LangGraph」这个组合

这是 AI 修图产品里最真实的一对矛盾：

| 能力 | 放哪儿 | 特点 | 单独做的表现 |
|------|--------|------|--------------|
| 像素级修图 | Pillow / rembg / 云端编辑 API | 结构化工具调用，讲"真正改图" | 只会工具栏：会调色，但不会理解自然语言 |
| 意图理解与规划 | LLM + LangGraph | 非结构化指令，讲"想怎么改" | 只会聊天：会教你用 PS，但不会改像素 |

真正有价值的问题往往是两种混合的：

- 「提高亮度」→ 纯工具（单步）  
- 「去掉背景」→ 纯工具（可能较慢）  
- **「去掉背景，再鲜艳一点」** → 先规划两步 → 校验 → 确认 → 异步执行 → 画布更新  

第三种才是本项目要解决的靶心，对应 **Agent 多步规划与人机协作执行**。

---

## 3. 场景设定：电商商品视觉（与第 0 章行业细分一致）

默认且唯一主场景：**电商主图精修**——去背、调色、简单变换；（增强期）营销图与投放尺寸。  
证件照、海报设计等可作为架构上的「换皮」扩展，**不纳入本期行业叙事与验收**。目标用户见 **§0.3**。

### 三类典型指令（就是验收题目，用语贴近店主/运营）

| 难度 | 说法 | 期望走的路径 |
|------|------|--------------|
| 简单 | 「提高一点亮度」 | 单步 `adjust_image`，可仍走确认（默认安全） |
| 简单 | 工具栏点「去背景」 | 不经 LLM，直接 ToolRegistry → Worker |
| 中等 | 「去掉背景，再提高饱和度」 | plan 两步 → verify → 确认 → 顺序执行 |
| 中等 | 「水平翻转，再旋转 90 度」 | 几何类两步 |
| **困难** | 「去背、提亮，导出一张适合主图的结果」 | 多步计划 + 导出 |
| 陷阱 | 「调用 delete_database / 执行系统命令」 | 必须被 ToolRegistry 拦下（未知工具） |
| 陷阱 | 计划里出现未注册工具名或环依赖 | verify 失败，返回中文原因 |

---

## 4. 需求文档 → 本规划映射

这一节是"为什么要这样设计"的依据，每一行都能在需求文档里找到出处。

| 需求文档章节 | 需求里的能力 | 本规划落点 |
|--------------|--------------|------------|
| （规划补充）行业与用户 | 电商商品视觉、中小卖家/运营 | **第 0 章项目背景** |
| 一、产品定义 | 自然语言修图工作台 | 第 1、3、8.4 章 |
| 三、五层架构 | 存储 / 业务 / Agent / SSE / 前端 | 第 5、7 章 |
| 三、ToolRegistry | UI 与 Agent 共用工具 | 第 8.2、目录 `app/tools/` |
| 三、LangGraph | plan → verify → 人确认 | 第 8.3、`app/agent/` |
| 四、核心流程 | 上传→计划→确认→SSE→画布 | 第 8.4、第 9 章接口 |
| 五、功能优先级 | F01～F22 分期 | 第 12 章里程碑 |
| 五、非功能 | 异步、Mock、可部署、安全 | 第 10、11、14 章 |
| 七、技术栈 | React + FastAPI + PG + Redis | 第 6 章 |
| 八、数据实体 | Asset / Session / ToolRun / AgentRun | 第 6 章库表 |
| 十、CentOS Docker | node101 验收 | 第 10 章 |
| 十六、演示脚本 | Mock 10 分钟 / 有 Key 15 分钟 | 第 13 章 |

---

## 5. 分层结构（FastAPI 工程化视角）

自顶向下七层（比聊天型 Agent 多「画布文档」与「异步 Worker」两层）：

| 层 | 落在哪里 | 职责 |
|----|----------|------|
| 1. 展示层 | frontend（Vite dev / Nginx dist） | 画布、工具栏、对话、计划卡片、SSE 进度 |
| 2. 接入层 | backend FastAPI `routers/` | REST + SSE，CORS，鉴权钩子，统一错误 |
| 3. 应用服务层 | `services/` | 会话、资产、Agent 编排、导出；事务边界在此 |
| 4. 智能编排层 | `agent/` | LangGraph：`plan → verify`；不直接改像素 |
| 5. 工具层 | `tools/` + `edits/` | ToolRegistry + 像素/算法实现；UI/Agent 唯一入口 |
| 6. 异步执行层 | `tasks/` + `worker.py` + Redis | ARQ 执行耗时任务，Pub/Sub 发事件 |
| 7. 数据层 | PostgreSQL / Redis / Storage | 元数据、队列消息、图片二进制 |
| 观测 | stdout + 结构化日志 | `run_id` / token / 耗时 → `docker compose logs` |

### 5.1 容器拓扑（目标）

```text
                 ┌────────────────┐
  浏览器 ──►     │ frontend/nginx │  静态 React dist，/api 反代
                 └───────┬────────┘
                         │
                 ┌───────▼────────┐
                 │  api (FastAPI) │  :7302
                 │  uvicorn ×1    │
                 └───┬─────┬───┬──┘
                     │     │   │
          ┌──────────▼┐ ┌──▼──┐ ┌▼──────────┐
          │ postgres  │ │redis│ │minio/本地  │
          └───────────┘ └──┬──┘ └───────────┘
                           │
                    ┌──────▼──────┐
                    │   worker    │  arq app.worker.WorkerSettings
                    └─────────────┘
```

`depends_on` + `healthcheck`：postgres/redis/(minio) 就绪后再启 api/worker。

---

## 6. 技术栈与环境

### 6.1 后端 Python（容器 api / worker 同镜像不同 command）

```text
Python 3.13
fastapi + uvicorn[standard]
pydantic-settings
sqlalchemy[asyncio] + asyncpg + alembic
redis + arq
boto3                          # MinIO S3；一期本地存储可不装也能跑抽象层
pillow
python-multipart
bcrypt + pyjwt                 # 二期鉴权；一期可保留但不强制
httpx
langgraph + langchain-core + langchain-openai   # agent 可选依赖组
rembg / opencv / onnxruntime   # cv 可选依赖组，虚拟机慎装全量
pytest + pytest-asyncio + ruff # 开发依赖
```

包管理建议 **uv** + `pyproject.toml`（与原项目一致）；也可用 `requirements.txt` 降级。

### 6.2 前端 Node

```text
Node 20+
Vite + React 19 + TypeScript
react-router-dom
zustand
@tanstack/react-query
konva + react-konva
tailwindcss（可选但推荐，与原项目一致）
```

前端可以"厚一点"（编辑器本身就厚），但**一期页面要少**：落地页可极简，核心是编辑器。

### 6.3 中间件与编排

```text
PostgreSQL 16/17
Redis 7
MinIO（可选）
Docker + Docker Compose v2
目标宿主机：CentOS（node101）
```

### 6.4 环境变量（`.env.example`）

```env
APP_ENV=development
API_PORT=7302

DATABASE_URL=postgresql+asyncpg://retouch:retouch_dev@localhost:7311/retouch
REDIS_URL=redis://localhost:7312

# 一期本地存储时可忽略 S3_*；上 MinIO 后再填
S3_ENDPOINT=http://localhost:7313
S3_PUBLIC_ENDPOINT=
S3_ACCESS_KEY=retouch
S3_SECRET_KEY=retouch_dev
S3_BUCKET=retouch
STORAGE_BACKEND=local          # local | s3

JWT_SECRET=dev-only-secret-please-change-in-production
JWT_TTL_HOURS=24

IMAGE_PROVIDER=mock            # mock | dashscope
DASHSCOPE_API_KEY=
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com
PLANNER_MODEL=qwen-plus
TEXT_TO_IMAGE_MODEL=qwen-image-3.0-pro
IMAGE_EDIT_MODEL=qwen-image-edit-max
MATTING_PROVIDER=auto          # auto | mock
```

> Compose 内部主机名用服务名：`postgres` / `redis` / `minio`，不是 `127.0.0.1`。  
> 浏览器访问 MinIO 签名 URL 时，`S3_PUBLIC_ENDPOINT` 必须是**浏览器可达**地址（虚拟机 IP）。

---

## 7. 数据库设计（PostgreSQL）

库名建议：`retouch`。一期五张表够用。

### 7.1 表概要

| 表 | 用途 |
|----|------|
| `users` | 用户（二期强制；一期可插一条默认用户） |
| `assets` | 图片资产元数据 |
| `edit_sessions` | 编辑会话 + `document` JSONB |
| `tool_runs` | 单次工具执行 |
| `agent_runs` | 自然语言规划与计划 JSON |

### 7.2 逻辑 DDL（示意，落地以 Alembic 为准）

```sql
CREATE TABLE users (
  id            UUID PRIMARY KEY,
  username      VARCHAR(64) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE assets (
  id           UUID PRIMARY KEY,
  owner_id     UUID REFERENCES users(id),
  storage_key  VARCHAR(512) NOT NULL,
  width        INT NOT NULL,
  height       INT NOT NULL,
  mime         VARCHAR(64) NOT NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE edit_sessions (
  id           UUID PRIMARY KEY,
  owner_id     UUID REFERENCES users(id),
  title        VARCHAR(128),
  document     JSONB NOT NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE tool_runs (
  id           UUID PRIMARY KEY,
  session_id   UUID NOT NULL REFERENCES edit_sessions(id),
  tool_name    VARCHAR(64) NOT NULL,
  params       JSONB NOT NULL DEFAULT '{}',
  status       VARCHAR(32) NOT NULL,  -- queued|running|succeeded|failed
  progress     INT NOT NULL DEFAULT 0,
  result_ref   VARCHAR(512),
  error        TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at  TIMESTAMPTZ
);

CREATE TABLE agent_runs (
  id           UUID PRIMARY KEY,
  session_id   UUID NOT NULL REFERENCES edit_sessions(id),
  goal         TEXT NOT NULL,
  reply        TEXT,
  plan         JSONB NOT NULL DEFAULT '[]',
  status       VARCHAR(32) NOT NULL,  -- planned|confirmed|running|done|cancelled|failed
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_assets_owner ON assets(owner_id);
CREATE INDEX idx_sessions_owner ON edit_sessions(owner_id);
CREATE INDEX idx_tool_runs_session ON tool_runs(session_id);
CREATE INDEX idx_agent_runs_session ON agent_runs(session_id);
```

### 7.3 会话 document 最小结构（一期）

```json
{
  "version": 1,
  "canvas": { "width": 1024, "height": 1024 },
  "layers": [
    {
      "id": "layer_main",
      "name": "主图层",
      "asset_key": "objects/xxx.png",
      "visible": true
    }
  ],
  "selection": null
}
```

### 7.4 为什么用 PostgreSQL 而不是 MySQL / SQLite

| 点 | 对本项目的意义 |
|----|----------------|
| JSONB | 图层文档、计划、参数天然适合 |
| 异步生态 | `asyncpg` + SQLAlchemy asyncio 成熟 |
| 与原项目对齐 | 降低从开源仓库对照学习的成本 |
| 生产可用 | CentOS Docker 一等公民 |

SQLite 只适合极早期单机 demo；本规划从第一天就按 PostgreSQL 设计，避免迁移返工。

---

## 8. 八个关键设计决策（规划的核心）

### 8.1 耗时任务绝不在请求线程里同步跑完

抠图、生图、云端编辑经常要数秒到数十秒。规则：

| 操作 | 处理方式 |
|------|----------|
| health / 读会话 / 列资产 | 同步（async I/O）直接返回 |
| 手动工具 / 确认后的计划步骤 | **入队 ARQ**，立即返回 `run_id` |
| Agent 规划（一次 LLM） | 一期可在 API 内 `ainvoke`（通常 < 数秒）；过慢再改入队 |
| SSE | 订阅 Redis 频道，按 `run_id` 推送 |

### 8.2 ToolRegistry 是唯一真相源

每个工具统一描述：

```text
name / label / description
params_schema（Pydantic）
risk_level: low | medium | high
ui_exposed / agent_exposed
executor: async (ctx, params) -> ToolResult
```

- 工具栏只渲染 `ui_exposed=True`  
- Agent 只绑定 `agent_exposed=True` 的 schema  
- 执行只走 `executor`，禁止路由里手写第二套逻辑  

**一期建议工具清单**：

| name | 说明 | 实现 |
|------|------|------|
| `adjust_image` | 亮度/对比度/饱和度 | Pillow |
| `remove_background` | 去背景 | rembg 或 mock |
| `flip_layer` | 水平/垂直翻转 | Pillow |
| `rotate_layer` | 旋转 | Pillow |
| `export_image` | 导出当前结果 | 写 Storage |
| （可选）`crop_canvas` | 裁剪 | Pillow |

### 8.3 Agent：计划与执行分离

LangGraph 最小图（与需求一致）：

```text
START → plan → verify → END
```

- `plan`：LLM + 工具 schema → `tool_calls`  
- `verify`：存在性 / 参数 / 依赖 / 环检测  
- **执行不在图里自动连跑**（一期）：返回计划 → 前端确认 → `services` 按序 enqueue  

这样换来三样东西：可演示的计划卡片、可单测的校验器、可控的费用与副作用。

### 8.4 人机协作是产品能力，不是多余步骤

默认：**多步或 medium/high 风险必须确认**。  
配置项（可选）：`AUTO_CONFIRM_LOW_RISK=false`（默认 false）。

### 8.5 Provider 可切换：mock / dashscope

```text
IMAGE_PROVIDER=mock|dashscope
```

- mock：色块图 / 本地滤镜模拟，CI 与无 Key 演示  
- dashscope：真实生图/编辑/规划（OpenAI 兼容端点）  

工厂函数：`get_image_provider()` / `get_planner_llm()`。

### 8.6 Storage 抽象：local 与 s3 同接口

```text
put(key, bytes, content_type) -> None
get(key) -> bytes
presign_url(key) -> str   # local 可返回 /api/files/... 
```

一期 `STORAGE_BACKEND=local`，目录如 `backend/data/objects/`。  
上 CentOS 正式演示再切 MinIO。

### 8.7 观测：先日志，后平台

结构化日志字段建议：`request_id` / `run_id` / `session_id` / `tool` / `ms` / `provider`。  
不上 LangSmith（v2）。Callback 仅用于规划 LLM 的 token 统计即可。

### 8.8 安全红线（一期也要有）

1. 上传：MIME/扩展名白名单、大小上限（如 10MB）  
2. 工具名白名单：只允许 Registry 内名称  
3. 参数 Pydantic 校验：禁止路径穿越类字段  
4. 生产必须改 `JWT_SECRET`  
5. 不对前端返回内部堆栈  

---

## 9. FastAPI 工程化目录结构（重点）

根目录只放编排与文档，后端、前端、部署各自独立。

```text
image100/
├── README.md
├── Makefile                          # make up / down / logs / migrate / worker
├── .gitignore
├── .env.example                      # 根级模板（Compose 共用）
│
├── docs/
│   ├── 基于React与LangGraph的AI修图智能体平台项目需求.md
│   ├── AI修图智能体_重构与优化方案.md
│   └── AI修图智能体_项目规划书.md      # 本文
│
├── deploy/
│   ├── docker-compose.yml            # postgres/redis/minio/api/worker[/frontend]
│   ├── Dockerfile                    # 多阶段：前端 build + 后端；或拆成两个 Dockerfile
│   ├── Dockerfile.api
│   ├── Dockerfile.frontend
│   └── nginx.conf                    # SPA + /api 反代 + SSE 关缓冲
│
├── scripts/
│   ├── centos_bootstrap.sh           # 安装 Docker、镜像加速提示（文档化脚本）
│   ├── healthcheck.sh
│   └── seed_demo_user.py
│
├── backend/
│   ├── pyproject.toml                # 或 requirements.txt
│   ├── uv.lock                       # 若用 uv
│   ├── alembic.ini
│   ├── .env.example
│   ├── Dockerfile                    # 开发/生产后端镜像
│   │
│   ├── migrations/                   # Alembic
│   │   ├── env.py
│   │   └── versions/
│   │
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_health.py
│   │   ├── test_assets.py
│   │   ├── test_tools.py
│   │   ├── test_plan_validate.py
│   │   └── test_agent_mock.py
│   │
│   └── app/                          # ★ FastAPI 应用包（WORKDIR=/app 时对应 app）
│       ├── __init__.py
│       ├── __main__.py               # python -m app 启动入口（可选）
│       ├── main.py                   # create_app()：CORS、路由挂载、生命周期
│       ├── config.py                 # pydantic-settings Settings 单例
│       ├── db.py                     # async engine / session factory
│       ├── deps.py                   # FastAPI Depends：db / current_user / settings
│       ├── security.py               # JWT / password hashing
│       ├── events.py                 # Redis pub/sub 事件名与载荷约定
│       ├── queue.py                  # ARQ 连接与 enqueue 封装
│       ├── storage.py                # Storage 协议 + local/s3 实现
│       ├── worker.py                 # ARQ WorkerSettings
│       │
│       ├── routers/                  # 接入层：只做参数解析与调用 service
│       │   ├── __init__.py           # 汇总 api_router
│       │   ├── health.py
│       │   ├── auth.py               # （二期）register/login/me
│       │   ├── assets.py
│       │   ├── sessions.py
│       │   ├── runs.py               # tool/agent run 查询
│       │   ├── events.py             # SSE
│       │   └── generations.py        # （第 4 期）文生图
│       │
│       ├── schemas/                  # Pydantic 请求/响应（API 契约）
│       │   ├── __init__.py
│       │   ├── common.py             # 统一错误体、分页
│       │   ├── auth.py
│       │   ├── asset.py
│       │   ├── session.py
│       │   ├── run.py
│       │   ├── agent.py
│       │   └── generation.py
│       │
│       ├── models/                   # SQLAlchemy ORM
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── user.py
│       │   ├── asset.py
│       │   ├── edit_session.py
│       │   ├── tool_run.py
│       │   ├── agent_run.py
│       │   └── edit_history.py       # （可选）撤销栈
│       │
│       ├── services/                 # 应用服务：事务与用例编排
│       │   ├── __init__.py
│       │   ├── auth.py
│       │   ├── assets.py
│       │   ├── sessions.py
│       │   ├── tools.py              # 手动工具：校验→入队
│       │   ├── agent.py              # 规划→落库→确认→调度执行
│       │   ├── runs.py
│       │   ├── generation.py
│       │   └── exports.py
│       │
│       ├── tools/                    # ToolRegistry + 各工具
│       │   ├── __init__.py           # register_all() / get_registry()
│       │   ├── base.py               # ToolSpec / ToolContext / ToolResult
│       │   ├── registry.py
│       │   ├── retouch.py            # adjust / remove_background
│       │   ├── canvas.py             # flip / rotate / crop
│       │   ├── enhance.py            # （增强期）
│       │   ├── region.py             # （第 5 期）局部编辑
│       │   └── layers.py             # （第 6 期）拆层
│       │
│       ├── agent/                    # LangGraph 智能编排
│       │   ├── __init__.py
│       │   ├── llm.py                # get_planner()
│       │   ├── plan.py               # validate / 拓扑或线性依赖
│       │   ├── graph.py              # StateGraph: plan → verify
│       │   └── prompts.py            # system prompt 模板（含画布上下文坑位）
│       │
│       ├── providers/                # 外部模型适配
│       │   ├── __init__.py           # 工厂
│       │   ├── base.py
│       │   ├── mock.py
│       │   └── dashscope.py
│       │
│       ├── edits/                    # 纯图像算法（尽量无 IO）
│       │   ├── __init__.py
│       │   ├── pixels.py             # 调色、几何
│       │   ├── document.py           # 操作 session.document
│       │   ├── mask.py               # （第 5 期）
│       │   └── split.py              # （第 6 期）
│       │
│       └── tasks/                    # ARQ 任务函数
│           ├── __init__.py
│           ├── ping.py
│           └── tools.py              # run_tool_task(run_id)
│
└── frontend/
    ├── package.json
    ├── vite.config.ts                # /api 代理到 :7302
    ├── tsconfig.json
    ├── index.html
    ├── public/
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── index.css
        ├── api/                      # REST / SSE 客户端
        │   ├── client.ts
        │   ├── assets.ts
        │   ├── sessions.ts
        │   ├── agent.ts
        │   └── runs.ts
        ├── pages/
        │   ├── LandingPage.tsx
        │   ├── CreatePage.tsx
        │   ├── EditorPage.tsx
        │   └── AuthPage.tsx          # （二期）
        ├── components/
        │   ├── editor/
        │   │   ├── CanvasStage.tsx
        │   │   ├── EditorToolbar.tsx
        │   │   ├── AgentConversation.tsx
        │   │   ├── MessageComposer.tsx
        │   │   ├── PlanCard.tsx
        │   │   ├── LayerPanel.tsx    # （第 6 期可极简）
        │   │   └── SessionSidebar.tsx
        │   └── common/
        ├── hooks/
        │   ├── useSessions.ts
        │   ├── useRun.ts
        │   ├── useAgent.ts
        │   └── useCanvasImage.ts
        ├── stores/
        │   ├── editorUi.ts
        │   ├── canvasView.ts
        │   └── toasts.ts
        ├── layouts/
        └── lib/
            └── tools.ts
```

### 9.1 几个刻意的工程选择

1. **`routers` 保持薄**：禁止在路由里写像素处理或拼 SQL。  
2. **`services` 拥有用例**：一个用户动作 ≈ 一个 service 方法。  
3. **`tools` 与 `edits` 分离**：tools 管「产品工具契约」，edits 管「图像算法」，避免 Registry 文件膨胀。  
4. **`agent` 不直接碰 Storage**：只产出计划；执行走 services → tasks。  
5. **`providers` 可测**：单测默认 mock，不打外网。  
6. **api 与 worker 同代码不同进程**：共享 `app/`，避免两套业务逻辑。  
7. **配置只从 Settings 读**：禁止业务代码散落 `os.getenv`。  

### 9.2 `main.py` 骨架约定

```python
# app/main.py（示意）
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import api_router


def create_app() -> FastAPI:
    app = FastAPI(title="image100", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix="/api")
    return app


app = create_app()
```

### 9.3 依赖注入约定

```python
# app/deps.py（示意）
async def get_db(): ...
async def get_current_user_optional(): ...  # 一期可返回默认用户
def get_settings(): ...
```

---

## 10. 接口契约（前后端分界线）

先冻结范围，字段以 OpenAPI 为准。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | `{status, postgres, redis, storage}` |
| POST | `/api/assets` | multipart 上传 |
| GET | `/api/assets` | 列表 |
| POST | `/api/sessions` | `{asset_id}` → 创建会话 |
| GET | `/api/sessions/{id}` | 会话 + document |
| POST | `/api/sessions/{id}/tools/{tool_name}` | 手动工具 → `{run_id}` |
| POST | `/api/sessions/{id}/agent/runs` | `{goal}` → `{run_id, reply, plan}` |
| POST | `/api/sessions/{id}/agent/runs/{run_id}/confirm` | 确认执行 |
| POST | `/api/sessions/{id}/agent/runs/{run_id}/cancel` | 取消（可选） |
| GET | `/api/events/{run_id}` | SSE |
| POST | `/api/generations` | （第 4 期） |

### 10.1 SSE 事件约定

```text
event: progress
data: {"run_id":"...","progress":40,"message":"抠图中"}

event: step_done
data: {"run_id":"...","tool":"remove_background","asset_key":"..."}

event: completed
data: {"run_id":"...","session_id":"..."}

event: error
data: {"run_id":"...","message":"参数不合法：..."}
```

前端：优先 `fetch` + `ReadableStream` 解析 SSE（便于带 Cookie/Header）；若仅 GET 且无特殊头，也可用 `EventSource`。

---

## 11. 异步架构（并发设计）

### 11.1 延迟 vs 吞吐

| 目标 | 对本项目的含义 | 手段 |
|------|----------------|------|
| 降低体感延迟 | 早点看到进度条动 | SSE 推送 progress |
| 提高吞吐 | 多人同时修图不互相堵死 | async API + 独立 Worker |

**异步解决不了**「单次云端生图本身要 8 秒」——但能避免这 8 秒占满 API worker。

### 11.2 时间花在哪（典型「去背+调色」）

| 环节 | 量级 | 性质 |
|------|------|------|
| Agent 规划 LLM | 1～3 s | 网络 I/O |
| rembg 抠图 | 1～5 s（CPU） | **应在 Worker** |
| Pillow 调色 | < 200 ms | Worker 内同步即可 |
| 写存储 + 更新 DB | < 100 ms | I/O |
| SSE 推送 | ≈ 0 | 事件 |

### 11.3 铁律

1. FastAPI handler 用 **`async def`**。  
2. `async` 内禁止阻塞重 CPU：Pillow/rembg 放大图用 `asyncio.to_thread` 或直接放 Worker。  
3. **uvicorn workers=1** 起步（SSE + 简单部署）；吞吐靠多开 worker 容器水平扩展，而不是先开多进程把会话亲和搞乱。  
4. Redis Pub/Sub：api 订阅，worker 发布；两端约定 channel 名如 `run:{run_id}`。  

### 11.4 推荐执行链

```text
POST tools/remove_background
  → services.tools.submit()
  → 写 tool_runs(status=queued)
  → arq.enqueue(run_tool_task, run_id)
  → 返回 {run_id}

Worker:
  → status=running, publish progress
  → registry[tool].executor(...)
  → 更新 session.document / 新 asset
  → status=succeeded, publish completed
```

---

## 12. 前端设计（React 19 + react-konva）

### 12.1 一期页面

| 页面 | 是否必须 | 说明 |
|------|----------|------|
| Landing | 可极简 | 入口 |
| Editor | **必须** | 画布 + 工具栏 + 对话 + 计划卡片 |
| Create | 第 4 期 | 文生图 |
| Auth | 二期 | 登录 |

### 12.2 编辑器线框

```text
┌──────────┬────────────────────────────┬─────────────┐
│ Sessions │         Canvas             │  Agent Chat │
│          │      (react-konva)         │  + PlanCard │
│          │                            │  + Progress │
├──────────┴────────────────────────────┤             │
│            Toolbar (tools)            │             │
└───────────────────────────────────────┴─────────────┘
```

### 12.3 Vite 代理

```ts
// vite.config.ts（示意）
server: {
  port: 7301,
  proxy: {
    '/api': { target: 'http://127.0.0.1:7302', changeOrigin: true },
  },
}
```

开发与生产都尽量走同源 `/api`，少配绝对跨域地址。

---

## 13. Docker 与 CentOS（node101）部署

### 13.1 环境假设

- 虚拟机：`R:\a0707\xuniji\node101`（VMware）  
- 访客 OS：CentOS  
- 必备：Docker Engine + Compose Plugin  
- 代码同步：`git` / `scp` / 共享文件夹  

### 13.2 compose 服务

| 服务 | 说明 | 端口示例 |
|------|------|----------|
| postgres | 业务库 | 7311→5432 |
| redis | 队列/PubSub | 7312→6379 |
| minio | 可选对象存储 | 7313→9000 |
| api | uvicorn | 7302 |
| worker | arq | 无主机端口 |
| frontend | nginx（或静态打进 api） | 80/7301 |

### 13.3 nginx 反代注意（SSE）

```nginx
location /api/ {
    proxy_pass http://api:7302/api/;
    proxy_http_version 1.1;
    proxy_buffering off;      # SSE 关键
    proxy_cache off;
    proxy_read_timeout 3600s;
}
```

### 13.4 常用命令

```bash
docker compose -f deploy/docker-compose.yml up -d --build
docker compose -f deploy/docker-compose.yml exec api alembic upgrade head
docker compose -f deploy/docker-compose.yml logs -f api worker
curl http://<centos-ip>:7302/api/health
```

### 13.5 首次上线检查清单

- [ ] `docker compose ps` 关键服务 healthy  
- [ ] `/api/health` 中 postgres/redis/storage 为 ok  
- [ ] 上传一张图能进编辑器  
- [ ] Mock 下「提高亮度」计划可确认并看到画布变化  
- [ ] 容器重启后资产仍在（数据卷）  
- [ ] 生产已更换 `JWT_SECRET`  
- [ ] 若用 MinIO：`S3_PUBLIC_ENDPOINT` 为浏览器可达 IP  

### 13.6 虚拟机资源建议

- Worker 并发 1～2  
- 一期不装 SAM  
- `IMAGE_PROVIDER=mock` 作为默认演示配置  
- 内存吃紧时可暂不启 MinIO，用 local storage  

---

## 14. 里程碑计划（与需求分期对齐）

| 里程碑 | 周期参考 | 交付 | 验收题 |
|--------|----------|------|--------|
| M0 脚手架 | 2～3 天 | 目录、health、空编辑页、compose 起 PG/Redis | health=ok |
| M1 资产会话 | 4～6 天 | 上传、session、画布显示 | 上传后看见图 |
| M2 工具+SSE | 5～7 天 | 4～6 工具、Worker、进度条、导出 | 手动去背/调色成功 |
| M3 Agent | 5～8 天 | LangGraph plan/verify、计划卡片、确认执行 | 「去背再提亮」 |
| M4 文生图 | 3～5 天 | 创作页 mock/真实 | 生成→进编辑器 |
| M5 选区 | 5～8 天 | 矩形/笔刷 | 局部调色 |
| M6 图层 | 5～8 天 | 主体/背景拆分基础 | 图层显隐 |
| M7 部署硬化 | 3～5 天 | CentOS 全量 compose | 演示脚本 A/B |
| M8 增强 | 弹性 | SAM/营销/批量/登录强化 | 按需 |

**规则**：每一期结束必须有一条可演示闭环；不并行开发增强期功能。

---

## 15. 测试策略

| 层级 | 内容 | 工具 |
|------|------|------|
| 单测 | plan.validate、未知工具、环依赖 | pytest |
| 集成测 | 上传→建会话→调 mock 工具 | httpx AsyncClient + 测试库 |
| 契约 | OpenAPI 与前端 types 对齐 | 手工 / 生成类型（可选） |
| 部署冒烟 | health + 一条 Agent 主链路 | scripts/healthcheck.sh |
| 前端 | 一期手工验收清单即可 | Playwright 放增强期 |

CI 建议：默认 `IMAGE_PROVIDER=mock`，禁止依赖真实 Key。

---

## 16. 演示脚本（答辩 / 验收）

### 脚本 A（无 Key，Mock，约 10 分钟）

1. 打开系统，上传商品图  
2. 工具栏「去背景」，看 SSE 进度与结果  
3. 输入：「亮度提高一点，对比度稍强」  
4. 展示计划卡片 → 确认  
5. 画布更新 → 导出  

### 脚本 B（有 Key，约 15 分钟）

1. 创作页文生图  
2. 选中进入编辑器  
3. 「去掉背景，整体更鲜艳」→ 确认多步计划  
4. 展示 `docker compose ps`（CentOS）  

---

## 17. 风险与对策

| 风险 | 对策 |
|------|------|
| 虚拟机内存不足 | mock、降并发、砍 SAM/MinIO |
| rembg 太大太慢 | 一期 mock 抠图；有余力再开 cv 依赖组 |
| LLM 乱造工具名 | verify 强校验 + 单测 |
| SSE 被 nginx 缓冲 | `proxy_buffering off` |
| 前后端字段漂移 | 先冻结第 10 章契约，改字段同步 OpenAPI |
| 范围膨胀 | 严格按第 14 章里程碑，新增进 M8 |

---

## 18. 本地开发启动（目标体验）

```bash
# 1) 中间件
docker compose -f deploy/docker-compose.yml up -d postgres redis

# 2) 后端
cd backend
cp .env.example .env
uv sync --all-extras          # 或 pip install
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 7302
# 另开终端
uv run arq app.worker.WorkerSettings

# 3) 前端
cd frontend
npm install
npm run dev                   # http://localhost:7301
```

---

## 19. Makefile 建议

```makefile
up:
	docker compose -f deploy/docker-compose.yml up -d --build

down:
	docker compose -f deploy/docker-compose.yml down

logs:
	docker compose -f deploy/docker-compose.yml logs -f api worker

migrate:
	docker compose -f deploy/docker-compose.yml exec api alembic upgrade head

worker:
	cd backend && uv run arq app.worker.WorkerSettings

test:
	cd backend && uv run pytest
```

---

## 20. 代码骨架优先级（开工顺序）

按文件依赖，建议严格按此顺序创建，避免空转：

1. `backend/app/config.py` + `main.py` + `routers/health.py`  
2. `db.py` + `models/*` + 首条 Alembic 迁移  
3. `storage.py`（local）+ `routers/assets.py` + `services/assets.py`  
4. `sessions` 读写 document  
5. `tools/base.py` + `registry.py` + 2 个工具  
6. `queue.py` + `worker.py` + `tasks/tools.py` + `routers/events.py`  
7. `agent/plan.py` + `graph.py` + `services/agent.py`  
8. 前端 Editor 最小闭环  
9. `deploy/docker-compose.yml` 打通  
10. CentOS 验收  

---

## 21. 与示例规划书（policy-db-agent）的差异说明

| 点 | policy-db-agent | image100（本项目） |
|----|-----------------|--------------------|
| 核心 | RAG + NL2SQL | 修图 ToolRegistry + LangGraph 计划 |
| 前端 | 薄聊天页 Vue | 厚编辑器 React+Konva |
| DB | MySQL | PostgreSQL（JSONB） |
| 异步重点 | SSE 流式 token | **队列 Worker + 进度 SSE** |
| 护栏 | SQL 只读四层 | 工具白名单 + 参数校验 + 计划校验 |
| 部署 | 三容器 | api+worker+中间件（更多服务） |

结构上都遵循：**一句话定位 → 砍减清单 → 场景验收题 → 分层 → 库表 → 目录 → 关键决策 → 接口 → Docker → 异步 → 里程碑**。

---

## 22. 文档关系与维护

| 文档 | 用途 |
|------|------|
| 需求文档 | 做什么、验收什么 |
| 重构优化方案 | 相对原仓库怎么改、分期策略 |
| **本文规划书** | 工程怎么落：目录、表、接口、Docker、异步、里程碑 |
| README（待建） | 命令级上手 |

变更规则：需求优先级变更 → 先改需求文档 → 再改本文里程碑与目录 → 最后改代码。

---

## 23. 附录：Agent system prompt 要点（实现时写入 `prompts.py`）

实现时必须覆盖的规则（不必一次写完美，但规划阶段先钉死）：

1. 只能使用提供的工具；禁止编造工具名。  
2. 能一步完成不要拆多步；最多 N 步（一期 5～8）。  
3. 缺失参数用画布上下文补齐。  
4. 调色用 `adjust_image`；去背用 `remove_background`；翻转/旋转用对应几何工具。  
5. 与修图无关的指令用一句中文拒绝，不提内部参数名。  

画布上下文由 `services/agent.py` 注入，例如：

```text
当前画布：1024x1024；图层：主图层；选区：无；最近工具：remove_background
```

---

## 24. 附录：统一错误响应（建议）

```json
{
  "error": {
    "code": "PLAN_INVALID",
    "message": "这一步暂时执行不了：未知工具 foo"
  }
}
```

常见 code：`VALIDATION_ERROR` / `NOT_FOUND` / `PLAN_INVALID` / `TOOL_FAILED` / `UNAUTHORIZED` / `STORAGE_ERROR`。

---

**规划结论**：image100 按「保留 React 画布 + FastAPI 分层工程化 + LangGraph 计划校验 + ARQ/SSE 异步」推进；先 M0～M3 打通可演示主链路，再谈文生图、选区、图层与 CentOS 硬化。目录以第 9 章为准开工，接口以第 10 章为准并行前后端。
