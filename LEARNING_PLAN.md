# 快速入门并实操 LangChain + LangGraph（前端 / PHP 背景专用）

> **你的轨道**：Python · 练习载体 = 用 LangGraph 重写 `virtual_rnd_center` 的 MVP 链路
> **时间预算**：5 周核心（约 55 小时）+ 按需扩展（每项 0.5–2 天）
> **API 基线**：`langchain 1.4.2`（2026-09-18）、`langgraph 1.2.12`（2026-09-21）。本文件的代码块均摘自官方文档当前版本，核对日 2026-09-22
> **配套示例**：`examples/` 目录 —— 每个概念一个能直接跑的浅显例子，**一半不需要 API Key**，默认走 Agnes 零配置，索引见第 16 节

---

## 1. 完整度复核：先看清整个战场

之前那版是"边聊边补"，必然漏。所以先建立**官方自己的分层**（这是选型的地图，不是营销话术）：

| 层 | 提供什么 | 什么时候用 | 同类产品 |
|---|---|---|---|
| **Runtime（运行时）** | 持久执行、流式、人机协同、持久化、底层控制 | 长跑、有状态、要精细控制 | **LangGraph**、Temporal、Inngest |
| **Framework（框架）** | 抽象与集成：agent loop、结构化内容块、中间件 | 快速起手、团队统一写法 | **LangChain**、Vercel AI SDK、CrewAI、OpenAI Agents SDK、Google ADK、LlamaIndex |
| **Harness（整套马具）** | 预制工具、预制提示词、子智能体、文件系统、Token 管理 | 更自主的 agent、复杂非确定性任务 | **Deep Agents SDK**、Claude Agent SDK、Manus |

> 来源：Concepts → Runtimes, frameworks, and harnesses（含"何时使用"与功能对照表）

**这解释了为什么必须学三层**：LangChain（框架）建在 LangGraph（运行时）之上，Deep Agents（马具）又建在 LangGraph 之上。只学最上面那层，你永远不知道出问题时该去哪一层修。

### 1.1 表面积矩阵（逐项对照本计划的覆盖情况）

| # | 能力面 | 本计划覆盖 | 深度 | 说明 |
|---|---|---|---|---|
| 1 | Agent Loop（机制） | 第 6.1 节 | ★★★ 手写 | 不可跳过的地基 |
| 2 | 模型调用 / 多厂商 / 网关 | 第 6.2 节 | ★★ | `init_chat_model` 一处切换 |
| 3 | 工具（Tool calling） | 第 6.2 节 | ★★ | 参数 schema 自动生成 |
| 4 | 结构化输出 | 第 6.3 节 | ★★★ | 替代正则解析 |
| 5 | 中间件（上下文/护栏/重试） | 第 6.4 节 | ★★★ | 你的 Express 心智直接复用 |
| 6 | **知识库 / RAG** | **第 8 节** | **★★★** | 含向量数据库、混合检索、重排、增量索引 |
| 7 | **向量数据库（生产）** | **第 8.3 节** | **★★★** | 选型 + pgvector 完整示例 |
| 8 | **状态数据库（checkpointer）** | **第 7.2 节** | **★★★** | Postgres / Mongo / Redis / SQLite |
| 9 | 短期记忆（thread 内） | 第 7.2 节 | ★★ | = checkpointer |
| 10 | 长期记忆（跨 thread） | 第 7.3 节 | ★★ | Store + 语义/情景/程序记忆三型 |
| 11 | 图编排（状态/边/分支/循环） | 第 7.1 节 | ★★★ | 你的 Redux 心智复用 |
| 12 | 人机协同（HITL） | 第 7.4 节 | ★★★ | `interrupt` / 审批中间件 |
| 13 | 流式输出 | 第 7.5 节 | ★★ | v3 事件流 |
| 14 | 时间旅行 / 复现 | 第 7.2 节 | ★★ | 调试长流程杀手锏 |
| 15 | 容错与长跑（持久执行） | 第 7.2、10.2 节 | ★★ | 失败恢复、pending writes |
| 16 | 子图与并行 | 第 7.1 节 | ◐ | 知道概念，用时查 |
| 17 | 多智能体四种模式 | 第 9.2 节 | ◐ | 你只需 custom workflow |
| 18 | **MCP（工具互操作）** | 第 9.1 节 | ★★ | `MCPAdapter`（beta） |
| 19 | **Deep Agents（马具层）** | **第 9.3 节** | ◐ | 知道它是什么、何时用 |
| 20 | 多模态（图/音/视频） | 第 9.4 节 | ○ | 需要时再学 |
| 21 | 沙箱与权限（跑代码/危险工具） | 第 9.5 节 | ★★ | 生产必需 |
| 22 | 评测（Evals） | 第 10.1 节 | ★★★ | 没有它所有优化都是猜 |
| 23 | 可观测性 / Trace | 第 5、10.2 节 | ★★ | 第一天就打开 |
| 24 | 测试（单元/集成） | 第 10.4 节 | ★★ | 工具先测 |
| 25 | 上下文工程 | 第 10.3 节 | ★★★ | 80% 效果问题在这 |
| 26 | 成本与缓存 | 第 10.5 节 | ◐ | 上限、退避、裁剪 |
| 27 | 前端接入（Generative UI） | 第 10.6 节 | ★★ | **你的主场** |
| 28 | 部署与本地服务 | 第 10.7 节 | ◐ | 图对了就能服务化 |
| 29 | 协议层：A2A / ACP | 第 9.6 节 | ○ | 只留入口 |
| 30 | TypeScript 轨道 | — | ✕ | 你已选 Python |
| 31 | 编辑器内智能体（VS Code 定制体系） | 第 15 章（附录B） | ★★ | BYOK / 指令 / MCP / Agent / Skill / Hook，配置即代码 |
| 32 | 浏览器 / computer-use | 第 15 章（阶段 2.5） | ◐ | API → DOM 自动化 → 视觉操作三层，能低不高 |
| 33 | 多智能体上下文契约 | 第 10 章 | ★★ | 交接包三件套 + 契约要测试，四种模式共同的真难点 |
| 34 | 模型路由与成本工程 | 第 11 章 | ★★ | 节点级路由 / 自动路由 / 缓存与批处理 |
| 35 | Agentic 评测（任务级） | 第 11 章 | ★★ | 轨迹断言：调对工具、轨迹有界、终态正确 |

