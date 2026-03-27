#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Optional

from redbook_browser_common import add_browser_args, dumps_pretty, launch_browser_context


NOTE_EVAL = r"""
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
  const allTexts = (selectors) => {
    const values = [];
    for (const selector of selectors) {
      document.querySelectorAll(selector).forEach((el) => {
        const value = text(el);
        if (value) values.push(value);
      });
    }
    return [...new Set(values)];
  };
  const normalizeNumber = (value) => {
    if (!value) return "";
    return value.replace(/\s+/g, "");
  };
  const numberAfterKeyword = (keyword) => {
    const nodes = Array.from(document.querySelectorAll("button, span, div"));
    for (const node of nodes) {
      const value = text(node);
      if (!value) continue;
      if (value === keyword) continue;
      if (value.includes(keyword)) {
        const cleaned = value.replace(keyword, "").trim();
        if (cleaned) return normalizeNumber(cleaned);
      }
    }
    return "";
  };
  const commentTotal = () => {
    const value = firstText([
      ".comments-container .total",
      ".comments-el .total",
      ".total"
    ]);
    const match = value.match(/共\s*([0-9]+(?:\.[0-9]+)?(?:万|w)?)\s*条评论/);
    return match ? match[1] : "";
  };
  const imageUrls = Array.from(document.querySelectorAll(
    ".swiper-slide img, .note-slider-img, .img-container img, .note-content img, img"
  ))
    .map((img) => img.currentSrc || img.src || "")
    .filter((src) => src && /xhscdn|xiaohongshu|sns-webpic|note/.test(src))
    .filter((src) => !/avatar|user-avatar|redmoji|emoji|badge/i.test(src));

  const bodyCandidates = allTexts([
    "#detail-desc",
    ".note-content",
    ".content",
    ".desc",
    "[class*='desc']",
    "[class*='content']"
  ]).filter((value) => value.length > 10);

  const tagCandidates = Array.from(document.querySelectorAll("a, span"))
    .map((el) => text(el))
    .filter((value) => /^#/.test(value));
  const topComments = Array.from(document.querySelectorAll(
    ".comments-container .comment-item .content, .comments-container .comment-item .note-text, .comments-el .comment-item .content, .comments-el .comment-item .note-text"
  ))
    .map((el) => text(el))
    .filter((value) => value && value.length > 1)
    .filter((value, index, arr) => arr.indexOf(value) === index)
    .slice(0, 10);

  return {
    title: firstText([
      "#detail-title",
      "h1",
      "[class*='title']",
      "[class*='Title']"
    ]),
    author: firstText([
      ".author-container a.name",
      ".author-wrapper a.name",
      ".author a.name",
      ".author-container .username",
      ".author-wrapper .username",
      "[class*='author']",
      "[class*='user'] [class*='name']",
      "a[href*='/user/profile/']"
    ]),
    body: bodyCandidates[0] || "",
    publish_time: firstText([
      "[class*='date']",
      "[class*='time']",
      "time"
    ]),
    likes: numberAfterKeyword("赞"),
    collects: numberAfterKeyword("收藏"),
    comments: commentTotal() || numberAfterKeyword("评论"),
    tags: [...new Set(tagCandidates)].slice(0, 20),
    top_comments: topComments,
    images: [...new Set(imageUrls)],
    page_text_excerpt: text(document.body).slice(0, 500)
  };
}
"""


def note_id_from_url(url: str) -> str:
    match = re.search(r"/explore/([^/?]+)", url) or re.search(r"/user/profile/[^/]+/([^/?]+)", url)
    return match.group(1) if match else "unknown-note"


def wait_for_note_page(page) -> None:
    page.wait_for_load_state("domcontentloaded", timeout=20000)
    try:
        page.wait_for_selector("h1, #detail-title, [class*='title']", timeout=15000)
    except Exception:
        page.wait_for_timeout(3000)


def clean_author(value: str) -> str:
    value = value.strip()
    value = re.sub(r"(互相关注|已关注|关注|互相|作者)+$", "", value)
    return value.strip()


def download_images(image_urls, output_dir: Path) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    saved_paths = []
    for index, url in enumerate(image_urls, start=1):
        suffix = Path(url.split("?")[0]).suffix or ".jpg"
        target = output_dir / f"{index:02d}{suffix}"
        try:
            urllib.request.urlretrieve(url, target)
            saved_paths.append(str(target))
        except Exception:
            continue
    return saved_paths


