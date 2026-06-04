import pytest

from utils.validators import check_filename_denylist, safe_relative_path


# ---------------------------------------------------------------------------
# safe_relative_path
# ---------------------------------------------------------------------------

class TestSafeRelativePath:

    # ---- normal / benign paths ----------------------------------------

    def test_empty_string_is_root(self):
        assert safe_relative_path("") == ""

    def test_simple_dir(self):
        assert safe_relative_path("docs") == "docs"

    def test_nested_path(self):
        assert safe_relative_path("a/b/c.txt") == "a/b/c.txt"

    def test_backslashes_normalised(self):
        assert safe_relative_path("a\\b\\c.txt") == "a/b/c.txt"

    def test_leading_slash_stripped(self):
        assert safe_relative_path("/docs") == "docs"

    def test_multiple_leading_slashes_stripped(self):
        assert safe_relative_path("//docs/file") == "docs/file"

    def test_dot_segment_removed(self):
        assert safe_relative_path("./docs") == "docs"

    def test_internal_dot_collapsed(self):
        assert safe_relative_path("a/./b") == "a/b"

    def test_benign_dotdot_within_root(self):
        # a/../b resolves to "b" — still inside the root
        assert safe_relative_path("a/../b") == "b"

    def test_mixed_separators(self):
        assert safe_relative_path("a\\b/c") == "a/b/c"

    # ---- traversal attacks --------------------------------------------

    def test_classic_traversal_rejected(self):
        with pytest.raises(ValueError, match="Access denied"):
            safe_relative_path("../../etc/passwd")

    def test_single_dotdot_rejected(self):
        with pytest.raises(ValueError, match="Access denied"):
            safe_relative_path("..")

    def test_leading_slash_then_traversal_rejected(self):
        with pytest.raises(ValueError, match="Access denied"):
            safe_relative_path("/../../etc/passwd")

    def test_subdir_then_escape_rejected(self):
        with pytest.raises(ValueError, match="Access denied"):
            safe_relative_path("docs/../../etc/passwd")

    def test_backslash_traversal_rejected(self):
        with pytest.raises(ValueError, match="Access denied"):
            safe_relative_path("..\\..\\etc\\passwd")

    def test_mixed_slash_escape_rejected(self):
        with pytest.raises(ValueError, match="Access denied"):
            safe_relative_path("a\\../..\\etc")

    def test_backslash_single_dotdot_rejected(self):
        with pytest.raises(ValueError, match="Access denied"):
            safe_relative_path("..\\secret")

    # ---- null bytes ---------------------------------------------------

    def test_null_byte_rejected(self):
        with pytest.raises(ValueError, match="Access denied"):
            safe_relative_path("file\x00.txt")

    def test_null_byte_at_start_rejected(self):
        with pytest.raises(ValueError, match="Access denied"):
            safe_relative_path("\x00etc/passwd")

    def test_null_byte_combined_with_traversal_rejected(self):
        with pytest.raises(ValueError):
            safe_relative_path("../../etc/passwd\x00extra")

    # ---- unicode path separators (must NOT be treated as separators) --

    def test_unicode_division_slash_is_literal(self):
        # U+2215 DIVISION SLASH is not a path separator in posixpath
        result = safe_relative_path("docs∕file.txt")
        assert "∕" in result
        assert not result.startswith("..")

    def test_unicode_fullwidth_slash_is_literal(self):
        # U+FF0F FULLWIDTH SOLIDUS is not a path separator
        result = safe_relative_path("docs／file.txt")
        assert "／" in result
        assert not result.startswith("..")

    def test_unicode_slashes_cannot_construct_traversal(self):
        # Attempting "../../etc" with unicode slashes should NOT escape root
        result = safe_relative_path("∕∕etc∕passwd")
        assert not result.startswith("..")

    # ---- ALLOWED_PATHS allowlist enforcement -------------------------

    def test_allowlist_permits_exact_dir(self, monkeypatch):
        monkeypatch.setattr("utils.validators.ALLOWED_PATHS", ["reports"])
        assert safe_relative_path("reports") == "reports"

    def test_allowlist_permits_subpath(self, monkeypatch):
        monkeypatch.setattr("utils.validators.ALLOWED_PATHS", ["reports"])
        assert safe_relative_path("reports/q1.csv") == "reports/q1.csv"

    def test_allowlist_blocks_outside_dir(self, monkeypatch):
        monkeypatch.setattr("utils.validators.ALLOWED_PATHS", ["reports"])
        with pytest.raises(ValueError, match="Access denied"):
            safe_relative_path("secrets/token.txt")

    def test_allowlist_blocks_root_when_set(self, monkeypatch):
        monkeypatch.setattr("utils.validators.ALLOWED_PATHS", ["reports"])
        with pytest.raises(ValueError, match="Access denied"):
            safe_relative_path("")

    def test_empty_allowlist_means_no_restriction(self, monkeypatch):
        monkeypatch.setattr("utils.validators.ALLOWED_PATHS", [])
        assert safe_relative_path("any/path") == "any/path"

    def test_allowlist_prefix_not_confused_with_dir(self, monkeypatch):
        # "reportsfoo" must NOT match the allowlist entry "reports"
        monkeypatch.setattr("utils.validators.ALLOWED_PATHS", ["reports"])
        with pytest.raises(ValueError, match="Access denied"):
            safe_relative_path("reportsfoo/file.txt")


