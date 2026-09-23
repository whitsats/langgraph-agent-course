# LangChain + LangGraph 智能体开发教程

写给**有编程经验、但没做过智能体**的人。全文默认你有 web 开发背景（前端 / PHP 等），
所以每个新概念都会先给你一个熟悉的类比，再讲它本身。

**基线版本**：`langchain 1.4.2` / `langgraph 1.2.12`（2026-09-22 核对）。
只写当前有效 API；已废弃的写法（`AgentExecutor`、`create_react_agent`、`MultiServerMCPClient`）
只在"坑"里提一次，用来帮你识别过时教程。

---

## 三样东西的分工

| 目录 | 是什么 | 怎么用 |
|---|---|---|
| **`tutorial/`**（本目录） | **讲义**：讲清为什么、怎么做、哪里会错 | 一章一章读 |
| `../examples/` | **跑步机**：每章配一个能直接跑的例子 | 读一章跑一个 |
| `../virtual_rnd_center/` | **毕业项目的需求来源**：一个真跑过、也真踩过坑的案例 | 第 13 章才用得上 |

---

## 找例子：文件名开头的数字 = 讲义章号

读到第几章，就跑那个数字开头的例子——只有这一套编号，不用换算。
同一章需要多个例子时用 `a`/`b`/`c` 区分。

| 讲义章 | 配套例子 | 需要 Key |
|---|---|---|
| 00 准备工作 | `00_env_check.py` | 否（加 `--live` 才真调模型） |
| 01 心智模型 | —（只读讲义，本章不碰代码） | — |
| 02 第一次跑通 | `02_hello_agent.py` | 是 |
| 03 手写循环 ★ | `03_handwritten_loop.py` | 是 |
| 04 工具与可靠交付 | `04_structured_output.py` | 是 |
| 05 状态与条件边 ★ | `05_graph_basics.py` | 否 |
| 06 状态落库与记忆 ★ | `06a_persistence_resume.py`、`06b_memory_agent.py`、`06c_long_term_memory.py` | `06a` 否；另两个是 |
| 07 人工审批 | `07a_human_approval_offline.py`、`07b_hitl_graph.py` | `07a` 否；`07b` 是 |
| 08 RAG 决策 | `08a_index_offline.py`、`08b_rag_agent.py` | `08a` 否；`08b` 是 |
| 09 向量库与检索质量 | 复用 `08a_index_offline.py` | 否 |
| 10 MCP 与能力扩展 | `10_mcp_docs_server.py` | 是（还要联网） |
| 11 工程化 ★ | `run_all.py`（当回归测试用） | 看跑哪一组 |
| 12 精读小项目 | `12_mini_project_coffee_shop.py` | 是 |
| 13 毕业项目 | `../virtual_rnd_center/` | — |
| 14 附录 | —（随时查） | — |

有章号没有对应文件，是故意的：01 只有讲义，11 用 `run_all.py` 当回归，13 用的是案例工程。

---

## 目录（14 章，全部已写完）

### 第一部分：上手（先把东西跑起来）

| 章 | 标题 | 配套例子 | 大概用时 |
|---|---|---|---|
| 00 | [准备工作](00-准备工作.md) | `00_env_check.py` | 0.5 天 |
| 01 | [先建立心智模型](01-先建立心智模型.md) | — | 1 小时 |
| 02 | [第一次跑通一个智能体](02-第一次跑通.md) | `02_hello_agent.py` | 0.5 天 |
| 03 | [手写智能体循环](03-手写智能体循环.md) ★ | `03_handwritten_loop.py` | **1 天** |
| 04 | [工具设计与可靠交付](04-工具与可靠交付.md) | `04_structured_output.py` | 1 天 |

### 第二部分：把流程变可控（LangGraph）

