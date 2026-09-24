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
