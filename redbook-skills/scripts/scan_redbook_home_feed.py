#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from redbook_browser_common import add_browser_args, dumps_pretty, launch_browser_context


HOME_FEED_EVAL = r"""
() => {
  const text = (node) => (node && node.textContent ? node.textContent.replace(/\s+/g, " ").trim() : "");
  const cards = [];
  const anchors = Array.from(document.querySelectorAll("a[href*='/explore/']"));

  for (const anchor of anchors) {
    const href = anchor.href || "";
    if (!href) continue;
    const root = anchor.closest("section, article, div") || anchor;
    const title = text(root.querySelector("img[alt], h1, h2, h3, [class*='title']")) || text(anchor);
    const author = text(root.querySelector("[class*='author'], [class*='user'], [class*='name']"));
    const summary = text(root).slice(0, 180);
    const image = root.querySelector("img");
    cards.push({
      href,
      title,
      author,
      summary,
      image: image ? (image.currentSrc || image.src || "") : "",
    });
  }

  const unique = [];
  const seen = new Set();
  for (const card of cards) {
    if (!card.href || seen.has(card.href)) continue;
    seen.add(card.href);
    unique.push(card);
  }
  return unique;
}
"""


def evaluate_cards(page):
    last_error = None
    for _ in range(3):
        try:
            page.wait_for_load_state("domcontentloaded", timeout=15000)
            return page.evaluate(HOME_FEED_EVAL)
        except Exception as exc:
            last_error = exc
            page.wait_for_timeout(1500)
    if last_error:
        raise last_error
    return []


def normalize_href(href: str) -> str:
    return href.split("?", 1)[0]


def clean_author(author: str) -> str:
    author = author.strip()
    author = re.sub(r"(粉丝|关注|赞).*?$", "", author)
    author = re.sub(r"\d+(?:\.\d+)?[万w]?$", "", author)
    return author.strip()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scan the RedBook home feed via Playwright.")
    parser.add_argument("--limit", type=int, default=20, help="max number of cards to return")
    parser.add_argument(
        "--output",
        help="optional path to save the captured feed JSON",
    )
    parser.add_argument("--screenshot", help="optional screenshot output path")
    add_browser_args(parser)
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    with launch_browser_context(
        chrome_path=args.chrome_path,
        user_data_dir=args.user_data_dir,
        profile_directory=args.profile_directory,
        headless=args.headless,
        no_copy_profile=args.no_copy_profile,
        slow_mo=args.slow_mo,
        cdp_url=args.cdp_url,
    ) as context:
        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://www.xiaohongshu.com/", wait_until="domcontentloaded", timeout=30000)
        for _ in range(5):
            page.wait_for_timeout(2500)
            page.mouse.wheel(0, 1200)
            cards = evaluate_cards(page)
            if cards:
                break
        else:
            cards = evaluate_cards(page)

        if args.screenshot:
            output_path = Path(args.screenshot).expanduser()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(output_path), full_page=True)
        normalized = []
        seen = set()
        for card in cards:
            href = normalize_href(card.get("href", ""))
            if not href or href in seen:
                continue
            seen.add(href)
            card["href"] = href
            card["author"] = clean_author(card.get("author", ""))
            normalized.append(card)

        cards = normalized[: args.limit]
        excerpt = page.evaluate("() => document.body.innerText.slice(0, 500)")

    payload = {"count": len(cards), "cards": cards, "page_excerpt": excerpt}
    if args.output:
        output_path = Path(args.output).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(dumps_pretty(payload), encoding="utf-8")

    sys.stdout.write(dumps_pretty(payload) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
