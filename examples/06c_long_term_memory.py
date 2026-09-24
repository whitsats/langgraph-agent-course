"""06c — 长期记忆：跨会话记住一个人（需要 Key）

短期记忆 = checkpointer：同一个 thread 内的对话，框架替你记。
长期记忆 = Store：跨 thread、跨进程，按 namespace 存——「换一个会话也不失忆」。

这个例子分两半：

  第一部分（不需要模型）：Store 的四个动作
    put / get / search / namespace 隔离——多用户隔离靠的是 namespace，不是 prompt。
  第二部分（需要 Key）：把它接进 agent
    在 thread chat-001 说一遍 → 换到 chat-002（全新会话）→ 依然记得你是谁。

为什么不是「把资料拼进 system_prompt」？因为那样只对当前这次请求有效，
而且用户画像会越拼越长。长期记忆要的是「按用户取、按主题召回」。

脚本自带断言（`_shared.Checks`）：Store 的读写与 namespace 隔离、以及
换会话后依然记得你。失败即以非 0 退出码结束（run_all 会变红）。
"""

import os
import sys
import uuid

import _shared  # noqa: F401  （导入时会把 Windows 控制台切到 UTF-8）
from _shared import Checks, get_model, title

CHECKS = Checks()

from langchain.agents import AgentState, create_agent
from langchain.tools import ToolRuntime, tool
from langchain_core.embeddings import DeterministicFakeEmbedding
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

USER_A = "user-001"
USER_B = "user-002"


def build_store() -> InMemoryStore:
    """建一个「能语义检索」的 Store。

    index 里的 embed 决定 search(query=...) 怎么算相似度。
    这里用假 embedding：跑得通、不花钱、但结果无语义（和 08a 的例子同一个思路）。
    要真效果就换成真 embedding（EMBEDDING_MODEL / EMBEDDING_API_KEY，见 _shared.get_embeddings）。

    ⚠️ 实测细节：不配 index 时 search(query=...) 不会报错，而是退化成
    「按插入顺序列出来」（返回项的 score 为 None）——静默降级，很容易被骗。
    """
    return InMemoryStore(index={"dims": 64, "embed": DeterministicFakeEmbedding(size=64)})


def demo_store(store: InMemoryStore) -> None:
    title("第一部分：Store 的四个动作（不需要模型）")

    # namespace = 记忆的抽屉。第一个维度给业务分类，第二个维度回答「这是谁的记忆」。
    store.put(("memories", USER_A), "fact-1", {"fact": "王小明喝咖啡不加糖"})
    store.put(("memories", USER_A), "fact-2", {"fact": "王小明对花生过敏"})
    store.put(("memories", USER_B), "fact-1", {"fact": "李雷只喝美式"})

    print("  put 之后，Store 里有哪些 namespace：")
    for ns in store.list_namespaces():
        print(f"    {ns}")

    got = store.get(("memories", USER_A), "fact-1")
    print(f"\n  get → {got.value}")

    hits = store.search(("memories", USER_A), query="口味", limit=5)
    print(f"\n  search(query='口味') 命中 {len(hits)} 条：")
    for h in hits:
        print(f"    - {h.value['fact']}")
    print(f"  （只命中 {USER_A} 自己的记忆，看不到 {USER_B} 的——隔离靠 namespace，不靠 prompt）")

    namespaces = [tuple(ns) for ns in store.list_namespaces()]
    CHECKS.expect(got is not None and "不加糖" in got.value["fact"], "Store.get 取回刚写进去的事实")
    CHECKS.expect(("memories", USER_A) in namespaces and ("memories", USER_B) in namespaces,
                  "两个用户的记忆各占一个 namespace（隔离靠 namespace，不靠 prompt）")
    CHECKS.expect(len(hits) == 2 and not any("李雷" in h.value["fact"] for h in hits),
                  f"search 只在 {USER_A} 自己的抽屉里找（共 2 条，看不到 {USER_B} 的）")

    print("\n  记忆点：checkpointer 由框架自动管；Store 要你自己设计")
    print("         ——存什么、存谁的、什么时候写。")


