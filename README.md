# RedBook Skills Repo

This repository publishes the `redbook-skills` Codex skill for Xiaohongshu/RedBook analysis and automation.

## Install

Install from the repo path:

```bash
python3 /Users/mia/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo mengqishn/mia.77 \
  --path redbook-skills
```

Or install from the GitHub URL:

```bash
python3 /Users/mia/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --url https://github.com/mengqishn/mia.77/tree/main/redbook-skills
```

After installing, restart Codex to pick up the new skill.

## Skill Path

- GitHub skill path: `redbook-skills`
- Skill entry: `redbook-skills/SKILL.md`

## What It Includes

- RedBook home feed analysis
- Account positioning and viral-note comparison
- Topic ideation from prior patterns
- Markdown knowledge base workflows
- Note download with metadata and images
- Batch import of note URLs into a Notion material database
- Note-level viral-learning summaries for each imported note
- Publishing and comment-reply browser automation through Playwright plus a local Chrome login state

## Repo Layout

```text
redbook-skills/
  SKILL.md
  agents/openai.yaml
  persona.md
  references/
  scripts/
```
