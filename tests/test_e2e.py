#!/usr/bin/env python3
"""End-to-end tests over a real socket.

The unit suite covers rendering and file handling; these tests prove the actual
HTTP behaviour a user experiences: one-shot save, refusal after expiry, token
checking, and the value-free audit line.
"""
import http.client
import json
import os
import re
import socket
import stat
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "secret_form.py")


def free_port():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class FormProcess:
    def __init__(self, spec, extra_args=()):
        self.dir = tempfile.mkdtemp(prefix="cif-e2e-")
        self.spec_path = os.path.join(self.dir, "spec.json")
        with open(self.spec_path, "w", encoding="utf-8") as fh:
            json.dump(spec, fh)
        self.port = free_port()
        self.audit = os.path.join(self.dir, "audit.log")
        cmd = [
            sys.executable, "-u", SCRIPT,
            "--spec", self.spec_path,
            "--bind", "127.0.0.1",
            "--port", str(self.port),
            "--audit-log", self.audit,
        ] + list(extra_args)
        self.proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        assert self.proc.stdout is not None
        self.url = self._wait_for_url()

    def _wait_for_url(self, timeout=10.0):
        stream = self.proc.stdout
        assert stream is not None
        deadline = time.time() + timeout
        while time.time() < deadline:
            line = stream.readline()
            if not line:
                if self.proc.poll() is not None:
                    break
                continue
            match = re.search(r"URL: (\S+)", line)
            if match:
                return match.group(1)
        rest = stream.read() if not stream.closed else ""
        raise AssertionError("server did not print a URL:\n" + (rest or ""))

    @property
    def path(self):
        return "/?" + self.url.split("?", 1)[1]

    def close(self):
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        if self.proc.stdout:
            self.proc.stdout.close()


class EndToEndTests(unittest.TestCase):
    def setUp(self):
        self.spec = {
            "title": "E2E",
            "subtitle": "socket test",
            "target": os.path.join(tempfile.mkdtemp(prefix="cif-target-"), "secrets.env"),
            "mode": "env",
            "fields": [
                {"key": "ACCOUNT_ID", "label": "Account ID", "type": "text"},
                {"key": "API_KEY", "label": "API key", "type": "password"},
            ],
        }
        self.form = None

    def tearDown(self):
        if self.form:
            self.form.close()

    def _request(self, method, path, body=None, headers=None):
        assert self.form is not None
        conn = http.client.HTTPConnection("127.0.0.1", self.form.port, timeout=5)
        try:
            conn.request(method, path, body=body, headers=headers or {})
            resp = conn.getresponse()
            return resp.status, resp.read().decode("utf-8", "replace")
        finally:
            conn.close()

    def test_one_shot_save_writes_0600_and_audits_without_values(self):
        self.form = FormProcess(self.spec, ["--expire-minutes", "5"])
        status, page = self._request("GET", self.form.path)
        self.assertEqual(status, 200)
        for marker in ("secret_vault", "LIVE / SINGLE USE", "[ commit securely ]", "closes in"):
            self.assertIn(marker, page)

        self.assertEqual(self._request("GET", "/?t=wrong-token")[0], 404)

        body = "f0=acct-1&f1=super-secret-value"
        status, done = self._request(
            "POST", "/save?" + self.form.url.split("?", 1)[1], body,
            {"Content-Type": "application/x-www-form-urlencoded"},
        )
        self.assertEqual(status, 200)
        self.assertIn("Saved securely", done)

        self.form.proc.wait(timeout=10)
        self.assertEqual(self.form.proc.returncode, 0)

        target = self.spec["target"]
        self.assertTrue(os.path.exists(target))
        self.assertEqual(stat.S_IMODE(os.stat(target).st_mode), 0o600)
        with open(target, encoding="utf-8") as fh:
            content = fh.read()
        self.assertIn("API_KEY=super-secret-value", content)

        with open(self.form.audit, encoding="utf-8") as fh:
            audit = fh.read()
        self.assertIn("saved-env", audit)
        self.assertIn("fields=ACCOUNT_ID,API_KEY", audit)
        self.assertNotIn("super-secret-value", audit)

        # server is gone: a second submission cannot be delivered
        token = self.form.url.split("t=", 1)[1]
        with self.assertRaises(OSError):
            self._request("POST", "/save?t=" + token, body,
                          {"Content-Type": "application/x-www-form-urlencoded"})

    def test_form_expires_and_writes_nothing(self):
        self.form = FormProcess(self.spec, ["--expire-minutes", "0.02"])
        self.assertEqual(self._request("GET", self.form.path)[0], 200)

        # after the deadline the link must render an expired page, not a blank socket
        time.sleep(2.5)
        status, expired_page = self._request("GET", self.form.path)
        self.assertEqual(status, 410)
        self.assertIn("This form expired", expired_page)

        token = self.form.url.split("t=", 1)[1]
        status, _ = self._request(
            "POST", "/save?t=" + token, "f0=a&f1=b",
            {"Content-Type": "application/x-www-form-urlencoded"},
        )
        self.assertEqual(status, 410)

        self.form.proc.wait(timeout=20)
        self.assertEqual(self.form.proc.returncode, 0)
        self.assertFalse(os.path.exists(self.spec["target"]))
        self.assertFalse(os.path.exists(self.form.audit))

    def test_wildcard_bind_refused_at_startup(self):
        proc = subprocess.run(
            [sys.executable, SCRIPT, "--bind", "0.0.0.0", "--spec", self.form_spec_path()],
            capture_output=True, text=True, timeout=20, check=False,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("wildcard", (proc.stdout + proc.stderr).lower())

    def form_spec_path(self):
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as fh:
            json.dump(self.spec, fh)
        return path


if __name__ == "__main__":
    unittest.main()
