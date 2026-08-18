"""Modèles du domaine pricing. Données immuables, aucun I/O, aucun calcul AWS.

Ce module définit la sortie de toute la phase pricing : composantes de coût,
coût par ressource, hypothèses et rapport final. Chaque objet est immuable
(frozen) et les montants utilisent Decimal (jamais float).

Les statuts sont des StrEnum. Leurs valeurs sont stables dans le JSON livré
au frontend et à l'analyse Bedrock. La sémantique de chaque statut est
documentée sur son enum. C'est la référence unique pour l'agrégation et
l'interprétation des résultats. Chaque champ de dataclass est documenté en
regard de sa déclaration.
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Any

DEFAULT_CURRENCY = "USD"


class ComponentStatus(StrEnum):
    """Statut d'une composante de coût.

    - known : prix et quantité connus depuis le .tf. Montant exact.
    - free : ressource explicitement gratuite. Coût nul garanti, pas une
      absence de calcul.
    - assumed : quantité remplacée par une hypothèse d'usage. Montant estimé.
    - unknown : dimension présente mais expression non résolue. Aucun montant
      produit.
    - unsupported : type non tarifé par l'outil. Exclu du total, listé
      explicitement.
    - catalog_error : consultation des prix AWS en échec. Jamais converti
      en coût nul.
    """


class ReportStatus(StrEnum):
    """Statut global du rapport.

    - complete : tout est connu ou explicitement gratuit. Total exact.
    - partial : des hypothèses, des inconnus ou des non supportés sont
      présents. Total estimé.
    - unavailable : aucun calcul fiable possible. Ne pas présenter de total.
    """


class QuantitySource(StrEnum):
    """Origine de la quantité d'une composante.

    - config : quantité extraite de la configuration Terraform.
    - assumed : quantité remplacée par une hypothèse d'usage.
    - unknown : expression Terraform non résolue. Quantité inconnue.
    """


class AssumptionSource(StrEnum):
    """Provenance de la valeur d'une hypothèse.

    - default : valeur par défaut documentée de l'outil.
    - override : valeur fournie explicitement par l'utilisateur.
    """


@dataclass(frozen=True)
class CostComponent:
    """Une ligne de facturation d'une ressource."""

    # Adresse complète de la ressource (ex. module.x.aws_s3_bucket.this).
    resource_address: str
    # Type Terraform de la ressource (ex. aws_s3_bucket).
    resource_type: str
    # Identifiant logique stable de la composante (ex. storage, requests).
    component_id: str
    # Libellé court d'affichage (ex. Stockage, Requêtes).
    name: str
    # Quantité facturée (Decimal, jamais float).
    quantity: Decimal
    # Unité de la quantité (ex. GB-month, requests, hours).
    unit: str
    # Prix unitaire de la dimension (Decimal, devise du rapport).
    unit_price: Decimal
    # Montant de la composante. Vaut quantity × unit_price.
    amount: Decimal
    # Devise des montants (USD par défaut).
    currency: str
    # Origine de la quantité. Voir QuantitySource.
    quantity_source: QuantitySource
    # Statut de la composante. Voir ComponentStatus.
    status: ComponentStatus
    # Clés des hypothèses utilisées pour la quantité (vide si aucune).
    assumptions_used: list[str]
    # Clé canonique de requête Price List. None si aucun catalogue.
    catalog_key: str | None


@dataclass(frozen=True)
class ResourceCost:
    """Coût agrégé d'une ressource."""

    # Adresse complète de la ressource (ex. module.x.aws_lambda_function.this).
    address: str
    # Type Terraform de la ressource (ex. aws_lambda_function).
    type: str
    # Fichier source Terraform, relatif à la racine de scan.
    source_file: str
    # Cardinalité effective (multiplicateur de coût). None si inconnue.
    cardinality: int | None
    # Composantes de coût de la ressource.
    components: list[CostComponent]
    # Coût mensuel total de la ressource. Somme des composantes × cardinalité.
    monthly_cost: Decimal
    # Statut agrégé de la ressource. Voir ComponentStatus.
    status: ComponentStatus
    # Avertissements non bloquants (ex. dimension non tarifée).
    warnings: list[str]


@dataclass(frozen=True)
class Assumption:
    """Une hypothèse d'usage appliquée au calcul."""

    # Clé de l'hypothèse (ex. lambda.requests_month).
    key: str
    # Valeur de l'hypothèse.
    value: Decimal
    # Unité de la valeur (ex. requests/month, GB).
    unit: str
    # Provenance de la valeur : default (outil) ou override (utilisateur).
    source: AssumptionSource
    # Adresse de la ressource ciblée. None si l'hypothèse est globale.
    resource_address: str | None
    # Identifiant de la composante ciblée. None si l'hypothèse est globale.
    component_id: str | None


@dataclass(frozen=True)
class CostReport:
    """Rapport global de coût."""

    # Somme des composantes calculables sans hypothèse. Montant exact.
    known_monthly_total: Decimal
    # Somme incluant les composantes assumées. Montant estimé.
    estimated_monthly_total: Decimal
    # Devise des montants (USD par défaut).
    currency: str
    # Statut global du rapport. Voir ReportStatus.
    status: ReportStatus
    # Coûts détaillés par ressource.
    resources: list[ResourceCost]
    # Hypothèses appliquées (défauts de l'outil et surcharges utilisateur).
    assumptions: list[Assumption]
    # Adresses des ressources non tarifées. Exclues du total, listées.
    unsupported_resources: list[str]
    # Adresses des ressources avec dimension ou cardinalité inconnue.
    unknown_resources: list[str]
    # Échecs de consultation des prix. Jamais convertis en zéro.
    catalog_errors: list[str]
    # Fichiers Terraform non parsés, reportés pour la couverture.
    unparsed_files: list[dict[str, Any]]
    # Couverture de l'analyse (ex. analyzed, unsupported, unparsed_files).
    coverage: dict[str, int]
