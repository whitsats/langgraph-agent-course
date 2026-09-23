import os

def thought_callback(step):
    """Module-level callback to ensure Pydantic serialization. ASCII-safe for Windows GBK."""
    if os.getenv("STREAM_THOUGHTS", "false").lower() == "true":
        print(f"[AI THOUGHT]: {step}", flush=True)
