#!/usr/bin/env python3
from pathlib import Path
import argparse
import shutil


README_TEMPLATE = """# RedBook Knowledge Base

这个目录用于沉淀小红书运营里的结构化结论，而不是堆聊天记录。

## 目录结构

```text
redbook-knowledge-base/
  README.md
  accounts/
  topics/
  patterns/
  actions/
  reviews/
```

## 使用规则

- 任务前先读本文件，再检索最近同类记录。
- 任务后至少补一条结构化记录。
- 每条记录最少包含：结论、证据、可复用点、风险、下一步。

## 当前重点

- 暂无。可随着项目推进持续更新。
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="project root to initialize")
    parser.add_argument(
        "--with-persona",
        action="store_true",
        help="copy bundled persona.md into the target root when missing",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    kb_root = root / "redbook-knowledge-base"
    kb_root.mkdir(parents=True, exist_ok=True)

    for name in ["accounts", "topics", "patterns", "actions", "reviews"]:
        (kb_root / name).mkdir(exist_ok=True)

    readme = kb_root / "README.md"
    if not readme.exists():
        readme.write_text(README_TEMPLATE, encoding="utf-8")

    if args.with_persona:
        bundled_persona = Path(__file__).resolve().parents[1] / "persona.md"
        target_persona = root / "persona.md"
        if bundled_persona.exists() and not target_persona.exists():
            shutil.copyfile(bundled_persona, target_persona)

    print(kb_root)


if __name__ == "__main__":
    main()
