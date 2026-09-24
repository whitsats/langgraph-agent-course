"""docs_server 的回归测试 —— 不需要 API Key，不需要启动 VS Code。

两种跑法：
    uv run python tools/mcp/test_docs_server.py          # 直接跑（退出码 0 = 全过）
    uv run python examples/run_all.py --offline          # 习惯示例回归后，把这个也纳入

测三层：
  1. 工具函数本身（列章节、搜关键词、命中上限）
  2. 异常输入不崩（第 15 章坑表里"关键词含换行直接崩"的回归）
  3. JSON-RPC 握手（VS Code 连接 server 时走的第一步）
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import docs_server  # noqa: E402

# Windows GBK 控制台打印 ✓ 会直接崩（本教程坑表第 00/15 章都记过这条），
# 复用 examples/_shared.py 的统一入口切 UTF-8。
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "examples"))
from _shared import setup_console  # noqa: E402

setup_console()

FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    tag = "PASS" if cond else "FAIL"
    print(f"  [{tag}] {name}" + (f" —— {detail}" if detail and not cond else ""))
    if not cond:
        FAILURES.append(name)


print("第 1 层：工具函数")
chapters = docs_server.list_chapters()
check("list_chapters 返回非空列表", isinstance(chapters, list) and len(chapters) >= 15,
      f"实际 {len(chapters)} 章")
check("列表里含 06 章与 15 章", any(n.startswith("06") for n in chapters)
      and any(n.startswith("15") for n in chapters))

hits = docs_server.search_tutorial("checkpointer")
check("search_tutorial('checkpointer') 有命中", len(hits) > 0)
check("命中带 file/line/text 三个字段",
      all({"file", "line", "text"} <= set(h) for h in hits))
check("命中上限 20 条生效", len(hits) <= 20)
check("搜不到的东西返回空列表", docs_server.search_tutorial("绝不存在的词xyzzy") == [])

print("第 2 层：异常输入不崩")
weird = ["", " ", "\n", "%s%d", "checkpointer\nother"]
for kw in weird:
    try:
        docs_server.search_tutorial(kw)
        check(f"关键词 {kw!r} 不崩", True)
    except Exception as e:  # noqa: BLE001
        check(f"关键词 {kw!r} 不崩", False, repr(e))

print("第 3 层：JSON-RPC 握手（stdio）")
proc = subprocess.run(
    ["uv", "run", "python", "tools/mcp/docs_server.py"],
    input=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                      "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                                 "clientInfo": {"name": "probe", "version": "0"}}}),
    capture_output=True, text=True, encoding="utf-8", timeout=60,
)
try:
    reply = json.loads(proc.stdout)
    check("initialize 返回合法 JSON-RPC result", "result" in reply)
    check("serverInfo.name == tutorial-docs",
          reply["result"]["serverInfo"]["name"] == "tutorial-docs")
    check("声明 tools 能力", "tools" in reply["result"]["capabilities"])
except json.JSONDecodeError as e:
    check("initialize 返回合法 JSON-RPC result", False, f"{e}; stdout[:200]={proc.stdout[:200]!r}")

print()
if FAILURES:
    print(f"✗ {len(FAILURES)} 项未通过：{FAILURES}")
    sys.exit(1)
print("✓ docs_server 回归全部通过")
