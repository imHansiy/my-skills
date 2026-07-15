# Colab CLI command reference (full audit)

Verified against installed binary **0.6.1.dev3+g354692959** (itzrnvr windows-support) by:

- `colab --help` and every subcommand `--help`
- Source defaults in `colab_cli/*.py` / `commands/*.py`
- Runtime checks: auth default, timeouts, accelerator fallbacks, self-install platform gate

Re-run live help if your version differs.

## Global options

```text
colab [GLOBAL OPTIONS] <command> [ARGS]
```

| Flag | Default | Notes |
|------|---------|-------|
| `--auth oauth2\|adc` | **`oauth2`** | Case-insensitive |
| `-c, --client-oauth-config PATH` | `~/.colab-cli-oauth-config.json` | Bundled client used if file missing |
| `--config PATH` | `~/.config/colab-cli/sessions.json` (when omitted) | Scratch isolation for agents |
| `--logtostderr` | off | |
| `--install-completion` / `--show-completion` | — | Shell completion helpers |
| `-h, --help` | — | |

```powershell
colab --auth oauth2 sessions
colab --auth adc --config $env:TEMP\agent.json new -s job
```

## Visible commands (`colab --help`)

`console` `download` `drivemount` `edit` `exec` `help` `install` `log` `ls` `new` `pay` `readme` `repl` `restart-kernel` `rm` `run` `sessions` `skill` `status` `stop` `update` `upload` `url` `version`

## Hidden but callable

| Command | Registration | Purpose |
|---------|--------------|---------|
| `colab whoami` | `hidden=True` | Auth provider, email, expiry, scopes |
| `colab auth [-s NAME]` | `hidden=True` | VM-side `google.colab.auth.authenticate_user()` |

Both still answer to `colab <cmd> --help`.

## Session management

### `colab new`

```text
colab new [-s NAME] [--gpu GPU] [--tpu TPU]
```

| Option | Behavior |
|--------|----------|
| `-s/--session` | Name; if omitted → `uuid4().hex[:6]` |
| `--gpu` | `T4\|L4\|G4\|H100\|A100` (case-insensitive). **Unknown → A100** |
| `--tpu` | `v5e1` → V5E1; **any other non-empty string → V6E1** |
| neither | CPU |

On accelerator **HTTP 400**, CLI prints quota/entitlement message and exits 1.  
After assign, keep-alive is pre-flighted; **403 scope errors** unassign the VM and exit 1 with remediation.

### Other session commands

| Command | Options |
|---------|---------|
| `colab sessions` | none |
| `colab status [-s NAME]` | optional session |
| `colab restart-kernel [-s NAME]` | optional session |
| `colab stop [-s NAME]` | optional session |
| `colab url [-s NAME] [--host URL] [--open]` | host default `https://colab.research.google.com`; `--open` default false |

`url` prints **only** the connect URL (pipe-friendly, no `[colab]` prefix on the URL line).

## Execution

### `colab exec`

```text
colab exec [-s NAME] [-f FILE] [--output-image PATH] [--timeout SEC]
```

| Option | Default | Notes |
|--------|---------|-------|
| `-s/--session` | resolved unique/active | |
| `-f/--file` | none | `.py` or `.ipynb` |
| `--output-image` | none | save plots |
| `--timeout` | **30.0** | wall clock for kernel execute |

Input selection:

1. If `-f` → file
2. Else if stdin is **not** a TTY → read stdin
3. Else → error *No input provided. Pipe code or provide a file.* exit 1

Notebook: runs each code cell; writes `<stem>_output.ipynb` beside the input path.  
Before user code: `os.chdir('/content')`.  
Kernel state persists across execs on the same session.

### `colab run`

```text
colab run [-s NAME] [--gpu GPU] [--tpu TPU] [--keep] [--timeout SEC] SCRIPT [SCRIPT_ARGS...]
```

| Option / arg | Default | Notes |
|--------------|---------|-------|
| `SCRIPT` | required | must exist **before** VM allocation |
| `SCRIPT_ARGS` | — | become `sys.argv[1:]` |
| `-s/--session` | auto name | useful with `--keep` |
| `--gpu` / `--tpu` | same mapping as `new` | unknown GPU→A100, unknown TPU→V6E1 |
| `--keep` | false | leave session running |
| `--timeout` | **30.0** | execution timeout |

Semantics: sets `sys.argv`, `__name__='__main__'`, strips shebang, filters IPython exit warning.  
CLI chatter → **stderr**; script stdout → **stdout**.  
Exit codes: SystemExit mapped like CPython; other errors → 1.  
Shebang `#!/usr/bin/env -S colab run ...` is **Unix-oriented** (not Windows cmd/PowerShell).

