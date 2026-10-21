# image100 中的 LangChain、LangGraph 与 RAG

> **文档目的**：说明本仓库哪些 Python 文件使用了 LangChain / LangGraph / RAG，对应课件中的哪些概念，以及一次真实请求在后端如何一步步跑通。  
> **课件参考**：`R:\a0707\two_mdfile\learn\agent`、`R:\a0707\two_mdfile\learn\RAG`  
> **整理日期**：2026-10-21  

---

## 1. 总览：本项目用了什么、没用什么

| 能力 | 本项目做法 | 课件对应 | 刻意未做 |
|------|------------|----------|----------|
| LLM 调用 | `langchain_openai.ChatOpenAI` 走 DashScope OpenAI 兼容接口 | Agent《02-LangChain入门》《03-核心组件》Model I/O | 未用 LCEL 长链、未用 Memory |
| 工具绑定 | `bind_tools` + `convert_to_openai_function` | LangChain Tools / function calling | 未用 `@tool` 装饰器自动 Agent 循环 |
| 编排 | `langgraph.graph.StateGraph`：`plan → verify` | 《04-LangGraph入门》《06-七大架构》《09-Plan-Execute》《15-Graph-Workflow》 | 图内无 ReAct 循环、无 Multi-Agent |
| 人机回环 | **产品层** PlanCard + REST `confirm`，**不是**图内 `interrupt()` | 《05-HITL》思想对齐，实现路径不同 | 未使用 `interrupt` / `Command(resume)` |
| RAG | Indexing（切块+Embedding+Chroma）→ Search → Generate | RAG《04-Native_RAG》《03-向量数据库》 | 未做 Self-RAG / Corrective / GraphRAG / 多模态 RAG |
| 可观测 | LangSmith 环境变量开关 | LangChain 生态 LangSmith | 默认关闭，需 `.env` 开启 |

一句话：**修图 Agent = 课件「③ Plan&Execute」+「⑦ Graph 外壳」+「产品层 HITL」；客服 = 课件「Native RAG」极简版。**

---

## 2. 涉及的 Python 文件清单

### 2.1 Agent / LangGraph / LangChain（修图规划）

| 文件 | 角色 |
|------|------|
| `backend/app/agent/graph.py` | **LangGraph**：`StateGraph`，节点 `plan` → `verify`，`ainvoke` 入口 |
| `backend/app/agent/plan.py` | 计划校验（工具白名单、参数、依赖环），对应 Plan 后的「质检」 |
| `backend/app/agent/prompts.py` | System Prompt 模板（画布上下文注入） |
| `backend/app/providers/dashscope.py` | **LangChain**：`ChatOpenAI` + `bind_tools` 产出 tool_calls |
| `backend/app/providers/mock.py` | 无 Key 时关键词规则规划（答辩可演示） |
| `backend/app/providers/base.py` | 规划器工厂 `get_planner` |
| `backend/app/services/agent.py` | 用例：建计划落库、确认入队、**图外串行 Execute** |
| `backend/app/routers/agent.py` | HTTP：`POST .../agent/runs`、confirm、cancel |
| `backend/app/tasks/agent.py` | ARQ Worker：调用 `execute_plan_serial` |
| `backend/app/queue.py` | `enqueue_agent_plan` 入队 |
| `backend/app/models/agent_run.py` | `agent_runs` 表（goal / plan / status） |
| `backend/app/tools/registry.py` | Agent 可暴露工具列表（`agent_exposed`） |
| `backend/app/tools/canvas_ops.py` | 工具 `flip_layer`（翻转） |
| `backend/app/tools/retouch.py` | 工具 `adjust_image`（提亮） |
| `backend/app/observability.py` | LangSmith tracing 环境变量 |

### 2.2 RAG（工作台客服）

| 文件 | 角色 |
|------|------|
| `backend/app/rag/index.py` | Indexing：教程切块、`OpenAIEmbeddings`、`Chroma` 持久化 |
| `backend/app/rag/retrieve.py` | Search + Generate：相似度检索 / 关键词降级 → `ChatOpenAI` 流式回答 |
| `backend/app/rag/build_index.py` | CLI：`python -m app.rag.build_index` 重建索引 |
| `backend/app/routers/assistant.py` | `POST /api/assistant/chat/stream` SSE |
| `backend/app/main.py` | 启动 lifespan 调用 `ensure_index()` |
| `backend/app/config.py` | `VISION_MODEL` / `EMBEDDING_MODEL` / `RAG_PERSIST_DIR` 等 |

