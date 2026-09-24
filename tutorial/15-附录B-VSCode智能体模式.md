# 第 15 章：附录 B —— 在 VS Code 智能体模式里做真实开发

> 这一章回答一个前 14 章一直没正面回答的问题：**"我自己平时写代码，能不能不写 Python 就得到这些能力？"**
> 能。VS Code 的智能体模式（Agent Mode）把 Harness、工具、记忆、审批、MCP 这些概念全部做成了**编辑器里的官方功能**。
> 这一章以真实项目（就是本仓库）为例，把前面学过的每个概念在 VS Code 里再实现一遍。

**基线**：VS Code Stable **1.139**（2026-09-23 发布），以下所有路径、文件名、设置项均以当月官方文档核对为准。
智能体相关功能迭代很快，半年后读到本文，请先对照文末"想深挖"里的官方链接确认。

**建议用时**：1 天（前 14 章学扎实的话，这章会非常快——每个概念都只是"换了个地方"）。

---

## 本章目标

1. 把第三方模型（还是 Agnes 网关）通过 BYOK 接进 VS Code，让智能体模式**不用 Copilot 订阅也能跑**
2. 用官方定制体系给本仓库配齐五件套：**项目指令、自定义 Agent、Skill、MCP、Hook**——每一件都真实可用
3. 把五件套串成一条完整的开发流程，并知道每一件**该用在哪、不该用在哪**

**配套文件**：本章用到的所有配置都**已随本仓库提供**——`tools/mcp/docs_server.py`（MCP server，已实测）、
`.github/` 下的指令 / Agent / Skill / Hook、根目录 `.mcp.json`。你可以逐个打开对照着读。
本章的"例子"就是你自己的 VS Code——它本身就是那台跑步机。

---

## 概念：VS Code 里也有一张分层图

第 01 章画过五块拼图。VS Code 的智能体体系就是那套拼图的**产品化实现**，逐层对上：

| 第 01 章的拼图 | VS Code 里的对应物 | 你在哪配置它 |
|---|---|---|
| Harness（马具） | **Agent Host**（承载 Copilot / Claude / Codex 三种 harness）或 **Local**（跑在扩展宿主里） | 聊天输入框下方的 Session Target |
| 模型 | 内置模型 / **BYOK 自带 Key** | 模型选择器 → Manage Language Models |
| 工具 | 内置工具 + **MCP 工具** + 扩展工具 | `#` 菜单、Configure Tools |
| 流程约定 | **项目指令、自定义 Agent、Skill** | `.github/` 下的文件 |
| 闸门 | **审批对话框** + **Hooks** | 聊天里点头 / `.github/hooks/*.json` |

两张图的根本差别只有一条：**前面 14 章里这些层是你写的代码；这一章里它们是你提交进仓库的配置文件。**
"写成配置"意味着三件事：能进版本库与团队共享、能被逐行 review、坏了有明确的排错入口。

### 管理入口只有一个

所有定制都在 **Agent Customizations 编辑器**里管理：命令面板（`Ctrl+Shift+P`）→ **Chat: Open Customizations**。
它按 Session Target 分区显示当前 harness 支持的定制类型。**改哪套配置之前，先选对 Session Target**——
选错了 harness，你写的文件可能根本不被读，这是本章第一个高频事故。

---

## 阶段 0：接入第三方模型（BYOK）

### 概念：BYOK = "自带酒水"

Copilot 默认走 GitHub 登录。**BYOK（Bring Your Own Key）让你用自己的 API Key 接任意兼容供应商**，
聊天体验和工具完全不变；可以不登录 GitHub 账号、没有 Copilot 订阅也能用，本地模型（如 Ollama）也走这条路。
这正是第 00 章"模型与代码解耦"思想在编辑器里的样子：换供应商只动配置，不动你教它的一切。

### 跟着做

1. 模型选择器（聊天输入框右下角）→ **Manage Language Models**（齿轮）→ **Add Models** → 选 **Custom Endpoint**
2. 分组名填 `Agnes`；按提示填显示名与 API Key
3. VS Code 会打开 `chatLanguageModels.json`，填成这样：

