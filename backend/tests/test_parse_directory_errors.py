"""Chemins d'erreur de parse_directory : racine absente, erreurs de lecture,
collecte dans unparsed_files."""

from pathlib import Path

import pytest

from backend.src.parser import parse_directory


class TestMissingRoot:
    def test_raises_file_not_found_for_missing_dir(self):
        with pytest.raises(FileNotFoundError):
            parse_directory(Path("/chemin/qui/n/existe/pas"))

    def test_raises_file_not_found_for_file_root(self):
        with pytest.raises(FileNotFoundError):
            parse_directory(Path("pyproject.toml"))

    def test_error_message_mentions_root(self):
        with pytest.raises(FileNotFoundError, match="racine introuvable"):
            parse_directory(Path("/chemin/qui/n/existe/pas"))


class TestReadErrors:
    def test_invalid_utf8_collected(self, tmp_path: Path):
        (tmp_path / "bad.tf").write_bytes(
            b'resource "aws_x" "a" {\n  bucket = "\xff\xfe"\n}\n'
        )
        (tmp_path / "good.tf").write_text(
            'resource "aws_s3_bucket" "ok" {\n  bucket = "ok"\n}\n',
            encoding="utf-8",
        )
        result = parse_directory(tmp_path)
        assert [r.address for r in result.resources] == ["aws_s3_bucket.ok"]
        assert len(result.unparsed_files) == 1
        assert result.unparsed_files[0]["file"] == "bad.tf"
        assert "codec" in result.unparsed_files[0]["error"]

    def test_invalid_hcl_collected(self, tmp_path: Path):
        (tmp_path / "bad.tf").write_text(
            'resource "aws_x" "a" {\n  bucket = \n}\n', encoding="utf-8"
        )
        result = parse_directory(tmp_path)
        assert len(result.unparsed_files) == 1
        assert result.unparsed_files[0]["file"] == "bad.tf"

    def test_tf_json_not_discovered_in_directory_mode(self, tmp_path: Path):
        # OBSERVATION : discover_tf_files glob *.tf — un fichier .tf.json ne
        # matche pas et n'est jamais lu en mode répertoire. Le rejet explicite
        # ("non supporté") ne s'applique qu'au paste mode (parse_files).
        (tmp_path / "main.tf.json").write_text('{"resource": {}}', encoding="utf-8")
        result = parse_directory(tmp_path)
        assert result.unparsed_files == []
        assert result.resources == []

    def test_mixed_errors_all_collected(self, tmp_path: Path):
        (tmp_path / "bad_utf8.tf").write_bytes(b"\xff\xfe\x00")
        (tmp_path / "bad_hcl.tf").write_text(
            'resource "aws_x" "a" {\n  bucket = \n}\n', encoding="utf-8"
        )
        result = parse_directory(tmp_path)
        assert len(result.unparsed_files) == 2
