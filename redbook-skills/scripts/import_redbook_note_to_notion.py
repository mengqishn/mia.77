#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Optional

from extract_redbook_note import extract_note, persist_note_artifacts
from redbook_browser_common import add_browser_args, dumps_pretty


NOTION_VERSION = "2022-06-28"


def notion_request(token: str, method: str, path: str, payload=None):
    url = f"https://api.notion.com/v1{path}"
    data = None
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    last_error = None
    for attempt in range(1, 4):
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request) as response:
                body = response.read().decode("utf-8")
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            if exc.code >= 500 and attempt < 3:
                last_error = RuntimeError(f"Notion API {exc.code} for {path}: {body}")
                time.sleep(1.0 * attempt)
                continue
            raise RuntimeError(f"Notion API {exc.code} for {path}: {body}") from exc
        except urllib.error.URLError as exc:
            last_error = exc
            if attempt < 3:
                time.sleep(1.0 * attempt)
                continue
            raise RuntimeError(f"Notion API network error for {path}: {exc}") from exc
    if last_error:
        raise RuntimeError(f"Notion API request failed for {path}: {last_error}")


def query_page_by_url(token: str, database_id: str, target_url: str) -> Optional[dict[str, Any]]:
    payload = {
        "filter": {
            "property": "链接",
            "url": {
                "equals": target_url,
            },
        },
        "page_size": 1,
    }
    response = notion_request(token, "POST", f"/databases/{database_id}/query", payload)
    results = response.get("results") or []
    return results[0] if results else None


def get_database_property_names(token: str, database_id: str) -> set[str]:
    response = notion_request(token, "GET", f"/databases/{database_id}")
    return set((response.get("properties") or {}).keys())


def plain_rich_text(value: str) -> list[dict[str, Any]]:
    if not value:
        return []
    chunks = []
    remaining = value
    while remaining:
        chunk = remaining[:1800]
        chunks.append({"type": "text", "text": {"content": chunk}})
        remaining = remaining[1800:]
    return chunks


def normalize_number(value: str) -> Optional[float]:
    if not value:
        return None
    cleaned = value.strip().lower().replace(",", "")
    multiplier = 1.0
    if cleaned.endswith("w"):
        multiplier = 10000.0
        cleaned = cleaned[:-1]
    if cleaned.endswith("万"):
        multiplier = 10000.0
        cleaned = cleaned[:-1]
    try:
        return float(cleaned) * multiplier
    except ValueError:
        return None


def infer_tags(metadata: dict[str, Any]) -> list[str]:
    text = " ".join(
        [
            metadata.get("title") or "",
            metadata.get("body") or "",
            " ".join(metadata.get("tags") or []),
        ]
    ).lower()
    inferred = []
    patterns = [
        ("教程", ["教程", "手把手", "入门", "速通"]),
        ("清单", ["清单", "合集", "汇总"]),
        ("资源型", ["资料", "教程", "知识库", "分享"]),
        ("标题钩子", ["逼自己", "一定要", "建议", "为什么"]),
        ("评论驱动", ["评论", "留言", "告诉我"]),
        ("情绪价值", ["治愈", "可爱", "崩溃", "惊艳"]),
        ("对比", ["vs", "对比", "差别"]),
    ]
    for label, keywords in patterns:
        if any(keyword in text for keyword in keywords):
            inferred.append(label)
    return inferred[:5]


def split_sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text or "").strip()
    if not normalized:
        return []
    parts = re.split(r"[。.!！?？]+", normalized)
    return [part.strip(" .") for part in parts if part.strip(" .")]


def infer_audience(metadata: dict[str, Any]) -> str:
    text = " ".join([metadata.get("title") or "", metadata.get("body") or "", " ".join(metadata.get("tags") or [])])
    hints = []
    if any(token in text for token in ["编程小白", "0基础", "入门"]):
        hints.append("AI/编程入门人群")
    if any(token in text.lower() for token in ["产品经理", "ai产品经理"]):
        hints.append("想转 AI 产品经理的人")
    if any(token in text for token in ["飞书", "钉钉", "本地开发", "云服务器", "Linux"]):
        hints.append("想落地部署 AI 助手的实操型用户")
    return "；".join(hints[:3])


