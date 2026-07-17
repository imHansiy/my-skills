#!/usr/bin/env node
/**
 * China Telecom intelligent gateway (LuCI) login + port mapping CLI.
 * Confirmed against ZXHN F4600T UI at /cgi-bin/luci.
 *
 * LLM-friendly stdout: JSON on --json / short status lines otherwise.
 * Never print passwords. Tokens/cookies only with --debug.
 */

import { createInterface } from "node:readline";
import { homedir } from "node:os";
import { join } from "node:path";
import { mkdir, readFile, writeFile, access } from "node:fs/promises";
import { constants as fsConstants } from "node:fs";

const DEFAULT_BASE = "http://192.168.1.1";
const DEFAULT_USER = "useradmin";
const CONFIG_DIR = join(homedir(), ".config");
const CONFIG_PATH = join(CONFIG_DIR, "telecom-gateway.yaml");

function usage() {
  return `Usage:
  node gateway-portmap.mjs <command> [options]

Commands:
  config show                          Show saved config status (no password value)
  config set                           Save defaults under ~/.config/telecom-gateway.yaml
    [--base-url URL] [--username USER] [--password PASS | --password-stdin]
  list
  add --name NAME --client IP --protocol TCP|UDP|BOTH --ex-port N --in-port N
  enable --name NAME
  disable --name NAME
  del --name NAME --yes
  enable-all
  disable-all
  info

Config (required before gateway ops):
  ${CONFIG_PATH}
  Must contain username + password (baseUrl defaults to ${DEFAULT_BASE}).
  If missing/empty, agent must ask the user once, then run config set.

Global options:
  --base-url URL          Gateway origin (default ${DEFAULT_BASE})
  --username USER         Login username (default ${DEFAULT_USER})
  --password PASS         Prefer saved config, TELECOM_GATEWAY_PASSWORD, or --password-stdin
  --password-stdin        Read password from stdin
  --config PATH           Config yaml path (default ${CONFIG_PATH})
  --json                  Machine-readable output (default for most commands)
  --debug                 Include cookie/token flags in JSON (still no password)
  --help
`;
}

function fail(msg, code = 1) {
  process.stderr.write(`Error: ${msg}\n`);
  process.exit(code);
}

/** Exit 2 + JSON so agents know to prompt the user and save config. */
function needConfig(configPath, missing, extra = {}) {
  const payload = {
    needConfig: true,
    path: configPath,
    missing,
    message:
      "Gateway credentials are not saved. Ask the user for router username and password (and baseUrl if not default), then run: node gateway-portmap.mjs config set --username <user> --password-stdin",
    ...extra,
  };
  process.stdout.write(JSON.stringify(payload, null, 2) + "\n");
  process.exit(2);
}

function configStatus(cfg, configPath, flags = {}) {
  const baseUrl = flags["base-url"] || cfg.baseUrl || DEFAULT_BASE;
  const username = flags.username || cfg.username || "";
  const hasPassword = Boolean(
    flags.password ||
      flags.passwordStdin ||
      process.env.TELECOM_GATEWAY_PASSWORD ||
      (cfg.password && String(cfg.password).length > 0)
  );
  const missing = [];
  if (!username) missing.push("username");
  if (!hasPassword) missing.push("password");
  return {
    path: configPath,
    exists: Object.keys(cfg).length > 0,
    ready: missing.length === 0,
    missing,
    baseUrl,
    username: username || null,
    hasPassword,
    envPassword: Boolean(process.env.TELECOM_GATEWAY_PASSWORD),
    defaults: { baseUrl: DEFAULT_BASE, username: DEFAULT_USER },
  };
}