```jsonc
[
  {
    "name": "Agnes",
    "vendor": "customendpoint",        // 固定值：Custom Endpoint 供应商
    "apiKey": "${input:agnesApiKey}",  // ★ 别裸写 Key：用输入变量，Key 进密钥存储
    "models": [
      {
        "id": "agnes-2.5-flash",       // 你网关上的模型 id（第 00 章的老朋友）
        "name": "Agnes 2.5 Flash",     // 显示名
        "url": "https://api.agnes-ai.cn/v1/chat/completions",  // ★ 写全 API 路径，避免歧义
        "toolCalling": true,           // ★ 没有它智能体模式里根本不显示这个模型
        "maxInputTokens": 128000,      // 按你网关的实际上下文窗口填
        "maxOutputTokens": 16000
      }
    ]
  }
]
```

4. 保存，回到模型选择器选它。没出现就**重启 VS Code**（官方明说的Tip，不是玄学）

### 看懂输出

- 模型选择器出现 `Agnes 2.5 Flash` → 接通了
- 给它一个会触发工具的提示（比如"列出 tutorial 目录下所有 md 文件"），它弹出**工具审批** → 工具调用能力 OK
- 如果模型根本不出现在选择器里：**九成是 `toolCalling` 没开或模型真不支持工具调用**——
  这就是第 00 章"`00_env_check.py --live` 先验证会不会调工具"的编辑器版

> ⚠️ BYOK 覆盖的是**聊天体验与工具任务**。行内补全、语义搜索这类依赖 embedding 的功能仍需 GitHub 账号。

---

## 阶段 1：项目指令——把仓库规矩写成文件

### 概念：全局生效的 system prompt

`.github/copilot-instructions.md` 是 Copilot 会话的**项目级常驻指令**：每次对话自动带上，等于给这个仓库写 system prompt。
跨工具的等价物是根目录 `AGENTS.md`（Codex、Copilot、Local 都认）。取舍：只用 Copilot 就写前者；团队混用多个 AI 工具就写 `AGENTS.md`。

### 跟着做

在仓库根创建 `.github/copilot-instructions.md`（本仓库的真实版本，直接可用）：

```markdown
# 仓库约定

* Python 教程仓库：讲义在 `tutorial/`，可跑示例在 `examples/`，文件名开头数字 = 讲义章号。
* 改讲义保持每章统一结构：本章目标 / 概念 / 跟着做 / 看懂输出 / 自己动手改 / 验收问题 / 坑 / 想深挖。
* 示例改动后必须验证：`uv run python examples/run_all.py --offline`（离线组，不需要 Key）。
* API Key 只出现在 `examples/.env`（已 gitignore）；示例代码一律从环境变量读配置。
* 文风：先类比后术语，说人话；不写没验证过的 API，不确定的写明"先用 inspect.signature 验证"。
```

### 看懂输出

随便问一句"这个仓库怎么跑测试"，回答应该直接引用 `run_all.py` 而不是泛泛的 pytest——
**展开回答里的 References（引用）区块，能看到这次实际带上了哪份定制文件**。验证定制生效，永远看 References，不猜。

---

## 阶段 2：MCP——给智能体装上仓库自己的工具

### 概念：第 10 章的 USB-C，插进编辑器

第 10 章说过：MCP 解决"互操作"。在 VS Code 里它解决的是**"智能体读不懂我这个仓库的特殊结构"**。
本仓库有个真实痛点：讲义分散在 15 个文件里，问"哪章讲过 checkpointer"全靠碰运气。
那就给智能体一个工具，让它**自己查**。

### 跟着做（先装别人的，再写自己的）

**先装一个现成的**（30 秒建立体感，两条路任选）：
- 扩展视图（`Ctrl+Shift+X`）→ 搜索框输入 `@mcp playwright` → 在结果的 **MCP 服务器** 区选 **Playwright MCP Server** → **Install**（装进用户配置）→ 弹窗选**信任**启动
- 或从聊天入口：聊天输入框的 Configure Tools（工具图标）→ **MCP 服务器** → 浏览市场 → 搜 Playwright

