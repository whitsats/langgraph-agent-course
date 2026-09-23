"""01 — reducer 与条件边（离线可跑，不需要 Key）

LangGraph 两个最重要的基础：
  1. reducer：节点返回的值怎么并入状态（不写 = 覆盖！）
  2. 条件边：下一步走哪个节点由函数决定

跑起来看输出，比读十遍文档清楚。
"""

from operator import add
from typing import Annotated

import _shared  # noqa: F401  （导入时会把 Windows 控制台切到 UTF-8，避免打印中文乱码）
from typing_extensions import TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Overwrite


# ===========================================================================
# 第一部分：三种 reducer 的差别
# ===========================================================================

class OverwriteState(TypedDict):
    items: list[str]          # 没写 reducer → 默认【覆盖】


class AppendState(TypedDict):
    items: Annotated[list[str], add]      # 用 operator.add → 【累加】


def append_b(state: AppendState) -> dict:
    """节点只需要返回"这次的变化"，不用返回整个状态。"""
    return {"items": ["b"]}


def demo_reducers() -> None:
    print("=" * 60)
    print("第一部分：reducer")
    print("=" * 60)

    # --- 覆盖（默认）---
    g1 = StateGraph(OverwriteState)
    g1.add_node("add_b", lambda s: {"items": ["b"]})
    g1.add_edge(START, "add_b")
    g1.add_edge("add_b", END)
    result = g1.compile().invoke({"items": ["a"]})
    print(f"没写 reducer      : {result['items']}   ← 'a' 被吃掉了")

    # --- 累加 ---
    g2 = StateGraph(AppendState)
    g2.add_node("add_b", append_b)
    g2.add_edge(START, "add_b")
    g2.add_edge("add_b", END)
    result = g2.compile().invoke({"items": ["a"]})
    print(f"Annotated[..., add]: {result['items']}   ← 这才是我们要的")

    # --- 想清空？返回空值没用，必须 Overwrite ---
    class ClearState(TypedDict):
        items: Annotated[list[str], add]
        cleared_at: str

    g3 = StateGraph(ClearState)
    g3.add_node("wrong", lambda s: {"items": []})                    # 错误的清空方式
    g3.add_edge(START, "wrong")
    g3.add_edge("wrong", END)
    result = g3.compile().invoke({"items": ["a", "b"], "cleared_at": "-"})
    print(f"返回空 list       : {result['items']}   ← 空值被合并进去，根本没清掉")

    g4 = StateGraph(ClearState)
    g4.add_node("right", lambda s: {"items": Overwrite([])})         # 正确的清空方式
    g4.add_edge(START, "right")
    g4.add_edge("right", END)
    result = g4.compile().invoke({"items": ["a", "b"], "cleared_at": "-"})
    print(f"Overwrite([])     : {result['items']}      ← 绕过 reducer，真正清空")

    print("\n记忆点：不写 reducer 就是覆盖；想清空带合并 reducer 的字段必须 Overwrite。")


# ===========================================================================
# 第二部分：条件边（用日常场景：订单审核）
# ===========================================================================

class OrderState(TypedDict):
    amount: int
    decision: str
    note: str


def check_order(state: OrderState) -> dict:
    print(f"  [check] 收到订单，金额 {state['amount']} 元")
    return {}


def route_by_amount(state: OrderState) -> str:
    """路由函数：只负责"下一步去哪"，返回的字符串必须是节点名。"""
    if state["amount"] <= 200:
        return "auto_approve"
    if state["amount"] <= 5000:
        return "manual_review"
    return "reject"


def auto_approve(state: OrderState) -> dict:
    print("  [auto_approve] 小额订单，自动放行")
    return {"decision": "approved", "note": "自动通过"}


def manual_review(state: OrderState) -> dict:
    print("  [manual_review] 中等金额，转人工复核")
    return {"decision": "pending", "note": "等待人工"}


def reject(state: OrderState) -> dict:
    print("  [reject] 金额过大，直接拒绝")
    return {"decision": "rejected", "note": "超限"}


def demo_branching() -> None:
    print("\n" + "=" * 60)
    print("第二部分：条件边（订单审核）")
    print("=" * 60)

    builder = StateGraph(OrderState)
    builder.add_node("check", check_order)
    builder.add_node("auto_approve", auto_approve)
    builder.add_node("manual_review", manual_review)
    builder.add_node("reject", reject)

    builder.add_edge(START, "check")
    builder.add_conditional_edges("check", route_by_amount)   # ★ 分流在这里
    builder.add_edge("auto_approve", END)
    builder.add_edge("manual_review", END)
    builder.add_edge("reject", END)

    graph = builder.compile()

    for amount in (88, 1280, 99999):
        print(f"\n下单 {amount} 元：")
        result = graph.invoke({"amount": amount, "decision": "", "note": ""})
        print(f"  → 结论: {result['decision']} ({result['note']})")

    print("\n记忆点：条件边就是把 if-else 挪到图外面，")
    print("        所以你的业务规则能单独测试，不跟模型混在一起。")


if __name__ == "__main__":
    demo_reducers()
    demo_branching()
