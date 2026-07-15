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
  Requires `colab` on PATH. Official PyPI targets Linux/macOS; Windows needs the
  community windows-support fork (else termios crash). This install defaults
  --auth to oauth2 (token ~/.config/colab-cli/token.json); adc via --auth adc.
  Network required; Colab compute units may be billed.
metadata:
  author: imHansiy
  version: "0.2.2"
  cli: google-colab-cli
  verified_cli_version: "0.6.1.dev3+g354692959 (itzrnvr windows-support)"
  verified_against: "live colab --help + source defaults 2026-07-15"
  platforms: "linux, macos, windows-with-fork"
---

# Colab CLI Operator

**Authority order when docs conflict:**

1. Live `colab --help` / `colab <cmd> --help`
2. This skill (verified against one installed binary)
3. Bundled `colab skill` text (may lag; e.g. it still says default auth is adc)

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
| `colab init` | first oauth2 paste-code login, or `gcloud auth application-default login` for adc |
| `colab start` | `colab new -s <name>` |
| `colab shell "..."` | `echo "..." \| colab console -s <name>` (prefer `colab exec`) |
| `colab list` | `colab sessions` |
| `colab stop <id>` (positional) | `colab stop -s <name>` |

## Verified environment

| Item | Live value |
|------|------------|
| OS | Windows cloud desktop |
| CLI | `uv tool install "git+https://github.com/itzrnvr/google-colab-cli.git@windows-support" --force` |
| Version | `0.6.1.dev3+g354692959` |
| Global `--auth` default | **`oauth2`** |
| Token | `~/.config/colab-cli/token.json` |
| OAuth client path default | `~/.colab-cli-oauth-config.json` (bundled client used if missing) |
| `exec` / `run` `--timeout` default | **`30.0`** |
| `ls` path default | **`content`** |
| `drivemount` path default | **`/content/drive`** |
| `url --host` default | **`https://colab.research.google.com`** |
| `update --install` platforms | **Linux + macOS** in source (`platform.system() in ("Linux","Darwin")`); help text says "Linux only" but code rejects Windows with "Linux and macOS" |
| Hidden commands | `whoami`, `auth` (callable; omitted from top-level command list) |

### Windows termios crash

```text
ModuleNotFoundError: No module named 'termios'
```

→ official PyPI on Windows. Reinstall the windows-support fork above.

### Linux / macOS official install

```bash
uv tool install google-colab-cli
# or: pip install google-colab-cli
```

## Command inventory (this binary)

### Visible in `colab --help`

`console`, `download`, `drivemount`, `edit`, `exec`, `help`, `install`, `log`, `ls`, `new`, `pay`, `readme`, `repl`, `restart-kernel`, `rm`, `run`, `sessions`, `skill`, `status`, `stop`, `update`, `upload`, `url`, `version`

### Hidden but callable

| Command | Purpose |
|---------|---------|
| `colab whoami` | Print provider / email / expiry / scopes |
| `colab auth [-s NAME]` | VM-side Google user auth (interactive; not CLI login) |

## Auth (critical)

Global flags **before** subcommand:

```powershell
colab --auth oauth2 sessions
colab --auth adc new -s demo
```

| Mode | Default? | Notes |
|------|----------|-------|
| `oauth2` | **yes** (this install) | Browser copy-paste code first time; caches `token.json` |
| `adc` | no | gcloud / service account / metadata |

**Do not confuse:**

| Command | What it authenticates |
|---------|------------------------|
| CLI `--auth oauth2\|adc` | Local CLI → Colab APIs |
| `colab auth` (hidden) | **Inside the VM** for BigQuery/GCS (`google.colab.auth`) |

Never use `colab auth` to fix CLI 401/403.

```powershell
colab whoami
```

Need scopes including `colaboratory` and `userinfo.email` (plus openid/cloud-platform for adc paths).

## Mental model

1. **Session = billable VM + persistent Jupyter kernel.**
2. Kernel state **survives** `colab exec` / `colab repl` on the same session.
3. `exec` / `repl` / `run` force `os.chdir('/content')` first.
4. `colab ls` default argument is the relative path **`content`** (help default); `/content/...` also works for file ops.
5. Each CLI call is fire-and-forget; keep-alive daemon starts at `colab new`.
6. Always **`colab stop -s <name>`** when done, or use `colab run` (stops unless `--keep`).

## Agent-safe usage

### Preferred non-interactive

