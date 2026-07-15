---
name: colab-cli
description: >-
  Operate Google Colab via the real `colab` CLI (google-colab-cli). Use when
  asked to create/manage Colab sessions, run Python on remote Colab CPU/GPU/TPU
  VMs, sync files, install packages on the VM, export session history, or use
  `colab run` / `colab exec` / `colab new` / `colab stop` / `colab sessions`.
  Prefer this over outdated docs that invent `colab start`, `colab shell`,
  `colab list`, or `colab init`.
license: MIT
compatibility: >-
  Requires `colab` on PATH. Official PyPI builds target Linux/macOS; on Windows
  install the community windows-support fork or hit termios import crash.
  Auth: this CLI defaults to oauth2 (token at ~/.config/colab-cli/token.json);
  adc also supported via --auth adc. Network + possible Colab compute unit cost.
metadata:
  author: imHansiy
  version: "0.2.1"
  cli: google-colab-cli
  verified_cli_version: "0.6.1.dev3+g354692959 (itzrnvr windows-support)"
  platforms: "linux, macos, windows-with-fork"
---

# Colab CLI Operator

Use **only** commands that exist in live `colab --help`. When unsure, run
`colab <cmd> --help` or `colab skill` (bundled official operator text).

## When to Apply

- Create / list / stop Colab sessions
- Run local `.py` / `.ipynb` / piped code on a remote Colab VM
- GPU/TPU one-shot jobs (`colab run`)
- Upload / download / install packages
- Export session history (`.ipynb` / `.md` / `.txt` / `.jsonl`)
- User mentions Colab CLI, remote Colab VM, `colab new`, `colab exec`

## Forbidden / invented commands

| Wrong | Correct |
|-------|---------|
| `colab init` | first login via oauth2 paste-code, or `gcloud auth application-default login` for adc |
| `colab start` | `colab new -s <name>` |
| `colab shell "..."` | `echo "..." \| colab console -s <name>` (prefer `colab exec`) |
| `colab list` | `colab sessions` |
| `colab stop <id>` (positional) | `colab stop -s <name>` |

## Environment (verified on this machine)

| Item | Value |
|------|--------|
| OS | Windows cloud desktop (no WSL/Docker required once CLI works) |
| CLI install | `uv tool install "git+https://github.com/itzrnvr/google-colab-cli.git@windows-support" --force` |
| Verified version | `0.6.1.dev3+g354692959` |
| Auth default | **`oauth2`** (live help: `[default: oauth2]`) |
| Token path | `~/.config/colab-cli/token.json` |
| OAuth client default | `~/.colab-cli-oauth-config.json` (bundled client works if file missing) |

### Windows termios crash

```text
ModuleNotFoundError: No module named 'termios'
```

Means official PyPI build on Windows. Reinstall the windows-support fork above.

### Linux / macOS official install

```bash
uv tool install google-colab-cli
# or: pip install google-colab-cli
```

## Auth (critical)

Global flags **must come before** the subcommand:

```powershell
colab --auth oauth2 sessions
colab --auth adc new -s demo
```

| Mode | When | Notes |
|------|------|-------|
| `oauth2` | default on this install | Browser copy-paste code on first use; caches `token.json` |
| `adc` | gcloud / service account available | For headless multi-host agents |

**CLI auth ≠ `colab auth`.**  
`colab auth -s <name>` injects **VM-side** GCP credentials for BigQuery/GCS and is interactive. Never use it to fix CLI 401/403.

Debug identity (hidden command, but real):

```powershell
colab whoami
```

Shows provider, email, expiry, scopes. Need `colaboratory` + `userinfo.email` among others.

## Mental model

1. **Session = billable VM + persistent Jupyter kernel.**
2. Kernel state **survives** across `colab exec` / `colab repl` on the same session.
3. Exec/repl/run `cd` to **`/content`** first. Prefer absolute `/content/...` paths.
4. `colab ls` default path is **`content`** (not `/content`); `/content/...` also works.
5. Each invocation is fire-and-forget; keep-alive daemon is started by `colab new`.
6. Always **`colab stop -s <name>`** when done, or use `colab run` (auto-stop unless `--keep`).

## Agent-safe commands

### Preferred non-interactive set

```powershell
colab sessions
colab whoami
colab new -s <name>
colab new -s <name> --gpu T4
colab status -s <name>
colab exec -s <name> -f script.py
colab exec -s <name> -f script.py --timeout 600
echo "print(1)" | colab exec -s <name>
colab run script.py
colab run --gpu T4 --timeout 600 train.py
colab run --keep -s keep1 train.py
colab install -s <name> numpy pandas
colab install -s <name> -r requirements.txt
colab ls -s <name>
colab ls -s <name> /content
colab upload -s <name> local.py /content/local.py
colab download -s <name> /content/out.bin .\out.bin
colab rm -s <name> /content/tmp.txt
colab log -s <name> -n 20
colab log -s <name> -t execution -n 50
colab log -s <name> -o summary.ipynb
colab url -s <name>
colab restart-kernel -s <name>
colab stop -s <name>
colab version
colab skill
colab readme
colab help
colab help exec
```

