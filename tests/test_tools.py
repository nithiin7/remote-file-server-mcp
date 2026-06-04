"""Mock-SMB integration tests for the four MCP tool handlers."""
import json
import pytest
from unittest.mock import MagicMock, patch

from tests.conftest import MockMCP, make_dir_entry, make_stat
from tools.list_files import register as _reg_list
from tools.read_files import register as _reg_read
from tools.get_file_info import register as _reg_info
from tools.search_file import register as _reg_search

# UNC root used by smb_path("") with our test credentials
_UNC_ROOT = "\\\\testhost\\testshare"


# ---------------------------------------------------------------------------
# Fixtures — one per tool, module-scoped so registration runs once
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def list_files():
    mcp = MockMCP()
    _reg_list(mcp)
    return mcp._tools["list_files"]


@pytest.fixture(scope="module")
def read_file():
    mcp = MockMCP()
    _reg_read(mcp)
    return mcp._tools["read_file"]


@pytest.fixture(scope="module")
def get_file_info():
    mcp = MockMCP()
    _reg_info(mcp)
    return mcp._tools["get_file_info"]


@pytest.fixture(scope="module")
def search_files():
    mcp = MockMCP()
    _reg_search(mcp)
    return mcp._tools["search_files"]


# ---------------------------------------------------------------------------
# list_files
# ---------------------------------------------------------------------------

class TestListFiles:

    def test_returns_files_and_dirs(self, list_files):
        entries = [
            make_dir_entry("reports", is_dir=True),
            make_dir_entry("readme.txt", size=512),
        ]
        with patch("smbclient.scandir", return_value=iter(entries)):
            result = json.loads(list_files(""))
        names = [e["name"] for e in result["entries"]]
        assert "reports" in names
        assert "readme.txt" in names

    def test_dirs_sorted_before_files(self, list_files):
        entries = [
            make_dir_entry("z_file.txt", size=10),
            make_dir_entry("a_subdir", is_dir=True),
        ]
        with patch("smbclient.scandir", return_value=iter(entries)):
            result = json.loads(list_files(""))
        types = [e["type"] for e in result["entries"]]
        assert types.index("directory") < types.index("file")

    def test_file_size_in_result(self, list_files):
        entries = [make_dir_entry("data.csv", size=1_234)]
        with patch("smbclient.scandir", return_value=iter(entries)):
            result = json.loads(list_files(""))
        assert result["entries"][0]["size"] == 1_234

    def test_directory_size_is_null(self, list_files):
        entries = [make_dir_entry("subdir", is_dir=True)]
        with patch("smbclient.scandir", return_value=iter(entries)):
            result = json.loads(list_files(""))
        assert result["entries"][0]["size"] is None

    def test_denied_filenames_silently_excluded(self, list_files):
        entries = [
            make_dir_entry("report.txt", size=10),
            make_dir_entry("id_rsa"),
            make_dir_entry(".env"),
            make_dir_entry("server.pem"),
        ]
        with patch("smbclient.scandir", return_value=iter(entries)):
            result = json.loads(list_files(""))
        names = [e["name"] for e in result["entries"]]
        assert "report.txt" in names
        assert "id_rsa" not in names
        assert ".env" not in names
        assert "server.pem" not in names

    def test_traversal_path_returns_error(self, list_files):
        result = json.loads(list_files("../../etc"))
        assert "error" in result

    def test_smb_error_returns_generic_error(self, list_files):
        with patch("smbclient.scandir", side_effect=RuntimeError("disk failure")):
            result = json.loads(list_files("docs"))
        assert "error" in result

    def test_truncates_at_200_entries(self, list_files):
        entries = [make_dir_entry(f"f{i}.txt", size=i) for i in range(210)]
        with patch("smbclient.scandir", return_value=iter(entries)):
            result = json.loads(list_files(""))
        assert len(result["entries"]) == 200
        assert result.get("truncated") is True
        assert "note" in result

    def test_no_truncation_flag_under_limit(self, list_files):
        entries = [make_dir_entry(f"f{i}.txt", size=i) for i in range(5)]
        with patch("smbclient.scandir", return_value=iter(entries)):
            result = json.loads(list_files(""))
        assert "truncated" not in result


# ---------------------------------------------------------------------------
# read_file
# ---------------------------------------------------------------------------

