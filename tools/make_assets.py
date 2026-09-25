"""从 site-assets/logo.svg 派生出全部位图素材。

标识本身只在 `site-assets/logo.svg` 里定义一次，本脚本把它光栅化、合成到靛蓝底上、
再配文字。这样改标识只需改那一处，不必在几份文件里各改一遍。

产出（都提交进仓库，构建时不重新生成）：

    site-assets/favicon.ico           16 / 32 / 48 三个尺寸，浏览器自己挑
    site-assets/apple-touch-icon.png  180×180，iOS 加到主屏时用
    site-assets/og-image.png          1200×630，链接分享出去的预览图

为什么素材要提交进仓库、而不是构建时生成：CI 里没必要为了一个图标多装
resvg-py 与 Pillow，也不必依赖「runner 上正好有合适的中文字体」。改标识时
手动跑一次本脚本即可。

用法（本机跑，不进 CI）：

    uvx --with resvg-py --with pillow python tools/make_assets.py

注意：og-image 上要写中文，所以本机得有中文字体。Windows 用微软雅黑，
macOS 用苹方，Linux 找 Noto CJK；都找不到会直接报错并告诉你怎么装。
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import resvg_py
from PIL import Image, ImageDraw, ImageFont

from _console import setup_console  # noqa: E402  （同目录的兄弟模块）

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "site-assets"
LOGO = ASSETS / "logo.svg"

# 与 zensical.toml 里 palette 的 primary 一致，确切值是 #4051b5 ——
# 不是 Material 文档里常见的 #3f51b5。实测顶栏 background 为 rgb(64, 81, 181)，
# 两者差 1/255，肉眼看不出来，但既然要说“和顶栏同色”就对齐真的那个。
# favicon 必须自带底色：标识是白色的，放在透明底上，
# 浏览器在浅色标签栏里就完全看不见了。
INDIGO = (64, 81, 181)          # #4051b5
INDIGO_DARK = (40, 50, 124)     # #28327c
INDIGO_TEXT = (197, 202, 233)   # #c5cae9
INDIGO_FAINT = (159, 168, 218)  # #9fa8da

# 渲染标识时的超采样倍数：先在 4 倍尺寸下画，再 LANCZOS 缩下来，
# 比让光栅化器直接在小尺寸下抗锯齿更干净（16px 那个尤其明显）。
SUPERSAMPLE = 4


def _find_fonts() -> tuple[str, str]:
    """返回 (粗体, 常规) 的中文字体路径。"""
    candidates = [
        (r"C:\Windows\Fonts\msyhbd.ttc", r"C:\Windows\Fonts\msyh.ttc"),
        ("/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/PingFang.ttc"),
        (
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        ),
    ]
    for bold, regular in candidates:
        if Path(bold).exists() and Path(regular).exists():
            return bold, regular
    raise SystemExit(
        "✗ 找不到中文字体。og-image.png 上要写中文，装一个 CJK 字体即可，"
        "例如 Debian/Ubuntu 上：apt-get install fonts-noto-cjk"
    )


def render_mark(size: int) -> Image.Image:
    """把 logo.svg 渲染成 size×size 的 RGBA 图（白色标识 + 透明底）。"""
    px = size * SUPERSAMPLE
    png = resvg_py.svg_to_bytes(
        svg_string=LOGO.read_text(encoding="utf-8"), width=px, height=px
    )
    img = Image.open(io.BytesIO(png)).convert("RGBA")
    return img.resize((size, size), Image.LANCZOS)


def tile_image(size: int, mark_ratio: float = 0.72) -> Image.Image:
    """靛蓝圆角方块 + 居中的白色标识 —— favicon / touch icon 的样式。"""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    radius = max(2, round(size * 0.22))
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=INDIGO)

    inner = max(8, round(size * mark_ratio))
    mark = render_mark(inner)
    off = (size - inner) // 2
    img.alpha_composite(mark, (off, off))
    return img


def gradient_background(w: int, h: int) -> Image.Image:
    """自上而下的靛蓝渐变，比纯色平一些、也更像“有设计过”。"""
    base = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / max(1, h - 1)
        base.putpixel(
            (0, y),
            tuple(round(a + (b - a) * t) for a, b in zip(INDIGO, INDIGO_DARK)),
        )
    return base.resize((w, h), Image.BILINEAR)


def build_og_image(bold_path: str, regular_path: str) -> Image.Image:
    img = gradient_background(1200, 630).convert("RGBA")

    # 左侧标识
    mark = render_mark(120)
    img.alpha_composite(mark, (100, 80))

    draw = ImageDraw.Draw(img)
    # 字号的选取依据是「缩小后还能不能读」，不是「图上好不好看」：
    # 分享预览一般只渲染 500~600px 宽，这里的 36px 缩到 0.45 倍约剩 16px，
    # 尚可辨认；26px 縮到 11px 就成糊了。最宽的一行仍远在 1200 内。
    f_big = ImageFont.truetype(bold_path, 68)
    f_mid = ImageFont.truetype(regular_path, 36)
    f_small = ImageFont.truetype(regular_path, 30)

    draw.text((100, 310), "LangChain + LangGraph", font=f_big, fill=(255, 255, 255), anchor="ls")
    draw.text((100, 390), "智能体开发教程", font=f_big, fill=(255, 255, 255), anchor="ls")
    draw.text(
        (100, 478),
        "写给有编程经验、但没做过智能体的人",
        font=f_mid,
        fill=INDIGO_TEXT,
        anchor="ls",
    )
    draw.text(
        (100, 556),
        "20 章讲义 · 22 个可直接运行的示例 · 一半离线可跑（不需要 Key）",
        font=f_small,
        fill=INDIGO_FAINT,
        anchor="ls",
    )
    return img


def main() -> int:
    setup_console()

    if not LOGO.exists():
        print(f"✗ 找不到 {LOGO.relative_to(ROOT)}", file=sys.stderr)
        return 1
    bold_path, regular_path = _find_fonts()

    # favicon：多尺寸 ICO，让浏览器按自己的场景挑，别只给一个尺寸硬缩。
    #
    # 注意 Pillow 的限制：ICO 写入器只接受**一张**源图，再自己重采样出
    # sizes 里请求的各个尺寸，不能逐尺寸喂不同的图（所以不要在这里循环
    # tile_image(s) —— 那些 tile 会被丢弃，只有最后一张进文件）。
    # 对策是直接把源图放大到最大尺寸的 4 倍（下同 SUPERSAMPLE 的思路），
    # 三个帧就都是从同一份矢量数据降采样得到的，比从 48 往下缩干净。
    ico_sizes = (16, 32, 48)
    tile_image(max(ico_sizes) * SUPERSAMPLE).save(
        ASSETS / "favicon.ico", format="ICO",
        sizes=[(s, s) for s in ico_sizes],
    )

    tile_image(180).save(ASSETS / "apple-touch-icon.png", format="PNG",
                         optimize=True)

    og = build_og_image(bold_path, regular_path)
    og.convert("RGB").save(ASSETS / "og-image.png", format="PNG", optimize=True)

    for name in ("favicon.ico", "apple-touch-icon.png", "og-image.png"):
        p = ASSETS / name
        print(f"  ✓ {name:24} {p.stat().st_size:>7} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
