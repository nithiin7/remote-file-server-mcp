import os
import sys

from utils.logger import log

_REQUIRED_ENV = ["SMB_HOST", "SMB_SHARE", "SMB_USERNAME", "SMB_PASSWORD"]

_INT_VARS = {
    "SMB_PORT": "445",
    "SMB_TIMEOUT": "30",
    "MAX_FILE_SIZE_MB": "10",
    "READ_PREVIEW_LINES": "100",
}

SMB_HOST = os.environ.get("SMB_HOST", "")
SMB_PORT: int = 445
SMB_USERNAME = os.environ.get("SMB_USERNAME", "")
SMB_PASSWORD = os.environ.get("SMB_PASSWORD", "")
SMB_SHARE = os.environ.get("SMB_SHARE", "")
SMB_ENCRYPT = os.environ.get("SMB_ENCRYPT", "true").lower() == "true"
SMB_TIMEOUT: int = 30
MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024
READ_PREVIEW_LINES: int = 100


def _parse_int(name: str, default: str) -> int:
    raw = os.environ.get(name, default)
    try:
        return int(raw)
    except ValueError:
        log.error("Invalid value for %s: %r — must be an integer", name, raw)
        sys.exit(1)


def validate() -> None:
    missing = [v for v in _REQUIRED_ENV if not os.environ.get(v)]
    if missing:
        log.error("Missing required environment variables: %s", ", ".join(missing))
        sys.exit(1)

    global SMB_PORT, SMB_TIMEOUT, MAX_FILE_SIZE_BYTES, READ_PREVIEW_LINES
    SMB_PORT = _parse_int("SMB_PORT", "445")
    SMB_TIMEOUT = _parse_int("SMB_TIMEOUT", "30")
    MAX_FILE_SIZE_BYTES = _parse_int("MAX_FILE_SIZE_MB", "10") * 1024 * 1024
    raw_preview = _parse_int("READ_PREVIEW_LINES", "100")
    if raw_preview > 10_000:
        log.error(
            "READ_PREVIEW_LINES=%d exceeds the maximum of 10,000 — lower the value",
            raw_preview,
        )
        sys.exit(1)
    READ_PREVIEW_LINES = raw_preview
