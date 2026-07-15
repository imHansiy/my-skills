---
name: colab-cli
description: >-
  Operate Google Colab via the official `colab` CLI (google-colab-cli). Use when
  asked to create/manage Colab sessions, run Python on remote Colab CPU/GPU/TPU
  VMs, sync files, install packages on the VM, export session history, or use
  `colab run` / `colab exec` / `colab new` / `colab stop`. Prefer this skill over
  outdated third-party Colab skill docs that invent commands like `colab start`
  or `colab shell`.
license: MIT
compatibility: >-
  Requires `colab` on PATH (google-colab-cli). Official PyPI package is Linux/macOS
  only; on Windows use the community windows-support install. Auth via oauth2
  token at ~/.config/colab-cli/token.json or gcloud ADC. Network access to Google
  Colab APIs required. Billable compute units may be consumed.
metadata:
  author: imHansiy
  version: "0.2.0"
  cli: google-colab-cli
  verified_cli_version: "0.6.1.dev3+g354692959 (itzrnvr windows-support)"
  platforms: "linux, macos, windows-with-fork"
---

# Colab CLI Operator

Operate Google Colab environments with the real `colab` CLI commands only.

## When to Apply

- Create / list / stop Colab sessions
- Run local `.py` / `.ipynb` / piped code on a remote Colab VM
- GPU/TPU one-shot jobs (`colab run`)
- Upload/download files, install packages on the VM
- Export session history as notebook/markdown/jsonl
- User mentions Colab CLI, remote Colab VM, `colab new`, `colab exec`

## Do NOT invent these commands

These appear in outdated third-party skills and **do not exist** in current CLI:

| Wrong | Correct |
|-------|---------|
| `colab init` | first-run OAuth / existing token / `gcloud auth application-default login` |
| `colab start` | `colab new -s <name>` |
| `colab shell "..."` | `echo "..." \| colab console -s <name>` or prefer `colab exec` |
| `colab list` | `colab sessions` |
| `colab stop <id>` | `colab stop -s <name>` |

Always verify with `colab --help` / `colab <cmd> --help` if unsure.

## Environment notes (this skill's target setup)

This skill is maintained for a **Windows cloud desktop** that already runs:

- CLI: community Windows fork (official main crashes on `import termios`)
- Install command used successfully:

```powershell
uv tool install "git+https://github.com/itzrnvr/google-colab-cli.git@windows-support" --force
```

- Auth: **oauth2** with token at `~/.config/colab-cli/token.json` (already authorized)
- No WSL / Docker / gcloud required once oauth2 token exists
- Official PyPI `google-colab-cli` works on Linux/macOS:

```bash
uv tool install google-colab-cli
# or
pip install google-colab-cli
```

### Windows termios crash (diagnosis)

If `colab --help` fails with `ModuleNotFoundError: No module named 'termios'`, you are on official PyPI under Windows. Reinstall the windows-support fork above.

### Auth modes

| Mode | When | Notes |
|------|------|-------|
| oauth2 (default in this environment) | token.json present | Interactive browser paste-code only on first login |
| adc | gcloud installed | Prefer for headless multi-machine agents |

Global flag must be **before** subcommand:

```text
colab --auth=oauth2 sessions
colab --auth=adc new -s demo
```

**Do not** run `colab auth` to fix CLI 401/403. That command injects **VM-side** GCP creds for BigQuery/GCS, not CLI login.

## Mental model

1. **Session = billable VM + persistent Jupyter kernel.**
2. Kernel state **survives** across `colab exec` in the same session (imports/variables stay).
3. Default remote cwd is `/content`. Prefer absolute `/content/...` paths.
4. Each `colab` invocation is fire-and-forget; keep-alive is a background daemon from `colab new`.
5. **Always `colab stop -s <name>` when done** or use `colab run` (auto-stop unless `--keep`).

## Agent-safe command rules

### Allowed non-interactive patterns

