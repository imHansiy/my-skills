#!/usr/bin/env node

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const CONFIG_PATH = path.join(os.homedir(), '.config', 'browserless.yaml');
const VIEWPORT_PROFILES = {
  desktop: { width: 1920, height: 1080, deviceScaleFactor: 1, isMobile: false, hasTouch: false },
  mobile: { width: 1080, height: 1920, deviceScaleFactor: 1, isMobile: true, hasTouch: true },
};

function printUsage() {
  console.log(`Browserless helper

Usage:
  browserless.mjs config list
  browserless.mjs config add --name NAME --url URL --token TOKEN [--default]
  browserless.mjs config remove --name NAME
  browserless.mjs config default --name NAME
  browserless.mjs version [--name NAME] [--url URL --token TOKEN]
  browserless.mjs sessions [--name NAME]
  browserless.mjs scrape --url-page URL --selector SELECTOR [--selector SELECTOR]
  browserless.mjs screenshot --url-page URL --output FILE [--full-page] [--type png|jpeg]
  browserless.mjs pdf --url-page URL --output FILE
  browserless.mjs content --url-page URL
  browserless.mjs debug --url-page URL [--action '{"action":"click","selector":"a"}'] [--actions-json '[...]'] [--output screenshot.png]
  browserless.mjs debug --url-page URL --script 'return await page.title()'
  browserless.mjs api --endpoint /json/version [--method GET] [--json-body '{...}'] [--output FILE]
  browserless.mjs function --file FILE
  browserless.mjs unblock --url-page URL
  browserless.mjs export --url-page URL --output FILE [--include-resources]
  browserless.mjs performance --url-page URL
  browserless.mjs session [--ttl 300000]
  browserless.mjs stop-session --stop-url URL

Common options:
  --name NAME       Saved target name from ~/.config/browserless.yaml
  --url URL         Browserless base URL; auto-saved when used with --token
  --token TOKEN     Browserless token; auto-saved when used with --url
  --default         Mark provided target as default
  --json FILE       Use an explicit JSON request body for endpoint commands
  --timeout MS      HTTP request timeout, default 60000
  --device NAME     Viewport profile: desktop (1920x1080, default) or mobile (1080x1920)
  --viewport WxH    Override viewport size, e.g. 1366x768
  --show-token      Show tokens in config list output
`);
}

function parseArgs(argv) {
  const out = { _: [] };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (!arg.startsWith('--')) {
      out._.push(arg);
      continue;
    }
    const eq = arg.indexOf('=');
    if (eq !== -1) {
      addOption(out, arg.slice(2, eq), arg.slice(eq + 1));
      continue;
    }
    const key = arg.slice(2);
    const next = argv[i + 1];
    if (next && !next.startsWith('--')) {
      addOption(out, key, next);
      i += 1;
    } else {
      addOption(out, key, true);
    }
  }
  return out;
}

function addOption(out, key, value) {
  if (Object.prototype.hasOwnProperty.call(out, key)) {
    if (!Array.isArray(out[key])) out[key] = [out[key]];
    out[key].push(value);
    return;
  }
  out[key] = value;
}

function yamlEscape(value) {
  const text = String(value ?? '');
  if (/^[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]+$/.test(text)) return text;
  return JSON.stringify(text);
}

function parseScalar(value) {
  const text = value.trim();
  if (!text) return '';
  if ((text.startsWith('"') && text.endsWith('"')) || (text.startsWith("'") && text.endsWith("'"))) {
    try {
      return JSON.parse(text);
    } catch {
      return text.slice(1, -1);
    }
  }
  return text;
}

function defaultConfig() {
  return { default: '', targets: [] };
}