★ 必学 ／ ◐ 知道即可、用时查 ／ ○ 暂不需要 ／ ✕ 明确不做

**明确不做的事**（写下来才不会被带跑）：不学 TypeScript 版、不深入 Generative UI 组件库、不碰 A2A/ACP、不用 CrewAI。

### 1.2 三条别走的路

1. **别从头学 Python**。你不缺编程能力，缺语法翻译，两天够（第 4 节）。
2. **别重学工程常识**。HTTP、JSON、Docker、Git、中间件分层**全部直接复用**。
3. **别从 LCEL 链开始**。`prompt | model | parser` 是语法糖，不是智能体。

**明确不学**：`AgentExecutor`、`initialize_agent`、`create_react_agent`（v1 起废弃）；旧 MCP 包 `langchain-mcp-adapters` 已被 `langchain.mcp.MCPAdapter` 取代。看到旧教程里有这几个词就关掉。

---

## 2. 你的存量技能 → 智能体概念的映射

| 你已经会的 | 对应物 | 说明 |
|---|---|---|
| **Redux / Vuex reducer** | **LangGraph reducer** | 几乎同一个东西：`(当前值, 更新) => 新值` |
| **Express / Laravel 中间件** | **LangChain Middleware** | 同名同概念，钩子点插逻辑 |
| TypeScript / Zod | **Pydantic / TypedDict** | schema + 运行时校验 |
| **Elasticsearch、SQL 全文检索** | **RAG 检索链路** | "建索引 → 查询 → 拼结果"就是 RAG 的前半段 |
| **MySQL / PostgreSQL 建模与迁移** | **向量库 + checkpointer** | pgvector 就是 Postgres 扩展，你上手最快 |
| Laravel Queue + Horizon | **checkpointer + 持久执行** | 别再用 Redis 自己拼一套 |
| 登录 session | **`thread_id`** | 一段会话的持久状态 |
| 第三方 HTTP API 对接 | **MCP** | 给工具定一套统一协议 |
| SSE / WebSocket | **event streaming** | 逐 token 回显 |
| Docker Compose | 直接复用 | 案例里就是这个 |
| `Promise.all` / npm / composer / Jest | `asyncio.gather` / `uv` / `pytest` | 一一对应 |

结论：你不是零基础，你是**换一套运行时 + 学一层新抽象**。

---

## 3. 时间总览

| 阶段 | 内容 | 时间 |
|---|---|---|
| 准备 | Python 差异 + 环境 | 2 天 |
| 开箱 | 跑通第一个 agent + 打开 trace | 1 天 |
| 第 1 周 | 机制层（手写 loop）+ LangChain 模型层 | 1 周 |
| 第 2 周 | 编排层 + **状态数据库** + 记忆 + HITL | 1 周 |
| 第 3 周 | **知识库 / RAG / 向量数据库** | 4–5 天 |
| 第 4 周 | 能力扩展（MCP / 多智能体 / Deep Agents / 沙箱） | 按需 |
| 第 5 周 | 工程层（评测 / 安全 / 测试 / 前端 / 部署） | 1 周 |
| 第 6 周 | 毕业项目：重写案例 MVP 链路 | 1 周 |

只有 3 周？见第 12 节的最小路径。

### 3.1 你的模型来源：Agnes 免费额度（零配置）

在 `examples/.env` 里填一行就能跑全部例子：

```bash
AGNES_API_KEY=sk-...
```

默认配置（代码里已经写好，不用改）：

| 项 | 值 |
|---|---|
| Base URL | `https://api.agnes-ai.cn/v1`（OpenAI 兼容，Bearer 认证；实测可用） |
| 默认模型 | **`agnes-2.5-flash`**（2026-09-23 实测：普通调用 0.5–8s、工具调用 0.6s） |
| 可选模型 | `agnes-3.0-flash`（⚠️ 2026-09-23 网关侧整段无响应，修好可用）、`agnes-2.5-pro`（⚠️ 免费额度 403） |

> **2026-09-23 实测的两个坑**：`agnes-3.0-flash` 会出现"连接通、请求收下、然后一个字不回"（连测 4 次全超时），
> 同一个 Key 调 `agnes-2.5-flash` 立刻正常；`agnes-2.5-pro` 在免费额度下直接 403。
> 二者都**不是你的配置问题**——遇到先换 `MODEL=agnes-2.5-flash`，再决定要不要继续排查。

**开工前先做一件事**——验证它会不会调用工具，这决定了你能不能做 agent：

```bash
uv run python examples/00_env_check.py --live
```

> **费用不再是约束，学法就要换。** 免费额度下你最该投资的是**质量**而不是省钱：
> 1. 每个例子跑三遍——agent 每次输出都不同，看多了才知道哪些是偶然
> 2. 做对照实验：换掉 `MODEL=` 各跑一遍同一个例子，比稳定性（免费额度有速率上限，连着跑会撞 429）
> 3. **每次改动都跑评测**（见 10.1）——别人因为烧钱而省略的这一步，你可以坚持做
> 4. 把重试上限、`max_iter` 设宽点，观察模型失败后怎么自己纠偏
> 5. 每个概念都**故意改坏一次**（摘揉 reducer、去掉 `thread_id`、写错 schema），看报错长什么样

> 来源：Agnes 官方文档（Overview / Quickstart / 各模型页）

---

## 4. Python 差异速成（2 天）

- [ ] 缩进即语法块、`def`/`class`/`self`
- [ ] 类型注解 + `Annotated` + `TypedDict` + `NotRequired`
- [ ] **Pydantic v2**（`BaseModel`、`Field`）≈ Zod
- [ ] **装饰器** `@tool` ≈ TS 装饰器 / PHP 8 属性
- [ ] `async def` / `await` / `asyncio.gather` / `async with`
- [ ] `with ... as ...`、推导式
- [ ] 包与导入、`uv run python -c "..."` 快速验证
- [ ] `.env` + `python-dotenv`（密钥绝不硬编码、绝不进仓库）
- [ ] 三个必踩的坑：**可变默认参数**、`is` 与 `==`、GIL（IO 密集用 async）

**产出**：`uv run python -c "from importlib.metadata import version; print(version('langchain'), version('langgraph'))"` 打印版本号。（实测：`langgraph` 没有 `__version__` 属性，不能用 `langgraph.__version__`。）

---

## 5. 第 0–1 天：开箱即用