function parseArgs(argv) {
  const args = { _: [], flags: {} };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--help" || a === "-h") args.flags.help = true;
    else if (a === "--json") args.flags.json = true;
    else if (a === "--debug") args.flags.debug = true;
    else if (a === "--yes") args.flags.yes = true;
    else if (a === "--password-stdin") args.flags.passwordStdin = true;
    else if (a.startsWith("--")) {
      const key = a.slice(2);
      const val = argv[i + 1];
      if (val == null || val.startsWith("--")) fail(`Missing value for ${a}`);
      args.flags[key] = val;
      i++;
    } else args._.push(a);
  }
  return args;
}

async function readStdinLine() {
  const rl = createInterface({ input: process.stdin, terminal: false });
  return new Promise((resolve) => {
    let data = "";
    rl.on("line", (line) => {
      data = line;
      rl.close();
    });
    rl.on("close", () => resolve(data));
  });
}

/** Minimal YAML subset: key: value lines only */
function parseSimpleYaml(text) {
  const out = {};
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim();
    if (!line || line.startsWith("#")) continue;
    const m = line.match(/^([A-Za-z0-9_-]+)\s*:\s*(.*)$/);
    if (!m) continue;
    let v = m[2].trim();
    if (
      (v.startsWith('"') && v.endsWith('"')) ||
      (v.startsWith("'") && v.endsWith("'"))
    ) {
      v = v.slice(1, -1);
    }
    out[m[1]] = v;
  }
  return out;
}

function toSimpleYaml(obj) {
  return (
    Object.entries(obj)
      .filter(([, v]) => v != null && v !== "")
      .map(([k, v]) => `${k}: ${String(v).includes(":") ? JSON.stringify(v) : v}`)
      .join("\n") + "\n"
  );
}

async function loadConfig(path) {
  try {
    await access(path, fsConstants.R_OK);
    const text = await readFile(path, "utf8");
    return parseSimpleYaml(text);
  } catch {
    return {};
  }
}

async function saveConfig(path, data) {
  await mkdir(CONFIG_DIR, { recursive: true });
  await writeFile(path, toSimpleYaml(data), "utf8");
}

