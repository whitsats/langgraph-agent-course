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

同一章需要多个例子时用 `a`/`b`/`c` 区分（第 06 章要三个：`06a` 落库、`06b` 短期记忆、`06c` 长期记忆；第 11 章四个：`11a` 评测集、`11b` 上下文预算、`11c` 流式前端、`11d` 成本账单）。
几个章号没有对应文件，那是故意的：**01** 只有讲义没有例子，**13** 用的是 `../virtual_rnd_center/`，**09** 复用 `08a_index_offline.py`（都是索引与检索那些动作），**14** 是速查表不用例子，**15** 的“例子”就是你自己的 VS Code（配套 MCP server 在 `../tools/mcp/docs_server.py`）；**10b / 11a / 11b / 16 / 17 / 18** 都不调模型——离线模拟"模型的决策"，把结构本身测清楚（派活隔离、评测回归、上下文取舍、攻击与契约）；**11c / 11d** 需要 Key（流式管道与 token 账单）。

## 第一组：不需要 Key（离线可跑）

| 文件 | 讲义章 | 讲什么 | 观察什么 |
|---|---|---|---|
| `00_env_check.py` | 00 | 环境自检 | 版本 + 核心 API 是否可用（加 `--live` 会真调一次模型） |
| `05_graph_basics.py` | 05 | reducer（覆盖 / 累加 / 清空）+ 条件边 | 同一份状态，三种写法结果完全不同 |
| `06a_persistence_resume.py` | 06 | SQLite 落盘 + `thread_id` | **分两次运行**：关掉进程，状态还在 |
| `07a_human_approval_offline.py` | 07 | `interrupt()` 暂停 + `Command(resume=)` | 程序停在半路等人点头；恢复时节点从头重跑 |
| `08a_index_offline.py` | 08 / 09 | 切分 / 元数据过滤 / 同 id 覆盖 / 删除 | 不花钱就能把知识库的索引动作全测一遍 |
| `10b_supervisor_lab.py` | 10 | supervisor 派活 / 扇出 / 聚合 | 一个 worker 崩了，简报照样出（失败隔离）；Send API 的前置形态 |
| `11a_eval_lab.py` | 11 | 评测集：跑分 + 版本回归对比 | 改 prompt 前后通过率 delta；编造与跳过审批被抓（`--judge` 才真调模型） |
| `11b_context_budget_lab.py` | 11 | 上下文预算：全量 / 裁剪 / 摘要 | 裁剪省 token 但丢"花生过敏"；摘要才是长会话的解 |
| `16_agent_security_lab.py` | 16 | 四个安全攻击实验（注入 / 投毒 / 权限） | ⚠️ 注入得手、✅ 补丁拦截——重点看实验 4 两种权限的两行对比 |
| `17_plan_and_verify_lab.py` | 17 | 规划与自我验证四实验 | 一口气式的编造收尾 vs 计划被校验/修复；验证器拒绝编造的候选 |
| `18_handoff_contract_lab.py` | 18 | 交接契约 + 通道认证四实验 | 自由文本交接丢数字；坏包死在门口；伪造/篡改/重放/过期消息全被拒；带毒字段不被执行；7 条契约测试锁两端（含类型层） |

> 注：`00_env_check` 是自检工具、不进回归组——所以 `run_all.py --offline` 的 11 项 =
> 上表除 00 外的 10 个脚本 + `06a` 跑两次（两组都恰好叫"11"，但成员不同：文件口径含 00，回归口径不含）。

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
| `11c_stream_frontend.py` | 11 | **流式 + 最小前端**：FastAPI 包 SSE | 默认自测帧序；`--serve` 起服务后浏览器直接玩 |
| `11d_cost_ledger.py` | 11 | token 成本账单 | 真调 3 次拿 `usage_metadata` 攒表；价格表留空由你填 |
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

跑完给一张结果表；失败的会打印末尾报错。改动例子后建议重跑一遍，当作回归测试；
改过某章的**断言/校验逻辑**，再跟着跑一次下面的变异检查。

**18 个例子都自带断言**（`examples/_shared.py` 里的 `Checks`）：每条检查失败都会让脚本以
**非 0 退出码**结束，并列出是哪条不变量红了，所以结果表里的 ✅ 是真的 ✅——不是"跑完没崩"。

