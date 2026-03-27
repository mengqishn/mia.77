#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

from redbook_browser_common import add_browser_args, dumps_pretty, launch_browser_context


PROFILE_EVAL = r"""
() => {
  const text = (node) => (node && node.textContent ? node.textContent.replace(/\s+/g, " ").trim() : "");
  const firstText = (selectors) => {
    for (const selector of selectors) {
      const el = document.querySelector(selector);
      const value = text(el);
      if (value) return value;
    }
    return "";
  };

  const notes = [];
  const cards = Array.from(document.querySelectorAll("section.note-item"));
  for (const card of cards) {
    const visibleAnchor = card.querySelector("a.cover[href*='/user/profile/'], a.mask[href*='/user/profile/']");
    const hiddenAnchor = card.querySelector("a[href*='/explore/']");
    const anchor = visibleAnchor || hiddenAnchor;
    const href = anchor ? (anchor.href || anchor.getAttribute("href") || "") : "";
    if (!href) continue;
    const root = card.closest("section, article, div") || card;
    const title = text(root.querySelector("img[alt], h1, h2, h3, [class*='title']")) || text(anchor);
    const summary = text(root).slice(0, 180);
    notes.push({ href, title, summary });
  }

  return {
    account_name: firstText([
      "h1",
      "[class*='user-name']",
      "[class*='username']",
      "[class*='name']"
    ]),
    note_count_hint: firstText([
      "[class*='note']",
      "[class*='tab']",
      "[class*='count']"
    ]),
    notes,
    page_excerpt: text(document.body).slice(0, 500),
    current_url: location.href,
    page_title: document.title
  };
}
"""


def normalize_note_url(href: str) -> str:
    href = (href or "").strip()
    if not href:
        return ""
    href = urljoin("https://www.xiaohongshu.com", href)
    href = href.split("#", 1)[0]
    return href


def note_id_from_url(url: str) -> str:
    match = re.search(r"/explore/([^/?]+)", url) or re.search(r"/user/profile/[^/]+/([^/?]+)", url)
    return match.group(1) if match else ""


def clean_account_name(value: str) -> str:
    value = (value or "").strip()
    value = re.sub(r"(关注|粉丝|获赞与收藏).*?$", "", value)
    return value.strip()


def dedupe_notes(notes: list[dict]) -> list[dict]:
    unique = []
    seen = set()
    for note in notes:
        href = normalize_note_url(note.get("href", ""))
        note_id = note_id_from_url(href)
        key = note_id or href
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(
            {
                "note_id": note_id,
                "url": href,
                "title": (note.get("title") or "").strip(),
                "summary": (note.get("summary") or "").strip(),
            }
        )
    return unique


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect note URLs from a RedBook profile page.")
    parser.add_argument("--profile-url", required=True, help="target RedBook profile URL")
    parser.add_argument("--limit", type=int, default=0, help="optional max notes to keep; 0 means no limit")
    parser.add_argument("--max-scrolls", type=int, default=60, help="max scroll rounds")
    parser.add_argument("--idle-rounds", type=int, default=4, help="stop after N rounds with no new notes")
    parser.add_argument("--output-json", help="optional JSON output path")
    parser.add_argument("--output-urls", help="optional text file path with one note URL per line")
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
        page.goto(args.profile_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2500)

        best_payload = None
        last_count = 0
        idle_rounds = 0

        for _ in range(args.max_scrolls):
            page.wait_for_timeout(1800)
            payload = page.evaluate(PROFILE_EVAL)
            notes = dedupe_notes(payload.get("notes") or [])
            payload["notes"] = notes
            count = len(notes)
            if best_payload is None or count > len(best_payload.get("notes") or []):
                best_payload = payload

            if count > last_count:
                idle_rounds = 0
                last_count = count
            else:
                idle_rounds += 1

            if args.limit and count >= args.limit:
                break
            if idle_rounds >= args.idle_rounds:
                break

            page.mouse.wheel(0, 2400)

        if best_payload is None:
            best_payload = page.evaluate(PROFILE_EVAL)
            best_payload["notes"] = dedupe_notes(best_payload.get("notes") or [])

        if args.limit:
            best_payload["notes"] = best_payload["notes"][: args.limit]

        best_payload["account_name"] = clean_account_name(best_payload.get("account_name") or "")
        best_payload["profile_url"] = args.profile_url
        best_payload["count"] = len(best_payload.get("notes") or [])

        if args.screenshot:
            screenshot_path = Path(args.screenshot).expanduser()
            screenshot_path.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(screenshot_path), full_page=True)
            best_payload["screenshot"] = str(screenshot_path)

    if args.output_json:
        output_path = Path(args.output_json).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(dumps_pretty(best_payload), encoding="utf-8")

    if args.output_urls:
        output_path = Path(args.output_urls).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        urls = [note["url"] for note in best_payload.get("notes") or [] if note.get("url")]
        output_path.write_text("\n".join(urls) + ("\n" if urls else ""), encoding="utf-8")

    sys.stdout.write(dumps_pretty(best_payload) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