### Never hang the agent

| Command | Why | Agent alternative |
|---------|-----|-------------------|
| `colab repl` | TTY REPL | `colab exec -f` / piped `exec` |
| `colab console` (no pipe) | interactive TTY | `echo cmd \| colab console -s NAME` |
| `colab auth` | human TTY on VM | ask user to run it |
| `colab drivemount` | human TTY | ask user to run it |
| `colab edit` | opens `$EDITOR` | `download` → edit local → `upload` |
| `colab pay` | opens browser | only if user asks |
| `colab update --install` | **Linux only** per help | Windows: reinstall via `uv tool install ...` |

Piped shell (noisy tmux bytes possible):

```powershell
echo "ls -la /content" | colab console -s <name>
```

Prefer:

```powershell
echo "import os; print(os.listdir('/content'))" | colab exec -s <name>
```

### Always name sessions

```powershell
colab new -s job1
```

Unnamed names become random 6-hex IDs.

## Timeouts (easy to get wrong)

Live defaults:

| Command | Flag | Default |
|---------|------|---------|
| `colab exec` | `--timeout` | **30.0** seconds |
| `colab run` | `--timeout` | **30.0** seconds |

Long training / installs in-script will die at 30s unless raised:

```powershell
colab exec -s train -f train.py --timeout 3600
colab run --gpu T4 --timeout 3600 train.py
```

Package install uses `colab install` (separate from exec timeout).

## Standard workflows

### A. Hello World

```powershell
colab new -s hello
echo "print('Hello from Google Colab!')" | colab exec -s hello
colab stop -s hello
```

### B. Script + download artifacts

```powershell
colab new -s train
colab install -s train torch
colab exec -s train -f train.py --timeout 3600
colab download -s train /content/checkpoints/model.bin .\model.bin
colab stop -s train
```

### C. Ephemeral one-shot

```powershell
colab run --gpu T4 --timeout 3600 train.py --epochs 1
# new + exec + stop (unless --keep)
# args after the script path go to sys.argv
```

### D. Notebook

```powershell
colab new -s nb
colab exec -s nb -f report.ipynb --timeout 1800
# writes report_output.ipynb next to input
colab stop -s nb
```

### E. Accelerators

| Flag | Values |
|------|--------|
| `--gpu` | `T4`, `L4`, `G4`, `H100`, `A100` |
| `--tpu` | `v5e1`, `v6e1` |

- Omit both → CPU.
- Unknown `--gpu` may silently fall toward **A100** then fail.
- Tier/capacity errors (400/412) → fall back to CPU or T4.
- Never assume free-tier GPU works.

## Safety

1. Stop sessions when finished; idle VMs burn compute units.
2. Prefer `colab run` for short jobs (self-cleanup).
3. Never print full OAuth / refresh tokens from `token.json`.
4. State files: `~/.config/colab-cli/sessions.json`, `token.json`, `settings.json`, `history/*.jsonl` — do not hand-edit.
5. Isolate agent runs:

```powershell
colab --config $env:TEMP\colab-agent.json new -s agent1
```

## Recovery

| Symptom | Action |
|---------|--------|
| `No module named 'termios'` | Reinstall windows-support fork |
| `Invalid code verifier` | New auth URL + fresh code only (PKCE) |
| Session not found / 404 / 401 on exec | `colab sessions` → `colab new` |
| Wedged kernel | `colab restart-kernel -s NAME` or stop+new |
| keep-alive 403 / consecutive_4xx | Fix scopes (`colab whoami`); re-auth |
| GPU 400/412 | CPU or lower GPU; check tier |
| Exec/run dies ~30s | Raise `--timeout` |
| `update --install` on Windows | Unsupported; use `uv tool install ... --force` |

## Quick command map

| Goal | Command |
|------|---------|
| Who am I | `colab whoami` |
| List sessions | `colab sessions` |
| Create CPU | `colab new -s NAME` |
| Create GPU | `colab new -s NAME --gpu T4` |
| Status | `colab status -s NAME` |
| Exec file | `colab exec -s NAME -f script.py [--timeout SEC]` |
| Exec stdin | `echo code \| colab exec -s NAME` |
| One-shot | `colab run [--gpu T4] [--timeout SEC] script.py [args...]` |
| Install | `colab install -s NAME pkg...` / `-r requirements.txt` |
| List files | `colab ls -s NAME [PATH]` |
| Upload | `colab upload -s NAME LOCAL REMOTE` |
| Download | `colab download -s NAME REMOTE LOCAL` |
| Remove remote | `colab rm -s NAME PATH` |
| Log / export | `colab log -s NAME [-n N] [-t TYPE] [-o FILE]` |
| Browser URL | `colab url -s NAME [--host URL] [--open]` |
| Restart kernel | `colab restart-kernel -s NAME` |
| Stop | `colab stop -s NAME` |
| Official skill dump | `colab skill` |

## More detail

- Full reference: `references/commands.md`
- Agent metadata: `agents/openai.yaml`

If this skill conflicts with live CLI output, **trust `colab --help` / `colab <cmd> --help`**.
