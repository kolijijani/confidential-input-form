#!/usr/bin/env python3
"""Build the Secret Vault docs site into docs/*.html.

Source of truth for wording: README.md. This generator keeps navigation, <head> metadata,
JSON-LD and the sitemap identical across pages, so a copy change is one edit here.
Run from the repository root:  python3 scripts/build_docs.py
"""
import datetime
import html
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SITE = "https://kolijijani.github.io/secret-vault"
REPO = "https://github.com/kolijijani/secret-vault"
VERSION = re.search(r'version\s*=\s*"([^"]+)"', (ROOT / "pyproject.toml").read_text()).group(1)
TODAY = datetime.date.today().isoformat()

NAV = [
    ("index.html", "overview"),
    ("install.html", "install"),
    ("usage.html", "usage"),
    ("agents.html", "agents"),
    ("security.html", "security"),
    ("faq.html", "faq"),
    ("changelog.html", "changelog"),
]

HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{site}/{page}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Secret Vault">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{site}/{page}">
<meta property="og:image" content="{site}/social-preview.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{site}/social-preview.png">
<meta name="theme-color" content="#0B0C10">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/style.css">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='6' fill='%230B0C10'/><text x='16' y='23' font-family='monospace' font-size='18' font-weight='700' text-anchor='middle' fill='%238CE62E'>//</text></svg>">
{extra}</head>
<body>
<header class="site"><div class="wrap">
  <a class="logo" href="index.html"><span class="slash">//</span> secret<span class="vault">_vault</span></a>
  <nav class="site">{nav}</nav>
</div></header>
<main class="wrap">
"""

FOOT = """</main>
<footer class="site"><div class="wrap">
  <span>MIT · v{version} · maintained by <a href="https://github.com/kolijijani">Mohammad Koliji Jani Bin Azizan</a></span>
  <span><a href="{repo}">GitHub</a> · <a href="{repo}/issues">Issues</a> · <a href="{repo}/blob/main/SECURITY.md">Security</a></span>
</div></footer>
</body>
</html>
"""

JSONLD = """<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"SoftwareApplication",
"name":"Secret Vault","applicationCategory":"DeveloperApplication",
"operatingSystem":"Linux, macOS","softwareVersion":"{version}",
"description":"One-shot local form for handing secrets to AI agents without putting them in chat.",
"url":"{site}/","downloadUrl":"{repo}",
"license":"https://opensource.org/licenses/MIT",
"offers":{{"@type":"Offer","price":"0","priceCurrency":"USD"}},
"author":{{"@type":"Person","name":"Mohammad Koliji Jani Bin Azizan","url":"https://github.com/kolijijani"}}}}
</script>
"""


def page(name, title, desc, body, extra=""):
    parts = []
    for href, label in NAV:
        cur = ' aria-current="page"' if href == name else ""
        parts.append(f'<a href="{href}"{cur}>{label}</a>')
    nav = "".join(parts)
    out = HEAD.format(title=title, desc=desc, site=SITE, page=name, nav=nav, extra=extra)
    out += body + FOOT.format(version=VERSION, repo=REPO)
    (DOCS / name).write_text(out, encoding="utf-8")
    return name


def code(block, lang="sh"):
    return f"<pre><code>{html.escape(block.strip())}</code></pre>"


AUDIT_EXAMPLE = code(
    "2026-10-22T04:31:07+00:00" + "\t" + "saved-env" + "\t"
    + "fields=MAIL_FROM,SIGNING_KEY" + "\t" + "bytes=88"
)

STDIN_EXAMPLE = code(
    """echo '{"title":"Provider key","target":"~/.config/secret-vault/provider.env","mode":"env","""
    + """
"fields":[{"key":"API_KEY","label":"API key","type":"password"}]}' \\
  | python3 scripts/secret_form.py --spec -"""
)

