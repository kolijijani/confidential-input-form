---
name: confidential-input-form
description: "Use when a task needs a secret, credential, API key or sensitive file — serve a one-time private-network form, never chat."
tags: [security, credentials, private-network, form, secrets]
---

# Confidential input — adaptive private-network form

## Rule (never break)
NEVER ask the user for a password, API key, token, card number, private key,
or any secret **in chat**. NEVER type one yourself. Instead **design a form for
the task** and serve it over a trusted private network so the user fills it in
their own browser.

## Tool
`scripts/secret_form.py` — make the page fit the need; do not force the
need into fixed content. You decide the title, subtitle, fields, labels, field
types, optional status, entry method (type vs paste vs upload), and where values
land.

### Fixed visual system; adaptive content

Every form uses the built-in **Terminal Vault** visual system: near-black canvas,
acid-lime security accent, monospace field labels, `// secret_vault` identity,
`LIVE / SINGLE USE` state, and `[ commit securely ]` action. Do not redesign,
re-theme, or generate custom HTML per task. The design is the constant; the JSON
spec is the adaptive layer.

Do not force every task into a password form. Choose fields from the actual need:
email/username/account ID may be visible `text`; secrets are `password`; JSON,
YAML, PEM, config, notes, and uploads use `code`, `file`, or `dual`. Write a clear
task-specific title and subtitle. Never expose target paths or secret values in
the user-facing copy.

**Before serving, verify the generated HTML contains** `secret_vault`,
`LIVE / SINGLE USE`, every requested field label, and the expected input names.
This proves both layers: consistent theme and task-specific content.

### Example adaptation (email + secret key + optional config)

```json
{
  "title": "Email delivery setup",
  "subtitle": "Provide the sender identity and signing credential",
  "target": "~/.config/secret-vault/mail.env",
  "mode": "env",
  "fields": [
    {"key": "MAIL_FROM", "label": "Sender email", "type": "text"},
    {"key": "SIGNING_KEY", "label": "Signing key", "type": "password"},
    {"key": "MAIL_CONFIG", "label": "Optional config", "type": "dual", "optional": true}
  ]
}
```

### Think first (design the page)
Ask yourself, then encode the answer in the spec:
1. **What does this task actually need?** one key? a pair (user+pass)? several
   unrelated secrets? a **whole JSON/YAML/config block**? a key *file*?
2. **Which fields are secret?** Anything sensitive -> `password` (masked).
   Non-secret context (region, project name, account id) -> `text`.
3. **Will he PASTE a blob or UPLOAD a file?** If unsure, use `dual` — one field
   offering BOTH a paste box and a file picker; he picks. If it is a long config
   /JSON/kod, `code` gives a monospace paste box.
4. **Any field optional?** If the task works without it -> `optional: true`.
5. **Where should the values go?**
   - env vars -> `mode:"env"` (default), one `KEY=VALUE` per field.
   - the whole content IS one file (service-account JSON, `.pem`, config) ->
     `mode:"file"` with a single field; the pasted/uploaded content is written
     verbatim to `target`.
   Pick `--target` accordingly (`.env`, a `.json`, a `.secrets`, a `.pem`).
6. **Title & subtitle** should tell HIM in plain words what this form is for.

### Field types
- `text` — plain, visible (non-secret context)
- `password` — masked
- `textarea` — multi-line note / short paste
- `code` — multi-line monospace paste (JSON / YAML / PEM / code)
- `file` — file upload (saved to `secret_files/`, its path stored as the value)
- `dual` — **one field, two ways**: paste OR upload; he chooses. Ideal default
  when you are not sure which he will do.
- `optional: true` — key skipped if left blank.

