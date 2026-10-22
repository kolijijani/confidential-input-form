#!/usr/bin/env python3
"""Regenerate the README screenshot from the current form renderer."""
from __future__ import annotations

import importlib.util
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "scripts" / "secret_form.py"
OUTPUT = ROOT / "docs" / "screenshots" / "terminal-vault.png"

spec = importlib.util.spec_from_file_location("secret_form", MODULE)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load {MODULE}")
secret_form = importlib.util.module_from_spec(spec)
spec.loader.exec_module(secret_form)

form = {
    "title": "Email delivery setup",
    "subtitle": "Provide the sender identity and signing credential",
    "fields": [
        {"key": "MAIL_FROM", "label": "Sender email", "type": "text"},
        {"key": "SIGNING_KEY", "label": "Signing key", "type": "password"},
        {"key": "MAIL_CONFIG", "label": "Config bundle", "type": "dual", "optional": True},
    ],
}
html = secret_form.build_page(secret_form.validate_spec(form), "preview-token", True)
chrome = next((shutil.which(x) for x in ("google-chrome", "chromium", "chromium-browser") if shutil.which(x)), None)
if not chrome:
    raise SystemExit("Chrome/Chromium was not found")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory() as tmp:
    page = Path(tmp) / "preview.html"
    page.write_text(html, encoding="utf-8")
    subprocess.run([
        chrome, "--headless", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
        "--window-size=1440,1050", "--force-device-scale-factor=1",
        f"--screenshot={OUTPUT}", page.as_uri(),
    ], check=True)
print(OUTPUT)
