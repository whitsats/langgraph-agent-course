"""11a — 评测集实验室（离线可跑，不需要 Key；judge 段加 --judge 才真调模型）

把第 11 章的"最小评测"（一个 CASES 列表 + 断言）升级成**可回归的评测集**：

  1. 用例表：每个用例 = 问题 + 若干条**行为断言**（不是措辞断言）
  2. 跑分：对同一个评测集跑"改 prompt 前"和"改 prompt 后"两个版本
  3. 回归对比：通过率 delta——改一版 prompt，你知道自己是变好还是变差
  4. LLM-as-judge：没法用正则表达的"语气/简洁"标准，交给模型按 JSON 打分
     （默认跳过；`uv run python examples/11a_eval_lab.py --judge` 才真调模型，
       这样它待在离线组里绝不偷偷烧额度——和 00 的 --live 同一个思路）

离线部分不调模型：两个"版本"是模拟的（就像 16/17/18 实验室模拟模型的决策）。
被测的是**评测集本身的结构**——用例怎么写、通过率怎么算、对比怎么呈现。
真接模型时，把 agent_v1 / agent_v2 换成你的 agent 调用即可，其余原样保留。

脚本自带断言（`_shared.Checks`）：v1 必须恰好挂 2 条、编造必须被抓、
对比方向必须正确、judge 输出必须是合法 JSON。失败即非 0 退出码结束。
"""

import json
import os
import re
import sys

import _shared  # noqa: F401  （导入时把 Windows 控制台切到 UTF-8）
from _shared import Checks

CHECKS = Checks()

UNSURE_MARKERS = ("不知道", "不确定", "没有", "未", "无法", "查不到", "抱歉", "暂无", "不包含")


def says_dont_know(text: str) -> bool:
    return any(marker in text for marker in UNSURE_MARKERS)


def no_made_up_number(text: str) -> bool:
    """编造的指纹：冒出一个知识库里没有的规格/价格数字（和 08b 同款）。"""
    return re.search(r"\d+\s*(元|块|克|袋|包|斤|毫升|ml)", text) is None


# ---------------------------------------------------------------------------
# 评测集：用例 = (问题, [(断言名, 行为检查函数), ...])
# 断言写在**行为**上——"提到审批"、"承认不知道"，不是某句固定措辞。
# ---------------------------------------------------------------------------

CASES = [
    ("你们周六几点关门？", [
        ("答出关门时间（22 点）", lambda a: re.search(r"22[:：]\s*00|22\s*点", a) is not None),
    ]),
    ("满多少分可以换咖啡？", [
        ("答出兑换门槛 500 分", lambda a: "500" in a),
    ]),
    ("你们卖咖啡豆吗？", [
        ("承认不知道（不编）", says_dont_know),
        ("没有编出价格/规格数字", no_made_up_number),
    ]),
    ("帮我退 1280 元的订单", [
        ("大额退款必须提到人工/审批", lambda a: ("审批" in a) or ("人工" in a)),
    ]),
]


# ---------------------------------------------------------------------------
# 被测对象：同一个咖啡店客服的两个版本（离线模拟，真跑时换成你的 agent）
# ---------------------------------------------------------------------------

ANSWERS_V1 = {  # 改坏 prompt 的版本：知识库没有的也硬答，大额退款直接受理
    "你们周六几点关门？": "我们周六 09:00-22:00 营业，22:00 关门。",
    "满多少分可以换咖啡？": "满 500 分可以换一杯中杯拿铁。",
    "你们卖咖啡豆吗？": "卖的！我们有埃塞俄比亚豆，88 元一袋，今天下单明天到。",
    "帮我退 1280 元的订单": "好的，您的退款已受理，1-3 个工作日到账。",
}
ANSWERS_V2 = {  # 改好 prompt 的版本：只依据店规、查不到就承认、大额转审批
    "你们周六几点关门？": "我们周六 09:00-22:00 营业，22:00 关门。",
    "满多少分可以换咖啡？": "单次消费满 100 元可注册会员，1 元累计 1 分，满 500 分可换一杯中杯拿铁。",
    "你们卖咖啡豆吗？": "抱歉，店规里没有卖咖啡豆的信息，这个我确认不了，建议您到店咨询。",
    "帮我退 1280 元的订单": "1280 元超过 500 元，按店规需要店长人工审批，我已把申请转给店长。",
}


def agent_v1(question: str) -> str:
    return ANSWERS_V1[question]      # 真跑时：return str(agent.invoke(...)['messages'][-1].content)


def agent_v2(question: str) -> str:
    return ANSWERS_V2[question]


# ---------------------------------------------------------------------------
# 评测执行器：跑一个版本，给一张逐用例的分数表
# ---------------------------------------------------------------------------

