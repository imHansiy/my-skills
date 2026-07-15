# Colab CLI command reference

Verified against installed CLI:

```text
colab version → 0.6.1.dev3+g354692959
default --auth → oauth2
```

Always re-check with `colab <cmd> --help` if behavior looks off.

## Global options

```text
colab [GLOBAL OPTIONS] <command> [ARGS]
```

| Flag | Meaning | Notes |
|------|---------|-------|
| `--auth oauth2\|adc` | Auth strategy | **Default: `oauth2`** on this install (not adc) |
| `-c, --client-oauth-config PATH` | OAuth client JSON | Default `~/.colab-cli-oauth-config.json` |
| `--config PATH` | Session state file | Default `~/.config/colab-cli/sessions.json` |
| `--logtostderr` | Debug to stderr | |
| `--install-completion` / `--show-completion` | Shell completion | |
| `-h, --help` | Help | |

Examples:

```powershell
colab --auth oauth2 sessions
colab --auth adc --config $env:TEMP\agent.json new -s job
```

## Hidden / debug

| Command | Purpose |
|---------|---------|
| `colab whoami` | Print auth provider, email, expiry, scopes (hidden but callable) |

## Session management

| Command | Purpose |
|---------|---------|
| `colab new -s NAME [--gpu GPU] [--tpu TPU]` | Create VM session |
| `colab sessions` | List active sessions; prune stale local entries |
| `colab status [-s NAME]` | Hardware / status |
| `colab restart-kernel [-s NAME]` | Reset kernel; keep VM |
| `colab stop [-s NAME]` | Terminate session + keep-alive |
| `colab url [-s NAME] [--host URL] [--open]` | Browser attach URL for existing session |

### Accelerators

| Flag | Values |
|------|--------|
| `--gpu` | `T4`, `L4`, `G4`, `H100`, `A100` |
| `--tpu` | `v5e1`, `v6e1` |

Omit both → CPU.

### url options

| Flag | Meaning |
|------|---------|
| `-s, --session` | Session name |
| `--host` | Frontend origin (default `https://colab.research.google.com`) |
| `--open` | Also open system browser (off by default so output stays pipeable) |

## Execution

| Command | Purpose |
|---------|---------|
| `colab exec [-s NAME] [-f FILE] [--output-image PATH] [--timeout SEC]` | Run stdin / `.py` / `.ipynb` |
| `colab run [--session NAME] [--gpu GPU] [--tpu TPU] [--keep] [--timeout SEC] SCRIPT [SCRIPT_ARGS...]` | Ephemeral new+exec+stop |
| `colab repl [-s NAME] [--output-image PATH]` | Interactive REPL (**agent: avoid**) |
| `colab console [-s NAME]` | Raw TTY; pipe stdin for batch (**agent: pipe only**) |

### Timeout defaults (important)

| Command | Option | Default |
|---------|--------|---------|
| `exec` | `--timeout` | **30.0** |
| `run` | `--timeout` | **30.0** |

Raise for long jobs:

```powershell
colab exec -s s1 -f train.py --timeout 3600
colab run --gpu T4 --timeout 3600 train.py
```

### exec notes

- Local `-f` files are read client-side and sent to the kernel (no prior upload required).
- Kernel state persists across execs on the same session.
- Working directory starts at `/content`.
- Notebooks write `<basename>_output.ipynb` next to the input file.
- PNG/JPEG can be captured with `--output-image PATH`.

### run notes

```text
colab run [options] SCRIPT [SCRIPT_ARGS...]
```

- SCRIPT is required; must exist **before** a VM is allocated.
- Args after SCRIPT become `sys.argv[1:]`.
- `--keep` leaves the session running (use `colab stop` later).
- `-s/--session` names the ephemeral session (useful with `--keep`).
- CLI chatter → **stderr**; script stdout stays on **stdout**.
- Exit codes propagate from the script.
- Shebang form is **Unix-oriented**:

```bash
#!/usr/bin/env -S colab run --gpu T4
```

Not applicable as a shebang on Windows cmd/PowerShell.

## Files

| Command | Purpose |
|---------|---------|
| `colab ls [-s NAME] [PATH]` | List remote files |
| `colab upload [-s NAME] LOCAL_PATH REMOTE_PATH` | Upload |
| `colab download [-s NAME] REMOTE_PATH LOCAL_PATH` | Download |
| `colab rm [-s NAME] PATH` | Delete remote file |
| `colab edit [-s NAME] REMOTE_PATH` | Edit via local `$EDITOR` (**agent: avoid**) |

Notes:

- `ls` default path is **`content`** (help default), not `/content`.
- Absolute `/content/...` paths work for ls/upload/download/rm.
- Argument order matters: upload is **local then remote**; download is **remote then local**.

## Automation / utilities

| Command | Purpose |
|---------|---------|
| `colab install [-s NAME] [PACKAGES...]` | Install via `uv pip install --system`, fallback `pip` |
| `colab install [-s NAME] -r FILE` | From requirements file |
| `colab auth [-s NAME]` | Authenticate Google **on the VM** (interactive) |
| `colab drivemount [-s NAME] [PATH]` | Mount Drive (default `/content/drive`, interactive) |
| `colab log [-s NAME] [-n LINES] [-t TYPE] [-o FILE]` | View/export history |
| `colab pay` | Open subscription page in browser |
| `colab version` | Print CLI version |
| `colab update [--install]` | Check update; `--install` runs pip upgrade (**Linux only**) |
| `colab skill` | Print bundled official SKILL.md |
| `colab readme` | Print bundled README.md |
| `colab help [COMMAND]` | Help listing / per-command help |

### log options

| Flag | Meaning |
|------|---------|
| `-s, --session` | Session name (omit to list sessions that have logs) |
| `-n, --lines` | Number of lines (default: all) |
| `-t, --type` | Filter event type (e.g. `execution`, `file_operation`) |
| `-o, --output` | Export path; suffix chooses format: `.ipynb`, `.md`, `.txt`, `.jsonl` |

## Auth storage

| Path | Content |
|------|---------|
| `~/.config/colab-cli/token.json` | oauth2 user token (**secret**) |
| `~/.config/colab-cli/sessions.json` | local session metadata |
| `~/.config/colab-cli/settings.json` | settings |
| `~/.config/colab-cli/history/*.jsonl` | structured history |
| `~/.colab-cli-oauth-config.json` | optional custom OAuth client |

Do not commit or print secrets.

## Install recipes

### Windows (this environment)

```powershell
uv tool install "git+https://github.com/itzrnvr/google-colab-cli.git@windows-support" --force
colab version
colab whoami
colab sessions
```

Upstream Windows PR: https://github.com/googlecolab/google-colab-cli/pull/75

### Linux / macOS

```bash
uv tool install google-colab-cli
# or: pip install google-colab-cli
```

### Self-update

```powershell
# Check only (all platforms that can reach PyPI metadata)
colab update

# In-place pip upgrade — Linux only per CLI help
colab update --install
```

On Windows, reinstall with `uv tool install ... --force` instead of `--install`.

## Agent anti-patterns

1. Inventing `start` / `shell` / `list` / `init`
2. Positional `colab stop <id>` instead of `-s`
3. Leaving sessions running after the task
4. Interactive `repl` / `console` / `auth` / `drivemount` / `edit` in agent loops
5. Assuming default 30s timeout is enough for training
6. Assuming free-tier GPU/TPU allocation
7. Printing refresh tokens
8. Using `colab auth` to fix CLI login errors
9. Running `colab update --install` on Windows and expecting it to work
