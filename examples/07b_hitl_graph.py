"""07b — 图 + 人工审批（需要 Key）

真实业务流程：模型先起草处理意见，金额超过阈值时必须有人点头，才真正执行。
关键是 interrupt() 让程序停在中间，把现场存起来，等人回答再继续。

这和第 07 章开头那个离线例子（07a）是同一个机制，区别是这里的"草案"由模型生成。

脚本自带断言（`_shared.Checks`）：小额**不该**中断、大额**必须**中断，
而且人工拒绝后绝不能走成受理（越权比答错严重得多）。失败即以非 0 退出码结束。
"""

import sys

from typing_extensions import TypedDict

from _shared import Checks, get_model, title

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

CHECKS = Checks()

APPROVAL_THRESHOLD = 500          # 超过这个金额，必须人工审批


class RefundState(TypedDict):
    request: str
    amount: int
    draft: str          # 模型起草的处理意见
    approved: bool
    result: str


def draft_reply(state: RefundState) -> dict:
    """用模型起草一份处理意见。"""
    model = get_model(temperature=0)
    prompt = (
        f"顾客的诉求：{state['request']}\n"
        f"涉及金额：{state['amount']} 元\n"
        "请用 2 句话起草给顾客的回复，语气礼貌，说明接下来会怎么处理。"
    )
    draft = model.invoke(prompt).content
    print(f"  [draft] 模型起草：{draft[:60]}...")
    return {"draft": draft}


def maybe_approve(state: RefundState) -> dict:
    """小额自动放行；大额挂起等人工。"""
    if state["amount"] <= APPROVAL_THRESHOLD:
        print(f"  [approve] {state['amount']} 元 未超阈值，自动放行")
        return {"approved": True}

    print(f"  [approve] {state['amount']} 元 超过阈值 {APPROVAL_THRESHOLD}，等待人工审批")
    # ⚠️ 这一行之前的代码在恢复时会重跑，别在这里写副作用
    decision = interrupt(
        {
            "问题": f"是否同意退款 {state['amount']} 元？",
            "诉求": state["request"],
            "模型草案": state["draft"],
            "选项": ["同意", "拒绝"],
        }
    )
    print(f"  [approve] 人工决定：{decision}")
    return {"approved": bool(decision)}


def finalize(state: RefundState) -> dict:
    if state["approved"]:
        result = f"【已受理】{state['draft']}"
    else:
        result = "【已驳回】很抱歉，本次退款未通过审批，我们会再联系您说明原因。"
    print(f"  [finalize] {result[:40]}...")
    return {"result": result}


def build_graph():
    builder = StateGraph(RefundState)
    builder.add_node("draft", draft_reply)
    builder.add_node("approve", maybe_approve)
    builder.add_node("finalize", finalize)
    builder.add_edge(START, "draft")
    builder.add_edge("draft", "approve")
    builder.add_edge("approve", "finalize")
    builder.add_edge("finalize", END)
    return builder.compile(checkpointer=InMemorySaver())


def run(graph, request: str, amount: int, thread_id: str,
        human_says: bool | None = None) -> dict:
    """跑一轮。返回 {是否中断, 最终是否受理, 结果文本, 模型草案}，供断言检查。"""
    config = {"configurable": {"thread_id": thread_id}}
    state_in = {"request": request, "amount": amount, "draft": "", "approved": False, "result": ""}

    result = graph.invoke(state_in, config)
    pending = result.get("__interrupt__")

    if not pending:
        print(f"  → 直接完成：{result['result'][:50]}")
        return {"interrupted": False, "approved": bool(result.get("approved")),
                "result": result.get("result", ""), "draft": result.get("draft", "")}

    print(f"\n  ⏸  已暂停，等待人工。审批内容：{pending[0].value if pending else ''}")
    decision = human_says if human_says is not None else True
    print(f"  人工回答：{'同意' if decision else '拒绝'}")
    final = graph.invoke(Command(resume=decision), config)
    print(f"  → 最终结果：{final['result'][:60]}")
    return {"interrupted": True, "approved": bool(final.get("approved")),
            "result": final.get("result", ""), "draft": final.get("draft", "")}


def main() -> None:
    graph = build_graph()

    title("场景 1：小额退款，自动通过（不会中断）")
    r1 = run(graph, "咖啡洒了想退款", 38, "case-1")
    CHECKS.expect(not r1["interrupted"], "38 元没超阈值 → 不该打断等人（阈值写在代码里）")
    CHECKS.expect(bool(r1["draft"]), "模型确实起草了回复（draft 非空）")
    CHECKS.expect("已受理" in r1["result"], "小额单直接走受理分支")

    title("场景 2：大额退款，人工同意")
    r2 = run(graph, "整单退款，活动取消", 1280, "case-2", human_says=True)
    CHECKS.expect(r2["interrupted"], "1280 元超阈值 → 必须中断等人点头")
    CHECKS.expect("已受理" in r2["result"], "人工同意后才走受理分支")

    title("场景 3：大额退款，人工拒绝")
    r3 = run(graph, "想退三个月前的订单", 2000, "case-3", human_says=False)
    CHECKS.expect(r3["interrupted"], "2000 元超阈值 → 必须中断等人点头")
    CHECKS.expect(not r3["approved"] and "已驳回" in r3["result"],
                  "人工拒绝后绝不能走成受理（越权比答错严重）")

    title("这套做法的价值")
    print("  - 模型负责起草，人负责拍板，各自做擅长的事")
    print("  - 阈值是显式业务规则，不在 prompt 里求模型自觉")
    print("  - 中断现场存在数据库里，人可以第二天再来点同意")
    print("  - 换成 PostgresSaver，服务重启也不丢")


if __name__ == "__main__":
    main()
    sys.exit(CHECKS.report())
