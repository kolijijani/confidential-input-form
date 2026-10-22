#!/usr/bin/env python3
"""
Adaptive one-time secret handoff for local AI agents.

The agent designs the form for the task: title, fields, input types, optional
status, and target file. The Terminal Vault theme stays consistent. Secret values
go directly from the user's browser to a local file and are never printed.

USAGE
-----
Simple (parallel args):
    python3 secret_form.py \
        --keys OPENAI_API_KEY \
        --labels "OpenAI API Key" --types password \
        --title "OpenAI Key"

Adaptive / full control (JSON spec) — recommended when fields differ in type
or you need textarea / file-upload / optional fields:
    python3 secret_form.py --spec -   <<'JSON'
    {
      "title": "Stripe Setup",
      "subtitle": "Enter the Stripe credentials for this project",
      "target": "~/.config/secret-vault/secrets.env",
      "fields": [
        {"key": "STRIPE_PK",  "label": "Publishable key", "type": "text"},
        {"key": "STRIPE_SK",  "label": "Secret key",      "type": "password", "hint": "Paste the secret key here"},
        {"key": "STRIPE_WH",  "label": "Webhook secret",  "type": "password", "optional": true},
        {"key": "STRIPE_NOTE","label": "Catatan",         "type": "textarea"}
      ]
    }
    JSON

Field types: text | password | textarea | code | file | dual
  - code   -> like textarea but monospace; for pasting JSON / YAML / PEM / code.
  - file   -> saves the uploaded file into a directory (--files-dir, default a
              subdir of the target's folder) and writes KEY=<saved path> to target.
  - dual   -> ONE field offering BOTH a paste box AND a file picker; the user
              chooses. Whichever is provided wins. Great when the agent is not
              sure whether the user will paste or upload.
  - optional=true  -> empty value allowed (KEY is skipped if blank).

Value vs file mode (spec-level `"mode"`):
  - mode = "env"  (DEFAULT): each field becomes KEY=VALUE in the target env file.
                               (file/dual fields store the SAVED PATH as the value)
  - mode = "file": the target IS the saved content. A single field only; the
                   pasted text or uploaded file is written verbatim to `target`
                   (e.g. a JSON/YAML/config or a .pem). Ideal for "paste a
                   service-account JSON" or "upload/ paste a key file".

Flags:
  --spec FILE   JSON spec ('-' = stdin). Overrides --keys/--labels/--types.
  --keys        comma-separated env keys (simple mode)
  --labels      comma-separated labels (simple mode)
  --types       comma-separated types (simple mode; default: text for all)
  --mask        comma list of 1-based indices to force to password (simple mode)
  --title, --subtitle
  --target      file to write KEY=VALUE lines (default ~/.config/secret-vault/secrets.env, mode 600)
  --files-dir   where uploaded files are stored (default <target dir>/secret_files)
  --bind, --port (default 127.0.0.1:8731; bind a private interface to share)

On success the server writes values, shows a confirmation, and exits (one-shot).
Values are NEVER echoed back, NEVER logged.
"""
import argparse
import datetime
import email.parser
import email.policy
import html
import http.server
import json
import os
import re
import secrets
import socket
import socketserver
import stat
import sys
import threading
import time
import urllib.parse

__version__ = "1.1.0"
EXPIRY_GRACE_SECONDS = 5  # keep the socket up briefly so a late visit sees the expired page
DEF_ENV = os.path.expanduser("~/.config/secret-vault/secrets.env")
ALLOWED_TYPES = {"text", "password", "textarea", "code", "file", "dual"}
KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def validate_spec(spec):
    if not isinstance(spec, dict) or not isinstance(spec.get("fields"), list) or not spec["fields"]:
        raise SystemExit("spec must contain a non-empty 'fields' list")
    if spec.get("mode", "env") not in {"env", "file"}:
        raise SystemExit("mode must be 'env' or 'file'")
    if spec.get("mode") == "file" and len(spec["fields"]) != 1:
        raise SystemExit("file mode requires exactly one field")
    for field in spec["fields"]:
        key = field.get("key", "")
        typ = field.get("type", "text")
        if not KEY_RE.fullmatch(key):
            raise SystemExit(f"invalid field key: {key!r}")
        if typ not in ALLOWED_TYPES:
            raise SystemExit(f"unsupported field type: {typ!r}")
    return spec