def infer_pain_point(metadata: dict[str, Any]) -> str:
    text = " ".join([metadata.get("title") or "", metadata.get("body") or ""])
    pains = []
    if any(token in text for token in ["编程小白", "0基础", "入门"]):
        pains.append("不会从零部署 AI 工具")
    if any(token in text for token in ["节省token", "token"]):
        pains.append("不清楚如何控制 token 成本")
    if any(token in text for token in ["飞书", "钉钉", "imessage"]):
        pains.append("不知道怎么把 AI 工具接进日常工作流")
    if any(token in text for token in ["本地开发", "云服务器", "Linux"]):
        pains.append("缺少跨环境部署指引")
    return "；".join(pains[:4])


def build_title_template(title: str) -> str:
    title = (title or "").strip()
    parts = []
    if re.search(r"[0-9]+页", title):
        parts.append("数字资料量")
    if title.startswith("逼自己"):
        parts.append("自我驱动开头")
    if any(token in title for token in ["就很", "就会", "直接", "起飞", "牛"]):
        parts.append("结果承诺收尾")
    if "OpenClaw" in title:
        parts.append("工具名直给")
    if parts:
        return " + ".join(parts)
    return "主题词直给 + 学习收益承诺"


def build_cover_template(metadata: dict[str, Any]) -> str:
    image_count = len(metadata.get("downloaded_images") or metadata.get("images") or [])
    hints = []
    if image_count >= 8:
        hints.append("多页轮播资料型封面")
    elif image_count >= 2:
        hints.append("轮播图文封面")
    else:
        hints.append("单图封面")
    if re.search(r"[0-9]+页", metadata.get("title") or ""):
        hints.append("封面突出资料规模")
    if any(token in (metadata.get("body") or "") for token in ["教程", "手把手", "速通"]):
        hints.append("教程/实操感强")
    return "；".join(hints)


def build_body_structure(metadata: dict[str, Any]) -> str:
    sentences = split_sentences(metadata.get("body") or "")
    if not sentences:
        return ""
    structure = []
    first = sentences[0]
    if any(token in first for token in ["专为", "适合", "打造"]):
        structure.append("先点名适合谁")
    if any(token in (metadata.get("body") or "") for token in ["覆盖", "全场景", "附赠"]):
        structure.append("再讲覆盖范围和交付物")
    if any(token in (metadata.get("body") or "") for token in ["速通", "快速上手", "十分钟", "一小时"]):
        structure.append("再给上手速度/收益")
    if any(token in (metadata.get("body") or "") for token in ["我实测", "从零开始"]):
        structure.append("最后用实测背书降低门槛")
    return " -> ".join(structure) or "人群定位 -> 价值承诺 -> 实测背书"


def build_interaction_mechanism(metadata: dict[str, Any]) -> str:
    comments = metadata.get("top_comments") or []
    joined = " ".join(comments)
    signals = []
    if any(token in joined for token in ["求分享", "求资料", "三连求分享", "点赞求分享"]):
        signals.append("评论区以索取资料/求分享为主")
    if normalize_number(metadata.get("comments") or ""):
        signals.append("资源承诺能拉高评论意愿")
    if not signals and comments:
        signals.append("评论区以要链接/要资料类需求为主")
    return "；".join(signals)


def build_comment_keywords(metadata: dict[str, Any]) -> str:
    comments = metadata.get("top_comments") or []
    keywords = []
    joined = " ".join(comments)
    for token in ["求分享", "求资料", "三连", "点赞求分享", "好嘞", "注意查收"]:
        if token in joined:
            keywords.append(token)
    if not keywords:
        keywords.extend(metadata.get("tags") or [])
    return " ".join(keywords[:12])


def build_learning_conclusion(metadata: dict[str, Any]) -> str:
    points = []
    title = metadata.get("title") or ""
    if title:
        points.append(f"这篇笔记的标题打法是「{build_title_template(title)}」，先把学习收益说满。")
    body_structure = build_body_structure(metadata)
    if body_structure:
        points.append(f"正文推进基本是「{body_structure}」，信息组织偏资料整理型。")
    interaction = build_interaction_mechanism(metadata)
    if interaction:
        points.append(f"评论触发点上，{interaction}。")
    if len(metadata.get("downloaded_images") or metadata.get("images") or []) >= 8:
        points.append("多页轮播强化了“资料很多、值得收藏”的第一感受，这是这篇内容的重要爆点。")
    if metadata.get("likes") or metadata.get("collects"):
        points.append("如果要学习这篇，不是学具体措辞，而是学它怎样把资料量、上手门槛和结果预期一起打包成保存理由。")
    else:
        points.append("如果要学习这篇，优先拆标题承诺、封面量感和正文信息层级，不直接照抄原文。")
    return " ".join(points)


