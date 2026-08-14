# Pin hcl2 — python-hcl2 8.1.2

> Étape 1 de la Phase 1. Reproduction : `uv run python docs/phase1/hcl2-probe.py`
> Version sondée : `8.1.2` · Date : 2026-08-14

Ce document verrouille empiriquement la représentation HCL renvoyée par `hcl2.loads()`.
Les formes ci-dessous conditionnent les règles de `parse.py` et les assertions des tests.

## Formes vérifiées (sortie réelle du probe)

### Blocs racine → listes de dicts

`resource`, `terraform`, `backend` et tous les blocs imbriqués sont des **listes de dicts** :

```python
{'resource': [{'"aws_s3_bucket"': {'"this"': {'bucket': '${var.bucket_name}', '__is_block__': True}}}]}
{'terraform': [{'backend': [{'"s3"': {'bucket': '"x"', 'use_lockfile': True, '__is_block__': True}}], '__is_block__': True}]}
```

- **Labels quotés** : `'"aws_s3_bucket"'`, `'"this"'` → à stripper.
- **Marqueur interne** `__is_block__: True` sur chaque bloc → à filtrer.
- Fichier commentaires-only : clé `__comments__` → à filtrer (non sondé ici, vu par le test-agent).

### Valeurs (brutes, jamais interprétées)

| Source HCL                       | Résultat hcl2                                                                                              |
| -------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `bucket = var.bucket_name`       | `'${var.bucket_name}'` (template)                                                                          |
| `bucket = aws_s3_bucket.this.id` | `'${aws_s3_bucket.this.id}'` (template)                                                                    |
| `count = 2`                      | `2` (**int**)                                                                                              |
| `count = length(var.list)`       | `'${length(var.list)}'` (**str**)                                                                          |
| `for_each = toset(var.items)`    | `'${toset(var.items)}'`                                                                                    |
| `methods = ["GET", "HEAD"]`      | `['"GET"', '"HEAD"']` (guillemets conservés)                                                               |
| `use_lockfile = true`            | `True` (bool)                                                                                              |
| `jsonencode({...})` multiligne   | aplati en un template unique `'${jsonencode({Version = "2012-10-17", Statement = [{Effect = "Allow"}]})}'` |
| heredoc `<<-EOT`                 | chaîne quotée, **marqueurs inclus** : `'"<<-EOT\n    ...\n  EOT"'` (`\n` échappés)                         |

### Blocs imbriqués / dynamic

```python
# versioning { status = "Enabled" }
'versioning': [{'status': '"Enabled"', '__is_block__': True}]

# dynamic "ingress" { for_each = ...; content { ... } }
'dynamic': [{'"ingress"': {'for_each': '${var.ports}',
                            'content': [{'port': '${ingress.value}', '__is_block__': True}],
                            '__is_block__': True}}]
```

### Asymétrie required_providers

La clé provider est **non quotée** (contrairement aux labels) — ne pas la stripper :

```python
{'required_providers': [{'aws': {'source': '"hashicorp/aws"', 'version': '"6.58.0"'}, '__is_block__': True}]}
```

### Cas d'erreur et cas triviaux

- HCL invalide → exception lark **`UnexpectedToken`** (ligne/colonne ; message brut inexploitable).
- `.tf.json` → même exception `UnexpectedToken` (le parser HCL2 ne lit pas le JSON).
- Fichier vide → `{}` (aucun bloc, aucune erreur).

## Règles retenues pour parse.py

1. Stripper les `"` des labels (resource/data/module/…), **sauf** les clés `required_providers`.
2. Normaliser les blocs racine : `liste → dict unique → {label1: {label2: body}}`.
3. Filtrer `__is_block__` et `__comments__` partout.
4. Conserver les valeurs **brutes** (templates `'${...}'`, littéraux quotés, bool, int). Ne rien interpréter.
5. Discriminer `count`/`for_each` : int littéral vs chaîne expression — les deux restent bruts en Phase 1.
6. Envelopper `UnexpectedToken` → `TerraformParseError` (message français ; `.tf.json` → « non supporté en Phase 1 »).
