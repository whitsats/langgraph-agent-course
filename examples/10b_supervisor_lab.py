"""10b — supervisor 派活实验室（离线可跑，不需要 Key）

第 10 章讲了扩展能力，第 18 章讲了平级 agent 之间的交接契约——中间还缺一环：
**上下级怎么派活**。一个主管（supervisor）接到任务后拆活、扇出给多个 worker、
再把结果聚合回来，这正是官方 Send API / 子图编排的前置形态。

本 lab 离线模拟这条链路（"主管的决策"像 16/17/18 一样是模拟的），测三个结构：

  1. 派活契约：主管给 worker 的任务是**结构化 dict**，不是一段自由文本（第 18 章）
  2. 失败隔离：一个 worker 崩了，只在自己的格子里记 error，**不能拖垮整张简报**
  3. 结果聚合：只聚合 status="ok" 的结果，失败的在"缺席"栏如实标注

worker 的返回也是结构化 dict——字段是数据不是指令（第 18 章），主管才能机器化聚合。

对应到 LangGraph：supervisor_dispatch → 路由节点用 Send API 一发多；
每个 worker → 一个子图节点；aggregate → reducer（第 05 章）。
真编排时把模拟的 worker 换成子图节点即可，本 lab 的包装层原样保留。

脚本自带断言（`_shared.Checks`）：失败被隔离、成功结果齐全、error 有记录、
简报不含失败 worker 的数据。失败即非 0 退出码结束。
"""

import sys

import _shared  # noqa: F401  （导入时把 Windows 控制台切到 UTF-8）
from _shared import Checks

CHECKS = Checks()

# ---------------------------------------------------------------------------
# 场景：咖啡店周报。三个 worker，其中一个故意埋雷（上周数据缺失，一算环比就崩）
# ---------------------------------------------------------------------------

REVENUE = {"2026-W38": [("拿铁", 8420), ("澳白", 6600), ("美式", 4100)]}
COMPLAINTS = ["等待时间太长", "杯量不符", "会员积分没到账"]


def run_sales(task: dict) -> dict:
    rows = REVENUE[task["week"]]
    return {"总营收": sum(a for _, a in rows), "最畅销": max(rows, key=lambda r: r[1])[0]}


def run_complaints(task: dict) -> dict:
    return {"客诉条数": len(COMPLAINTS), "清单": COMPLAINTS}


def run_forecast(task: dict) -> dict:
    last_week = 0                                    # ← 上周数据没接进来，埋雷
    growth = (19120 - last_week) / last_week * 100
    return {"环比增长%": round(growth, 1)}


WORKERS = {"sales": run_sales, "complaints": run_complaints, "forecast": run_forecast}

# 派活契约：结构化 dict，不是"帮我看下销售情况"这种一段话（对比第 18 章的自由文本交接）
TASKS = [
    {"worker": "sales", "task": {"week": "2026-W38"}},
    {"worker": "complaints", "task": {"week": "2026-W38"}},
    {"worker": "forecast", "task": {"week": "2026-W38"}},
]


# ---------------------------------------------------------------------------
# supervisor 的三段：派活扇出 → 执行（带失败隔离）→ 聚合
# ---------------------------------------------------------------------------

def worker_wrapper(name: str, fn, task: dict) -> dict:
    """失败隔离的边界：包住每一个 worker。真编排里这个 try/except 在节点内部。"""
    try:
        return {"worker": name, "status": "ok", "data": fn(task), "error": None}
    except Exception as exc:
        return {"worker": name, "status": "failed", "data": None,
                "error": f"{type(exc).__name__}: {exc}"}


def supervisor_dispatch(tasks: list[dict]) -> list[dict]:
    """扇出：真编排里这里是 Send API（一发多、并行跑子图）；离线模拟顺序执行——
    要学的是派活与聚合的结构，不是并行本身。"""
    return [worker_wrapper(t["worker"], WORKERS[t["worker"]], t["task"]) for t in tasks]


def aggregate(results: list[dict]) -> dict:
    brief: dict = {"正文": [], "缺席": []}
    for r in results:
        if r["status"] == "ok":
            brief["正文"].append((r["worker"], r["data"]))
        else:
            brief["缺席"].append((r["worker"], r["error"]))
    return brief


def banner(t: str) -> None:
    print("\n" + "=" * 64)
    print(t)
    print("=" * 64)


def main() -> None:
    banner("实验：主管拆任务 → 扇出 → 聚合（一个 worker 崩了，简报照样出）")
    print("  派活：" + "、".join(t["worker"] for t in TASKS))
    results = supervisor_dispatch(TASKS)

    print("\n  各 worker 的回执：")
    for r in results:
        if r["status"] == "ok":
            print(f"    ✅ {r['worker']:<12} data={r['data']}")
        else:
            print(f"    ❌ {r['worker']:<12} error={r['error']}")

    brief = aggregate(results)
    print("\n  聚合出的周报简报：")
    for name, data in brief["正文"]:
        print(f"    [{name}] {data}")
    for name, error in brief["缺席"]:
        print(f"    ⚠️ [{name}] 缺席（{error}）——如实标注，不编数据补位")

    # —— 结构不变量 ——
    status = {r["worker"]: r["status"] for r in results}
    CHECKS.expect(status["sales"] == "ok" and status["complaints"] == "ok",
                  "正常 worker 的结果被完整带回来")
    CHECKS.expect(status["forecast"] == "failed" and "ZeroDivisionError" in (results[2]["error"] or ""),
                  "崩掉的 worker 只在自己的格子里记 error（异常有记录、类型可查）")
    brief_workers = [name for name, _ in brief["正文"]]
    CHECKS.expect(set(brief_workers) == {"sales", "complaints"},
                  "简报正文只聚合 status=ok 的结果")
    CHECKS.expect("forecast" not in brief_workers and len(brief["缺席"]) == 1,
                  "失败 worker 被隔离（不进简报正文，只在缺席栏如实标注）")
    sales_data = dict(brief["正文"])["sales"]
    CHECKS.expect(sales_data["总营收"] == 19120 and sales_data["最畅销"] == "拿铁",
                  "聚合的数据可机器化使用（worker 返回的是结构化 dict，不是一段话）")

    print("\n  对应到 LangGraph（真编排时的替换表）：")
    print("    supervisor_dispatch → 路由节点，用 Send API 一发多（并行跑 worker 子图）")
    print("    worker_wrapper      → 每个 worker 一个节点，try/except 在节点内部")
    print("    aggregate           → reducer 按字段合并（第 05 章）；error 是状态里的普通字段")
    print("    派活契约/回执契约   → 就是第 18 章的交接契约，只是方向变成了上下级")


if __name__ == "__main__":
    main()
    sys.exit(CHECKS.report())