装完在聊天里输入："打开 code.visualstudio.com，截一张首页的图。" 看它弹出的 Playwright 工具审批——这就是 MCP 工具在聊天里的样子。

**再写一个自己的**。新文件 `tools/mcp/docs_server.py`（已随本章提交，可直接用）：

```python
"""把本教程的讲义变成 MCP 工具（mcp 2.x 写法，注意不是 FastMCP）"""
from pathlib import Path
from mcp.server.mcpserver import MCPServer

DOCS = Path(__file__).resolve().parents[2] / "tutorial"
server = MCPServer("tutorial-docs",
                   instructions="LangChain+LangGraph 教程检索工具：列章节、按关键词搜讲义。")

@server.tool()
def list_chapters() -> list[str]:
    """列出 tutorial/ 下全部讲义章节文件名。"""
    return sorted(p.name for p in DOCS.glob("*.md") if p.name != "README.md")

@server.tool()
def search_tutorial(keyword: str) -> list[dict]:
    """在讲义全文里搜关键词，返回 (文件名, 行号, 内容) 最多 20 条。"""
    hits: list[dict] = []
    for path in sorted(DOCS.glob("*.md")):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if keyword in line:
                hits.append({"file": path.name, "line": lineno, "text": line.strip()[:120]})
                if len(hits) >= 20:
                    return hits
    return hits

if __name__ == "__main__":
    server.run(transport="stdio")
```

然后在 `.vscode/mcp.json` 里注册（VS Code 格式，顶层键是 `servers`；本仓库根目录的 `.mcp.json` 已带同样配置）：

```jsonc
{
  "servers": {
    "tutorial-docs": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "python", "tools/mcp/docs_server.py"]
    }
  }
}
```

保存后会先后看到两件事：右下角弹"已检测到工作区 MCP 服务器 tutorial-docs"→ 选**信任并启动**；
命令面板跑 `MCP: List Servers`，确认它显示"正在运行"并带 `2 tools`（跑 `MCP: Show Server Output` 能看到启动时的 JSON-RPC 握手日志）。

回到聊天，**三条提示词逐条验证**（Copilot 与 Local 两个 Session Target 各跑一遍）：

1. `#tutorial-docs` → 菜单里列出 `list_chapters` / `search_tutorial` → 选后者，参数填 `"checkpointer"` 直接跑（**点名调用**）
2. 自然语言："用 tutorial-docs 搜一下哪章讲 checkpointer。"——看它**自己**选中这个工具
3. "不用任何工具，直接告诉我哪章讲 checkpointer。"——答案应一致，但**没有工具调用**（确认工具是可选的，不是劫持对话）

### 看懂输出

第 1、2 条应调用 `search_tutorial`，返回的首条命中指向第 06 章《状态落库与记忆》。
**注意工具调用的展开面板**：入参 `keyword`、返回的命中列表都看得见——出问题先看这里，而不是猜。

### 两个真实的坑（都发生在写这章时）

1. **`.vscode/` 在本仓库被 gitignore 了**——`.vscode/mcp.json` 不会进版本库。想让团队共享，把配置放到根目录
   `.mcp.json`（可移植格式，顶层键是 `mcpServers`），它会被提交——本仓库已经这样做了，两个文件是同一台 server。
2. **Copilot 会话（Agent Host）不直接读 `.vscode/mcp.json`**：VS Code 会把配置转发给 Agent Host，
   但原生读取的是工作区 `.mcp.json` 和用户级 `~/.copilot/mcp-config.json`。两个格式都写上最稳。

### 什么时候该写 MCP server（对照第 10 章的判断表）