# ---------------------------------------------------------------------------
# check_filename_denylist
# ---------------------------------------------------------------------------

class TestCheckFilenameDenylist:

    # ---- blocked patterns --------------------------------------------

    def test_dotenv_exact(self):
        with pytest.raises(ValueError, match="Access denied"):
            check_filename_denylist(".env")

    def test_dotenv_prefixed(self):
        with pytest.raises(ValueError, match="Access denied"):
            check_filename_denylist("production.env")

    def test_key_extension(self):
        with pytest.raises(ValueError, match="Access denied"):
            check_filename_denylist("private.key")

    def test_pem_extension(self):
        with pytest.raises(ValueError, match="Access denied"):
            check_filename_denylist("cert.pem")

    def test_p12_extension(self):
        with pytest.raises(ValueError, match="Access denied"):
            check_filename_denylist("keystore.p12")

    def test_pfx_extension(self):
        with pytest.raises(ValueError, match="Access denied"):
            check_filename_denylist("cert.pfx")

    def test_crt_extension(self):
        with pytest.raises(ValueError, match="Access denied"):
            check_filename_denylist("server.crt")

    def test_cer_extension(self):
        with pytest.raises(ValueError, match="Access denied"):
            check_filename_denylist("server.cer")

    def test_der_extension(self):
        with pytest.raises(ValueError, match="Access denied"):
            check_filename_denylist("server.der")

    def test_id_rsa(self):
        with pytest.raises(ValueError, match="Access denied"):
            check_filename_denylist("id_rsa")

    def test_id_dsa(self):
        with pytest.raises(ValueError, match="Access denied"):
            check_filename_denylist("id_dsa")

    def test_id_ecdsa(self):
        with pytest.raises(ValueError, match="Access denied"):
            check_filename_denylist("id_ecdsa")

    def test_id_ed25519(self):
        with pytest.raises(ValueError, match="Access denied"):
            check_filename_denylist("id_ed25519")

    def test_id_rsa_pub(self):
        with pytest.raises(ValueError, match="Access denied"):
            check_filename_denylist("id_rsa.pub")

    def test_secret_extension(self):
        with pytest.raises(ValueError, match="Access denied"):
            check_filename_denylist("app.secret")

    def test_token_extension(self):
        with pytest.raises(ValueError, match="Access denied"):
            check_filename_denylist("auth.token")

    def test_credentials_exact(self):
        with pytest.raises(ValueError, match="Access denied"):
            check_filename_denylist("credentials")

    def test_credentials_with_extension(self):
        with pytest.raises(ValueError, match="Access denied"):
            check_filename_denylist("credentials.json")

    def test_netrc(self):
        with pytest.raises(ValueError, match="Access denied"):
            check_filename_denylist(".netrc")

    def test_htpasswd(self):
        with pytest.raises(ValueError, match="Access denied"):
            check_filename_denylist(".htpasswd")

    def test_kdbx(self):
        with pytest.raises(ValueError, match="Access denied"):
            check_filename_denylist("passwords.kdbx")

    def test_keystore(self):
        with pytest.raises(ValueError, match="Access denied"):
            check_filename_denylist("app.keystore")

    def test_jks(self):
        with pytest.raises(ValueError, match="Access denied"):
            check_filename_denylist("app.jks")

    def test_bak(self):
        with pytest.raises(ValueError, match="Access denied"):
            check_filename_denylist("id_rsa.bak")

    # ---- case insensitivity ------------------------------------------

    def test_env_uppercase(self):
        with pytest.raises(ValueError):
            check_filename_denylist(".ENV")

    def test_pem_uppercase(self):
        with pytest.raises(ValueError):
            check_filename_denylist("CERT.PEM")

    def test_key_mixed_case(self):
        with pytest.raises(ValueError):
            check_filename_denylist("Private.Key")

    # ---- allowed filenames ------------------------------------------

    def test_plain_txt_allowed(self):
        check_filename_denylist("report.txt")

    def test_docx_allowed(self):
        check_filename_denylist("document.docx")

    def test_csv_allowed(self):
        check_filename_denylist("data.csv")

    def test_py_allowed(self):
        check_filename_denylist("script.py")

    def test_environment_txt_allowed(self):
        # "environment.txt" does NOT match "*.env" because extension is .txt
        check_filename_denylist("environment.txt")

    def test_pdf_allowed(self):
        check_filename_denylist("annual_report.pdf")

    def test_xlsx_allowed(self):
        check_filename_denylist("budget.xlsx")
