import functools
import sys

import smbclient

from config import SMB_HOST, SMB_PORT, SMB_USERNAME, SMB_PASSWORD, SMB_SHARE, SMB_ENCRYPT, SMB_TIMEOUT
from utils.logger import log

_RETRYABLE = frozenset({
    "SMBConnectionClosed",
    "BrokenPipeError",
    "ConnectionResetError",
    "ConnectionAbortedError",
})


def is_connection_error(exc: Exception) -> bool:
    return type(exc).__name__ in _RETRYABLE


def reconnect() -> None:
    log.warning("SMB connection lost — reconnecting to \\\\%s", SMB_HOST)
    try:
        smbclient.reset_connection_cache()
    except Exception:
        pass
    smbclient.register_session(
        SMB_HOST,
        username=SMB_USERNAME,
        password=SMB_PASSWORD,
        port=SMB_PORT,
        require_signing=True,
        encrypt=SMB_ENCRYPT,
        connection_timeout=SMB_TIMEOUT,
    )
    log.info("SMB reconnected to \\\\%s", SMB_HOST)


def with_reconnect(fn):
    """Retry fn once after re-registering the SMB session on connection drop."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            if not is_connection_error(exc):
                raise
            reconnect()
            return fn(*args, **kwargs)
    return wrapper


def setup() -> None:
    smbclient.register_session(
        SMB_HOST,
        username=SMB_USERNAME,
        password=SMB_PASSWORD,
        port=SMB_PORT,
        require_signing=True,
        encrypt=SMB_ENCRYPT,
        connection_timeout=SMB_TIMEOUT,
    )
    _check_connection()


def _check_connection() -> None:
    """
    Probe the share root to confirm the SMB connection and credentials are valid.
    Exits the process with a clear error message if the server is unreachable or
    authentication fails.
    """
    share_root = f"\\\\{SMB_HOST}\\{SMB_SHARE}"
    try:
        smbclient.stat(share_root)
        log.info("SMB session ready — connected to \\\\%s\\%s", SMB_HOST, SMB_SHARE)
    except Exception as exc:
        exc_type = type(exc).__name__
        if "LogonFailure" in exc_type or "AccessDenied" in exc_type:
            log.error(
                "SMB authentication failed. Check SMB_USERNAME and SMB_PASSWORD. (%s)",
                exc_type,
            )
        elif "ConnectionRefused" in exc_type or "Timeout" in exc_type or "NoSuchServer" in exc_type:
            log.error(
                "Cannot reach SMB server at %s:%d. Check SMB_HOST and SMB_PORT. (%s)",
                SMB_HOST, SMB_PORT, exc_type,
            )
        elif "ObjectNotFound" in exc_type or "BadNetworkName" in exc_type:
            log.error(
                "SMB share not found. Check SMB_SHARE. (%s)", exc_type,
            )
        else:
            log.error("SMB connection check failed: %s — %s", exc_type, exc)
        sys.exit(1)
