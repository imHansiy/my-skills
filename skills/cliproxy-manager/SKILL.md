---
name: cliproxy-manager
description: Unified management skill for CLIProxyAPI, enabling AI to dynamically update service configurations (API Keys, model aliases, proxy rules) and monitor usage statistics.
---

# CLIProxyAPI Manager Skill

This skill grants the AI instance the ability to manage the CLIProxyAPI service remotely or locally. With this skill, the AI can automate configuration processes, modify model routing, and monitor service health.

## ⚠️ Prerequisites (MANDATORY)

Before executing any API operations, the AI must:
1. **Confirm Service Status**: Check if the CLIProxyAPI process is running (default port `8317`).
2. **Obtain Management Key**: A valid key must be provided for authentication.
    - Check the `MANAGEMENT_PASSWORD` environment variable.
    - Search for `remote-management.secret-key` in `config.yaml`.
    - If the key is hashed (bcrypt), the user must provide the plaintext key or use a temporary key set via the command line (`--password`).
3. **Verify Connectivity**: Attempt to call `GET /v0/management/config` for an authentication test.

## Key Workflows

### 1. Configuration Management
- **View Current Config**: Call `GET /config` to understand current routing and model providers.
- **Update Model Aliases or API Keys**: Use `PATCH` on the corresponding endpoint (e.g., `/claude-api-key` or `/openai-compatibility`).
- **Synchronous Updates**: All API changes are automatically written back to the disk file; no manual YAML editing is required.

### 2. Status & Statistics
- **Usage Stats**: Use `GET /usage` to view quotas and request counts for different models or API keys.
- **Debug Monitoring**: Use `GET /debug` to retrieve backend connection status.

### 3. API Reference
| Endpoint                | Method      | Common Use Case                                                        |
| :---------------------- | :---------- | :--------------------------------------------------------------------- |
| `/config`               | `GET`       | Fetch the final global configuration                                   |
| `/api-keys`             | `PUT/PATCH` | Manage CLIProxyAPI's own access keys                                   |
| `/gemini-api-key`       | `PATCH`     | Rotate or add Gemini keys                                              |
| `/claude-api-key`       | `PATCH`     | Rotate or add Claude keys                                              |
| `/openai-compatibility` | `PATCH`     | Configure new OpenAI-compatible providers (e.g., DeepSeek, OpenRouter) |
| `/usage`                | `GET`       | View real-time model usage reports                                     |

## Scripts

A helper Python script `cliproxy_api.py` is provided in the `<SKILL_PATH>/scripts/` directory to encapsulate authentication logic:

```bash
# Example: Fetch all configurations
python <SKILL_PATH>/scripts/cliproxy_api.py --key YOUR_KEY get config

# Example: Update a specific API Key in the config
python <SKILL_PATH>/scripts/cliproxy_api.py --key YOUR_KEY patch api-keys --data '{"old":"k1", "new":"k2"}'
```

## Rules & Best Practices

- **Security First**: Never log the full management key in any output or logs.
- **Transactional Consistency**: Always perform `GET /config` to verify current state before applying updates.
- **Backup Recommendation**: Before a full configuration overwrite (`PUT`), it is recommended to back up the current `GET /config` result to `/tmp/`.
