# Agent 学习工作区

这个仓库里有三样东西：**一套教程**、**一份学习计划**，和**一个毕业项目要重写的案例工程**。

## 从这里开始

**在线读：<https://whitsats.github.io/langgraph-agent-course/>** —— 讲义已发布成站点，
手机上也能读、章内可跳转。站点由 `tutorial/` 直接生成，改完讲义推到 `main` 会自动重建，
详见下面的“站点怎么维护”。

1. **`tutorial/`** ← 主入口（讲义，17 章）。从 [`tutorial/00-准备工作.md`](tutorial/00-准备工作.md) 开始，
   或先看 [`tutorial/README.md`](tutorial/README.md) 的目录与三条学习路径。
   **每章配一个能直接跑的例子**，读一章跑一个：

   ```bash
   uv sync                                         # 依赖清单在根目录 pyproject.toml
   cp examples/.env.example examples/.env          # 填 AGNES_API_KEY=...
   uv run python examples/00_env_check.py --live   # 先确认模型会调用工具
   uv run python examples/run_all.py --offline     # 不需要 Key 的那组，也能直接跑
   uv run python examples/run_all.py               # 一键全跑
   ```

   > ✅ 实测状态（2026-09-22）：网关 `https://api.agnes-ai.cn/v1` 下**全部例子 14/14 通过**（离线 5 项 + 在线 9 项，`06a` 跑两次）。
   > 先跑 `00_env_check.py --live`，看到 `✅ 会调用工具` 再往下读。若报 `401 Invalid token`，那是 **Key 的问题，不是代码问题**（排查方法见 `tutorial/README.md` 的“实测状态”节）。

2. **`LEARNING_PLAN.md`** ← 时间与取舍视角的配套。开头是一张**完整度复核矩阵**（30 项能力面 × 覆盖位置 × 深度取舍），后面是 5 周核心计划 + 按需扩展：手写 Agent Loop、LangChain 模型层、LangGraph 编排、**状态数据库（checkpointer 各后端）**、记忆三型、**知识库 / RAG / 向量数据库（pgvector、元数据过滤、混合检索、重排、增量索引）**、MCP、多智能体、Deep Agents、沙箱权限、评测、前端接入、部署；最后一周用 LangGraph 重写 `virtual_rnd_center/` 的 MVP 链路。
3. **`examples/`** ← 配套示例，**每个概念一个能直接跑的小例子**（一半不需要 API Key）。默认走 Agnes 免费额度，填一行 `AGNES_API_KEY` 就能跑全部。索引见 `examples/README.md` 与 `LEARNING_PLAN.md` 第 16 节。
4. 读到毕业项目那章（或想提前看看要重写什么）时，再进 `virtual_rnd_center/`。

## 目录

```
.
├── tutorial/                 # ★ 讲义：17 章，从心智模型到毕业项目 + 三篇附录
│   ├── README.md             #   目录、三条学习路径、开始之前
│   ├── 00–04                 #   上手：环境、心智模型、第一次跑通、手写循环、工具
│   ├── 05–07                 #   编排：状态与 reducer、落库与记忆、人工审批
│   ├── 08–10                 #   知识：RAG 决策、向量库与检索质量、MCP 与扩展
│   └── 11–17                 #   交付：工程化、精读小项目、毕业项目、附录、VS Code 附录B、安全附录C、规划附录D
├── LEARNING_PLAN.md          # 学习计划（时间与完整度视角）
├── README.md                 # 本文件：导航
├── pyproject.toml            # 根项目定义：教程/示例的依赖清单 + 索引源
├── uv.lock                   # 锁定版本（实测环境：langchain 1.4.2 / langgraph 1.2.12）
├── examples/                 # 配套示例：文件名开头的数字 = 讲义章号
│   ├── README.md             #   示例索引、命名规则与运行方式
│   ├── 00、05、06a、07a、08a   #   前五个不需要 Key（离线可跑）
│   ├── 其余 9 个               #   需要一个模型 Key
│   ├── 12_mini_project_coffee_shop.py  #   完整小项目：把零件拼成可交付形态
│   └── 06c_long_term_memory.py         #   长期记忆（Store）：跨会话记住同一个人
├── virtual_rnd_center/       # 案例工程：用 CrewAI 写的"虚拟研发中心"
│   ├── README.md             #   案例的真实上手说明
│   ├── src/                  #   多智能体流程源码
│   ├── templates/            #   各阶段文档模板
│   ├── output/               #   跑出来的产物与报告（真实运行痕迹）
│   ├── AGENTS.md             #   CrewAI API 参考手册（本项目维护用，学习路径无关）
│   └── virtual_rnd_center_presentation.md  # 设计说明：讲清了"为什么这么设计"
├── zensical.toml             # 讲义站点配置（GitHub Pages）
├── site-assets/              # 站点素材：logo.svg 是标识的唯一来源，位图由脚本派生
├── tools/                    # 构建脚本：拼装站点源文件、生成素材
├── overrides/                # 站点模板覆盖：只补社交分享的 og:/twitter: 标签
└── archive/                  # 归档：不再作为学习材料，仅留档
    ├── crewai-spec-prompt.md #   当初生成这个案例的需求提示词（CrewAI 语境）
    ├── crewai-scaffold-README.md  # 脚手架原始 README（占位符未替换）
    └── dev-logs/session_audit.log # 两万余行调试日志
```

