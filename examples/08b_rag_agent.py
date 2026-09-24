"""08b — RAG：给 agent 一个能查内部资料的检索工具（需要 Key）

这是最容易理解的一种 RAG（官方叫 2-Step 的变体 / Agentic RAG）：
   把检索包装成一个工具，让模型自己决定要不要查。

观察重点：知识库里没有的东西，它应该说"不知道"，而不是编。

脚本自带断言（`_shared.Checks`）：知识库里**有**的事实必须带对（周六 22:00 / 500 分），
知识库里**没有**的必须承认不知道、且不得出现任何具体数字（编造就是在这里被抓的）。
断言写在语义特征上（第 11 章），不比对整句话——模型的措辞会漂：22:00 可能被说成
「晚上十点」，所以时间特征用等价说法的正则去匹配，而不是死抠字面「22」。
失败即以非 0 退出码结束。
"""

import re
import sys

from _shared import Checks, get_embeddings, get_model, title

from langchain.agents import create_agent
from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.tools import tool

CHECKS = Checks()

# 承认不知道的说法（语义特征，不是唯一措辞——见第 11 章）
UNSURE_MARKERS = ("不知道", "不确定", "没有", "未", "无法", "查不到", "抱歉", "暂无", "不包含")


def says_dont_know(text: str) -> bool:
    return any(marker in text for marker in UNSURE_MARKERS)


# ── 小知识库（真实项目里换成你的产品手册 / 客服 FAQ）─────────────────────
RAW_DOCS = [
    Document(
        page_content="营业时间：周一至周五 08:00-20:00；周六 09:00-22:00；周日休息。",
        metadata={"source": "营业规则", "tenant": "shop-001"},
    ),
    Document(
        page_content="会员制度：单次消费满 100 元可注册会员，1 元累计 1 分，满 500 分可换中杯拿铁一杯。",
        metadata={"source": "会员规则", "tenant": "shop-001"},
    ),
    Document(
        page_content="退款规则：饮品制作前可全额退款；已制作完成不支持退款；金额超过 500 元需店长审批。",
        metadata={"source": "退款规则", "tenant": "shop-001"},
    ),
]


def build_retriever():
    """建索引入口。注意它是【函数】而不是模块级代码。

    反面写法（我一开始就是这么写的）：
        RETRIEVER = build_retriever()      # ← 模块被 import 时就真的去建索引了
    后果：任何人 import 这个文件都会触发网络请求；没配 Key 就直接崩在 import 行。
    **有副作用的初始化要放在函数里、由入口显式调用。**
    """
    splitter = RecursiveCharacterTextSplitter(chunk_size=120, chunk_overlap=20)
    splits = splitter.split_documents(RAW_DOCS)
    store = InMemoryVectorStore.from_documents(documents=splits, embedding=get_embeddings())
    # 换成生产向量库时，只有这一行要改（PGVector / Chroma / Qdrant）
    return store.as_retriever(search_kwargs={"k": 2})


def make_search_tool(retriever):
    """把检索器包成工具：模型自己决定要不要查、查什么。"""

    @tool
    def search_rules(query: str) -> str:
        """查询咖啡店的内部规则（营业时间、会员、退款等）。query 用中文自然语言。"""
        docs = retriever.invoke(query)
        if not docs:
            return "知识库里没有找到相关内容。"
        return "\n".join(f"[{d.metadata['source']}] {d.page_content}" for d in docs)

    return search_rules


def main() -> None:
    retriever = build_retriever()
    search_rules = make_search_tool(retriever)

    agent = create_agent(
        # 温度 0：RAG 管线的演示要的是稳定复现，不是文采（00 / 06c 同款）
        model=get_model(temperature=0),
        tools=[search_rules],
        system_prompt=(
            "你是咖啡店客服。回答涉及店内规则的问题时，必须先调用 search_rules 查询，"
            "只根据查到的内容回答；查不到就明确说不知道，不要编造。"
        ),
    )

    # (问题, 答案必须命中的事实特征（正则），特征的人话描述)
    # None = 知识库里没有，必须承认不知道
    questions = [
        # 22:00 的措辞会漂：22:00 / 22 点 / 晚上十点 都算对——断言的是"答对了时间"这个语义，
        # 不是某个字面写法（这正是第 11 章"断言写在语义特征上"的活例子）
        ("你们周六几点关门？", r"22[:：]\s*00|22\s*点|十点|10\s*点", "周六关门时间 22:00"),
        ("满多少分可以换咖啡？", r"500", "兑换门槛 500 分"),
        ("你们卖咖啡豆吗？", None, "知识库里没有咖啡豆"),
    ]

    for q, expect_fact, label in questions:
        title(f"问：{q}")
        result = agent.invoke({"messages": [{"role": "user", "content": q}]})

        # 把工具调用过程打出来，方便看清"答案有没有依据"
        used_retrieval = False
        for msg in result["messages"]:
            for call in getattr(msg, "tool_calls", None) or []:
                used_retrieval = True
                print(f"  🔍 检索: {call['args']}")
            if type(msg).__name__ == "ToolMessage":
                print(f"  📄 查到: {msg.content[:80]}...")
        answer = str(result["messages"][-1].content)
        print(f"  💬 回答: {answer}")

        if expect_fact:
            CHECKS.expect(used_retrieval, "回答前先调了 search_rules（不是凭记忆答）")
            CHECKS.expect(re.search(expect_fact, answer) is not None,
                          f"知识库里有 → 答案带上「{label}」")
        else:
            CHECKS.expect(says_dont_know(answer), "知识库里没有 → 明确承认不知道")
            # 编造的指纹：冒出一个知识库里根本没有的规格/价格数字
            CHECKS.expect(not re.search(r"\d+\s*(元|块|克|袋|包|斤|毫升|ml)", answer),
                          "知识库里没有 → 没有编出价格/规格数字")

    title("下一步可以做什么")
    print("  1. 换成生产向量库：pgvector（Postgres 扩展）/ Chroma / Qdrant")
    print("  2. 加元数据过滤，做多租户隔离（见 08a_index_offline.py）")
    print("  3. 检索质量不够时：先加 MMR，再加混合检索与重排（Rerank）")
    print("  4. 让模型自己决定改不改写问题再查 → 就是官方说的 Hybrid RAG")
    print("\n  灌数据的脚本要单独可重跑，别写在 agent 里。")


if __name__ == "__main__":
    main()
    sys.exit(CHECKS.report())