SPEC_EXAMPLE = code(
    """{
  "title": "Email delivery setup",
  "subtitle": "Provide the sender identity and signing credential",
  "target": "~/.config/secret-vault/mail.env",
  "mode": "env",
  "fields": [
    {"key": "MAIL_FROM", "label": "Sender email", "type": "text"},
    {"key": "SIGNING_KEY", "label": "Signing key", "type": "password"},
    {"key": "MAIL_CONFIG", "label": "Config bundle", "type": "dual", "optional": true}
  ]
}"""
)


# ---------------------------------------------------------------- overview
overview = f"""
<span class="pill">v{VERSION} · stable</span>
<h1><span class="slash">//</span> Secret Vault</h1>
<p class="lede">A one-shot, local form for handing an API key, password, certificate or config file to
an AI agent — without pasting it into chat, where it lands in model context, transcripts and tool logs.</p>

<div class="cards">
  <a class="card" href="install.html"><b>Install</b><span>Clone, run, or install as a command with pipx or uvx. Standard library only.</span></a>
  <a class="card" href="usage.html"><b>Usage</b><span>Adaptive fields, raw-file mode, expiry, audit log.</span></a>
  <a class="card" href="agents.html"><b>Use with an agent</b><span>Claude Code, Codex, Cursor, Hermes — where the skill goes.</span></a>
  <a class="card" href="security.html"><b>Security model</b><span>What it protects, what it does not, and how to report a flaw.</span></a>
</div>

<h2>Why this exists</h2>
<p>An agent asks for a key. You paste it into the chat box. That value is now part of the conversation
history, the provider's request, the session transcript on disk, and possibly a tool log — and you cannot
take it back.</p>
<p>Secret Vault replaces that paste with a form on your own machine. The agent declares which fields it
needs; you type the value into the page; it is written straight to a protected local file with mode
<code>0600</code>. The server accepts exactly one submission and exits.</p>

<h2>How it works</h2>
<table>
<tr><th>Stage</th><th>Responsibility</th><th>Secret exposure</th></tr>
<tr><td>Agent</td><td>Creates a JSON form specification</td><td>Sees field definitions, never values</td></tr>
<tr><td>Local server</td><td>Serves a random-token, one-shot form</td><td>Holds values only while writing</td></tr>
<tr><td>Your browser</td><td>Submits over localhost or a trusted private network</td><td>You control the entry point</td></tr>
<tr><td>Protected target</td><td>Receives an atomic write with mode <code>0600</code></td><td>Values remain local</td></tr>
</table>

<h2>Quickstart</h2>
{code('''git clone https://github.com/kolijijani/secret-vault.git
cd secret-vault
python3 scripts/secret_form.py --spec examples/api-key.json''')}
<p>The command prints a one-time URL and waits for one submission:</p>
{code('''URL: http://127.0.0.1:8731/?t=<random-token>
TARGET: /home/user/.config/secret-vault/provider.env
EXPIRES: 900s
Waiting for one submission...''')}
<p>Open that URL on the same machine. After the value is saved the server writes the target file and
exits; if nobody submits before the deadline it exits and writes nothing.</p>

<h2>What it does</h2>
<ul>
<li>Keeps secret values out of chat, model context and request logs.</li>
<li>Lets the agent adapt title, labels, field types, optional fields and target file per task.</li>
<li>Supports visible text, masked secrets, long text, code, file uploads and paste-or-upload fields.</li>
<li>Writes <code>KEY=VALUE</code> env files or complete raw files such as JSON, YAML, PEM and config files.</li>
<li>Atomic mode-<code>0600</code> writes, symlink rejection, random server-side upload names.</li>
<li>Random URL token plus a locked single-claim submission state.</li>
<li>Closes itself after a deadline (<code>--expire-minutes</code>, 15 by default) and refuses wildcard binds.</li>
<li>Preserves binary uploads with bounded, standards-aware multipart parsing.</li>
<li>Runs on the Python standard library — no package installation required.</li>
<li>Optional value-free audit line per submission (<code>--audit-log</code>).</li>
<li>Ships an agent-ready <code>SKILL.md</code>, an <code>install.sh</code>, examples, CI and 33 tests.</li>
</ul>

<div class="note">Secret Vault is a local handoff utility, not an internet-facing secret manager.
Use localhost or a trusted private network such as Tailscale or a VPN.</div>
"""
page("index.html",
     "Secret Vault — give an API key to an AI agent without pasting it in chat",
     "One-shot local form for handing secrets to AI agents. The agent declares the fields, you type the "
     "value into a local page, it is written straight to a mode-0600 file. Standard library only.",
     overview, extra=JSONLD.format(version=VERSION, site=SITE, repo=REPO))