### Two ways to build it
Simple (all text, one mask set):
```
python3 scripts/secret_form.py \
  --keys OPENAI_API_KEY \
  --labels "OpenAI API Key" --types password \
  --title "OpenAI Key" --subtitle "Untuk modul AI projek"
```
Adaptive (mixed types / dual / optional) — prefer this when in doubt:
```
python3 scripts/secret_form.py --spec - <<'JSON'
{
  "title": "Stripe Setup",
  "subtitle": "Stripe credentials for this project",
  "target": "~/.config/secret-vault/secrets.env",
  "mode": "env",
  "fields": [
    {"key": "STRIPE_PK",  "label": "Publishable key", "type": "text"},
    {"key": "STRIPE_SK",  "label": "Secret key",      "type": "password", "hint": "Paste the secret key here"},
    {"key": "STRIPE_WH",  "label": "Webhook secret",  "type": "password", "optional": true},
    {"key": "STRIPE_CERT","label": "Cert (tampal/upload)", "type": "dual"}
  ]
}
JSON
```
Whole-file mode (paste OR upload a service-account JSON):
```
python3 scripts/secret_form.py --spec - <<'JSON'
{
  "title": "Google Service Account",
  "subtitle": "Paste JSON or upload a .json file",
  "target": "~/.config/secret-vault/gcloud.json",
  "mode": "file",
  "fields": [
    {"key": "SA_JSON", "label": "Service account JSON", "type": "dual"}
  ]
}
JSON
```

### Flags
`--target` file to write (default `~/.config/secret-vault/secrets.env`, mode 600)
`--files-dir` where uploads land
`--bind` / `--port` (default `127.0.0.1:8731`; bind to a private-network interface when needed —
`0.0.0.0` is refused unless `--allow-wildcard` is passed)
`--expire-minutes` deadline in minutes (default 15; `0` disables it)
`--audit-log` append a value-free line per submission (time, outcome, field names, byte count)
`--version` print the version and exit

## Run it (background) then hand over the URL
```
python3 scripts/secret_form.py --bind <private-ip> --spec /tmp/spec.json --expire-minutes 20
```
It prints e.g. `URL: http://<private-ip>:8731/?t=<token>` and `EXPIRES: 1200s`.
Give that URL to the intended user over a private channel. The token means only the link holder can submit.
The server writes values straight to the target (never echoed, never logged) and
exits after the first successful save. If nobody submits before the deadline it exits and writes
nothing, so an abandoned link never stays open — raise `--expire-minutes` for multi-file tasks
instead of leaving the form open indefinitely.

## After he says "dah simpan"
1. Verify keys/content exist WITHOUT printing values:
   `grep -q '^KEY=' target && echo ok` (env mode) or
   `test -s target && echo ok` (file mode).
2. Confirm the server exited (one-shot).
3. Continue the task — read the secret only inside your script/from the file,
   never surface it in chat.

## Why
Chat transcripts, tool logs and model context all persist. A private network form
keeps the secret out of every one of them; direct-fill into the target (600)
makes it available to your scripts but never to the conversation.

## Pitfalls

- **Never echo or log secret values.** The server writes directly to the target file; never print values to stdout. When verifying, check existence with `grep -q` or `test -s`, never `cat`.
- **Wildcard binds are refused.** `--bind 0.0.0.0` exits with an error: pass the actual localhost or private-network address so the form cannot appear on an interface you did not intend.
- **One-shot server exits after first save.** If the user refreshes or submits twice, the server is already gone. Tell the user to fill everything in one go.
- **Token in URL is the only access control.** Anyone with the link can submit. Share the URL only with the intended user through a private channel.
- **`dual` fields need both paste and upload handling in POST.** The server checks `f<paste>` first, then `f<upload>_file`. If paste is blank, it falls back to the uploaded file. Test both paths before deploying.
- **`mode:"file"` writes raw content, not KEY=VALUE.** Use this when the target is a standalone file (JSON, PEM, YAML). The entire pasted/uploaded content becomes the file verbatim.
- **Optional fields are skipped entirely.** If a field has `optional: true` and is left blank, no key is written to the target. This is correct behavior — don't add empty keys.
