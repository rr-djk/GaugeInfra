import os
from dataclasses import replace
from pathlib import Path
from typing import Any

import hcl2

from .exceptions import TerraformParseError
from .extractors import extract_all
from .loader import discover_tf_files, read_file_content
from .model import ModuleCall, ParsedTerraform, Resource


def _parse_single_file(
    filename: str,
    content: str,
    module_path: tuple[str, ...] = (),
) -> ParsedTerraform:
    """Parse un fichier HCL2 brut en ParsedTerraform (sans I/O)."""
    try:
        raw = hcl2.loads(content)
    except Exception as exc:
        # lark (sous python-hcl2) peut lever plusieurs types d'exceptions
        # non documentées exhaustivement — on les enveloppe toutes.
        msg = str(exc)
        if filename.endswith(".tf.json"):
            msg = ".tf.json non supporté en Phase 1"
        raise TerraformParseError(f"{filename}: {msg}") from exc

    return extract_all(raw, module_path=module_path, source_file=filename)


def parse_files(files: dict[str, str]) -> ParsedTerraform:
    """Parse un dict {nom_fichier: contenu} en ParsedTerraform.

    Pur, sans I/O, déterministe. Ne lève jamais : les fichiers invalides
    sont collectés dans unparsed_files.
    """
    return _parse_files_with_path(files, module_path=())


def _parse_files_with_path(
    files: dict[str, str],
    module_path: tuple[str, ...],
) -> ParsedTerraform:
    """Implémentation de parse_files avec namespacing par module_path.

    Deux except distincts : TerraformParseError = faute du fichier (syntaxe
    HCL), Exception générique = structure inattendue dans extract_all (bug
    potentiel du pipeline). Les deux sont collectés dans unparsed_files.
    """
    resources: list[Resource] = []
    data_sources: list[Resource] = []
    module_calls: list[ModuleCall] = []
    variables: dict[str, Any] = {}
    outputs: dict[str, Any] = {}
    locals_: dict[str, Any] = {}
    providers: list[dict[str, Any]] = []
    backend: dict[str, Any] | None = None
    other_blocks: dict[str, int] = {}
    unparsed: list[dict[str, Any]] = []

    for filename, content in files.items():
        try:
            parsed = _parse_single_file(filename, content, module_path)
        except TerraformParseError as exc:
            unparsed.append({"file": filename, "error": str(exc)})
            continue
        except Exception as exc:
            unparsed.append(
                {"file": filename, "error": f"erreur d'extraction interne : {exc}"}
            )
            continue

        resources.extend(parsed.resources)
        data_sources.extend(parsed.data_sources)
        module_calls.extend(parsed.module_calls)
        variables.update(parsed.variables)
        outputs.update(parsed.outputs)
        locals_.update(parsed.locals)
        providers.extend(parsed.providers)
        if parsed.backend is not None:
            backend = parsed.backend
        for k, v in parsed.other_blocks.items():
            other_blocks[k] = other_blocks.get(k, 0) + v

    return ParsedTerraform(
        resources=resources,
        data_sources=data_sources,
        module_calls=module_calls,
        variables=variables,
        outputs=outputs,
        locals=locals_,
        providers=providers,
        backend=backend,
        unparsed_files=unparsed,
        other_blocks=other_blocks,
    )


def parse_directory(root: Path) -> ParsedTerraform:
    """Parse un répertoire Terraform en ParsedTerraform (avec expansion).

    Lève FileNotFoundError si la racine n'existe pas. Les fichiers invalides
    ET les erreurs de lecture sont collectés dans unparsed_files (jamais levés).
    """
    parsed = _parse_directory_io(root, module_path=(), base_root=root)

    from . import expansion

    return expansion.expand_modules(
        parsed,
        root,
        source_stack={str(root.resolve())},
        base_root=root,
    )


def _parse_directory_io(
    root: Path,
    module_path: tuple[str, ...],
    base_root: Path,
) -> ParsedTerraform:
    """I/O + parse d'un répertoire, sans expansion ni état de récursion.

    source_file est relatif à base_root (racine d'origine du scan) pour la
    traçabilité. os.path.relpath ne lève jamais, même si un module pointe
    hors de base_root (ex. source = "../../../shared/modules/x").
    """
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"Répertoire racine introuvable : {root}")

    files: dict[str, str] = {}
    read_errors: list[dict[str, Any]] = []
    for path in discover_tf_files(root):
        rel = Path(os.path.relpath(path, base_root)).as_posix()
        try:
            files[rel] = read_file_content(path)
        except (OSError, UnicodeDecodeError) as exc:
            read_errors.append({"file": rel, "error": str(exc)})

    parsed = _parse_files_with_path(files, module_path=module_path)
    if read_errors:
        parsed = replace(
            parsed,
            unparsed_files=parsed.unparsed_files + read_errors,
        )
    return parsed
