"""一键把 examples 全部跑一遍，最后给一张结果表。

    uv run python examples/run_all.py              # 先跑离线组，再跑需要 Key 的组
    uv run python examples/run_all.py --offline    # 只跑不需要 Key 的
    uv run python examples/run_all.py --live       # 只跑需要 Key 的
    uv run python examples/run_all.py --only 06    # 只跑第 06 章那一组（06a/06b/06c 全跑）

每个例子都是独立子进程，互不影响；失败的会打印末尾输出，方便你直接定位。
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

import _shared  # noqa: F401  （导入时会把 Windows 控制台切到 UTF-8）

HERE = Path(__file__).parent
CHECKPOINT_DB = HERE / "checkpoints.db"

# (脚本, 命令行参数) —— 06a 需要跑两次才能演示"跨进程恢复"
OFFLINE = [
    ("05_graph_basics.py", None),
    ("06a_persistence_resume.py", "first"),
    ("06a_persistence_resume.py", "second"),
    ("07a_human_approval_offline.py", None),
    ("08a_index_offline.py", None),
    ("16_agent_security_lab.py", None),
]

LIVE = [
    ("02_hello_agent.py", None),
    ("03_handwritten_loop.py", None),
    ("04_structured_output.py", None),
    ("06b_memory_agent.py", None),
    ("06c_long_term_memory.py", None),
    ("07b_hitl_graph.py", None),
    ("08b_rag_agent.py", None),
    ("10_mcp_docs_server.py", None),
    ("12_mini_project_coffee_shop.py", None),
]


def has_key() -> bool:
    if os.getenv("MODEL_API_KEY") or os.getenv("AGNES_API_KEY") or os.getenv("OPENAI_API_KEY"):
        return True
    env_file = HERE / ".env"
    if env_file.exists():
        text = env_file.read_text(encoding="utf-8", errors="replace")
        return any(
            line.strip().startswith(("AGNES_API_KEY=", "MODEL_API_KEY=", "OPENAI_API_KEY="))
            and not line.strip().endswith("=")
            for line in text.splitlines()
            if not line.strip().startswith("#")
        )
    return False


# 免费额度有速率上限：一口气跑十几个例子会撞 429（实测 agnes-2.5-flash）。
# 这不是你的代码错，所以这里自动等一会儿重试，并且给例子之间留间隔。
RATE_LIMIT_HINTS = ("429", "RateLimitError", "速率限制")
RETRY_WAITS = (20, 45)      # 每次撞限流后的等待秒数
PACE = 3.0                  # 在线组每个例子之间歇一下


def _attempt(script: str, arg: str | None) -> tuple[bool, float, str, str]:
    """跑一次例子，返回 (是否成功, 秒数, 失败时的输出尾部, 完整输出)。"""
    cmd = [sys.executable, script] + ([arg] if arg else [])
    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd,
            cwd=HERE,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=900,
            # 子进程同样强制 UTF-8，否则 Windows GBK 控制台下打印 emoji 会直接崩
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
    except subprocess.TimeoutExpired:
        return False, time.time() - t0, "     超时（15 分钟）", "TimedOut"

    elapsed = time.time() - t0
    ok = proc.returncode == 0
    if ok:
        return True, elapsed, "", proc.stdout or ""

    tail = (proc.stdout or "").strip().splitlines()[-6:]
    err = (proc.stderr or "").strip().splitlines()[-12:]
    shown = "\n".join(f"     {line}" for line in tail + err)
    return False, elapsed, shown, (proc.stdout or "") + "\n" + (proc.stderr or "")


def run_one(script: str, arg: str | None) -> tuple[bool, float, str]:
    label = script + (f" {arg}" if arg else "")
    print(f"\n▶ {label}", flush=True)

    for attempt, wait in enumerate((0.0, *RETRY_WAITS)):
        if wait:
            print(f"  ⏳ 撞上限流（429），等 {wait:.0f}s 自动重试……", flush=True)
            time.sleep(wait)
        ok, elapsed, shown, raw = _attempt(script, arg)
        if ok:
            note = "（限流重试后通过）" if attempt else ""
            print(f"  ✅ 通过（{elapsed:.1f}s）{note}")
            return True, elapsed, ""
        if attempt < len(RETRY_WAITS) and any(h in raw for h in RATE_LIMIT_HINTS):
            continue
        print(f"  ❌ 失败（{elapsed:.1f}s）")
        print(shown)
        return False, elapsed, "有输出见上"

    return False, 0.0, "限流重试仍失败"


def run_group(name: str, cases: list, results: list, pace: float = 0.0) -> None:
    print("\n" + "=" * 60)
    print(name)
    print("=" * 60)
    for i, (script, arg) in enumerate(cases):
        if i and pace:
            time.sleep(pace)
        ok, elapsed, note = run_one(script, arg)
        results.append((script + (f" {arg}" if arg else ""), ok, elapsed, note))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true", help="只跑不需要 Key 的例子")
    parser.add_argument("--live", action="store_true", help="只跑需要 Key 的例子")
    parser.add_argument("--only", default=None, help="只跑章号匹配的那一组，如 06 会跑 06a/06b/06c")
    args = parser.parse_args()

    if not (args.offline or args.live or args.only):
        args.offline = args.live = True

    results: list = []

    if args.only:
        cases = [(s, a) for s, a in OFFLINE + LIVE if s.startswith(args.only)]
        if not cases:
            print(f"没找到章号以 {args.only} 开头的例子")
            return
        run_group(f"只跑 {args.only}", cases, results)
    else:
        if args.offline:
            # 02 会写 SQLite，先清掉保证"第一次运行"是真的第一次
            if CHECKPOINT_DB.exists():
                CHECKPOINT_DB.unlink()
            run_group("第一组：不需要 Key（离线）", OFFLINE, results)

        if args.live:
            if has_key():
                run_group("第二组：需要模型 Key", LIVE, results, pace=PACE)
            else:
                print("\n" + "=" * 60)
                print("第二组：需要模型 Key —— 已跳过")
                print("=" * 60)
                print("  没有检测到 Key。执行下面两步后重跑：")
                print("    cp examples/.env.example examples/.env")
                print("    # 在 examples/.env 里填 AGNES_API_KEY=...")
                print("  然后：uv run python examples/run_all.py --live")

    # ── 汇总 ────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("结果汇总")
    print("=" * 60)
    if not results:
        print("  没有执行任何例子")
        return

    passed = sum(1 for _, ok, _, _ in results if ok)
    for name, ok, elapsed, _ in results:
        print(f"  {'✅' if ok else '❌'} {name:<38} {elapsed:>6.1f}s")
    print("-" * 60)
    print(f"  通过 {passed}/{len(results)}")

    if passed == len(results):
        print("\n  全部通过 🎉  下一步看 LEARNING_PLAN 第 6 周：用 LangGraph 重写案例")
    else:
        print("\n  如果失败里出现 429 / '速率限制'：那是免费额度的速率上限，隔几分钟再跑；")
        print("  其余情况，把失败那条的完整报错贴给我，我来修。")


if __name__ == "__main__":
    main()
