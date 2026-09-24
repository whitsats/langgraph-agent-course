"""17 — 规划与自我验证实验室（离线可跑，不需要 Key）

同一个咖啡店月报任务，四种做法逐步升级。全部离线：我们模拟"模型的决策"，
把规划与验证的**结构**本身测清楚——因为结构错了，换多强的模型都白搭。

四个实验对应讲义第 17 章（附录D）的四个概念：
  1. plan-and-execute：先出计划再执行，对比"一口气式"agent 的退化
  2. 计划校验：坏计划在执行前就被拒绝（幽灵工具 / 幻觉参数 / 越权动作）
  3. 执行断言 + 重规划：每步用断言验证，失败只修那一步
  4. generator-verifier：两个候选答案，外部验证器对账裁决

贯穿的场景：月底给老板写经营报告（订单、品类营收、落成报告文件）。

脚本自带断言（`_shared.Checks`）：坏计划必须被拒、计划必须收敛、断言过的步骤必须
被复用、编造的候选必须被验证器挡下。任何一条失败，脚本以非 0 退出码结束——
run_all.py 会当场变红，不用等人盯着输出看。
"""

import sys

import _shared  # noqa: F401  （导入时把 Windows 控制台切到 UTF-8）

CHECKS = _shared.Checks()

# ---------------------------------------------------------------------------
# 场景数据与工具层（和第 16 章同一个咖啡店）
# ---------------------------------------------------------------------------

ORDERS = {"1001": {"customer": "张三", "phone": "138xxxx", "amount": 1280}}

REVENUE = {
    "2026-07": [("拿铁", 7200), ("美式", 5100)],
    "2026-08": [("拿铁", 8420), ("澳白", 6600), ("美式", 4100)],
}
VALID_MONTHS = sorted(REVENUE)                       # 台账里真实存在的月份

REPORTS: dict[str, str] = {}                         # "报告柜"：写进去的报告

TOOL_RISK = {"search_orders": "低（只读）", "revenue_by_category": "低（只读）",
             "write_report": "高（写入）", "send_email": "高危（外发）"}


def tool(name: str, arg: str) -> tuple[bool, str]:
    """真实工具层。返回 (是否成功, 输出)。失败必须带"为什么"。"""
    if name == "search_orders":
        order = ORDERS.get(arg)
        if order is None:
            return False, f"错误：没有订单 {arg}（现有订单：{'、'.join(ORDERS)}）"
        return True, f"订单 {arg}：{order['customer']}，金额 {order['amount']} 元"
    if name == "revenue_by_category":
        rows = REVENUE.get(arg)
        if rows is None:
            return False, f"错误：没有 {arg} 的营收数据（可用月份：{'、'.join(VALID_MONTHS)}）"
        return True, "；".join(f"{cat} {amt} 元" for cat, amt in rows)
    if name == "write_report":
        REPORTS[arg[0]] = arg[1]
        return True, f"已写入 {arg[0]}（{len(arg[1])} 字）"
    if name == "send_email":
        return True, f"（演示）已发送给 {arg}"
    return False, f"未知工具 {name}"


def banner(title: str) -> None:
    print("\n" + "=" * 64)
    print(title)
    print("=" * 64)


# ---------------------------------------------------------------------------
# 实验 1：一口气式 vs plan-and-execute
# ---------------------------------------------------------------------------

TASK = "把 8 月经营情况整理成报告：查 1001 号订单、哪个品类卖得最好，落成月报文件"