function joinUrl(base, path) {
  const b = base.replace(/\/+$/, "");
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${b}${p}`;
}

function extractToken(html) {
  const m =
    html.match(/token:\s*['"]([a-f0-9]{16,})['"]/i) ||
    html.match(/token\s*=\s*['"]([a-f0-9]{16,})['"]/i);
  return m ? m[1] : null;
}

function extractSetCookie(res) {
  // Node fetch: getSetCookie if available
  if (typeof res.headers.getSetCookie === "function") {
    return res.headers.getSetCookie();
  }
  const single = res.headers.get("set-cookie");
  return single ? [single] : [];
}

function parseSysauth(setCookies) {
  for (const c of setCookies) {
    const m = c.match(/sysauth=([^;]+)/);
    if (m) return m[1];
  }
  return null;
}

class GatewayClient {
  constructor({ baseUrl, username, password, debug }) {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
    this.username = username;
    this.password = password;
    this.debug = debug;
    this.sysauth = null;
    this.token = null;
  }

  cookieHeader() {
    return this.sysauth ? `sysauth=${this.sysauth}` : "";
  }

  async request(method, path, { body, form, headers = {} } = {}) {
    const url = joinUrl(this.baseUrl, path);
    const h = { ...headers };
    if (this.sysauth) h.Cookie = this.cookieHeader();
    let payload;
    if (form) {
      h["Content-Type"] = "application/x-www-form-urlencoded";
      payload = new URLSearchParams(form).toString();
    } else if (body != null) {
      payload = body;
    }
    const res = await fetch(url, {
      method,
      headers: h,
      body: payload,
      redirect: "manual",
    });
    const text = await res.text();
    return { res, text, url };
  }

  isLoginHtml(text) {
    return (
      /<!DOCTYPE/i.test(text) &&
      (/login_username/i.test(text) || /确认登录/.test(text))
    );
  }

  async login() {
    const { res, text } = await this.request("POST", "/cgi-bin/luci", {
      form: { username: this.username, psd: this.password },
    });
    const setCookies = extractSetCookie(res);
    let auth = parseSysauth(setCookies);

    // Some firmwares set cookie on redirect target
    if (!auth && (res.status === 302 || res.status === 301)) {
      const loc = res.headers.get("location") || "/cgi-bin/luci/";
      const path = loc.startsWith("http")
        ? new URL(loc).pathname + new URL(loc).search
        : loc;
      const follow = await this.request("GET", path, {
        headers: setCookies.length
          ? { Cookie: setCookies.map((c) => c.split(";")[0]).join("; ") }
          : {},
      });
      auth = parseSysauth(extractSetCookie(follow.res)) || auth;
      // Also accept cookie only on follow if server re-sets
      if (!auth) {
        const m = (follow.res.headers.get("set-cookie") || "").match(
          /sysauth=([^;]+)/
        );
        if (m) auth = m[1];
      }
      // Try Cookie jar from first response manually
      if (!auth && setCookies.length) {
        const m = setCookies.join("\n").match(/sysauth=([^;]+)/);
        if (m) auth = m[1];
      }
      this.sysauth = auth;
      if (!this.sysauth) {
        // Last resort: request home with any partial cookies
        const home = await this.request("GET", "/cgi-bin/luci/", {
          headers: {
            Cookie: setCookies.map((c) => c.split(";")[0]).join("; "),
          },
        });
        auth = parseSysauth(extractSetCookie(home.res));
        this.sysauth = auth;
        if (this.sysauth) {
          this.token = extractToken(home.text);
          return;
        }
      }
    } else {
      this.sysauth = auth;
    }

    if (!this.sysauth) {
      // Some devices put sysauth only after GET /cgi-bin/luci/ with no prior jar — re-login capture failed
      fail(
        `Login failed (HTTP ${res.status}). Check username/password and base URL.`
      );
    }

    // Load admin page for CSRF token
    const admin = await this.request("GET", "/cgi-bin/luci/admin/settings/portmap_config");
    if (this.isLoginHtml(admin.text)) {
      fail("Login cookie rejected; credentials may be wrong.");
    }
    this.token = extractToken(admin.text);
    if (!this.token) {
      // try shell
      const shell = await this.request("GET", "/cgi-bin/luci/");
      this.token = extractToken(shell.text);
    }
    if (!this.token) fail("Logged in but CSRF token not found in admin HTML.");
  }

  async ensureSession() {
    if (!this.sysauth || !this.token) await this.login();
  }

  async pmDisplay() {
    await this.ensureSession();
    const { text } = await this.request(
      "GET",
      `/cgi-bin/luci/admin/settings/pmDisplay?_=${Math.random()}`
    );
    if (this.isLoginHtml(text)) {
      this.sysauth = null;
      await this.login();
      return this.pmDisplay();
    }
    try {
      return JSON.parse(text);
    } catch {
      fail(`pmDisplay returned non-JSON: ${text.slice(0, 120)}`);
    }
  }

  async pmSetSingle(fields) {
    await this.ensureSession();
    const form = {
      token: this.token,
      ...fields,
      _: String(Math.random()),
    };
    const { text } = await this.request(
      "POST",
      "/cgi-bin/luci/admin/settings/pmSetSingle",
      { form }
    );
    if (this.isLoginHtml(text) || text.trim().startsWith("<!DOCTYPE")) {
      this.sysauth = null;
      await this.login();
      return this.pmSetSingle(fields);
    }
    try {
      return JSON.parse(text);
    } catch {
      fail(`pmSetSingle returned non-JSON: ${text.slice(0, 120)}`);
    }
  }

  async pmSetAll(op) {
    await this.ensureSession();
    const { text, res } = await this.request(
      "POST",
      "/cgi-bin/luci/admin/settings/pmSetAll",
      {
        form: {
          token: this.token,
          op,
          _: String(Math.random()),
        },
      }
    );
    if (this.isLoginHtml(text)) {
      this.sysauth = null;
      await this.login();
      return this.pmSetAll(op);
    }
    if (text && text.trim()) {
      try {
        return JSON.parse(text);
      } catch {
        return { ok: res.ok, status: res.status, raw: text.slice(0, 200) };
      }
    }
    return { ok: res.ok, status: res.status };
  }

  async info() {
    await this.ensureSession();
    const { text } = await this.request(
      "GET",
      `/cgi-bin/luci/admin/settings/gwinfo?get=all&_=${Math.random()}`
    );
    if (this.isLoginHtml(text)) {
      this.sysauth = null;
      await this.login();
      return this.info();
    }
    try {
      return JSON.parse(text);
    } catch {
      fail(`gwinfo returned non-JSON: ${text.slice(0, 120)}`);
    }
  }
}

function rulesFromDisplay(json) {
  const n = Number(json.count || 0);
  const rules = [];
  for (let i = 1; i <= n; i++) {
    const r = json[`pmRule${i}`];
    if (r) rules.push(r);
  }
  return rules;
}

function print(obj, asJson) {
  if (asJson) process.stdout.write(JSON.stringify(obj, null, 2) + "\n");
  else if (typeof obj === "string") process.stdout.write(obj + "\n");
  else process.stdout.write(JSON.stringify(obj, null, 2) + "\n");
}

function isValidPort(p) {
  const n = Number(p);
  return Number.isInteger(n) && n >= 1 && n <= 65535;
}

function isValidIPv4(ip) {
  const m = String(ip).match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/);
  if (!m) return false;
  return m.slice(1).every((x) => {
    const n = Number(x);
    return n >= 0 && n <= 255;
  });
}

async function resolvePassword(flags, cfg) {
  if (flags.passwordStdin) {
    const p = (await readStdinLine()).trim();
    if (!p) fail("Empty password on stdin");
    return p;
  }
  if (flags.password) return flags.password;
  if (process.env.TELECOM_GATEWAY_PASSWORD)
    return process.env.TELECOM_GATEWAY_PASSWORD;
  if (cfg && cfg.password) return cfg.password;
  return null;
}

async function buildClient(flags, cfg, configPath) {
  const baseUrl = flags["base-url"] || cfg.baseUrl || DEFAULT_BASE;
  const username = flags.username || cfg.username || "";
  const password = await resolvePassword(flags, cfg);

  const missing = [];
  // Empty/missing file: require explicit username at least once (do not silent-default until saved).
  if (!username) missing.push("username");
  if (!password) missing.push("password");
  if (missing.length) {
    needConfig(configPath, missing, { baseUrl: baseUrl || DEFAULT_BASE });
  }

  return new GatewayClient({
    baseUrl: baseUrl || DEFAULT_BASE,
    username,
    password,
    debug: !!flags.debug,
  });
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.flags.help || args._.length === 0) {
    process.stdout.write(usage());
    process.exit(args.flags.help || args._.length === 0 ? 0 : 1);
  }

  const configPath = args.flags.config || CONFIG_PATH;
  const cfg = await loadConfig(configPath);
  const cmd = args._[0];
  const sub = args._[1];

  if (cmd === "config") {
    if (sub === "show" || sub === "status" || sub == null) {
      const status = configStatus(cfg, configPath, args.flags);
      print(status, true);
      process.exit(status.ready ? 0 : 2);
    }
    if (sub === "set") {
      const next = { ...cfg };
      if (args.flags["base-url"]) next.baseUrl = args.flags["base-url"];
      else if (!next.baseUrl) next.baseUrl = DEFAULT_BASE;

      if (args.flags.username) next.username = args.flags.username;
      if (args.flags.passwordStdin) {
        next.password = (await readStdinLine()).trim();
        if (!next.password) fail("Empty password on stdin");
      } else if (args.flags.password) {
        next.password = args.flags.password;
      }

      // First-time save must include username + password
      const missing = [];
      if (!next.username) missing.push("username");
      if (!next.password) missing.push("password");
      if (missing.length) {
        needConfig(configPath, missing, {
          hint: "config set requires --username and --password/--password-stdin when those fields are not already saved",
        });
      }
      if (!next.baseUrl) next.baseUrl = DEFAULT_BASE;

      await saveConfig(configPath, next);
      const status = configStatus(next, configPath);
      print(
        {
          ok: true,
          path: configPath,
          saved: ["baseUrl", "username", "password"].filter((k) => next[k]),
          ready: status.ready,
          // never echo password
          baseUrl: next.baseUrl,
          username: next.username,
          hasPassword: Boolean(next.password),
        },
        true
      );
      return;
    }
    fail(`Unknown config subcommand: ${sub || "(none)"}. Use: show | set`);
  }

  const client = await buildClient(args.flags, cfg, configPath);

  if (cmd === "list") {
    const data = await client.pmDisplay();
    const rules = rulesFromDisplay(data);
    const out = {
      count: data.count,
      lanIp: data.lanIp,
      mask: data.mask,
      rules,
    };
    if (args.flags.debug) {
      out._debug = { hasSysauth: !!client.sysauth, hasToken: !!client.token };
    }
    print(out, true);
    return;
  }

  if (cmd === "info") {
    const data = await client.info();
    print(data, true);
    return;
  }

  if (cmd === "add") {
    const name = args.flags.name;
    const clientIp = args.flags.client;
    const protocol = (args.flags.protocol || "TCP").toUpperCase();
    const exPort = args.flags["ex-port"];
    const inPort = args.flags["in-port"];
    if (!name) fail("--name required");
    if (!clientIp || !isValidIPv4(clientIp)) fail("--client must be a valid IPv4");
    if (!["TCP", "UDP", "BOTH"].includes(protocol))
      fail("--protocol must be TCP, UDP, or BOTH");
    if (!isValidPort(exPort)) fail("--ex-port invalid");
    if (!isValidPort(inPort)) fail("--in-port invalid");

    const before = await client.pmDisplay();
    if (clientIp === before.lanIp) fail("client IP must not equal gateway LAN IP");
    for (const r of rulesFromDisplay(before)) {
      if (r.desp === name) fail(`Rule name already exists: ${name}`);
    }

    const result = await client.pmSetSingle({
      op: "add",
      srvname: name,
      client: clientIp,
      protocol,
      exPort: String(exPort),
      inPort: String(inPort),
    });
    if (result.retVal !== 0) fail(`Add failed: ${JSON.stringify(result)}`);
    const after = await client.pmDisplay();
    print(
      {
        ok: true,
        retVal: result.retVal,
        rule: {
          desp: name,
          client: clientIp,
          protocol,
          exPort: Number(exPort),
          inPort: Number(inPort),
        },
        count: after.count,
      },
      true
    );
    return;
  }

  if (cmd === "enable" || cmd === "disable" || cmd === "del") {
    const name = args.flags.name;
    if (!name) fail("--name required");
    if (cmd === "del" && !args.flags.yes)
      fail("del requires --yes to confirm deletion");
    const op = cmd === "del" ? "del" : cmd;
    const result = await client.pmSetSingle({ op, srvname: name });
    if (result.retVal !== 0) fail(`${cmd} failed: ${JSON.stringify(result)}`);
    print({ ok: true, op, srvname: name, retVal: result.retVal }, true);
    return;
  }

  if (cmd === "enable-all" || cmd === "disable-all") {
    const op = cmd === "enable-all" ? "enable" : "disable";
    const result = await client.pmSetAll(op);
    print({ ok: true, op: `${op}-all`, result }, true);
    return;
  }

  fail(`Unknown command: ${cmd}\n\n${usage()}`);
}

main().catch((e) => {
  fail(e && e.message ? e.message : String(e));
});
