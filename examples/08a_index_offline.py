"""08a — 知识库的索引动作（离线可跑，不需要 Key）

这个例子不花钱，因为用的是【假 embedding】——它只验证"链路通不通"，
向量本身没有语义，所以别指望它答对问题。

但知识库里真正容易搞错的几件事，跟向量质量无关，这里全能看清：
  1. 文档怎么切分（chunk）
  2. metadata 过滤（多租户 / 权限隔离就靠它）
  3. 同 id 覆盖 = 更新机制
  4. 删除

依赖：uv add langchain-text-splitters numpy
  （numpy 是 DeterministicFakeEmbedding 的隐性依赖，langchain-core 没有声明它）

真实效果只要把假 embedding 换成真 embedding 即可（文件最后一行有说明）。

⚠️ 已实测的陷阱（langchain-core 1.6.4）：
  InMemoryVectorStore 的 filter 只接受【可调用对象】 (Document) -> bool，
  传元数据字典会直接崩：TypeError: 'dict' object is not callable。
  原因在它内部：filter 这个参数名把内置函数 filter() 遮盖了，而库里真的去调用它。
  字典式过滤（{"$eq": ...}）是 Chroma / PGVector 这类集成各自实现的，不是通用协议。
"""

import _shared  # noqa: F401  （导入时会把 Windows 控制台切到 UTF-8，避免打印 emoji 崩溃）
from langchain_core.documents import Document
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 我们的小知识库：一份咖啡店规则文档（故意写得很啰嗦，方便演示切分）
DOC = """
营业时间：周一至周五 08:00-20:00。周六 09:00-22:00。周日休息，不营业。
节假日营业时间另行通知，请关注店内公告。

会员制度：单次消费满 100 元可注册会员。会员每次消费可累积 1 元 1 分。
积分满 500 分可兑换一杯中杯拿铁。会员生日当天可享 8 折优惠。

退款规则：饮品制作前可全额退款。已制作完成的饮品不支持退款。
金额超过 500 元的订单退款，需要店长人工审批。
"""


def by_metadata(**expected: str):
    """把 {"field": "value"} 这种简单条件转成 InMemoryVectorStore 能吃的谓词。

    这一层转换不是装饰——它正好暴露了"过滤语法没有跨库统一标准"这件事。
    换到 pgvector 你写的又是另一套（$eq/$in/$and），所以别把过滤语法硬编码进业务层。
    """

    def predicate(doc: Document) -> bool:
        return all(doc.metadata.get(key) == value for key, value in expected.items())

    return predicate


def main() -> None:
    # ------------------------------------------------------------------
    # 1. 切分：把长文档切成小块（块太大检索不准，太小会丢上下文）
    # ------------------------------------------------------------------
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=60,        # 每块最多 60 字（真实项目一般 300-800）
        chunk_overlap=10,     # 相邻块重叠 10 字，避免把句子切断
        separators=["\n\n", "\n", "。", "，", ""],
    )
    chunks = splitter.split_documents(
        [Document(page_content=DOC.strip(), metadata={"source": "coffee-rules.md"})]
    )

    print("=" * 60)
    print(f"切分结果：{len(chunks)} 块")
    print("=" * 60)
    for i, c in enumerate(chunks):
        print(f"  [{i}] {c.page_content[:40]}...")

    # ------------------------------------------------------------------
    # 2. 灌进向量库（假 embedding：只为跑通流程）
    # ------------------------------------------------------------------
    embeddings = DeterministicFakeEmbedding(size=256)
    store = InMemoryVectorStore(embeddings)          # 位置参数，别写成 embedding=

    docs = []
    for i, c in enumerate(chunks):
        docs.append(
            Document(
                page_content=c.page_content,
                metadata={
                    "id": f"rule-{i}",                  # ★ 稳定的 id 是更新/删除的前提
                    "source": "coffee-rules.md",
                    "tenant": "shop-001",                # ★ 多租户隔离字段
                    "category": "营业时间" if "营业" in c.page_content else "规则",
                },
            )
        )

    ids = store.add_documents(docs, ids=[d.metadata["id"] for d in docs])
    print(f"\n已入库 {len(ids)} 条，ids={ids}")

    # ------------------------------------------------------------------
    # 3. 元数据过滤：权限/租户隔离靠它，不靠模型自觉
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("元数据过滤")
    print("=" * 60)

    only_hours = store.similarity_search("营业时间", k=20, filter=by_metadata(category="营业时间"))
    print(f"  只看 category='营业时间' → 命中 {len(only_hours)} 条")
    for d in only_hours:
        print(f"    - {d.page_content[:36]}...")

    other_tenant = store.similarity_search("营业时间", k=20, filter=by_metadata(tenant="shop-999"))
    print(f"  换个 tenant='shop-999' → 命中 {len(other_tenant)} 条（看不到别家的数据 ✅）")

    # 下面是反面示范：字典过滤在这个向量库上会崩。注释掉是因为它会中断整个脚本。
    #   store.similarity_search("营业时间", k=20, filter={"category": "营业时间"})
    #   → TypeError: 'dict' object is not callable
    # 请亲手把那行的注释去掉跑一次，这是最能记住"API 不统一"的一课。
    try:
        store.similarity_search("营业时间", k=20, filter={"category": "营业时间"})
    except TypeError as e:
        print(f"\n  [演示] 传字典会崩：TypeError: {e}")
        print("         同一个 as_retriever(search_kwargs={'filter': {...}}) 写法在 Chroma/PGVector 才成立。")

    # ------------------------------------------------------------------
    # 4. 更新：同一个 id 再写一次 = 覆盖
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("更新一条（同 id 覆盖）")
    print("=" * 60)
    store.add_documents(
        [Document(page_content="营业时间：周六改为 10:00-23:00。", metadata={"id": "rule-0", "category": "营业时间"})],
        ids=["rule-0"],
    )
    after = store.similarity_search("营业时间", k=20, filter=by_metadata(category="营业时间"))
    print(f"  更新后命中 {len(after)} 条（数量不变，说明是覆盖而不是新增）")

    # ------------------------------------------------------------------
    # 5. 删除
    # ------------------------------------------------------------------
    store.delete(ids=["rule-0"])
    after_delete = store.similarity_search("营业时间", k=20, filter=by_metadata(category="营业时间"))
    print(f"  删除 rule-0 后命中 {len(after_delete)} 条")

    print("\n" + "=" * 60)
    print("上面所有结论都与向量质量无关，换成真 embedding 结果一样。")
    print("")
    print("⚠️ 但有个现实要注意：embedding 是【另一条供应链】。")
    print("   Agnes 文档列出的端点没有 /embeddings，也没有 embedding 模型，")
    print("   所以 chat 的 Key 算不了向量，RAG 必须另找一家（或先用假 embedding 学）。")
    print("")
    print("要看真实检索效果，在 examples/.env 里加：")
    print("   EMBEDDING_MODEL=text-embedding-3-small")
    print("   EMBEDDING_API_KEY=sk-...")
    print("（也可用本地模型 fastembed / Ollama；见 _shared.get_embeddings()）")
    print("=" * 60)


if __name__ == "__main__":
    main()
