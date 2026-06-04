import json
import posixpath

import smbclient
from mcp.server.fastmcp import FastMCP

from config import MAX_FILE_SIZE_BYTES, READ_PREVIEW_LINES
from smb.helpers import smb_path
from smb.session import is_connection_error, with_reconnect
from utils.document_parsers import extract_document_text
from utils.logger import audit
from utils.validators import check_filename_denylist, safe_relative_path, sanitised_error


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    @with_reconnect
    def read_file(path: str) -> str:
        """
        Read the contents of a file from the SMB share.

        Args:
            path: Relative path to the file within the share.
                  Forward or back slashes are both accepted.
                  Parent directory traversal (..) is not permitted.

        Returns:
            File contents as a string, or a JSON error object.
            If the file exceeds MAX_FILE_SIZE_MB, the first READ_PREVIEW_LINES lines
            are returned with a truncation notice (set READ_PREVIEW_LINES=0 to hard-error
            instead). Binary files are identified by size but their contents are not returned.
        """
        try:
            relative = safe_relative_path(path)
            if not relative:
                audit("read_file", path, "denied", reason="empty path")
                return json.dumps({"error": "A file path is required."})
            filename = posixpath.basename(relative)
            check_filename_denylist(filename)
        except ValueError as exc:
            audit("read_file", path, "denied", reason=str(exc))
            return json.dumps({"error": str(exc)})

        smb_file = smb_path(relative)
        try:
            stat = smbclient.stat(smb_file)
            oversized = stat.st_size > MAX_FILE_SIZE_BYTES

            if oversized and READ_PREVIEW_LINES == 0:
                audit("read_file", relative, "denied",
                      reason="file_too_large", file_size_bytes=stat.st_size)
                return json.dumps({
                    "error": (
                        f"File is too large to read "
                        f"({stat.st_size // (1024 * 1024)} MB). "
                        f"Maximum allowed size is {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB."
                    )
                })

            try:
                with smbclient.open_file(smb_file, mode="r", encoding="utf-8") as f:
                    if oversized:
                        lines: list[str] = []
                        for _ in range(READ_PREVIEW_LINES):
                            line = f.readline()
                            if not line:
                                break
                            lines.append(line)
                        content = "".join(lines)
                        truncation_notice = (
                            f"\n\n[Truncated — showing first {READ_PREVIEW_LINES} lines of a "
                            f"{stat.st_size // (1024 * 1024)} MB file. "
                            f"Use get_file_info() to inspect the full size.]"
                        )
                        audit("read_file", relative, "truncated",
                              file_size_bytes=stat.st_size, preview_lines=READ_PREVIEW_LINES)
                        return content + truncation_notice
                    else:
                        content = f.read()
                        audit("read_file", relative, "success",
                              file_size_bytes=stat.st_size, encoding="utf-8")
                        return content
            except UnicodeDecodeError:
                if oversized:
                    audit("read_file", relative, "denied",
                          reason="file_too_large", file_size_bytes=stat.st_size)
                    return json.dumps({
                        "error": (
                            f"File is too large to read "
                            f"({stat.st_size // (1024 * 1024)} MB). "
                            f"Maximum allowed size is {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB."
                        )
                    })
                with smbclient.open_file(smb_file, mode="rb") as f:
                    data = f.read(MAX_FILE_SIZE_BYTES + 1)
                if len(data) > MAX_FILE_SIZE_BYTES:
                    audit("read_file", relative, "denied",
                          reason="file_too_large", file_size_bytes=len(data))
                    return json.dumps({
                        "error": (
                            f"File is too large to read "
                            f"({len(data) // (1024 * 1024)} MB). "
                            f"Maximum allowed size is {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB."
                        )
                    })
                extracted = extract_document_text(filename, data)
                if extracted is not None:
                    audit("read_file", relative, "success",
                          file_size_bytes=stat.st_size, encoding="document")
                    return extracted
                audit("read_file", relative, "success",
                      file_size_bytes=stat.st_size, encoding="binary")
                return f"[Binary file – {len(data):,} bytes, cannot display as text]"

        except ValueError as exc:
            audit("read_file", relative, "denied", reason=str(exc))
            return json.dumps({"error": str(exc)})
        except Exception as exc:
            if is_connection_error(exc):
                raise
            audit("read_file", relative, "error")
            return sanitised_error(exc)