## 怎么用 `virtual_rnd_center/` 这个案例

**不要学它的框架（CrewAI），要看它的设计。** 它踩过的坑比它写对的代码更值钱——`LEARNING_PLAN.md` §13 和 `tutorial/13-毕业项目.md` 都有一张对照表，把案例里每个设计翻译成 LangGraph 的对应物，照着读可以过滤掉框架细节。

推荐的两份材料：

| 文件 | 为什么值得读 |
|---|---|
| `virtual_rnd_center/virtual_rnd_center_presentation.md` | 唯一讲"设计理由"的文档：为什么不让 Agent 互相聊天、为什么要路径沙箱、为什么人机闸门放在路由层 |
| `virtual_rnd_center/src/virtual_rnd_center/crews/mvp_crew/config/tasks.yaml` | 教科书级的"工具契约写成配置"示范：工具名、参数形状、输出格式、禁止行为全写死 |

## 站点怎么维护

在线站由 `tutorial/` **直接**生成，仓库里不存第二份文档 —— `site-src/`（拼装产物）与 `site-out/`（构建产物）都在 `.gitignore` 里，改动只落在讲义原文。

```bash
uv run python tools/build_site.py                                      # 拼装：tutorial/ + 学习计划 + 示例索引 → site-src/
uvx --with-requirements requirements-docs.txt zensical serve           # 本地预览 http://127.0.0.1:8000/
uvx --with-requirements requirements-docs.txt zensical build --strict  # 构建（失效链接直接报错）
```

推到 `main` 且改动落在讲义 / 配置 / 素材相关路径时，[`.github/workflows/docs.yml`](.github/workflows/docs.yml) 自动重建并部署。
**加一章讲义只需两步**：写 `.md`、在 `zensical.toml` 的 `nav` 里登记一行。

**换标识与分享预览图**：编辑 `site-assets/logo.svg`（标识的**唯一**来源），然后

```bash
uvx --with resvg-py --with pillow python tools/make_assets.py
```

`favicon.ico`（16/32/48 多尺寸）、`apple-touch-icon.png`、`og-image.png` 全部从那个 SVG 派生，
生成后提交即可 —— CI 不装光栅化依赖。站点标题与描述在 `zensical.toml` 的 `site_name` / `site_description`，
分享卡片的 `og:` 标签由 `overrides/main.html` 补齐（Zensical 0.0.64 自己不输出任何 `og:`）。

## 关于清理

为了让干扰项不混进学习材料，做了以下**非破坏性**整理（全部可回滚，文件没删，只是挪了位置）：

| 原位置 | 现位置 | 原因 |
|---|---|---|
| `crewAi提示词.md` | `archive/crewai-spec-prompt.md` | 它是 CrewAI 语境的需求提示词，当学习材料会误导 |
| `virtual_rnd_center/README.md` | `archive/crewai-scaffold-README.md` | 脚手架模板，`{{crew_name}}` 占位符未替换、说明与实际功能不符；已重写 |
| `virtual_rnd_center/output/session_audit.log` | `archive/dev-logs/session_audit.log` | 两万余行调试日志，污染案例输出目录 |

未改动：`src/` 全部源码、`templates/`、`output/` 里的产物与报告、`AGENTS.md`、设计说明。案例本身仍可运行。
