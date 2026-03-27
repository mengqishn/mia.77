# Mia.77 Skills Collection

This repository is a Codex skill collection.

It is structured as a multi-skill repo: each top-level folder is a self-contained skill that can be installed independently with Codex's GitHub skill installer.

## Available Skills

### `redbook-skills`

Xiaohongshu/RedBook analysis and automation skillset.

What it covers:

- Home feed analysis
- Account positioning and viral-note comparison
- Topic ideation from prior patterns
- Markdown knowledge base workflows
- Note download with metadata and images
- Batch import of note URLs into a Notion material database
- Note-level viral-learning summaries for each imported note
- Publishing and comment-reply browser automation through Playwright plus a local Chrome login state

Skill path:

- `redbook-skills`

Skill entry:

- `redbook-skills/SKILL.md`

## Install A Skill

Install by repo path:

```bash
python3 /Users/mia/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo mengqishn/mia.77 \
  --path redbook-skills
```

Install by GitHub URL:

```bash
python3 /Users/mia/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --url https://github.com/mengqishn/mia.77/tree/main/redbook-skills
```

After installing, restart Codex to pick up the new skill.

## Repository Convention

- Each top-level skill folder is installable on its own.
- Every skill keeps its own `SKILL.md`, `agents/`, `scripts/`, and `references/`.
- This repo can grow into a broader skill library without changing existing install paths.

## Repository Layout

```text
redbook-skills/
  SKILL.md
  agents/openai.yaml
  persona.md
  references/
  scripts/
```

More skills can be added later as additional top-level folders in the same repository.