```powershell
colab sessions
colab new -s <name>
colab new -s <name> --gpu T4
colab status -s <name>
colab exec -s <name> -f script.py
echo "print(1)" | colab exec -s <name>
colab run script.py
colab run --gpu T4 train.py
colab install -s <name> numpy pandas
colab upload -s <name> local.py /content/local.py
colab download -s <name> /content/out.bin .\out.bin
colab log -s <name> -n 20
colab log -s <name> -o summary.ipynb
colab stop -s <name>
colab version
colab skill
```

### Never run interactively from an agent (will hang)

- `colab repl` (TTY)
- `colab console` without piped stdin
- `colab auth` (human TTY)
- `colab drivemount` (human TTY)

Piped-only alternatives:

```powershell
# batch shell (noisy tmux control bytes possible)
echo "ls -la /content" | colab console -s <name>

# prefer Python via exec
echo "import os; print(os.listdir('/content'))" | colab exec -s <name>
```

### Always name sessions

```powershell
colab new -s job1
```

Unnamed sessions become random 6-hex IDs and are harder to target.

## Standard workflows

### A. Hello World smoke test

```powershell
colab new -s hello
echo "print('Hello from Google Colab!')" | colab exec -s hello
colab stop -s hello
```

### B. Run local script on existing session

```powershell
colab new -s train
colab install -s train torch
colab exec -s train -f train.py
colab download -s train /content/checkpoints/model.bin .\model.bin
colab stop -s train
```

### C. Ephemeral one-shot (preferred for short jobs)

```powershell
colab run --gpu T4 train.py --epochs 1
# auto: new + exec + stop (unless --keep)
```

### D. Notebook

```powershell
colab new -s nb
colab exec -s nb -f report.ipynb
# writes report_output.ipynb next to input
colab stop -s nb
```

### E. Accelerator notes

Supported GPU: `T4`, `L4`, `G4`, `H100`, `A100`  
Supported TPU: `v5e1`, `v6e1`

- Unknown `--gpu` may silently fall back toward A100 → then fail.
- Free / low tiers often only get CPU. On 400 / 412 / capacity errors, fall back to CPU or T4.
- Do not assume GPU/TPU allocation succeeds.

## Safety

1. **Stop sessions** when finished. Idle VMs burn compute units.
2. Prefer `colab run` for short jobs (self-cleanup).
3. Do not print full OAuth tokens / refresh tokens.
4. Local state: `~/.config/colab-cli/sessions.json`, `token.json`, `settings.json`. Do not hand-edit.
5. Isolate agent runs with `--config` if needed:

```powershell
colab --config $env:TEMP\colab-agent.json new -s agent1
```

## Recovery

| Symptom | Action |
|---------|--------|
| `No module named 'termios'` on Windows | Reinstall windows-support fork |
| `Invalid code verifier` during oauth | Re-generate auth URL + fresh code (PKCE one-shot) |
| Session not found / 404 / 401 on exec | `colab sessions` then `colab new` |
| Wedged kernel | `colab restart-kernel -s <name>` or stop+new |
| keep-alive 403 / consecutive_4xx | Re-auth with correct scopes (`colaboratory` required) |
| GPU 400/412 | Use CPU or lower GPU; check account tier |

## Quick command map

| Goal | Command |
|------|---------|
| List sessions | `colab sessions` |
| Create CPU | `colab new -s NAME` |
| Create GPU | `colab new -s NAME --gpu T4` |
| Exec file | `colab exec -s NAME -f script.py` |
| Exec stdin | `echo code \| colab exec -s NAME` |
| One-shot | `colab run [--gpu T4] script.py` |
| Install pkgs | `colab install -s NAME pkg1 pkg2` |
| Upload | `colab upload -s NAME local remote` |
| Download | `colab download -s NAME remote local` |
| Export log | `colab log -s NAME -o out.ipynb` |
| Stop | `colab stop -s NAME` |
| Built-in official skill text | `colab skill` |

## More detail

- Full command reference: `references/commands.md`
- OpenAI agent metadata: `agents/openai.yaml`

When this skill conflicts with memory, **trust live `colab --help` and `colab skill` output**.