| 需求 | 结论 |
|---|---|
| 让智能体查仓库自己的结构化信息（本章场景） | ✅ 一个几十行的 stdio server，最划算 |
| 接现成服务（浏览器、数据库、GitHub） | ✅ 装别人的，别造轮子 |
| 只是教它一套**操作流程**（怎么发版、怎么审 PR） | ❌ 那是 Skill 的活，见阶段 4 |
| 只是几条代码规范 | ❌ 那是 instructions 的活，见阶段 1 |

另外记一条硬限制：**单次请求最多挂 128 个工具**。工具多了就去工具选择器里关掉整个不相关的 server，
而不是指望模型自己分辨。

---

## 阶段 3：自定义 Agent——给仓库一个"评审员"

### 概念：角色 = 指令 + 工具白名单

自定义 Agent 是 `.agent.md` 文件定义的**角色**：一段专属指令 + 一份工具白名单，可挂交接按钮（handoffs）。
它和第 10 章"Router / Subagents"的对应关系：自定义 Agent 就是**编辑器托管的 subagent 单元**，
主 Agent 通过 `agents` 属性调用它们，不用你写任何编排代码。

### 跟着做

创建 `.github/agents/reviewer.agent.md`（本仓库已带，可直接用）：

```markdown
---
description: 审查当前改动：正确性、可维护性、与仓库约定的一致性。只报告，不修改。
name: Reviewer
tools: ['search/codebase', 'search/usages', 'web/fetch']
handoffs:
  - label: 按意见修复
    agent: agent
    prompt: 按上面 Reviewer 的意见逐条修复，改完跑 uv run python examples/run_all.py --offline 验证。
    send: false
---

# 评审规则

1. 先读 .github/copilot-instructions.md，以仓库约定为评审基准。
2. 逐条检查当前未提交的改动：正确性、可维护性、是否与约定冲突。
3. 每条意见给出：文件位置、问题、建议修法。按严重程度排序。
4. **绝不修改文件**——你只有搜索工具，这是故意的。
5. 结尾给一行结论：可以提交 / 需要修改。
```

聊天输入框上方的 Agent 下拉里选 **Reviewer**，丢给它一句"审一下我的改动"。

### 看懂输出

- 它**没有**尝试改文件——因为工具白名单里只有搜索类工具。这就是"把约束做进配置而不是写进提示词"：
  指令可以被模型忽略，**工具白名单不能**
- 回答末尾出现 **Implement Plan 式的交接按钮**（"按意见修复"）→ handoffs 生效，点一下就带着上下文切回通用 Agent

---

## 阶段 4：Skill——把"发布流程"打包成可复用能力

### 概念：instructions 教规矩，skill 教手艺

Agent Skill 是一个开放标准（agentskills.io）的目录：`SKILL.md` + 可选的脚本与资源，**按需加载**。
和 instructions 的分工：

| | instructions | Skill |
|---|---|---|
| 装什么 | 编码规范、约定 | 一套**工作流程**（步骤、脚本、模板） |
| 何时生效 | 常驻（或按 glob 匹配文件） | **任务相关时才加载**（三级渐进：名字/描述 → 正文 → 引用的资源） |
| 可移植性 | VS Code / GitHub.com | 开放标准：Copilot CLI、cloud agent 通用 |

### 跟着做

创建 `.github/skills/release-drill/SKILL.md`（注意：**目录名必须和 name 完全一致**；本仓库已带）：

```markdown
---
name: release-drill
description: 发布演练：先验证示例回归全部通过，再从 git 状态生成符合仓库风格的提交信息草案。当用户要求"走发布流程/发个版本/准备提交"时使用。
---

# 发布演练

按顺序执行，任何一步失败就停下报告，不许带病前进：

1. 回归验证：`uv run python examples/run_all.py --offline`，确认全部通过。
2. 查看现场：`git status` + `git diff --stat`，把改动按主题分组。
3. 查看历史：`git log --oneline -5`，模仿本仓库的提交信息风格（讲清"为什么"，不写"Update xxx"）。
4. 产出：每组改动给一条提交信息草案。**只输出草案，不执行 git add / git commit。**
5. 结尾提醒：涉及讲义的改动要确认 `tools/build_site.py` 拼装无报错后再提交。
```

