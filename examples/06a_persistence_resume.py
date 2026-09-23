"""06a — 用 SQLite 真正落盘 + thread_id 续跑（离线可跑，不需要 Key）

这个例子要你【分两次运行】，才能看到"状态真的存到磁盘了"：

    uv run python examples/06a_persistence_resume.py first
    # 关掉终端、甚至重启电脑都行
    uv run python examples/06a_persistence_resume.py second

第二次会从数据库里把状态读回来，继续往下走。
这就是"断点续跑"，也是为什么你不用再自己搭一套 Redis 任务队列。

依赖：uv add langgraph-checkpoint-sqlite
"""

import sys
from pathlib import Path

import _shared  # noqa: F401  （导入时会把 Windows 控制台切到 UTF-8，避免打印中文乱码）
from typing_extensions import TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

DB_PATH = Path(__file__).parent / "checkpoints.db"
THREAD_ID = "user-001"          # ★ 相当于 session_id，换成别的就"失忆"了


class CustomerState(TypedDict):
    name: str
    visits: int


def welcome(state: CustomerState) -> dict:
    """把来访次数 +1。第一次是"新客人"，之后就是"回头客"。"""
    visits = state.get("visits", 0) + 1
    if visits == 1:
        print(f"  [welcome] 欢迎新客人！")
    else:
        print(f"  [welcome] 欢迎回来，{state.get('name')}（第 {visits} 次访问）")
    return {"visits": visits}


def build_graph(checkpointer):
    builder = StateGraph(CustomerState)
    builder.add_node("welcome", welcome)
    builder.add_edge(START, "welcome")
    builder.add_edge("welcome", END)
    return builder.compile(checkpointer=checkpointer)


def main() -> None:
    step = sys.argv[1] if len(sys.argv) > 1 else "first"
    if step not in ("first", "second"):
        print("用法：python 06a_persistence_resume.py [first|second]")
        sys.exit(1)

    # with 会自动开关连接。生产环境把这一行换成 PostgresSaver 即可（API 一样）：
    #   from langgraph.checkpoint.postgres import PostgresSaver
    #   with PostgresSaver.from_conn_string(DB_URI) as checkpointer: ...
    with SqliteSaver.from_conn_string(str(DB_PATH)) as checkpointer:
        graph = build_graph(checkpointer)
        config = {"configurable": {"thread_id": THREAD_ID}}      # ★ 必须有

        if step == "first":
            print("【第一次运行】录入客人姓名")
            graph.invoke({"name": "小明", "visits": 0}, config)
            print(f"\n已写入数据库：{DB_PATH}")
            print("现在把进程关掉，再执行：")
            print("  uv run python examples/06a_persistence_resume.py second")
        else:
            print("【第二次运行】读取上次留下的状态")
            snapshot = graph.get_state(config)
            print(f"  从数据库读到的状态: {snapshot.values}")
            print("  可以看到：这一次进程里从来没有设置过 name/visits，值是磁盘给的。")

            # ★ 关键：输入传空字典 {}，不覆盖任何字段，直接用磁盘上的状态继续跑
            graph.invoke({}, config)

            final = graph.get_state(config)
            print(f"运行后的状态: {final.values}")
            print(f"  历史 checkpoint 数量: {len(list(graph.get_state_history(config)))}")


if __name__ == "__main__":
    main()
