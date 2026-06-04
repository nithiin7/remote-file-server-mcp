import fnmatch
import json
import os
import posixpath

from utils.logger import log

# ---------------------------------------------------------------------------
# Sensitive file denylist (glob patterns matched against the filename)
# ---------------------------------------------------------------------------

DENIED_FILENAME_PATTERNS: list[str] = [
    ".env",
    "*.env",
    "*.key",
    "*.pem",
    "*.p12",
    "*.pfx",
    "*.crt",
    "*.cer",
    "*.der",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa.pub",
    "*.secret",
    "*.token",
    "credentials",
    "credentials.*",
    ".netrc",
    ".htpasswd",
    "*.kdbx",          # KeePass database
    "*.keystore",
    "*.jks",           # Java keystore
    "*.bak",           # backups of any of the above (e.g. id_rsa_backup, production.pem.bak)
]

# Optional allowlist: restrict access to specific subdirectories.
# Stored as a list of normalised forward-slash paths without leading slash.
_raw_allowed = os.environ.get("ALLOWED_PATHS", "").strip()
ALLOWED_PATHS: list[str] = (
    [p.strip().strip("/").replace("\\", "/") for p in _raw_allowed.split(",") if p.strip()]
    if _raw_allowed
    else []
)

for _p in ALLOWED_PATHS:
    if ".." in _p.split("/"):
        raise ValueError(
            f"ALLOWED_PATHS contains an unsafe entry: {_p!r}. "
            "Paths must not contain '..' components."
        )


def safe_relative_path(path: str) -> str:
    """
    Normalise and validate a caller-supplied relative path.

    - Converts all separators to forward slashes.
    - Resolves '.' and '..' via posixpath.normpath so that traversal
      sequences are collapsed before any check is applied.
    - Rejects paths that resolve outside the share root (i.e. start with '..').
    - Enforces ALLOWED_PATHS if configured.

    Returns the clean relative path (no leading slash, forward slashes).
    Raises ValueError with a generic message on any violation.
    """
    # Normalise separators, strip leading slashes
    normalised = path.replace("\\", "/").lstrip("/")

    # Collapse . and .. segments
    resolved = posixpath.normpath(normalised) if normalised else "."

    # posixpath.normpath("") returns "." which we treat as root
    if resolved == ".":
        resolved = ""

    # Block traversal outside the share root
    if resolved.startswith(".."):
        raise ValueError("Access denied: path resolves outside the share root.")

    # Enforce ALLOWED_PATHS allowlist
    if ALLOWED_PATHS:
        allowed = any(
            resolved == ap or resolved.startswith(ap.rstrip("/") + "/")
            for ap in ALLOWED_PATHS
        )
        if not allowed:
            raise ValueError("Access denied: path is not within an allowed directory.")

    return resolved


def check_filename_denylist(name: str) -> None:
    """
    Raise ValueError if the filename matches any sensitive file pattern.
    Checked against the bare filename only (not the full path).
    """
    lower = name.lower()
    for pattern in DENIED_FILENAME_PATTERNS:
        if fnmatch.fnmatch(lower, pattern.lower()):
            raise ValueError("Access denied: this file type is not permitted.")


def sanitised_error(exc: Exception) -> str:
    """
    Return a generic, non-leaking error payload.
    The real exception is logged server-side only.
    """
    log.error("Operation failed: %s", exc, exc_info=True)
    name = type(exc).__name__
    if "NotFound" in name or "NoSuchFile" in name or "ObjectNotFound" in name:
        return json.dumps({"error": "The requested path was not found."})
    if "PermissionError" in name or "AccessDenied" in name or "LogonFailure" in name:
        return json.dumps({"error": "Permission denied."})
    if "Timeout" in name or "Connection" in name:
        return json.dumps({"error": "Could not reach the file server. Try again later."})
    return json.dumps({"error": "An unexpected error occurred. Check server logs for details."})
