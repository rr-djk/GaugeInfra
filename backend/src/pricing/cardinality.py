"""Résolution de la cardinalité effective des ressources.

La cardinalité effective est le multiplicateur de coût d'une ressource :
cardinalité de la ressource × cardinalité du module parent × cardinalité
des modules ancêtres. Elle est reconstruite depuis les adresses Terraform
(ex. module.a.module.b.aws_s3_bucket.this) et les ModuleCall du
ParsedTerraform.

Une expression non résolue (count = var.x) rend la cardinalité inconnue.
Elle n'est jamais remplacée par 1. Un count = 0 sur un ancêtre annule le
coût, même si un descendant est inconnu. Les références var.*, local.* et
les fonctions HCL restent hors périmètre de résolution.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from backend.src.parser.model import ParsedTerraform, Resource


class CardinalityStatus(StrEnum):
    """Statut de la cardinalité effective.

    - known : multiplicateur déterminé. Peut valoir 0 (coût nul).
    - unknown : expression non résolue ou configuration invalide. Aucun
      multiplicateur.
    """

    KNOWN = "known"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Cardinality:
    """Cardinalité effective d'une ressource (multiplicateur de coût)."""

    # Messages de raison réutilisables pour les cardinalités inconnues.
    REASON_UNRESOLVED = "expression Terraform non résolue"
    REASON_NEGATIVE_COUNT = "count négatif invalide"
    REASON_COUNT_AND_FOR_EACH = (
        "count et for_each ne peuvent pas être définis simultanément"
    )
    REASON_MODULE_NOT_FOUND = "module introuvable : {prefix}"
    REASON_UNKNOWN = "cardinalité inconnue"

    # Multiplicateur effectif. None si inconnu.
    multiplier: int | None
    # Statut de la cardinalité. Voir CardinalityStatus.
    status: CardinalityStatus
    # Raison d'une cardinalité inconnue. None si connue.
    reason: str | None = None


def _count_multiplier(count: Any) -> Cardinality:
    """Multiplicateur d'un count littéral (int ou bool).

    :param count: valeur du meta-argument count. Un int est un littéral,
        un bool vaut 1 (true) ou 0 (false), toute autre forme est une
        expression non résolue.
    :return: cardinalité du count.
    """
    if isinstance(count, bool):
        return Cardinality(multiplier=int(count), status=CardinalityStatus.KNOWN)
    if not isinstance(count, int):
        return Cardinality(
            multiplier=None,
            status=CardinalityStatus.UNKNOWN,
            reason=Cardinality.REASON_UNRESOLVED,
        )
    if count < 0:
        return Cardinality(
            multiplier=None,
            status=CardinalityStatus.UNKNOWN,
            reason=Cardinality.REASON_NEGATIVE_COUNT,
        )
    return Cardinality(multiplier=count, status=CardinalityStatus.KNOWN)


def _for_each_multiplier(for_each: Any) -> Cardinality:
    """Multiplicateur d'un for_each littéral (collection).

    :param for_each: valeur du meta-argument for_each. Une collection
        (liste, dict, set, tuple) donne sa longueur, toute autre forme est
        une expression non résolue.
    :return: cardinalité du for_each.
    """
    if isinstance(for_each, (list, dict, set, tuple)):
        return Cardinality(multiplier=len(for_each), status=CardinalityStatus.KNOWN)
    return Cardinality(
        multiplier=None,
        status=CardinalityStatus.UNKNOWN,
        reason=Cardinality.REASON_UNRESOLVED,
    )


def _block_cardinality(count: Any, for_each: Any) -> Cardinality:
    """Cardinalité d'un bloc (ressource ou module) depuis ses meta-arguments.

    :param count: meta-argument count du bloc. None si absent.
    :param for_each: meta-argument for_each du bloc. None si absent.
    :return: cardinalité du bloc. 1 si aucun meta-argument.
    """
    if count is not None and for_each is not None:
        return Cardinality(
            multiplier=None,
            status=CardinalityStatus.UNKNOWN,
            reason=Cardinality.REASON_COUNT_AND_FOR_EACH,
        )
    if count is not None:
        return _count_multiplier(count)
    if for_each is not None:
        return _for_each_multiplier(for_each)
    return Cardinality(multiplier=1, status=CardinalityStatus.KNOWN)


def _module_prefixes(address: str) -> list[str]:
    """Préfixes de modules d'une adresse, du plus court au plus long.

    Ex. "module.a.module.b.aws_s3_bucket.this" →
    ["module.a", "module.a.module.b"].

    :param address: adresse Terraform complète d'une ressource.
    :return: préfixes de modules de l'adresse, du plus court au plus long.
    """
    parts = address.split(".")
    prefixes: list[str] = []
    current: list[str] = []
    i = 0
    while i + 1 < len(parts) and parts[i] == "module":
        current.extend((parts[i], parts[i + 1]))
        prefixes.append(".".join(current))
        i += 2
    return prefixes


def _combine(factors: list[Cardinality]) -> Cardinality:
    """Multiplie les cardinalités connues.

    Un count = 0 sur un facteur annule le résultat, même si un autre
    facteur est inconnu. Sinon, la raison du premier facteur inconnu est
    propagée pour le diagnostic.

    :param factors: cardinalités à multiplier (ressource puis ancêtres).
    :return: cardinalité effective combinée.
    """
    for factor in factors:
        if factor.multiplier == 0:
            return Cardinality(multiplier=0, status=CardinalityStatus.KNOWN)
    for factor in factors:
        if factor.status == CardinalityStatus.UNKNOWN:
            return Cardinality(
                multiplier=None,
                status=CardinalityStatus.UNKNOWN,
                reason=factor.reason or Cardinality.REASON_UNKNOWN,
            )
    product = 1
    for factor in factors:
        product *= factor.multiplier
    return Cardinality(multiplier=product, status=CardinalityStatus.KNOWN)


class CardinalityResolver:
    """Résout la cardinalité effective d'une ressource depuis un ParsedTerraform."""

    def __init__(self, parsed: ParsedTerraform):
        """Construit le resolver.

        :param parsed: résultat du parsing Terraform. Les ModuleCall sont
            indexés par adresse pour retrouver les modules ancêtres.
        """
        self._module_calls = {call.address: call for call in parsed.module_calls}

    def resolve(self, resource: Resource) -> Cardinality:
        """Cardinalité effective d'une ressource.

        :param resource: ressource à évaluer. Sa cardinalité est multipliée
            par celle de ses modules ancêtres.
        :return: cardinalité effective de la ressource.
        """
        factors = [_block_cardinality(resource.count, resource.for_each)]
        factors.extend(self._ancestor_cardinalities(resource.address))
        return _combine(factors)

    def _ancestor_cardinalities(self, address: str) -> list[Cardinality]:
        """Cardinalités des modules ancêtres, du plus proche au plus lointain.

        :param address: adresse Terraform de la ressource.
        :return: cardinalités des modules ancêtres. Un module introuvable
            produit une cardinalité inconnue.
        """
        factors: list[Cardinality] = []
        for prefix in _module_prefixes(address):
            call = self._module_calls.get(prefix)
            if call is None:
                factors.append(
                    Cardinality(
                        multiplier=None,
                        status=CardinalityStatus.UNKNOWN,
                        reason=Cardinality.REASON_MODULE_NOT_FOUND.format(
                            prefix=prefix
                        ),
                    )
                )
            else:
                factors.append(_block_cardinality(call.count, call.for_each))
        return factors