### 看懂输出

聊天里输入 `/`，菜单里出现 `release-drill` → 选中执行。
三个观察点：① 它**先跑了回归测试**（步骤 1 是硬门槛）；② 提交信息草案长得很像仓库既有风格（步骤 3 起作用）；
③ 它停在"草案"，把 `git commit` 的决定留给了你——**Skill 里写死的止损点，比提示词里拜托模型"要小心"可靠得多**。

> 进阶：SKILL.md 的 frontmatter 还有 `user-invocable`（是否出现在 `/` 菜单）、
> `disable-model-invocation`（是否允许模型按相关性自动加载）、`context: fork`（在独立子 agent 里跑，只把结果带回主对话）。
> 调试类、读大量文件类的大技能，`context: fork` 能保住主对话的上下文窗口。

---

## 阶段 5：Hook——不靠模型自觉的闸门

### 概念：审批是"每次问人"，hook 是"规则永远生效"

第 07 章讲过：能确定性判断的事不要交给模型。Hook 是在 agent 生命周期事件上挂的**本地命令**：
`PreToolUse` 在每次工具调用前触发，脚本从 stdin 读到事件 JSON，往 stdout 写回决策 JSON——
可以放行、可以**强制弹人工审批**、可以拦截。这本质上是你在第 03 章手写过的"循环里插一段检查"，只是循环是 VS Code 的。

### 跟着做（Local harness）

创建 `.github/hooks/audit.json`（本仓库已带，脚本已在 Node 24 上实测写入日志）：

```json
{
  "hooks": {
    "PreToolUse": [
      { "type": "command", "command": "node .github/hooks/log-tool-use.cjs" }
    ]
  }
}
```

创建 `.github/hooks/log-tool-use.cjs`（官方文档同款审计钩子）：

```javascript
const fs = require('node:fs');
let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => (input += chunk));
process.stdin.on('end', () => {
  const event = JSON.parse(input);
  fs.appendFileSync('.github/hooks/tool-use.log',
    `${event.timestamp} ${event.tool_name}\n`);
});
```

跑一个会调用工具的任务，然后看 `.github/hooks/tool-use.log`——**每一条工具调用都留了底**。
这份日志还有个妙用：**查到 Local harness 里工具的真实名字**（比如终端工具叫什么），
下一步的精确拦截就靠它，不要从别的 harness 抄工具名。

想升级成"敏感操作强制问人"，把决策写回 stdout 即可（`permissionDecision: "ask"` 强制弹审批）。
完整文件在 `.github/hooks/require-approval.cjs` + `.github/hooks/approval.json`，核心逻辑一眼能看懂：

```javascript
// require-approval.cjs（完整文件在 .github/hooks/）：命中敏感工具 → 强制人工审批
const decision = event.tool_name === process.env.SENSITIVE_TOOL_NAME
  ? { hookSpecificOutput: {
        hookEventName: 'PreToolUse',
        permissionDecision: 'ask',          // ask=弹审批；另有 allow / deny
        permissionDecisionReason: '该工具需人工确认。' } }
  : { continue: true };
process.stdout.write(JSON.stringify(decision));
```

配套配置里用 `env` 传要盯防的工具名（换目标不用改脚本）：

```jsonc
// .github/hooks/approval.json —— <tool-name> 先用审计日志查出来再填
{ "hooks": { "PreToolUse": [
    { "type": "command", "command": "node .github/hooks/require-approval.cjs",
      "env": { "SENSITIVE_TOOL_NAME": "<tool-name>" } } ] } }
```

**三步验证**：① 把 `<tool-name>` 换成审计日志里查到的真实工具名；② 让 agent 调那个工具 → 弹审批，理由就是 reason 里的字；③ 换个普通工具 → 直接放行、无感。
**注意：hook 的 stdout 只留给决策 JSON**——`console.log` 调试会污染协议，调试输出走 stderr（输出面板的 Hooks 通道看得到）。

### 用 hook 的三条纪律（官方安全建议，原文照录的意思）

