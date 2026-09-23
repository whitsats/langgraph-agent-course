"""06b — 短期记忆：让 agent 记住上下文（需要 Key）

agent 本身不记得任何东西。"记忆"是基础设施：状态被存进 checkpointer，
用 thread_id 区分不同的会话。

观察重点：同一个 thread_id → 记得；换个 thread_id → 立刻失忆。
"""

from _shared import get_model, title

from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver


def ask(agent, question: str, thread_id: str) -> str:
    config = {"configurable": {"thread_id": thread_id}}       # ★ 会话 id
    result = agent.invoke({"messages": [{"role": "user", "content": question}]}, config)
    return result["messages"][-1].content


def main() -> None:
    # 开发用内存版；生产换成持久版，API 完全一样：
    #   from langgraph.checkpoint.postgres import PostgresSaver
    #   from langgraph.checkpoint.sqlite import SqliteSaver
    agent = create_agent(
        model=get_model(),
        tools=[],
        system_prompt="你是一个咖啡店客服。回答要简短。",
        checkpointer=InMemorySaver(),        # ★ 没有它就没有记忆
    )

    title("第 1 轮（thread = customer-001）：告诉它我的名字和口味")
    print(" ", ask(agent, "你好！我叫小明，我平时只喝不加糖的拿铁。", "customer-001"))

    title("第 2 轮（同一个 thread）：它记得吗？")
    print(" ", ask(agent, "我想点杯咖啡，你有什么建议？", "customer-001"))
    print("\n  ↑ 如果它提到'不加糖的拿铁'，说明记忆生效了。")

    title("第 3 轮（换一个 thread）：它会立刻失忆")
    print(" ", ask(agent, "我想点杯咖啡，你有什么建议？", "customer-002"))
    print("\n  ↑ 换了 thread_id，它不知道你是谁了——这正是多用户隔离的原理。")

    title("生产环境怎么换")
    print("  把 checkpointer 换成数据库即可，业务代码一行都不用改：")
    print("    from langgraph.checkpoint.postgres import PostgresSaver")
    print("    with PostgresSaver.from_conn_string(DB_URI) as cp:   # 首次要 cp.setup()")
    print("        agent = create_agent(..., checkpointer=cp)")
    print("\n  这就是为什么你不需要自己搭一套 Redis 会话存储。")


if __name__ == "__main__":
    main()