```python
from langchain.agents import create_agent

agent = create_agent(
    model="claude-sonnet-4-6",          # 或 init_chat_model(...)，便于换任何兼容网关
    tools=[search_web],
    system_prompt="You are a helpful research assistant.",
)
result = agent.invoke({"messages": [{"role": "user", "content": "查一下 AI agent 的最新进展"}]})
```

> 来源：Releases → What's new in LangChain v1

**当天同时打开 trace**，比读十篇教程有用：

```bash
export LANGSMITH_TRACING="true"
export LANGSMITH_API_KEY="..."
```

> 来源：Build a semantic search engine（Configure LangSmith）

---

## 6. 第 1 周：机制层 + LangChain 模型层

### 6.1 ★ 手写 Agent Loop（本周最重要）

官方原话：`create_agent` 底层就是"调模型 → 让模型选工具执行 → 不再调工具就结束"的循环。自己写一遍（150–200 行）：

```python
from langchain.chat_models import init_chat_model
from langchain.messages import ToolMessage

model = init_chat_model("openai:gpt-4o", temperature=0)
model_with_tools = model.bind_tools([get_weather, search_web])

messages = [{"role": "user", "content": "北京今天多少度？"}]

for step in range(max_steps):                  # ★ 步数上限，否则死循环烧钱
    ai = model_with_tools.invoke(messages)
    messages.append(ai)
    if not ai.tool_calls:                      # ★ 终止条件
        break
    for call in ai.tool_calls:
        try:
            output = TOOLS[call["name"]].invoke(call["args"])
        except Exception as e:
            output = f"工具执行失败：{e}"        # ★ 失败要显式返回，不许伪造成功
        messages.append(ToolMessage(content=str(output), tool_call_id=call["id"]))
```

> 来源：Releases → What's new in LangChain v1（agent loop）；Interrupts（`bind_tools` 用法）；migration guide（`langchain.messages`）

必须自己实现的五件事：① 工具 schema 生成 ② 分发与异常兜底 ③ 终止条件（步数/token/循环检测）④ 上下文裁剪 ⑤ 可读 trace。

### 6.2 模型与工具

| 主题 | 关键点 |
|---|---|
| 模型 | `from langchain.chat_models import init_chat_model`；`init_chat_model("openai:gpt-4o", base_url=..., api_key=...)`，换网关只改这三个字段 |
| 消息 | `langchain.messages`：System / Human / AI / Tool；**对话历史就是消息列表** |
| 工具 | `from langchain.tools import tool, ToolRuntime`；`@tool` 参数 schema 自动生成 |
| 注入运行时 | `def greet(runtime: ToolRuntime[None, CustomState])` + `create_agent(state_schema=CustomState)` |

### 6.3 结构化输出（可靠交付）

```python
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

agent = create_agent("gpt-5.4-mini", tools=[weather_tool], response_format=ToolStrategy(Weather))
agent.invoke({"messages": [{"role": "user", "content": "SF 天气？"}]})["structured_response"]
```

- 结果在 `result["structured_response"]`；v1 已并进主循环，**不再多花一次 LLM 调用**
- 直接传 schema → 支持原生结构化输出的模型自动用 `ProviderStrategy`，否则退回 `ToolStrategy`
- `ProviderStrategy(schema, strict=...)` 需 `langchain>=1.2`；`ToolStrategy(schema, handle_errors=...)`

### 6.4 中间件

| 钩子 | 时机 | 你的直觉 |
|---|---|---|
| `before_agent` | agent 前一次 | 全局中间件 |
| `before_model` | 每次模型调用前 | 请求预处理 |
| `wrap_model_call` | 包住模型调用 | 重试/熔断/换模型 |
| `wrap_tool_call` | 包住工具调用 | 工具层兜底 |
| `after_model` | 每次返回后 | 响应校验、护栏 |
| `after_agent` | 结束后一次 | 收尾清理 |

```python
from langchain.agents.middleware import PIIMiddleware, SummarizationMiddleware, HumanInTheLoopMiddleware
middleware=[
    PIIMiddleware("email", strategy="redact", apply_to_input=True),
    SummarizationMiddleware(model="claude-sonnet-4-6", trigger={"tokens": 500}),
    HumanInTheLoopMiddleware(interrupt_on={"send_email": {"allowed_decisions": ["approve", "edit", "reject"]}}),
]
```

**两个版本坑**：v1 不支持把 `model.bind_tools(...)` 传给 `create_agent`；**`create_agent` 不支持 Pydantic 状态 schema**（状态只能 `TypedDict`）。

**本周产出**：① 双工具 agent（一个故意抛异常）② 模型工厂 ③ 结构化返回 ④ 手写 loop
**验收**：模型连续 3 次调用同一工具失败，谁负责终止？

---

## 7. 第 2 周：编排层 + 状态数据库 + 记忆

### 7.1 图与状态

```python
from typing import Annotated
from typing_extensions import TypedDict
from operator import add
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

class State(TypedDict):
    messages: Annotated[list, add_messages]     # reducer：追加而非覆盖
    round: int

builder = StateGraph(State)
builder.add_node("review", review_node)
builder.add_edge(START, "review")
builder.add_edge("review", END)
graph = builder.compile()                        # 必须先 compile
```

**reducer 是第一大坑**（你的 Redux 主场）：不写 = **默认覆盖**；累加用 `operator.add`；消息用 `add_messages`；想**清空**带合并 reducer 的字段必须 `Overwrite([])`（`from langgraph.types import Overwrite`）；输入输出可收窄（`input_schema=` / `output_schema=`）。

> 来源：Graph API overview（State / Reducers / Resetting a reducer field）

### 7.2 ★ 状态数据库（checkpointer）——这一节的答案就是"数据库"

短期记忆 = **状态被持久化到数据库**，而你只需要选后端。官方直接给了各家写法：

| 后端 | 包 | 导入 |
|---|---|---|
| 内存（开发/测试） | 内置 | `from langgraph.checkpoint.memory import InMemorySaver` |
| **PostgreSQL** | `langgraph-checkpoint-postgres` | `from langgraph.checkpoint.postgres import PostgresSaver`（异步：`.postgres.aio.AsyncPostgresSaver`） |
| **MongoDB** | `langgraph-checkpoint-mongodb` | `from langgraph.checkpoint.mongodb import MongoDBSaver`（异步：`.mongodb.aio.AsyncMongoDBSaver`） |
| **Redis** | `langgraph-checkpoint-redis` | `from langgraph.checkpoint.redis import RedisSaver` |
| SQLite（本地持久） | 官方提供 | `SqliteSaver` |

