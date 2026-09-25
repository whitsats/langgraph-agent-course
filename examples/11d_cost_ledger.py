"""11d — 成本账单（需要 Key 才有真数据；账本函数本身离线可演示）

demo 阶段没人看 token 账，上线第一个月账单吓一跳。第 11 章"模型路由与成本工程"
的第一步是**让花费可见**：每次调用的 token 数从哪拿、怎么攒成一张表。

  1. 单次调用：`response.usage_metadata` = {input_tokens, output_tokens, total_tokens}
     （流式时它在最后一个 chunk 上——11c 的收尾帧就是这么带出来的）
  2. 账本：每次调用记一行，攒成表，算合计
  3. 换算：费用 = token 数 / 1_000_000 × 单价。单价随供应商随时变，
     所以 PRICE_TABLE 留空由你自己填，本脚本绝不写死任何价格

两部分：
  第一部分（离线）：用三条假记录演示账本函数与合计口径
  第二部分（在线）：真调 3 次小请求，把真 usage_metadata 喂进同一个账本

脚本自带断言（`_shared.Checks`）：每次真调用都带 usage、total = input + output、
账本合计与逐行一致。失败即非 0 退出码结束。
"""

import os
import sys

import _shared  # noqa: F401  （导入时把 Windows 控制台切到 UTF-8）
from _shared import Checks

CHECKS = Checks()

# 单价表：模型名 → (输入单价, 输出单价)，单位 = 每百万 token 的货币数。
# 故意留空：价格随供应商/时间变，写死必过期。你接哪家，就按它官网填哪行，
# 例如 PRICE_TABLE["your-model"] = (2.0, 8.0)。没填的模型只记 token，不算钱。
PRICE_TABLE: dict[str, tuple[float, float]] = {}

QUESTIONS = [
    "用一句话说明什么是检索增强（RAG）。",
    "把「本店周六 09:00-22:00 营业」改写成一句更友好的店员话术。",
    "你们卖咖啡豆吗？店规：只有饮品，没有豆子。",
]


def ledger_row(label: str, usage: dict) -> dict:
    """把一次调用的 usage_metadata 归一成账本的一行。"""
    return {
        "label": label,
        "input": usage.get("input_tokens", 0),
        "output": usage.get("output_tokens", 0),
        "total": usage.get("total_tokens", 0),
    }


def print_ledger(rows: list[dict], title: str, model_name: str | None = None) -> dict:
    """打一张账单表，返回合计行。价格填了才算钱，没填只看 token。"""
    price = PRICE_TABLE.get(model_name) if model_name else None
    print(f"\n  {title}")
    print(f"  {'调用':<30}{'输入':>8}{'输出':>8}{'合计':>8}   费用")
    print("  " + "-" * 66)
    for r in rows:
        cost = (f"¥{(r['input'] / 1e6 * price[0]) + (r['output'] / 1e6 * price[1]):.4f}"
                if price else "—（PRICE_TABLE 未填价）")
        print(f"  {r['label']:<30}{r['input']:>8}{r['output']:>8}{r['total']:>8}   {cost}")
    totals = {
        "input": sum(r["input"] for r in rows),
        "output": sum(r["output"] for r in rows),
        "total": sum(r["total"] for r in rows),
    }
    print("  " + "-" * 66)
    print(f"  {'合计':<30}{totals['input']:>8}{totals['output']:>8}{totals['total']:>8}")
    return totals


def banner(t: str) -> None:
    print("\n" + "=" * 64)
    print(t)
    print("=" * 64)


def main() -> None:
    banner("第一部分：账本函数（离线，假数据演示口径）")
    fake = [
        ledger_row("今早全量评测（20 条）", {"input_tokens": 4200, "output_tokens": 900, "total_tokens": 5100}),
        ledger_row("索引 30 篇文档", {"input_tokens": 15000, "output_tokens": 0, "total_tokens": 15000}),
        ledger_row("日常问答 1 小时", {"input_tokens": 30000, "output_tokens": 6200, "total_tokens": 36200}),
    ]
    fake_totals = print_ledger(fake, "示例账单（数据是编的，口径是真的）")
    CHECKS.expect(fake_totals["total"] == 5100 + 15000 + 36200, "账本合计 = 逐行相加")
    CHECKS.expect(all(r["total"] == r["input"] + r["output"] for r in fake),
                  "每行 total = input + output（口径先对齐，账才可信）")

    banner("第二部分：真调用 3 次，拿真 usage_metadata")
    if not (os.getenv("MODEL_API_KEY") or os.getenv("AGNES_API_KEY") or os.getenv("OPENAI_API_KEY")):
        print("  需要 Key。在 examples/.env 里填 AGNES_API_KEY=... 后重跑。")
        print("  （想现在只看账本长什么样：上面第一部分就是完整口径。）")
        return

    from _shared import get_model, resolve_config

    model = get_model(temperature=0)
    model_name = resolve_config()["model"]
    rows = []
    for i, q in enumerate(QUESTIONS, 1):
        resp = model.invoke(q)
        usage = getattr(resp, "usage_metadata", None)
        CHECKS.expect(bool(usage) and usage.get("total_tokens", 0) > 0,
                      f"第 {i} 次调用带回了 usage_metadata（拿不到它就无从记账）")
        if usage:
            CHECKS.expect(usage["total_tokens"] == usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
                          f"第 {i} 次调用 total = input + output（供应商口径一致）")
            rows.append(ledger_row(f"Q{i}：{q[:14]}…", usage))

    totals = print_ledger(rows, f"真调用账单（{model_name}）", model_name=model_name)
    CHECKS.expect(totals["total"] == sum(r["total"] for r in rows), "真调用的账本合计自洽")

    print("\n  三个省钱抓手（按性价比排序，详见第 11 章成本工程一节）：")
    print("    1. 上下文瘦身——input 占大头，裁剪/摘要（11b）直接砍 input")
    print("    2. 模型分级——简单步骤走便宜模型，路由逻辑就在 middleware 里")
    print("    3. 批处理——评测/离线索引走 Batch API，打折换慢")
    print("  把 print_ledger 挂进你的评测脚本（11a）末尾，每次跑分顺便看花了多少。")


if __name__ == "__main__":
    main()
    sys.exit(CHECKS.report())
