from typing import Any


def strip_quotes(value: str) -> str:
    """Retire les guillemets encadrants une chaîne HCL2."""
    if isinstance(value, str) and value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    return value


def clean_value(value: Any) -> Any:
    """Filtre récursivement les marqueurs internes et déquote les strings."""
    if isinstance(value, dict):
        return {
            strip_quotes(k): clean_value(v)
            for k, v in value.items()
            if k not in ("__is_block__", "__comments__")
        }
    if isinstance(value, list):
        return [clean_value(v) for v in value]
    if isinstance(value, str):
        return strip_quotes(value)
    return value


def normalize_block(blocks: list[dict]) -> dict[str, Any]:
    """
    Transforme une liste de dicts HCL2 en un dict unique.
    Les labels sont déquotés (idempotent car clean_value le fait déjà).
    Les doublons de même clé sont mergés shallow.
    """
    result: dict[str, Any] = {}
    for item in blocks:
        item = clean_value(item)
        if not isinstance(item, dict):
            continue
        for key, val in item.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(val, dict)
            ):
                result[key].update(val)
            else:
                result[key] = val
    return result