```python
from langgraph.checkpoint.postgres import PostgresSaver

DB_URI = "postgresql://postgres:postgres@localhost:5432/postgres?sslmode=disable"
with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
    # checkpointer.setup()          # 首次使用要建表
    graph = builder.compile(checkpointer=checkpointer)

graph.invoke(
    {"messages": [{"role": "user", "content": "hi, i am Bob"}]},
    {"configurable": {"thread_id": "1"}},          # ★ 相当于 session_id
)
```

> 来源：LangGraph → Memory → Add short-term memory（Postgres / MongoDB / Redis / 异步各版本示例）

**生产要点**（都是官方明确写了的）：
- **必须给 `thread_id`**，否则什么都不存、中断也无法恢复
- Postgres / Redis **首次要 `checkpointer.setup()`**
- `PostgresSaver` 的 `thread_id` 有列长度限制（**<255 字符**），用 UUID 或哈希
- **checkpoint 会无限增长**，要定期清理或设保留策略
- `InMemorySaver` 重启即丢，只能用于开发
- 子图有自己的 checkpoint 命名空间（`config["configurable"]["checkpoint_ns"]`），父子图状态互通要留意
- 不需要序列化的字段（数据库连接、缓存、大对象）用 `UntrackedValue`，不落盘

> 来源：Persistence / Checkpointers（含 troubleshooting 一节）

另外：`graph.get_state(config)` 读快照；`graph.get_state_history(config)` + `graph.update_state(config, values=..., as_node=...)` 做时间旅行与分叉。⚠️ 回放会**真的重调 LLM**，且会**重新触发 `interrupt`**。

### 7.3 记忆三型（长期记忆不要只会"存个向量"）

长期记忆 = 跨 thread、按 namespace 存，用 **Store**（`from langgraph.store.memory import InMemoryStore` → 生产换持久 store）。

官方给的分类框架（照抄这个概念，业务里就不会乱）：

| 记忆类型 | 存什么 | Agent 例子 |
|---|---|---|
| **Semantic**（语义） | 事实 | 关于用户的事实 |
| **Episodic**（情景） | 经历 | 过去做过什么操作 |
| **Procedural**（程序） | 规则/指令 | agent 的系统提示词 |

语义记忆的两种管理方式：**Profile**（一份持续更新的 JSON 文档，容易随规模增长而难维护）vs **Collection**（文档集合，召回率更高但删除/更新更难）。写入时机也有两种：**热路径**（agent 决定"记住"后再回答）vs **后台任务**（异步生成记忆）。

> 来源：Concepts → Memory overview；LangGraph → Memory

### 7.4 人机协同

```python
from langgraph.types import interrupt, Command

def review_node(state: State):
    approved = interrupt("代码审查是否通过？")     # 暂停并存档
    return {"verdict": "ok" if approved else "rework"}

graph.invoke(Command(resume=True), config)        # 同一 thread_id 恢复
```

三个必须记住的点：需要 checkpointer + 同一 `thread_id`；**恢复时中断所在节点从头重跑**（`interrupt()` 之前不能有副作用）；驱动会中断的图官方推荐 `stream_events(..., version="v3")`（`stream.interrupts` / `stream.interrupted` / `stream.output`）。Agent 场景直接用 `HumanInTheLoopMiddleware`。

> 来源：Interrupts（Pause / Resuming / Key points）

### 7.5 流式与两套 API

- 流式：`stream_events(input, config, version="v3")`；`stream.values` 看完整快照，`output_keys=[...]` 只订阅指定通道，`stream_mode="updates"` 只看增量
- **LangGraph 有两套 API**：Graph API（声明式建图）与 Functional API（`@entrypoint` / `@task` 函数式）。官方有专门选型页，别看到另一套就以为学错了

**本周产出**：带"条件边 + Postgres checkpointer + interrupt"的图，杀进程后同 `thread_id` 继续
**验收**：为什么不用再引入 Redis 做任务持久化？checkpoint 无限增长怎么办？

---

## 8. 第 3 周：知识库、RAG 与向量数据库

### 8.1 先做决策：到底要不要知识库

按这个顺序问，能省掉一半无用功：

1. **模型自己会不会？** 通用知识、写作、代码 → 不需要知识库
2. **要的是"内部/新鲜"知识？** → 需要
3. **语料多小？** 几十页以内 → 直接塞进上下文（长上下文 + 提示缓存），**别上向量库**
4. **是结构化数据？** 订单、用户、库存 → 用 SQL / Text2SQL 工具，**别把数据库向量化**
5. **要精确匹配/关键词？** 编号、报错码、法条 → 关键词检索（BM25/ES）往往比向量更强
6. **以上都不是** → 上向量检索（RAG）

### 8.2 三种 RAG 架构（先选架构，再写代码）

| 架构 | 检索时机 | 控制 | 灵活 | 延迟 | 适用 |
|---|---|---|---|---|---|
| **2-Step RAG** | 生成前**总是**先检索 | 高 | 低 | 快、可预测 | FAQ、文档问答 |
| **Agentic RAG** | **模型决定**何时/如何检索 | 低 | 高 | 波动 | 研究助手、多工具 |
| **Hybrid RAG** | 两者结合 + 校验环节 | 中 | 中 | 波动 | 需质量校验的领域问答 |

核心认知（官方原文大意）：**智能体要具备 RAG 能力，只需要给它一个能抓外部知识的工具**。RAG 在今天不是固定流水线，而是"给 agent 接一个检索工具"。

Hybrid 的典型组件：查询改写/扩写 → 检索结果相关性校验（不合格就改写查询重来）→ 答案与来源一致性校验。

> 来源：Retrieval（RAG architectures 表格 / 2-step / Agentic / Hybrid）

### 8.3 ★ 向量数据库：从本地到生产

**构建链路**（照抄官方教程）：

```bash
uv add langgraph langchain langchain-openai langchain-text-splitters beautifulsoup4 requests pypdf
```

```python
from langchain_core.documents import Document                       # page_content / metadata / id
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_core.vectorstores import InMemoryVectorStore

splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(chunk_size=100, chunk_overlap=50)
splits = splitter.split_documents(docs)

store = InMemoryVectorStore.from_documents(documents=splits, embedding=OpenAIEmbeddings())
retriever = store.as_retriever()
retriever.invoke("types of reward hacking")
```

