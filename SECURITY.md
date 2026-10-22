# Security

## Threat model

Secret Vault is a local-network handoff utility, not an internet-facing secret manager. Version 1.0 supports Linux and macOS, where it can enforce POSIX permission and symlink guarantees. Run it only on a trusted machine and expose it through a private network such as Tailscale, a VPN, or localhost.

- The random URL token prevents accidental access; it is not a replacement for TLS or network access control.
- HTTP is unencrypted. Do not expose the default server directly to the public internet.
- Submitted values are atomically written locally through mode-`0600` temporary files; symlink targets are rejected. Values are never echoed or request-logged by the app.
- The server accepts one successful submission and then exits; if nobody submits before the deadline
  (`--expire-minutes`, 15 by default) it exits and writes nothing.
- Uploaded files receive random server-side names and are created exclusively with mode `0600`. Protect and rotate them as you would any credential.

## What this does not protect against

Secret Vault moves a secret from a browser into a file without crossing chat logs. It is not a
vault, and the following are explicitly out of scope:

- **A compromised host.** Anyone who can read the target file, the process memory, or attach a
  debugger gets the secret. Root on the machine defeats every control here.
- **A compromised browser or extension.** The value passes through the page you type it into.
- **Observation.** Screen sharing, recordings, shoulder surfing, and clipboard managers are outside
  the tool's control.
- **Persistence elsewhere.** Backups, snapshots, swap, and crash dumps of the host may contain the
  value; rotate the credential if the machine is lost or reimaged.
- **Transport encryption.** The built-in server speaks plain HTTP. Use localhost, a private overlay
  network such as Tailscale, or a TLS-terminating proxy; do not publish the port.
- **Rotation and revocation.** After the handoff the secret is a normal file. Rotation, scope
  reduction, and revocation stay your job, at the provider.

The deadline (`--expire-minutes`, 15 by default) and the single-use claim limit the window in which
a leaked link is useful. They do not make a weak token safe, so share the URL only with the intended
person, over a private channel.

## Reporting a vulnerability

Please open a private GitHub security advisory instead of a public issue. Do not include real credentials in reports.
