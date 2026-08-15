"""Fixtures partagées de la suite de tests du parseur Terraform.

Les échantillons HCL vivent dans `fixtures/` (formes du pinning
docs/phase1/HCL2-PINNING.md) ; les arbres de modules pour l'expansion
sont construits dynamiquement dans tmp_path quand ils doivent être
modifiés (ex. chaîne de profondeur).
"""

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def read_fixture():
    """Lit le contenu UTF-8 d'un fichier de fixtures."""

    def _read(name: str) -> str:
        return (FIXTURES_DIR / name).read_text(encoding="utf-8")

    return _read


@pytest.fixture
def hcl_samples(read_fixture) -> dict[str, str]:
    """Échantillons HCL des fixtures, prêts pour parse_files (paste mode)."""
    return {
        "basic.tf": read_fixture("basic.tf"),
        "providers.tf": read_fixture("providers.tf"),
        "variables_outputs_locals.tf": read_fixture("variables_outputs_locals.tf"),
        "modules.tf": read_fixture("modules.tf"),
        "unknown_blocks.tf": read_fixture("unknown_blocks.tf"),
        "invalid.tf": read_fixture("invalid.tf"),
        "main.tf.json": read_fixture("main.tf.json"),
        "comments_only.tf": read_fixture("comments_only.tf"),
        "empty.tf": read_fixture("empty.tf"),
    }


@pytest.fixture
def expansion_root() -> Path:
    """Racine d'expansion : modules imbriqués + source distante + module manquant."""
    return FIXTURES_DIR / "expansion" / "root"


@pytest.fixture
def cycle_root() -> Path:
    """Racine d'un cycle de modules (a -> b -> a)."""
    return FIXTURES_DIR / "expansion" / "cycle"


def build_depth_tree(tmp_path: Path, n_modules: int) -> Path:
    """Construit une chaîne de n_modules modules locaux imbriqués.

    Chaque module m_i appelle m_{i+1} via `source = "../mod_{i+1}"`.
    Le dernier module contient une ressource. Retourne la racine.
    """
    root = tmp_path / "depth_root"
    for i in range(n_modules):
        (root / f"mod_{i}").mkdir(parents=True, exist_ok=True)
    (root / "main.tf").write_text(
        'module "m0" {\n  source = "./mod_0"\n}\n', encoding="utf-8"
    )
    for i in range(n_modules - 1):
        (root / f"mod_{i}" / "main.tf").write_text(
            f'module "m{i + 1}" {{\n  source = "../mod_{i + 1}"\n}}\n',
            encoding="utf-8",
        )
    (root / f"mod_{n_modules - 1}" / "main.tf").write_text(
        'resource "aws_s3_bucket" "deep" {\n  bucket = "deep"\n}\n',
        encoding="utf-8",
    )
    return root