**本地持久（开发够用）**：

```python
from langchain_chroma import Chroma
vector_store = Chroma(
    collection_name="example_collection",
    embedding_function=embeddings,
    persist_directory="./chroma_langchain_db",     # 落盘
)
```

**生产：pgvector（你已有 Postgres 经验，首选）**：

```python
from langchain_postgres import PGVector          # 包名 langchain-postgres

vector_store = PGVector(
    embeddings=embeddings,
    collection_name="my_docs",
    connection="postgresql+psycopg://langchain:langchain@localhost:6024/langchain",  # 只支持 psycopg3
    use_jsonb=True,
)
vector_store.add_documents(docs, ids=[doc.metadata["id"] for doc in docs])   # ★ 同 id 会覆盖
vector_store.delete(ids=["3"])
vector_store.similarity_search("kitty", k=10, filter={"id": {"$in": [1, 5, 2, 9]}})
vector_store.similarity_search_with_score(query="cats", k=1)
retriever = vector_store.as_retriever(search_type="mmr", search_kwargs={"k": 1})
```

起一个带 pgvector 的 Postgres 只要一行：

```bash
docker run --name pgvector-container -e POSTGRES_USER=langchain -e POSTGRES_PASSWORD=langchain \
  -e POSTGRES_DB=langchain -p 6024:5432 -d pgvector/pgvector:pg16
```

> 来源：PGVector integration（`langchain-postgres`）；Chroma 见 Build a semantic search engine

**元数据过滤（多租户 / 权限隔离的关键）**——PGVector 支持的操作符：

| 操作符 | 含义 | 操作符 | 含义 |
|---|---|---|---|
| `$eq` / `$ne` | 等于 / 不等于 | `$in` / `$nin` | 属于 / 不属于 |
| `$lt` / `$lte` | 小于 / 小于等于 | `$between` | 区间 |
| `$gt` / `$gte` | 大于 / 大于等于 | `$like` / `$ilike` | 文本 / 忽略大小写 |
| `$and` / `$or` | 逻辑与 / 或 | | |

多个字段无操作符时，顶层按 **AND** 处理。

> ⚠️ 官方明确提示：**pgvector 集成不支持 schema 变更的数据迁移**，改结构要重建表并重新灌数据。要提前想好这个代价。

### 8.4 检索质量：光有向量不够

提升检索质量的标准手段（官方 retrievers 目录里都有对应实现）：

| 手段 | 解决什么 | 代表实现（来自官方 retrievers 表） |
|---|---|---|
| **MMR** | 结果太相似、覆盖不全 | `as_retriever(search_type="mmr", ...)` |
| **元数据过滤** | 权限、租户、时间范围 | 上面那张操作符表 |
| **混合检索** | 关键词 + 向量各自会漏 | `MongoDBAtlasHybridSearchRetriever`、`ElasticsearchRetriever`（BM25 系） |
| **重排（Rerank）** | 召回够但排序差 | Cohere reranker、Pinecone rerank、Contextual AI reranker、`WatsonxRerank` |
| **Graph RAG** | 需要实体/关系推理 | `langchain-graph-retriever` |
| **Self-Query** | 用户查询里带结构化条件 | Self Querying（如 SAP HANA 示例） |
| 查询改写/多查询 | 用户问得不好 | Hybrid RAG 的 query enhancement |

> 来源：Retriever integrations（完整目录表）

**顺序建议**：先 相似度检索 → 加 MMR → 加元数据过滤 → 再加混合检索与重排。一次性全上你无法判断是谁起了作用。

### 8.5 增量更新：知识库不是一次性脚本（★ 新手最大盲区）

- **索引 API 的导入路径变了**：`langchain` 包里的 indexing API 与 retrievers 已迁到 **`langchain-classic`**（`from langchain_classic.indexes import ...`）。写增量索引前先确认导入路径，别照抄老博客
- 文档要**带稳定 id**（`add_documents(docs, ids=[...])`），同 id 会**覆盖**——这就是更新机制
- 需要自己决定：源文档改了怎么办（重新切分覆盖？按版本号并存？）、删了怎么办（`delete(ids=...)`）
- 大知识库要定期重建索引（embedding 模型换了就得全量重灌），并把"灌数据"做成独立可重跑的脚本，**不要写在 agent 运行时里**

> 来源：LangChain v1 migration guide（indexing / retrievers 的命名空间迁移）

### 8.6 把检索接进 agent

```python
from langchain.tools import tool

@tool
def retrieve_docs(query: str) -> str:
    """Search and return the most relevant internal documentation."""
    return "\n\n".join(doc.page_content for doc in _get_retriever().invoke(query))
```

LangGraph 版（用条件边做"文档相关度打分 → 通过就回答 / 不通过就改写问题重来"）：

```python
from langgraph.graph import MessagesState
from langchain.chat_models import init_chat_model

response_model = init_chat_model("openai:gpt-5.4-mini", temperature=0)

def generate_query_or_respond(state: MessagesState):
    response = response_model.bind_tools([retriever_tool]).invoke(state["messages"])
    return {"messages": [response]}
```

> 来源：Build a custom RAG agent with LangGraph（含 `GradeDocuments` 结构化打分与重试）

**省钱测试技巧**：用 `from langchain_core.embeddings import DeterministicFakeEmbedding` 跑测试，不消耗 embedding 额度。

### 8.7 评测检索质量（别只看"感觉变好了"）

最起码要能回答：**召回率**够不够（该被检索到的文档有没有出现）？**相关性**如何（返回的文档是否切题）？**答案是否 grounded**（有没有编）？官方有专门的"Evaluate a RAG application"教程，衡量 answer correctness / relevance / groundedness / retrieval quality。

**本周产出**：① 一个能跑的知识库灌数据脚本（可重跑）② 一个检索工具 ③ 一份检索质量记录（相似度 / MMR / 过滤 三档对比）
**验收**：你的知识库更新一条文档，需要几步？能不能只重跑一条？

---

## 9. 第 4 周：能力扩展（按需，每项 0.5–2 天）

### 9.1 MCP（工具互操作，★ API 刚换过）

**旧写法（`langchain-mcp-adapters` 的 `MultiServerMCPClient`）已被取代**，现在是 `langchain.mcp.MCPAdapter`，基于 FastMCP：

