# Browserless command reference

All commands use:

```bash
node scripts/browserless.mjs <command> [options]
```

Run commands from the skill directory, or use the absolute script path.

## Configuration

List configured targets with masked tokens:

```bash
node scripts/browserless.mjs config list
```

List configured targets with full tokens only when needed:

```bash
node scripts/browserless.mjs config list --show-token
```

Add or update a target:

```bash
node scripts/browserless.mjs config add --name NAME --url URL --token TOKEN --default
```

Remove a target:

```bash
node scripts/browserless.mjs config remove --name NAME
```

Change the default target:

```bash
node scripts/browserless.mjs config default --name NAME
```

## Health checks

When a local browser tool and Browserless are both available, run Browserless first. Start with these health checks, then perform the requested action through `node scripts/browserless.mjs`. Use local browser automation only after Browserless is unreachable, rejects the target as local/private, or the remote action fails in a way that prevents completing the task. Report the remote failure before falling back locally.

Check Chrome and protocol version:

```bash
node scripts/browserless.mjs version --name NAME
```

List active sessions:

```bash
node scripts/browserless.mjs sessions --name NAME
```

## Remote webpage debugging

Debug a public webpage and print a JSON report with navigation status, final URL, title, DOM counts, text sample, discovered interactive elements, console messages, page errors, failed requests, and HTTP error responses:

```bash
node scripts/browserless.mjs debug --url-page https://example.com
```

By default, page commands use a desktop viewport of `1920x1080`.

Use the mobile viewport of `1080x1920` when needed:

```bash
node scripts/browserless.mjs debug --url-page https://example.com --device mobile
```

Use a custom viewport only when explicitly needed:

```bash
node scripts/browserless.mjs debug --url-page https://example.com --viewport 1366x768
```

Debug and save a full-page screenshot:

```bash
node scripts/browserless.mjs debug --url-page https://example.com --output debug.png
```

Wait for a selector while debugging:

```bash
node scripts/browserless.mjs debug --url-page https://example.com --selector main --selectorTimeout 15000
```

Interact with the remote page during debugging by passing actions directly in command arguments:

```bash
node scripts/browserless.mjs debug --url-page https://example.com --action '{"action":"click","selector":"a","waitForNavigation":true}' --output after-actions.png
```

Pass multiple actions by repeating `--action`:

```bash
node scripts/browserless.mjs debug --url-page https://duckduckgo.com --action '{"action":"type","selector":"input[name=q]","text":"browserless","clear":true}' --action '{"action":"press","key":"Enter"}' --action '{"action":"waitForSelector","selector":"#links, [data-testid=web-vertical]","timeout":15000}'
```

Or pass an action array with `--actions-json`:

```json
[
  {"action": "click", "selector": "a", "waitForNavigation": true},
  {"action": "waitForSelector", "selector": "main"},
  {"action": "type", "selector": "input[name=q]", "text": "browserless", "clear": true},
  {"action": "press", "key": "Enter"},
  {"action": "wait", "ms": 1000}
]
```

```bash
node scripts/browserless.mjs debug --url-page https://example.com --actions-json '[{"action":"click","selector":"a","waitForNavigation":true}]'
```

`--actions FILE` is supported for compatibility, but the AI should prefer inline `--action` or `--actions-json` and should not create temporary action files during normal debugging.

The shortcut action list is not a capability boundary. If a page needs behavior not covered by the shortcuts, use custom Puppeteer code directly:

```bash
node scripts/browserless.mjs debug --url-page https://example.com --script 'return {title: await page.title(), hrefs: await page.$$eval("a", els => els.map(a => a.href))}'
```

The script runs after navigation and after any shortcut actions. It receives these variables:

- `page`: Puppeteer page object.
- `config`: debug configuration.
- `actionResults`: results from shortcut actions.
- `assertRemoteUrl(url)`: helper that rejects local/private URLs before navigation.

Use `--script-file FILE` only when the inline command would be impractically long; inline `--script` is preferred for normal AI debugging.

Supported debug actions:

| Action | Required fields | Notes |
| --- | --- | --- |
| `click` | `selector` | Optional `waitForNavigation`, `delay`, `timeout` |
| `type` | `selector`, `text` | Optional `clear`, `delay`, `timeout` |
| `press` | `key` | Optional `selector` focuses an element before pressing |
| `waitForSelector` | `selector` | Optional `timeout` |
| `wait` | `ms` | Sleeps for the given milliseconds |
| `select` | `selector`, `value` or `values` | For `<select>` elements |
| `check` / `uncheck` | `selector` | For checkbox/radio-like controls |
| `hover` | `selector` | Moves mouse over an element |
| `scroll` | `x`, `y` | Scrolls by offset |
| `evaluate` | `expression` or `script` | Runs JavaScript in the page context |
| `goto` / `navigate` | `url` | Only non-local HTTP(S) URLs are allowed |

