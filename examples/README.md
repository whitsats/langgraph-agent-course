# 可运行示例集（配合 `../tutorial/`）

> 这里是**跑步机**，讲义在 [`../tutorial/`](../tutorial/README.md)：读一章 → 跑一个例子交替推进。
> 时间与取舍视角的计划在 [`../LEARNING_PLAN.md`](../LEARNING_PLAN.md)。

每个概念配一个**能直接跑、看得懂**的小例子，用同一个日常场景（咖啡店 / 订单）贯穿。

## 三步开始

```bash
# 1. 装依赖（在仓库根目录执行）
#    依赖清单已在根目录 pyproject.toml 里写好，一条命令搞定：
uv sync
# 注：默认的清华 PyPI 镜像对 langchain 返回 403（uv 会误报“包不存在”），
#     所以 pyproject.toml 里已显式指定官方源，你不用额外加参数。

# 2. 填 Key（只要这一行）
cp examples/.env.example examples/.env
#    在 examples/.env 里写：AGNES_API_KEY=sk-...

# 3. 自检 + 一键全跑
uv run python examples/00_env_check.py --live
uv run python examples/run_all.py
```

环境建在**仓库根目录的 `.venv`**，所以两种写法都能跑：

```bash
uv run python examples/05_graph_basics.py    # 从根目录
cd examples && uv run python 05_graph_basics.py   # 从 examples/（uv 会自动往上找）
```

（根目录的 `.venv` 与 `virtual_rnd_center/` 自己的环境互不干扰。）

`00_env_check.py --live` 会做一件对智能体开发最要命的检查：**这个模型到底会不会调用工具**。
不会调工具，后面所有 agent 写法都白搭——所以先确认它，再开始学。

> 默认模型是 **`agnes-2.5-flash`**（实测普通调用 0.5–8s、工具调用 0.6s）。
> 想换：在 `examples/.env` 里改一行 `MODEL=...` 即可，**代码一行都不用动**。
>
> ⚠️ **2026-09-23 实测两件事**（都不是你的配置问题）：
> - `agnes-3.0-flash` 在网关侧**整段无响应**：连接建立、请求收下，然后一个字都不返回。
>   非流式 / 流式 / 带不带 `max_tokens` 全部 15s+ 超时，连测 4 次。所以默认暂时不用它。
> - `agnes-2.5-pro` 在免费额度下直接 **403**（无权限）。
>
> `--live` 现已加 45s 上限：卡住会直接告诉你"这是网关侧没回"，不让你对着光标干等。

---

## 命名规则：文件名开头的数字 = 讲义章号

`05_graph_basics.py` 就是**第 05 章**的配套例子 —— 读到哪一章，就跑哪个数字开头的文件，不用查表。

同一章需要多个例子时用 `a`/`b`/`c` 区分（第 06 章要三个：`06a` 落库、`06b` 短期记忆、`06c` 长期记忆）。
几个章号没有对应文件，那是故意的：**01** 只有讲义没有例子，**11** 直接用 `run_all.py` 当回归测试，**13** 用的是 `../virtual_rnd_center/`，**09** 复用 `08a_index_offline.py`（都是索引与检索那些动作），**14** 是速查表不用例子，**15** 的“例子”就是你自己的 VS Code（配套 MCP server 在 `../tools/mcp/docs_server.py`）。

## 第一组：不需要 Key（离线可跑）

| 文件 | 讲义章 | 讲什么 | 观察什么 |
|---|---|---|---|
| `00_env_check.py` | 00 | 环境自检 | 版本 + 核心 API 是否可用（加 `--live` 会真调一次模型） |
| `05_graph_basics.py` | 05 | reducer（覆盖 / 累加 / 清空）+ 条件边 | 同一份状态，三种写法结果完全不同 |
| `06a_persistence_resume.py` | 06 | SQLite 落盘 + `thread_id` | **分两次运行**：关掉进程，状态还在 |
| `07a_human_approval_offline.py` | 07 | `interrupt()` 暂停 + `Command(resume=)` | 程序停在半路等人点头；恢复时节点从头重跑 |
| `08a_index_offline.py` | 08 / 09 | 切分 / 元数据过滤 / 同 id 覆盖 / 删除 | 不花钱就能把知识库的索引动作全测一遍 |