- **离线组**（08a / 10b / 11a / 11b / 16 / 17 / 18）：第 16 章前三个实验是**演示型断言**——它们断言"漏洞确实存在"，
  谁不小心把这个洞堵上了反而会红；其余都是普通的不变量断言。
- **在线组**（其余 11 个）：断言写在**语义特征**上（第 11 章），因为模型每次措辞都不同：
  知识库里有的必须带对事实、没有的必须承认不知道且不编数字、大额退款必须中断、
  人工拒绝不得走成受理、同一 thread 的记忆不得丢。**行为不许变，措辞随便变。**

## 断言可信度：变异检查（离线，秒级）

`run_all.py --offline` 全绿只能说明**示例没崩**，不能说明**断言还在咬人**。
断言会以三种方式悄悄失效：写成同义反复（断言一个字面量、或一个刚被 `clear()` 的全局变量）、
覆盖不到（实现改坏了却没有检查变红）、只打印不判定（`❌` 信号写进了输出却没人拿它当回事）。
抓它们的办法是**变异测试**：把每个关键不变量**故意改坏**，再跑一遍示例，看它是不是真的报了错。

```bash
uv run python examples/mutation_check.py             # 全部（23 条，秒级，不需要 Key）
uv run python examples/mutation_check.py --only 18   # 只查第 18 章那个实验室
uv run python examples/mutation_check.py --list      # 只列清单，不跑
```

改坏了还是一片 ✅ = 这条变异**存活**，说明那处检查是装饰品；脚本以非 0 退出码结束。
杀死一条变异有三条途径：那句话该出现（`expect_appear`）、那句话该消失（`expect_vanish`）、
或者**脚本自己非 0 退出**（实验室的断言就是这么报的——也是 `run_all.py` 变红的原因）。
它还会先跑一遍原始文件做**防"假红"**校验：每条信号的方向必须刚好相反
（该出现的原本不出现、该消失的原本在），否则报"配置问题"。变异后的源码还会
先过一遍 `compile()`——语法错误的变异（片段缩进写错之类）同样按"配置问题"处理，
因为崩溃不是断言在咬人，不该算"杀死"。

覆盖范围是**代码里强制执行的检查**：第 08 章 a 的租户隔离（元数据过滤谓词）、
第 10 章 b 的派活失败隔离（聚合不过滤状态 → 崩掉的 worker 混进简报）、
第 11 章 a/b 的评测判卷与上下文裁剪、第 16 章实验 4（工具白名单 / 路径范围）、
第 17 章（计划校验 / 重规划 / 验证器 / 断点）、
第 18 章（契约校验各层 / 通道三件套 / 消费者纪律 / 契约测试）。
第 16 章前三个实验是**故意展示漏洞**的演示，没有该红的地方。

> **2026-09-24 首跑：15/15 被杀死。** 但第一次跑时挂了两条——身份检查与完整性检查
> "存活"：测试数据里那个篡改包沿用了已见过的序号，先撞上重放检查，于是把 MAC 校验
> 整个删掉测试照样全绿。修法是让每条检查都有**只触发它自己**的用例（篡改包改内容时
> 也把序号换掉）。第二轮它又暴露一个覆盖缺口：**类型层原本只靠输出里的一句话兜着**
> （把类型校验删掉，6 条用例照样全绿）——现已为它补上第 7 条用例。
> 这道检查头两次运行都抓到真问题——这就是它存在的理由。
>
> **2026-09-24 增补**：变异表扩到 **20 条**——补上 08a 租户隔离、17 幽灵工具、
> 18 夹带过程 / 超长 / 新鲜性（其中超长与新鲜性是先给实验室补了「超长版」坏包与
> 「⑤过期消息」用例才进表的，改坏它们原本什么都不红）。另加 `compile()` 前置校验：
> 变异把源码改出语法错误时按"配置问题"报告，不再把崩溃误记成"杀死"。
>
> **2026-09-25 增补**：第 10 / 11 章补 5 个 lab（`10b_supervisor_lab`、`11a_eval_lab`、
> `11b_context_budget_lab`、`11c_stream_frontend`、`11d_cost_ledger`），离线的三个
> 各带一条变异进表，总数 **23 条**，23/23 被杀死。
>
> 注：变异检查只覆盖**离线组**带不变量的例子（秒级、不需要 Key）；在线组的 11 个例子
> 靠 `run_all.py --live` 验证断言——每次都要真调模型，不适合逐条改坏重跑。

---

## 验证状态（2026-09-25 最新实跑）

