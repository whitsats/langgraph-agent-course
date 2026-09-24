"""04 — 结构化输出（需要 Key）

让模型按你定义好的 schema 返回数据，而不是返回一段自然语言让你去正则解析。
这是 web 开发者最容易犯的老毛病：拿到文本就想 re.search / JSON.parse。

结果不在 messages 里，而在 result["structured_response"]。

脚本自带断言（`_shared.Checks`）：每条口语都断言**抽出来的字段**对不对
（数量 / 杯型 / 发票），不比对措辞。失败即以非 0 退出码结束（run_all 会变红）。
"""

import sys
from typing import Literal

from _shared import Checks, get_model, title

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from pydantic import BaseModel, Field

CHECKS = Checks()


# ── 定义你要的数据结构（就像写 TypeScript interface / Zod schema）────────
class OrderIntent(BaseModel):
    """从用户的一句自然语言里抽取出的下单意图。"""

    product: str = Field(description="商品名，例如 拿铁")
    quantity: int = Field(description="数量，至少 1", ge=1)
    size: Literal["中杯", "大杯", "超大杯"] = Field(description="杯型")
    needs_invoice: bool = Field(description="是否需要发票")
    note: str = Field(default="", description="其他备注，没有就留空")


def main() -> None:
    agent = create_agent(
        model=get_model(),
        tools=[],                                        # 这个任务不需要工具
        system_prompt="你负责把用户的口语下单需求抽取成结构化数据。",
        response_format=ToolStrategy(OrderIntent),       # ★ 关键：声明输出 schema
    )

    sentences = [
        ("帮我点两杯大杯拿铁，要开发票，少冰。",
         {"quantity": 2, "size": "大杯", "needs_invoice": True, "product_has": "拿铁"}),
        ("来一杯中杯美式，不用发票。",
         {"quantity": 1, "size": "中杯", "needs_invoice": False, "product_has": "美式"}),
    ]

    for s, want in sentences:
        title(f"输入：{s}")
        result = agent.invoke({"messages": [{"role": "user", "content": s}]})

        order: OrderIntent = result["structured_response"]      # ★ 直接是 Pydantic 对象
        print(f"  类型      : {type(order).__name__}")
        print(f"  product   : {order.product}")
        print(f"  quantity  : {order.quantity}")
        print(f"  size      : {order.size}")
        print(f"  invoice   : {order.needs_invoice}")
        print(f"  note      : {order.note!r}")

        # 因为已经是对象了，后面接业务代码就是普通的 Python
        total = order.quantity * 28
        print(f"  业务计算  : {order.quantity} × 28 = {total} 元")

        # 断言写在抽出来的字段上（第 11 章）：换个说法也不该影响这几个字段
        CHECKS.expect(isinstance(order, OrderIntent), "返回的是 OrderIntent 对象，不是一段文本")
        CHECKS.expect(order.quantity == want["quantity"], f"数量抽对（{want['quantity']}）")
        CHECKS.expect(order.size == want["size"], f"杯型抽对（{want['size']}）")
        CHECKS.expect(order.needs_invoice is want["needs_invoice"], "发票字段抽对")
        CHECKS.expect(want["product_has"] in order.product, f"商品识别到「{want['product_has']}」")

    title("为什么必须这么做")
    print("  ❌ 错误做法：让模型自由发挥，然后 re.search(r'(\\d+)杯', text)")
    print("     模型换个说法（'两杯' / '2 杯' / '双份'）你的正则就崩了。")
    print("  ✅ 正确做法：声明 schema，让模型自己对齐字段。")
    print("\n  进阶：ToolStrategy 的 handle_errors 参数可以控制校验失败后是否自动重试。")
    print("  多种策略见官方文档 → Structured output。")


if __name__ == "__main__":
    main()
    sys.exit(CHECKS.report())
