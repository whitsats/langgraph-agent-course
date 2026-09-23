"""03 — 人工审批：暂停 / 恢复（离线可跑，不需要 Key）

程序跑到一半停下来等你点头，然后从原地继续。
这就是把「人不放心的地方」交给人的标准做法，也是 interrupt() 的唯一用途。

重点观察两件事：
  1. 第一次运行会停在 interrupt()，并把现场存进 checkpointer
  2. 恢复时，【节点会从头再跑一遍】——interrupt() 之前的代码会再执行一次
"""

from typing_extensions import TypedDict

import _shared  # noqa: F401  （导入时会把 Windows 控制台切到 UTF-8，避免打印 emoji 崩溃）
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class OrderState(TypedDict):
    order_id: str
    amount: int
    approved: bool
    shipped: bool


def submit(state: OrderState) -> dict:
    print(f"  [submit] 提交订单 {state['order_id']}，金额 {state['amount']} 元")
    return {}


def approve(state: OrderState) -> dict:
    # ⚠️ 这一行在【恢复时会再执行一次】。所以不要在这里写副作用（发消息、扣款、写文件）。
    print("  [approve] 进入审批节点（第一次会停在这里）")

    decision = interrupt(
        {
            "问题": f"订单 {state['order_id']} 金额 {state['amount']} 元，是否批准？",
            "选项": ["同意", "拒绝"],
        }
    )
    print(f"  [approve] 收到人工决定: {decision}")
    return {"approved": bool(decision)}


def ship(state: OrderState) -> dict:
    if state["approved"]:
        print("  [ship] 已发货 ✅")
        return {"shipped": True}
    print("  [ship] 未批准，取消订单 ❌")
    return {"shipped": False}


def build_graph():
    builder = StateGraph(OrderState)
    builder.add_node("submit", submit)
    builder.add_node("approve", approve)
    builder.add_node("ship", ship)
    builder.add_edge(START, "submit")
    builder.add_edge("submit", "approve")
    builder.add_edge("approve", "ship")
    builder.add_edge("ship", END)
    # ★ 中断必须有 checkpointer，否则没地方存暂停现场
    return builder.compile(checkpointer=InMemorySaver())


def main() -> None:
    graph = build_graph()
    config = {"configurable": {"thread_id": "order-A-1"}}      # ★ 必须有

    print("=" * 60)
    print("第一次运行：跑到审批节点会停下来")
    print("=" * 60)
    result = graph.invoke({"order_id": "A-1", "amount": 1280, "approved": False, "shipped": False}, config)

    # invoke 用法下，中断信息在 __interrupt__ 里（用 stream_events 则看 stream.interrupts）
    interrupts = result.get("__interrupt__")
    print(f"\n  程序已暂停。需要人工回答的内容：")
    print(f"  {interrupts}")

    print("\n" + "=" * 60)
    print("恢复运行：把人的决定传回去")
    print("=" * 60)
    final = graph.invoke(Command(resume=True), config)        # resume 的值 = interrupt() 的返回值

    print(f"\n  最终状态: {final}")
    print("\n记忆点：")
    print("  - interrupt() 需要 checkpointer + 同一个 thread_id")
    print("  - 恢复时该节点从头重跑，所以 interrupt() 之前不能放副作用")
    print("  - 生产里要换成持久 checkpointer（Postgres/Redis/SQLite），才能跨进程恢复")


if __name__ == "__main__":
    main()