| 章 | 标题 | 配套例子 | 大概用时 |
|---|---|---|---|
| 05 | [状态、reducer 与条件边](05-状态与条件边.md) ★ | `05_graph_basics.py` | 1 天 |
| 06 | [状态落库与记忆](06-状态落库与记忆.md) ★ | `06a_persistence_resume.py`、`06b_memory_agent.py`、`06c_long_term_memory.py` | 1.5 天 |
| 07 | [把人类放回流程](07-人工审批.md) | `07a_human_approval_offline.py`、`07b_hitl_graph.py` | 1 天 |

### 第三部分：给它知识和外部能力

| 章 | 标题 | 配套例子 | 大概用时 |
|---|---|---|---|
| 08 | [RAG：先决定要不要知识库](08-RAG决策.md) | `08a_index_offline.py`、`08b_rag_agent.py` | 1 天 |
| 09 | [向量库与检索质量](09-向量库与检索质量.md) | `08a_index_offline.py` | 1.5 天 |
| 10 | [MCP 与能力扩展（按需）](10-MCP与能力扩展.md) | `10_mcp_docs_server.py` | 0.5–2 天 |

### 第四部分：做成能交付的东西

| 章 | 标题 | 配套例子 | 大概用时 |
|---|---|---|---|
| 11 | [工程化：评测、trace、上下文、安全](11-工程化.md) ★ | `run_all.py`（当回归用） | 2 天 |
| 12 | [精读一个完整小项目](12-精读小项目.md) | `12_mini_project_coffee_shop.py` | 0.5 天 |
| 13 | [毕业项目：重写真实链路](13-毕业项目.md) | `../virtual_rnd_center/` | **1 周** |
| 14 | [附录：API 速查与排错](14-附录.md) | — | 随时查 |

---

## 三条学习路径

**A. 极速路径（3 天，先把东西转起来）**
读 00 → 01 → 02 → 03，跑通 `examples/00_env_check.py`、`02_hello_agent.py`、`03_handwritten_loop.py`。
目标：知道智能体是什么、能自己写一条循环。**跳过所有 RAG / MCP / 工程化内容。**

**B. 标准路径（约 3 周，学到能交付）**
按章顺序走，每章读完立刻跑对应例子，第 13 章做毕业项目。
配套 `../LEARNING_PLAN.md` 的 17 节打卡表使用。

**C. 只补缺口（已经写过 agent，只想查漏）**
**前提**：你已经自己写出过一个能跑的工具调用循环（第 03 章那种），否则不要走这条。
满足前提的话，直接翻第 05（reducer）、06（checkpointer）、11（工程化）三章——这三章是最容易"看懂了但写错"的地方。

> ⚠️ 这里的"已有基础"指**智能体基础**，不是编程基础。有 web 开发经验不等于可以直接跳到第 05：
> 05 讲的是"状态在循环里怎么合并"，没手写过那个循环，reducer 就只是没有对象的语法糖。

> 打 ★ 的四章（03、05、06、11）是**不可跳过**的：手写循环、状态合并、持久化、评测。
> 少任何一章，你都会在毕业项目里卡住，而且卡得很困惑。

---

## 每章的统一结构

我刻意让每章长得一样，方便你形成节奏：

1. **本章目标** —— 3 条，学完你应该能自己做到
2. **概念** —— 用你熟悉的 web 开发类比讲，不堆术语
3. **跟着做** —— 对应哪个例子、执行什么命令
4. **看懂输出** —— 输出里哪一行才是重点
5. **自己动手改** —— 2–4 个变体任务，**改坏比跑通学得多**
6. **验收问题** —— 答不上来就回读，别往下走
7. **坑** —— 这一章最容易踩的地方
8. **想深挖** —— 官方文档的哪几页（带直链）

---

## 三条写作约定

1. **浅显优先。** 能用咖啡店举例就不用"语义空间""认知架构"这种词。
2. **只写当前版本的 API。** 废弃写法只在"坑"里出现，用来帮你筛教程。
3. **每个概念都要能跑。** 讲完一个概念，你要么能立刻执行一个例子，要么能立刻改一处代码看到变化。

---

