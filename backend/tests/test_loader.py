"""Contrat de loader.py : I/O disque (scan non récursif, lecture UTF-8/BOM)."""

from pathlib import Path

import pytest

from backend.src.parser.loader import discover_tf_files, read_file_content


class TestDiscoverTfFiles:
    def test_returns_only_tf_files_sorted(self, tmp_path: Path):
        (tmp_path / "b.tf").write_text("", encoding="utf-8")
        (tmp_path / "a.tf").write_text("", encoding="utf-8")
        (tmp_path / "c.tf").write_text("", encoding="utf-8")
        files = discover_tf_files(tmp_path)
        assert files == [tmp_path / "a.tf", tmp_path / "b.tf", tmp_path / "c.tf"]

    def test_ignores_tfvars(self, tmp_path: Path):
        (tmp_path / "terraform.tfvars").write_text("x = 1", encoding="utf-8")
        (tmp_path / "main.tf").write_text("", encoding="utf-8")
        assert discover_tf_files(tmp_path) == [tmp_path / "main.tf"]

    def test_ignores_non_tf_extensions(self, tmp_path: Path):
        (tmp_path / "notes.txt").write_text("", encoding="utf-8")
        (tmp_path / "main.tf.bak").write_text("", encoding="utf-8")
        (tmp_path / "main.tf").write_text("", encoding="utf-8")
        assert discover_tf_files(tmp_path) == [tmp_path / "main.tf"]

    def test_ignores_directories_matching_glob(self, tmp_path: Path):
        # Un dossier nommé "x.tf" matche le glob mais n'est pas un fichier.
        (tmp_path / "x.tf").mkdir()
        (tmp_path / "main.tf").write_text("", encoding="utf-8")
        assert discover_tf_files(tmp_path) == [tmp_path / "main.tf"]

    def test_not_recursive(self, tmp_path: Path):
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "nested.tf").write_text("", encoding="utf-8")
        (tmp_path / "root.tf").write_text("", encoding="utf-8")
        assert discover_tf_files(tmp_path) == [tmp_path / "root.tf"]

    def test_empty_directory(self, tmp_path: Path):
        assert discover_tf_files(tmp_path) == []


class TestReadFileContent:
    def test_reads_utf8(self, tmp_path: Path):
        path = tmp_path / "main.tf"
        path.write_text('resource "aws_x" "a" {}\n', encoding="utf-8")
        assert read_file_content(path) == 'resource "aws_x" "a" {}\n'

    def test_tolerates_bom(self, tmp_path: Path):
        path = tmp_path / "bom.tf"
        path.write_bytes(b'\xef\xbb\xbfresource "aws_x" "a" {}\n')
        assert read_file_content(path) == 'resource "aws_x" "a" {}\n'

    def test_raises_on_invalid_utf8(self, tmp_path: Path):
        path = tmp_path / "bad.tf"
        path.write_bytes(b'resource "aws_x" "a" {\n  bucket = "\xff\xfe"\n}\n')
        with pytest.raises(UnicodeDecodeError):
            read_file_content(path)
