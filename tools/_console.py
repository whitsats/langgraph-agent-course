"""仓库根目录下 tools/ 里几个脚本共用的控制台处理。

Windows 默认代码页是 GBK，打印 ✓ / ✅ 这类字符会直接让脚本死于
`UnicodeEncodeError: 'gbk' codec can't encode character ...`，
而报错位置往往离真正的工作很远，很容易被误判成“上一步失败了”。

examples/_shared.py 里有同一段处理（那边是为了让例子能打印 emoji），
这里再留一份是为了让 tools/ 下的脚本只依赖标准库、不反向依赖 examples/。
这份绕行代码在本仓库已经踩到三次了，所以集中到这里，别再复制第四份。
"""

from __future__ import annotations

import sys


def setup_console() -> None:
    """尽力把 stdout/stderr 切到 UTF-8；切不动也不影响逻辑。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass
