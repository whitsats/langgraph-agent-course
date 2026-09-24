"""把本教程的讲义变成 MCP 工具 —— 教程第 15 章（附录B）的配套 server。

用 VS Code 试它：
  1. .vscode/mcp.json 里注册（见第 15 章阶段 2）
  2. 保存后信任并启动 server
  3. 聊天里问："用 tutorial-docs 搜一下哪章讲 checkpointer"

注意：用的是 mcp 2.x 的 MCPServer（旧教程里的 FastMCP 在 2.x 已改名，
from mcp.server.fastmcp import FastMCP 会直接 ModuleNotFoundError）。
"""

from __future__ import annotations

from pathlib import Path

from mcp.server.mcpserver import MCPServer

DOCS = Path(__file__).resolve().parents[2] / "tutorial"

server = MCPServer(
    "tutorial-docs",
    instructions="LangChain+LangGraph 教程检索工具：列章节、按关键词搜讲义。",
)


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
