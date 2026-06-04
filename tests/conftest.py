import os

# Must be set before any project module is imported; config.py and smb/helpers.py
# read these at module level.
os.environ.setdefault("SMB_HOST", "testhost")
os.environ.setdefault("SMB_SHARE", "testshare")
os.environ.setdefault("SMB_USERNAME", "testuser")
os.environ.setdefault("SMB_PASSWORD", "testpass")

from unittest.mock import MagicMock


class MockMCP:
    """Minimal MCP stand-in that captures tool registrations."""

    def __init__(self):
        self._tools: dict = {}

    def tool(self):
        def decorator(fn):
            self._tools[fn.__name__] = fn
            return fn
        return decorator


def make_dir_entry(name: str, *, is_dir: bool = False, size: int = 0) -> MagicMock:
    """Build a fake smbclient DirEntry."""
    entry = MagicMock()
    entry.name = name
    entry.is_dir.return_value = is_dir
    stat_result = MagicMock()
    stat_result.st_size = size
    entry.stat.return_value = stat_result
    return entry


def make_stat(
    size: int = 100,
    mtime: float = 1_717_200_000.0,
    ctime: float = 1_717_100_000.0,
) -> MagicMock:
    """Build a fake smbclient stat result."""
    st = MagicMock()
    st.st_size = size
    st.st_mtime = mtime
    st.st_ctime = ctime
    return st