# ---------------------------------------------------------------- install
install = f"""
<h1><span class="slash">//</span> Install</h1>
<p class="lede">Three ways in: run from a checkout, install as a command, or install the agent skill.
None of them need a third-party Python package.</p>

<h2>Requirements</h2>
<ul>
<li>Linux or macOS with Python 3.10 or newer</li>
<li>A modern browser</li>
<li>Localhost, or a trusted private network when opening the form from another device</li>
<li>Chrome or Chromium only if you want to regenerate the README screenshot</li>
</ul>

<h2>Run from a checkout</h2>
{code('''git clone https://github.com/kolijijani/secret-vault.git
cd secret-vault
python3 scripts/secret_form.py --version''')}

<h2>Install as a command</h2>
{code('''pipx install agent-secret-form''')}
{code('''uvx --from agent-secret-form secret-vault --version''')}
<p>The distribution on PyPI is <strong><code>agent-secret-form</code></strong>; the console command stays
<code>secret-vault</code>. Installing from Git also works:</p>
{code('''pipx install git+https://github.com/kolijijani/secret-vault.git''')}
<div class="warn">Do not <code>pip install secret-vault</code>: that name on PyPI belongs to an unrelated
project.</div>

<h2>Install the agent skill</h2>
<p>The installer copies <code>SKILL.md</code> into the agent's skill directory and rewrites the script path
to your checkout:</p>
{code('''./install.sh              # auto-detects ~/.hermes/skills, ~/.claude/skills, ~/.agents/skills''')}
{code('''./install.sh ~/.claude/skills   # or name the directory explicitly''')}
{code('''./install.sh --dry-run          # preview without writing''')}
<p>See <a href="agents.html">Use with an agent</a> for the per-agent matrix.</p>

<h2>Verify</h2>
{code('''python3 scripts/secret_form.py --version''')}
<p>Then start the example and confirm the page shows <code>// secret_vault</code>, <code>LIVE / SINGLE USE</code>
and a countdown.</p>

<h2>Uninstall</h2>
{code('''pipx uninstall secret-vault''')}
<p>Remove the skill directory the installer created, and any <code>~/.config/secret-vault/</code> files you
no longer want.</p>
"""
page("install.html",
     "Install Secret Vault — pipx, uvx, or run from source",
     "Install Secret Vault on Linux or macOS with Python 3.10+: clone and run, pipx/uvx from the Git URL, "
     "or copy the SKILL.md into your agent's skill directory.",
     install)

