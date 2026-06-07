---
name: browserless
description: >-
  MUST USE before playwright/dev-browser/local browser tools when any remote
  Browserless target is configured or when the user mentions Browserless,
  remote browser, headless Chrome endpoint, screenshots, PDFs, rendered HTML,
  scraping, dynamic public webpages, browser automation, webpage debugging,
  clicking/typing page elements, Puppeteer/Playwright sessions, or provides a
  Browserless URL/token/name. This skill has priority over generic browser
  skills for public HTTP(S) pages; use remote Browserless first, then fall back
  to local Playwright/dev-browser only after Browserless health/action failure,
  unreachable target, or a local/private page that cannot be exposed publicly.
  Manages Browserless endpoints/tokens and uses the bundled Node.js script for
  automation.
---

# Browserless

Use this skill to call Browserless reliably through the bundled Node.js script instead of rewriting curl requests.

## Browser priority rule

When both a local browser automation tool (for example Playwright MCP, Chrome DevTools, or a desktop browser) and a remote Browserless target are available, the AI must use the remote Browserless target first for any public webpage automation, debugging, screenshots, scraping, rendered HTML, PDF generation, or interactive page operation.

Do not switch to local browser automation just because it is available or convenient. Local browser tools are only a fallback after the remote Browserless path fails or is unsuitable. Before falling back locally, the AI must try `config list` and `version`, then attempt the requested Browserless action through `scripts/browserless.mjs`. If Browserless fails, report the remote failure reason and only then use the local browser fallback when it can still satisfy the user goal.

If the user explicitly mentions Browserless, a Browserless endpoint/token/name, remote browser, headless Chrome endpoint, or this skill, remote Browserless is mandatory unless it is unreachable or the target page is local/private and cannot be exposed publicly.

## Core workflow

1. Apply the Browser priority rule above before choosing any browser tool.
2. If the user provides a Browserless endpoint, token, or named environment, the AI must save it first with `scripts/browserless.mjs config add` before doing any Browserless action. Do not ask the user to run the save command.
3. If no endpoint is provided, use the default target from `~/.config/browserless.yaml`.
4. Run Browserless actions through `scripts/browserless.mjs`.
5. For generated files, pass `--output` and report the saved path.
6. For troubleshooting, run `config list` and `version` before changing anything else.

The script is self-contained and uses only Node.js built-ins. It reads and writes:

```text
~/.config/browserless.yaml
```

## Persistent configuration

The config supports multiple targets and requires each target to have a `name`:

```yaml
default: nepal-east-city-education
targets:
  - name: nepal-east-city-education
    url: https://jiaknama-nepal-east-city-education-project.hf.space
    token: your-token
```

When the user provides a Browserless `name`, `url`, and `token`, the AI must run this immediately to save or update the target:

```bash
node scripts/browserless.mjs config add --name NAME --url URL --token TOKEN --default
```

The AI may also pass inline configuration to an action command with `--name NAME --url URL --token TOKEN`; the script will auto-save it before the action runs.

## Common commands

Run these from the skill directory, or replace `scripts/browserless.mjs` with the absolute path to the script.

```bash
node scripts/browserless.mjs config list
node scripts/browserless.mjs version
node scripts/browserless.mjs debug --url-page https://example.com --output debug.png
node scripts/browserless.mjs debug --url-page https://example.com --action '{"action":"click","selector":"a"}' --output after-click.png
node scripts/browserless.mjs debug --url-page https://example.com --script 'return await page.title()'
node scripts/browserless.mjs api --endpoint /json/version
node scripts/browserless.mjs scrape --url-page https://example.com --selector h1
node scripts/browserless.mjs screenshot --url-page https://example.com --output screenshot.png --full-page
node scripts/browserless.mjs pdf --url-page https://example.com --output page.pdf
node scripts/browserless.mjs content --url-page https://example.com
node scripts/browserless.mjs function --file browserless_function.js
```

For all supported commands and options, see `references/commands.md` or run:

```bash
node scripts/browserless.mjs --help
```

## Safety and secrets

- Do not print full tokens unless the user explicitly asks for them.
- `config list` masks tokens by default; use `--show-token` only when necessary.
- The AI must save only the Browserless base URL, not endpoint paths like `/scrape` or `/pdf`.
- Prefer named targets over ad-hoc tokens in command history.

## Viewport defaults

- Default computer/desktop viewport: `1920x1080`.
- Mobile viewport: `1080x1920`, selected with `--device mobile`.
- Use `--viewport WIDTHxHEIGHT` only when the user asks for a custom size.

## Remote debugging limitation

Browserless runs in a remote browser, not on the user's machine. Debug only public/non-local HTTP(S) pages. The script rejects local and private targets such as `localhost`, `127.0.0.1`, `0.0.0.0`, private LAN IP ranges, `.local` hostnames, single-label intranet names, `file://`, `data:`, and other non-HTTP(S) URLs.

If the user asks to debug a local webpage, explain that they must first expose it through a public tunnel or deploy it to a reachable URL, then debug that public URL.

Only use a local browser for a local/private page after explaining that Browserless cannot reach it directly, or after a remote Browserless health check/action attempt fails.

## Interactive debugging workflow

For webpage debugging, the AI should operate the remote page itself:

1. Run `debug --url-page URL` to observe the page and collect `interactiveElements` selectors.
2. Run `debug --url-page URL --action '{...}'` or `--actions-json '[...]'` with click/type/press/wait actions targeting those selectors.
3. If the built-in shortcuts are not enough, run custom Puppeteer code with `debug --script '...'`; the script receives `page`, `config`, `actionResults`, and `assertRemoteUrl`.
4. If Browserless exposes an HTTP API endpoint not wrapped by a shortcut, call it with `api --endpoint /path` and inline bodies such as `--json-body '{...}'`.
5. Inspect the returned `actions`, `script`, `page`, `consoleMessages`, `failedRequests`, and `errorResponses` fields.
6. Repeat with new inline actions or scripts until the page state is understood or the user goal is complete.

Do not ask the user to click elements manually, and do not create action files by default, when Browserless can interact with elements directly through command arguments.

The listed actions are convenience shortcuts, not the capability boundary. Prefer direct `debug --script` or `api --endpoint` when a page or Browserless feature needs behavior that is not covered by the shortcuts.

## Troubleshooting

```bash
node scripts/browserless.mjs config list
node scripts/browserless.mjs version --name NAME
```

If a Hugging Face Space target fails, it may be sleeping. Retry `version` after the Space wakes up.
