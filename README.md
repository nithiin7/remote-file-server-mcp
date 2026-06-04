# remote-file-server-mcp

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that gives any MCP client read access to an SMB/CIFS file share. Connection credentials are passed as environment variables and never appear in tool calls or conversation history.

---

## How It Works

```
MCP Client  ──(MCP/stdio)──►  file-server-mcp  ──(SMB/CIFS)──►  File Server
```

The server runs as a subprocess managed by the MCP client. All file access is read-only. SMB packet signing is enforced by default; full encryption is available via an env var.

---

## Tools

| Tool            | Arguments                                            | Description                                                                                                                                                                            |
| --------------- | ---------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `list_files`    | `path` (optional)                                    | List files and directories at a path. Empty path = share root. Denied filenames are omitted from results. Returns JSON.                                                                |
| `read_file`     | `path`                                               | Return text contents of a file. Oversized files return a preview (first N lines) or hard-error if `READ_PREVIEW_LINES=0`. Binary Office/PDF files are parsed into text when supported. |
| `get_file_info` | `path`                                               | Return metadata (size, type, timestamps) for a file or directory without reading its contents.                                                                                         |
| `search_files`  | `pattern`, `path` (optional), `max_depth` (optional) | Find files by glob pattern (e.g. `*.csv`). Recurses to `max_depth` (default `5`, max `10`) and returns up to `200` matches.                                                            |

All paths are relative to the share root (e.g. `reports/2024/q1.xlsx`).

---

## Security

- **SMB packet signing** is required on all connections (protects against tampering in transit).
- **Encryption** can be enabled via `SMB_ENCRYPT=true` for end-to-end SMB encryption.
- **Path traversal** is blocked — `..` segments are rejected before any SMB call is made.
- **Sensitive files** (`.env`, `*.key`, `*.pem`, `*.bak`, `id_rsa`, `*.pfx`, `*.p12`, `*.token`, `.netrc`, `.htpasswd`, keystore files, etc.) are never listed or read. The denylist covers well-known patterns but is **not exhaustive** — `ALLOWED_PATHS` is the stronger control and should be used in production to restrict access to only the directories the model needs.
- **File size limit** prevents reading files that would exceed the context window.
- **Allowed paths** can restrict the server to specific subdirectories only (recommended for production).
- **Audit logging** records every tool call (operation, path, outcome, size) in JSON — never file contents.
- Error messages are sanitised — internal hostnames, UNC paths, and credentials are never exposed to the client.

---

## Setup

### Option A — pip install

```bash
pip install -e /path/to/remote-file-server
```

Then configure Claude Desktop (see below) with:

```json
"command": "file-server-mcp"
```

### Option B — run from source (no package install)

```bash
python3 -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python server.py
```

### Option C — uv

```bash
# No install needed — uv resolves dependencies automatically
uv run --directory /path/to/remote-file-server file-server-mcp
```

Or install into a uv-managed environment:

```bash
uv pip install -e /path/to/remote-file-server
uv run file-server-mcp
```

### Option D — Docker

```bash
docker build -t file-server-mcp .
```

See `Dockerfile` for runtime usage.

---

## MCP Client Configuration

Open your Client config file:

Add an entry under `mcpServers`.

**If using `uv` (run from source, no prior install):**

```json
{
  "mcpServers": {
    "file-server": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/path/to/remote-file-server",
        "file-server-mcp"
      ],
      "env": {
        "SMB_HOST": "192.168.1.100",
        "SMB_SHARE": "my_share",
        "SMB_USERNAME": "my_user",
        "SMB_PASSWORD": "my_password"
      }
    }
  }
}
```

**If installed via pip/uv pip (console script entry point):**

```json
{
  "mcpServers": {
    "file-server": {
      "command": "file-server-mcp",
      "env": {
        "SMB_HOST": "192.168.1.100",
        "SMB_SHARE": "my_share",
        "SMB_USERNAME": "my_user",
        "SMB_PASSWORD": "my_password",
        "SMB_PORT": "445",
        "ALLOWED_PATHS": "reports,finance",
        "AUDIT_LOG_PATH": "/var/log/file-server-mcp/audit.jsonl"
      }
    }
  }
}
```

> **Security note:** The config file contains credentials. Ensure it is only readable by your user account (`chmod 600` on macOS/Linux).

Restart Claude Desktop after saving.

### Connecting to Multiple Servers

Add a separate entry for each server with a unique key:

```json
{
  "mcpServers": {
    "file-server-prod": {
      "command": "file-server-mcp",
      "env": {
        "SMB_HOST": "10.0.0.10",
        "SMB_SHARE": "Production",
        "...": "..."
      }
    },
    "file-server-dev": {
      "command": "file-server-mcp",
      "env": {
        "SMB_HOST": "10.0.0.20",
        "SMB_SHARE": "Development",
        "...": "..."
      }
    }
  }
}
```

---

## Environment Variables

| Variable             | Required | Default | Description                                                           |
| -------------------- | -------- | ------- | --------------------------------------------------------------------- |
| `SMB_HOST`           | Yes      | —       | IP address or hostname of the SMB server                              |
| `SMB_SHARE`          | Yes      | —       | Share name on the server                                              |
| `SMB_USERNAME`       | Yes      | —       | Username for SMB authentication                                       |
| `SMB_PASSWORD`       | Yes      | —       | Password for SMB authentication                                       |
| `SMB_PORT`           | No       | `445`   | SMB port                                                              |
| `SMB_ENCRYPT`        | No       | `true`  | Set to `false` to disable SMB encryption (not recommended)            |
| `SMB_TIMEOUT`        | No       | `30`    | Seconds before an SMB connect or operation times out                  |
| `MAX_FILE_SIZE_MB`   | No       | `10`    | Maximum file size in MB that `read_file` will read                    |
| `READ_PREVIEW_LINES` | No       | `100`   | Lines to return for oversized files. Set to `0` to hard-error instead |
| `ALLOWED_PATHS`      | No       | —       | Comma-separated subdirectory allowlist, e.g. `reports,finance/2024`   |
| `AUDIT_LOG_PATH`     | No       | stdout  | File path for JSON audit logs. Falls back to stdout if unset          |

---

## Requirements

- Python 3.11+
- Network access to the SMB server (port 445 by default)
- SMB credentials with read permissions on the share
