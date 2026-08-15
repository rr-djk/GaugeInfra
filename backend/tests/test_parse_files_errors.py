"""Chemins d'erreur de parse_files : deux except distincts, collecte dans
unparsed_files, jamais levé."""

import backend.src.parser.pipeline as pipeline
from backend.src.parser import parse_files


class TestTerraformParseErrorPath:
    def test_tf_json_rejected_with_french_message(self, hcl_samples):
        result = parse_files({"main.tf.json": hcl_samples["main.tf.json"]})
        assert len(result.unparsed_files) == 1
        assert result.unparsed_files[0]["file"] == "main.tf.json"
        assert "non supporté" in result.unparsed_files[0]["error"]

    def test_invalid_hcl_collected(self, hcl_samples):
        result = parse_files({"invalid.tf": hcl_samples["invalid.tf"]})
        assert len(result.unparsed_files) == 1
        assert result.unparsed_files[0]["file"] == "invalid.tf"
        assert "invalid.tf" in result.unparsed_files[0]["error"]

    def test_error_message_contains_filename(self, hcl_samples):
        result = parse_files({"invalid.tf": hcl_samples["invalid.tf"]})
        assert "invalid.tf" in result.unparsed_files[0]["error"]

    def test_valid_files_still_parsed_alongside_invalid(self, hcl_samples):
        result = parse_files(
            {
                "invalid.tf": hcl_samples["invalid.tf"],
                "basic.tf": hcl_samples["basic.tf"],
            }
        )
        assert len(result.resources) == 8
        assert len(result.unparsed_files) == 1


class TestGenericExceptionPath:
    def test_internal_error_collected(self, hcl_samples, monkeypatch):
        def boom(body, module_path=(), source_file=""):
            raise RuntimeError("shape inattendue")

        monkeypatch.setattr(pipeline, "extract_all", boom)
        result = parse_files({"x.tf": hcl_samples["basic.tf"]})
        assert len(result.unparsed_files) == 1
        assert result.unparsed_files[0]["error"] == (
            "erreur d'extraction interne : shape inattendue"
        )

    def test_internal_error_does_not_abort_other_files(self, hcl_samples, monkeypatch):
        def boom(body, module_path=(), source_file=""):
            raise RuntimeError("boom")

        monkeypatch.setattr(pipeline, "extract_all", boom)
        result = parse_files(
            {
                "a.tf": hcl_samples["basic.tf"],
                "b.tf": hcl_samples["basic.tf"],
            }
        )
        assert len(result.unparsed_files) == 2
        assert result.resources == []


class TestErrorCollectionShape:
    def test_unparsed_files_entries_are_dicts(self, hcl_samples):
        result = parse_files(
            {
                "invalid.tf": hcl_samples["invalid.tf"],
                "main.tf.json": hcl_samples["main.tf.json"],
            }
        )
        for entry in result.unparsed_files:
            assert set(entry) == {"file", "error"}
            assert isinstance(entry["file"], str)
            assert isinstance(entry["error"], str)

    def test_empty_and_comments_only_files_are_not_errors(self, hcl_samples):
        result = parse_files(
            {
                "empty.tf": hcl_samples["empty.tf"],
                "comments_only.tf": hcl_samples["comments_only.tf"],
            }
        )
        assert result.unparsed_files == []

    def test_comments_only_file_produces_no_other_blocks(self, hcl_samples):
        # La clé racine __comments__ (marqueur interne hcl2) est filtrée :
        # un fichier commentaires-only ne produit aucun bloc inconnu.
        result = parse_files({"comments_only.tf": hcl_samples["comments_only.tf"]})
        assert result.other_blocks == {}