- Hook 以 harness 进程的权限执行——**把它当可执行代码 review**，别人的仓库里带 hook 配置时尤其如此
- Hook 输入一律当不可信：JSON 解析后再用，别直接拼进 shell
- 密钥只进密钥存储，不进 hook 配置、脚本和输出

---

## 阶段 6：串成一条真实流程

五件套就位后，本仓库的定制文件地图长这样：

```
.
├── .github/
│   ├── copilot-instructions.md      # ✔ 常驻：仓库约定（阶段 1）
│   ├── agents/reviewer.agent.md     # ✔ 角色：只读评审员（阶段 3）
│   ├── skills/release-drill/        # ✔ 流程：发布演练（阶段 4）
│   │   └── SKILL.md
│   └── hooks/                       # ✔ 闸门：审计 + 强制审批（阶段 5）
│       ├── audit.json               #   挂钩子：PreToolUse → 记日志
│       ├── log-tool-use.cjs         #   记日志（Node 24 实测通过）
│       ├── approval.json            #   挂钩子：敏感工具 → 强制审批（工具名先填）
│       └── require-approval.cjs     #   写回决策 JSON
├── .mcp.json                        # ✔ 工具：docs server（可移植格式，提交这份）
├── .vscode/mcp.json                 #   同一台 server 的本机配置（.vscode/ 已 gitignore）
└── tools/mcp/docs_server.py         #   ↑ 它启动的 server
```

（✔ = 文件已随仓库提供，打开即用；在你自己的仓库里练手时，照着各阶段亲手写一遍。）

一次真实的"改讲义"工作流（你在自己仓库照做即可）：

1. **选模型**：BYOK 的 Agnes；**选 Agent**：内置通用 Agent
2. "把第 06 章的示例索引补充 06c 的说明，用 tutorial-docs 工具确认行号没有过期" → 它查仓库、改文件
3. **切到 Reviewer**："审一下我的改动" → 拿到带位置和修法的意见清单
4. **切回通用 Agent**，点 Reviewer 留下的交接按钮（或自己说）："按意见逐条修复，修完跑离线回归"
5. `/release-drill` → 回归通过、拿到分组提交信息草案 → 你亲自逐组提交
6. 全程 `.github/hooks/tool-use.log` 里留有审计痕迹

注意这个流程的形状：**你只在两个点做决定（采纳哪些意见、是否提交），其余是配置在替你把关。**
这就是第 13 章"流程可控 > 智能涌现"的编辑器版——只是你一行编排代码都没写。

---

## 自己动手改（改坏比跑通学得多）

1. **把 `reviewer.agent.md` 的 `tools` 删掉**，重新审一次改动——观察它开始尝试编辑文件。
   体会"约束做进工具白名单"和"约束写进提示词"的可靠性差距。
2. **给 `docs_server.py` 加第三个工具** `get_chapter(name)`：返回整章内容。重启 MCP server
   （命令面板 → MCP: List Servers → Restart）后再问一个问题，观察它选择用哪个工具。
3. **把 `release-drill` 的步骤 1 改成在线组**（`run_all.py` 不带 `--offline`），没填 Key 的机器上跑一次，
   观察它如何报告失败——以及它有没有"自作主张"跳过失败继续走（Skill 里的"停下报告"就是防这个的）。
4. **故意写错 skill 名**：目录叫 `release-drills`、frontmatter 里叫 `release-drill`。
   观察现象：`/` 菜单里**什么都没出现，也没有任何报错**——这就是名字不匹配 = 静默失效。

---

## 验收问题

答不上来就回读，别往下走：

1. BYOK 和 Copilot 登录各覆盖什么？哪些功能 BYOK 给不了？
2. 一段"发布前要跑的检查清单"，写成 instructions、Skill、MCP server 有什么区别？你的默认选择是哪个？
3. 为什么 Reviewer 的"不改文件"要用工具白名单实现，而不是只写在指令里？
4. Hook 和聊天里每次弹的审批对话框，分别解决什么问题？重复吗？
5. 你配置的 skill 没出现在 `/` 菜单里，列出三个可能原因。

