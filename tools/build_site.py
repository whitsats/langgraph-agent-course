"""把散在仓库各处的文档拼进一个临时目录，供 mkdocs 构建。

为什么需要这一步：MkDocs 只能有一个 docs_dir，而这三处内容天然分居三个地方 ——
讲义在 `tutorial/`、学习计划在仓库根目录、示例索引在 `examples/`。

两种做法里选了后者：

  ✗ 把三份文件复制进仓库（比如 `docs/`）再提交 —— 于是仓库里同时存在两份教材，
    改一处忘一处，迟早不一致（这个仓库刚因为"两套编号"栽过一次）。
  ✓ 构建时临时拼装（本脚本）—— 仓库里始终只有一份原文，站点是它的产物。

用法（三步，本脚本是第一步）：

    uv run python tools/build_site.py                                  # 生成 site-src/
    uvx --with-requirements requirements-docs.txt zensical serve       # 本地预览，默认 8000 端口
    uvx --with-requirements requirements-docs.txt zensical build       # 只构建，产出 site-out/

Zensical 走 uvx 隔离运行 —— 它是 CLI 工具而非本项目的库依赖，不必碰根目录的 .venv。
`site-src/` 与 `site-out/` 都已进 .gitignore。CI 在推送到 main 时做同样的事
并部署到 GitHub Pages，见 `.github/workflows/docs.yml`。

⚠️ 输出目录名不能以点开头：Zensical 会跳过隐藏目录，结果是构建“成功”、
   产出 0 页、且不报任何警告（实测踩过）。写法详见 zensical.toml 顶部注释。
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from _console import setup_console  # noqa: E402  （同目录的兄弟模块）

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site-src"
ASSETS_SRC = ROOT / "site-assets"

# 单独搬运、且要改名的页面：(源文件, 站点里的文件名)
EXTRA_PAGES = [
    (ROOT / "tutorial" / "README.md", "index.md"),
    (ROOT / "LEARNING_PLAN.md", "learning-plan.md"),
    (ROOT / "examples" / "README.md", "examples.md"),
]

# 拼装之后相对位置变了，这些链接必须跟着改（只改副本，源文件不动）
REWRITES = [
    ("](../tutorial/README.md)", "](index.md)"),
    ("](../LEARNING_PLAN.md)", "](learning-plan.md)"),
    # 讲义里把首页写作 README.md，拼装后它叫 index.md
    ("](README.md)", "](index.md)"),
]


def main() -> int:
    setup_console()

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    # 全部讲义章（00–18 由 glob 自动收，新增章不用改这里）：
    # 文件名原样搬过去，正文里的互链（NN-标题.md）就不用改了
    chapters = sorted(p for p in (ROOT / "tutorial").glob("*.md") if p.name != "README.md")
    if not chapters:
        print("✗ 没找到 tutorial/*.md", file=sys.stderr)
        return 1
    for src in chapters:
        shutil.copy2(src, OUT / src.name)

    for src, name in EXTRA_PAGES:
        if not src.exists():
            print(f"✗ 缺少源文件：{src.relative_to(ROOT)}", file=sys.stderr)
            return 1
        shutil.copy2(src, OUT / name)

    # 站点素材（logo / favicon / 分享预览图）也必须位于 docs_dir 内部，
    # 所以同样复制一份。源文件是 site-assets/，其中位图由 tools/make_assets.py
    # 从 logo.svg 派生 —— 仓库里不存第二份标识定义。
    copied_assets = 0
    if ASSETS_SRC.is_dir():
        assets_dst = OUT / "assets"
        assets_dst.mkdir(parents=True, exist_ok=True)
        for item in sorted(ASSETS_SRC.iterdir()):
            if item.is_file():
                shutil.copy2(item, assets_dst / item.name)
                copied_assets += 1

    touched = 0
    for page in OUT.glob("*.md"):
        text = page.read_text(encoding="utf-8")
        new = text
        for old, repl in REWRITES:
            new = new.replace(old, repl)
        if new != text:
            page.write_text(new, encoding="utf-8")
            touched += 1

    pages = sorted(OUT.glob("*.md"))
    print(f"✓ 已生成 {OUT.relative_to(ROOT)}/：{len(pages)} 页，{copied_assets} 个站点素材，改写了 {touched} 个文件里的跨目录链接")
    print("  本地预览：uvx --with-requirements requirements-docs.txt zensical serve")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