The AI should use the returned `page.interactiveElements` list to choose selectors, then run another `debug` call with inline `--action` arguments. Do not ask the user to click or type manually, and do not create action files by default, when Browserless can do it remotely.

Remote-only rule: Browserless cannot inspect pages on the user's computer. The script rejects local/private targets including `localhost`, `127.0.0.1`, `0.0.0.0`, RFC1918 private IP ranges, `.local`, single-label intranet hosts, `file://`, and non-HTTP(S) URLs. Expose local pages with a public tunnel before debugging.

## Page operations

Scrape CSS selectors:

```bash
node scripts/browserless.mjs scrape --url-page https://example.com --selector h1 --selector p
```

Take a screenshot:

```bash
node scripts/browserless.mjs screenshot --url-page https://example.com --output screenshot.png --full-page
```

Take an element screenshot:

```bash
node scripts/browserless.mjs screenshot --url-page https://example.com --selector h1 --output element.png
```

Generate PDF:

```bash
node scripts/browserless.mjs pdf --url-page https://example.com --output page.pdf
```

Get rendered HTML:

```bash
node scripts/browserless.mjs content --url-page https://example.com
```

Export page content:

```bash
node scripts/browserless.mjs export --url-page https://example.com --output page.html
```

Try unblock flow:

```bash
node scripts/browserless.mjs unblock --url-page https://example.com
```

Run Lighthouse performance audit:

```bash
node scripts/browserless.mjs performance --url-page https://example.com
```

## Generic Browserless API calls

Use `api` for Browserless endpoints that are not wrapped by a convenience command:

```bash
node scripts/browserless.mjs api --endpoint /json/version
```

POST an inline JSON body without creating a file:

```bash
node scripts/browserless.mjs api --endpoint /content --method POST --json-body '{"url":"https://example.com"}'
```

Write non-text responses to a file when needed:

```bash
node scripts/browserless.mjs api --endpoint /screenshot --method POST --json-body '{"url":"https://example.com","options":{"fullPage":true,"type":"png"}}' --output screenshot.png
```

Use endpoint paths such as `/content`, `/screenshot`, or `/json/version`, not full URLs; the script automatically targets the configured Browserless base URL and appends the token.

## Custom function and sessions

Execute Browserless function JavaScript:

```bash
node scripts/browserless.mjs function --file browserless_function.js
```

Create a persistent session:

```bash
node scripts/browserless.mjs session --ttl 300000
```

Stop a persistent session:

```bash
node scripts/browserless.mjs stop-session --stop-url "https://..."
```

## Advanced JSON bodies

For unsupported endpoint options, write the full request body to a JSON file and pass it with `--json`:

```bash
node scripts/browserless.mjs scrape --json request.json
```

## Shared options

- `--name NAME`: select a saved target.
- `--url URL --token TOKEN`: provide inline configuration and auto-save it.
- `--default`: make the inline or added target the default.
- `--timeout MS`: set HTTP request timeout; default is `60000`.
- `--device desktop|mobile`: viewport profile. `desktop` is `1920x1080` and is the default; `mobile` is `1080x1920`.
- `--viewport WIDTHxHEIGHT`: custom viewport override.
- `--no-default-viewport`: do not inject the default viewport into generic Browserless request bodies.
- `--output FILE`: write binary/text response to a file when the command supports output.
- `--waitUntil VALUE`: navigation wait strategy for `debug`, `scrape`, and `content` where supported.
- `--selector SELECTOR`: wait for or target an element, depending on the command.
- `--action JSON`: one inline debug action; repeat for multiple actions.
- `--actions-json JSON`: inline JSON action array or object with `actions` array.
- `--actions FILE`: JSON action sequence file; compatibility fallback, not the default AI workflow.
- `--script CODE`: inline Puppeteer code for `debug`; use for arbitrary interactions beyond shortcuts.
- `--script-file FILE`: Puppeteer code file for very long debug scripts; compatibility fallback, not the default AI workflow.
- `--endpoint PATH`: Browserless endpoint path for generic `api` calls.
- `--json-body JSON`: inline JSON body for generic `api` calls.
- `--body TEXT`, `--body-file FILE`, `--content-type TYPE`, `--method METHOD`: lower-level `api` options.
- `--maxElements N`: maximum discovered interactive elements to include in a debug report.