---

## 坑（这一章最容易踩的地方）

| 现象 | 原因 | 解决 |
|---|---|---|
| 加的模型不在选择器里 | 没重启 / 模型不支持工具调用 | 重启 VS Code；确认 `toolCalling: true` 且模型真会调工具 |
| `chatLanguageModels.json` 里裸写 Key | 图省事 | 用 `${input:...}` 输入变量；这文件别提交 |
| Skill 写了但 `/` 菜单没有，**无报错** | `name` 与目录名不一致，或含点/斜杠/冒号 | 名字只能小写字母、数字、连字符；必须与目录名完全一致 |
| `.claude/settings.json` 格式的 hook 不生效 | `chat.useClaudeHooks` 默认关闭 | 开它；且 Local 会忽略 matcher（事件里的每条命令都会跑） |
| hook 好像根本没跑 | 工作区不受信任 / 设置关了 | `chat.useHooks` 默认开，但要求受信任的工作区；排查用 Show Agent Debug Logs 和输出面板的 Hooks 通道 |
| 团队拿不到我的 MCP server | 配置写进了 `.vscode/mcp.json`（本仓库 gitignore 了它） | 共享配置放根目录 `.mcp.json`（`mcpServers` 顶层键） |
| Copilot 会话里 MCP 工具不见了 | Agent Host 不直接读 `.vscode/mcp.json` | 用工作区 `.mcp.json` 或用户级 `~/.copilot/mcp-config.json` |
| `Cannot have more than 128 tools per request` | 挂的工具太多 | 工具选择器里整组关掉不相关 server |
| 老教程的 `from mcp.server.fastmcp import FastMCP` 报 `ModuleNotFoundError` | **mcp 2.x 把 FastMCP 改名为 `MCPServer`**（`mcp.server.mcpserver`） | 用本章的 2.x 写法；或按官方迁移指南临时 `mcp<2` |
| Agent 一顿操作把额度跑光 | 多轮工具调用 + 连跑测试很费 token；免费额度有 429 限速 | 先用离线组验证；撞 429 等 20s 再试（第 00 章实测过） |
| hook 脚本 print 中文直接崩 | Windows GBK 控制台（第 00 章的老坑在 hook 里重演） | hook 输出用英文或 ASCII；要中文就设 `PYTHONIOENCODING=utf-8` |
| 有人推荐你用 `.prompt.md` 提示文件 | prompt files 已弃用（Agent Host 不加载），官方建议迁移成 skill | 新东西一律写 skill |

---

## 想深挖（官方文档，2026-09-23 核对过的直链）

- Agent 定制总览（Agent Customizations 编辑器、作用域、迁移）：`https://code.visualstudio.com/docs/agent-customization/overview`
- 项目指令与 `AGENTS.md`：`https://code.visualstudio.com/docs/agent-customization/custom-instructions`
- 自定义 Agent（frontmatter 字段全表）：`https://code.visualstudio.com/docs/agent-customization/custom-agents`
- Agent Skills（开放标准、三级加载）：`https://code.visualstudio.com/docs/agent-customization/agent-skills`
- Hooks（预览；四种 harness 的差异必读）：`https://code.visualstudio.com/docs/agent-customization/hooks`
- MCP servers（配置格式、信任、沙箱）：`https://code.visualstudio.com/docs/agent-customization/mcp-servers`
- 模型与 BYOK（Custom Endpoint 字段参考）：`https://code.visualstudio.com/docs/agent-customization/language-models`
- 工具体系（内置工具、审批、128 上限）：`https://code.visualstudio.com/docs/agents/run/tools`
- 智能体总览：`https://code.visualstudio.com/docs/agents/overview`

> 和第 14 章同样的纪律：**凡是不确定的行为，先在 Agent Debug Logs（命令面板 → Developer: Open Agent Debug Logs）里看真相，再改配置。**

---

← 上一章 [14 附录：API 速查与排错](14-附录.md) ｜ 回到 [目录](README.md)
