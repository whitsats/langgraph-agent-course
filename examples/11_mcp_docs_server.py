"""11 — MCP：不写工具也能有工具（需要 Key + 网络）

MCP 是"工具的 USB 接口"。接上别人的 MCP server，工具就自动出现在你手里。

这里连的是官方文档自己的公开 server（https://docs.langchain.com/mcp，无需额外 Key），
所以这个例子能直接跑通，不用自己写 server。

依赖：uv add "langchain[mcp]"
注意：langchain.mcp 目前是 beta，导入时会打印一次 LangChainBetaWarning。
"""

import asyncio

from _shared import get_model, title

from langchain.agents import create_agent
from langchain.mcp import MCPAdapter

DOCS_SERVER = "https://docs.langchain.com/mcp"


async def main() -> None:
    # MCPAdapter 会根据你给的 target 自动判断连接方式：
    #   "https://..."        → 远程 HTTP
    #   Path("server.py")    → 本地脚本（子进程 stdio）
    #   FastMCP 实例          → 进程内（写测试最合适）
    #   {"mcpServers": {...}} → 一次挂多个 server
    async with MCPAdapter(DOCS_SERVER) as adapter:
        tools = await adapter.list_tools()

        title("这个 MCP server 提供了哪些工具")
        for t in tools:
            print(f"  - {t.name}: {t.description[:70]}")

        # 这些工具和 @tool 写出来的东西没有区别，直接丢给 agent
        agent = create_agent(
            get_model(),
            tools,
            system_prompt="你是一个技术助理。回答 LangChain/LangGraph 的问题时必须先查文档。",
        )

        title("问一个需要查文档的问题")
        question = "怎么给 agent 加短期记忆？"
        print(f"问：{question}\n")
        result = await agent.ainvoke({"messages": [{"role": "user", "content": question}]})

        # 看看它调用了哪些 MCP 工具
        for msg in result["messages"]:
            for call in getattr(msg, "tool_calls", None) or []:
                print(f"  🔧 调用 MCP 工具: {call['name']}")

        print(f"\n答：{result['messages'][-1].content[:400]}...")

    title("什么时候该上 MCP")
    print("  ✅ 工具要被多个 agent / 多个客户端共享")
    print("  ✅ 要接别人已经写好的 server（GitHub、数据库、内部系统）")
    print("  ❌ 自家项目就调两个函数 → 用 @tool 够了，别为架构而架构")
    print("\n  安全提醒：MCPAdapter 拒绝非 URL 字符串，防止把配置里的路径当命令执行——别绕过。")


if __name__ == "__main__":
    asyncio.run(main())