```powershell
colab sessions
colab whoami
colab new -s <name>
colab new -s <name> --gpu T4
colab status -s <name>
colab exec -s <name> -f script.py
colab exec -s <name> -f script.py --timeout 600
# PowerShell:
"print(1)" | colab exec -s <name>
# bash:
# echo "print(1)" | colab exec -s <name>
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

### `exec` input rules (source-accurate)

| Input | Behavior |
|-------|----------|
| `-f file.py` | Read local file, execute as one cell |
| `-f file.ipynb` | Run each code cell; write `<stem>_output.ipynb` beside input |
| stdin pipe | Read all stdin as code |
| TTY + no `-f` | **Error**: `No input provided. Pipe code or provide a file.` then exit 1 |

### Never hang the agent

| Command | Why | Agent alternative |
|---------|-----|-------------------|
| `colab repl` | interactive TTY | `colab exec -f` / piped `exec` |
| `colab console` without pipe | interactive TTY | `"cmd" \| colab console -s NAME` |
| `colab auth` (hidden) | interactive VM OAuth (600s budget) | user runs it |
| `colab drivemount` | interactive Drive OAuth (600s budget) | user runs it |
| `colab edit` | opens `$EDITOR` | download → edit local → upload |
| `colab pay` | opens browser | only if user asks |
| `colab update --install` on Windows | **unsupported** (Linux/macOS only) | `uv tool install ... --force` |

Piped shell (tmux control bytes possible):

```powershell
"ls -la /content" | colab console -s <name>
```

Prefer:

```powershell
"import os; print(os.listdir('/content'))" | colab exec -s <name>
```

### Always name sessions

```powershell
colab new -s job1
```

Omitted name → random `uuid4().hex[:6]`.

## Timeouts (easy to get wrong)

| Call path | Timeout |
|-----------|---------|
| `colab exec --timeout` | default **30.0** |
| `colab run --timeout` | default **30.0** |
| `colab auth` / `colab drivemount` | fixed **600** s interactive budget |
| `colab install` | **no CLI timeout flag**; uses kernel client default when quiet (~**10s** quiet stretches can `TimeoutError`) |
| keep-alive HTTP | ~10s per ping (daemon) |

Long training:

```powershell
colab exec -s train -f train.py --timeout 3600
colab run --gpu T4 --timeout 3600 train.py
```

For heavy `colab install` sets, prefer installing inside `exec`/`run` with a high `--timeout`, or split packages, if install hangs/times out.

## Accelerators (source mapping)

| Flag | Supported values |
|------|------------------|
| `--gpu` | `T4`, `L4`, `G4`, `H100`, `A100` (case-insensitive) |
| `--tpu` | `v5e1` → V5E1; **anything else non-empty** (including typos) → **V6E1** |
| neither | CPU (`Variant.DEFAULT`) |

**Silent fallbacks (important):**

- Unknown **GPU** string → **A100**
- Unknown / non-`v5e1` **TPU** string → **V6E1**

Then backend may 400 if no quota. Prefer exact supported tokens only.

## Standard workflows

### A. Hello World

```powershell
colab new -s hello
"print('Hello from Google Colab!')" | colab exec -s hello
colab stop -s hello
```

### B. Script + download

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
# new + exec + stop unless --keep
# args after script → sys.argv[1:]
```

### D. Notebook

```powershell
colab new -s nb
colab exec -s nb -f report.ipynb --timeout 1800
# writes report_output.ipynb next to input
colab stop -s nb
```

## Safety

1. Stop sessions when finished; idle VMs burn compute units.
2. Prefer `colab run` for short jobs (self-cleanup).
3. Never print OAuth / refresh tokens from `token.json`.
4. State: `~/.config/colab-cli/sessions.json`, `token.json`, `settings.json`, `history/*.jsonl` — do not hand-edit.
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
| keep-alive 403 / consecutive_4xx | `colab whoami` scopes; re-auth |
| GPU/TPU 400 | wrong/fallback accelerator or no quota → CPU/T4 |
| Exec/run dies ~30s | raise `--timeout` |
| `install` TimeoutError | long quiet pip/uv; install via `exec -f` with high timeout |
| `update --install` on Windows | unsupported; reinstall with uv |
| TTY exec no `-f` | pipe code or pass `-f` |

## Quick command map

| Goal | Command |
|------|---------|
| Who am I | `colab whoami` |
| List sessions | `colab sessions` |
| Create CPU | `colab new -s NAME` |
| Create GPU | `colab new -s NAME --gpu T4` |
| Status | `colab status -s NAME` |
| Exec file | `colab exec -s NAME -f script.py [--timeout SEC]` |
| Exec stdin | `"code" \| colab exec -s NAME` |
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

If this skill conflicts with live CLI output, **trust the live CLI**.