### 2.3 其它用了 LangChain、但不是 Agent/RAG 主路径

| 文件 | 用途 |
|------|------|
| `backend/app/services/copywriting.py` | 文案 SSE：`ChatOpenAI`（文本）+ 视觉模型看图 |
| `backend/app/services/prompt_variants.py` | 多图提示词改写：`ChatOpenAI` |

以上属于「单次 Chat 调用」，更接近课件 **① 单 Agent / Model I/O**，没有 LangGraph。

---

## 3. 架构怎么落地（对照课件）

### 3.1 七大架构里本项目站哪一格

课件《06-七大架构速览》里：

- **③ Plan & Execute**：先产出结构化步骤（`tool_name` + `params` + `depends_on`），再执行。  
- **⑦ Graph / Workflow**：用 `StateGraph` 把「规划」和「校验」固定成流水线节点。  
- **⑤ HITL 思想**：执行前必须人点确认——但实现是 **REST confirm + ARQ**，不是图内 `interrupt()`（《05》课件的 `Command(resume)`）。

**不是**：② ReAct（Thought→Action→Observation 自动循环）、⑤ Multi-Agent、⑥ Blackboard、④ Router+Skill。

### 3.2 修图 Agent 运行时拓扑

```text
前端编辑器输入 goal
        │
        ▼
POST /api/sessions/{id}/agent/runs
        │
        ▼
services.agent.create_agent_run
        │
        ├─ 组装画布 context（图层/选区摘要）
        │
        ▼
agent.graph.run_planner  【LangGraph】
   START → plan 节点 → verify 节点 → END
        │                │
        │                └─ plan.validate_plan（白名单/参数/环依赖）
        │
        ├─ plan 节点内：
        │     mock：关键词规则
        │     dashscope：ChatOpenAI.bind_tools → tool_calls  【LangChain】
        │
        ▼
落库 agent_runs（status=planned），返回 PlanCard
        │
用户点「确认」
        ▼
POST .../agent/runs/{id}/confirm
        │
        ▼
enqueue_agent_plan → Redis/ARQ Worker
        │
        ▼
execute_plan_serial  【图外 Execute】
   for step in plan.steps:
       invoke_tool(step) → 等 tool_run succeeded → 下一步
        │
        ▼
status=done，画布 document 已更新，前端 SSE/轮询刷新
```

要点（写进课件对照）：

1. **Planning 在图内，Execution 在图外**——图只负责「想清楚并校验」，真正改图走工具队列。  
2. **HITL 在产品层**：未确认的计划不会入队执行。  
3. **工具注册表**统一服务 UI 按钮与 Agent（`agent_exposed`），避免两套工具定义。

### 3.3 RAG 运行时拓扑（Native RAG）

课件《04-Native_RAG》三步：**Indexing → Search → Generate**。

```text
【Indexing】（启动 ensure_index / 手动 build_index）
  docs/电商商品视觉工作台使用教程.md
       │ RecursiveCharacterTextSplitter(chunk_size=600, overlap=80)
       ▼
  OpenAIEmbeddings(model=text-embedding-v3, DashScope)
       ▼
  Chroma 持久化到 data/rag_chroma（集合 workbench_guide）

【Search + Generate】（客服提问）
  POST /api/assistant/chat/stream
       │
       ▼
  similarity_search(question, k=4)   （无 Key 则关键词降级）
       │
       ├─ 域外 / 无命中 → 拒答固定句
       └─ 命中 → System+摘录+历史 → ChatOpenAI 流式生成
```

对照课件：

| 课件章节 | 本项目运用 |
|----------|------------|
| 《03-向量数据库》Embedding + 向量库 | DashScope embedding + Chroma |
| 《04-Native_RAG》Indexing/Search/Generate | 完整三步，知识源仅「使用教程」 |
| 《05–09》高级 RAG | **未实现**（无查询改写、无重排、无 Self/Corrective） |
| 《14-多模态 RAG》 | 客服 RAG 纯文本；看图在文案模块单独用视觉模型，不进 Chroma |