## 第二组：需要 Key

| 文件 | 讲义章 | 讲什么 | 观察什么 |
|---|---|---|---|
| `02_hello_agent.py` | 02 | `create_agent` 最小用法 | 15 行就干活；打印消息轨迹看它做了什么决定 |
| `03_handwritten_loop.py` | 03 | **手写 agent loop** ★ | 框架到底替你兜了什么 |
| `04_structured_output.py` | 04 | 结构化输出 | 口语下单 → Pydantic 对象，告别正则 |
| `06b_memory_agent.py` | 06 | 短期记忆 | 换个 `thread_id` 立刻失忆 = 多用户隔离的原理 |
| `06c_long_term_memory.py` | 06 | **长期记忆（Store）** | 先看 Store 四个动作（不需要模型）；再看 agent 换 thread 后依然记得同一个人 |
| `07b_hitl_graph.py` | 07 | 图 + 人工审批 | 小额自动、大额挂起等人点头 |
| `08b_rag_agent.py` | 08 | 小知识库 + 检索工具 | 知识库里没有的问题，它该说"不知道"而不是编 |
| `10_mcp_docs_server.py` | 10 | `MCPAdapter` 接官方文档 server | 不写工具也能有工具 |
| `12_mini_project_coffee_shop.py` | 12 | **完整小项目** | 状态机 + 结构化输出 + 知识 + 人工 + 记忆拼在一起 |

---

## 有免费额度，怎么学得更快

费用不再是约束，学法就该换：

1. **每个例子跑三遍，看三次输出**。agent 的输出每次都不一样，看多了才知道哪些是偶然。
2. **做对照实验**，而不是"跑通就走"：
   换一个模型各跑一遍 `12_mini_project`（改 `.env` 里的 `MODEL=`），比一比意图识别和工具调用谁稳；
   `agnes-3.0-flash` 一旦恢复，值得再比一次。
3. **直接做评测**（`LEARNING_PLAN.md` §10.1）：把 10–20 条固定问法写成断言，之后每次改 prompt 都重跑。免费额度让你**负担得起"每次都跑评测"**，这正是别人做不到的。
4. **让模型多迭代**：把重试上限、`max_iter` 设宽一点，观察它在失败后怎么自己纠偏。
5. **每个概念都改坏一次**：故意摘掉 reducer、摘掉 `thread_id`、把 schema 写错——看报错信息长什么样。这比看文档记得牢。
6. **开 trace**（`.env` 里打开 `LANGSMITH_TRACING`），每条都点进去看它到底看到了什么上下文。

## 一键全跑

```bash
uv run python examples/run_all.py              # 两组都跑
uv run python examples/run_all.py --offline    # 只跑离线组
uv run python examples/run_all.py --live       # 只跑需要 Key 的组
uv run python examples/run_all.py --only 06    # 只跑第 06 章那一组（06a/06b/06c）
```

跑完给一张结果表；失败的会打印末尾报错。改动例子后建议重跑一遍，当作回归测试。

---

## 验证状态（2026-09-23 最新实跑）

网关 `https://api.agnes-ai.cn/v1`、模型 `agnes-2.5-flash`；Python 3.13.13 / langchain 1.4.2 / langgraph 1.2.12。
下表耗时取自一次实测，仅作参考（随网络与服务端负载波动）。

**最新一次（2026-09-23，`agnes-2.5-flash`）—— 14/14 通过：**

