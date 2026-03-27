#!/usr/bin/env python3
from datetime import datetime
from pathlib import Path
import argparse
import re


VALID_TYPES = {"accounts", "topics", "patterns", "actions", "reviews"}


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "entry"


def entry_template(entry_type: str, entry_id: str) -> str:
    return f"""---
id: {entry_id}
type: {entry_type[:-1] if entry_type.endswith('s') else entry_type}
status: active
created_at: {datetime.now().astimezone().isoformat(timespec="seconds")}
source_url:
tags: []
---

# 结论

# 证据
- 

# 可复用点
- 

# 风险
- 

# 下一步
- 
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="project root")
    parser.add_argument("--type", required=True, choices=sorted(VALID_TYPES))
    parser.add_argument("--brief", required=True, help="short brief used in filename")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    kb_root = root / "redbook-knowledge-base"
    target_dir = kb_root / args.type
    target_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%d")
    brief = slugify(args.brief)
    filename = f"{date_str}-{brief}.md"
    path = target_dir / filename
    entry_id = f"{date_str}-{brief}"

    if not path.exists():
        path.write_text(entry_template(args.type, entry_id), encoding="utf-8")

    print(path)


if __name__ == "__main__":
    main()