def exp1_plan_vs_one_shot() -> None:
    banner("实验 1：一口气式（ReAct 循环） vs plan-and-execute")    # —— 做法 A：一口气式。每一步都让"模型"重新看着全部对话现场发挥 ——
    def one_shot_decide(steps_done, results):
        # 真实 ReAct 循环里这就是模型：每步重新读全上下文再拍板。步骤一多，
        # 它会"忘"之前查过什么、算错月份——这里模拟两个最典型的退化。
        while True:
            if not steps_done:
                yield ("search_orders", "1001", None)
            elif len(steps_done) == 1:
                yield ("revenue_by_category", "2026-13", None)   # 月份数错了（8 月写成 13 月）
            elif len(steps_done) == 2:
                yield (None, None, "已完成：本月订单 1 笔，最畅销品类是美式。")  # 编造收尾
            else:
                break

    trace, results = [], []
    print(f"  任务：{TASK}\n")
    print("  【做法 A：一口气式，每步都重新问一次\"模型\"】")
    for name, arg, final in one_shot_decide(trace, results):
        if name is None:
            print(f"    最终回答: {final}")
            break
        ok, out = tool(name, arg)
        trace.append(f"{name}({arg}) {'✓' if ok else '✗'}")
        print(f"    {trace[-1]}  {out}")
        results.append(out)
    CHECKS.expect(any("2026-13" in t and "✗" in t for t in trace),
                  "实验 1：一口气式确实点错了月份（演示型断言）")

    # —— 做法 B：plan-and-execute。规划一次，执行交给确定性 runner ——
    print("\n  【做法 B：先出计划，再逐步执行】")
    plan = [("search_orders", "1001"), ("revenue_by_category", "2026-08")]
    print("    计划：" + " → ".join(f"{n}({a})" for n, a in plan) + " → write_report")
    for name, arg in plan:
        ok, out = tool(name, arg)
        print(f"    {name}({arg}) {'✓' if ok else '✗'}  {out}")
    rev = REVENUE["2026-08"]
    best = max(rev, key=lambda r: r[1])
    report = (f"8 月营收 {sum(a for _, a in rev)} 元；订单 1001：张三 1280 元；"
              f"最畅销品类：{best[0]}（{best[1]} 元）。")
    tool("write_report", ("reports/2026-08.md", report))
    print(f"    write_report ✓  最终报告：{report}")
    print(f"    决策调用：一口气式 = 每步都要\"模型\"拍板；计划式 = 规划 1 次，执行零调用")


# ---------------------------------------------------------------------------
# 实验 2：计划校验——坏计划死在执行前
# ---------------------------------------------------------------------------

ALLOWED_TOOLS = {"search_orders", "revenue_by_category", "write_report"}
KNOWN_MONTHS = tuple(VALID_MONTHS)
KNOWN_ORDER_IDS = tuple(ORDERS)


def validate_plan(plan, available_tools, known_months, known_orders):
    """静态计划校验器：三个检查，全部通过才放行。返回 (是否通过, 问题列表)。"""
    problems = []
    for i, (name, arg) in enumerate(plan):
        if name not in available_tools:
            problems.append(f"第 {i + 1} 步：{name} 不在允许工具集里（幽灵工具）")
        elif name == "revenue_by_category" and arg not in known_months:
            problems.append(f"第 {i + 1} 步：月份 {arg} 不在台账里（幻觉参数，可用：{'、'.join(known_months)}）")
        elif name == "search_orders" and arg not in known_orders:
            problems.append(f"第 {i + 1} 步：订单号 {arg} 不存在（幻觉参数）")
    return not problems, problems


