import json

import smbclient

from smb.helpers import SEARCH_MAX_RESULTS, smb_path
from smb.session import is_connection_error, with_reconnect
from utils.logger import audit
from utils.validators import check_filename_denylist, safe_relative_path, sanitised_error


def register(mcp) -> None:
    @mcp.tool()
    @with_reconnect
    def list_files(path: str = "") -> str:
        """
        List files and directories at the given path on the SMB share.

        Args:
            path: Relative path within the share (empty string = root of share).
                  Forward or back slashes are both accepted.
                  Parent directory traversal (..) is not permitted.

        Returns:
            JSON object with key "entries": array of objects with keys: name, type ("file"|"directory"),
            size (bytes, null for dirs). Includes "truncated": true and a "note" when results are capped
            at 200 entries.
        """
        try:
            relative = safe_relative_path(path)
        except ValueError as exc:
            audit("list_files", path, "denied", reason=str(exc))
            return json.dumps({"error": str(exc)})

        smb_dir = smb_path(relative)
        try:
            entries: list[dict[str, object]] = []
            for entry in sorted(
                smbclient.scandir(smb_dir),
                key=lambda e: (not e.is_dir(), e.name.lower()),
            ):
                # Skip denied filenames silently in listings (don't reveal they exist)
                try:
                    check_filename_denylist(entry.name)
                except ValueError:
                    continue

                entries.append(
                    {
                        "name": entry.name,
                        "type": "directory" if entry.is_dir() else "file",
                        "size": None if entry.is_dir() else entry.stat().st_size,
                    }
                )
                if len(entries) == SEARCH_MAX_RESULTS:
                    break

            result: dict[str, object] = {"entries": entries}
            if len(entries) == SEARCH_MAX_RESULTS:
                result["truncated"] = True
                result["note"] = f"Results limited to {SEARCH_MAX_RESULTS} entries. Refine the path to see more."
            audit("list_files", relative, "success", entry_count=len(entries), truncated=len(entries) == SEARCH_MAX_RESULTS)
            return json.dumps(result, indent=2)
        except ValueError as exc:
            audit("list_files", relative, "denied", reason=str(exc))
            return json.dumps({"error": str(exc)})
        except Exception as exc:
            if is_connection_error(exc):
                raise
            audit("list_files", relative, "error")
            return sanitised_error(exc)
