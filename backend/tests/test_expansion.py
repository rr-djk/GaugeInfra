"""Contrat de expansion.py : graphe de modules, namespacing, cycles,
profondeur, modules manquants, sources distantes."""

from pathlib import Path

from conftest import build_depth_tree

from backend.src.parser import parse_directory
from backend.src.parser.expansion import (
    MAX_MODULE_DEPTH,
    _is_local_source,
    expand_modules,
)
from backend.src.parser.pipeline import _parse_directory_io


class TestIsLocalSource:
    def test_local_sources(self):
        assert _is_local_source("./mod_a")
        assert _is_local_source("../mod_b")
        assert _is_local_source("../../shared/mod")

    def test_remote_sources(self):
        assert not _is_local_source("terraform-aws-modules/vpc/aws")
        assert not _is_local_source("git::https://example.com/repo.git")
        assert not _is_local_source("registry.terraform.io/hashicorp/aws")
        assert not _is_local_source("")


class TestMaxModuleDepth:
    def test_constant(self):
        assert MAX_MODULE_DEPTH == 10


class TestExpandModulesDirect:
    def test_base_root_defaults_to_root(self, tmp_path: Path):
        # expand_modules(root) sans base_root : base_root = root, les
        # source_file restent relatifs à la racine du module courant.
        (tmp_path / "main.tf").write_text(
            'resource "aws_s3_bucket" "this" {}\n', encoding="utf-8"
        )
        parsed = _parse_directory_io(tmp_path, module_path=(), base_root=tmp_path)
        expanded = expand_modules(
            parsed, tmp_path, source_stack={str(tmp_path.resolve())}
        )
        assert expanded.resources[0].source_file == "main.tf"


class TestExpandModules:
    def test_namespacing_by_construction(self, expansion_root: Path):
        result = parse_directory(expansion_root)
        addresses = {r.address for r in result.resources}
        assert "aws_s3_bucket.root_bucket" in addresses
        assert "module.a.aws_s3_bucket.a_bucket" in addresses
        assert "module.a.module.b.aws_s3_bucket.b_bucket" in addresses
        assert "module.a.module.b.module.c.aws_s3_bucket.c_bucket" in addresses

    def test_source_file_relative_to_base_root(self, expansion_root: Path):
        result = parse_directory(expansion_root)
        by_address = {r.address: r.source_file for r in result.resources}
        assert by_address["aws_s3_bucket.root_bucket"] == "main.tf"
        assert by_address["module.a.aws_s3_bucket.a_bucket"] == "mod_a/main.tf"
        assert by_address["module.a.module.b.aws_s3_bucket.b_bucket"] == "mod_b/main.tf"
        assert (
            by_address["module.a.module.b.module.c.aws_s3_bucket.c_bucket"]
            == "mod_c/main.tf"
        )

    def test_remote_source_kept_not_an_error(self, expansion_root: Path):
        result = parse_directory(expansion_root)
        remote = [m for m in result.module_calls if m.address == "module.remote"]
        assert len(remote) == 1
        assert remote[0].source == "terraform-aws-modules/vpc/aws"
        assert not any("module.remote" in u["file"] for u in result.unparsed_files)

    def test_missing_module_recorded_never_raised(self, expansion_root: Path):
        result = parse_directory(expansion_root)
        missing = [u for u in result.unparsed_files if u["file"] == "module.missing"]
        assert len(missing) == 1
        assert "module local introuvable" in missing[0]["error"]

    def test_all_module_calls_kept_after_expansion(self, expansion_root: Path):
        result = parse_directory(expansion_root)
        assert [m.address for m in result.module_calls] == [
            "module.a",
            "module.remote",
            "module.missing",
            "module.a.module.b",
            "module.a.module.b.module.c",
        ]

    def test_cycle_detected(self, cycle_root: Path):
        result = parse_directory(cycle_root)
        cycles = [u for u in result.unparsed_files if "cycle" in u["error"]]
        assert len(cycles) == 1
        assert cycles[0]["file"] == "module.a.module.b.module.a"
        assert "cycle de modules détecté" in cycles[0]["error"]

    def test_depth_limit_recorded(self, tmp_path: Path):
        root = build_depth_tree(tmp_path, n_modules=12)
        result = parse_directory(root)
        depth_errors = [
            u for u in result.unparsed_files if "profondeur maximale" in u["error"]
        ]
        assert len(depth_errors) == 1
        assert depth_errors[0]["file"] == (
            "module.m0.module.m1.module.m2.module.m3.module.m4."
            "module.m5.module.m6.module.m7.module.m8.module.m9.module.m10"
        )
        assert (
            f"profondeur maximale ({MAX_MODULE_DEPTH}) dépassée"
            in (depth_errors[0]["error"])
        )

    def test_depth_limit_stops_expansion(self, tmp_path: Path):
        root = build_depth_tree(tmp_path, n_modules=12)
        result = parse_directory(root)
        # La ressource du module 11 n'est jamais atteinte.
        assert result.resources == []
        # Les appels m0..m10 restent visibles (11 appels).
        assert len(result.module_calls) == 11

    def test_same_module_called_twice_is_not_a_cycle(self, tmp_path: Path):
        # Un même module source appelé 2× n'est PAS un cycle (namespacing
        # par module_path, unicité sur adresse complète).
        root = tmp_path / "twice"
        (root / "mod_x").mkdir(parents=True)
        (root / "main.tf").write_text(
            'module "x1" {\n  source = "./mod_x"\n}\n'
            'module "x2" {\n  source = "./mod_x"\n}\n',
            encoding="utf-8",
        )
        (root / "mod_x" / "main.tf").write_text(
            'resource "aws_s3_bucket" "x" {\n  bucket = "x"\n}\n',
            encoding="utf-8",
        )
        result = parse_directory(root)
        assert [r.address for r in result.resources] == [
            "module.x1.aws_s3_bucket.x",
            "module.x2.aws_s3_bucket.x",
        ]
        assert result.unparsed_files == []

    def test_module_outside_base_root(self, tmp_path: Path):
        # source = "../shared/mod" : os.path.relpath gère le ../ sans lever.
        root = tmp_path / "root"
        shared = tmp_path / "shared" / "mod"
        shared.mkdir(parents=True)
        root.mkdir()
        (root / "main.tf").write_text(
            'module "shared" {\n  source = "../shared/mod"\n}\n',
            encoding="utf-8",
        )
        (shared / "main.tf").write_text(
            'resource "aws_s3_bucket" "s" {\n  bucket = "s"\n}\n',
            encoding="utf-8",
        )
        result = parse_directory(root)
        assert [r.address for r in result.resources] == [
            "module.shared.aws_s3_bucket.s"
        ]
        assert result.resources[0].source_file == "../shared/mod/main.tf"
        assert result.unparsed_files == []
