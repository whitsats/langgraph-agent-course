"""03 — 手写 agent loop（需要 Key）★ 学计划里最重要的一步

用 50 行把 05 里 create_agent 做的事手工走一遍：
   调模型 → 模型要工具 → 执行工具 → 把结果塞回对话 → 再调模型 → 不要工具就结束

看完你就明白框架替你兜了什么：状态累积、工具分发、错误重试、终止判定。

脚本自带断言（`_shared.Checks`）：断言的是**循环行为**——没撞上步数上限、
真的调了工具、数字算对了。任何一条失败，脚本以非 0 退出码结束（run_all 会变红）。
"""

import json
import sys

from _shared import Checks, get_model, title

from langchain.messages import ToolMessage
from langchain.tools import tool

CHECKS = Checks()

MAX_STEPS = 6          # ★ 必须有上限，否则模型可能无限循环，烧钱又卡死


@tool
def get_weather(city: str) -> str:
    """查询指定城市的天气。city 是城市名，例如 上海。"""
    return {"上海": "多云 26 度", "北京": "晴 31 度"}.get(city, f"{city}：暂无数据")


@tool
def calculate(expression: str) -> str:
    """计算一个数学表达式，例如 '128 * 3'。"""
    allowed = set("0123456789+-*/(). ")
    if not set(expression) <= allowed:
        return "表达式包含不允许的字符"
    return str(eval(expression))                # noqa: S307


TOOLS = {t.name: t for t in (get_weather, calculate)}      # 名字 → 工具，用于分发


def run_loop(question: str) -> tuple[str, list[str], bool]:
    """核心：一条手写的 agent 循环。返回 (回答, 调过的工具, 是否耗尽步数)。"""
    model = get_model(temperature=0)
    model_with_tools = model.bind_tools(list(TOOLS.values()))      # ★ 告诉模型有哪些工具

    messages = [{"role": "user", "content": question}]
    called: list[str] = []

    for step in range(1, MAX_STEPS + 1):
        print(f"\n--- 第 {step} 轮：把 {len(messages)} 条消息发给模型 ---")
        ai = model_with_tools.invoke(messages)
        messages.append(ai)

        # ★ 终止条件 1：模型不再要求调用工具，说明它准备好回答了
        if not ai.tool_calls:
            print("--- 模型不再需要工具，循环结束 ---")
            text = ai.content if isinstance(ai.content, str) else str(ai.content)
            return text, called, False

        # ★ 执行模型要求的每个工具，并把结果回灌
        for call in ai.tool_calls:
            name, args, call_id = call["name"], call["args"], call["id"]
            print(f"    模型要求调用: {name}({args})")
            called.append(name)

            tool_fn = TOOLS.get(name)
            if tool_fn is None:
                output = f"错误：没有名为 {name} 的工具"
            else:
                try:
                    output = tool_fn.invoke(args)
                except Exception as e:                       # ★ 失败要显式返回给模型
                    output = f"工具执行失败：{type(e).__name__}: {e}"

            print(f"    工具返回: {output}")
            messages.append(ToolMessage(content=str(output), tool_call_id=call_id))

    # ★ 终止条件 2：步数用尽。必须显式兜底，不能假装成功。
    return (f"达到最大步数 {MAX_STEPS}，未能完成。最后一条消息：{messages[-1].content!r}",
            called, True)


def main() -> None:
    title("手写循环：问一个需要两步工具的问题")
    answer, called, exhausted = run_loop("上海今天多少度？如果明天升 3 度，明天多少度？")
    print(f"\n最终回答：{answer}")

    # 三条断言，正好对应手写循环里最容易写错的三件事
    CHECKS.expect(not exhausted, "循环正常终止（没撞上 MAX_STEPS 上限）")
    CHECKS.expect("get_weather" in called, "模型确实调用了天气工具（分发起作用了）")
    CHECKS.expect("29" in answer, "答案算出了 29 度（26 + 3）")

    title("和框架对比")
    print("  手写这份代码里，下面这些都要你自己负责：")
    print("   - 消息列表怎么累积、工具结果怎么回灌")
    print("   - 工具不存在 / 抛异常怎么办")
    print("   - 什么时候停（不再要工具 / 步数上限 / 循环检测）")
    print("   - 上下文太长怎么裁剪")
    print("\n  这些正是 create_agent + middleware 替你管的东西。")
    print("  所以顺序必须是：先手写一遍 → 再看框架，反过来你只会背 API。")


if __name__ == "__main__":
    main()
    sys.exit(CHECKS.report())