```bash
uv add "langchain[mcp]"        # 需要 langchain[mcp]>=1.4.0
```

```python
from langchain.agents import create_agent
from langchain.mcp import MCPAdapter

async def main():
    async with MCPAdapter("https://example.com/mcp") as adapter:
        tools = await adapter.list_tools()          # 自动发现远端工具
        agent = create_agent("claude-sonnet-5", tools)
        return await agent.ainvoke({"messages": [{"role": "user", "content": "..."}]})
```

transport 由 target 自动推断：

| target | 连接方式 |
|---|---|
| `"https://example.com/mcp"` | streamable HTTP（远程） |
| `Path("weather_server.py")` | 子进程 stdio（本地脚本） |
| 一个 FastMCP 实例 | 进程内，无子进程无 socket（**最适合写测试**） |
| `{"mcpServers": {...}}` | 一个 adapter 挂多个 server |

**两个警报**：`langchain.mcp` 是 **beta**（导入抛 `LangChainBetaWarning`，API 可能变）；`MCPAdapter` 会**拒绝**非 URL 字符串，防止把配置路径当命令启动子进程——别绕过。

**练习对象**：官方文档自己就是公开 MCP server（`https://docs.langchain.com/mcp`，免 key，含 `search_docs_by_lang_chain` 等工具），先拿它练手，不用自己写 server。

**什么时候用**：工具要被多个 agent/客户端共享，或要接别人现成的 server。自家调两个函数用 `@tool` 就够。

> 来源：Model Context Protocol (MCP)

### 9.2 多智能体：四种模式

| 模式 | 形态 | 何时用 |
|---|---|---|
| Subagents | 主 agent 调度子 agent | 任务可明显分工 |
| Handoffs | agent 间交接控制权 | 客服分诊 |
| Router | 先分类再路由 | 多来源知识库 |
| **Custom workflow** | **自己用 LangGraph 显式建图** | **你的案例** |

阶段明确、要人工卡点、要能重工的场景，**显式建图比自由交接可控**。

> 来源：LangChain → Multi-agent；概念对比见 LangGraph → Workflows and agents

### 9.3 Deep Agents（马具层）：知道它存在、知道何时用

它是"电池已装好"的 agent 骨架，内置四件事：**规划**（待办清单）、**委派**（子智能体）、**文件系统**（可插拔存储后端）、**Token 管理**（历史摘要 + 大工具结果驱逐）。适合长跑、多步、需要规划分解的任务。

**什么时候不用它**：你要的是"确定性的业务流程 + 人工卡点"（比如你的案例），自己建图更可控。**什么时候考虑**：做研究型/写作型/数据分析型 agent，需要大量探索与自我规划时，从它起手比从零搭快得多。

> 来源：Concepts → Runtimes, frameworks, and harnesses；Deep Agents → overview / quickstart / rag / memory / skills / subagents

### 9.4 多模态（需要时再学）

Deep Agents 与 LangChain 都支持多模态输入输出（图片、语音）。做"看设计稿生成代码""读截图修 bug"这类需求时再深入。

### 9.5 沙箱与权限（生产必需）

**只要 agent 能执行代码或改文件，安全就是第一问题**：
- 隔离执行：远程沙箱（官方列了 LangSmith、AgentCore、Daytona、Modal、Runloop、Vercel、E2B 等）
- 权限：文件/命令级审批（Deep Agents 有专门的 Permissions、Approval modes；LangChain 侧用 `HumanInTheLoopMiddleware`）
- 你的老本行：路径白名单、只读挂载、最小权限、审计日志

> 来源：Deep Agents → Sandboxes / Permissions / approval modes；LangChain → Middleware（HumanInTheLoopMiddleware）

### 9.6 协议层（只留入口）

A2A（Agent-to-Agent）与 ACP（Agent Client Protocol）用于跨系统互通。现在只需要记住名字和出处，等真的要多系统协同时再学。

> 来源：Deep Agents → A2A server / Agent Client Protocol (ACP)

---

## 10. 第 5 周：工程层

### 10.1 评测（没有它，所有"优化"都是猜）

固定用例集 + 每次改 prompt/换模型都跑。官方有 Agent Evals 专题；RAG 另有一套指标（correctness / relevance / groundedness / retrieval quality）。

> 来源：LangChain → Test → Agent Evals；LangGraph → Test

### 10.2 可观测性

LangSmith tracing 第 0 天就该打开。生产还可用它做数据集、实验对比、在线评测与监控。别用 `print` 调试 agent。

### 10.3 上下文工程（80% 的效果问题在这层）

在正确的时刻把正确的信息给模型：裁剪消息、摘要压缩（`SummarizationMiddleware`）、按需检索、动态注入（`@dynamic_prompt` + 运行时上下文）、把大产物挪出上下文（Deep Agents 的"大工具结果驱逐"就是这个思路）。**别靠把 prompt 写长来修 bug。**

> 来源：LangChain → Context engineering in agents；Deep Agents → Context engineering

### 10.4 测试

单元测工具（纯函数最好测）、集成测整条图、用 `DeterministicFakeEmbedding` 测索引链路。官方有 unit / integration testing 专页。

### 10.5 成本、限流与容错

你用的是免费额度，所以这里不教你省钱，只教你**别把系统跑崩**：

- **步数与重试必须有硬上限**：免费不等于无限，循环卡死的是你的时间
- 长任务靠持久执行：失败恢复、pending writes 不重跑已成功的节点
- 超时与退避：网关偶发失败要重试，但要区分“可重试”与“必须人工介入”
- 统计每轮 token：不是为了省钱，是为了知道**上下文在哪一步失控**

> 来源：LangGraph → Fault tolerance / errors（如 `GRAPH_RECURSION_LIMIT`）

### 10.6 前端接入（你的主场）

Generative UI（受控/声明式/开放式）、AI Elements、`assistant-ui`、CopilotKit、工具调用的 UI 呈现、结构化输出渲染、人工审批 UI、消息队列、断线重连流（join & rejoin）、reasoning token 展示、分支对话、时间旅行 UI。
两个开箱工具：**Agent Chat UI**（现成聊天界面）、**LangSmith Studio**（可视化调试你的图，**建议第 2 周就装**）。

### 10.7 部署

本地服务、部署、服务端 API（threads / assistants / runs、后台运行、定时任务）都有官方页。图写对了就能被服务化，先不用深挖。