# ---------------------------------------------------------------- usage
usage = f"""
<h1><span class="slash">//</span> Usage</h1>
<p class="lede">The agent writes a small JSON spec. The form adapts to it. You submit once.</p>

<h2>Start a form</h2>
{code('''python3 scripts/secret_form.py --spec examples/api-key.json''')}
<p>Or pass the spec on stdin:</p>
{STDIN_EXAMPLE}

<h2>Adaptive form</h2>
<p>The design stays fixed; the content changes per task. Field types, labels, optional flags, the target
file and the page title all come from the spec:</p>
{SPEC_EXAMPLE}

<h2>Field types</h2>
<table>
<tr><th>Type</th><th>Intended use</th></tr>
<tr><td><code>text</code></td><td>Visible context such as email, account ID, region or project name</td></tr>
<tr><td><code>password</code></td><td>Masked API keys, passwords, tokens and signing secrets</td></tr>
<tr><td><code>textarea</code></td><td>Multi-line notes or short text blobs</td></tr>
<tr><td><code>code</code></td><td>Monospace JSON, YAML, PEM, config or code</td></tr>
<tr><td><code>file</code></td><td>File upload</td></tr>
<tr><td><code>dual</code></td><td>Lets the user choose paste or upload</td></tr>
<tr><td><code>optional: true</code></td><td>Skips an empty field</td></tr>
</table>

<h2>Raw file mode</h2>
<p>Use <code>mode: "file"</code> when the submitted content <em>is</em> the target file — a JSON service
account, a PEM key, a YAML config:</p>
{code('''python3 scripts/secret_form.py --spec examples/config-file.json''')}

<h2>Expiry and single use</h2>
<p>The form is one-shot: the first successful save closes it. It also has a deadline, so an abandoned link
never stays open.</p>
{code('''python3 scripts/secret_form.py --spec examples/api-key.json --expire-minutes 20''')}
<p><code>--expire-minutes</code> defaults to 15; pass <code>0</code> to disable the deadline. When the
deadline passes the page returns <code>410 Gone</code> and no values are written. After the process exits
the port is closed and the token is useless.</p>
<p>For OS-level belt-and-braces on a shared machine, wrap the process in a hard kill:</p>
{code('''systemd-run --user --unit=secret-form --property=RuntimeMaxSec=900 --collect python3 scripts/secret_form.py --bind 127.0.0.1 --spec examples/api-key.json''')}

<h2>Audit log</h2>
<p><code>--audit-log PATH</code> appends one line per submission with the timestamp, outcome, field
<strong>names</strong> and byte count — never values. It is written <code>0600</code> and is useful when an
agent must prove a handoff happened without touching the secret.</p>
{AUDIT_EXAMPLE}

<h2>Command options</h2>
<table>
<tr><th>Option</th><th>Default</th><th>Purpose</th></tr>
<tr><td><code>--spec</code></td><td>—</td><td>JSON spec file, or <code>-</code> for stdin</td></tr>
<tr><td><code>--target</code></td><td><code>~/.config/secret-vault/secrets.env</code></td><td>Override the target file</td></tr>
<tr><td><code>--bind</code></td><td><code>127.0.0.1</code></td><td>IPv4 interface to listen on</td></tr>
<tr><td><code>--port</code></td><td><code>8731</code></td><td>Local TCP port</td></tr>
<tr><td><code>--max-bytes</code></td><td><code>5242880</code></td><td>Maximum request body size</td></tr>
<tr><td><code>--files-dir</code></td><td>target-adjacent <code>secret_files/</code></td><td>Upload storage directory</td></tr>
<tr><td><code>--expire-minutes</code></td><td><code>15</code></td><td>Close after N minutes; <code>0</code> disables</td></tr>
<tr><td><code>--allow-wildcard</code></td><td>off</td><td>Permit <code>--bind 0.0.0.0</code></td></tr>
<tr><td><code>--audit-log</code></td><td>none</td><td>Append a value-free line per submission</td></tr>
<tr><td><code>--version</code></td><td>—</td><td>Print the version and exit</td></tr>
</table>

<h2>Open the form from another device</h2>
<p>Wildcard binds are refused unless you pass <code>--allow-wildcard</code>, so a typo cannot quietly expose
the form on every interface. Bind the machine's IPv4 address on a trusted VPN or LAN instead:</p>
{code('''python3 scripts/secret_form.py --bind 100.x.y.z --spec examples/api-key.json''')}
<div class="warn">Never bind to a public interface without a protected tunnel and TLS proxy.</div>
"""
page("usage.html",
     "Secret Vault usage — adaptive forms, raw files, expiry, audit log",
     "How to run a Secret Vault form: JSON spec, field types, raw-file mode, --expire-minutes deadline, "
     "single-claim submission and the value-free audit log.",
     usage)