---

## 4. LangChain 用了哪些「零件」

来自课件《02》《03》：

| 组件 | 本项目用法 | 出现位置 |
|------|------------|----------|
| Chat Model | `ChatOpenAI`（兼容百炼） | dashscope / retrieve / copywriting / prompt_variants |
| Messages | `SystemMessage` / `HumanMessage` | 同上 |
| Tools / function calling | `bind_tools` + `convert_to_openai_function(Pydantic)` | `providers/dashscope.py` |
| Text Splitter | `RecursiveCharacterTextSplitter` | `rag/index.py` |
| Embeddings | `OpenAIEmbeddings` | `rag/index.py` |
| VectorStore | `langchain_chroma.Chroma` | `rag/index.py` / `retrieve.py` |
| LangSmith | 环境变量开关 | `observability.py` + `main.py` 启动配置 |

**没有用**：`create_react_agent`、ConversationMemory、RetrievalQA 一键链、LlamaIndex（课件多模态篇）。

---

## 5. 完整例子：前端输入「把图片翻转，然后提亮」

假设用户已在编辑器打开某张商品图，会话 id 为 `S`，规划器选 **DashScope（LLM）**（无 Key 时走 Mock，结论类似）。

### 5.1 前端

1. 用户在 Agent 输入框提交：`把图片翻转，然后提亮`。  
2. 前端请求：`POST /api/sessions/{S}/agent/runs`，body 大致为：

```json
{ "goal": "把图片翻转，然后提亮", "planner_provider": "dashscope" }
```

3. （若开启计费）先校验/扣除一轮 Agent 积分，再调规划接口。  
4. 收到 `status=planned` 与 `plan.steps` 后，展示 PlanCard，等待用户点「确认」。

### 5.2 后端：创建规划（LangGraph + LangChain）

**①** `routers/agent.py` → `services.agent.create_agent_run`：

- 读取 `EditSession.document`，拼出 context，例如：  
  `画布 800×800；图层：主图(layer_xxx,显)；当前层=layer_xxx；选区：无`  
- 作废同会话旧的 `planned` 计划。

**②** 调用 `agent.graph.run_planner(goal, context, planner_provider="dashscope")`：

LangGraph 状态（`AgentState`）：

```text
goal / context / planner_provider / plan / reply / error
```

图结构（课件 ⑦）：

```text
START ──► plan ──► verify ──► END
```

**③ `plan` 节点**（`graph._plan_node`）：

- `get_planner("dashscope")` → `DashscopePlanner.plan`  
- 构造 `ChatOpenAI(model=qwen-plus, base_url=DashScope兼容地址)`  
- `bind_tools([...])`：把 Registry 里 `agent_exposed=True` 的工具（含 `flip_layer`、`adjust_image` 等）转成 OpenAI function schema  
- System：`prompts.build_system_prompt(context)`（规则写明：提亮默认 brightness=0.2、能一步不拆、最多 6 步…）  
- Human：用户原句 `把图片翻转，然后提亮`  
- 模型返回 **tool_calls**（理想情况两步），例如：

```json
[
  { "tool_name": "flip_layer", "params": {} },
  { "tool_name": "adjust_image", "params": { "brightness": 0.2, "contrast": 0.0, "saturation": 0.0 } }
]
```

（若用 **Mock**：`mock.py` 看到「翻转」「提亮」关键词，也会按规则追加同样两步，顺序为先提亮后翻转——**LLM 与 Mock 顺序可能不同**；以实际返回的 `plan.steps` 为准。用户语义「先翻转再提亮」时，DashScope Prompt 通常按语序生成翻转→提亮。）

**④ `verify` 节点**（`plan.validate_plan`）：

- 工具名必须在 `list_agent_tools()` 白名单  
- 用各工具的 Pydantic `params_model` 校验参数  
- 缺省补上线性 `depends_on`：第二步依赖第一步  
- 检查环依赖、步数 ≤ 6  
- 生成默认中文回复，例如：`将按以下步骤执行：水平翻转 → 提亮。确认后开始。`

**⑤** 落库：

```text
agent_runs:
  goal = "把图片翻转，然后提亮"
  plan = { "steps": [ {id, tool_name, params, depends_on}, ... ] }
  status = "planned"
  planner_provider = "dashscope"
```

