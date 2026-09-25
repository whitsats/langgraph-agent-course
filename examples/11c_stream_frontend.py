"""11c — 流式输出 + 最小前端（需要 Key）

第 11 章说"流式既是调试工具，也是前端体验"——这一课给它一个能跑的着陆点：
**一个单文件 FastAPI 服务，把 agent 的 token 流包装成 SSE 吐给浏览器**。

  GET /chat?q=你们周六几点关门
  → 一串 SSE 帧：
      data: {"type": "delta", "text": "周六"}     ← 逐 token（前端先出字）
      data: {"type": "delta", "text": "营业"}     ← ……
      data: {"type": "done",  "answer": "…", "usage": {…}}   ← 收尾帧带 token 账（接 11d）

默认模式是**自测**：在 127.0.0.1 随机端口起服务 → 用 httpx 当前端 →
解析 SSE 帧 → 断言"先有 delta、done 在最后、usage 有真数"。
想用浏览器手动玩：`uv run python examples/11c_stream_frontend.py --serve`
然后开 http://127.0.0.1:8765/chat?q=你们周六几点关门

流式 API 用的是 `stream_mode="messages"`（逐 token 稳定可用）；
做审批 UI 时用第 11 章讲的 `stream_events`（拿 stream.interrupts 更直白）。

脚本自带断言（`_shared.Checks`）：帧序正确、delta 拼出非空回答、收尾帧带 usage。
失败即非 0 退出码结束。
"""

import json
import sys
import threading
import time

import _shared  # noqa: F401  （导入时把 Windows 控制台切到 UTF-8）
from _shared import Checks, get_model

CHECKS = Checks()

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

SYSTEM_PROMPT = (
    "你是咖啡店客服。只依据下面的店规简短作答；店规里没有的就承认不知道。\n"
    "店规：周六 09:00-22:00 营业；满 500 积分可换中杯拿铁；超过 500 元的退款需店长审批。"
)


def build_agent():
    from langchain.agents import create_agent

    return create_agent(model=get_model(temperature=0), tools=[], system_prompt=SYSTEM_PROMPT)


def sse_frames(agent, question: str):
    """把 agent 的 token 流包装成 SSE 帧生成器。这就是前后端之间唯一的契约。"""
    answer_parts, usage = [], None
    for msg, _meta in agent.stream(
        {"messages": [{"role": "user", "content": question}]}, stream_mode="messages"
    ):
        delta = str(getattr(msg, "content", "") or "")
        if delta:
            answer_parts.append(delta)
            yield "data: " + json.dumps({"type": "delta", "text": delta}, ensure_ascii=False) + "\n\n"
        if getattr(msg, "usage_metadata", None):
            usage = msg.usage_metadata
    yield "data: " + json.dumps(
        {"type": "done", "answer": "".join(answer_parts), "usage": usage}, ensure_ascii=False
    ) + "\n\n"


app = FastAPI()


@app.get("/chat")
def chat(q: str = "你们周六几点关门？"):
    agent = build_agent()
    return StreamingResponse(sse_frames(agent, q), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# 自测：起服务（随机端口）→ httpx 当前端 → 断言帧序
# ---------------------------------------------------------------------------

def run_selftest() -> None:
    import httpx
    import uvicorn

    config = uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning")  # port=0：系统挑空闲端口
    server = uvicorn.Server(config)
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(200):                      # 等服务就绪（最多 ~10s）
        if server.started:
            break
        time.sleep(0.05)
    port = server.servers[0].sockets[0].getsockname()[1]
    url = f"http://127.0.0.1:{port}/chat"
    print(f"  测试服务已起：{url}")

    frames = []
    with httpx.stream("GET", url, params={"q": "你们周六几点关门？"},
                      timeout=httpx.Timeout(120)) as resp:
        print(f"  HTTP {resp.status_code}，开始收 SSE 帧：")
        for line in resp.iter_lines():
            if line.startswith("data: "):
                frames.append(json.loads(line[len("data: "):]))
                f = frames[-1]
                if f["type"] == "delta":
                    print(f"    ▸ delta: {f['text']!r}")
                else:
                    print(f"    ▪ done : answer={f['answer'][:40]!r} usage.total_tokens="
                          f"{(f.get('usage') or {}).get('total_tokens')}")

    server.should_exit = True                 # 关掉测试服务

    deltas = [f for f in frames if f["type"] == "delta"]
    done = [f for f in frames if f["type"] == "done"]
    CHECKS.expect(len(frames) >= 3 and len(deltas) >= 2,
                  "SSE 流先到多个 delta 帧（前端'先出字'的来源）")
    CHECKS.expect(bool(deltas) and bool(done) and frames[-1]["type"] == "done",
                  "done 帧在最后（前端靠它判断收尾）")
    joined = "".join(f["text"] for f in deltas)
    CHECKS.expect(len(joined) >= 6 and bool(done) and joined == done[0]["answer"],
                  "delta 拼起来 = done 帧里的完整回答（流没有丢字）")
    CHECKS.expect(bool(done) and (done[0].get("usage") or {}).get("total_tokens", 0) > 0,
                  "收尾帧带 usage（token 账在这一帧交给前端，接 11d 的成本账单）")
    print("\n  生产化清单：换 POST + 鉴权、工具调用事件（stream_mode='messages' 也会吐 ToolMessage）、"
          "客户端断开时中止生成、把 /chat 换成你的前端框架。")


def serve() -> None:
    import uvicorn

    print("  打开：http://127.0.0.1:8765/chat?q=你们周六几点关门   （Ctrl+C 停止）")
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="warning")


if __name__ == "__main__":
    if "--serve" in sys.argv:
        serve()
    else:
        run_selftest()
        sys.exit(CHECKS.report())
