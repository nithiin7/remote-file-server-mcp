import os
import sys

from utils.logger import log

_REQUIRED_ENV = ["SMB_HOST", "SMB_SHARE", "SMB_USERNAME", "SMB_PASSWORD"]

SMB_HOST = os.environ.get("SMB_HOST", "")
SMB_PORT = int(os.environ.get("SMB_PORT", "445"))
SMB_USERNAME = os.environ.get("SMB_USERNAME", "")
SMB_PASSWORD = os.environ.get("SMB_PASSWORD", "")
SMB_SHARE = os.environ.get("SMB_SHARE", "")
SMB_ENCRYPT = os.environ.get("SMB_ENCRYPT", "true").lower() == "true"
SMB_TIMEOUT = int(os.environ.get("SMB_TIMEOUT", "30"))
MAX_FILE_SIZE_BYTES = int(os.environ.get("MAX_FILE_SIZE_MB", "10")) * 1024 * 1024
READ_PREVIEW_LINES = int(os.environ.get("READ_PREVIEW_LINES", "100"))


def validate() -> None:
    missing = [v for v in _REQUIRED_ENV if not os.environ.get(v)]
    if missing:
        log.error("Missing required environment variables: %s", ", ".join(missing))
        sys.exit(1)