返回前端 → 用户看到计划卡片。**此时图片尚未被修改。**

### 5.3 用户确认 → 图外 Execute

**⑥** `POST /api/sessions/{S}/agent/runs/{run_id}/confirm`

- `status: planned → confirmed → running`  
- `enqueue_agent_plan(run_id)` 写入 ARQ 队列  

**⑦** Worker `tasks.agent.execute_agent_plan` → `execute_plan_serial`：

对上面两步 **严格串行**：

| 顺序 | tool_name | 做什么 | 落地代码 |
|------|-----------|--------|----------|
| 1 | `flip_layer` | 主图层水平镜像 | `tools/canvas_ops.py` → `pixels.flip_horizontal` |
| 2 | `adjust_image` | brightness=+0.2 | `tools/retouch.py` → `pixels.adjust_image` |

每一步：

1. `tools_service.invoke_tool(..., source="agent")` 创建 `tool_runs`  
2. 工具异步/同步执行，更新会话 `document`（图层像素/资源）  
3. `_wait_tool_succeeded` 轮询直到 `succeeded`  
4. 失败则整个 `agent_run` 标记 `failed` 并停止  

全部成功：`agent_run.status = done`。前端通过事件流或刷新会话看到翻转后且提亮后的图。

### 5.4 和课件 Plan&Execute 的对应关系

| 课件 Plan&Execute 阶段 | 本项目 |
|------------------------|--------|
| Planning | LangGraph `plan` 节点 + LLM/Mock |
| （额外）计划校验 | LangGraph `verify` 节点 |
| Human 确认 | REST confirm（课件 HITL 思想） |
| Execution | ARQ + `execute_plan_serial`（**不在图内**） |
| Synthesize | 弱化：用 `reply` 文案 + 画布结果，无单独「汇总 LLM」节点 |

---

## 6. RAG 例子：客服问「文案生成扣多少积分？」

1. 前端悬浮球 → `POST /api/assistant/chat/stream`。  
2. `ensure_index()`：若无 `.built` 标记则切块教程写入 Chroma。  
3. `similarity_search` 取 Top-K 教程片段（含计费说明）。  
4. `_looks_in_domain`：问题含「积分」等关键词 → 放行。  
5. `ChatOpenAI` 流式回答，System 限制「只能依据摘录、禁止编造」。  
6. 若问「今天股市怎么样」→ 域判断失败 → 只返回拒答固定句（课件里「垂直知识边界」的产品化）。

---

## 7. 配置与运维入口

| 项 | 说明 |
|----|------|
| `DASHSCOPE_API_KEY` | 规划 / Embedding / 客服生成共用 |
| `PLANNER_MODEL` | 默认 `qwen-plus` |
| `EMBEDDING_MODEL` | 默认 `text-embedding-v3` |
| `RAG_PERSIST_DIR` | 默认 `./data/rag_chroma` |
| `LANGSMITH_TRACING` | true 时 Agent/LLM 可进 LangSmith |
| 重建索引 | `cd backend && python -m app.rag.build_index` |
| 规划器切换 | 前端 Mock / LLM；接口 `GET /api/agent/planner-options` |

---

## 8. 学习对照：课件哪些「看过但没用」

便于答辩时说明「知道边界」：

- Agent《08-ReAct》：本项目不自动循环调工具，计划一次成型。  
- Agent《11-Multi-Agent》《12-CrewAI》《13-AutoGen》：单规划器，无多角色辩论。  
- Agent《05-HITL》的 `interrupt`：用 REST 确认代替图内暂停。  
- RAG《08-Self-RAG》《09-Corrective》《13-GraphRAG》《14-多模态》：客服保持 Native RAG + 拒答。  

这些不是缺陷，而是 **电商修图场景下的有意裁剪**：可控、可审计、可 Mock 演示、成本可控。

---

## 9. 相关交付文档

- `docs/电商商品视觉生产_v4交付说明.md`（Agent 首版）  
- `docs/电商商品视觉生产_v10交付说明.md`（LangSmith）  
- `docs/电商商品视觉生产_v12交付说明.md` / `v12_第十二版完成总结.md`（RAG 客服）  
- `docs/电商商品视觉工作台使用教程.md`（RAG 唯一知识源）  
