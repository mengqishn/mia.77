---
name: redbook-skills
description: 小红书/RedBook 运营与自动化执行技能。Use when Codex needs to analyze the RedBook home feed, inspect an account's定位与爆款差异, generate topic ideas from prior patterns, maintain a markdown knowledge base, batch import RedBook note URLs into a Notion 素材库 with note-level viral-learning summaries, download a target note's assets/text, recreate a viral note, or automate RedBook publishing and comment replies through Playwright plus a local Chrome login state instead of OpenClaw.
---

# RedBook Skills

## Overview

用这套技能处理小红书的完整闭环：找信号、拆结构、沉淀知识、再执行发布/回复/复刻。

默认浏览器方案不是 OpenClaw，而是 `Playwright + 本地 Chrome 用户目录`。当任务涉及站内浏览、抓取、发布、评论回复时，先读 [references/redbook-browser-playwright.md](references/redbook-browser-playwright.md)。
首次启用浏览器脚本前，再读 [references/redbook-browser-setup.md](references/redbook-browser-setup.md)。

## Quick Start

开始新任务时按这个顺序走：

1. 先读本技能目录下的 [persona.md](persona.md)，确认默认人设、语气和边界。
2. 在当前工作目录检查是否已有 `redbook-knowledge-base/README.md`。
3. 若没有知识库，运行 `scripts/init_knowledge_base.py` 为当前项目初始化本地知识库。
4. 读当前项目里的 `redbook-knowledge-base/README.md`，再按任务类型检索最近记录。
5. 进入对应能力流转，不要跳过“写回知识库”。
6. 若当前机器还没装 `playwright`，先按 [references/redbook-browser-setup.md](references/redbook-browser-setup.md) 安装依赖。

## Core Capabilities

### 1. 首页推荐流分析

目标：回答“为什么这些内容推给你，它们靠什么传播”。

- 先用真实浏览器进入首页推荐流，优先记录近 10 条里高频出现的主题、标题句式、封面层级和互动动作。
- 输出聚焦 4 件事：推荐理由、传播钩子、内容结构、可迁移方向。
- 详细流程见 [references/redbook-home-feed-analysis.md](references/redbook-home-feed-analysis.md)。

### 2. 账号分析

目标：回答“这个账号在做什么，不同笔记差在哪，为什么某篇赞更高”。

- 默认采样最近 9-15 篇内容。
- 从定位、结构、互动、辨识度、持续性 5 个维度判断。
- 结论必须包含：最大优势、最大短板、下一步动作。
- 详细流程见 [references/redbook-account-analysis.md](references/redbook-account-analysis.md)。

### 3. 选题灵感

目标：把平台信号、已有 pattern、账号定位合成可发选题。

- 默认输出 3-5 条。
- 每条都带：选题标题、切入角度、三段式正文、互动钩子、风险提示。
- 详细流程见 [references/redbook-topic-ideation.md](references/redbook-topic-ideation.md)。

### 4. 知识库

目标：把分析和执行沉淀成可检索的 markdown，而不是聊天记录。

- 默认在当前工作目录写入 `redbook-knowledge-base/`。
- 任务前先检索，任务后至少写一条记录。
- 分析优先记到 `patterns/`、`topics/`、`reviews/`。
- 执行动作优先记到 `actions/`。
- 详细结构见 [references/redbook-knowledge-base.md](references/redbook-knowledge-base.md)。

### 5. 自动发布笔记

目标：上传图片、填写标题正文、到发布前停手或按用户要求提交。

- 发布前先确认登录态、创作页、素材文件路径。
- 到“发布”按钮可见时默认停手，除非用户明确要求发布。
- 详细流程见 [references/redbook-publish-flow.md](references/redbook-publish-flow.md)。

### 6. 自动回复评论

目标：逐条处理通知里的评论或指定笔记评论。

- 默认一轮只处理一个明确范围，避免误回。
- 先对位评论，再生成回复，再输入发送。
- 详细流程见 [references/redbook-comment-ops.md](references/redbook-comment-ops.md)。

### 7. 目标笔记下载

目标：保存目标 URL 的标题、正文、图片链接或下载图片。