def save_metadata(output_dir: Path, metadata: dict) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "metadata.json").write_text(dumps_pretty(metadata), encoding="utf-8")
    markdown = [
        f"# {metadata.get('title') or metadata.get('note_id')}",
        "",
        f"- URL: {metadata.get('url', '')}",
        f"- Author: {metadata.get('author', '')}",
        f"- Publish Time: {metadata.get('publish_time', '')}",
        f"- Likes: {metadata.get('likes', '')}",
        f"- Collects: {metadata.get('collects', '')}",
        f"- Comments: {metadata.get('comments', '')}",
        "",
        "## Body",
        metadata.get("body", ""),
        "",
        "## Tags",
    ]
    tags = metadata.get("tags") or []
    markdown.extend([f"- {tag}" for tag in tags] or ["- "])
    markdown.extend(["", "## Images"])
    images = metadata.get("images") or []
    markdown.extend([f"- {image}" for image in images] or ["- "])
    markdown.extend(["", "## Extraction"])
    markdown.append(f"- Page Title: {metadata.get('page_title', '')}")
    markdown.append(f"- Current URL: {metadata.get('current_url', '')}")
    markdown.append(f"- Restricted: {metadata.get('restricted', False)}")
    markdown.append(f"- Logged In: {metadata.get('logged_in', False)}")
    (output_dir / "metadata.md").write_text("\n".join(markdown), encoding="utf-8")


def collect_urls_from_obj(value: Any, acc: list[str]) -> None:
    if isinstance(value, dict):
        for item in value.values():
            collect_urls_from_obj(item, acc)
        return
    if isinstance(value, list):
        for item in value:
            collect_urls_from_obj(item, acc)
        return
    if isinstance(value, str):
        if re.search(r"xhscdn|xiaohongshu|sns-webpic|note", value) and re.search(
            r"\.(?:jpg|jpeg|png|webp|avif)|imageView|format/", value, re.I
        ):
            acc.append(value)


def merge_image_urls(*groups: list[str]) -> list[str]:
    merged = []
    seen = set()
    for group in groups:
        for url in group:
            if not url:
                continue
            normalized = url.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            merged.append(normalized)
    return merged


def is_likely_note_image(url: str) -> bool:
    if not url:
        return False
    lowered = url.lower()
    if any(bad in lowered for bad in ["picasso-static.xiaohongshu.com/fe-platform", "avatar", "emoji", "badge", "icon"]):
        return False
    has_host = any(good in lowered for good in ["sns-webpic", "xhscdn.com", "sns-img", "note"])
    has_shape = any(
        token in lowered
        for token in ["1000g", "1040g", "format/", "imageview", ".jpg", ".jpeg", ".png", ".webp", ".avif", "notes_pre_post"]
    )
    return has_host and has_shape


def clean_metric_value(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    if len(value) > 24:
        return ""
    if re.fullmatch(r"[0-9]+(?:\.[0-9]+)?(?:万|w)?", value.lower()):
        return value
    return ""


def response_probe(page, note_id: str) -> dict[str, Any]:
    collected: dict[str, Any] = {
        "image_candidates": [],
        "json_hits": [],
        "logged_in": None,
    }

    def handle_response(resp):
        try:
            content_type = resp.headers.get("content-type", "")
            if "json" not in content_type:
                return
            body = resp.text()
            if '"msg":"无登录信息' in body or '"code":-101' in body:
                collected["logged_in"] = False
            try:
                payload = json.loads(body)
            except Exception:
                return

            urls: list[str] = []
            collect_urls_from_obj(payload, urls)
            if urls:
                collected["image_candidates"].extend(urls)

            serialized = body[:2500]
            if note_id in body or any(key in body for key in ["note_card", "display_title", "image_list", "imageList"]):
                collected["json_hits"].append({"url": resp.url, "body": serialized})
        except BaseException:
            return

    page.on("response", handle_response)
    collected["_handler"] = handle_response
    return collected


def extract_note_once(
    url: str,
    chrome_path: str,
    user_data_dir: str,
    profile_directory: str,
    headless: bool,
    no_copy_profile: bool,
    slow_mo: int = 0,
    screenshot: Optional[str] = None,
    cdp_url: Optional[str] = None,
) -> dict[str, Any]:
    note_id = note_id_from_url(url)

    with launch_browser_context(
        chrome_path=chrome_path,
        user_data_dir=user_data_dir,
        profile_directory=profile_directory,
        headless=headless,
        no_copy_profile=no_copy_profile,
        slow_mo=slow_mo,
        cdp_url=cdp_url,
    ) as context:
        page = context.pages[0] if context.pages else context.new_page()
        probe = response_probe(page, note_id)
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            wait_for_note_page(page)
            metadata = page.evaluate(NOTE_EVAL)
            metadata["url"] = url
            metadata["note_id"] = note_id
            metadata["current_url"] = page.url
            metadata["page_title"] = page.title()
            metadata["title"] = metadata.get("title") or note_id
            metadata["author"] = clean_author(metadata.get("author") or "")
            metadata["likes"] = clean_metric_value(metadata.get("likes") or "")
            metadata["collects"] = clean_metric_value(metadata.get("collects") or "")
            metadata["comments"] = clean_metric_value(metadata.get("comments") or "")
            metadata["images"] = merge_image_urls(
                metadata.get("images") or [],
                probe.get("image_candidates") or [],
            )
            metadata["all_images"] = metadata["images"][:]
            metadata["images"] = [url for url in metadata["images"] if is_likely_note_image(url)]
            body_text = metadata.get("page_text_excerpt") or ""
            current_url = metadata.get("current_url") or ""
            page_title = metadata.get("page_title") or ""
            restricted = (
                "安全限制" in page_title
                or "IP存在风险" in body_text
                or current_url.rstrip("/") == "https://www.xiaohongshu.com/explore"
            )
            metadata["restricted"] = restricted
            logged_in = probe.get("logged_in")
            if logged_in is None and any(token in body_text for token in ["我马上登录即可", "登录后", "登录即可", "马上登录"]):
                logged_in = False
            metadata["logged_in"] = logged_in
            metadata["json_hits"] = probe.get("json_hits") or []

            if screenshot:
                screenshot_path = Path(screenshot).expanduser()
                screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(screenshot_path), full_page=True)
                metadata["screenshot"] = str(screenshot_path)
        finally:
            handler = probe.get("_handler")
            if handler is not None:
                try:
                    page.remove_listener("response", handler)
                except Exception:
                    pass

    return metadata