class TestReadFile:

    def _mock_open(self, content: str):
        """Return (stat_mock, open_file_mock) for a normal text read."""
        st = make_stat(size=len(content.encode()))
        fh = MagicMock()
        fh.read.return_value = content
        cm = MagicMock()
        cm.__enter__.return_value = fh
        cm.__exit__.return_value = False
        return st, cm

    def test_reads_text_content(self, read_file):
        st, cm = self._mock_open("hello world")
        with patch("smbclient.stat", return_value=st), \
             patch("smbclient.open_file", return_value=cm):
            result = read_file("docs/notes.txt")
        assert result == "hello world"

    def test_empty_path_returns_error(self, read_file):
        result = json.loads(read_file(""))
        assert "error" in result

    def test_traversal_returns_error(self, read_file):
        result = json.loads(read_file("../../etc/passwd"))
        assert "error" in result

    def test_denied_filename_returns_error(self, read_file):
        result = json.loads(read_file("keys/id_rsa"))
        assert "error" in result

    def test_oversized_returns_preview_lines(self, read_file):
        big = 20 * 1024 * 1024
        st = make_stat(size=big)
        fh = MagicMock()
        fh.readline.side_effect = ["line1\n", "line2\n", ""]
        cm = MagicMock()
        cm.__enter__.return_value = fh
        cm.__exit__.return_value = False
        with patch("smbclient.stat", return_value=st), \
             patch("smbclient.open_file", return_value=cm), \
             patch("tools.read_files.MAX_FILE_SIZE_BYTES", 10 * 1024 * 1024), \
             patch("tools.read_files.READ_PREVIEW_LINES", 2):
            result = read_file("docs/big.txt")
        assert "line1" in result
        assert "Truncated" in result

    def test_oversized_hard_errors_when_preview_disabled(self, read_file):
        big = 20 * 1024 * 1024
        st = make_stat(size=big)
        with patch("smbclient.stat", return_value=st), \
             patch("tools.read_files.MAX_FILE_SIZE_BYTES", 10 * 1024 * 1024), \
             patch("tools.read_files.READ_PREVIEW_LINES", 0):
            result = json.loads(read_file("docs/big.txt"))
        assert "error" in result
        assert "large" in result["error"].lower()

    def test_binary_file_returns_notice(self, read_file):
        st = make_stat(size=256)
        # First open (text mode) → UnicodeDecodeError; second (binary) → bytes
        text_fh = MagicMock()
        text_fh.read.side_effect = UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid")
        text_cm = MagicMock()
        text_cm.__enter__.return_value = text_fh
        text_cm.__exit__.return_value = False

        bin_fh = MagicMock()
        bin_fh.read.return_value = b"\xff" * 256
        bin_cm = MagicMock()
        bin_cm.__enter__.return_value = bin_fh
        bin_cm.__exit__.return_value = False

        with patch("smbclient.stat", return_value=st), \
             patch("smbclient.open_file", side_effect=[text_cm, bin_cm]):
            result = read_file("images/photo.jpg")
        assert "Binary" in result or "binary" in result

    def test_smb_error_returns_generic_error(self, read_file):
        with patch("smbclient.stat", side_effect=RuntimeError("network gone")):
            result = json.loads(read_file("docs/file.txt"))
        assert "error" in result


# ---------------------------------------------------------------------------
# get_file_info
# ---------------------------------------------------------------------------

class TestGetFileInfo:

    def test_returns_file_metadata(self, get_file_info):
        st = make_stat(size=4_096)
        with patch("smbclient.stat", return_value=st), \
             patch("smbclient.path.isdir", return_value=False):
            result = json.loads(get_file_info("docs/report.txt"))
        assert result["name"] == "report.txt"
        assert result["type"] == "file"
        assert result["size_bytes"] == 4_096
        assert "modified_time" in result
        assert "created_time" in result

    def test_returns_directory_metadata(self, get_file_info):
        st = make_stat(size=0)
        with patch("smbclient.stat", return_value=st), \
             patch("smbclient.path.isdir", return_value=True):
            result = json.loads(get_file_info("docs"))
        assert result["type"] == "directory"
        assert result["name"] == "docs"

    def test_timestamps_are_iso8601(self, get_file_info):
        st = make_stat()
        with patch("smbclient.stat", return_value=st), \
             patch("smbclient.path.isdir", return_value=False):
            result = json.loads(get_file_info("docs/file.txt"))
        # ISO 8601 strings contain a 'T' separator
        assert "T" in result["modified_time"]
        assert "T" in result["created_time"]

    def test_empty_path_returns_error(self, get_file_info):
        result = json.loads(get_file_info(""))
        assert "error" in result

    def test_traversal_returns_error(self, get_file_info):
        result = json.loads(get_file_info("../../etc/shadow"))
        assert "error" in result

    def test_denied_filename_returns_error(self, get_file_info):
        result = json.loads(get_file_info("keys/server.pem"))
        assert "error" in result

    def test_smb_error_returns_generic_error(self, get_file_info):
        with patch("smbclient.stat", side_effect=RuntimeError("timeout")):
            result = json.loads(get_file_info("docs/file.txt"))
        assert "error" in result


