# virtual_rnd_center — 虚拟研发中心（案例工程）

一个用 **CrewAI Flow** 编排的多智能体研发流水线：需求裁剪 → 架构与代码生成 → 代码审查 → 容器部署 → 接口测试，并在关键网关处插入「红蓝对抗 + 人工裁决 + 重工循环」。

> 这是**案例**，不是教程。它的价值在于设计取舍与踩过的坑，见仓库根目录 `LEARNING_PLAN.md` 第 9 节的设计对照表。
> 设计理由见 `virtual_rnd_center_presentation.md`。

---

## 快速上手

### 1. 依赖

```bash
# 需要 Python >=3.10,<3.14；本目录已自带 uv.lock
uv sync
```

### 2. 配置密钥

复制 `.env` 模板并填入真实值。**代码实际读取的变量名如下**（注意不是 `OPENAI_API_KEY`）：

| 变量 | 是否必需 | 说明 |
|---|---|---|
| `DEEPSEEK_API_KEY` | ✅ 必需 | 模型密钥，`utils/llm_factory.py` 读取 |
| `OPENAI_API_BASE` | ✅ 必需 | 模型网关地址，默认 `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | ✅ 必需 | 模型名，如 `deepseek-v4-pro` |
| `SERPER_API_KEY` | 可选 | 联网检索工具使用 |
| `STREAM_THOUGHTS` | 可选 | `true` 时打印每步思考 |
| `CREWAI_TRACING_ENABLED` / `CREWAI_LOG_LEVEL` | 可选 | 可观测性与日志级别 |

> 换任何 OpenAI 兼容网关（含 Agnes 这类平台）只需要改上面三个字段：`base_url` + `api_key` + 模型名。
> ⚠️ 但注意 `LLMFactory` 里对模型名加了 LiteLLM 的 provider 前缀（`model = f"deepseek/{model_name}"`），换网关时这个前缀也要一起改，否则会报找不到模型。

### 3. 运行

四种模式通过环境变量 `RND_MODE` 切换（默认 `mvp`）：

```bash
uv run kickoff                    # 默认 MVP 模式
RND_MODE=enterprise uv run kickoff
RND_MODE=backend    uv run kickoff
RND_MODE=frontend   uv run kickoff

uv run plot                       # 生成流程图 HTML（virtual_rnd_flow.html）
```

`pyproject.toml` 里注册的入口：`kickoff` / `run_crew` / `plot` / `run_with_trigger`。若已安装 CrewAI CLI，`crewai run` 等价。

各模式的产物目录：

| 模式 | 输出目录 | 输入类型 |
|---|---|---|
| `mvp` | `output/mvp_project/` | 人类自然语言需求（写在 `main.py:kickoff()` 里，可直接改） |
| `enterprise` | `output/enterprise_project/` | 人类自然语言需求 |
| `backend` | `output/backend_project/` | 本地 PRD 文档 |
| `frontend` | `output/frontend_project/` | 本地 PRD + UI 规范文档 |

### 4. 运行时的两个行为要知道

- **所有控制台输出会被同时写入 `output/session_audit.log`**。`main.py` 在导入时就把 `sys.stdout` 换成了 `LoggerTee`（且不会恢复），所以别在这个进程里做依赖真实 stdout 的事。
- **终端交互式裁决**：判定为「未通过」时会挂起并弹出中文菜单（强行通过 / 打回重工 / 打回并注入自定义整改意见 / 遵循自动裁决）。非 TTY 环境（如重定向、CI）会自动跳过人工步骤。

---

## 产物长什么样

跑完一轮，`output/mvp_project/` 里是这样的：

```
requirements.md          # 需求（BA 落盘，作为下游唯一信源）
boundary_manifest.md     # 边界清单 + 违禁功能清单
tech_specs.md            # 技术契约（端口、健康检查、接口）
code_review_report.md    # 代码审查结论
deployment_report.md     # 部署结论
qa_report.md             # 接口测试结论
backend/ frontend/       # 实际生成的源码
docker-compose.yml
```

`output/confrontation_report.md` 是每轮的胜负汇总表。

---

## 已知问题（读代码前先看，省得被误导）

这些是案例里真实存在的问题，**当作反面教材读，不要照抄**：

| 位置 | 问题 |
|---|---|
| `main.py` `_read_verdict_from` | 靠正则在 Markdown 报告里找 `APPROVED`/`REJECTED` 字样判定成败——报告里出现该词即命中，极易误判。正确做法是结构化输出（Pydantic） |
| `tools/docker_mcp_tool.py` | 部署失败或抛异常时返回**伪造的** `RUNNING (healthy)`。生产里这是流水线撒谎 |
| `tools/docker_mcp_tool.py` | 用 `subprocess(shell=True)` 拼接字符串执行，是工具越权/注入的经典面；且名为 MCP 实际不是 MCP（`.env` 里的 `DOCKER_MCP_GATEWAY_URL` 全程未使用） |
| `crews/*/config/*.py` | 所有 Agent 都是 `reasoning=False`，与设计说明里宣称的"自省推理环"不符；全项目也没有一处 `output_pydantic` |
| `crews/enterprise_crew/config/tasks.yaml` | 让 Agent 读 `templates/enterprise/prd.tpl.md`，但该文件不存在（目录里只有 code_audit/impl_plan/research/sad），必然白烧一轮 |
| `src/virtual_rnd_center/config/*.yaml` | 与各 crew 的 `config/` 并存，且未被任何 Crew 引用，疑似死配置（未删，未验证） |
| `src/virtual_rnd_center/main.py` | 685 行；判定逻辑在 `quality_gate` / `rework_gate` 中重复两遍；`import datetime` 两次、`import shutil` 未使用 |
| 四个模式的完整性 | 只有 MVP 模式有完整的红蓝重工闭环；`enterprise/backend/frontend` 的 gate 直接返回 `success_exit` |
| `tests/` | 空目录，项目没有任何测试 |
