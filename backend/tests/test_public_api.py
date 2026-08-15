"""Contrat des 2 API publiques du package parser (façade __init__.py).

- parse_files(files: dict[str, str]) -> ParsedTerraform : pur, sans I/O,
  déterministe, ne lève jamais.
- parse_directory(root: Path) -> ParsedTerraform : scan racine non récursif
  + expansion des modules locaux ; lève FileNotFoundError si la racine
  n'existe pas.
"""

from pathlib import Path

import pytest

from backend.src.parser import (
    ModuleCall,
    ParsedTerraform,
    Resource,
    TerraformParseError,
    parse_directory,
    parse_files,
)


class TestPublicSurface:
    def test_all_symbols_importable(self):
        assert callable(parse_files)
        assert callable(parse_directory)
        assert issubclass(TerraformParseError, Exception)
        assert Resource.__name__ == "Resource"
        assert ModuleCall.__name__ == "ModuleCall"
        assert ParsedTerraform.__name__ == "ParsedTerraform"

    def test_parse_files_signature(self):
        result = parse_files({"main.tf": 'resource "aws_x" "a" {}\n'})
        assert isinstance(result, ParsedTerraform)
        assert result.resources[0].address == "aws_x.a"

    def test_parse_directory_signature(self, tmp_path: Path):
        (tmp_path / "main.tf").write_text('resource "aws_x" "a" {}\n', encoding="utf-8")
        result = parse_directory(tmp_path)
        assert isinstance(result, ParsedTerraform)
        assert result.resources[0].address == "aws_x.a"


class TestParseFilesContract:
    def test_never_raises_on_any_content(self, hcl_samples):
        # HCL invalide, .tf.json, vide, commentaires : tout est collecté.
        result = parse_files(
            {
                "invalid.tf": hcl_samples["invalid.tf"],
                "main.tf.json": hcl_samples["main.tf.json"],
                "empty.tf": hcl_samples["empty.tf"],
                "comments_only.tf": hcl_samples["comments_only.tf"],
            }
        )
        assert len(result.unparsed_files) == 2

    def test_deterministic_across_calls(self, hcl_samples):
        files = {"basic.tf": hcl_samples["basic.tf"]}
        assert parse_files(files) == parse_files(files)

    def test_pure_no_filesystem_access(self, hcl_samples, tmp_path: Path):
        # Le contenu est parsé sans jamais toucher le disque : un nom de
        # fichier fantôme fonctionne, et aucun fichier n'est créé.
        before = set(tmp_path.iterdir())
        parse_files({"fantome.tf": hcl_samples["basic.tf"]})
        assert set(tmp_path.iterdir()) == before

    def test_paste_mode_modules_recorded_unresolved(self, hcl_samples):
        result = parse_files({"modules.tf": hcl_samples["modules.tf"]})
        assert len(result.module_calls) == 2
        assert result.unparsed_files == []


class TestParseDirectoryContract:
    def test_raises_file_not_found_for_missing_root(self):
        with pytest.raises(FileNotFoundError):
            parse_directory(Path("/chemin/qui/n/existe/pas"))

    def test_scan_root_only_not_recursive(self, tmp_path: Path):
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "nested.tf").write_text(
            'resource "aws_x" "nested" {}\n', encoding="utf-8"
        )
        (tmp_path / "main.tf").write_text(
            'resource "aws_x" "root" {}\n', encoding="utf-8"
        )
        result = parse_directory(tmp_path)
        assert [r.address for r in result.resources] == ["aws_x.root"]

    def test_expands_local_modules(self, expansion_root: Path):
        result = parse_directory(expansion_root)
        assert any(
            r.address.startswith("module.a.module.b.module.c.")
            for r in result.resources
        )

    def test_never_raises_on_invalid_files(self, tmp_path: Path):
        (tmp_path / "bad.tf").write_text(
            'resource "aws_x" "a" {\n  bucket = \n}\n', encoding="utf-8"
        )
        result = parse_directory(tmp_path)
        assert len(result.unparsed_files) == 1
