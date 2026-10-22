#!/usr/bin/env python3
import importlib.util
import os
import stat
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("secret_form", ROOT / "scripts/secret_form.py")
if spec is None or spec.loader is None:
    raise RuntimeError("could not load scripts/secret_form.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class SecretFormTests(unittest.TestCase):
    def test_terminal_theme_and_adaptive_fields_without_network_claim(self):
        form = {
            "title": "Email delivery setup",
            "subtitle": "Sender identity and signing credential",
            "fields": [
                {"key": "EMAIL", "label": "Sender email", "type": "text"},
                {"key": "KEY", "label": "Secret key", "type": "password"},
                {"key": "CFG", "label": "Config", "type": "dual", "optional": True},
            ],
        }
        page = mod.build_page(mod.validate_spec(form), "test-token", True)
        for item in ("secret_vault", "LIVE / SINGLE USE", "Sender email", "Secret key", "f2_paste", "f2_file"):
            self.assertIn(item, page)
        self.assertNotIn("Tailscale access only", page)

    def test_html_is_escaped(self):
        form = {"title": "<script>x</script>", "fields": [{"key": "A", "label": "<b>x</b>", "type": "text"}]}
        page = mod.build_page(mod.validate_spec(form), "token", False)
        self.assertNotIn("<script>x</script>", page)
        self.assertIn("&lt;script&gt;x&lt;/script&gt;", page)
        self.assertIn("&lt;b&gt;x&lt;/b&gt;", page)

    def test_rejects_invalid_field_key(self):
        with self.assertRaises(SystemExit):
            mod.validate_spec({"fields": [{"key": "BAD-KEY", "type": "password"}]})

    def test_env_serialization_escapes_line_controls_and_backslashes(self):
        value = "first\\literal\rINJECT=bad\nNEXT=bad"
        self.assertEqual(
            mod.serialize_env_value(value),
            r"first\\literal\rINJECT=bad\nNEXT=bad",
        )

    def test_env_serialization_rejects_nul(self):
        with self.assertRaises(ValueError):
            mod.serialize_env_value("before\0after")

    def test_upsert_cannot_inject_additional_env_lines(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "secrets.env"
            mod.upsert(str(path), {"SAFE": "value\rINJECTED=one\nSECOND=two"})
            self.assertEqual(
                path.read_text().splitlines(),
                [r"SAFE=value\rINJECTED=one\nSECOND=two"],
            )

    def test_upsert_creates_mode_600_atomically(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "secrets.env"
            mod.upsert(str(path), {"EXAMPLE_KEY": "test-value"})
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(path.read_text(), "EXAMPLE_KEY=test-value\n")

    def test_secure_creation_requests_0600_at_open_time(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "secret"
            real_open = os.open
            create_modes = []

            def recording_open(name, flags, mode=0o777):
                if flags & os.O_CREAT:
                    create_modes.append((flags, mode))
                return real_open(name, flags, mode)

            with mock.patch.object(mod.os, "open", side_effect=recording_open):
                mod.secure_replace(str(path), b"value")
            self.assertEqual(len(create_modes), 1)
            flags, mode = create_modes[0]
            self.assertTrue(flags & os.O_EXCL)
            self.assertEqual(mode, 0o600)

    def test_upsert_replacement_remains_mode_600(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "secrets.env"
            path.write_text("OLD=value\n")
            path.chmod(0o666)
            mod.upsert(str(path), {"NEW": "value"})
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(path.read_text(), "OLD=value\nNEW=value\n")

    def test_upsert_rejects_symlink_target_without_touching_referent(self):
        with tempfile.TemporaryDirectory() as d:
            victim = Path(d) / "victim"
            victim.write_text("safe")
            link = Path(d) / "secrets.env"
            link.symlink_to(victim)
            with self.assertRaises(OSError):
                mod.upsert(str(link), {"KEY": "value"})
            self.assertEqual(victim.read_text(), "safe")
            self.assertTrue(link.is_symlink())

    def test_secure_write_rejects_symlink_target(self):
        with tempfile.TemporaryDirectory() as d:
            victim = Path(d) / "victim"
            victim.write_bytes(b"safe")
            link = Path(d) / "config.json"
            link.symlink_to(victim)
            with self.assertRaises(OSError):
                mod.secure_replace(str(link), b"secret")
            self.assertEqual(victim.read_bytes(), b"safe")

    def test_upload_names_are_random_unique_and_ignore_client_filename(self):
        with tempfile.TemporaryDirectory() as d:
            first = Path(mod.save_upload(d, "same.pem", b"one"))
            second = Path(mod.save_upload(d, "same.pem", b"two"))
            self.assertNotEqual(first, second)
            self.assertNotEqual(first.name, "same.pem")
            self.assertEqual(first.suffix, ".pem")
            self.assertEqual(first.read_bytes(), b"one")
            self.assertEqual(second.read_bytes(), b"two")
            self.assertEqual(stat.S_IMODE(first.stat().st_mode), 0o600)

    def test_upload_never_overwrites_preexisting_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            victim = Path(d) / "victim"
            victim.write_bytes(b"safe")
            (Path(d) / "fixed.bin").symlink_to(victim)
            names = iter(["fixed", "fresh"])
            result = mod.save_upload(d, "x.bin", b"secret", random_name=lambda: next(names))
            self.assertEqual(Path(result).name, "fresh.bin")
            self.assertEqual(victim.read_bytes(), b"safe")

    def test_upload_directory_is_created_mode_700(self):
        with tempfile.TemporaryDirectory() as d:
            directory = Path(d) / "uploads"
            result = mod.save_upload(str(directory), "x.bin", b"secret")
            self.assertEqual(stat.S_IMODE(directory.stat().st_mode), 0o700)
            self.assertEqual(Path(result).read_bytes(), b"secret")

    def test_upload_rejects_symlinked_directory(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            victim = root / "victim"
            victim.mkdir()
            link = root / "uploads"
            link.symlink_to(victim, target_is_directory=True)
            with self.assertRaises(OSError):
                mod.save_upload(str(link), "x.bin", b"secret")
            self.assertEqual(list(victim.iterdir()), [])

    def test_upload_rejects_symlinked_parent_component(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            victim = root / "victim"
            victim.mkdir()
            link = root / "linked-parent"
            link.symlink_to(victim, target_is_directory=True)
            with self.assertRaises(OSError):
                mod.save_upload(str(link / "uploads"), "x.bin", b"secret")
            self.assertEqual(list(victim.iterdir()), [])

    def test_multipart_is_binary_safe_with_quoted_boundary(self):
        binary = b"\x00alpha\r\n--not-the-boundary--\xff\r\n--hyphens--\r\n"
        body = (
            b"--AaB03x\r\n"
            b'Content-Disposition: form-data; name="f0"; filename="blob.bin"\r\n'
            b"Content-Type: application/octet-stream\r\n\r\n"
            + binary
            + b"\r\n--AaB03x--\r\n"
        )
        fields = mod.parse_multipart(body, 'multipart/form-data; boundary="AaB03x"')
        self.assertEqual(fields["f0"], (binary, "blob.bin"))

    def test_multipart_rejects_missing_boundary(self):
        with self.assertRaises(ValueError):
            mod.parse_multipart(b"anything", "multipart/form-data")

    def test_multipart_rejects_malformed_body(self):
        with self.assertRaises(ValueError):
            mod.parse_multipart(b"not multipart", "multipart/form-data; boundary=abc")

    def test_multipart_preserves_trailing_crlf_and_boundary_like_hyphens(self):
        payload = b"ends-with-crlf\r\n\r\n--abc-not-a-delimiter--"
        body = (
            b"--abc\r\nContent-Disposition: form-data; name=\"f0\"; filename=\"x\"\r\n\r\n"
            + payload
            + b"\r\n--abc--\r\n"
        )
        self.assertEqual(
            mod.parse_multipart(body, "multipart/form-data; boundary=abc")["f0"][0],
            payload,
        )

    def test_multipart_rejects_duplicate_field_names(self):
        body = (
            b"--x\r\nContent-Disposition: form-data; name=\"f0\"\r\n\r\na\r\n"
            b"--x\r\nContent-Disposition: form-data; name=\"f0\"\r\n\r\nb\r\n--x--\r\n"
        )
        with self.assertRaises(ValueError):
            mod.parse_multipart(body, "multipart/form-data; boundary=x")

    def test_claim_state_allows_exactly_one_concurrent_claim(self):
        state = mod.ClaimState()
        barrier = threading.Barrier(16)
        results = []
        lock = threading.Lock()

        def claim():
            barrier.wait()
            result = state.try_claim()
            with lock:
                results.append(result)

        threads = [threading.Thread(target=claim) for _ in range(16)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(results.count(True), 1)
        self.assertEqual(results.count(False), 15)

    def test_failed_claim_can_be_released_but_consumed_claim_cannot(self):
        state = mod.ClaimState()
        self.assertTrue(state.try_claim())
        state.release()
        self.assertTrue(state.try_claim())
        state.consume()
        self.assertFalse(state.try_claim())

    def test_ipv6_wildcard_is_rejected(self):
        with self.assertRaises(ValueError):
            mod.validate_bind("::")
        self.assertEqual(mod.validate_bind("127.0.0.1"), "127.0.0.1")

    def test_wildcard_bind_is_denied_unless_explicitly_allowed(self):
        for wildcard in ("0.0.0.0", "*", ""):
            with self.assertRaises(ValueError):
                mod.validate_bind(wildcard)
            self.assertEqual(mod.validate_bind(wildcard, allow_wildcard=True), wildcard)

    def test_page_reports_single_use_and_optional_countdown(self):
        form = {"title": "T", "fields": [{"key": "K", "label": "Key", "type": "password"}]}
        plain = mod.build_page(mod.validate_spec(form), "tok", False)
        self.assertIn("single use", plain)
        self.assertNotIn("closes in", plain)
        self.assertNotIn("expiry: after first save", plain)

        timed = mod.build_page(mod.validate_spec(form), "tok", False, expires_seconds=600)
        self.assertIn('id="cd"', timed)
        self.assertIn("closes in", timed)
        self.assertIn("var left = 600", timed)

    def test_expired_page_is_available_and_has_no_secret(self):
        self.assertIn("This form expired", mod.EXPIRED)
        self.assertIn("secret_vault", mod.EXPIRED)

    def test_audit_line_has_fields_and_bytes_but_no_values(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "audit.log")
            mod.write_audit(path, "saved-env", ["API_KEY", "ACCOUNT"], 42)
            mod.write_audit(None, "saved-env", ["X"], 1)  # no-op
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)
            self.assertIn("saved-env", text)
            self.assertIn("fields=API_KEY,ACCOUNT", text)
            self.assertIn("bytes=42", text)
            self.assertNotIn("secret", text)

    def test_labels_are_programmatically_associated(self):
        form = {"title": "T", "fields": [
            {"key": "A", "label": "Alpha", "type": "text"},
            {"key": "B", "label": "Beta", "type": "password"},
            {"key": "C", "label": "Gamma", "type": "dual"},
            {"key": "D", "label": "Delta", "type": "code"},
        ]}
        page = mod.build_page(mod.validate_spec(form), "tok", True)
        for i, label in enumerate(("Alpha", "Beta", "Gamma", "Delta")):
            self.assertIn(f'<label for="f{i}">{label}', page)
        self.assertIn('id="f0"', page)
        self.assertIn('id="f1"', page)
        self.assertIn('id="f2_paste"', page)
        self.assertIn('id="f2_file"', page)
        self.assertIn('id="f3"', page)
        self.assertEqual(page.count('<label for="f2">'), 1)

    def test_version_string_exists(self):
        self.assertRegex(mod.__version__, r"^\d+\.\d+\.\d+$")


if __name__ == "__main__":
    unittest.main()
