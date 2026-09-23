# Role & Context
你是一个精通最新版 CrewAI（特别是 CrewAI Flows 架构）的高级系统架构师。请调用你内置的官方 `crewaiinc/skills` (如 getting-started, design-agent 等)，严格按照最新官方规范，为我从零生成一个“多模式虚拟研发中心”的核心代码工程。

# Project Objective
开发一个基于 CrewAI Flows 的动态工程。它不仅能通过模式路由动态拉起不同的虚拟团队（Crews），还必须严格区分“人类对话输入”与“文档读取输入”，并在所有长流程的关键节点强制植入“AI 红蓝对抗 (Adversarial Collaboration)”与“人工验收闸门 (Human-in-the-Loop)”。

# Input Strategies, Agents & Mode Routing (核心业务要求)

请使用 CrewAI Flows (使用 `@start` 和 `@listen` 装饰器) 实现以下 4 种独立的工作流模式。必须严格遵守对应的输入类型、对抗逻辑和人工卡点规则：

## 模式 1：极速 MVP 流 (MVP Mode)
- **输入类型**：人类非结构化自然语言（业务想法）。
- **团队配置**：需求分析师 (BA)、全栈极客。
- **业务逻辑**：BA 负责与用户（人类）交互明确需求。确定后交由全栈极客直接生成核心代码骨架。
- **人工卡点**：仅在 BA 梳理需求完毕后开启确认 (`human_input=True`)，后续代码生成完全自治。

## 模式 2：企业级长流程 (Enterprise SDLC) - 包含红蓝对抗机制
- **输入类型**：人类非结构化自然语言。
- **团队配置**：BA、产品经理 (PM)、UI/UX 设计师、业务杠精 (Edge-case 挖掘者)、架构师、技术杠精 (混沌/安全工程师)、DBA、后端开发、前端开发、代码审查杠精 (Nitpicker QA)、DevOps 运维。
- **业务逻辑与多级人机评审 (CRITICAL)**：
  必须在核心里程碑引入“AI 内部互掐”与“人工拍板”机制：
  1. **需求对抗节点**：PM 产出初版 PRD -> 业务杠精发起攻击，指出边缘场景漏洞 -> PM 修正 -> 开启 `human_input=True`，人类确认放行。
  2. **架构对抗节点**：架构师与 DBA 产出初版 SAD 和表结构 -> 技术杠精进行高并发与安全质询 -> 架构师补充容灾/防范方案 -> 开启 `human_input=True`，人类拍板。
  3. **代码对抗节点**：开发产出代码 -> 代码审查杠精打回不规范代码直到通过 -> 开启 `human_input=True`，人类验收。
  4. **上线评审节点**：DevOps 输出部署脚本和流水线配置 -> 开启 `human_input=True`，人类确认。

## 模式 3：前端专项团队 (Frontend Only Mode)
- **输入类型**：本地规范文档（必须通过 `FileReadTool` 读取本地的 PRD 和 UI 规范 Markdown 文件作为上下文，而非人类对话）。
- **团队配置**：前端架构师、高级 Vue/React 研发、代码审查杠精、UI/UX 测试。
- **业务逻辑与人工卡点**：
  1. 前端架构师解析文档并输出状态管理与组件树设计 -> 开启 `human_input=True`，人工验收架构。
  2. 研发进行组件代码实现 -> 代码审查杠精审查 -> 核心组件落盘后开启 `human_input=True`。
  3. 测试进行交互验收报告 -> 开启 `human_input=True`。

## 模式 4：后端专项团队 (Backend Only Mode)
- **输入类型**：本地规范文档（依赖 `FileReadTool` 读取 PRD）。
- **团队配置**：后端架构师、DBA、技术杠精、高级 Java 研发、代码审查杠精。
- **业务逻辑与人工卡点**：
  1. DBA与架构师输出设计 -> 技术杠精质询（慢 SQL 风险、死锁风险等）-> 修正后开启 `human_input=True`。
  2. 研发完成接口逻辑编写 -> 代码审查杠精进行规范审查 -> 开启 `human_input=True`。

# Implementation Specifications

1. **标准脚手架**：请使用 `crewai create flow virtual_rnd_center` 的标准目录结构（包含 `src/` 和 `pyproject.toml`）。
2. **配置文件 (YAML-First)**：
   - 将上述 4 种模式涉及的全部角色（包含三大杠精角色）的 role, goal, backstory 写入 `agents.yaml`。
   - 将所有相关的原子任务写入 `tasks.yaml`。
3. **Crews 定义**：在 Python 代码中分别定义 `MvpCrew`, `EnterpriseCrew`, `FrontendCrew`, `BackendCrew` 类。确保在关联 Task 时，正确注入 `human_input=True` 属性。
4. **工具挂载与落盘**：
   - 模式 3 和 4 的初始任务必须挂载 `crewai_tools` 中的 `FileReadTool`。
   - 所有的文档和代码产物（PRD, SAD, 代码骨架）必须使用框架的原生 `output_file` 属性落盘到本地目录。
5. **安全限制**：严禁在生成的代码中包含任何调用 `subprocess` 或执行系统终端命令的逻辑，本项目仅生成文档和代码实体。

# Output Requirements (NO YAP)
不要解释你的思考过程。请直接使用多段 Markdown 代码块，输出以下内容：
1. 项目完整的目录结构树。
2. 包含全部角色和任务的 `agents.yaml` 与 `tasks.yaml`。
3. 包含 `MvpCrew` 和 `EnterpriseCrew` 定义的核心 Python 代码示例。
4. 实现多模式路由和状态管理的主 Flow 逻辑代码（`main.py`）。