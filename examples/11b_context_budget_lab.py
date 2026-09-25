"""11b — 上下文预算实验室（离线可跑，不需要 Key）

长会话的死结：轮数一多，上下文线性膨胀 → 变慢、变贵、最后撞爆窗口。
第 11 章给的两个抓手——**裁剪**（只留最近 N 轮）与**摘要压缩**（旧轮压成一段摘要）——
各有代价：裁剪省钱但**丢早期事实**；摘要有损压缩但保得住关键信息。

本 lab 用同一个 12 轮的对话，把三种策略放在一起对比：

  全量保留  ── 贵，但答对
  裁剪      ── 便宜，但第 1 轮说过的"花生过敏"没了 → 答错
  摘要压缩  ── 适中，关键事实进摘要 → 答对

全部离线：token 用**假 tokenizer** 近似（CJK 1 字 ≈ 1 token，其余 4 字符 ≈ 1 token），
"模型"是模拟的（和 16/17/18 同款手法）——测的是**结构**：上下文里有什么，
决定了模型能答对什么。真跑时把近似计数换成 `response.usage_metadata`（见 11d），
把模拟的策略换成 `create_agent(middleware=[SummarizationMiddleware(...)])`（第 11 章中间件节）。

脚本自带断言（`_shared.Checks`）：两种策略都省 token、裁剪版确实丢事实、
摘要版保得住、模拟模型的答案随上下文改变。失败即非 0 退出码结束。
"""

import sys
import unicodedata

import _shared  # noqa: F401  （导入时把 Windows 控制台切到 UTF-8）
from _shared import Checks

CHECKS = Checks()


def approx_tokens(text: str) -> int:
    """假 tokenizer：CJK 1 字 ≈ 1 token，其余 4 字符 ≈ 1 token。

    离线演示够用；精确值以 `response.usage_metadata` 为准（真账见 11d）。
    """
    cjk = sum(1 for ch in text if unicodedata.east_asian_width(ch) in "WF")
    return cjk + (len(text) - cjk + 3) // 4


# ---------------------------------------------------------------------------
# 素材：一段 12 轮的咖啡店对话。第 1 轮埋了后面要考的关键事实。
# ---------------------------------------------------------------------------

TURNS = [
    ("user", "我叫小明，对花生过敏，记一下。"),
    ("assistant", "好的小明，已记下您对花生过敏，推荐饮品时我会避开含花生的。"),
    ("user", "拿铁多大杯？"),
    ("assistant", "中杯 360ml，大杯 480ml。"),
    ("user", "会员怎么注册？"),
    ("assistant", "单次消费满 100 元可注册，1 元累计 1 分。"),
    ("user", "积分能换什么？"),
    ("assistant", "满 500 分可换一杯中杯拿铁。"),
    ("user", "昨天买的杯子能退吗？"),
    ("assistant", "饮品制作前可全额退款；器具类需要店长确认。"),
    ("user", "帮我看看最近的优惠。"),
    ("assistant", "本周拿铁第二杯半价，会员生日当天 8 折。"),
]
RECENT_N = 4        # 裁剪策略：只保留最近 4 条消息（2 个来回）
QUESTION = "我第一次来的时候说过我对什么过敏？"

SUMMARY = "（前情摘要）顾客小明，对花生过敏；问过杯型、会员积分（满 500 分换拿铁）与退款规则。"


def render(turns) -> str:
    return "\n".join(f"{role}: {text}" for role, text in turns)


def fake_answer(context: str, question: str) -> str:
    """模拟模型：它只能看到喂给它的上下文——上下文里没有的事实，它就只能编或说没有。"""
    if "过敏" in question:
        if "花生" in context:
            return "您第一次来时说过：您对花生过敏。"
        return "抱歉，我们的对话记录里没有找到您说过过敏的信息。"
    return "（与本实验无关，略）"


def banner(t: str) -> None:
    print("\n" + "=" * 64)
    print(t)
    print("=" * 64)


def main() -> None:
    full_ctx = render(TURNS)
    kept = TURNS[-RECENT_N:]                       # 裁剪：只留最近 N 轮
    trimmed_ctx = render(kept)
    summarized_ctx = SUMMARY + "\n" + render(kept)  # 摘要压缩：旧轮换成一段摘要 + 最近 N 轮

    banner("同一个问题，三种上下文策略")
    print(f"  考题（需要第 1 轮的事实才能答对）：{QUESTION}\n")
    strategies = [
        ("全量保留", full_ctx),
        (f"裁剪（留最近 {RECENT_N} 条）", trimmed_ctx),
        ("摘要压缩", summarized_ctx),
    ]
    full_tokens = approx_tokens(full_ctx)
    answers = {}
    for name, ctx in strategies:
        tokens = approx_tokens(ctx)
        answers[name] = fake_answer(ctx, QUESTION)
        saved = f"（省 {full_tokens - tokens}）" if tokens < full_tokens else ""
        fact = "✓ 花生过敏还在" if "花生" in ctx else "✗ 关键事实已丢"
        print(f"  {name:<14} {tokens:>5} tokens {saved:<10} {fact}")
        print(f"{'':<16}↳ {answers[name]}")

    # —— 结构不变量 ——
    trim_tokens = approx_tokens(trimmed_ctx)
    sum_tokens = approx_tokens(summarized_ctx)
    CHECKS.expect(trim_tokens < full_tokens and sum_tokens < full_tokens,
                  "两种策略都必须比全量省 token（不然要它干嘛）")
    CHECKS.expect(sum_tokens < full_tokens and "花生" in summarized_ctx,
                  "摘要压缩：token 变少的同时保住关键事实")
    # 演示型断言：裁剪的代价是真实的——这不是 bug，是这类策略的固有取舍
    CHECKS.expect("花生" not in trimmed_ctx, "裁剪版确实丢了早期事实（演示型断言：裁剪的代价）")
    CHECKS.expect("没有找到" in answers["裁剪（留最近 4 条）"],
                  "上下文里没有的事实，模型只能答'没有'（拿掉事实，答案就变）")
    CHECKS.expect("花生" in answers["摘要压缩"] and "花生" in answers["全量保留"],
                  "摘要版与全量版都答对了考题")

    print("\n  取舍表（这就是第 11 章那张表的展开）：")
    print("    裁剪     —— 最便宜，适合'只看最近'的场景（闲聊、跟进当前任务）")
    print("    摘要压缩 —— 便宜 + 保关键，适合长会话客服；代价：摘要本身也占 token，且要选触发时机")
    print("    真跑时  ：create_agent(middleware=[SummarizationMiddleware(model=..., trigger=('tokens', 4000))])")
    print("    记账时  ：把本 lab 的假 tokenizer 换成 response.usage_metadata（见 11d）")


if __name__ == "__main__":
    main()
    sys.exit(CHECKS.report())
