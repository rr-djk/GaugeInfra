from pathlib import Path


def discover_tf_files(directory: Path) -> list[Path]:
    """Retourne les fichiers .tf à la racine d'un répertoire (non récursif).

    La descente dans les sous-dossiers est gérée par expansion.py via les
    module_calls.source. Ignore .tfvars et les entrées non-fichiers.
    Tri déterministe (par chemin).
    """
    files: list[Path] = []
    for path in sorted(directory.glob("*.tf")):
        if not path.is_file():
            continue
        if path.name.endswith(".tfvars"):
            continue
        files.append(path)
    return files


def read_file_content(path: Path) -> str:
    """Lit le contenu UTF-8 d'un fichier (tolère un BOM optionnel).

    Les exceptions de lecture (UnicodeDecodeError, PermissionError, fichier
    supprimé entre discover et read) remontent brutes — pipeline.py les
    attrape et les collecte dans unparsed_files.
    """
    return path.read_text(encoding="utf-8-sig")
