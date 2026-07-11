# Vault format and security boundary

## Files

- `vault.json`: plaintext discovery metadata and synchronization rules. It must not contain secret values.
- `vault-key.json`: the random 256-bit master key wrapped by a passphrase-derived key.
- `objects/*.vault`: independently encrypted configuration contents.

## Per-user defaults

`configure` writes a separate version 1 defaults document outside the repository:

```json
{
  "version": 1,
  "repository": "git@github.com:me/config-vault.git",
  "vault": "C:\\Users\\me\\AppData\\Local\\config-vault\\checkout",
  "keyFile": "C:\\Users\\me\\AppData\\Roaming\\config-vault\\vault.key",
  "profile": "work",
  "os": "windows",
  "remote": "origin",
  "branch": "main"
}
```

Windows stores this document at `%APPDATA%\config-vault\config.json`. Other platforms use `$XDG_CONFIG_HOME/config-vault/config.json` or `~/.config/config-vault/config.json`. The persistent checkout uses the platform data directory.

The defaults document stores only the internal password-file path. When `configure --password-stdin` receives the Vault password, it writes the value separately to `vault.key` with owner-only permissions and records that path. Users do not create this file. `configure` validates the password against `vault-key.json` before saving either file. The legacy `--key-stdin` spelling remains an alias, and `--key-file` supports migration from an existing setup.

## Manifest

`vault.json` uses version 1:

```json
{
  "version": 1,
  "createdAt": "2026-07-11T00:00:00Z",
  "updatedAt": "2026-07-11T00:00:00Z",
  "items": [
    {
      "id": "service.api",
      "object": "objects/<sha256-of-id>.vault",
      "description": "Service API settings",
      "format": "json",
      "mode": "0600",
      "tags": ["service"],
      "profiles": ["work"],
      "os": ["windows", "linux"],
      "targets": {
        "default": ".config/service/config.json",
        "windows": "AppData/Roaming/Service/config.json"
      }
    }
  ]
}
```

Multiple selector tags use AND. An item matches a profile or OS when its rule contains that value or `*`. Targets are always relative to the supplied home directory; absolute paths and traversal are rejected.

Supported validation formats are `text`, `env`, `json`, `toml`, `ini`, `yaml`, and `powershell`. JSON, TOML, and INI receive syntax validation; the other formats receive UTF-8 validation.

## Cryptography

Initialization generates a random 32-byte master key. The operator passphrase derives a wrapping key with scrypt (`N=32768`, `r=8`, `p=1`, random 16-byte salt). AES-256-GCM wraps the master key with a random 12-byte nonce.

Each object uses the master key with AES-256-GCM and a fresh random 12-byte nonce. Authenticated associated data binds the ciphertext to the item id and format version, so copying ciphertext between ids fails authentication.

`rekey` only rewraps the master key. It does not rewrite object ciphertext.

## Exposure boundary

The repository exposes item ids, descriptions, tags, target paths, profiles, operating systems, encrypted object sizes, and Git history. Keep the repository private when that metadata is sensitive.

Anyone holding both Git write access and the vault key can read, add, modify, delete, and publish every item in that vault. Use a dedicated repository credential and a dedicated vault per trust boundary. This version does not implement per-item cryptographic authorization.

Plaintext written by `read`, `search --show-matches`, or `apply` can be captured by shell history, process logs, terminals, backups, or AI transcripts. Prefer file redirection into a restricted temporary directory and avoid printing secret values.