def build_agent(store: InMemoryStore):
    @tool
    def remember(fact: str, runtime: ToolRuntime[None, AgentState]) -> str:
        """把关于当前用户的一条事实写进长期记忆。一条一句话，例如「喝咖啡要少冰」。"""
        user_id = runtime.config["configurable"]["user_id"]
        # id 必须全局唯一：拿「现有条数」拼 id（fact-{len(existing)}）会撞掉旧条目
        # —— put 的语义是「同 id 覆盖」，不是追加（和 08a 的更新机制同一件事）。
        runtime.store.put(("memories", user_id), uuid.uuid4().hex, {"fact": fact})
        return "已记住。"

    @tool
    def recall(query: str, runtime: ToolRuntime[None, AgentState]) -> str:
        """从长期记忆里回忆关于当前用户的事。query 是主题，例如「咖啡」或「过敏」。"""
        user_id = runtime.config["configurable"]["user_id"]
        hits = runtime.store.search(("memories", user_id), query=query, limit=3)
        if not hits:
            return "没有相关记忆。"
        return "\n".join(h.value["fact"] for h in hits)

    return create_agent(
        model=get_model(temperature=0),
        tools=[remember, recall],
        system_prompt=(
            "你是咖啡店客服，回答要简短。"
            "涉及用户的身份、偏好、病史时，先调用 recall 查长期记忆，不要凭猜。"
        ),
        checkpointer=InMemorySaver(),   # 短期记忆：这个 thread 内的对话
        store=store,                    # ★ 长期记忆：工具里通过 runtime.store 拿到
    )


def demo_agent(store: InMemoryStore) -> None:
    title("第二部分：接进 agent（跨会话记住同一个人）")

    agent = build_agent(store)
    # ★ 关键区别：thread_id 是「这一次会话」，user_id 是「这个人」。
    #   记忆挂在 user_id 上，所以换会话也找得到。
    config1 = {"configurable": {"thread_id": "chat-001", "user_id": USER_A}}
    config2 = {"configurable": {"thread_id": "chat-002", "user_id": USER_A}}

    print(f"（会话 1，thread_id={config1['configurable']['thread_id']}）说一遍偏好：")
    r1 = agent.invoke(
        {"messages": [{"role": "user", "content": "记一下：我喝咖啡要少冰，另外我对花生过敏。"}]},
        config1,
    )
    print(f"  回答: {str(r1['messages'][-1].content)[:80]}")

    print(f"\n（会话 2，thread_id={config2['configurable']['thread_id']}——全新会话，同一个人）")
    r2 = agent.invoke(
        {"messages": [{"role": "user", "content": "我上次说的咖啡偏好是什么？我对什么过敏？"}]},
        config2,
    )
    print("  它实际调用的工具：")
    for message in r2["messages"]:
        for call in getattr(message, "tool_calls", None) or []:
            print(f"    - {call['name']}({call['args']})")
    answer2 = str(r2["messages"][-1].content)
    print(f"  回答: {answer2[:140]}")

    # 断言撞在"跨会话"上：新 thread 里也必须拿得到同一份记忆
    called = [c["name"] for m in r2["messages"]
              for c in (getattr(m, "tool_calls", None) or [])]
    CHECKS.expect("recall" in called, "会话 2 先调 recall 查长期记忆，而不是凭猜")
    CHECKS.expect(("少冰" in answer2) or ("花生" in answer2),
                  "新会话里依然记得偏好/过敏（跨 thread 记忆生效）")

    print("\n  对照：如果只有 checkpointer、没有 store（第 08 章的例子），")
    print("        会话 2 完全不认识你——checkpointer 跨不出单个 thread。")


def main() -> None:
    store = build_store()
    demo_store(store)

    if not (os.getenv("MODEL_API_KEY") or os.getenv("AGNES_API_KEY") or os.getenv("OPENAI_API_KEY")):
        print("\n第二部分需要模型 Key（Store 本身不需要）。")
        print("在 examples/.env 里填 AGNES_API_KEY=... 后重跑。")
        return

    demo_agent(store)

    title("收尾：上生产前要改的三件事")
    print("  1. 换持久化 Store：InMemoryStore 重启即丢，用户会被「清空记忆」。")
    print("  2. 换真 embedding：search(query=...) 才有真实语义（假 embedding 只把链路跑通）。")
    print("  3. 想清生命周期：记什么类型（语义 / 情景 / 程序）、谁决定写（热路径 or 后台）、怎么删。")
    print("     ——「怎么删」这一条最容易漏：用户要有一个清空记忆的入口。")
    print("\n  官方 Memory 页列了长期记忆的几种后端与安装包："
          "https://docs.langchain.com/oss/python/langgraph/add-memory")


if __name__ == "__main__":
    main()
    sys.exit(CHECKS.report())
