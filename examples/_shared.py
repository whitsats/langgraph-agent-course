"""示例共用小工具 —— 默认走 Agnes，零配置。

只要在 examples/.env 里填一行就能跑所有"需要 Key"的例子：

    AGNES_API_KEY=sk-...

想换模型/换网关，用环境变量覆盖即可，不用改任何示例代码：

    MODEL=agnes-2.5-pro                  # 换模型
    MODEL_BASE_URL=...                    # 换网关
    MODEL_API_KEY=...                     # 换 Key
    MODEL=openai:gpt-4o OPENAI_API_KEY=.. # 完全换成别家
"""

import os
import sys

try:  # 有 .env 就自动读，没有也不报错
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


def setup_console() -> None:
    """把控制台输出切到 UTF-8（Windows 上这一步是必须的）。

    实测：Windows 默认代码页 GBK，示例里的 ✅ / emoji 会让整个脚本死于
        UnicodeEncodeError: 'gbk' codec can't encode character '\u2705'
    报错位置跟你的逻辑毫无关系，非常劝退。这里在导入时尽力切一次 UTF-8；
    切不动也不影响逻辑（老终端下可以手动 `chcp 65001`）。
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


setup_console()

AGNES_BASE_URL = "https://api.agnes-ai.cn/v1"
# 默认模型。
# 2026-09-23 实测：agnes-3.0-flash 在网关侧【整段无响应】——连接建立、请求收下，
#   然后一个字都不返回（非流式 / 流式 / 带不带 max_tokens 全部 15s+ 超时，连测 4 次）。
#   同一个 Key 调 agnes-2.5-flash 正常（普通调用 ~1s，工具调用 0.8s），
#   所以默认暂时锁 2.5-flash，保证你第一次 `--live` 就能看到 ✅。
#   agnes-3.0-flash 恢复后想换回来：在 examples/.env 里写一行 MODEL=agnes-3.0-flash 即可。
# 注：agnes-2.5-pro 需要更高额度，免费 Key 会直接 403（不是你的配置问题）。
DEFAULT_MODEL = "agnes-2.5-flash"


def resolve_config() -> dict:
    """算出这次要用哪个模型、哪个网关、哪个 Key。打印出来方便排查。"""
    key = os.getenv("MODEL_API_KEY") or os.getenv("AGNES_API_KEY")
    model = os.getenv("MODEL")
    base = os.getenv("MODEL_BASE_URL")

    if not model:
        # 有 Agnes Key 就用 Agnes；否则退回 OpenAI 官方
        model = DEFAULT_MODEL if key else "openai:gpt-4o"

    if ":" not in model:
        # 没有 provider 前缀 → 按 OpenAI 兼容协议走（Agnes 就是这种）
        if base is None and model.startswith("agnes"):
            base = AGNES_BASE_URL
        model = f"openai:{model}"

    config = {"model": model}
    if base:
        config["base_url"] = base
    if key:
        config["api_key"] = key
    return config


def get_model(**kwargs):
    """拿到一个模型实例。所有示例都通过它取模型，方便一处切换。

    默认带超时与少量重试：万一网关侧某个模型卡住（请求收下、然后一个字都不返回），
    你会拿到一个明确的超时错误，而不是无限干等。
    实测 2026-09-23：`agnes-3.0-flash` 就是这样卡住的，换 `agnes-2.5-flash` 立刻正常。
    想自己控制就传参覆盖：`get_model(timeout=120, max_retries=3)`。
    """
    from langchain.chat_models import init_chat_model

    kwargs.setdefault("timeout", 60)
    kwargs.setdefault("max_retries", 1)

    config = resolve_config()
    model = config.pop("model")
    return init_chat_model(model, **config, **kwargs)


def get_embeddings():
    """拿到一个 embedding 实例（RAG 用）。

    ⚠️ 重要现实：**embedding 和 chat 是两条独立供应链。**
    Agnes 文档里列出的端点只有 chat/completions、responses、messages、
    images/generations、videos —— **没有 /embeddings**，模型清单里也没有 embedding 模型。
    所以你的 Agnes Key 不能用来算向量，必须另找一家。

    这个函数把三种情况都兜住，你只用改 .env：

    1. 没配置任何 embedding → 用假 embedding（DeterministicFakeEmbedding）
       ✅ 不用 Key、不用联网、不花钱；❌ 向量没有语义，检索结果是随机的
       → 适合验证"链路通不通"，不适合验证"答得对不对"
    2. 配置了 EMBEDDING_MODEL / EMBEDDING_BASE_URL / EMBEDDING_API_KEY → 走它
    3. 只配了 OPENAI_API_KEY → 走 OpenAI 官方 embedding
    """
    model = os.getenv("EMBEDDING_MODEL")
    base = os.getenv("EMBEDDING_BASE_URL")
    key = os.getenv("EMBEDDING_API_KEY") or os.getenv("OPENAI_API_KEY")

    if not model and not key:
        from langchain_core.embeddings import DeterministicFakeEmbedding

        print("  [!] 未配置 embedding → 用假 embedding（检索结果是随机的，只看链路）")
        print("      要真效果：在 .env 里设 EMBEDDING_MODEL=text-embedding-3-small 和 EMBEDDING_API_KEY=...")
        return DeterministicFakeEmbedding(size=256)

    from langchain_openai import OpenAIEmbeddings

    config: dict = {"model": model or "text-embedding-3-small"}
    if base:
        config["base_url"] = base
    if key:
        config["api_key"] = key
    return OpenAIEmbeddings(**config)


def title(text: str) -> None:
    """打印一个小标题，让输出更容易看。"""
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60)


def show_config() -> None:
    """打印当前生效的配置（不泄露完整 Key）。"""
    config = resolve_config()
    key = config.get("api_key", "")
    masked = f"{key[:6]}...{key[-4:]}" if len(key) > 12 else ("已设置" if key else "未设置")
    print(f"  model    : {config['model']}")
    print(f"  base_url : {config.get('base_url', '(provider 默认)')}")
    print(f"  api_key  : {masked}")
