# colab-cli

Agent skill for the real Google Colab CLI (`google-colab-cli`) with command syntax verified against a live install.

## Why this exists

Third-party skills often invent non-existent commands (`colab start`, `colab shell`, `colab list`, `colab init`). This skill is aligned with:

- Live `colab --help` / `colab <cmd> --help`
- Official `colab skill` operator notes
- A Windows cloud desktop using the community windows-support fork

## Install skill (from this monorepo)

```bash
npx skills add imHansiy/my-skills --skill colab-cli -y -g
```

## Local CLI prerequisite

**Windows:**

```powershell
uv tool install "git+https://github.com/itzrnvr/google-colab-cli.git@windows-support" --force
```

**Linux / macOS:**

```bash
uv tool install google-colab-cli
```

## Verified facts (0.2.1)

| Fact | Value |
|------|--------|
| Default `--auth` | `oauth2` (this install) |
| Exec/run default timeout | `30.0` seconds |
| `ls` default path | `content` |
| `update --install` | Linux only |
| Hidden debug command | `colab whoami` |

## Contents

| Path | Purpose |
|------|---------|
| `SKILL.md` | Agent instructions |
| `references/commands.md` | Full command map |
| `agents/openai.yaml` | Display metadata |
| `README.md` | Human notes |

## Safety

Sessions are billable. Always `colab stop -s <name>`, or use `colab run` for ephemeral jobs.