def exp2_plan_validation() -> None:
    banner("实验 2：计划校验——坏计划死在执行前（不需要等它跑）")

    good_plan = [("search_orders", "1001"),
                 ("revenue_by_category", "2026-08"),
                 ("write_report", "reports/2026-08.md")]
    bad_plans = [
        ("幻觉日期版", [("revenue_by_category", "2026-13"),
                       ("write_report", "reports/2026-13.md")]),
        ("幽灵工具版", [("search_orders", "1001"),
                       ("export_sales_csv", "all"),
                       ("write_report", "reports/x.md")]),
        ("越权动作版", [("revenue_by_category", "2026-08"),
                       ("send_email", "boss@example.com")]),
    ]

    ok, problems = validate_plan(good_plan, ALLOWED_TOOLS, KNOWN_MONTHS, KNOWN_ORDER_IDS)
    print("  计划 A（干净）：")
    print("    " + " → ".join(f"{n}({a if isinstance(a, str) else a[0]})" for n, a in good_plan))
    print(f"    校验：{'✅ 通过，放行执行' if ok else '❌ ' + '；'.join(problems)}")
    CHECKS.expect(ok, "干净计划通过静态校验")

    for label, plan in bad_plans:
        ok, problems = validate_plan(plan, ALLOWED_TOOLS, KNOWN_MONTHS, KNOWN_ORDER_IDS)
        print(f"\n  计划 B（{label}）：")
        print("    " + " → ".join(f"{n}({a if isinstance(a, str) else a[0]})" for n, a in plan))
        for p in problems:
            print(f"    ❌ 拒绝：{p}")
        CHECKS.expect(not ok, f"{label}的坏计划被拒（{len(problems)} 处问题）")

    print("\n  这就是 ASI08（级联失败）「计划-执行之间加校验」的落地；")
    print("  第 16 章实验 3 那种「每步都合法、组合不合法」的外泄轨迹，")
    print("  在计划层就能被工具白名单直接掐死——比在执行层逐个放行安全得多。")


# ---------------------------------------------------------------------------
# 实验 3：执行断言 + 重规划——失败只修那一步
# ---------------------------------------------------------------------------

# 每个计划步骤的"验收断言"：不信任执行器说成功，检查结果本身
ASSERTIONS = {
    ("search_orders", "1001"): lambda out: "张三" in out and "1280" in out,
    ("revenue_by_category", "2026-08"): lambda out: "拿铁" in out,
}


def run_with_verify(plan, max_rounds: int = 3) -> tuple[bool, int]:
    """返回 (是否收敛, 复用了几个断点)。"""
    passed: set[int] = set()                # 断点：已通过断言的步骤索引
    skipped = 0
    for attempt in range(1, max_rounds + 1):
        print(f"\n  —— 第 {attempt} 轮执行 ——")
        failed = None
        for i, (name, arg) in enumerate(plan):
            if i in passed:
                print(f"    {i + 1}. {name}（上轮已通过断言，断点复用，跳过）")
                skipped += 1
                continue
            ok, out = tool(name, arg)
            if ok and (name, arg) in ASSERTIONS:
                ok = ASSERTIONS[(name, arg)](out)      # 断言：输出内容必须像预期
            print(f"    {i + 1}. {name}({arg if isinstance(arg, str) else arg[0]}) "
                  f"{'✓' if ok else '✗'}  {out}")
            if not ok:
                failed = (i, name, arg, out)
                break
            passed.add(i)
        if failed is None:
            print("    全部步骤通过断言 ✔")
            return True, skipped
        i, name, arg, out = failed
        print(f"    ⚠️ 第 {i + 1} 步失败 → 重规划（只修这一步，其余步骤原样保留）")
        if name == "revenue_by_category" and arg not in VALID_MONTHS:
            fix = "2026-08"
            plan[i] = (name, fix)
            print(f"       replanner：{arg} 不在台账 → 改为 {fix}（错误信息里给的可用月份）")
        else:
            plan[i] = (name, arg)
            print("       replanner：本步重试一次")
    return False, skipped


def exp3_assert_and_replan() -> None:
    banner("实验 3：执行断言 + 重规划——失败定位到步，而不是从头再来")

    plan = [("search_orders", "1001"),
            ("revenue_by_category", "2026-13"),          # ← 故意放一个坏步骤
            ("write_report", ("reports/2026-08.md", "8 月经营报告（内容来自前两步的执行结果）"))]
    print("  初始计划：" + " → ".join(f"{n}({a if isinstance(a, str) else a[0]})"
                                     for n, a in plan))
    done, skipped = run_with_verify(plan)

    print(f"\n  结果：{'✅ 计划收敛' if done else '❌ 轮次耗尽'}；最终计划：")
    print("    " + " → ".join(f"{n}({a if isinstance(a, str) else a[0]})" for n, a in plan))
    print(f"    报告柜：{sorted(REPORTS)}")
    CHECKS.expect(done, "计划最终收敛（坏的那一步被 replanner 修好）")
    CHECKS.expect(skipped > 0, "第二轮复用了已通过断言的步骤（断点生效）")
    print("\n  对照 ReAct：模型自由发挥时会在坏步骤上原地打转或换个说法硬编；")
    print("  这里的失败是断言逼出来的具体错误，replanner 只需修那一步。")
    print("  第 2 轮里已通过断言的步骤直接复用、不再重跑——这就是第 06 章")
    print("  checkpointer 在真实系统里的价值：修复从断点重放，不从零开始。")


