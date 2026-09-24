"""02 — 最小的智能体（需要 Key）

不到 15 行，一个能干活的智能体。
先跑通这个，再去看它内部怎么转（下一个例子 03）。

运行前：cp .env.example .env 并填好 Key（或设置 MODEL / MODEL_BASE_URL / MODEL_API_KEY）

脚本自带断言（`_shared.Checks`）：断言的是**行为**不是措辞——
它真的调了工具、答案里带上了工具给的数字。任何一条失败，脚本以非 0 退出码结束，
run_all.py 会当场变红（模型换了/提示词改坏了，这里先红给你看）。
"""

import sys

from _shared import Checks, get_model, title

from langchain.agents import create_agent
from langchain.tools import tool

CHECKS = Checks()


# ── 工具：就是一个普通 Python 函数，加个 @tool 装饰器 ────────────────────
@tool
def get_weather(city: str) -> str:
    """查询指定城市的天气。city 是城市名，例如 上海。"""
    fake_data = {"上海": "多云 26 度", "北京": "晴 31 度"}
    return fake_data.get(city, f"{city}：暂无数据")


@tool
def calculate(expression: str) -> str:
    """计算一个数学表达式，例如 '128 * 3'。"""
    allowed = set("0123456789+-*/(). ")
    if not set(expression) <= allowed:          # 安全习惯：绝不直接 eval 任意字符串
        return "表达式包含不允许的字符"
    return str(eval(expression))                # noqa: S307（教学示例，已限制字符集）


def main() -> None:
    agent = create_agent(
        model=get_model(),
        tools=[get_weather, calculate],
        system_prompt="你是一个简洁的助理。需要数据时必须调用工具，不要凭空猜。",
    )

    title("问题 1：需要调用一个工具")
    result1 = agent.invoke({"messages": [{"role": "user", "content": "上海天气怎么样？"}]})
    answer1 = str(result1["messages"][-1].content)
    print(answer1)

    title("问题 2：需要调用工具 + 做计算")
    result2 = agent.invoke(
        {"messages": [{"role": "user", "content": "如果上海今天 26 度，明天升 3 度又降 1 度，明天多少度？"}]}
    )
    answer2 = str(result2["messages"][-1].content)
    print(answer2)

    # 断言写在行为上（第 11 章）：调没调工具、数字对不对——不检查它怎么措辞
    called = [c["name"] for m in result1["messages"]
              for c in (getattr(m, "tool_calls", None) or [])]
    CHECKS.expect("get_weather" in called, "问题 1 真的调了 get_weather（不是凭空猜温度）")
    CHECKS.expect("26" in answer1, "问题 1 的答案带上了工具给的温度（多云 26 度）")
    CHECKS.expect("28" in answer2, "问题 2 算出了 28 度（26 + 3 - 1）")

    title("消息轨迹：看看模型到底做了什么决定")
    for i, msg in enumerate(result2["messages"]):
        kind = type(msg).__name__
        tool_calls = getattr(msg, "tool_calls", None)
        print(f"  [{i}] {kind:<14} {str(tool_calls) if tool_calls else (msg.content or '')[:60]}")

    print("\n接下来：examples/03_handwritten_loop.py 会把这条轨迹手工走一遍。")


if __name__ == "__main__":
    main()
    sys.exit(CHECKS.report())
