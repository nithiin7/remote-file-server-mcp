# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 0.1.x   | Yes       |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Please report security issues by emailing **nithinp150@gmail.com** with the subject line `[SECURITY] remote-file-server-mcp`.

Include as much of the following as you can:

- A description of the vulnerability and its potential impact
- Steps to reproduce or a proof-of-concept
- Affected versions
- Any suggested mitigations

You should receive a response within **72 hours**. If you do not, follow up to ensure the original message was received.

## Disclosure Policy

- Vulnerabilities will be investigated and a fix prepared before public disclosure.
- Once a fix is released, a GitHub Security Advisory will be published crediting the reporter (unless anonymity is requested).
- Please allow reasonable time (up to 90 days) for a fix before public disclosure.

## Scope

This project handles SMB/CIFS credentials and provides access to corporate file shares via an MCP server. Areas of particular concern include:

- Credential exposure (SMB username/password leaking via logs, error messages, or MCP tool responses)
- Path traversal bypasses that escape the configured share root
- Filename denylist bypasses that expose sensitive files (`.env`, private keys, certificates)
- Injection attacks through malformed file paths or SMB share names
- Insecure defaults that expose more of the filesystem than intended

## Out of Scope

- Vulnerabilities in upstream dependencies (report those to their maintainers)
- Issues that require physical access to the machine running the server
- Denial-of-service via resource exhaustion on the SMB server itself