# ---------------------------------------------------------------- agents
agents = f"""
<h1><span class="slash">//</span> Use with an agent</h1>
<p class="lede"><code>SKILL.md</code> is the agent-facing instruction file. <code>scripts/secret_form.py</code>
is the tool it calls. Installing the skill does not install the script.</p>

<h2>Skill directory per agent</h2>
<table>
<tr><th>Agent</th><th>Skill directory</th><th>Notes</th></tr>
<tr><td>Hermes</td><td><code>~/.hermes/skills/secret-vault/SKILL.md</code></td><td>Raw SKILL.md install works, but the script path still needs fixing</td></tr>
<tr><td>[CC]</td><td><code>~/.claude/skills/secret-vault/SKILL.md</code></td><td>Skills load by <code>name</code> + <code>description</code> frontmatter</td></tr>
<tr><td>Codex / generic agent</td><td><code>~/.agents/skills/</code> or project <code>.agents/skills/</code></td><td>Any layout that lets the agent read <code>SKILL.md</code> on demand</td></tr>
<tr><td>Cursor</td><td>project <code>.cursor/rules/</code> or <code>AGENTS.md</code></td><td>Reference the SKILL.md path in the rule text</td></tr>
</table>

<h2>Install</h2>
{code('''git clone https://github.com/kolijijani/secret-vault.git
cd secret-vault
./install.sh ~/.claude/skills''')}
<p><code>./install.sh</code> with no argument auto-detects the first existing directory from
<code>~/.hermes/skills</code>, <code>~/.claude/skills</code>, <code>~/.agents/skills</code>,
<code>~/.config/agents/skills</code>. Use <code>--dry-run</code> to preview.</p>
<p>Without the installer, copy <code>SKILL.md</code> and replace every <code>scripts/secret_form.py</code>
with the absolute path to your checkout. If you installed the CLI instead, replace it with
<code>secret-vault</code>.</p>

<h2>Why the path matters</h2>
<p><code>SKILL.md</code> ships with <code>scripts/secret_form.py</code>, a repository-relative path. Copy only
the markdown and the agent will call a script that does not exist — the failure mode is a confused agent
asking you to paste a key into chat, which is exactly what this project prevents.</p>

<h2>Verify the handoff works</h2>
{code('''python3 scripts/secret_form.py --version''')}
<p>Then ask the agent for a form and confirm the page shows <code>// secret_vault</code>,
<code>LIVE / SINGLE USE</code> and a countdown. If the agent shows you a secret value in chat, stop and
re-read the skill's <em>Rule (never break)</em> section.</p>

<h2>Give the agent the rule, not the value</h2>
<p>The skill's core instruction is one line: when a task needs a credential, start a form and give the user
the URL — never ask for the value in chat. Everything else in the skill exists to make that work in
practice: choosing field types, choosing the target file, handling expiry, and proving the handoff with the
audit log.</p>
"""
page("agents.html",
     "Use Secret Vault with an AI agent — Hermes, Claude, Codex, Cursor",
     "Where to install the Secret Vault SKILL.md for Hermes, Claude, Codex and Cursor, why the script path "
     "matters, and how to verify a handoff worked.",
     agents)