## 开始之前

```bash
# 建环境：依赖清单已在根目录 pyproject.toml 里写好
uv sync
# 注：默认的清华 PyPI 镜像对 langchain 返回 403（uv 会误报“包不存在”），
#     pyproject.toml 里已显式指定官方源，你不用额外加参数。

# 填 Key（一行就够，免费额度）
cp examples/.env.example examples/.env        # 写 AGNES_API_KEY=...

# 自检：环境 + 模型到底会不会调用工具
uv run python examples/00_env_check.py --live
```

看到 `✅ 会调用工具` 再往下读。看不到就先换模型——**这个问题不解决，后面全白学**。

---

## 实测状态（2026-09-23 全量实跑）

网关：**`https://api.agnes-ai.cn/v1`**（模型 `agnes-2.5-flash`）。环境：Python 3.13.13 / `langchain 1.4.2` / `langgraph 1.2.12` / `langchain-core 1.6.4`，Windows。

| 范围 | 状态 |
|---|---|
| 离线组（`00`、`05`、`06a`、`07a`、`08a`，不需要 Key） | ✅ **5/5 通过**，输出与正文描述一致 |
| 需要 Key 的组（其余 9 个） | ✅ **9/9 通过**（最慢的是 `08b_rag_agent` 和 `10_mcp_docs_server`，几十秒到一分钟） |
| 核心 API 可用性（`00_env_check.py`） | ✅ 8/8 可用；`--live` 会打印 `✅ 会调用工具` |

一键复现：`uv run python examples/run_all.py`（离线 5 项 + 在线 9 项，跑完给结果表）。

实跑之后确认的事（都已回写进正文或示例）：

1. **`langgraph` 没有 `__version__` 属性**（会 `AttributeError`）→ 查版本必须用 `importlib.metadata`。
2. **`DeterministicFakeEmbedding` 需要 `numpy`**，而 langchain-core 没声明它 → 报 `NameError: name 'np' is not defined`。
3. **`InMemoryVectorStore` 的 `filter` 只接受 callable**，传元数据字典会 `TypeError: 'dict' object is not callable`——同一写法在 Chroma/PGVector 上才能用。
4. 清华 PyPI 镜像对 `langchain` 返回 `403 Forbidden`，uv 会误报"包不存在"→ 需要显式指定官方源。
5. **Windows GBK 控制台打印 `✅` 会直接崩**（`UnicodeEncodeError: 'gbk' codec can't encode character '\u2705'`）→ 示例已内置 `_shared.setup_console()` 自动切 UTF-8，`run_all.py` 也会给子进程设 `PYTHONIOENCODING=utf-8`。
6. **`ToolRuntime` 注入必须写泛型**：`ToolRuntime[None, AgentState]`；裸写 `ToolRuntime` 会报 `TypeError: BaseModel.__init__() takes 1 positional argument but 2 were given`（写第 06 章长期记忆例子时实测）。
7. **事件流 v3 在 `langgraph 1.2.12` 上会打 `LangChainBetaWarning`**（`The v3 streaming protocol on Pregel is experimental.`）——是提示不是错误，官方文档已把它当推荐路径。
8. **`agnes-3.0-flash` 曾在网关侧整段无响应**：连接通、请求收下、一个字不回（非流式/流式/带不带 `max_tokens` 全部 15s+ 超时，连测 4 次）；同 Key 调 `agnes-2.5-flash` 0.5–8s 正常。默认模型因此改为 `agnes-2.5-flash`，`--live` 加了 45s 上限。
9. **免费额度有速率上限**：连跑十几个例子会撞 `429`（原文"您已达到免费用户的 API 速率限制"）。实测等 20s 即恢复；`run_all.py` 已内置 20s/45s 自动重试与 3s 间隔。

> 换自己的 Key / 网关：只改 `examples/.env`，代码一行不用动。
> 凡是我不确定的 API，正文里一律写明了"先用 `inspect.signature` 验证"，没有编造。