def validate_bind(bind, allow_wildcard=False):
    if ":" in bind:
        raise ValueError("IPv6 bind addresses are not supported")
    if bind.strip() in ("", "*", "0.0.0.0") and not allow_wildcard:
        raise ValueError(
            "refusing to bind a wildcard address: pass an explicit interface "
            "(e.g. 127.0.0.1 or your private-network IP) or --allow-wildcard"
        )
    return bind


def public_host(bind):
    if bind != "0.0.0.0":
        return bind
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("1.1.1.1", 80))
        host = sock.getsockname()[0]
        sock.close()
        return host
    except OSError:
        return "127.0.0.1"


def _spec_from_args(args):
    if args.spec:
        if args.spec == "-":
            raw = sys.stdin.read()
        else:
            with open(args.spec, encoding="utf-8") as fh:
                raw = fh.read()
        spec = json.loads(raw)
        spec.setdefault("title", "Confidential input")
        spec.setdefault("target", DEF_ENV)
        if "fields" not in spec:
            raise SystemExit("spec must contain 'fields'")
        return spec
    keys = [k.strip() for k in (args.keys or "").split(",") if k.strip()]
    labels = [l.strip() for l in (args.labels or "").split(",")]
    types = [t.strip() for t in (args.types or "").split(",")]
    mask = {int(x) for x in (args.mask or "").split(",") if x.strip()}
    if not keys:
        raise SystemExit("provide --keys or --spec")
    if not labels:
        labels = keys
    fields = []
    for i, k in enumerate(keys):
        t = types[i] if i < len(types) else "text"
        if (i + 1) in mask:
            t = "password"
        fields.append({"key": k, "label": labels[i] if i < len(labels) else k, "type": t})
    return {"title": args.title, "subtitle": args.subtitle, "target": args.target, "fields": fields}


def render_field(i, f, multipart):
    t = f.get("type", "text")
    lbl = html.escape(str(f.get("label", f["key"])))
    opt = " <span class='opt'>(optional)</span>" if f.get("optional") else ""
    hint = html.escape(str(f.get("hint", "")), quote=True)
    ph = f" placeholder=\"{hint}\"" if hint and t not in ("textarea", "code") else ""
    if t in ("textarea", "code"):
        cls = ' class="mono"' if t == "code" else ""
        pha = f' placeholder="{hint}"' if hint else ""
        inp = f'<textarea id="f{i}" name="f{i}" rows="{6 if t == "code" else 3}"{cls} autocomplete="off"{pha}></textarea>'
    elif t == "file":
        inp = f'<input id="f{i}" name="f{i}" type="file" autocomplete="off">'
    elif t == "dual":
        # paste OR upload — user picks. A tiny JS helper toggles which is used.
        inp = (
            f'<div class="dual" data-i="{i}">'
            f'<div class="tabs">'
            f'<button type="button" class="tab on" onclick="dualPick({i},\'paste\')">📋 Paste</button>'
            f'<button type="button" class="tab" onclick="dualPick({i},\'upload\')">⬆️ Upload</button>'
            f'</div>'
            f'<textarea id="f{i}_paste" name="f{i}_paste" rows="6" class="mono" autocomplete="off" '
            f'placeholder="{hint or "Paste content here…"}"></textarea>'
            f'<input id="f{i}_file" name="f{i}_file" type="file" style="display:none" '
            f'autocomplete="off" aria-label="{lbl} (upload)">'
            f'</div>'
        )
    else:
        typ = "password" if t == "password" else "text"
        af = " autofocus" if i == 0 else ""
        inp = f'<input id="f{i}" name="f{i}" type="{typ}" autocomplete="off"{ph}{af}>'
    return f'<label for="f{i}">{lbl}{opt}</label>{inp}'