# ---------------------------------------------------------------------------
# 实验 4：generator-verifier——两个候选，外部验证器裁决
# ---------------------------------------------------------------------------

def verify_candidate(candidate: str) -> tuple[bool, list[str]]:
    """外部验证器：把候选答案里的可检验事实逐条对台账，不看文采。"""
    cand = candidate.replace(",", "")                    # 千分位逗号先抹掉再对数
    _ok, _ = tool("revenue_by_category", "2026-08")      # 验证器自己也走工具拿台账
    checks = []
    for cat, amt in REVENUE["2026-08"]:
        if cat in cand and str(amt) in cand:
            checks.append(f"{cat} {amt} 元：✓ 候选说法与台账一致")
        elif cat in cand:
            checks.append(f"{cat}：候选提到了，但数字与台账（{amt} 元）对不上 → ⚠️")
        else:
            checks.append(f"{cat} {amt} 元：候选未提（不加分不扣分）")
    # 候选里出现的金额必须都能在台账里找到，否则视为编造
    import re
    amounts = {str(a) for _, a in REVENUE["2026-08"]}
    for num in re.findall(r"\d{3,}", cand):
        if num in amounts or num == "2026":
            continue
        checks.append(f"金额 {num}：台账里查无此数 → ⚠️ 疑似编造")
        return False, checks
    return True, checks


def exp4_generator_verifier() -> None:
    banner("实验 4：generator-verifier——两个候选答案，验证器对账裁决")

    question = "8 月最畅销的品类是哪个？给出依据。"
    c1 = "最畅销的是美式，8 月美式营收 9,000 元，遥遥领先。"          # 编造
    c2 = "最畅销的是拿铁：8 月拿铁 8,420 元居首，第二名澳白 6,600 元。"  # 真实
    print(f"  问题：{question}\n")
    print(f"  候选 1（语气自信）：{c1}")
    ok, checks = verify_candidate(c1)
    for c in checks:
        print(f"    - {c}")
    print(f"    裁决：{'✅ 采纳' if ok else '❌ 拒绝'}\n")
    print(f"  候选 2（语气朴素）：{c2}")
    ok2, checks2 = verify_candidate(c2)
    for c in checks2:
        print(f"    - {c}")
    print(f"    裁决：{'✅ 采纳' if ok2 else '❌ 拒绝'}")
    CHECKS.expect(not ok, "编造的候选被验证器拒绝（对不上台账）")
    CHECKS.expect(ok2, "与台账一致的候选被采纳")
    print(f"\n  最终给老板的答案来自候选 {'2' if ok2 else '?'}——不是最自信的，是对得上台账的。")
    print("  为什么不让模型\"自己检查自己\"：同一个上下文、同一套偏见，")
    print("  很容易顺着自己刚才的话再圆一遍。验证器必须在外部：工具台账、")
    print("  测试用例、或换一套提示的第二个模型。Reflexion 的自我批评是文字，")
    print("  这里的对账是断言——后者硬得多。")


if __name__ == "__main__":
    exp1_plan_vs_one_shot()
    exp2_plan_validation()
    exp3_assert_and_replan()
    exp4_generator_verifier()
    print("\n四个实验跑完。计划不是装饰：它是能被校验、被执行、被修复的对象。")
    print("回去读第 17 章（附录D）的「跟着做」一节，把断言和校验搬进你自己的链路。")
    sys.exit(CHECKS.report())