### 10.8 安全（必须真改代码）

- 工具参数当不可信输入：路径沙箱、**绝不 `shell=True` 拼模型字符串**、高危操作走审批
- **禁止假成功**：案例里 `docker_mcp_tool.py` 失败时返回伪造的 `RUNNING (healthy)`，是标准反面教材
- 输入侧 `PIIMiddleware` 脱敏，输出侧结构/事实校验
- 重工与步数**必须有硬上限**，超限转人工而不是硬闯

---

## 11. 第 6 周：毕业项目——用 LangGraph 重写案例的 MVP 链路

原案例链路：`需求访谈 → 需求文档 → 架构+代码 → 代码审查 → 部署 → 接口测试 → 裁决 →（不过）重工`。三个毛病一起解决：

| 原问题 | 你要怎么做 |
|---|---|
| 正则扫 Markdown 关键词判定成败 | `response_format` + Pydantic `Verdict` |
| 无持久化，重跑从头来 | `compile(checkpointer=SqliteSaver(...))` + `thread_id` |
| 失败返回伪造成功状态 | 显式失败，交条件边处理 |

**状态草案**：

```python
from typing import Annotated
from typing_extensions import TypedDict
from operator import add
from pydantic import BaseModel, Field

class Verdict(BaseModel):
    """一次评审的结构化结论。"""
    passed: bool = Field(description="是否通过")
    reasons: list[str] = Field(description="不通过的具体原因，通过则为空")

class RndState(TypedDict):
    requirement: str
    boundary: str                        # 边界清单文件路径
    verdicts: Annotated[list[str], add]  # 每轮结论，追加
    round: int
    max_rounds: int
    artifact_dir: str
```

**节点清单**：`interview`（interrupt 问人类二元问题）→ `write_boundary` → `write_requirements` → `generate_code` → `code_review` → `deploy` → `qa_test` → `gate`（条件边）→ `rework` / `finalize`。

**九条硬要求**：
1. 三方判定全部用结构化输出，**禁止正则扫报告**
2. `compile(checkpointer=SqliteSaver(...))`，跑一半 Ctrl+C，重启后同 `thread_id` 继续
3. 达到 `max_rounds` 路由到 `interrupt()` 人工决策，而不是硬闯或死循环
4. 重工阶段**跳过需求访谈**，只重跑"代码→审查→部署→测试"（原案例这点做得对）
5. 工具失败显式失败，不许伪造成功
6. **加一个知识库节点**：把历史评审意见/编码规范灌进向量库，重工时检索"上次为什么被拒"作为上下文；灌数据脚本可重跑
7. **加检索质量记录**：至少对比 相似度 / MMR / 元数据过滤 三档
8. **接一个 MCP 工具**（可先用官方文档 MCP server 练手）
9. 附评测脚本：3 条固定需求 × 断言（产物存在、最终通过、轮数 ≤ 上限）

---

## 12. 如果只有 3 周（最小路径）

砍掉：MCP、多智能体、Deep Agents、多模态、沙箱、前端接入、部署、长期记忆、混合检索与重排。
保留：手写 loop → 图 + checkpointer + interrupt → 结构化输出 → 基础 RAG（相似度 + 元数据过滤）→ 毕业项目 → 评测脚本。
**一个都不能砍的**：手写 loop、checkpointer、结构化输出、上下文裁剪、评测。

---

## 13. 案例对照表（读原代码时用）

| 原案例（CrewAI） | 在解决什么 | LangGraph 对应物 |
|---|---|---|
| `@CrewBase` + `agents.yaml` | 角色声明式配置 | 节点函数 / `create_agent(system_prompt=...)` |
| `@start` / `@listen` | 事件回调编排 | `START` / `add_node` / `add_edge` |
| `@router` 返回字符串标签 | 条件路由 | `add_conditional_edges` |
| `RndState`(Pydantic) | 跨步骤状态 | `TypedDict` + reducer |
| `human_input=True` / TTY 菜单 | 人工闸门 | `interrupt()` + `Command(resume=...)` |
| `max_reworks=3` | 防死循环 | 条件边 + 计数器（超限转人工） |
| 只删报告不删源码 | 断点续跑、增量重工 | checkpointer + 复用 `thread_id` |
| `Context=[]` + 落盘传参 | 上下文最小化 | 状态只放引用 + 摘要压缩 |
| `_read_verdict_from` 扫关键词 | ⚠️ 反面教材 | `response_format` + `structured_response` |
| 失败返回 `RUNNING (healthy)` | ⚠️ 反面教材 | 抛异常 / 显式失败态 |
| `shell=True` 拼模型字符串 | ⚠️ 反面教材 | 参数白名单 + 沙箱 + 人工审批 |

设计说明：`virtual_rnd_center/virtual_rnd_center_presentation.md`。

---

## 14. Web 开发者特有的坑

- **拿写接口的思维写 agent**：节点碎成十几个，每次都要过模型，又慢又贵。节点是"一个决策"，不是"一个函数"
- **用正则解析模型输出**：JSON.parse 的既视感，但自然语言不是 JSON
- **想自己搭持久化**：Laravel Queue 的肌肉记忆会让你再写一套，checkpointer 已经做了
- **把数据库向量化**：结构化数据用 SQL / Text2SQL，别硬上向量库
- **知识库当一次性脚本**：没有增量更新与重灌脚本，三个月后没人敢动它
- **在中断点之前写副作用**：恢复会重跑那段
- **在 prompt 里堆规则**：改用上下文编排
- **为了架构好看上 MCP / 多智能体**：一个 `@tool` 能解决的事别上协议

---

## 15. API 自查（每次写代码前两分钟）

```bash
uv run python -c "from importlib.metadata import version; print(version('langchain'), version('langgraph'))"
```

1. **文档索引**（找页面最快的入口）：`https://docs.langchain.com/llms.txt`，分栏索引如 `/oss/python/langchain/llms.txt`、`/oss/python/langgraph/llms.txt`、`/oss/python/deepagents/llms.txt`
2. 迁移指南：`/oss/python/migrate/langchain-v1`、`/oss/python/migrate/langgraph-v1`
3. 查签名：`https://reference.langchain.com/python/langchain`
4. 版本行为：`langchain>=1.1` 结构化输出策略按模型 profile 自动选择；`ProviderStrategy.strict` 需 `>=1.2`；`langchain.mcp` 需 `>=1.4.0` 且为 beta
5. **判断教程死活**：搜 `AgentExecutor` 或 `MultiServerMCPClient`。有 = 过时

