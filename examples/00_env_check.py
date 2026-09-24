"""00 — 环境自检（先跑这个）

    uv run python examples/00_env_check.py           # 只查环境，不发请求
    uv run python examples/00_env_check.py --live    # 再真实调用一次，验证 Key 和工具调用

--live 会顺便测一件对智能体开发最要命的事：**这个模型到底会不会调用工具**。
不会调工具，后面所有 agent 写法都跑不通。
"""

import os
import sys
import time

import _shared  # noqa: F401  （导入时会把 Windows 控制台切到 UTF-8，避免打印 emoji 崩溃）


def version_checks() -> int:
    """返回不可用的 API 数量（0 = 全部可用）。"""
    from importlib.metadata import PackageNotFoundError, version

    print(f"Python: {sys.version.split()[0]}")
    print("-" * 56)

    # 注意：langgraph 没有 __version__ 属性，必须走 importlib.metadata
    for pkg in ("langchain", "langgraph", "langchain-core", "langchain-openai"):
        try:
            print(f"  {pkg:<18}: {version(pkg)}")
        except PackageNotFoundError:
            print(f"  {pkg:<18}: 未安装")

    print("-" * 56)

    checks = [
        ("from langchain.agents import create_agent", "新版智能体入口（旧版叫 create_react_agent）"),
        ("from langchain.chat_models import init_chat_model", "统一模型初始化"),
        ("from langchain.tools import tool", "工具装饰器"),
        ("from langchain.agents.structured_output import ToolStrategy", "结构化输出"),
        ("from langgraph.graph import StateGraph, START, END", "图 API"),
        ("from langgraph.graph.message import add_messages", "消息 reducer"),
        ("from langgraph.types import interrupt, Command, Overwrite", "人工中断 / 清空字段"),
        ("from langgraph.checkpoint.memory import InMemorySaver", "内存 checkpointer"),
    ]

    failed = 0
    for stmt, why in checks:
        try:
            exec(stmt, {})
            print(f"  OK   {stmt}")
        except Exception as e:
            failed += 1
            print(f"  FAIL {stmt}\n       ({why})\n       {type(e).__name__}: {e}")

    print("-" * 56)
    if failed:
        print(f"{failed} 项不可用 → 先升级：uv add --upgrade langchain langgraph")
    else:
        print("核心 API 全部可用 ✅")
    print("提醒：判断一份教程死活，搜有没有 AgentExecutor。有 = 过时。")
    return failed


def live_check() -> int:
    """返回退出码：0 = 两项检查都通过；1 = 没跑成或模型不会调工具。"""
    try:
        from _shared import get_model, resolve_config, title
        from langchain.tools import tool
    except ImportError as e:
        print(f"\n无法导入示例依赖（{e}）→ 先执行：uv add langchain langchain-openai python-dotenv")
        return 1

    config = resolve_config()
    title("当前配置（来自 examples/.env 或环境变量）")
    masked = config.get("api_key", "")
    print(f"  model    : {config['model']}")
    print(f"  base_url : {config.get('base_url', '(provider 默认)')}")
    print(f"  api_key  : {'已设置 (' + masked[:6] + '...)' if masked else '未设置'}")

    if not config.get("api_key") and not os.environ.get("OPENAI_API_KEY"):
        print("\n没有找到 Key。请在 examples/.env 里填 AGNES_API_KEY=...")
        return 1

    @tool
    def get_time(city: str) -> str:
        """查询指定城市的当前时间。"""
        return f"{city} 现在是 10:30"

    # 超时给足但不算无限：网关侧某个模型卡住时，你应该在 45 秒内拿到结论，
    # 而不是盯着光标干等（实测 agnes-3.0-flash 就是这个症状）。
    LIVE_TIMEOUT = 45

    try:
        model = get_model(temperature=0, timeout=LIVE_TIMEOUT, max_retries=0)

        title("1/2 普通调用")
        t0 = time.time()
        reply = model.invoke("用一句中文回答：你是谁？")
        print(f"  耗时 {time.time() - t0:.1f}s")
        print(f"  回复: {str(reply.content)[:100]}")

        title("2/2 工具调用（智能体的生命线）")
        t0 = time.time()
        ai = model.bind_tools([get_time]).invoke("上海现在几点？必须调用工具查，不要猜。")
        elapsed = time.time() - t0
        calls = getattr(ai, "tool_calls", None)

        if calls:
            print(f"  ✅ 会调用工具（{elapsed:.1f}s）")
            print(f"     模型要求调用: {calls[0]['name']}({calls[0]['args']})")
            print("\n  可以开始学了：uv run python examples/02_hello_agent.py")
        else:
            print(f"  ❌ 没有发起工具调用（{elapsed:.1f}s）——这个模型做不了智能体")
            print(f"     模型原话: {str(ai.content)[:150]}")
            print("\n  解决：在 examples/.env 里换模型试试")
            print("     MODEL=agnes-2.5-flash  （默认，实测会调工具）")
            print("     然后重新执行：uv run python examples/00_env_check.py --live")
            return 1
        return 0
    except Exception as e:
        print(f"\n调用失败：{type(e).__name__}: {e}")

        # 超时是最容易被误判成"我哪儿写错了"的一种失败：其实请求已经发出去了，
        # 是网关侧没回。分开提示，省你半小时。
        text = f"{type(e).__name__} {e}".lower()
        if "timeout" in text or "timed out" in text:
            print("\n  ⚠️ 这是【网关侧没有响应】，不是你的代码或 Key 的问题：")
            print(f"     - 模型 {config['model']} 在 {LIVE_TIMEOUT} 秒内一个字都没返回")
            print("     - 同一个 Key 调别的模型是通的（这是判断依据）")
            print("\n  解决：在 examples/.env 里换一行模型名，再重跑本条命令")
            print("     MODEL=agnes-2.5-flash   （实测正常，会调工具）")
            print("     实测记录：2026-09-23 agnes-3.0-flash 就是这个症状；")
            print("               agnes-2.5-pro 在免费额度下直接 403（也跟你无关）")
            return 1

        print("\n排查顺序：")
        print("  1. Key 是否正确、有没有空格")
        print("  2. MODEL_BASE_URL 是否是 https://api.agnes-ai.cn/v1")
        print("  3. 模型名是否写对（agnes-2.5-flash / agnes-3.0-flash …）")
        print("  4. 网络能否访问该网关")
        return 1


if __name__ == "__main__":
    failed = version_checks()
    if "--live" in sys.argv:
        failed += live_check()
    else:
        print("\n下一步：加 --live 做一次真实调用测试")
        print("  uv run python examples/00_env_check.py --live")
    sys.exit(1 if failed else 0)