def material_properties(metadata: dict[str, Any], local_dir: Path) -> dict[str, Any]:
    tags = infer_tags(metadata)
    body = metadata.get("body") or ""
    title_template = build_title_template(metadata.get("title") or "")
    cover_template = build_cover_template(metadata)
    body_structure = build_body_structure(metadata)
    interaction = build_interaction_mechanism(metadata)
    reusable = build_learning_conclusion(metadata)

    risk = [
        "当前为自动提取+规则总结，建议人工复核封面层级和互动机制后再拿去复刻。",
    ]
    if metadata.get("restricted"):
        risk.append("本次命中平台安全限制或跳转，结果可能来自缓存/部分页面，不适合直接判断爆款强度。")
    if metadata.get("logged_in") is False:
        risk.append("当前浏览器会话未携带有效登录态，部分字段可能缺失。")
    if not metadata.get("likes") and not metadata.get("collects") and not metadata.get("comments"):
        risk.append("本次未稳定抓到互动数据，暂不据此判断爆款强度。")

    status_name = "已提炼"
    if metadata.get("restricted"):
        status_name = "待拆解"

    return {
        "素材名称": {
            "title": plain_rich_text(metadata.get("title") or metadata.get("note_id") or "未命名素材")
        },
        "原笔记标题": {"rich_text": plain_rich_text(metadata.get("title") or "")},
        "链接": {"url": metadata.get("url") or ""},
        "作者": {"rich_text": plain_rich_text(metadata.get("author") or "")},
        "状态": {"select": {"name": status_name}},
        "点赞": {"number": normalize_number(metadata.get("likes") or "")},
        "收藏": {"number": normalize_number(metadata.get("collects") or "")},
        "评论": {"number": normalize_number(metadata.get("comments") or "")},
        "目标人群": {"rich_text": plain_rich_text(infer_audience(metadata))},
        "核心痛点": {"rich_text": plain_rich_text(infer_pain_point(metadata))},
        "标题模板": {"rich_text": plain_rich_text(title_template)},
        "封面模板": {"rich_text": plain_rich_text(cover_template)},
        "正文结构": {"rich_text": plain_rich_text(body_structure or body[:1800])},
        "互动机制": {"rich_text": plain_rich_text(interaction)},
        "评论关键词": {"rich_text": plain_rich_text(build_comment_keywords(metadata))},
        "可复用结论": {"rich_text": plain_rich_text(reusable)},
        "风险边界": {"rich_text": plain_rich_text(" ".join(risk))},
        "标签": {"multi_select": [{"name": tag} for tag in tags]},
    }


def build_children(metadata: dict[str, Any], local_dir: Path) -> list[dict[str, Any]]:
    downloaded = metadata.get("downloaded_images") or []
    image_lines = downloaded if downloaded else metadata.get("images") or []
    bullets = [
        f"来源链接：{metadata.get('url', '')}",
        f"笔记 ID：{metadata.get('note_id', '')}",
        f"本地目录：{local_dir}",
        f"metadata.json：{local_dir / 'metadata.json'}",
        f"metadata.md：{local_dir / 'metadata.md'}",
        f"当前页面标题：{metadata.get('page_title', '')}",
        f"当前页面 URL：{metadata.get('current_url', '')}",
        f"restricted：{metadata.get('restricted', False)}",
        f"logged_in：{metadata.get('logged_in')}",
    ]
    if downloaded:
        bullets.append(f"图片目录：{local_dir / 'images'}")
    else:
        bullets.append("本次未落到图片文件，可能是页面未返回可下载图片。")

    blocks: list[dict[str, Any]] = []
    for line in bullets:
        blocks.append(
            {
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": plain_rich_text(line)},
            }
        )

    blocks.append(
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": plain_rich_text("正文摘录")},
        }
    )
    blocks.append(
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": plain_rich_text((metadata.get("body") or "")[:1800] or "未提取到正文")},
        }
    )

    if image_lines:
        blocks.append(
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": plain_rich_text("图片资源")},
            }
        )
        for line in image_lines[:20]:
            blocks.append(
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {"rich_text": plain_rich_text(str(line))},
                }
            )
    json_hits = metadata.get("json_hits") or []
    if json_hits:
        blocks.append(
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": plain_rich_text("接口命中摘要")},
            }
        )
        for hit in json_hits[:3]:
            blocks.append(
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": plain_rich_text(
                            f"{hit.get('url', '')}\n{(hit.get('body', '') or '')[:1200]}"
                        )
                    },
                }
            )
    return blocks