---

## 16. 配套示例索引（可直接跑）

概念光看懂没用，必须手上有能跑的东西。`examples/` 里每个概念配一个小例子，用同一个日常场景（咖啡店）贯穿。

### 16.1 先跑这五个：不需要 API Key

```bash
uv venv && uv add langgraph langchain-core langchain-text-splitters langgraph-checkpoint-sqlite
uv run python examples/00_env_check.py
```

| 文件 | 讲义章 | 对应概念（本计划节号） | 观察点 |
|---|---|---|---|
| `00_env_check.py` | 00 | 环境基线（§15） | 你装的版本 + 新版 API 是否存在 |
| `05_graph_basics.py` | 05 | reducer / 条件边（§7.1） | 覆盖 vs 累加 vs `Overwrite` 的差别；路由函数怎么写 |
| `06a_persistence_resume.py` | 06 | 状态数据库（§7.2） | **分两次运行**：关掉进程后状态还在（真落盘） |
| `07a_human_approval_offline.py` | 07 | 人工中断（§7.4） | 程序停半路等人回答；恢复时节点从头重跑 |
| `08a_index_offline.py` | 08 / 09 | 索引 / 过滤（§8.3–8.5） | 切分、元数据过滤、同 id 覆盖、删除——不花钱 |

### 16.2 再跑这些：需要一个模型 Key

```bash
uv sync                                      # 依赖已在根目录 pyproject.toml 里写好了
cp examples/.env.example examples/.env      # 填 AGNES_API_KEY=...
uv run python examples/00_env_check.py --live   # 先确认会调工具
uv run python examples/02_hello_agent.py
```

| 文件 | 讲义章 | 对应概念 | 观察点 |
|---|---|---|---|
| `02_hello_agent.py` | 02 | create_agent（§5） | 15 行就能干活；打印消息轨迹看它做了什么决定 |
| `03_handwritten_loop.py` | 03 | **手写 loop（§6.1）** | 框架到底替你兜了什么 |
| `04_structured_output.py` | 04 | 结构化输出（§6.3） | 口语下单 → Pydantic 对象，告别正则 |
| `06b_memory_agent.py` | 06 | 短期记忆（§7.2–7.3） | 换 `thread_id` 立刻失忆 = 多用户隔离 |
| `06c_long_term_memory.py` | 06 | **长期记忆（Store）**（§7.3） | 先看 Store 四个动作；再看 agent 换 thread 后依然记得同一个人 |
| `07b_hitl_graph.py` | 07 | 图 + 人工审批（§7.4） | 小额自动、大额挂起等人点头 |
| `08b_rag_agent.py` | 08 | RAG（§8.6） | 知识库没有的问题，它该说不知道而不是编 |
| `10_mcp_docs_server.py` | 10 | MCP（§9.1） | 不写工具，直接接官方文档 server |
| `12_mini_project_coffee_shop.py` | 12 | **完整小项目** | 状态机 + 结构化输出 + 知识 + 人工 + 记忆拼在一起 |

一键全跑（跑完给结果表，改动后重跑等于回归测试）：

```bash
uv run python examples/run_all.py            # 两组都跑
uv run python examples/run_all.py --offline  # 只跑离线组
uv run python examples/run_all.py --only 06  # 只跑第 06 章那一组（06a/06b/06c）
```

### 16.3 关于示例的说明

- 全部文件已在 `langchain 1.4.2` / `langgraph 1.2.12` / Python 3.13 上**实测通过**（网关 `https://api.agnes-ai.cn/v1`）：离线组 5/5，需要 Key 的组 9/9。一键回归：`uv run python examples/run_all.py`。
- 所有“需要 Key”的例子都从环境变量读模型配置，**换任何 OpenAI 兼容网关都不用改代码**（`MODEL` / `MODEL_BASE_URL` / `MODEL_API_KEY`）。
- 示例刻意避开“抓博客做 RAG”那种一上来就复杂的东西，用咖啡店规则、订单审核这类日常场景。
- `12_mini_project_coffee_shop.py` 是毕业项目之前的热身：它已经具备一个可交付小项目的骨架，只缺持久化、评测与 trace。
- `06c_long_term_memory.py` 专门补上第 5 项打卡内容（记忆）：Store 的基本动作 + agent 跨 thread 记住同一个用户。

---

## 17. 打卡表

| 阶段 | 内容 | 时间 | 产出 | 完成 |
|---|---|---|---|---|
| 0 | Python 差异 + `uv` 环境 | 2 天 | 打印版本号 | ☐ |
| 1 | 开箱即用 + 打开 trace | 1 天 | 跑通的 agent | ☐ |
| 2 | **手写 Agent Loop** | 2 天 | 200 行无框架 loop | ☐ |
| 3 | 模型层：工具 / 结构化输出 / 中间件 | 4 天 | 双工具 agent + 模型工厂 | ☐ |
| 4 | 编排层：状态 / 条件边 / **Postgres checkpointer** / interrupt | 1 周 | 关进程能恢复的图 | ☐ |
| 5 | 记忆：短期（checkpointer）+ 长期（Store，三型） | 2 天 | 跨会话记住用户偏好 | ☐ |
| 6 | **知识库**：灌数据脚本 + 向量库 + 元数据过滤 + MMR | 3 天 | 可重跑的索引脚本 + 检索工具 | ☐ |
| 7 | **检索质量**：混合检索 / 重排 / RAG 评测 | 2 天 | 三档对比记录 | ☐ |
| 8 | 能力扩展：MCP / 多智能体 / Deep Agents / 沙箱 | 按需 | 至少接通一个 MCP 工具 | ☐ |
| 9 | 工程层：评测 / trace / 安全 / 测试 / 前端接入 | 1 周 | 评测脚本 + 安全整改 | ☐ |
| 10 | 毕业项目：重写案例 MVP 链路 | 1 周 | 可运行仓库 + 评测报告 | ☐ |
| 11 | 附录B：VS Code 智能体模式（BYOK / 指令 / MCP / Agent / Skill / Hook） | 1 天 | 本仓库 `.github/` 定制文件组用通 | ☐ |

**每周固定动作**：写出可运行的代码（不是笔记）→ 记 3 条踩过的坑 → 把不确定的事写成一条待验证的问题，下周第一件事就是验证它。