```
  ✅ 05_graph_basics.py                 1.0s
  ✅ 06a_persistence_resume.py first     1.0s
  ✅ 06a_persistence_resume.py second    1.0s
  ✅ 07a_human_approval_offline.py       1.0s
  ✅ 08a_index_offline.py                0.8s
  ✅ 02_hello_agent.py                  6.5s
  ✅ 03_handwritten_loop.py             4.1s
  ✅ 04_structured_output.py            4.1s
  ✅ 06b_memory_agent.py                 3.8s
  ✅ 08b_rag_agent.py                   55.8s
  ✅ 07b_hitl_graph.py                   5.1s
  ✅ 10_mcp_docs_server.py             20.2s
  ✅ 12_mini_project_coffee_shop.py     4.7s
  ✅ 06c_long_term_memory.py            17.2s   ← 撞了两次限流，等 20s + 45s 后通过

  通过 14/14
```

> **免费额度有速率上限**：一口气连跑十几个例子会撞 `429`
> （报错原文：`您已达到免费用户的 API 速率限制`）。这不是代码错。
> `run_all.py` 现在会自动等 20s / 45s 重试，并在例子之间留 3s 间隔；
> 手动连跑时，撞到 429 就歇一两分钟（实测 20s 后即恢复）。

<details>
<summary>历史记录（2026-09-22，模型 `agnes-3.0-flash`）</summary>

```
第一组：不需要 Key（离线）
  ✅ 05_graph_basics.py                1.1s
  ✅ 06a_persistence_resume.py first    1.0s
  ✅ 06a_persistence_resume.py second   1.1s
  ✅ 07a_human_approval_offline.py      1.0s
  ✅ 08a_index_offline.py               0.9s

第二组：需要 Key
  ✅ 02_hello_agent.py                13.4s
  ✅ 03_handwritten_loop.py            7.7s
  ✅ 04_structured_output.py          10.8s
  ✅ 06b_memory_agent.py               10.5s
  ✅ 08b_rag_agent.py                  69.5s
  ✅ 07b_hitl_graph.py                  8.9s
  ✅ 10_mcp_docs_server.py            52.7s
  ✅ 12_mini_project_coffee_shop.py   13.4s
  ✅ 06c_long_term_memory.py           （Store 那半不需要 Key；agent 那半实测会跨 thread 找回记忆）

  ✅ 通过 14/14
```

</details>

两次实跑的每份输出都逐一对照过教程描述，没有虚报。过程中查出并修掉了这些问题（都已体现在代码 / 正文里）：

| 问题 | 现象 | 修法 |
|---|---|---|
| `langgraph.__version__` 不存在 | `AttributeError` | 改用 `importlib.metadata.version` |
| `DeterministicFakeEmbedding` 隐性依赖 numpy | `NameError: name 'np' is not defined` | 依赖清单加 `numpy` |
| `InMemoryVectorStore(filter={...})` | `TypeError: 'dict' object is not callable` | 改用 callable 谓词，并把这条陷阱写进示例与第 09 章 |
| Windows GBK 控制台打印 emoji | `UnicodeEncodeError: 'gbk' codec can't encode character '\u2705'` | `_shared.setup_console()` 自动切 UTF-8；`run_all.py` 给子进程设 `PYTHONIOENCODING=utf-8` |
| 工具注入 `runtime` 报 `TypeError: BaseModel.__init__() takes 1 positional argument...` | `ToolRuntime` 漏写泛型 | 标注写成 `ToolRuntime[None, AgentState]`（第 06 章） |
| `agnes-3.0-flash` 连测 4 次全部 15s+ 无响应 | 网关侧该模型不返回（同 Key 调 2.5-flash 正常） | 默认模型改为 `agnes-2.5-flash`；`--live` 加 45s 上限并单列"网关侧没回"的提示（2026-09-23） |
| 连跑例子中途大面积失败 | `429 您已达到免费用户的 API 速率限制` | `run_all.py` 自动等 20s/45s 重试 + 例子间 3s 间隔；手动撞了就歇一两分钟 |