- 优先保存结构化信息，再决定是否下载素材。
- 若下载图片，按笔记 ID 建目录。
- 详细流程见 [references/redbook-download-flow.md](references/redbook-download-flow.md)。

### 7.5 批量导入爆款素材库

目标：把多条小红书笔记链接批量导入 Notion 爆款素材库，并为每条笔记生成“这篇内容该学什么”的学习型字段。

- 默认同时保存 `metadata.json`、`metadata.md` 和图片到本地目录。
- `可复用结论` 要写成“这篇爆款笔记的学习结论”，不是泛泛复用建议。
- 可批量接收多个 `--url`，或从 `--url-file` 读取一批链接。
- 适合用在爆款笔记收集、拆解入库、后续自动化发帖前的数据整理。

### 8. 爆款笔记复刻

目标：输入一条爆款链接，产出同主题、同互动机制、但不逐字复制的新笔记。

- 先拆 `标题模板 + 封面层级 + 正文节奏 + 互动机制`。
- 再输出新封面、新标题、新正文、新话题。
- 详细流程见 [references/redbook-viral-copy-flow.md](references/redbook-viral-copy-flow.md)。

## Working Rules

- 始终优先真实浏览器登录态，不要假设未验证的页面内容。
- 抓取优先 `evaluate`/DOM 提取，少做整页 dump。
- 关键操作最多重试 1 次；第二次失败就换稳妥路径并汇报。
- 未直接读到页面时，不要编造标题、正文、作者或互动数据。
- 复刻只做结构级学习，不做逐字照抄或原图复用。

## Playwright Browser Mode

涉及浏览器动作时遵循：

1. 优先复用本机已登录的 Chrome 用户目录。
2. 用持久化上下文而不是匿名无痕会话。
3. 每次先校验页面是否登录、是否 404、是否能看到标题或互动区。
4. 两次失败就停止盲重试，返回“当前页面需人工接管”。

浏览器实现细节见 [references/redbook-browser-playwright.md](references/redbook-browser-playwright.md)。

可直接复用的脚本：

- `scripts/extract_redbook_note.py`
  读取一条笔记 URL，提取标题、作者、正文、互动数据、图片链接；可选下载图片。
- `scripts/import_redbook_note_to_notion.py`
  批量读取笔记 URL，保存 `metadata + 图片` 到本地，再 upsert 到 Notion 爆款素材库，并写入笔记级爆款学习结论。
- `scripts/scan_redbook_home_feed.py`
  打开首页推荐流，抓取前若干条卡片用于首页推荐流分析。
- `scripts/redbook_browser_common.py`
  Playwright 启动、Chrome 配置和 profile 复制逻辑。
- `scripts/open_chrome_cdp.sh`
  用远程调试端口启动 Chrome，供 `--cdp-url` 连接真实浏览器会话。

## Knowledge Base Write-Back

任务结束时至少补一条记录，最小标准：

- 一句话结论
- 证据或来源 URL
- 可复用点
- 风险或边界
- 下一步动作

需要新建知识库时，运行：

```bash
python3 scripts/init_knowledge_base.py --root "$PWD"
```

需要快速生成条目模板时，运行：

```bash
python3 scripts/create_kb_entry.py --root "$PWD" --type patterns --brief title-hook
```

## References

- 浏览器运行规则：[references/redbook-browser-playwright.md](references/redbook-browser-playwright.md)
- 浏览器安装与启动：[references/redbook-browser-setup.md](references/redbook-browser-setup.md)
- 首页推荐流分析：[references/redbook-home-feed-analysis.md](references/redbook-home-feed-analysis.md)
- 账号分析：[references/redbook-account-analysis.md](references/redbook-account-analysis.md)
- 选题灵感：[references/redbook-topic-ideation.md](references/redbook-topic-ideation.md)
- 知识库：[references/redbook-knowledge-base.md](references/redbook-knowledge-base.md)
- 发布流程：[references/redbook-publish-flow.md](references/redbook-publish-flow.md)
- 评论回复：[references/redbook-comment-ops.md](references/redbook-comment-ops.md)
- 目标笔记下载：[references/redbook-download-flow.md](references/redbook-download-flow.md)
- 爆款复刻：[references/redbook-viral-copy-flow.md](references/redbook-viral-copy-flow.md)
