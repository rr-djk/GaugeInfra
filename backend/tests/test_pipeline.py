"""Contrat de pipeline.py : parse_files (pur, paste mode, fusion) et
parse_directory (I/O + expansion). Les chemins d'erreur sont couverts
dans test_parse_files_errors.py et test_parse_directory_errors.py."""

from pathlib import Path

from backend.src.parser import parse_directory, parse_files
from backend.src.parser.model import ParsedTerraform


class TestParseFiles:
    def test_returns_parsed_terraform(self, hcl_samples):
        result = parse_files({"basic.tf": hcl_samples["basic.tf"]})
        assert isinstance(result, ParsedTerraform)

    def test_empty_dict(self):
        result = parse_files({})
        assert result.resources == []
        assert result.unparsed_files == []

    def test_deterministic(self, hcl_samples):
        files = {
            "basic.tf": hcl_samples["basic.tf"],
            "providers.tf": hcl_samples["providers.tf"],
        }
        assert parse_files(files) == parse_files(files)

    def test_pure_no_io(self, hcl_samples):
        # Le nom de fichier n'a pas besoin d'exister sur le disque.
        result = parse_files({"inexistant.tf": hcl_samples["basic.tf"]})
        assert len(result.resources) == 8

    def test_paste_mode_modules_unresolved(self, hcl_samples):
        result = parse_files({"modules.tf": hcl_samples["modules.tf"]})
        assert [m.address for m in result.module_calls] == [
            "module.vpc",
            "module.local",
        ]
        assert result.module_calls[0].source == "terraform-aws-modules/vpc/aws"
        assert result.module_calls[1].source == "./local_mod"
        assert result.unparsed_files == []

    def test_merge_resources_and_data_sources(self):
        result = parse_files(
            {
                "a.tf": 'resource "aws_x" "a" {}\n',
                "b.tf": 'resource "aws_y" "b" {}\ndata "aws_ami" "u" {}\n',
            }
        )
        assert [r.address for r in result.resources] == ["aws_x.a", "aws_y.b"]
        assert [d.address for d in result.data_sources] == ["data.aws_ami.u"]

    def test_merge_variables_last_wins(self):
        result = parse_files(
            {
                "a.tf": 'variable "x" { default = 1 }\n',
                "b.tf": 'variable "x" { default = 2 }\nvariable "y" { default = 3 }\n',
            }
        )
        assert result.variables == {"x": {"default": 2}, "y": {"default": 3}}

    def test_merge_outputs_and_locals(self):
        result = parse_files(
            {
                "a.tf": 'output "o" { value = 1 }\nlocals { a = 1 }\n',
                "b.tf": "locals { b = 2 }\n",
            }
        )
        assert result.outputs == {"o": {"value": 1}}
        assert result.locals == {"a": 1, "b": 2}

    def test_merge_other_blocks_sums(self):
        result = parse_files(
            {
                "a.tf": "moved {\n  from = aws_x.a\n  to = aws_x.b\n}\n",
                "b.tf": "moved {\n  from = aws_y.a\n  to = aws_y.b\n}\n",
            }
        )
        assert result.other_blocks == {"moved": 2}

    def test_merge_providers_extends(self):
        result = parse_files(
            {
                "a.tf": 'provider "aws" {\n  region = "us-east-1"\n}\n',
                "b.tf": 'provider "aws" {\n  alias = "west"\n}\n',
            }
        )
        assert len(result.providers) == 2

    def test_backend_last_wins(self):
        # Input invalide (2 blocs backend dans le même module = échoue
        # `terraform validate`) : comportement défensif déterministe — le
        # backend du dernier fichier gagne.
        result = parse_files(
            {
                "a.tf": 'terraform {\n  backend "s3" {\n    bucket = "a"\n  }\n}\n',
                "b.tf": 'terraform {\n  backend "s3" {\n    bucket = "b"\n  }\n}\n',
            }
        )
        assert result.backend == {"type": "s3", "bucket": "b"}

    def test_required_providers_extracted_via_pipeline(self):
        result = parse_files(
            {
                "providers.tf": (
                    "terraform {\n  required_providers {\n"
                    '    aws = {\n      source  = "hashicorp/aws"\n'
                    '      version = "6.58.0"\n    }\n  }\n}\n'
                )
            }
        )
        assert result.providers == [
            {
                "required_providers": {
                    "aws": {"source": "hashicorp/aws", "version": "6.58.0"}
                }
            }
        ]

    def test_backend_merge_last_wins_when_extracted(self, monkeypatch):
        # Fusion last-wins isolée : on force _parse_single_file pour couvrir
        # le merge de pipeline.py sans dépendre de la forme hcl2.
        import backend.src.parser.pipeline as pipeline
        from backend.src.parser.model import ParsedTerraform

        def fake_parse(filename, content, module_path=()):
            return ParsedTerraform(backend={"type": "s3", "bucket": filename})

        monkeypatch.setattr(pipeline, "_parse_single_file", fake_parse)
        result = parse_files({"a.tf": "", "b.tf": ""})
        assert result.backend == {"type": "s3", "bucket": "b.tf"}


class TestParseDirectory:
    def test_empty_directory(self, tmp_path: Path):
        result = parse_directory(tmp_path)
        assert result.resources == []
        assert result.unparsed_files == []

    def test_source_file_relative_to_root(self, tmp_path: Path):
        (tmp_path / "main.tf").write_text(
            'resource "aws_s3_bucket" "this" {}\n', encoding="utf-8"
        )
        result = parse_directory(tmp_path)
        assert result.resources[0].source_file == "main.tf"

    def test_ignores_tfvars_in_directory(self, tmp_path: Path):
        (tmp_path / "terraform.tfvars").write_text("x = 1", encoding="utf-8")
        (tmp_path / "main.tf").write_text(
            'resource "aws_s3_bucket" "this" {}\n', encoding="utf-8"
        )
        result = parse_directory(tmp_path)
        assert len(result.resources) == 1
        assert result.unparsed_files == []