def update_page(token: str, page_id: str, properties: dict[str, Any]) -> dict[str, Any]:
    payload = {"properties": properties}
    return notion_request(token, "PATCH", f"/pages/{page_id}", payload)


def append_children(token: str, block_id: str, children: list[dict[str, Any]]) -> dict[str, Any]:
    payload = {"children": children}
    return notion_request(token, "PATCH", f"/blocks/{block_id}/children", payload)


def create_page(token: str, database_id: str, properties: dict[str, Any], children: list[dict[str, Any]]) -> dict[str, Any]:
    payload = {
        "parent": {"database_id": database_id},
        "properties": properties,
        "children": children,
    }
    return notion_request(token, "POST", "/pages", payload)


def sanitize_dir_name(value: str) -> str:
    value = value.strip()
    value = re.sub(r"[^\w\-\u4e00-\u9fff]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "redbook-note"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract one or more RedBook notes, save metadata/images locally, and upsert them into a Notion material database."
    )
    parser.add_argument("--url", action="append", dest="urls", help="target note URL; pass multiple times for batch import")
    parser.add_argument("--url-file", help="text file with one note URL per line")
    parser.add_argument("--notion-token", required=True, help="Notion integration token")
    parser.add_argument("--database-id", required=True, help="Notion database id for 爆款素材库")
    parser.add_argument(
        "--output-root",
        required=True,
        help="root directory where note_id folders, metadata and images should be saved",
    )
    parser.add_argument("--screenshot", help="optional screenshot path")
    parser.add_argument("--continue-on-error", action="store_true", help="continue importing remaining URLs if one fails")
    add_browser_args(parser)
    return parser


def load_urls(args) -> list[str]:
    urls = list(args.urls or [])
    if args.url_file:
        lines = Path(args.url_file).expanduser().read_text(encoding="utf-8").splitlines()
        urls.extend([line.strip() for line in lines if line.strip() and not line.strip().startswith("#")])
    deduped = []
    seen = set()
    for url in urls:
        if url not in seen:
            seen.add(url)
            deduped.append(url)
    return deduped


def import_single_url(args, database_property_names: set[str], url: str) -> dict[str, Any]:
    metadata = extract_note(
        url=url,
        chrome_path=args.chrome_path,
        user_data_dir=args.user_data_dir,
        profile_directory=args.profile_directory,
        headless=args.headless,
        no_copy_profile=args.no_copy_profile,
        slow_mo=args.slow_mo,
        screenshot=args.screenshot,
        cdp_url=args.cdp_url,
    )

    title_or_id = metadata.get("title") or metadata.get("note_id") or "redbook-note"
    dir_name = sanitize_dir_name(f"{metadata.get('note_id')}-{title_or_id}")[:80]
    local_dir = Path(args.output_root).expanduser() / dir_name
    metadata = persist_note_artifacts(local_dir, metadata, download_image_files=True)

    raw_properties = material_properties(metadata, local_dir)
    properties = {name: value for name, value in raw_properties.items() if name in database_property_names}
    omitted_properties = sorted(set(raw_properties.keys()) - set(properties.keys()))
    children = build_children(metadata, local_dir)

    existing = query_page_by_url(args.notion_token, args.database_id, metadata.get("url") or "")
    if existing:
        page = update_page(args.notion_token, existing["id"], properties)
        append_children(args.notion_token, existing["id"], children)
        action = "updated"
    else:
        page = create_page(args.notion_token, args.database_id, properties, children)
        action = "created"

    return {
        "action": action,
        "page_id": page["id"],
        "page_url": page.get("url"),
        "local_dir": str(local_dir),
        "metadata_json": str(local_dir / "metadata.json"),
        "metadata_md": str(local_dir / "metadata.md"),
        "downloaded_images": metadata.get("downloaded_images") or [],
        "title": metadata.get("title"),
        "author": metadata.get("author"),
        "url": metadata.get("url"),
        "omitted_properties": omitted_properties,
    }


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    urls = load_urls(args)
    if not urls:
        parser.error("Provide at least one --url or a --url-file.")
    database_property_names = get_database_property_names(args.notion_token, args.database_id)
    results = []
    errors = []

    for url in urls:
        try:
            results.append(import_single_url(args, database_property_names, url))
        except Exception as exc:
            error_info = {"url": url, "error": str(exc)}
            errors.append(error_info)
            if not args.continue_on_error:
                raise

    payload = {
        "count": len(results),
        "results": results,
        "errors": errors,
    }
    print(dumps_pretty(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
