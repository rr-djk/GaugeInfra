from dataclasses import replace
from pathlib import Path

from .model import ParsedTerraform
from .pipeline import _parse_directory_io

# Limite de sécurité contre la récursion pathologique : les projets
# Terraform réels n'imbriquent jamais plus de ~5 niveaux de modules.
# 10 est un plafond généreux qui ne se déclenche jamais sur du code
# légitime, tout en bornant le pire cas (cycles échappant à la pile,
# empilement de frames Python, explosion combinatoire). Au-delà,
# l'appel est enregistré dans unparsed_files, jamais silencieux.
MAX_MODULE_DEPTH = 10


def _is_local_source(source: str) -> bool:
    """Une source locale commence par ./ ou ../ (chemin relatif)."""
    return source.startswith("./") or source.startswith("../")


def expand_modules(
    parsed: ParsedTerraform,
    root: Path,
    source_stack: frozenset[str] = frozenset(),
    current_path: tuple[str, ...] = (),
    depth: int = 0,
    base_root: Path | None = None,
) -> ParsedTerraform:
    """Résout récursivement les modules locaux d'un ParsedTerraform.

    Porte tout l'état de récursion (pile de sources pour détecter les cycles,
    profondeur pour limiter la récursion, namespacing pour construire les
    adresses de type "module.a.module.b.resource").

    root : répertoire du module en cours de traitement (change à chaque
           niveau de récursion).
    base_root : racine du projet, fixe sur toute la récursion — utilisée
           pour calculer des chemins relatifs cohérents (ex: source_file)
           peu importe la profondeur d'imbrication du module courant.

    Les sources distantes (registry, git, etc.) restent non résolues dans
    module_calls. Les cycles, dépassements de profondeur et modules
    introuvables sont collectés dans unparsed_files (jamais silencieux,
    jamais levés).
    """
    if base_root is None:
        base_root = root

    resources = list(parsed.resources)
    data_sources = list(parsed.data_sources)
    module_calls = list(parsed.module_calls)
    unparsed = list(parsed.unparsed_files)
    other_blocks = dict(parsed.other_blocks)

    for call in parsed.module_calls:
        if not _is_local_source(call.source):
            continue

        resolved = (root / call.source).resolve()
        canonical = str(resolved)

        # Chaque garde ci-dessous correspond à une raison de ne PAS descendre
        # dans ce module ; l'échec est toujours enregistré (jamais silencieux)
        # et on passe à l'appel suivant plutôt que d'interrompre toute la
        # résolution du projet.
        if canonical in source_stack:
            unparsed.append(
                {
                    "file": call.address,
                    "error": f"cycle de modules détecté : {canonical}",
                }
            )
            continue
        if depth >= MAX_MODULE_DEPTH:
            unparsed.append(
                {
                    "file": call.address,
                    "error": f"profondeur maximale ({MAX_MODULE_DEPTH}) dépassée",
                }
            )
            continue
        if not resolved.is_dir():
            unparsed.append(
                {
                    "file": call.address,
                    "error": f"module local introuvable : {canonical}",
                }
            )
            continue

        # call.address est déjà préfixé par current_path (ex: si on est dans
        # module.parent, call.address = "module.parent.module.child"). On ne
        # veut garder que le segment propre à cet appel ("module.child"), car
        # new_path va lui-même être construit par concaténation avec
        # current_path plus bas — dupliquer le préfixe parent créerait
        # "module.parent.module.parent.module.child".
        #
        # Exemple : call.address = "module.parent.module.child"
        #           -> call_name  = "module.child"
        call_name = "module." + call.address.rsplit("module.", 1)[-1]
        new_path = current_path + (call_name,)
        sub = _parse_directory_io(resolved, module_path=new_path, base_root=base_root)
        sub_expanded = expand_modules(
            sub,
            resolved,
            source_stack=source_stack | {canonical},
            current_path=new_path,
            depth=depth + 1,
            base_root=base_root,
        )

        resources.extend(sub_expanded.resources)
        data_sources.extend(sub_expanded.data_sources)
        module_calls.extend(sub_expanded.module_calls)
        unparsed.extend(sub_expanded.unparsed_files)
        for k, v in sub_expanded.other_blocks.items():
            other_blocks[k] = other_blocks.get(k, 0) + v

    return replace(
        parsed,
        resources=resources,
        data_sources=data_sources,
        module_calls=module_calls,
        unparsed_files=unparsed,
        other_blocks=other_blocks,
    )
