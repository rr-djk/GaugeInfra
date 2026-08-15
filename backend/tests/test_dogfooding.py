"""Dogfooding : le parser validé sur le vrai infra/ du projet.

Golden sets vérifiés (TODOS.md Phase 1) :
- parse_directory(infra/environments/dev) : 18 resources, 5 data_sources,
  4 module_calls, 0 unparsed_files ; adresses préfixées par module ;
  source_file relatif à la racine (../../modules/frontend/main.tf).
- parse_directory(infra/bootstrap) : 4 resources, 0 unparsed_files.

Marqué @pytest.mark.dogfood : exclu de `make test-unit`, seul dans
`make test-dogfood`.
"""

from pathlib import Path

import pytest

from backend.src.parser import parse_directory

pytestmark = pytest.mark.dogfood

DEV_RESOURCES = {
    "module.api.aws_apigatewayv2_api.this",
    "module.api.aws_apigatewayv2_stage.this",
    "module.api.aws_cloudwatch_log_group.api_gw",
    "module.api.aws_iam_role.api_gw_logging",
    "module.api.aws_iam_role_policy_attachment.api_gw_logging",
    "module.bedrock.aws_iam_policy.this",
    "module.bedrock.aws_iam_role_policy_attachment.this",
    "module.frontend.aws_cloudfront_cache_policy.this",
    "module.frontend.aws_cloudfront_distribution.this",
    "module.frontend.aws_cloudfront_origin_access_control.this",
    "module.frontend.aws_cloudfront_response_headers_policy.security_headers",
    "module.frontend.aws_s3_bucket.this",
    "module.frontend.aws_s3_bucket_policy.this",
    "module.frontend.aws_s3_bucket_public_access_block.this",
    "module.frontend.aws_s3_bucket_versioning.this",
    "module.lambda.aws_iam_role.this",
    "module.lambda.aws_iam_role_policy_attachment.basic_execution",
    "module.lambda.aws_lambda_function.this",
}

DEV_DATA_SOURCES = {
    "module.api.data.aws_iam_policy.api_gw_push_logs",
    "module.bedrock.data.aws_iam_policy_document.bedrock",
    "module.frontend.data.aws_iam_policy_document.cloudfront_read",
    "module.lambda.data.archive_file.this",
    "module.lambda.data.aws_iam_policy_document.assume_role",
}

DEV_MODULE_CALLS = {"module.api", "module.bedrock", "module.frontend", "module.lambda"}

BOOT_RESOURCES = {
    "aws_s3_bucket.state",
    "aws_s3_bucket_public_access_block.state",
    "aws_s3_bucket_server_side_encryption_configuration.state",
    "aws_s3_bucket_versioning.state",
}


class TestDevEnvironment:
    def test_golden_counts(self, repo_root: Path):
        result = parse_directory(repo_root / "infra" / "environments" / "dev")
        assert len(result.resources) == 18
        assert len(result.data_sources) == 5
        assert len(result.module_calls) == 4
        assert result.unparsed_files == []

    def test_golden_resource_addresses(self, repo_root: Path):
        result = parse_directory(repo_root / "infra" / "environments" / "dev")
        assert {r.address for r in result.resources} == DEV_RESOURCES

    def test_golden_data_source_addresses(self, repo_root: Path):
        result = parse_directory(repo_root / "infra" / "environments" / "dev")
        assert {d.address for d in result.data_sources} == DEV_DATA_SOURCES

    def test_golden_module_calls(self, repo_root: Path):
        result = parse_directory(repo_root / "infra" / "environments" / "dev")
        assert {m.address for m in result.module_calls} == DEV_MODULE_CALLS

    def test_addresses_namespaced_by_module(self, repo_root: Path):
        result = parse_directory(repo_root / "infra" / "environments" / "dev")
        assert "module.frontend.aws_s3_bucket.this" in {
            r.address for r in result.resources
        }
        assert "module.frontend.data.aws_iam_policy_document.cloudfront_read" in {
            d.address for d in result.data_sources
        }

    def test_source_file_relative_to_scan_root(self, repo_root: Path):
        result = parse_directory(repo_root / "infra" / "environments" / "dev")
        by_address = {r.address: r.source_file for r in result.resources}
        assert by_address["module.frontend.aws_s3_bucket.this"] == (
            "../../modules/frontend/main.tf"
        )
        assert by_address["module.lambda.aws_lambda_function.this"] == (
            "../../modules/lambda/main.tf"
        )

    def test_variables_outputs_locals_root_only(self, repo_root: Path):
        result = parse_directory(repo_root / "infra" / "environments" / "dev")
        assert set(result.variables) == {
            "region",
            "project",
            "environment",
            "frontend_bucket_name",
            "frontend_force_destroy",
            "lambda_memory_size",
            "lambda_timeout",
        }
        assert set(result.outputs) == {
            "cloudfront_domain_name",
            "frontend_bucket",
            "api_endpoint",
            "lambda_function_name",
            "lambda_role_arn",
            "bedrock_policy_arn",
        }
        assert set(result.locals) == {"tags"}

    def test_other_blocks_counts_terraform_blocks(self, repo_root: Path):
        result = parse_directory(repo_root / "infra" / "environments" / "dev")
        # 5 blocs terraform avec une clé hors backend/required_providers
        # (providers.tf + 4 versions.tf de modules).
        assert result.other_blocks == {"terraform": 5}

    def test_providers_shape(self, repo_root: Path):
        result = parse_directory(repo_root / "infra" / "environments" / "dev")
        # ProviderExtractor ne nettoie pas : name quoté, __is_block__ conservé.
        assert {
            "region": "${var.region}",
            "__is_block__": True,
            "name": '"aws"',
        } in result.providers
        # required_providers extrait depuis providers.tf (racine). expand_modules
        # ne fusionne pas providers des sous-modules : seules les entrées racine
        # apparaissent ici.
        assert {
            "required_providers": {
                "aws": {"source": "hashicorp/aws", "version": "6.58.0"}
            }
        } in result.providers
        assert len(result.providers) == 2

    def test_backend_extracted(self, repo_root: Path):
        result = parse_directory(repo_root / "infra" / "environments" / "dev")
        # backend.tf de la racine (pas de bucket : externalisé dans
        # backend.tfvars, gitignoré).
        assert result.backend == {
            "key": "environments/dev/terraform.tfstate",
            "region": "us-east-1",
            "encrypt": True,
            "use_lockfile": True,
            "type": "s3",
        }


class TestBootstrap:
    def test_golden_counts(self, repo_root: Path):
        result = parse_directory(repo_root / "infra" / "bootstrap")
        assert len(result.resources) == 4
        assert result.unparsed_files == []

    def test_golden_resource_addresses(self, repo_root: Path):
        result = parse_directory(repo_root / "infra" / "bootstrap")
        assert {r.address for r in result.resources} == BOOT_RESOURCES

    def test_no_module_calls(self, repo_root: Path):
        result = parse_directory(repo_root / "infra" / "bootstrap")
        assert result.module_calls == []

    def test_source_file_relative(self, repo_root: Path):
        result = parse_directory(repo_root / "infra" / "bootstrap")
        assert {r.source_file for r in result.resources} == {"main.tf"}
