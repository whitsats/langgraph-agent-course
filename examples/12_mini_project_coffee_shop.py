"""12 — 完整小项目：咖啡店客服（需要 Key）★ 把零件拼成能交付的最小形态

前面每个例子只讲一件事。这个文件把它们拼起来，就是一个真实可交付的形态：

    LangGraph 状态机    → 流程可控、能分支、能断点续跑
    结构化输出          → 意图识别不靠正则
    工具 + 知识         → 回答有依据
    人工审批            → 大额操作必须人点头
    checkpointer        → 同一 thread 记住上下文

流程：
    START → classify ─┬─ 咨询 → answer ───────────────→ finalize → END
                      └─ 退款 → approve（大额时 interrupt）→ finalize → END
"""

from typing import Annotated, Literal

from typing_extensions import TypedDict
from operator import add

from _shared import get_model, title

from langchain.agents import create_agent
from langchain.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from pydantic import BaseModel, Field

APPROVAL_THRESHOLD = 500          # 业务规则写死在代码里，不靠模型自觉

# ── 店规。只有 3 条 → 直接放进提示词就够了；语料大了才上向量库（见 09）──────
RULES = """
- 营业时间：周一至周五 08:00-20:00；周六 09:00-22:00；周日休息。
- 会员：单次消费满 100 元可注册，1 元记 1 分，满 500 分换中杯拿铁一杯。
- 退款：饮品制作前可全额退；已制作完成不退；超过 500 元需店长审批。
"""


class Intent(BaseModel):
    """把用户一句话分类。"""

    kind: Literal["咨询", "退款申请"] = Field(description="意图类别")
    amount: int = Field(default=0, description="涉及金额（元）；咨询填 0")


class ServiceState(TypedDict):
    message: str
    kind: str
    amount: int
    answer: str
    history: Annotated[list[str], add]      # ★ 简易记忆：每轮追加，用 reducer 才不会丢


@tool
def lookup_order(phone: str) -> str:
    """根据手机号查最近的订单。"""
    return "最近一笔订单：拿铁 ×2，金额 56 元，状态 已完成"


# ── 节点 1：分类 ────────────────────────────────────────────────────────────
def classify(state: ServiceState) -> dict:
    intent = get_model(temperature=0).with_structured_output(Intent).invoke(
        f"判断下面这句话的意图：{state['message']}"
    )
    print(f"  [classify] 意图={intent.kind} 金额={intent.amount}")
    return {"kind": intent.kind, "amount": intent.amount}


def route_after_classify(state: ServiceState) -> str:
    return "approve" if state["kind"] == "退款申请" else "answer"


# ── 节点 2：咨询 → 带工具的 agent 回答 ─────────────────────────────────────
def answer(state: ServiceState) -> dict:
    agent = create_agent(
        get_model(),
        tools=[lookup_order],
        system_prompt=(
            "你是咖啡店客服。只用下面的店规回答，查不到就说不知道，不要编。\n" + RULES
        ),
    )
    result = agent.invoke({"messages": [{"role": "user", "content": state["message"]}]})
    reply = result["messages"][-1].content
    print(f"  [answer] {reply[:50]}...")
    return {"answer": reply, "history": [f"咨询：{state['message'][:20]}"]}


# ── 节点 3：退款 → 大额必须人工 ────────────────────────────────────────────
def approve(state: ServiceState) -> dict:
    if state["amount"] <= APPROVAL_THRESHOLD:
        print(f"  [approve] {state['amount']} 元未超阈值，自动受理")
        return {"answer": f"已受理退款 {state['amount']} 元，预计 3 个工作日到账。",
                "history": [f"自动退款 {state['amount']} 元"]}

    print(f"  [approve] {state['amount']} 元超阈值，等待人工审批")
    decision = interrupt({"问题": f"同意退款 {state['amount']} 元吗？", "诉求": state["message"]})
    if decision:
        return {"answer": f"退款 {state['amount']} 元已通过审批，正在处理。",
                "history": [f"人工批准退款 {state['amount']} 元"]}
    return {"answer": "很抱歉，本次退款未通过审批，我们会电话联系您说明原因。",
            "history": [f"人工拒绝退款 {state['amount']} 元"]}


def finalize(state: ServiceState) -> dict:
    return {}


def build_graph():
    builder = StateGraph(ServiceState)
    builder.add_node("classify", classify)
    builder.add_node("answer", answer)
    builder.add_node("approve", approve)
    builder.add_node("finalize", finalize)

    builder.add_edge(START, "classify")
    builder.add_conditional_edges("classify", route_after_classify)   # ★ 分流
    builder.add_edge("answer", "finalize")
    builder.add_edge("approve", "finalize")
    builder.add_edge("finalize", END)
    return builder.compile(checkpointer=InMemorySaver())


def turn(graph, config, message: str, human_reply: bool | None = None) -> None:
    """处理一轮对话。如果中途需要人工，就恢复一次。"""
    state_in = {"message": message, "kind": "", "amount": 0, "answer": "", "history": []}
    result = graph.invoke(state_in, config)

    if result.get("__interrupt__"):
        pending = result["__interrupt__"][0].value
        print(f"  ⏸  等待人工：{pending.get('问题')}")
        decide = True if human_reply is None else human_reply
        print(f"  人工回答：{'同意' if decide else '拒绝'}")
        result = graph.invoke(Command(resume=decide), config)

    print(f"  💬 {result['answer']}")


def main() -> None:
    graph = build_graph()
    thread = {"configurable": {"thread_id": "customer-888"}}     # ★ 同一个客人

    title("第 1 轮：咨询（走 answer 分支）")
    turn(graph, thread, "你们周六几点关门？")

    title("第 2 轮：小额退款（自动受理）")
    turn(graph, thread, "我那杯拿铁做错了，想退款 38 元")

    title("第 3 轮：大额退款（触发人工审批）")
    turn(graph, thread, "团建订的 1280 元想整单退掉", human_reply=True)

    title("第 4 轮：换个方式问，看它记不记得这个客人")
    turn(graph, thread, "再问一下，我刚才是退了多少钱？")
    snapshot = graph.get_state(thread)
    print(f"\n  这个 thread 的记忆（history 字段）:")
    for item in snapshot.values.get("history", []):
        print(f"    - {item}")

    title("一个能交付的小项目，还差什么？")
    print("  ✅ 流程可控（状态机）+ 分支 + 人工卡点 + 断点续跑")
    print("  ✅ 意图识别用结构化输出，不用正则")
    print("  ⬜ 换持久 checkpointer：PostgresSaver → 重启不丢")
    print("  ⬜ 接真实向量库：语料超过几十条就上 pgvector（见 09 / 04）")
    print("  ⬜ 评测：10-20 条固定问法 + 断言（意图对不对、金额抽得准不准）")
    print("  ⬜ Trace：LANGSMITH_TRACING=true，逐条看它看到了什么上下文")
    print("  ⬜ 重试上限：给循环设硬上限，超限转人工而不是硬闯")


if __name__ == "__main__":
    main()
