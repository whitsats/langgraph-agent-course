# 仓库约定（教程第 15 章的阶段 1 示例，也是本仓库真实生效的项目指令）

* Python 教程仓库：讲义在 `tutorial/`，可跑示例在 `examples/`，文件名开头数字 = 讲义章号。
* 改讲义保持每章统一结构：本章目标 / 概念 / 跟着做 / 看懂输出 / 自己动手改 / 验收问题 / 坑 / 想深挖。
* 示例改动后必须验证：`uv run python examples/run_all.py --offline`（离线组，不需要 Key）。
* API Key 只出现在 `examples/.env`（已 gitignore）；示例代码一律从环境变量读配置。
* 文风：先类比后术语，说人话；不写没验证过的 API，不确定的写明"先用 inspect.signature 验证"。