function readConfig() {
  if (!fs.existsSync(CONFIG_PATH)) return defaultConfig();
  const text = fs.readFileSync(CONFIG_PATH, 'utf8');
  const config = defaultConfig();
  let current = null;
  for (const rawLine of text.split(/\r?\n/)) {
    const line = rawLine.replace(/#.*$/, '').trimEnd();
    if (!line.trim()) continue;
    const top = line.match(/^([A-Za-z0-9_-]+):\s*(.*)$/);
    if (top && !rawLine.startsWith(' ') && !rawLine.startsWith('\t')) {
      const [, key, value] = top;
      if (key === 'default') config.default = parseScalar(value);
      if (key === 'targets') current = null;
      continue;
    }
    const item = line.match(/^\s*-\s*name:\s*(.*)$/);
    if (item) {
      current = { name: parseScalar(item[1]), url: '', token: '' };
      config.targets.push(current);
      continue;
    }
    const field = line.match(/^\s+([A-Za-z0-9_-]+):\s*(.*)$/);
    if (field && current) current[field[1]] = parseScalar(field[2]);
  }
  config.targets = config.targets.filter((target) => target.name && target.url);
  return config;
}

function writeConfig(config) {
  const dir = path.dirname(CONFIG_PATH);
  fs.mkdirSync(dir, { recursive: true });
  const lines = [];
  lines.push(`default: ${yamlEscape(config.default || '')}`);
  lines.push('targets:');
  for (const target of config.targets) {
    lines.push(`  - name: ${yamlEscape(target.name)}`);
    lines.push(`    url: ${yamlEscape(trimTrailingSlash(target.url))}`);
    lines.push(`    token: ${yamlEscape(target.token || '')}`);
  }
  fs.writeFileSync(CONFIG_PATH, `${lines.join('\n')}\n`, { encoding: 'utf8', mode: 0o600 });
}

function publicConfig(config, showToken = false) {
  return {
    path: CONFIG_PATH,
    default: config.default,
    targets: config.targets.map((target) => ({
      name: target.name,
      url: target.url,
      token: showToken ? target.token : maskToken(target.token),
    })),
  };
}

function maskToken(token) {
  if (!token) return '';
  const text = String(token);
  if (text.length <= 8) return '***';
  return `${text.slice(0, 4)}...${text.slice(-4)}`;
}

function upsertTarget(config, target, makeDefault = false) {
  if (!target.name) throw new Error('Missing target name. Provide --name NAME.');
  if (!target.url) throw new Error('Missing Browserless URL. Provide --url URL.');
  const normalized = {
    name: target.name,
    url: trimTrailingSlash(target.url),
    token: target.token || '',
  };
  const idx = config.targets.findIndex((item) => item.name === normalized.name);
  if (idx === -1) config.targets.push(normalized);
  else config.targets[idx] = { ...config.targets[idx], ...normalized };
  if (makeDefault || !config.default) config.default = normalized.name;
  writeConfig(config);
  return normalized;
}

function trimTrailingSlash(url) {
  return String(url || '').replace(/\/+$/, '');
}

function inferNameFromUrl(url) {
  try {
    return new URL(url).hostname.replace(/[^A-Za-z0-9_-]+/g, '-').replace(/^-|-$/g, '') || 'default';
  } catch {
    return 'default';
  }
}

function resolveTarget(args) {
  const config = readConfig();
  if (args.url || args.token) {
    if (!args.url || !args.token) throw new Error('Provide both --url and --token when supplying inline configuration.');
    const name = args.name || inferNameFromUrl(args.url);
    return upsertTarget(config, { name, url: args.url, token: args.token }, Boolean(args.default));
  }
  const name = args.name || config.default;
  if (!name) throw new Error(`No Browserless target configured. Add one with: node ${scriptPath()} config add --name NAME --url URL --token TOKEN --default`);
  const target = config.targets.find((item) => item.name === name);
  if (!target) throw new Error(`Browserless target '${name}' not found in ${CONFIG_PATH}.`);
  return target;
}

function scriptPath() {
  return fileURLToPath(import.meta.url);
}

function withToken(url, token) {
  const parsed = new URL(url);
  if (token) parsed.searchParams.set('token', token);
  return parsed.toString();
}

function readJsonBody(args, fallback) {
  if (!args.json) return fallback;
  return JSON.parse(fs.readFileSync(args.json, 'utf8'));
}

function resolveViewport(args) {
  const device = String(args.device || 'desktop').toLowerCase();
  const base = VIEWPORT_PROFILES[device];
  if (!base) throw new Error(`Unknown --device '${args.device}'. Use desktop or mobile.`);
  const viewport = { ...base };
  if (args.viewport) {
    const match = String(args.viewport).toLowerCase().replace('×', 'x').match(/^(\d+)x(\d+)$/);
    if (!match) throw new Error(`Invalid --viewport '${args.viewport}'. Use WIDTHxHEIGHT, e.g. 1920x1080.`);
    viewport.width = Number(match[1]);
    viewport.height = Number(match[2]);
  }
  if (args.width) viewport.width = Number(args.width);
  if (args.height) viewport.height = Number(args.height);
  if (!Number.isInteger(viewport.width) || !Number.isInteger(viewport.height) || viewport.width <= 0 || viewport.height <= 0) {
    throw new Error(`Invalid viewport size ${viewport.width}x${viewport.height}.`);
  }
  if (args['device-scale-factor']) viewport.deviceScaleFactor = Number(args['device-scale-factor']);
  return viewport;
}

function withDefaultViewport(body, args) {
  if (args['no-default-viewport']) return body;
  if (!body || typeof body !== 'object' || Array.isArray(body)) return body;
  if (!Object.prototype.hasOwnProperty.call(body, 'url')) return body;
  if (body.viewport) return body;
  return { ...body, viewport: resolveViewport(args) };
}

function normalizeEndpoint(endpoint) {
  if (!endpoint) throw new Error('Missing --endpoint for api.');
  if (/^https?:\/\//i.test(endpoint)) throw new Error('Use a Browserless endpoint path like /json/version, not a full URL.');
  return endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
}

function readApiBody(args) {
  if (args['json-body']) {
    return { body: JSON.stringify(withDefaultViewport(JSON.parse(args['json-body']), args)), contentType: 'application/json' };
  }
  if (args.json) {
    return { body: JSON.stringify(withDefaultViewport(JSON.parse(fs.readFileSync(args.json, 'utf8')), args)), contentType: 'application/json' };
  }
  if (args.body) {
    return { body: String(args.body), contentType: args['content-type'] || 'text/plain' };
  }
  if (args['body-file']) {
    return { body: fs.readFileSync(args['body-file']), contentType: args['content-type'] || 'application/octet-stream' };
  }
  return { body: undefined, contentType: args['content-type'] || 'application/json' };
}

function jsonSelectors(args) {
  const selectors = args.selector ? (Array.isArray(args.selector) ? args.selector : [args.selector]) : [];
  return selectors.map((selector) => ({ selector }));
}

function requireOption(args, key, command) {
  if (!args[key]) throw new Error(`Missing --${key} for ${command}.`);
  return args[key];
}

function remotePageUrl(args, command) {
  const pageUrl = requireOption(args, 'url-page', command);
  assertRemotePageUrl(pageUrl);
  return pageUrl;
}

function assertRemotePageUrl(rawUrl) {
  let parsed;
  try {
    parsed = new URL(rawUrl);
  } catch {
    throw new Error(`Invalid page URL: ${rawUrl}`);
  }
  if (!['http:', 'https:'].includes(parsed.protocol)) {
    throw new Error(`Browserless can only debug remote HTTP(S) pages. Refusing '${parsed.protocol}' URL: ${rawUrl}`);
  }
  const hostname = parsed.hostname.toLowerCase();
  if (isLocalOrPrivateHost(hostname)) {
    throw new Error(`Browserless runs in a remote browser and cannot debug local/private pages. Refusing URL: ${rawUrl}`);
  }
}

function isLocalOrPrivateHost(hostname) {
  const host = hostname.replace(/^\[|\]$/g, '');
  if (!host) return true;
  if (host === 'localhost' || host.endsWith('.localhost')) return true;
  if (host === 'host.docker.internal' || host.endsWith('.local') || host.endsWith('.localdomain')) return true;
  if (!host.includes('.') && !host.includes(':')) return true;
  const ipv4 = parseIpv4(host);
  if (ipv4) return isPrivateOrReservedIpv4(ipv4);
  if (host.includes(':')) return isPrivateOrReservedIpv6(host);
  return false;
}

function parseIpv4(host) {
  const parts = host.split('.');
  if (parts.length !== 4) return null;
  const nums = parts.map((part) => {
    if (!/^\d+$/.test(part)) return Number.NaN;
    const value = Number(part);
    return value >= 0 && value <= 255 ? value : Number.NaN;
  });
  return nums.some(Number.isNaN) ? null : nums;
}

function isPrivateOrReservedIpv4([a, b]) {
  if (a === 0 || a === 10 || a === 127) return true;
  if (a === 100 && b >= 64 && b <= 127) return true;
  if (a === 169 && b === 254) return true;
  if (a === 172 && b >= 16 && b <= 31) return true;
  if (a === 192 && b === 168) return true;
  if (a === 192 && b === 0) return true;
  if (a === 192 && b === 88) return true;
  if (a === 198 && (b === 18 || b === 19)) return true;
  if (a >= 224) return true;
  return false;
}

function isPrivateOrReservedIpv6(host) {
  const normalized = host.toLowerCase();
  return normalized === '::1'
    || normalized === '::'
    || normalized.startsWith('fc')
    || normalized.startsWith('fd')
    || normalized.startsWith('fe80:')
    || normalized.startsWith('fec0:')
    || normalized.startsWith('::ffff:127.')
    || normalized.startsWith('::ffff:10.')
    || normalized.startsWith('::ffff:192.168.')
    || /^::ffff:172\.(1[6-9]|2\d|3[0-1])\./.test(normalized);
}

async function request(target, endpoint, { method = 'GET', body, contentType = 'application/json', timeout = 60000 } = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  const url = withToken(`${trimTrailingSlash(target.url)}${endpoint}`, target.token);
  try {
    const response = await fetch(url, {
      method,
      headers: body === undefined ? undefined : { 'Content-Type': contentType },
      body,
      signal: controller.signal,
    });
    const buffer = Buffer.from(await response.arrayBuffer());
    if (!response.ok) {
      const preview = buffer.toString('utf8', 0, Math.min(buffer.length, 1000));
      throw new Error(`Browserless ${method} ${endpoint} failed: HTTP ${response.status}\n${preview}`);
    }
    return { response, buffer };
  } finally {
    clearTimeout(timer);
  }
}

function printBuffer(buffer, contentType) {
  const textLike = !contentType || /json|text|html|javascript|xml/.test(contentType);
  if (textLike) console.log(buffer.toString('utf8'));
  else process.stdout.write(buffer);
}

async function writeOutputOrPrint(result, args) {
  if (args.output) {
    fs.writeFileSync(args.output, result.buffer);
    console.log(`Saved ${result.buffer.length} bytes to ${args.output}`);
    return;
  }
  printBuffer(result.buffer, result.response.headers.get('content-type') || '');
}

function buildBody(command, args) {
  if (args.json) return withDefaultViewport(readJsonBody(args, {}), args);
  if (command === 'scrape') {
    return withDefaultViewport({
      url: remotePageUrl(args, command),
      elements: jsonSelectors(args),
      gotoOptions: { waitUntil: args.waitUntil || 'networkidle2', timeout: Number(args.gotoTimeout || 30000) },
    }, args);
  }
  if (command === 'screenshot') {
    return withDefaultViewport({
      url: remotePageUrl(args, command),
      options: { fullPage: Boolean(args['full-page']), type: args.type || 'png' },
      ...(args.selector ? { selector: args.selector } : {}),
    }, args);
  }
  if (command === 'pdf') {
    return withDefaultViewport({
      url: remotePageUrl(args, command),
      options: { format: args.format || 'A4', printBackground: args.printBackground !== false },
    }, args);
  }
  if (command === 'content') return withDefaultViewport({ url: remotePageUrl(args, command), gotoOptions: { waitUntil: args.waitUntil || 'networkidle0' } }, args);
  if (command === 'unblock') return withDefaultViewport({ url: remotePageUrl(args, command), browserWSEndpoint: false, cookies: false, content: true, screenshot: false }, args);
  if (command === 'export') return withDefaultViewport({ url: remotePageUrl(args, command), includeResources: Boolean(args['include-resources']) }, args);
  if (command === 'performance') return withDefaultViewport({ url: remotePageUrl(args, command) }, args);
  if (command === 'session') return { ttl: Number(args.ttl || 300000), stealth: Boolean(args.stealth), headless: args.headless !== false };
  throw new Error(`Unsupported body command: ${command}`);
}

function readDebugActions(args) {
  const actions = [];
  if (args['actions-json']) {
    const parsed = JSON.parse(args['actions-json']);
    actions.push(...normalizeDebugActions(parsed, '--actions-json'));
  }
  if (args.action) {
    const inlineActions = Array.isArray(args.action) ? args.action : [args.action];
    for (const value of inlineActions) actions.push(...normalizeDebugActions(JSON.parse(value), '--action'));
  }
  if (args.actions) {
    const parsed = JSON.parse(fs.readFileSync(args.actions, 'utf8'));
    actions.push(...normalizeDebugActions(parsed, '--actions'));
  }
  validateDebugActions(actions);
  return actions;
}

function readDebugScript(args) {
  const parts = [];
  if (args['script-file']) parts.push(fs.readFileSync(args['script-file'], 'utf8'));
  if (args.script) {
    const scripts = Array.isArray(args.script) ? args.script : [args.script];
    parts.push(...scripts.map(String));
  }
  return parts.join('\n');
}

function normalizeDebugActions(parsed, source) {
  const actions = Array.isArray(parsed) ? parsed : parsed.actions ? parsed.actions : [parsed];
  if (!Array.isArray(actions)) throw new Error('Debug actions file must be a JSON array or an object with an actions array.');
  if (!actions.every((action) => action && typeof action === 'object' && !Array.isArray(action))) {
    throw new Error(`${source} must contain action objects.`);
  }
  return actions;
}

function validateDebugActions(actions) {
  for (const action of actions) {
    const actionName = action.action || action.type;
    if ((actionName === 'goto' || actionName === 'navigate') && action.url) assertRemotePageUrl(action.url);
  }
}

function createDebugFunctionSource(args) {
  const debugScript = readDebugScript(args);
  const config = {
    url: remotePageUrl(args, 'debug'),
    actions: readDebugActions(args),
    scriptBase64: Buffer.from(debugScript, 'utf8').toString('base64'),
    viewport: resolveViewport(args),
    waitUntil: args.waitUntil || 'networkidle2',
    gotoTimeout: Number(args.gotoTimeout || 45000),
    selector: args.selector || '',
    selectorTimeout: Number(args.selectorTimeout || 10000),
    maxText: Number(args.maxText || 2000),
    maxElements: Number(args.maxElements || 40),
    maxEvents: Number(args.maxEvents || 40),
    includeScreenshot: Boolean(args.output || args.screenshot),
  };
  return `const config = ${JSON.stringify(config)};

export default async ({ page }) => {
  const consoleMessages = [];
  const pageErrors = [];
  const failedRequests = [];
  const errorResponses = [];
  const pushLimited = (list, item) => {
    if (list.length < config.maxEvents) list.push(item);
  };

  page.on('console', (message) => {
    pushLimited(consoleMessages, {
      type: message.type(),
      text: message.text(),
      location: typeof message.location === 'function' ? message.location() : undefined,
    });
  });
  page.on('pageerror', (error) => {
    pushLimited(pageErrors, { message: error.message, stack: error.stack });
  });
  page.on('requestfailed', (request) => {
    const failure = request.failure();
    pushLimited(failedRequests, {
      method: request.method(),
      url: request.url(),
      failure: failure ? failure.errorText : 'unknown',
    });
  });
  page.on('response', (response) => {
    const status = response.status();
    if (status >= 400) {
      pushLimited(errorResponses, { status, statusText: response.statusText(), url: response.url() });
    }
  });

  const decodeBase64 = (value) => {
    if (!value) return '';
    if (typeof Buffer !== 'undefined') return Buffer.from(value, 'base64').toString('utf8');
    if (typeof atob !== 'undefined') return decodeURIComponent(escape(atob(value)));
    throw new Error('No base64 decoder available in Browserless function runtime.');
  };

  const assertRemoteUrl = (rawUrl) => {
    const parsed = new URL(rawUrl);
    if (!['http:', 'https:'].includes(parsed.protocol)) throw new Error('Only remote HTTP(S) URLs are allowed: ' + rawUrl);
    const host = parsed.hostname.toLowerCase().replace(/^\\[|\\]$/g, '');
    const isPrivateIpv4 = (value) => {
      const parts = value.split('.').map(Number);
      if (parts.length !== 4 || parts.some((part) => !Number.isInteger(part) || part < 0 || part > 255)) return false;
      const [a, b] = parts;
      return a === 0 || a === 10 || a === 127 || (a === 100 && b >= 64 && b <= 127) || (a === 169 && b === 254) || (a === 172 && b >= 16 && b <= 31) || (a === 192 && b === 168) || a >= 224;
    };
    if (!host || host === 'localhost' || host.endsWith('.localhost') || host.endsWith('.local') || host === 'host.docker.internal') throw new Error('Local/private URLs are not allowed: ' + rawUrl);
    if (!host.includes('.') && !host.includes(':')) throw new Error('Single-label intranet hosts are not allowed: ' + rawUrl);
    if (isPrivateIpv4(host)) throw new Error('Private IP URLs are not allowed: ' + rawUrl);
    if (host === '::1' || host === '::' || host.startsWith('fc') || host.startsWith('fd') || host.startsWith('fe80:')) throw new Error('Private IPv6 URLs are not allowed: ' + rawUrl);
  };

  const originalGoto = page.goto.bind(page);
  page.goto = async (url, options) => {
    assertRemoteUrl(url);
    return originalGoto(url, options);
  };

  const summarizeAction = (action) => {
    const summary = { ...action };
    if (Object.prototype.hasOwnProperty.call(summary, 'text')) summary.text = '[' + String(summary.text).length + ' chars]';
    if (Object.prototype.hasOwnProperty.call(summary, 'value')) summary.value = '[' + String(summary.value).length + ' chars]';
    return summary;
  };

  const runActions = async (actions) => {
    const results = [];
    for (let index = 0; index < actions.length; index += 1) {
      const action = actions[index] || {};
      const actionName = action.action || action.type;
      const started = Date.now();
      const result = { index, action: actionName, input: summarizeAction(action), ok: false, elapsedMs: 0 };
      try {
        if (!actionName) throw new Error('Missing action/type field.');
        if (actionName === 'wait') {
          await new Promise((resolve) => setTimeout(resolve, Number(action.ms || 1000)));
        } else if (actionName === 'waitForSelector') {
          if (!action.selector) throw new Error('waitForSelector requires selector.');
          await page.waitForSelector(action.selector, { timeout: Number(action.timeout || config.selectorTimeout) });
        } else if (actionName === 'click') {
          if (!action.selector) throw new Error('click requires selector.');
          await page.waitForSelector(action.selector, { timeout: Number(action.timeout || config.selectorTimeout) });
          if (action.waitForNavigation) {
            const navigation = page.waitForNavigation({ waitUntil: action.waitUntil || config.waitUntil, timeout: Number(action.navigationTimeout || config.gotoTimeout) })
              .then((response) => response ? { status: response.status(), url: response.url() } : null)
              .catch((error) => ({ error: error.message }));
            await page.click(action.selector, { delay: Number(action.delay || 0) });
            result.navigation = await navigation;
          } else {
            await page.click(action.selector, { delay: Number(action.delay || 0) });
          }
        } else if (actionName === 'type') {
          if (!action.selector) throw new Error('type requires selector.');
          await page.waitForSelector(action.selector, { timeout: Number(action.timeout || config.selectorTimeout) });
          if (action.clear) {
            await page.$eval(action.selector, (element) => {
              element.focus();
              if ('value' in element) element.value = '';
              else element.textContent = '';
              element.dispatchEvent(new Event('input', { bubbles: true }));
              element.dispatchEvent(new Event('change', { bubbles: true }));
            });
          }
          await page.type(action.selector, String(action.text || ''), { delay: Number(action.delay || 0) });
        } else if (actionName === 'press') {
          if (action.selector) await page.click(action.selector);
          if (!action.key) throw new Error('press requires key.');
          await page.keyboard.press(action.key, { delay: Number(action.delay || 0) });
        } else if (actionName === 'select') {
          if (!action.selector) throw new Error('select requires selector.');
          const values = Array.isArray(action.values) ? action.values : [action.value];
          result.selected = await page.select(action.selector, ...values.filter((value) => value !== undefined).map(String));
        } else if (actionName === 'check' || actionName === 'uncheck') {
          if (!action.selector) throw new Error(actionName + ' requires selector.');
          const shouldCheck = actionName === 'check';
          await page.waitForSelector(action.selector, { timeout: Number(action.timeout || config.selectorTimeout) });
          const checkedBefore = await page.$eval(action.selector, (element) => Boolean(element.checked));
          if (checkedBefore !== shouldCheck) await page.click(action.selector);
          result.checked = shouldCheck;
        } else if (actionName === 'hover') {
          if (!action.selector) throw new Error('hover requires selector.');
          await page.hover(action.selector);
        } else if (actionName === 'scroll') {
          await page.evaluate((x, y) => window.scrollBy(x, y), Number(action.x || 0), Number(action.y || 0));
        } else if (actionName === 'evaluate') {
          if (action.expression) {
            result.value = await page.evaluate((source) => Function('return (' + source + ')')(), String(action.expression));
          } else if (action.script) {
            result.value = await page.evaluate((source) => Function(source)(), String(action.script));
          } else {
            throw new Error('evaluate requires expression or script.');
          }
        } else if (actionName === 'goto' || actionName === 'navigate') {
          if (!action.url) throw new Error(actionName + ' requires url.');
          const response = await page.goto(action.url, { waitUntil: action.waitUntil || config.waitUntil, timeout: Number(action.timeout || config.gotoTimeout) });
          result.navigation = response ? { status: response.status(), url: response.url() } : null;
        } else {
          throw new Error('Unsupported debug action: ' + actionName);
        }
        result.ok = true;
      } catch (error) {
        result.error = { message: error.message, stack: error.stack };
      }
      result.elapsedMs = Date.now() - started;
      results.push(result);
      if (!result.ok && !action.continueOnError) break;
    }
    return results;
  };

  const collectSnapshot = async () => page.evaluate((maxText, maxElements) => {
    const bySelector = (selector) => document.querySelectorAll(selector).length;
    const cssEscape = (value) => {
      if (window.CSS && typeof window.CSS.escape === 'function') return window.CSS.escape(value);
      return String(value).replace(/[^a-zA-Z0-9_-]/g, (char) => '\\\\' + char);
    };
    const attrSelector = (tag, name, value) => tag + '[' + name + '=' + JSON.stringify(value) + ']';
    const selectorFor = (element) => {
      const tag = element.tagName.toLowerCase();
      if (element.id) return '#' + cssEscape(element.id);
      for (const attr of ['data-testid', 'data-test', 'data-cy', 'name', 'aria-label', 'title']) {
        const value = element.getAttribute(attr);
        if (value) return attrSelector(tag, attr, value);
      }
      const parts = [];
      let current = element;
      while (current && current.nodeType === Node.ELEMENT_NODE && current !== document.body && parts.length < 5) {
        const currentTag = current.tagName.toLowerCase();
        const parent = current.parentElement;
        if (!parent) break;
        const siblings = Array.from(parent.children).filter((child) => child.tagName === current.tagName);
        const index = siblings.indexOf(current) + 1;
        parts.unshift(siblings.length > 1 ? currentTag + ':nth-of-type(' + index + ')' : currentTag);
        current = parent;
      }
      return parts.length ? parts.join(' > ') : tag;
    };
    const visible = (element) => {
      const style = getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      return style.visibility !== 'hidden' && style.display !== 'none' && rect.width > 0 && rect.height > 0;
    };
    const describeElement = (element) => {
      const rect = element.getBoundingClientRect();
      return {
        selector: selectorFor(element),
        tag: element.tagName.toLowerCase(),
        type: element.getAttribute('type') || '',
        role: element.getAttribute('role') || '',
        name: element.getAttribute('name') || '',
        ariaLabel: element.getAttribute('aria-label') || '',
        placeholder: element.getAttribute('placeholder') || '',
        href: element.href || '',
        text: (element.innerText || element.value || element.getAttribute('value') || '').replace(/\\s+/g, ' ').trim().slice(0, 120),
        visible: visible(element),
        disabled: Boolean(element.disabled || element.getAttribute('aria-disabled') === 'true'),
        box: { x: Math.round(rect.x), y: Math.round(rect.y), width: Math.round(rect.width), height: Math.round(rect.height) },
      };
    };
    const interactiveSelector = 'a[href],button,input,textarea,select,[role="button"],[role="link"],[onclick],summary,[contenteditable="true"]';
    const interactiveElements = Array.from(document.querySelectorAll(interactiveSelector))
      .filter(visible)
      .slice(0, maxElements)
      .map(describeElement);
    return {
      readyState: document.readyState,
      title: document.title,
      finalUrl: location.href,
      lang: document.documentElement ? document.documentElement.lang : '',
      charset: document.characterSet,
      counts: {
        links: bySelector('a[href]'),
        images: bySelector('img'),
        scripts: bySelector('script'),
        stylesheets: bySelector('link[rel~="stylesheet"]'),
        forms: bySelector('form'),
        inputs: bySelector('input, textarea, select, button'),
        headings: bySelector('h1,h2,h3,h4,h5,h6'),
        interactive: interactiveElements.length,
      },
      h1: Array.from(document.querySelectorAll('h1')).slice(0, 5).map((el) => el.innerText.trim()).filter(Boolean),
      interactiveElements,
      textSample: (document.body && document.body.innerText ? document.body.innerText : '').replace(/\\s+/g, ' ').trim().slice(0, maxText),
    };
  }, config.maxText, config.maxElements).catch((error) => ({ evaluateError: error.message }));

  const startedAt = Date.now();
  let mainResponse = null;
  let navigationError = null;
  try {
    await page.setViewport(config.viewport);
    const response = await page.goto(config.url, { waitUntil: config.waitUntil, timeout: config.gotoTimeout });
    if (response) {
      mainResponse = {
        status: response.status(),
        statusText: response.statusText(),
        ok: response.ok(),
        url: response.url(),
      };
    }
  } catch (error) {
    navigationError = { message: error.message, stack: error.stack };
  }

  let selectorFound = null;
  if (config.selector) {
    try {
      await page.waitForSelector(config.selector, { timeout: config.selectorTimeout });
      selectorFound = true;
    } catch {
      selectorFound = false;
    }
  }

  const actionResults = await runActions(config.actions || []);
  let scriptResult = null;
  const debugScript = decodeBase64(config.scriptBase64);
  if (debugScript) {
    const started = Date.now();
    try {
      const run = new Function('page', 'config', 'actionResults', 'assertRemoteUrl', 'return (async () => {\\n' + debugScript + '\\n})()');
      scriptResult = { ok: true, elapsedMs: Date.now() - started, value: await run(page, config, actionResults, assertRemoteUrl) };
    } catch (error) {
      scriptResult = { ok: false, elapsedMs: Date.now() - started, error: { message: error.message, stack: error.stack } };
    }
  }
  const pageSnapshot = await collectSnapshot();

  const metrics = typeof page.metrics === 'function' ? await page.metrics().catch(() => null) : null;
  let screenshotBase64 = null;
  if (config.includeScreenshot) {
    screenshotBase64 = await page.screenshot({ type: 'png', fullPage: true, encoding: 'base64' }).catch(() => null);
  }

  return {
    data: {
      requestedUrl: config.url,
      finalUrl: pageSnapshot.finalUrl || page.url(),
      elapsedMs: Date.now() - startedAt,
      mainResponse,
      navigationError,
      actions: actionResults,
      script: scriptResult,
      viewport: config.viewport,
      selector: config.selector ? { value: config.selector, found: selectorFound } : null,
      page: pageSnapshot,
      consoleMessages,
      pageErrors,
      failedRequests,
      errorResponses,
      metrics,
      screenshotBase64,
    },
    type: 'application/json',
  };
};`;
}

function parseDebugReport(buffer) {
  const parsed = JSON.parse(buffer.toString('utf8'));
  return parsed && parsed.data && parsed.type ? parsed.data : parsed;
}

function outputDebugReport(report, args) {
  const output = { ...report };
  if (output.screenshotBase64 && args.output) {
    fs.writeFileSync(args.output, Buffer.from(output.screenshotBase64, 'base64'));
    output.screenshotPath = args.output;
  }
  if (!args['include-screenshot-base64']) delete output.screenshotBase64;
  console.log(JSON.stringify(output, null, 2));
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const [command, subcommand] = args._;
  if (!command || args.help) {
    printUsage();
    return;
  }

  if (command === 'config') {
    const config = readConfig();
    if (subcommand === 'list') {
      console.log(JSON.stringify(publicConfig(config, Boolean(args['show-token'])), null, 2));
      return;
    }
    if (subcommand === 'add') {
      const target = upsertTarget(config, {
        name: requireOption(args, 'name', 'config add'),
        url: requireOption(args, 'url', 'config add'),
        token: requireOption(args, 'token', 'config add'),
      }, Boolean(args.default));
      console.log(`Saved Browserless target '${target.name}' to ${CONFIG_PATH}`);
      return;
    }
    if (subcommand === 'remove') {
      const name = requireOption(args, 'name', 'config remove');
      const before = config.targets.length;
      config.targets = config.targets.filter((target) => target.name !== name);
      if (before === config.targets.length) throw new Error(`Browserless target '${name}' not found.`);
      if (config.default === name) config.default = config.targets[0]?.name || '';
      writeConfig(config);
      console.log(`Removed Browserless target '${name}' from ${CONFIG_PATH}`);
      return;
    }
    if (subcommand === 'default') {
      const name = requireOption(args, 'name', 'config default');
      if (!config.targets.some((target) => target.name === name)) throw new Error(`Browserless target '${name}' not found.`);
      config.default = name;
      writeConfig(config);
      console.log(`Set default Browserless target to '${name}' in ${CONFIG_PATH}`);
      return;
    }
    throw new Error('Unknown config command. Use config list, config add, config remove, or config default.');
  }

  if (command === 'stop-session') {
    const stopUrl = requireOption(args, 'stop-url', command);
    const response = await fetch(stopUrl, { method: 'DELETE' });
    const text = await response.text();
    if (!response.ok) throw new Error(`Stop session failed: HTTP ${response.status}\n${text}`);
    console.log(text);
    return;
  }

  const target = resolveTarget(args);
  const timeout = Number(args.timeout || 60000);

  if (command === 'version') {
    await writeOutputOrPrint(await request(target, '/json/version', { timeout }), args);
    return;
  }
  if (command === 'sessions') {
    await writeOutputOrPrint(await request(target, '/sessions', { timeout }), args);
    return;
  }
  if (command === 'function') {
    const file = requireOption(args, 'file', command);
    const source = fs.readFileSync(file, 'utf8');
    await writeOutputOrPrint(await request(target, '/function', { method: 'POST', body: source, contentType: 'application/javascript', timeout }), args);
    return;
  }
  if (command === 'debug') {
    const source = createDebugFunctionSource(args);
    if (args['dump-source']) {
      console.log(source);
      return;
    }
    const result = await request(target, '/function', { method: 'POST', body: source, contentType: 'application/javascript', timeout });
    outputDebugReport(parseDebugReport(result.buffer), args);
    return;
  }
  if (command === 'api') {
    const { body, contentType } = readApiBody(args);
    const method = String(args.method || (body === undefined ? 'GET' : 'POST')).toUpperCase();
    await writeOutputOrPrint(await request(target, normalizeEndpoint(args.endpoint), { method, body, contentType, timeout }), args);
    return;
  }

  const endpoints = {
    scrape: '/scrape',
    screenshot: '/screenshot',
    pdf: '/pdf',
    content: '/content',
    unblock: '/unblock',
    export: '/export',
    performance: '/performance',
    session: '/session',
  };
  if (!endpoints[command]) throw new Error(`Unknown command: ${command}`);
  const body = JSON.stringify(buildBody(command, args));
  await writeOutputOrPrint(await request(target, endpoints[command], { method: 'POST', body, timeout }), args);
}

main().catch((error) => {
  console.error(`Error: ${error.message}`);
  process.exit(1);
});
