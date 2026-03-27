# Playwright Browser Setup

这套 skill 默认不用 OpenClaw，改用 `Python Playwright + 本机 Google Chrome`。

## 环境要求

- macOS 上已安装 Google Chrome
- 本机 Chrome 里已经登录小红书
- Python 3.9+

## 安装

先安装 Python 包：

```bash
python3 -m pip install --user playwright
```

默认优先复用本机 Chrome，不强制下载 Playwright 自带浏览器。

## 更稳的登录态方案：连接正在运行的 Chrome

如果复制 profile 后经常出现：

- `无登录信息`
- 标题正文能读到，但图片/互动数据不完整
- 页面偶尔掉到安全限制页

优先改用 `CDP` 连接真实浏览器会话。

### 启动带调试端口的专用 Chrome

```bash
zsh scripts/open_chrome_cdp.sh
```

默认使用：

- 端口：`9223`
- user data dir：`~/.codex/redbook-chrome-cdp`
- profile：`Default`

这个目录是给自动化专用的，不复用你日常 Chrome 默认数据目录。
第一次启动后，请在这个专用 Chrome 窗口里手动登录一次小红书。

### 用脚本连接这个 Chrome

```bash
python3 scripts/extract_redbook_note.py \
  --cdp-url 'http://127.0.0.1:9223' \
  --url 'https://www.xiaohongshu.com/explore/...'
```

## 默认路径

- Chrome 可执行文件：
  `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`
- Chrome 用户目录：
  `~/Library/Application Support/Google/Chrome`
- Chrome profile：
  `Default`

## 推荐运行方式

### 提取单条笔记

```bash
python3 scripts/extract_redbook_note.py \
  --url 'https://www.xiaohongshu.com/explore/...' \
  --output-dir ./tmp/redbook-note
```

### 下载图片

```bash
python3 scripts/extract_redbook_note.py \
  --url 'https://www.xiaohongshu.com/explore/...' \
  --output-dir ./tmp/redbook-note \
  --download-images
```

### 扫描首页推荐流

```bash
python3 scripts/scan_redbook_home_feed.py --limit 20 --output ./tmp/home-feed.json
```

### 提取并导入 Notion

```bash
python3 scripts/import_redbook_note_to_notion.py \
  --url 'https://www.xiaohongshu.com/explore/...' \
  --notion-token 'ntn_xxx' \
  --database-id 'your-material-db-id' \
  --output-root ./tmp/redbook-materials \
  --cdp-url 'http://127.0.0.1:9223'
```

## 关于 profile 复制

脚本默认会先把 Chrome profile 复制到临时目录，再用副本启动浏览器：

- 好处：避免跟你正在使用的 Chrome 互相锁文件
- 代价：第一次启动会慢一点

如果你明确要直接使用当前 profile，可加：

```bash
--no-copy-profile
```

但如果当前 Chrome 已经打开，`--no-copy-profile` 常会因为单例锁失败。
此时优先用专用 automation Chrome + `--cdp-url`。

## 常见问题

### 找不到登录态

- 先确认你登录的是同一个 Chrome profile
- 再确认脚本使用的 `--profile-directory` 是否正确

### 页面打开但抓不到标题

- 小红书页面结构可能变了
- 先截图页面，确认是否被登录弹窗或风控层挡住
- 再更新选择器

### Chrome 路径不对

手动传：

```bash
--chrome-path '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
```