# ---------------------------------------------------------------- security
security = f"""
<h1><span class="slash">//</span> Security model</h1>
<p class="lede">Secret Vault is a local handoff utility, not an internet-facing secret manager.
This page states exactly what it protects and what it does not.</p>

<h2>What it protects</h2>
<ul>
<li>Secret values never enter chat, model context, or application request logs.</li>
<li>HTTP request logging is disabled; values are never printed by the application.</li>
<li>Targets and uploads are created with mode <code>0600</code>.</li>
<li>Writes are atomic — a partial write never leaves a half-written credential.</li>
<li>Symlink targets are rejected, so a link cannot redirect a secret into an unexpected file.</li>
<li>Uploads get random server-side names, so a supplied filename cannot escape the directory.</li>
<li>One concurrent request claims the token; later requests are rejected (<code>409</code>).</li>
<li>A wrong or missing token returns <code>404</code>, not an error page that confirms a form exists.</li>
<li>Pages send <code>Cache-Control: no-store</code>, <code>Referrer-Policy: no-referrer</code>,
    <code>X-Content-Type-Options: nosniff</code> and a restrictive Content-Security-Policy.</li>
<li>Wildcard binds are refused unless explicitly allowed.</li>
<li>The deadline plus the single-use claim shrink the window in which a leaked link is useful.</li>
</ul>

<h2>What it does not do</h2>
<ul>
<li><strong>No TLS.</strong> The built-in server speaks HTTP. Put a trusted TLS proxy in front, or use a
private overlay network that encrypts transport.</li>
<li><strong>No rotation, revocation or validation</strong> of the submitted credential.</li>
<li><strong>No history.</strong> The process is intentionally single-use and stores no submissions.</li>
<li><strong>No protection after the write.</strong> Once the credential lands in the target file, protecting
that file and the host is your normal security posture.</li>
<li><strong>No Windows support.</strong> Its filesystem permission and symlink semantics do not provide the
POSIX guarantees this release enforces.</li>
<li><strong>No IPv6 bind addresses.</strong></li>
</ul>

<h2>Deployment rules</h2>
<ol>
<li>Use localhost or a trusted private network such as Tailscale or a VPN.</li>
<li>Treat the random URL as confidential until it is consumed.</li>
<li>Never expose the server directly to the public internet.</li>
<li>Prefer the default 15-minute deadline; shorten it when the user is already at the keyboard.</li>
<li>Use <code>--audit-log</code> when you need proof that a handoff happened.</li>
</ol>

<div class="note">A leaked form link is only useful until it is consumed or expires. Start a new process for
every value you need — never reuse a URL.</div>

<h2>Reporting a vulnerability</h2>
<p>Use a private GitHub security advisory on the repository. Never include a real credential in a report;
use a dummy value that reproduces the issue.</p>
{code('''https://github.com/kolijijani/secret-vault/security/advisories/new''')}
<p>The full threat model lives in
<a href="{REPO}/blob/main/SECURITY.md">SECURITY.md</a>.</p>
"""
page("security.html",
     "Secret Vault security model — what it protects and what it does not",
     "Secret Vault's threat model: atomic 0600 writes, symlink rejection, single-claim tokens, 404 on a "
     "wrong token, no TLS, no rotation, and how to report a vulnerability.",
     security)

# ---------------------------------------------------------------- faq
faq = f"""
<h1><span class="slash">//</span> FAQ &amp; troubleshooting</h1>
<p class="lede">The problems people actually hit, and the limitations worth knowing before you rely on this.</p>

<h2>The URL works only on the server machine</h2>
<p>The secure default is <code>127.0.0.1</code>. Bind explicitly to a trusted private IPv4 address when
another device must open the form:</p>
{code('''python3 scripts/secret_form.py --bind 100.x.y.z --spec examples/api-key.json''')}
<p>Never bind to a public interface without a protected tunnel and TLS proxy.</p>

<h2>Port already in use</h2>
{code('''python3 scripts/secret_form.py --port 8732 --spec examples/api-key.json''')}

<h2>The page closes after submission</h2>
<p>That is expected. A successful submission consumes the token and shuts the server down. Start a new
process to collect another value.</p>

<h2>A target symlink is rejected</h2>
<p>That is deliberate protection against redirecting a secret into an unexpected file. Use a regular file
path owned by the current user.</p>

<h2>The form expired before I submitted</h2>
<p>The deadline defaults to 15 minutes. Restart the process for a fresh token, or raise the deadline with
<code>--expire-minutes 30</code>. <code>410 Gone</code> means nothing was written.</p>

<h2>My agent keeps asking me to paste the key in chat</h2>
<p>The skill is installed but its script path is wrong, so the agent cannot start a form and falls back to
asking. Re-run <code>./install.sh</code> against the right skill directory, or replace
<code>scripts/secret_form.py</code> inside <code>SKILL.md</code> with the absolute path to your checkout.</p>

<h2>Can I use it over the internet?</h2>
<p>Not directly. Put it behind Tailscale, a VPN, or a TLS proxy you trust. The built-in server is HTTP and
has no authentication beyond the random token.</p>

<h2>Does it work on Windows?</h2>
<p>No. Windows filesystem permission and symlink semantics do not provide the POSIX guarantees this release
enforces. Use WSL if you need it on a Windows machine.</p>

<h2>Is it a secret manager like Vault or 1Password?</h2>
<p>No. It is a handoff tool: one form, one value, one write, then it exits. It does not store, rotate,
version or share secrets. Use a real secret manager for anything long-lived.</p>

<h2>Limitations, in one list</h2>
<ul>
<li>HTTP only; TLS termination belongs to a proxy or private overlay network.</li>
<li>IPv6 bind addresses are not supported.</li>
<li>Windows is not supported.</li>
<li>Single-use by design; no submission history.</li>
<li>Does not rotate, revoke or validate the submitted credential.</li>
<li>Protecting the destination directory and host remains your responsibility.</li>
</ul>
"""
page("faq.html",
     "Secret Vault FAQ — port in use, expired form, symlink rejected, agent still asking",
     "Answers to the common Secret Vault problems: form only reachable on localhost, port in use, expired "
     "token, rejected symlink, and an agent that still asks for the key in chat.",
     faq)

