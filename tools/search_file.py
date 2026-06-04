import json

import smbclient

from smb.helpers import SEARCH_MAX_RESULTS, collect_matches, smb_path
from smb.session import is_connection_error, with_reconnect
from utils.logger import audit
from utils.validators import safe_relative_path, sanitised_error


def register(mcp) -> None:
    @mcp.tool()
    @with_reconnect
    def search_files(pattern: str, path: str = "", max_depth: int = 5) -> str:
        """
        Search for files whose names match a glob pattern within a directory subtree.

        Args:
            pattern:   Glob pattern to match against filenames.
                       MUST include a wildcard (*) to match multiple files, e.g. "*.txt",
                       "*.csv", "report_*", "*budget*". To find a specific file by exact
                       name, pass the full filename, e.g. "notes.txt". Patterns without
                       a wildcard only match files with that exact name.
            path:      Relative path to the directory to search within (default: share root).
                       Forward or back slashes are both accepted.
                       Parent directory traversal (..) is not permitted.
            max_depth: Maximum directory depth to recurse into (default: 5, max: 10).
                       Use 1 to search only the immediate directory.

        Returns:
            JSON object with key "results": array of objects with keys: path (relative to share root),
            name, size_bytes. Includes "truncated": true and a "note" when capped at 200 results.
            Denied files are excluded silently.
        """
        max_depth = min(max(1, max_depth), 10)  # clamp: 1–10

        # Auto-correct bare extension patterns: ".txt" → "*.txt"
        if pattern.startswith(".") and "*" not in pattern:
            pattern = f"*{pattern}"

        try:
            relative = safe_relative_path(path)
        except ValueError as exc:
            audit("search_files", path, "denied", reason=str(exc), pattern=pattern)
            return json.dumps({"error": str(exc)})

        smb_base = smb_path(relative)
        base_depth = smb_base.count("\\")

        try:
            results: list[dict[str, object]] = []

            for dirpath, dirnames, filenames in smbclient.walk(smb_base):
                current_depth = dirpath.count("\\") - base_depth
                if current_depth >= max_depth:
                    dirnames.clear()  # prevent walk from descending further
                    continue

                results.extend(collect_matches(dirpath, filenames, pattern))

                if len(results) >= SEARCH_MAX_RESULTS:
                    results = results[:SEARCH_MAX_RESULTS]
                    audit("search_files", relative, "success",
                          pattern=pattern, result_count=len(results), capped=True)
                    return json.dumps({
                        "results": results,
                        "truncated": True,
                        "note": f"Result limit of {SEARCH_MAX_RESULTS} reached. Narrow your search.",
                    }, indent=2)

            audit("search_files", relative, "success",
                  pattern=pattern, result_count=len(results), capped=False)
            return json.dumps({"results": results}, indent=2)

        except ValueError as exc:
            audit("search_files", relative, "denied", reason=str(exc), pattern=pattern)
            return json.dumps({"error": str(exc)})
        except Exception as exc:
            if is_connection_error(exc):
                raise
            audit("search_files", relative, "error", pattern=pattern)
            return sanitised_error(exc)