### `colab repl` / `colab console`

| Command | Options | Agent |
|---------|---------|-------|
| `repl` | `-s`, `--output-image` | avoid (TTY) |
| `console` | `-s` | pipe only |

## Files

| Command | Signature | Defaults / notes |
|---------|-----------|------------------|
| `ls` | `[-s NAME] [PATH]` | PATH default **`content`** |
| `upload` | `[-s NAME] LOCAL_PATH REMOTE_PATH` | local then remote |
| `download` | `[-s NAME] REMOTE_PATH LOCAL_PATH` | remote then local |
| `rm` | `[-s NAME] PATH` | required path |
| `edit` | `[-s NAME] REMOTE_PATH` | uses `$EDITOR`; agent avoid |

Absolute `/content/...` works. Relative paths are relative to VM contents API roots.

## Automation / utilities

### `colab install`

```text
colab install [-s NAME] [-r REQUIREMENTS] [PACKAGES...]
```

- Requires packages and/or `-r`.
- `-r` file must exist **locally**; uploaded to `content/<basename>` then installed as `/content/<basename>`.
- Remote: try `uv pip install --system ...`, else `python -m pip install ...`.
- **No `--timeout` flag.** Kernel quiet default ~10s can surface `TimeoutError` on long installs.

### `colab auth` (hidden)

```text
colab auth [-s NAME]
```

Runs VM `google.colab.auth.authenticate_user()` with **600s** interactive timeout. Not CLI login.

### `colab drivemount`

```text
colab drivemount [-s NAME] [PATH]
```

PATH default **`/content/drive`**. Interactive Drive OAuth; **600s** budget; may print URL and wait for Enter.

### `colab log`

```text
colab log [-s NAME] [-n LINES] [-t TYPE] [-o FILE]
```

| Flag | Default | Notes |
|------|---------|-------|
| `-s` | omit → list sessions with logs | |
| `-n/--lines` | all | |
| `-t/--type` | none | e.g. `execution`, `file_operation` |
| `-o/--output` | none | suffix: `.ipynb` `.md` `.txt` `.jsonl` |

### Other

| Command | Notes |
|---------|-------|
| `pay` | opens `https://colab.research.google.com/signup` |
| `version` | `Version: <pep440>` |
| `update` | check PyPI |
| `update --install` | **Linux + macOS only** (source). Help string says "Linux only"; Windows exits 1 with message mentioning Linux and macOS |
| `skill` / `readme` | print bundled resources |
| `help [COMMAND]` | root help or one command |

## Auth storage

| Path | Content |
|------|---------|
| `~/.config/colab-cli/token.json` | oauth2 user token (**secret**) |
| `~/.config/colab-cli/sessions.json` | session metadata |
| `~/.config/colab-cli/settings.json` | settings (incl. update check) |
| `~/.config/colab-cli/history/*.jsonl` | history events |
| `~/.colab-cli-oauth-config.json` | optional custom OAuth client |

## Install recipes

### Windows (this environment)

```powershell
uv tool install "git+https://github.com/itzrnvr/google-colab-cli.git@windows-support" --force
colab version
colab whoami
colab sessions
```

PR: https://github.com/googlecolab/google-colab-cli/pull/75

### Linux / macOS

```bash
uv tool install google-colab-cli
```

### Self-update

```powershell
colab update                 # check (any platform that can reach PyPI)
colab update --install       # Linux/macOS only
```

Windows: reinstall with `uv tool install ... --force` (do not expect `--install`).

Note: upgrade recommendation for uv tools checks `"/uv/tools/"` in `sys.executable` (forward slashes). Windows paths use backslashes; self-install is already platform-gated off on Windows.

## Accelerator fallback matrix (source)

| Input | Result |
|-------|--------|
| no gpu/tpu | CPU |
| `--gpu T4` (any case) | GPU T4 |
| `--gpu nope` | GPU **A100** |
| `--tpu v5e1` | TPU V5E1 |
| `--tpu v6e1` / `foo` / `v5` | TPU **V6E1** |

## Agent anti-patterns

1. Inventing `start` / `shell` / `list` / `init`
2. Positional `colab stop <id>`
3. Leaving sessions running
4. Interactive `repl` / unpiped `console` / `auth` / `drivemount` / `edit`
5. Relying on default 30s for training
6. Assuming free-tier GPU/TPU
7. Printing refresh tokens
8. Using `colab auth` to fix CLI login
9. `colab update --install` on Windows
10. `colab exec` on a TTY without `-f` or pipe
11. Typos in `--gpu`/`--tpu` (silent wrong accelerator)
