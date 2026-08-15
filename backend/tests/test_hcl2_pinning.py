"""Régression sur les formes brutes de python-hcl2 8.1.2 (pinning).

Encode les formes H1-H14 de docs/phase1/HCL2-PINNING.md : labels quotés,
marqueurs __is_block__/__comments__, valeurs brutes, asymétrie
required_providers, .tf.json rejeté. Si une forme change (upgrade hcl2),
ces tests cassent immédiatement.
"""

import hcl2
import pytest

from backend.src.parser.exceptions import TerraformParseError
from backend.src.parser.pipeline import _parse_single_file


class TestRawHcl2Shapes:
    def test_labels_are_quoted(self):
        raw = hcl2.loads(
            'resource "aws_s3_bucket" "this" {\n  bucket = var.bucket_name\n}\n'
        )
        assert raw == {
            "resource": [
                {
                    '"aws_s3_bucket"': {
                        '"this"': {"bucket": "${var.bucket_name}", "__is_block__": True}
                    }
                }
            ]
        }

    def test_count_int_vs_expression_string(self):
        raw = hcl2.loads('resource "aws_x" "a" {\n  count = 2\n}\n')
        assert raw["resource"][0]['"aws_x"']['"a"']["count"] == 2
        raw = hcl2.loads('resource "aws_x" "a" {\n  count = length(var.list)\n}\n')
        assert raw["resource"][0]['"aws_x"']['"a"']["count"] == "${length(var.list)}"

    def test_for_each_template(self):
        raw = hcl2.loads('resource "aws_x" "a" {\n  for_each = toset(var.items)\n}\n')
        assert raw["resource"][0]['"aws_x"']['"a"']["for_each"] == "${toset(var.items)}"

    def test_list_values_keep_quotes(self):
        raw = hcl2.loads('resource "aws_x" "a" {\n  methods = ["GET", "HEAD"]\n}\n')
        assert raw["resource"][0]['"aws_x"']['"a"']["methods"] == ['"GET"', '"HEAD"']

    def test_bool_and_int_kept(self):
        raw = hcl2.loads(
            'terraform {\n  backend "s3" {\n    use_lockfile = true\n  }\n}\n'
        )
        backend = raw["terraform"][0]["backend"][0]['"s3"']
        assert backend["use_lockfile"] is True

    def test_jsonencode_flattened(self):
        raw = hcl2.loads(
            'resource "aws_iam_role" "r" {\n'
            "  assume_role_policy = jsonencode({\n"
            '    Version = "2012-10-17"\n'
            '    Statement = [{ Effect = "Allow" }]\n'
            "  })\n"
            "}\n"
        )
        value = raw["resource"][0]['"aws_iam_role"']['"r"']["assume_role_policy"]
        assert value == (
            '${jsonencode({Version = "2012-10-17", Statement = [{Effect = "Allow"}]})}'
        )

    def test_heredoc_kept_brut_with_markers(self):
        raw = hcl2.loads(
            'resource "aws_x" "a" {\n'
            "  policy = <<-EOT\n"
            '    {"Version": "2012-10-17"}\n'
            "  EOT\n"
            "}\n"
        )
        assert raw["resource"][0]['"aws_x"']['"a"']["policy"] == (
            '"<<-EOT\n    {"Version": "2012-10-17"}\n  EOT"'
        )

    def test_nested_blocks_are_lists_of_dicts(self):
        raw = hcl2.loads(
            'resource "aws_s3_bucket" "b" {\n'
            "  versioning {\n"
            '    status = "Enabled"\n'
            "  }\n"
            "}\n"
        )
        versioning = raw["resource"][0]['"aws_s3_bucket"']['"b"']["versioning"]
        assert versioning == [{"status": '"Enabled"', "__is_block__": True}]

    def test_dynamic_block_shape(self):
        raw = hcl2.loads(
            'resource "aws_x" "a" {\n'
            '  dynamic "ingress" {\n'
            "    for_each = var.ports\n"
            "    content {\n"
            "      port = ingress.value\n"
            "    }\n"
            "  }\n"
            "}\n"
        )
        dynamic = raw["resource"][0]['"aws_x"']['"a"']["dynamic"]
        assert dynamic == [
            {
                '"ingress"': {
                    "for_each": "${var.ports}",
                    "content": [{"port": "${ingress.value}", "__is_block__": True}],
                    "__is_block__": True,
                }
            }
        ]

    def test_required_providers_key_not_quoted(self):
        raw = hcl2.loads(
            "terraform {\n"
            "  required_providers {\n"
            "    aws = {\n"
            '      source  = "hashicorp/aws"\n'
            '      version = "6.58.0"\n'
            "    }\n"
            "  }\n"
            "}\n"
        )
        rp = raw["terraform"][0]["required_providers"][0]
        assert "aws" in rp  # clé non quotée (asymétrie avec les labels)
        # L'objet aws = {...} est une assignation, pas un bloc : pas de
        # marqueur __is_block__ à l'intérieur (il est sur l'entrée
        # required_providers).
        assert rp["aws"] == {
            "source": '"hashicorp/aws"',
            "version": '"6.58.0"',
        }
        assert rp["__is_block__"] is True

    def test_comments_only_file(self):
        raw = hcl2.loads("# juste un commentaire\n")
        assert "__comments__" in raw

    def test_empty_file(self):
        assert hcl2.loads("") == {}


class TestErrorWrapping:
    def test_invalid_hcl_wrapped_in_terraform_parse_error(self):
        with pytest.raises(TerraformParseError):
            _parse_single_file("bad.tf", 'resource "aws_x" "a" {\n  bucket = \n}\n')

    def test_tf_json_wrapped_with_french_message(self):
        with pytest.raises(TerraformParseError, match="non supporté"):
            _parse_single_file("main.tf.json", '{"resource": {}}')

    def test_tf_json_message_contains_filename(self):
        with pytest.raises(TerraformParseError) as exc_info:
            _parse_single_file("main.tf.json", '{"resource": {}}')
        assert "main.tf.json" in str(exc_info.value)

    def test_invalid_hcl_error_chains_lark_cause(self):
        with pytest.raises(TerraformParseError) as exc_info:
            _parse_single_file("bad.tf", 'resource "aws_x" "a" {\n  bucket = \n}\n')
        assert exc_info.value.__cause__ is not None
