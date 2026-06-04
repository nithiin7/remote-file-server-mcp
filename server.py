"""
MCP server for SMB file server access.

Configure via environment variables:
  SMB_HOST          - IP or hostname of the SMB server (required)
  SMB_SHARE         - Share name (required)
  SMB_USERNAME      - Username (required)
  SMB_PASSWORD      - Password (required)
  SMB_PORT          - Port (default: 445)
  SMB_ENCRYPT       - Enable SMB encryption: "true"/"false" (default: false)
  MAX_FILE_SIZE_MB  - Maximum file size to read in MB (default: 10)
  ALLOWED_PATHS     - Comma-separated list of allowed subdirectory paths
                      within the share (default: unrestricted).
                      Example: "reports,finance/2024"
  AUDIT_LOG_PATH      - File path for structured JSON audit logs.
                        If unset, audit logs are written to stdout.
  READ_PREVIEW_LINES  - Number of lines to return when a file exceeds
                        MAX_FILE_SIZE_MB (default: 100). Set to 0 to
                        hard-error instead of truncating.
"""

from importlib.metadata import PackageNotFoundError, version as _pkg_version

try:
    __version__ = _pkg_version("file-server-mcp")
except PackageNotFoundError:
    __version__ = "unknown"

import config
import tools
from mcp.server.fastmcp import FastMCP
from smb.session import setup

config.validate()

mcp = FastMCP("file-server")

setup()
tools.register_all(mcp)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
