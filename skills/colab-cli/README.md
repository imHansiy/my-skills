# colab-cli

Agent skill for the real Google Colab CLI (`google-colab-cli`), fully audited against a live install + source defaults.

## Why this exists

Third-party skills invent non-existent commands (`colab start`, `colab shell`, `colab list`, `colab init`). Bundled `colab skill` can also lag (e.g. claiming default auth is `adc` while this binary defaults to `oauth2`).

## Install skill

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

## Audit snapshot (v0.2.2)

Verified CLI: `0.6.1.dev3+g354692959` (itzrnvr windows-support)

| Fact | Value |
|------|--------|
| Default `--auth` | `oauth2` |
| Visible commands | 24 (no `auth`/`whoami` in list) |
| Hidden commands | `auth`, `whoami` (still callable) |
| `exec`/`run` timeout default | `30.0` |
| `ls` default path | `content` |
| `drivemount` default path | `/content/drive` |
| `url --host` default | `https://colab.research.google.com` |
| Unknown `--gpu` | falls back to **A100** |
| Unknown `--tpu` | falls back to **V6E1** |
| `update --install` | Linux + macOS only (source); Windows rejected |
| `install` timeout flag | **none** (kernel quiet default ~10s risk) |
| `auth`/`drivemount` interactive budget | 600s |

## Contents

| Path | Purpose |
|------|---------|
| `SKILL.md` | Agent instructions |
| `references/commands.md` | Full audited command map |
| `agents/openai.yaml` | Display metadata |
| `README.md` | Human notes |

## Safety

Sessions are billable. Always `colab stop -s <name>`, or use `colab run` for ephemeral jobs.