# ---------------------------------------------------------------- changelog
changelog_md = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
body = changelog_md.split("\n", 2)[2]
lines, out = body.splitlines(), []
in_list = False
for line in lines:
    if line.startswith("## "):
        if in_list:
            out.append("</ul>")
            in_list = False
        out.append(f"<h2>{html.escape(line[3:])}</h2>")
    elif line.startswith("### "):
        if in_list:
            out.append("</ul>")
            in_list = False
        out.append(f"<h3>{html.escape(line[4:])}</h3>")
    elif line.startswith("- "):
        if not in_list:
            out.append("<ul>")
            in_list = True
        out.append(f"<li>{html.escape(line[2:])}</li>")
    elif line.strip() == "":
        if in_list:
            out.append("</ul>")
            in_list = False
    else:
        if in_list:
            out.append("</ul>")
            in_list = False
        out.append(f"<p>{html.escape(line)}</p>")
if in_list:
    out.append("</ul>")

changelog = f"""
<h1><span class="slash">//</span> Changelog</h1>
<p class="lede">Every release, newest first. The machine-readable copy lives in
<a href="{REPO}/blob/main/CHANGELOG.md">CHANGELOG.md</a>.</p>
{''.join(out)}
"""
page("changelog.html",
     "Secret Vault changelog — every release",
     "Release history for Secret Vault: renames, form layout fixes, expiry timer, audit log and the "
     "one-shot form behaviour.",
     changelog)

# ---------------------------------------------------------------- 404, robots, sitemap
(DOCS / "404.html").write_text(
    HEAD.format(title="Page not found — Secret Vault", desc="That page does not exist.",
                site=SITE, page="404.html", nav="", extra="")
    + '<h1><span class="slash">//</span> 404</h1>\n<p class="lede">That page does not exist. '
      'Start from the <a href="index.html">overview</a>.</p>\n'
    + FOOT.format(version=VERSION, repo=REPO),
    encoding="utf-8")

(DOCS / "robots.txt").write_text(
    f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n", encoding="utf-8")

urls = "".join(
    f"  <url><loc>{SITE}/{href}</loc><lastmod>{TODAY}</lastmod>"
    f"<changefreq>{'weekly' if href == 'changelog.html' else 'monthly'}</changefreq>"
    f"<priority>{'1.0' if href == 'index.html' else '0.7'}</priority></url>\n"
    for href, _ in NAV
)
(DOCS / "sitemap.xml").write_text(
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    f"{urls}</urlset>\n", encoding="utf-8")

(DOCS / ".nojekyll").write_text("", encoding="utf-8")
print(f"built {len(NAV) + 1} pages + robots.txt + sitemap.xml into {DOCS}")
