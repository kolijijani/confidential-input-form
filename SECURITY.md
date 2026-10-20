# Security

## Threat model

Terminal Vault is a local-network handoff utility, not an internet-facing secret manager. Version 1.0 supports Linux and macOS, where it can enforce POSIX permission and symlink guarantees. Run it only on a trusted machine and expose it through a private network such as Tailscale, a VPN, or localhost.

- The random URL token prevents accidental access; it is not a replacement for TLS or network access control.
- HTTP is unencrypted. Do not expose the default server directly to the public internet.
- Submitted values are atomically written locally through mode-`0600` temporary files; symlink targets are rejected. Values are never echoed or request-logged by the app.
- The server accepts one successful submission and then exits.
- Uploaded files receive random server-side names and are created exclusively with mode `0600`. Protect and rotate them as you would any credential.

## Reporting a vulnerability

Please open a private GitHub security advisory instead of a public issue. Do not include real credentials in reports.
