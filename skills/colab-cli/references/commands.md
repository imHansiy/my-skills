# Colab CLI command reference

Verified against `google-colab-cli` Windows fork `0.6.1.dev3+g354692959` and official CLI help. Prefer live `colab <cmd> --help` if versions differ.

## Global options

```text
colab [GLOBAL] <command> [ARGS]
```

| Flag | Meaning |
|------|---------|
| `--auth oauth2\|adc` | Auth strategy (this Windows setup uses oauth2 token) |
| `-c, --client-oauth-config PATH` | OAuth client config JSON |
| `--config PATH` | Session state file (default `~/.config/colab-cli/sessions.json`) |
| `--logtostderr` | Debug logs to stderr |
| `--help, -h` | Help |

## Session management

| Command | Purpose |
|---------|---------|
| `colab new -s NAME [--gpu GPU] [--tpu TPU]` | Create VM session |
| `colab sessions` | List active sessions (server + local prune) |
| `colab status [-s NAME]` | Hardware / status |
| `colab restart-kernel [-s NAME]` | Reset kernel, keep VM |
| `colab stop [-s NAME]` | Terminate session + keep-alive |
| `colab url [-s NAME] [--open]` | Browser URL for existing session |

GPU: `T4`, `L4`, `G4`, `H100`, `A100`  
TPU: `v5e1`, `v6e1`

## Execution

| Command | Purpose |
|---------|---------|
| `colab exec [-s NAME] [-f FILE] [--output-image PATH] [--timeout SEC]` | Run stdin / `.py` / `.ipynb` |
| `colab run [--gpu GPU] [--tpu TPU] [--keep] [-s NAME] SCRIPT [ARGS...]` | Ephemeral new+exec+stop |
| `colab repl [-s NAME]` | Interactive REPL (**agent: avoid**) |
| `colab console [-s NAME]` | Raw TTY / piped shell (**agent: pipe only**) |

### exec notes

- Local file content is read client-side and sent to kernel (no manual upload required for `-f`).
- Kernel state persists across execs in the same session.
- Default timeout may be short for long training; raise `--timeout` for long jobs.
- Notebooks write `<basename>_output.ipynb` beside input.

### run notes

- Sets `sys.argv` and `__name__ == "__main__"` like native Python.
- Exit codes propagate from the script.
- `[colab] ...` chatter → stderr; script stdout stays clean.
- Nonexistent script fails **before** allocating a VM.

## Files

| Command | Purpose |
|---------|---------|
| `colab ls [-s NAME] [PATH]` | List remote files |
| `colab upload [-s NAME] LOCAL REMOTE` | Upload |
| `colab download [-s NAME] REMOTE LOCAL` | Download |
| `colab rm [-s NAME] PATH` | Delete remote |
| `colab edit [-s NAME] PATH` | Edit remote with `$EDITOR` (**agent: avoid**) |

Default remote workspace: `/content`.

## Automation / utilities

| Command | Purpose |
|---------|---------|
| `colab install [-s NAME] PKG...` | `uv pip install --system` (fallback pip) |
| `colab install [-s NAME] -r requirements.txt` | From requirements |
| `colab auth [-s NAME]` | VM-side GCP creds (**interactive**) |
| `colab drivemount [-s NAME] [PATH]` | Mount Drive (**interactive**, default `/content/drive`) |
| `colab log [-s NAME] [-n N] [-o FILE]` | History / export (`.ipynb` `.md` `.txt` `.jsonl`) |
| `colab pay` | Open subscription page |
| `colab version` | Print CLI version |
| `colab update [--install]` | Check / self-update (platform-dependent) |
| `colab skill` | Print bundled official operator skill |
| `colab readme` | Print bundled README |
| `colab help [CMD]` | Help listing |

## Auth storage

| Path | Content |
|------|---------|
| `~/.config/colab-cli/token.json` | oauth2 user token (do not commit / print) |
| `~/.config/colab-cli/sessions.json` | local session metadata |
| `~/.config/colab-cli/settings.json` | settings |
| `~/.config/colab-cli/history/*.jsonl` | structured history |

## Windows install (recommended for this environment)

```powershell
# Requires uv
uv tool install "git+https://github.com/itzrnvr/google-colab-cli.git@windows-support" --force
colab version
colab sessions
```

Upstream PR: https://github.com/googlecolab/google-colab-cli/pull/75

Official (Linux/macOS):

```bash
uv tool install google-colab-cli
```

## Agent anti-patterns

1. Using `start` / `shell` / `list` / `init` from outdated skills
2. Leaving sessions running after task completion
3. Interactive `repl` / `console` / `auth` / `drivemount` in non-TTY agent loops
4. Printing refresh tokens from `token.json`
5. Assuming free-tier GPU availability