def build_page(spec, token, multipart, expires_seconds=None):
    title = html.escape(str(spec.get("title", "Confidential input")))
    subtitle = html.escape(str(spec.get("subtitle", "Enter the requested information below")))
    fields = "\n".join(render_field(i, f, multipart) for i, f in enumerate(spec["fields"]))
    enc = ' enctype="multipart/form-data"' if multipart else ""
    if expires_seconds:
        note = ('target: protected file · mode: 0600 · single use'
                '<br>This page closes in <span id="cd" role="timer">--:--</span> or after the first save.')
        countdown = f"""
<script>
(function(){{
  var left = {int(expires_seconds)};
  var el = document.getElementById('cd');
  function tick(){{
    if(left <= 0){{ el.textContent = 'expired'; return; }}
    var m = Math.floor(left/60), s = left % 60;
    el.textContent = m + ':' + (s<10?'0':'') + s;
    left -= 1;
    setTimeout(tick, 1000);
  }}
  tick();
}})();
</script>"""
    else:
        note = ('target: protected file · mode: 0600 · single use'
                '<br>Values never return to chat or logs. Use only on localhost or a trusted private network.')
        countdown = ""
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>{title}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
 *{{box-sizing:border-box}} body{{font-family:Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif;background:#0c0d12;color:#e8e7ed;min-height:100vh;margin:0;padding:28px}}
 .shell{{width:760px;max-width:100%;margin:0 auto}}
 .top{{display:flex;align-items:center;justify-content:space-between;margin-bottom:72px}}
 .brand{{font-weight:850;letter-spacing:-.04em}} .brand span,.kicker{{color:#a3e635}}
 .live{{font-size:11px;color:#a3e635;border:1px solid #a3e635;border-radius:999px;padding:7px 11px;letter-spacing:.06em}}
 .kicker{{font-size:11px;text-transform:uppercase;letter-spacing:.14em;font-weight:800;margin-bottom:14px}}
 h1{{font-size:clamp(38px,7vw,66px);line-height:.98;letter-spacing:-.065em;margin:0 0 18px;max-width:720px}}
 p.sub{{font-size:16px;line-height:1.55;color:#a8a8b3;margin:0 0 34px;max-width:590px}}
 .card{{background:#15171f;padding:28px;border:1px solid #30333d;border-radius:20px;width:620px;max-width:100%}}
 label{{display:block;font:650 12px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;margin:17px 0 8px;color:#a3e635}}
 label:first-child{{margin-top:0}} .opt{{color:#9b9eaa;font-size:11px}}
 input,textarea{{width:100%;padding:13px 14px;border-radius:10px;border:1px solid #3d414e;background:#0c0d12;color:#fff;font-size:14px;font-family:inherit;outline:none}}
 input:focus,textarea:focus{{border-color:#a3e635;box-shadow:0 0 0 3px rgba(163,230,53,.12)}}
 textarea{{resize:vertical}} textarea.mono{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:13px}}
 .tabs{{display:flex;gap:8px;margin-bottom:9px}}
 .tab{{flex:1;padding:9px;border-radius:9px;border:1px solid #3d414e;background:#0c0d12;color:#9b9eaa;font-size:12px;cursor:pointer}}
 .tab.on{{background:#26321a;color:#cffa7a;border-color:#a3e635}}
 button[type=submit]{{margin-top:24px;width:100%;padding:13px;border:0;border-radius:10px;background:#a3e635;color:#10120c;font-size:14px;font-weight:800;cursor:pointer}}
 button[type=submit]:hover{{background:#b6f15e}} button[type=submit]:focus-visible{{outline:3px solid #fff;outline-offset:3px}}
 .note{{font:11px/1.55 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;color:#858894;margin-top:16px}}
 @media(max-width:600px){{body{{padding:20px}}.top{{margin-bottom:48px}}.card{{padding:20px}}}}
</style>
<script>
function dualPick(i, which){{
  var box = document.querySelector('.dual[data-i="'+i+'"]');
  var ta = box.querySelector('textarea'); var fi = box.querySelector('input[type=file]');
  var tabs = box.querySelectorAll('.tab');
  if(which==='paste'){{ ta.style.display=''; fi.style.display='none'; tabs[0].classList.add('on'); tabs[1].classList.remove('on'); }}
  else {{ ta.style.display='none'; fi.style.display=''; tabs[1].classList.add('on'); tabs[0].classList.remove('on'); }}
}}
</script></head><body>
<main class="shell" id="secret_vault">
 <header class="top"><div class="brand">// secret<span>_vault</span></div><div class="live">● LIVE / SINGLE USE</div></header>
 <div class="kicker">Secure input channel</div>
 <h1>{title}</h1>
 <p class="sub">{subtitle}</p>
 <section class="card">
  <form method="POST" action="/save?t={token}"{enc}>
{fields}
    <button type="submit">[ commit securely ]</button>
  </form>
  <div class="note">{note}</div>
 </section>
</main>{countdown}</body></html>"""


DONE = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Saved</title>
<style>*{box-sizing:border-box}body{font-family:Inter,system-ui;background:#0c0d12;color:#e8e7ed;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;padding:24px}.card{background:#15171f;border:1px solid #30333d;border-radius:20px;padding:34px;text-align:center;max-width:480px}.brand{font-weight:850}.brand span,h1{color:#a3e635}h1{font-size:34px;letter-spacing:-.04em;margin:28px 0 10px}p{color:#a8a8b3;line-height:1.55}.tag{font:11px ui-monospace,monospace;color:#a3e635;border:1px solid #a3e635;border-radius:999px;padding:7px 11px;display:inline-block;margin-top:18px}</style>
</head><body><div class="card" id="secret_vault"><div class="brand">// secret<span>_vault</span></div><h1>Saved securely.</h1><p>The value was written directly to its protected target.<br>This one-time page can now be closed.</p><div class="tag">CHANNEL CLOSED</div></div></body></html>"""

EXPIRED = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Expired</title>
<style>*{box-sizing:border-box}body{font-family:Inter,system-ui;background:#0c0d12;color:#e8e7ed;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;padding:24px}.card{background:#15171f;border:1px solid #30333d;border-radius:20px;padding:34px;text-align:center;max-width:480px}.brand{font-weight:850}.brand span,h1{color:#a3e635}h1{font-size:34px;letter-spacing:-.04em;margin:28px 0 10px}p{color:#a8a8b3;line-height:1.55}.tag{font:11px ui-monospace,monospace;color:#a3e635;border:1px solid #a3e635;border-radius:999px;padding:7px 11px;display:inline-block;margin-top:18px}</style>
</head><body><div class="card" id="secret_vault"><div class="brand">// secret<span>_vault</span></div><h1>This form expired.</h1><p>No values were written.<br>Ask the agent for a fresh link if you still need to hand over a secret.</p><div class="tag">CHANNEL CLOSED</div></div></body></html>"""


def _reject_symlink(path):
    try:
        mode = os.lstat(path).st_mode
    except FileNotFoundError:
        return
    if stat.S_ISLNK(mode):
        raise OSError("refusing to replace a symlink target")
    if not stat.S_ISREG(mode):
        raise OSError("target must be a regular file")


def _read_regular_file(path):
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise OSError("target must be a regular file")
        with os.fdopen(fd, "r", encoding="utf-8", newline=None) as stream:
            fd = -1
            return stream.read()
    finally:
        if fd >= 0:
            os.close(fd)


def secure_replace(path, data):
    """Atomically replace a regular file via a mode-0600 sibling temp file."""
    directory = os.path.dirname(path)
    os.makedirs(directory, mode=0o700, exist_ok=True)
    _reject_symlink(path)
    temp_path = None
    for _ in range(128):
        temp_path = os.path.join(directory, ".secret-form-" + secrets.token_hex(16))
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        try:
            fd = os.open(temp_path, flags, 0o600)
            break
        except FileExistsError:
            continue
    else:
        raise OSError("could not allocate a secure temporary file")
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        _reject_symlink(path)
        os.replace(temp_path, path)
        temp_path = None
    finally:
        if temp_path is not None:
            try:
                os.unlink(temp_path)
            except FileNotFoundError:
                pass


def serialize_env_value(value):
    """Serialize one env value without allowing a new assignment line."""
    if "\0" in value:
        raise ValueError("environment values cannot contain NUL")
    return value.replace("\\", "\\\\").replace("\r", "\\r").replace("\n", "\\n")


def upsert(path, kv):
    lines = []
    try:
        lines = _read_regular_file(path).splitlines()
    except FileNotFoundError:
        pass
    for k, v in kv.items():
        pat = re.compile(rf"^{re.escape(k)}\s*=")
        lines = [ln for ln in lines if not pat.match(ln)]
        lines.append(f"{k}={serialize_env_value(v)}")
    secure_replace(path, ("\n".join(lines) + "\n").encode("utf-8"))


def parse_multipart(body, content_type):
    """Parse a bounded multipart body without modifying binary payload bytes."""
    header = email.parser.BytesHeaderParser(policy=email.policy.default).parsebytes(
        b"Content-Type: " + content_type.encode("ascii", "strict") + b"\r\n\r\n"
    )
    if header.get_content_type() != "multipart/form-data":
        raise ValueError("expected multipart/form-data")
    boundary = header.get_boundary()
    if not boundary or any(ch in boundary for ch in "\r\n"):
        raise ValueError("missing or invalid multipart boundary")
    message = email.parser.BytesParser(policy=email.policy.default).parsebytes(
        b"Content-Type: " + content_type.encode("ascii", "strict")
        + b"\r\nMIME-Version: 1.0\r\n\r\n" + body
    )
    if not message.is_multipart() or message.defects:
        raise ValueError("malformed multipart body")
    out = {}
    for part in message.iter_parts():
        if part.get_content_disposition() != "form-data" or part.defects:
            raise ValueError("malformed multipart part")
        name = part.get_param("name", header="content-disposition")
        if not name or name in out:
            raise ValueError("missing or duplicate multipart field name")
        data = part.get_payload(decode=True)
        if data is None:
            raise ValueError("invalid multipart payload")
        filename = part.get_filename() or None
        out[name] = (data, filename)
    return out


def ensure_private_directory(directory):
    """Create a mode-0700 directory without accepting symlink path components."""
    directory = os.path.abspath(directory)
    drive, tail = os.path.splitdrive(directory)
    current = drive + os.sep if os.path.isabs(directory) else drive
    for part in [item for item in tail.split(os.sep) if item]:
        current = os.path.join(current, part)
        try:
            info = os.lstat(current)
        except FileNotFoundError:
            os.mkdir(current, 0o700)
            info = os.lstat(current)
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise OSError("upload directory must not contain symlinks")
    os.chmod(directory, 0o700)
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(directory, flags)
    if not stat.S_ISDIR(os.fstat(fd).st_mode):
        os.close(fd)
        raise OSError("upload destination must be a directory")
    return directory, fd


def save_upload(directory, client_filename, data, random_name=None):
    """Save an upload under a random server name using exclusive mode-0600 creation."""
    directory, directory_fd = ensure_private_directory(directory)
    suffix = os.path.splitext(client_filename or "")[1]
    suffix = suffix if re.fullmatch(r"\.[A-Za-z0-9]{1,16}", suffix) else ""
    make_name = random_name or (lambda: secrets.token_hex(16))
    try:
        for _ in range(128):
            name = make_name() + suffix.lower()
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
            try:
                fd = os.open(name, flags, 0o600, dir_fd=directory_fd)
            except FileExistsError:
                continue
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
                return os.path.join(directory, name)
            except BaseException:
                try:
                    os.unlink(name, dir_fd=directory_fd)
                except FileNotFoundError:
                    pass
                raise
    finally:
        os.close(directory_fd)
    raise OSError("could not allocate a unique upload name")


def write_audit(path, outcome, keys, nbytes):
    """Append a value-free audit line: time, outcome, field names, byte count."""
    if not path:
        return
    try:
        target = os.path.expanduser(path)
        stamp = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
        line = f"{stamp}\t{outcome}\tfields={','.join(keys)}\tbytes={nbytes}\n"
        with open(target, "a", encoding="utf-8") as fh:
            fh.write(line)
        try:
            os.chmod(target, 0o600)
        except OSError:
            pass
    except OSError:
        pass


class ClaimState:
    def __init__(self):
        self._lock = threading.Lock()
        self._claimed = False
        self._consumed = False

    def try_claim(self):
        with self._lock:
            if self._claimed or self._consumed:
                return False
            self._claimed = True
            return True

    def release(self):
        with self._lock:
            if not self._consumed:
                self._claimed = False

    def consume(self):
        with self._lock:
            self._consumed = True
            self._claimed = False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", help="JSON spec file ('-' = stdin)")
    ap.add_argument("--keys"); ap.add_argument("--labels"); ap.add_argument("--types"); ap.add_argument("--mask")
    ap.add_argument("--title", default="Confidential input")
    ap.add_argument("--subtitle", default="Enter the requested information below")
    ap.add_argument("--target", default=DEF_ENV)
    ap.add_argument("--files-dir", dest="files_dir", default=None)
    ap.add_argument("--bind", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8731)
    ap.add_argument("--max-bytes", type=int, default=5 * 1024 * 1024,
                    help="maximum request body size (default: 5 MiB)")
    ap.add_argument("--expire-minutes", type=float, default=15.0,
                    help="close the form after this many minutes (default: 15; 0 = never)")
    ap.add_argument("--allow-wildcard", action="store_true",
                    help="allow binding 0.0.0.0 (not recommended)")
    ap.add_argument("--audit-log", default=None,
                    help="append a value-free line per submission to this file")
    ap.add_argument("--version", action="version",
                    version=f"confidential-input-form {__version__}")
    args = ap.parse_args()

    spec = validate_spec(_spec_from_args(args))
    target = os.path.abspath(os.path.expanduser(spec.get("target", DEF_ENV)))
    if not os.path.dirname(target):
        raise SystemExit("target must include a directory")
    files_dir = os.path.expanduser(args.files_dir or os.path.join(os.path.dirname(target), "secret_files"))
    mode = spec.get("mode", "env")  # "env" = KEY=VALUE, "file" = write content to target
    has_file = any(f.get("type") in ("file", "dual") for f in spec["fields"])
    token = secrets.token_urlsafe(16)
    expires_seconds = int(args.expire_minutes * 60) if args.expire_minutes > 0 else None
    page = build_page(spec, token, has_file, expires_seconds).encode()
    claim_state = ClaimState()
    expired = threading.Event()

    class H(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):
            pass  # never log request contents

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            supplied = urllib.parse.parse_qs(parsed.query).get("t", [""])[0]
            if parsed.path != "/" or not secrets.compare_digest(supplied, token):
                self.send_error(404); return
            if expired.is_set():
                body = EXPIRED.encode()
                self.send_response(410)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)

        def handle_expect_100(self):
            # Accept curl's 'Expect: 100-continue' so multipart POSTs aren't stalled.
            self.send_response_only(100)
            self.end_headers()
            return True

        def do_POST(self):
            parsed = urllib.parse.urlparse(self.path)
            supplied = urllib.parse.parse_qs(parsed.query).get("t", [""])[0]
            if parsed.path != "/save" or not secrets.compare_digest(supplied, token):
                self.send_error(404); return
            if expired.is_set():
                self.send_error(410, "form expired"); return
            if not claim_state.try_claim():
                self.send_error(409, "submission already claimed"); return
            try:
                n = int(self.headers.get("Content-Length", 0))
            except ValueError:
                claim_state.release(); self.send_error(400); return
            if n <= 0 or n > args.max_bytes:
                claim_state.release(); self.send_error(413); return
            raw = self.rfile.read(n)
            if len(raw) != n:
                claim_state.release(); self.send_error(400, "incomplete request body"); return
            ctype = self.headers.get("Content-Type", "")
            try:
                media_type = ctype.split(";", 1)[0].strip().lower()
                if media_type == "multipart/form-data":
                    fields = parse_multipart(raw, ctype)
                elif media_type == "application/x-www-form-urlencoded":
                    q = urllib.parse.parse_qs(raw.decode("utf-8", "strict"), keep_blank_values=True)
                    fields = {k: (v[0].encode(), None) for k, v in q.items()}
                else:
                    raise ValueError("unsupported content type")
            except (UnicodeError, ValueError):
                claim_state.release(); self.send_error(400, "malformed form data"); return

            kv = {}

            # mode="file": a single field's content (pasted or uploaded) is the
            # target file itself, written verbatim.
            if mode == "file":
                f = spec["fields"][0] if spec["fields"] else None
                if not f:
                    self.send_error(400, "spec has no fields"); return
                i = 0
                data, filename = None, None
                if f.get("type") == "dual":
                    pasted = fields.get(f"f{i}_paste")
                    up = fields.get(f"f{i}_file")
                    if pasted and pasted[0].strip():
                        data, filename = pasted
                    elif up and up[1]:
                        data, filename = up
                else:
                    item = fields.get(f"f{i}")
                    if item:
                        data, filename = item
                if data is None:
                    claim_state.release(); self.send_error(400, "no content"); return
                try:
                    secure_replace(target, data if isinstance(data, bytes) else data.encode())
                except OSError:
                    claim_state.release(); self.send_error(400, "unsafe target"); return
                claim_state.consume()
                write_audit(args.audit_log, "saved-file", [spec["fields"][0]["key"]],
                            len(data) if isinstance(data, bytes) else len(data.encode()))
                body = DONE.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return

            for i, f in enumerate(spec["fields"]):
                key = f["key"]
                ftype = f.get("type")

                if ftype == "dual":
                    pasted = fields.get(f"f{i}_paste")
                    up = fields.get(f"f{i}_file")
                    use_paste = pasted and pasted[0].strip()
                    use_up = up and up[1]
                    if not use_paste and not use_up:
                        if f.get("optional"): continue
                        claim_state.release(); self.send_error(400, f"missing {key}"); return
                    if use_paste:
                        try:
                            kv[key] = pasted[0].decode("utf-8", "strict").strip()
                        except UnicodeError:
                            claim_state.release(); self.send_error(400, f"invalid text for {key}"); return
                    else:
                        assert up is not None
                        raw_data, filename = up
                        try:
                            dest = save_upload(files_dir, filename, raw_data)
                        except OSError:
                            claim_state.release(); self.send_error(400, "could not save upload"); return
                        kv[key] = dest
                    continue

                item = fields.get(f"f{i}")
                if item is None:
                    if f.get("optional"): continue
                    claim_state.release(); self.send_error(400, f"missing {key}"); return
                data, filename = item
                if ftype == "file":
                    if not filename:
                        if f.get("optional"): continue
                        claim_state.release(); self.send_error(400, f"no file for {key}"); return
                    try:
                        dest = save_upload(files_dir, filename, data)
                    except OSError:
                        claim_state.release(); self.send_error(400, "could not save upload"); return
                    kv[key] = dest
                else:
                    try:
                        val = data.decode("utf-8", "strict").strip()
                    except UnicodeError:
                        claim_state.release(); self.send_error(400, f"invalid text for {key}"); return
                    if not val:
                        if f.get("optional"): continue
                        claim_state.release(); self.send_error(400, f"missing {key}"); return
                    kv[key] = val
            try:
                upsert(target, kv)
            except (OSError, ValueError):
                claim_state.release(); self.send_error(400, "unsafe value or target"); return
            claim_state.consume()
            write_audit(args.audit_log, "saved-env", sorted(kv), sum(len(v) for v in kv.values()))
            body = DONE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            threading.Thread(target=self.server.shutdown, daemon=True).start()

    try:
        bind = validate_bind(args.bind, args.allow_wildcard)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    with socketserver.ThreadingTCPServer((bind, args.port), H) as httpd:
        httpd.daemon_threads = True
        host = public_host(bind)
        print(f"URL: http://{host}:{args.port}/?t={token}")
        print(f"TARGET: {target}")
        if expires_seconds:
            print(f"EXPIRES: {expires_seconds}s")
        print("Waiting for one submission...")
        timer = None
        if expires_seconds:
            def _expire():
                # Mark the form dead first (POST/GET now answer 410), then keep the
                # socket alive for a short grace period so a late visitor gets a page
                # instead of a bare connection-refused error.
                expired.set()
                time.sleep(EXPIRY_GRACE_SECONDS)
                httpd.shutdown()
            timer = threading.Timer(expires_seconds, _expire)
            timer.daemon = True
            timer.start()
        try:
            httpd.serve_forever()
        finally:
            if timer is not None:
                timer.cancel()
    if expired.is_set():
        print("Expired; server stopped, nothing written.")
    else:
        print("Saved; server stopped.")


if __name__ == "__main__":
    main()