def extraction_score(metadata: dict[str, Any]) -> int:
    score = 0
    if metadata.get("title"):
        score += 5
    if metadata.get("body"):
        score += 10
    if not metadata.get("restricted"):
        score += 10
    score += min(len(metadata.get("images") or []), 20) * 4
    if metadata.get("logged_in") is True:
        score += 10
    if metadata.get("current_url") == metadata.get("url"):
        score += 5
    return score


def extract_note(
    url: str,
    chrome_path: str,
    user_data_dir: str,
    profile_directory: str,
    headless: bool,
    no_copy_profile: bool,
    slow_mo: int = 0,
    screenshot: Optional[str] = None,
    attempts: int = 5,
    retry_sleep_seconds: float = 1.0,
    cdp_url: Optional[str] = None,
) -> dict[str, Any]:
    best: Optional[dict[str, Any]] = None
    histories = []

    for attempt in range(1, attempts + 1):
        run_screenshot = screenshot
        if screenshot and attempts > 1:
            shot_path = Path(screenshot).expanduser()
            run_screenshot = str(shot_path.with_name(f"{shot_path.stem}-attempt-{attempt}{shot_path.suffix}"))
        current = extract_note_once(
            url=url,
            chrome_path=chrome_path,
            user_data_dir=user_data_dir,
            profile_directory=profile_directory,
            headless=headless,
            no_copy_profile=no_copy_profile,
            slow_mo=slow_mo,
            screenshot=run_screenshot,
            cdp_url=cdp_url,
        )
        current["attempt"] = attempt
        current["score"] = extraction_score(current)
        histories.append(
            {
                "attempt": attempt,
                "restricted": current.get("restricted"),
                "logged_in": current.get("logged_in"),
                "image_count": len(current.get("images") or []),
                "current_url": current.get("current_url"),
                "score": current["score"],
            }
        )

        if best is None or current["score"] > best.get("score", -1):
            best = current

        if current["images"] and not current.get("restricted"):
            best = current
            break

        if attempt < attempts:
            time.sleep(retry_sleep_seconds)

    assert best is not None
    best["attempt_history"] = histories
    return best


def persist_note_artifacts(output_dir: Path, metadata: dict[str, Any], download_image_files: bool) -> dict[str, Any]:
    save_metadata(output_dir, metadata)
    if download_image_files:
        metadata["downloaded_images"] = download_images(metadata.get("images") or [], output_dir / "images")
        save_metadata(output_dir, metadata)
    return metadata


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract a RedBook/Xiaohongshu note via Playwright.")
    parser.add_argument("--url", required=True, help="target note URL")
    parser.add_argument("--output-dir", help="write metadata and optional images into this directory")
    parser.add_argument("--download-images", action="store_true", help="download extracted images")
    parser.add_argument("--screenshot", help="optional screenshot output path")
    add_browser_args(parser)
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    metadata = extract_note(
        url=args.url,
        chrome_path=args.chrome_path,
        user_data_dir=args.user_data_dir,
        profile_directory=args.profile_directory,
        headless=args.headless,
        no_copy_profile=args.no_copy_profile,
        slow_mo=args.slow_mo,
        screenshot=args.screenshot,
        cdp_url=args.cdp_url,
    )

    if args.output_dir:
        output_dir = Path(args.output_dir).expanduser()
        metadata = persist_note_artifacts(output_dir, metadata, args.download_images)

    sys.stdout.write(dumps_pretty(metadata) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