网关 `https://api.agnes-ai.cn/v1`、模型 `agnes-2.5-flash`；Python 3.13.13 / langchain 1.4.2 / langgraph 1.2.12。
耗时取自 2026-09-25 的实测，仅作参考（随网络与服务端负载波动）。

**离线组 11/11 + 变异检查 23/23 + 在线组 10/11（唯一失败见下）：**

```
  ✅ 05_graph_basics.py                 1.1s
  ✅ 06a_persistence_resume.py first     1.1s
  ✅ 06a_persistence_resume.py second    1.0s
  ✅ 07a_human_approval_offline.py       1.1s
  ✅ 08a_index_offline.py                0.9s
  ✅ 10b_supervisor_lab.py               0.1s
  ✅ 11a_eval_lab.py                     0.1s
  ✅ 11b_context_budget_lab.py           0.1s
  ✅ 16_agent_security_lab.py            0.1s
  ✅ 17_plan_and_verify_lab.py           0.1s
  ✅ 18_handoff_contract_lab.py          0.1s
  ✅ 02_hello_agent.py                  10.0s
  ✅ 03_handwritten_loop.py             10.4s
  ✅ 04_structured_output.py             3.9s
  ✅ 06b_memory_agent.py                24.9s
  ✅ 06c_long_term_memory.py             6.0s
  ✅ 07b_hitl_graph.py                  28.2s
  ❌ 08b_rag_agent.py                   14.3s   ← 见下方说明；单跑通过（已实测）
  ✅ 10_mcp_docs_server.py              37.0s
  ✅ 11c_stream_frontend.py              2.8s
  ✅ 11d_cost_ledger.py                 17.0s
  ✅ 12_mini_project_coffee_shop.py      7.4s

  通过 21/22
```

> **关于 08b 的那次 ❌（这是特性，不是 bug）**：全量连跑到末段时免费额度限流开始密集出现，
> 08b 的两次 429 重试（20s + 45s）耗尽后，第三次的模型响应**真的降级了**——答案既丢了
> "周六 22:00" 这个事实、又编造了价格数字，两条行为断言如实变红。断言没有误报：
> 限流压力下的质量下降是真实发生的。**单跑或歇几分钟重跑即过**（均已实测）。
> 这也是第 11 章"断言写在行为上"的活例子：它拦的不是措辞，是退化的回答。

<details>
<summary>历史记录（2026-09-24，模型 `agnes-2.5-flash`，17/17）</summary>

```
  ✅ 05_graph_basics.py                 1.1s
  ✅ 06a_persistence_resume.py first     1.1s
  ✅ 06a_persistence_resume.py second    1.0s
  ✅ 07a_human_approval_offline.py       1.0s
  ✅ 08a_index_offline.py                0.8s
  ✅ 16_agent_security_lab.py            0.1s
  ✅ 17_plan_and_verify_lab.py           0.1s
  ✅ 18_handoff_contract_lab.py          0.1s
  ✅ 02_hello_agent.py                  27.3s
  ✅ 03_handwritten_loop.py             30.1s
  ✅ 04_structured_output.py             4.4s
  ✅ 06b_memory_agent.py                17.4s
  ✅ 06c_long_term_memory.py            28.1s
  ✅ 07b_hitl_graph.py                   6.1s
  ✅ 08b_rag_agent.py                   68.3s   ← 中途撞了限流，等 20s + 45s 后通过
  ✅ 10_mcp_docs_server.py              22.5s
  ✅ 12_mini_project_coffee_shop.py     11.4s

  通过 17/17
```

</details>

> **2026-09-24 顺带修复**：`08b` 的「周六 22:00」断言原来死抠字面「22」，模型把它说成
> 「晚上十点」时会在全量连跑里误报失败（实测连挂两次、单跑通过）。已改成等价说法的
> 正则并给模型加 `temperature=0`。另外 `run_all.py` 现在失败会以非 0 退出码结束
> （此前永远退出 0，当回归测试用会骗绿）。

<details>
<summary>历史记录（2026-09-23，模型 `agnes-2.5-flash`，14/14）</summary>

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

</details>

> **2026-09-24 增补**：离线组收编 `16_agent_security_lab.py`（第 16 章安全攻击实验）、`17_plan_and_verify_lab.py`（第 17 章规划与自我验证实验）与 `18_handoff_contract_lab.py`（第 18 章交接契约实验），`run_all.py --offline` 现为 **8/8 通过**。

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