# ---------------------------------------------------------------------------
# search_files
# ---------------------------------------------------------------------------

class TestSearchFiles:

    def _walk(self, *entries):
        """Build a walk() return value. Each entry is (dirpath, dirnames, filenames)."""
        return iter(list(entries))

    def test_finds_matching_files(self, search_files):
        walk = self._walk(
            (_UNC_ROOT, [], ["report.txt", "data.csv", "notes.txt"]),
        )
        st = make_stat(size=100)
        with patch("smbclient.walk", return_value=walk), \
             patch("smbclient.stat", return_value=st):
            result = json.loads(search_files("*.txt"))
        names = [r["name"] for r in result]
        assert "report.txt" in names
        assert "notes.txt" in names
        assert "data.csv" not in names

    def test_bare_extension_autocorrected(self, search_files):
        # ".txt" should be treated as "*.txt"
        walk = self._walk((_UNC_ROOT, [], ["readme.txt"]))
        st = make_stat(size=50)
        with patch("smbclient.walk", return_value=walk), \
             patch("smbclient.stat", return_value=st):
            result = json.loads(search_files(".txt"))
        assert any(r["name"] == "readme.txt" for r in result)

    def test_denied_files_excluded_silently(self, search_files):
        walk = self._walk(
            (_UNC_ROOT, [], ["report.txt", "id_rsa", "server.pem"]),
        )
        st = make_stat(size=10)
        with patch("smbclient.walk", return_value=walk), \
             patch("smbclient.stat", return_value=st):
            result = json.loads(search_files("*"))
        names = [r["name"] for r in result]
        assert "report.txt" in names
        assert "id_rsa" not in names
        assert "server.pem" not in names

    def test_no_matches_returns_empty_list(self, search_files):
        walk = self._walk((_UNC_ROOT, [], ["readme.md", "data.csv"]))
        st = make_stat(size=0)
        with patch("smbclient.walk", return_value=walk), \
             patch("smbclient.stat", return_value=st):
            result = json.loads(search_files("*.exe"))
        assert result == []

    def test_traversal_path_returns_error(self, search_files):
        result = json.loads(search_files("*.txt", path="../../etc"))
        assert "error" in result

    def test_result_includes_path_name_size(self, search_files):
        walk = self._walk((_UNC_ROOT, [], ["notes.txt"]))
        st = make_stat(size=999)
        with patch("smbclient.walk", return_value=walk), \
             patch("smbclient.stat", return_value=st):
            result = json.loads(search_files("*.txt"))
        assert len(result) == 1
        assert result[0]["name"] == "notes.txt"
        assert result[0]["size_bytes"] == 999
        assert "path" in result[0]

    def test_caps_at_200_results(self, search_files):
        filenames = [f"f{i}.txt" for i in range(210)]
        walk = self._walk((_UNC_ROOT, [], filenames))
        st = make_stat(size=1)
        with patch("smbclient.walk", return_value=walk), \
             patch("smbclient.stat", return_value=st):
            result = json.loads(search_files("*.txt"))
        # Capped response is a dict with "results" key
        entries = result.get("results", result)
        assert len(entries) == 200

    def test_max_depth_clamped_to_10(self, search_files):
        # max_depth > 10 should be treated as 10 (no crash)
        walk = self._walk((_UNC_ROOT, [], ["file.txt"]))
        st = make_stat(size=1)
        with patch("smbclient.walk", return_value=walk), \
             patch("smbclient.stat", return_value=st):
            result = json.loads(search_files("*.txt", max_depth=999))
        assert isinstance(result, list)
