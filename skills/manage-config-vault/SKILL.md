---
name: manage-config-vault
description: Manage AI-readable and AI-writable encrypted configuration repositories with persistent per-user defaults. Use when Codex needs to remember a vault repository and Vault password after first setup, initialize or clone a vault, discover configuration by metadata or decrypted content, read secrets, add/edit/delete encrypted items, apply profile/OS/tag rules, validate a vault, rotate its password, or publish changes safely through Git branches.
---

# Manage Config Vault

Use `scripts/vaultctl.py` for deterministic vault operations. Require Python 3.11+, `cryptography`, and Git for remote workflows. If `cryptography` is missing, install `scripts/requirements.txt` into the active Python environment.

## Safety rules

- Receive the Vault password once and pass it through stdin to `configure --password-stdin`. Never put it in an argument, commit, log, or final response.
- Treat decrypted output as secret. Use a restricted temporary directory, avoid echoing values, and remove plaintext after use.
- Search metadata first. Add `--content` only when metadata is insufficient; add `--show-matches` only when the plaintext line is actually needed.
- Publish AI writes on an `ai/...` or `codex/...` branch. Do not push directly to the default branch unless the user explicitly requests it.
- Validate with `validate --decrypt` before publishing.
- Require explicit user intent before deleting an item or applying `--force` to a real home directory.
- Keep Git authentication separate from the vault key. Use a repository-scoped credential.

## Resolve saved defaults first

Run this before asking the user for a repository or key:

```powershell
python scripts/vaultctl.py defaults --json
```

If it succeeds, use the saved checkout, key file, profile, OS, remote, and branch automatically. Do not ask the user for them again. Normal commands load these defaults without explicit flags.

If it reports that no default exists, ask once for the repository address and Vault password:

```powershell
python scripts/vaultctl.py configure --repository <repository> --password-stdin `
  --profile <profile> --os <os>
```

Pass the password through a subprocess stdin channel and never interpolate it into a shell command. `configure` stores it in a separate owner-restricted internal `vault.key`, clones the remote into a persistent checkout, and saves defaults under the user's configuration directory. Do not ask the user to create a key file. Use `--key-file` only to migrate an existing setup.

Use `--vault`, `--key-file`, `--profile`, or `--os` later only when the user explicitly requests a one-off override.

## Discover and read

List the plaintext catalog without decrypting objects:

```powershell
python scripts/vaultctl.py list --json
python scripts/vaultctl.py search <query>
```

Search decrypted content without printing matching values:

```powershell
python scripts/vaultctl.py search <query> --content
```

Read only the chosen item:

```powershell
python scripts/vaultctl.py read <item-id>
```

## Add and update

Write proposed plaintext to a restricted temporary file. Add a new item with metadata that makes it discoverable and controls where it applies:

```powershell
python scripts/vaultctl.py add <item-id> --from <temp-file> `
  --format toml --item-tag cli --item-profile work --item-os windows `
  --target "windows=.config/tool/config.toml"
```

Replace content or metadata:

```powershell
python scripts/vaultctl.py update <item-id> --from <temp-file>
```

Delete only when the user requested deletion:

```powershell
python scripts/vaultctl.py delete <item-id> --yes
```

## Validate and apply rules

Validate metadata, authentication tags, keys, and supported JSON/TOML/INI syntax:

```powershell
python scripts/vaultctl.py validate --decrypt
```

Preview full or selective application. Use `--id`, repeatable `--tag`, `--profile`, and `--os` as selectors:

```powershell
python scripts/vaultctl.py apply --home <sandbox-home> --dry-run
```

Apply to a sandbox first. Existing files are changed only with `--force`.

## Publish changes

Publish validated vault files only; unrelated working-tree files remain unstaged:

```powershell
python scripts/vaultctl.py publish `
  --branch ai/<short-change-name> --message "chore(config): <summary>"
```

Create a pull request with the available GitHub integration after the branch is pushed. Report the branch if no PR integration is available.

Read [references/vault-format.md](references/vault-format.md) when changing the manifest schema, diagnosing authentication failures, rotating keys, or reviewing the encryption boundary.
