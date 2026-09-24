# 仓库约定（教程第 15 章的阶段 1 示例，也是本仓库真实生效的项目指令）

* Python 教程仓库：讲义在 `tutorial/`，可跑示例在 `examples/`，文件名开头数字 = 讲义章号。
* 改讲义保持每章统一结构：本章目标 / 概念 / 跟着做 / 看懂输出 / 自己动手改 / 验收问题 / 坑 / 想深挖。
* 示例改动后必须验证：`uv run python examples/run_all.py --offline`（离线组，不需要 Key）。
* 示例里的检查要写成**断言**（`_shared.Checks` + `sys.exit(checks.report())`），不要只 `print("❌ ...")`——打印不影响退出码，run_all 看不见。
* 需要 Key 的例子里，断言写在**语义特征**上（第 11 章）：容忍措辞/千分位差异，但不容忍行为差异（编造、跳过审批、拒绝后还受理）。先跑 `run_all.py --offline`，再跑 `--live`。
* 改了离线实验的**断言 / 校验逻辑**后，再跑 `uv run python examples/mutation_check.py`（离线秒级）：它把关键不变量逐个改坏，要求示例真的变红；有变异"存活"就以非 0 退出码结束。
* API Key 只出现在 `examples/.env`（已 gitignore）；示例代码一律从环境变量读配置。
* 文风：先类比后术语，说人话；不写没验证过的 API，不确定的写明"先用 inspect.signature 验证"。