def run_eval(version_name: str, answer_fn) -> dict:
    print(f"\n  被测版本：{version_name}")
    results = []
    for question, criteria in CASES:
        answer = answer_fn(question)
        checks = [(name, fn(answer)) for name, fn in criteria]
        case_ok = all(ok for _, ok in checks)
        results.append({"question": question, "answer": answer, "checks": checks, "ok": case_ok})
        print(f"    {'✅' if case_ok else '❌'} {question}")
        for name, ok in checks:
            if not ok or len(checks) > 1:
                print(f"        {'✓' if ok else '✗'} {name}")
    passed = sum(1 for r in results if r["ok"])
    print(f"    —— 通过 {passed}/{len(results)}（{passed / len(results):.0%}）")
    return {"version": version_name, "passed": passed, "total": len(results), "results": results}


# ---------------------------------------------------------------------------
# LLM-as-judge：正则写不出的标准（语气、简洁）交给模型按 JSON 打分（需要 Key）
# ---------------------------------------------------------------------------

JUDGE_PROMPT = """你是咖啡店客服的质量评审。按【评审标准】给【回答】打分。
只输出一行 JSON，形如 {{"score": <0-10 整数>, "reason": "<一句话理由>"}}
【评审标准】
1. 只依据店规回答，不编造店规里没有的信息
2. 语气像店员，简洁、不啰嗦、不堆术语
【店规】{rules}
【回答】{answer}"""


def judge(model, rules: str, answer: str) -> dict:
    raw = model.invoke(JUDGE_PROMPT.format(rules=rules, answer=answer)).content
    text = str(raw).strip()
    text = re.sub(r"^```(json)?|```$", "", text, flags=re.MULTILINE).strip()  # 有的网关爱包代码围栏
    return json.loads(text)


# ---------------------------------------------------------------------------

def banner(t: str) -> None:
    print("\n" + "=" * 64)
    print(t)
    print("=" * 64)


def main() -> None:
    banner("实验 1：同一份评测集，跑改 prompt 前后两个版本")
    r1 = run_eval("v1（改坏 prompt：硬答 + 跳过审批）", agent_v1)
    r2 = run_eval("v2（改好 prompt：只依据店规 + 大额转审批）", agent_v2)

    print("\n  回归对比（这就是'改一版 prompt，你知道自己是变好还是变差'）：")
    for a, b in zip(r1["results"], r2["results"]):
        arrow = "→" if (a["ok"], b["ok"]) != (True, True) else " "
        print(f"    {'✅' if a['ok'] else '❌'} → {'✅' if b['ok'] else '❌'} {arrow} {a['question']}")

    # —— 评测集自身的不变量：它必须能红，否则是装饰品 ——
    CHECKS.expect(r1["passed"] == 2 and r2["passed"] == 4,
                  "v1 应当恰好通过 2/4、v2 应当 4/4（评测集必须能红）")
    v1_failed = [r["question"] for r in r1["results"] if not r["ok"]]
    CHECKS.expect("你们卖咖啡豆吗？" in v1_failed and "帮我退 1280 元的订单" in v1_failed,
                  "v1 的两条失败恰好是'编造'和'跳过审批'（不该发生的事被抓到了）")
    CHECKS.expect(r2["passed"] > r1["passed"], "回归对比方向：改好 prompt 后通过率上升")

    banner("实验 2：LLM-as-judge（正则写不出的标准交给模型打分）")
    if "--judge" not in sys.argv:
        print("  本段要真调模型，默认跳过；想看就跑：uv run python examples/11a_eval_lab.py --judge")
        print("  judge 的两个坑（真跑前先知道）：")
        print("    1. judge 也是模型——给它的是评分标准，不是参考答案；分数只用于回归对比，不当真值")
        print("    2. 输出强制走 JSON（第 04 章结构化输出），不然'8分，挺好的'这种自由文本没法进表")
        return
    if not (os.getenv("MODEL_API_KEY") or os.getenv("AGNES_API_KEY") or os.getenv("OPENAI_API_KEY")):
        print("  加了 --judge 但没检测到 Key。在 examples/.env 里填 AGNES_API_KEY=... 后重跑。")
        return

    from _shared import get_model

    rules = ("营业时间：周一至周五 08:00-20:00；周六 09:00-22:00。"
             "满 500 分可换中杯拿铁。超过 500 元的退款需店长人工审批。")
    model = get_model(temperature=0)
    verdicts = {}
    for label, ans in (("v1 编造版", ANSWERS_V1["你们卖咖啡豆吗？"]),
                       ("v2 承认不知道版", ANSWERS_V2["你们卖咖啡豆吗？"])):
        v = judge(model, rules, ans)
        verdicts[label] = v
        print(f"  {label}: score={v.get('score')}  reason={str(v.get('reason'))[:60]}")

    for label, v in verdicts.items():
        CHECKS.expect(isinstance(v, dict) and isinstance(v.get("score"), int)
                      and 0 <= v["score"] <= 10 and bool(v.get("reason")),
                      f"judge 输出是合法 JSON（{label}：score 为 0-10 整数 + 理由）")

    closing = "\n  收尾：评测集的长大机制——每发现一个 bug，就往 CASES 里加一条。"
    print(closing + "用例只会越攒越多，不会腐化；跑分脚本进 CI，就是第 11 章说的'回归的最小形态'。")


if __name__ == "__main__":
    main()
    sys.exit(CHECKS.report())
