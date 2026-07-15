# colab-cli

Agent skill for operating the official Google Colab CLI (`google-colab-cli`) with **real command names**.

## Why this exists

Third-party skills often document non-existent commands (`colab start`, `colab shell`, `colab list`, `colab init`). This skill is aligned with:

- Live CLI help from installed `colab`
- Official `colab skill` operator docs
- A Windows cloud desktop that needs the community windows-support fork

## Install (from this monorepo)

```bash
npx skills add imHansiy/my-skills --skill colab-cli -y -g
```

## Local CLI prerequisite

**Windows (this environment):**

```powershell
uv tool install "git+https://github.com/itzrnvr/google-colab-cli.git@windows-support" --force
```

**Linux / macOS:**

```bash
uv tool install google-colab-cli
```

## Contents

| Path | Purpose |
|------|---------|
| `SKILL.md` | Agent instructions |
| `references/commands.md` | Command map + auth paths |
| `agents/openai.yaml` | OpenAI/Codex display metadata |
| `README.md` | Human-facing notes |

## Safety

Sessions are billable. Always `colab stop -s <name>` or use `colab run` for ephemeral jobs.
