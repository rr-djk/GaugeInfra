"""Contrat de la résolution de cardinalité : helpers, combinaison, resolver."""

import json
from dataclasses import FrozenInstanceError

import pytest

from backend.src.parser.model import ModuleCall, ParsedTerraform, Resource
from backend.src.pricing.cardinality import (
    Cardinality,
    CardinalityResolver,
    CardinalityStatus,
    _block_cardinality,
    _combine,
    _count_multiplier,
    _for_each_multiplier,
    _module_prefixes,
)


def _make_resource(**overrides) -> Resource:
    """Construit une ressource valide, surchargeable par mot-clés."""
    base = {
        "address": "aws_s3_bucket.this",
        "type": "aws_s3_bucket",
        "name": "this",
    }
    base.update(overrides)
    return Resource(**base)


def _make_module_call(**overrides) -> ModuleCall:
    """Construit un appel de module valide, surchargeable par mot-clés."""
    base = {
        "address": "module.app",
        "source": "./app",
    }
    base.update(overrides)
    return ModuleCall(**base)


def _make_parsed(**overrides) -> ParsedTerraform:
    """Construit un ParsedTerraform valide, surchargeable par mot-clés."""
    base = {"module_calls": []}
    base.update(overrides)
    return ParsedTerraform(**base)


class TestCardinalityStatus:
    """Contrat de CardinalityStatus : valeurs, str, sérialisation JSON."""

    @pytest.mark.parametrize(
        ("member", "expected"),
        [
            (CardinalityStatus.KNOWN, "known"),
            (CardinalityStatus.UNKNOWN, "unknown"),
        ],
    )
    def test_value_str_json(self, member, expected):
        assert member == expected
        assert str(member) == expected
        assert json.dumps(member) == f'"{expected}"'

    def test_exhaustive_members(self):
        assert issubclass(CardinalityStatus, str)
        assert {member.name: member.value for member in CardinalityStatus} == {
            "KNOWN": "known",
            "UNKNOWN": "unknown",
        }


class TestCardinality:
    """Contrat de Cardinality : champs, default reason, frozen."""

    def test_full_construction(self):
        card = Cardinality(multiplier=3, status=CardinalityStatus.KNOWN)
        assert card.multiplier == 3
        assert card.status is CardinalityStatus.KNOWN
        assert card.reason is None

    def test_unknown_with_reason(self):
        card = Cardinality(
            multiplier=None,
            status=CardinalityStatus.UNKNOWN,
            reason="expression Terraform non résolue",
        )
        assert card.multiplier is None
        assert card.status is CardinalityStatus.UNKNOWN
        assert card.reason == "expression Terraform non résolue"

    @pytest.mark.parametrize("field_name", ["multiplier", "status", "reason"])
    def test_is_frozen(self, field_name):
        card = Cardinality(multiplier=1, status=CardinalityStatus.KNOWN)
        with pytest.raises(FrozenInstanceError):
            setattr(card, field_name, "autre")


class TestCountMultiplier:
    """Contrat de _count_multiplier : bool, int, expressions non résolues."""

    @pytest.mark.parametrize(
        ("count", "expected"),
        [
            (True, 1),
            (False, 0),
            (0, 0),
            (1, 1),
            (3, 3),
        ],
    )
    def test_literal_known(self, count, expected):
        card = _count_multiplier(count)
        assert card.multiplier == expected
        assert card.status is CardinalityStatus.KNOWN
        assert card.reason is None

    def test_negative_count_unknown(self):
        card = _count_multiplier(-1)
        assert card.multiplier is None
        assert card.status is CardinalityStatus.UNKNOWN
        assert card.reason == "count négatif invalide"

    @pytest.mark.parametrize("count", ["${var.replicas}", "var.replicas", 1.5, None])
    def test_unresolved_expression_unknown(self, count):
        card = _count_multiplier(count)
        assert card.multiplier is None
        assert card.status is CardinalityStatus.UNKNOWN
        assert card.reason == "expression Terraform non résolue"


class TestForEachMultiplier:
    """Contrat de _for_each_multiplier : collections littérales, expressions."""

    @pytest.mark.parametrize(
        ("for_each", "expected"),
        [
            (["a", "b"], 2),
            ({"blue": 1, "green": 2}, 2),
            ({"a", "b", "c"}, 3),
            (("a", "b", "c", "d"), 4),
            ([], 0),
            ({}, 0),
        ],
    )
    def test_literal_collection_known(self, for_each, expected):
        card = _for_each_multiplier(for_each)
        assert card.multiplier == expected
        assert card.status is CardinalityStatus.KNOWN
        assert card.reason is None

    @pytest.mark.parametrize("for_each", ["${var.items}", "var.items", 3, None])
    def test_unresolved_expression_unknown(self, for_each):
        card = _for_each_multiplier(for_each)
        assert card.multiplier is None
        assert card.status is CardinalityStatus.UNKNOWN
        assert card.reason == "expression Terraform non résolue"


class TestBlockCardinality:
    """Contrat de _block_cardinality : count/for_each exclusifs, défaut 1."""

    def test_no_meta_argument(self):
        card = _block_cardinality(None, None)
        assert card.multiplier == 1
        assert card.status is CardinalityStatus.KNOWN
        assert card.reason is None

    def test_count_only(self):
        card = _block_cardinality(3, None)
        assert card.multiplier == 3
        assert card.status is CardinalityStatus.KNOWN

    def test_for_each_only(self):
        card = _block_cardinality(None, ["a", "b"])
        assert card.multiplier == 2
        assert card.status is CardinalityStatus.KNOWN

    def test_count_and_for_each_conflict(self):
        card = _block_cardinality(2, ["a"])
        assert card.multiplier is None
        assert card.status is CardinalityStatus.UNKNOWN
        assert (
            card.reason == "count et for_each ne peuvent pas être définis simultanément"
        )


class TestModulePrefixes:
    """Contrat de _module_prefixes : préfixes du plus court au plus long."""

    def test_nested_modules(self):
        assert _module_prefixes("module.a.module.b.aws_s3_bucket.this") == [
            "module.a",
            "module.a.module.b",
        ]

    def test_single_module(self):
        assert _module_prefixes("module.a.aws_s3_bucket.this") == ["module.a"]

    def test_no_module_prefix(self):
        assert _module_prefixes("aws_s3_bucket.this") == []

    def test_module_only_address(self):
        assert _module_prefixes("module.a") == ["module.a"]


class TestCombine:
    """Contrat de _combine : zéro gagne, premier inconnu propagé, produit."""

    def test_all_known_product(self):
        factors = [
            Cardinality(multiplier=2, status=CardinalityStatus.KNOWN),
            Cardinality(multiplier=3, status=CardinalityStatus.KNOWN),
        ]
        card = _combine(factors)
        assert card.multiplier == 6
        assert card.status is CardinalityStatus.KNOWN
        assert card.reason is None

    def test_single_factor(self):
        card = _combine([Cardinality(multiplier=5, status=CardinalityStatus.KNOWN)])
        assert card.multiplier == 5
        assert card.status is CardinalityStatus.KNOWN

    def test_empty_factors(self):
        card = _combine([])
        assert card.multiplier == 1
        assert card.status is CardinalityStatus.KNOWN

    def test_zero_wins_over_unknown(self):
        factors = [
            Cardinality(
                multiplier=None,
                status=CardinalityStatus.UNKNOWN,
                reason="expression Terraform non résolue",
            ),
            Cardinality(multiplier=0, status=CardinalityStatus.KNOWN),
        ]
        card = _combine(factors)
        assert card.multiplier == 0
        assert card.status is CardinalityStatus.KNOWN
        assert card.reason is None

    def test_zero_wins_over_known(self):
        factors = [
            Cardinality(multiplier=0, status=CardinalityStatus.KNOWN),
            Cardinality(multiplier=3, status=CardinalityStatus.KNOWN),
        ]
        card = _combine(factors)
        assert card.multiplier == 0
        assert card.status is CardinalityStatus.KNOWN

    def test_first_unknown_reason_propagated(self):
        factors = [
            Cardinality(
                multiplier=None,
                status=CardinalityStatus.UNKNOWN,
                reason="première",
            ),
            Cardinality(
                multiplier=None,
                status=CardinalityStatus.UNKNOWN,
                reason="seconde",
            ),
        ]
        card = _combine(factors)
        assert card.multiplier is None
        assert card.status is CardinalityStatus.UNKNOWN
        assert card.reason == "première"

    def test_unknown_without_reason_fallback(self):
        card = _combine(
            [Cardinality(multiplier=None, status=CardinalityStatus.UNKNOWN)]
        )
        assert card.multiplier is None
        assert card.status is CardinalityStatus.UNKNOWN
        assert card.reason == "cardinalité inconnue"


class TestCardinalityResolver:
    """Contrat de CardinalityResolver : ressource × modules ancêtres."""

    def test_resource_without_module(self):
        resolver = CardinalityResolver(_make_parsed())
        card = resolver.resolve(_make_resource())
        assert card.multiplier == 1
        assert card.status is CardinalityStatus.KNOWN
        assert card.reason is None

    @pytest.mark.parametrize(
        ("count", "expected"),
        [
            (3, 3),
            (True, 1),
            (False, 0),
        ],
    )
    def test_resource_count(self, count, expected):
        resolver = CardinalityResolver(_make_parsed())
        card = resolver.resolve(_make_resource(count=count))
        assert card.multiplier == expected
        assert card.status is CardinalityStatus.KNOWN

    @pytest.mark.parametrize(
        ("for_each", "expected"),
        [
            (["a", "b"], 2),
            ({"blue": 1, "green": 2}, 2),
            ({"a", "b", "c"}, 3),
        ],
    )
    def test_resource_for_each(self, for_each, expected):
        resolver = CardinalityResolver(_make_parsed())
        card = resolver.resolve(_make_resource(for_each=for_each))
        assert card.multiplier == expected
        assert card.status is CardinalityStatus.KNOWN

    def test_parent_module_count_multiplies(self):
        parsed = _make_parsed(
            module_calls=[_make_module_call(address="module.app", count=3)]
        )
        resolver = CardinalityResolver(parsed)
        card = resolver.resolve(
            _make_resource(address="module.app.aws_s3_bucket.this", count=2)
        )
        assert card.multiplier == 6
        assert card.status is CardinalityStatus.KNOWN

    def test_parent_module_for_each_multiplies(self):
        parsed = _make_parsed(
            module_calls=[
                _make_module_call(address="module.app", for_each=["a", "b", "c"])
            ]
        )
        resolver = CardinalityResolver(parsed)
        card = resolver.resolve(_make_resource(address="module.app.aws_s3_bucket.this"))
        assert card.multiplier == 3
        assert card.status is CardinalityStatus.KNOWN

    def test_module_for_each_and_resource_count(self):
        parsed = _make_parsed(
            module_calls=[_make_module_call(address="module.app", for_each=["a", "b"])]
        )
        resolver = CardinalityResolver(parsed)
        card = resolver.resolve(
            _make_resource(address="module.app.aws_s3_bucket.this", count=3)
        )
        assert card.multiplier == 6
        assert card.status is CardinalityStatus.KNOWN

    def test_nested_modules_product(self):
        parsed = _make_parsed(
            module_calls=[
                _make_module_call(address="module.a", count=2),
                _make_module_call(address="module.a.module.b", count=3),
            ]
        )
        resolver = CardinalityResolver(parsed)
        card = resolver.resolve(
            _make_resource(address="module.a.module.b.aws_s3_bucket.this", count=4)
        )
        assert card.multiplier == 24
        assert card.status is CardinalityStatus.KNOWN

    def test_resource_count_zero(self):
        resolver = CardinalityResolver(_make_parsed())
        card = resolver.resolve(_make_resource(count=0))
        assert card.multiplier == 0
        assert card.status is CardinalityStatus.KNOWN

    def test_zero_ancestor_wins_over_unknown_descendant(self):
        parsed = _make_parsed(
            module_calls=[_make_module_call(address="module.a", count=0)]
        )
        resolver = CardinalityResolver(parsed)
        card = resolver.resolve(
            _make_resource(
                address="module.a.aws_s3_bucket.this", count="${var.replicas}"
            )
        )
        assert card.multiplier == 0
        assert card.status is CardinalityStatus.KNOWN

    @pytest.mark.parametrize(
        ("count", "for_each"),
        [
            ("${var.replicas}", None),
            (None, "${var.items}"),
        ],
    )
    def test_unresolved_expression_never_one(self, count, for_each):
        resolver = CardinalityResolver(_make_parsed())
        card = resolver.resolve(_make_resource(count=count, for_each=for_each))
        assert card.multiplier is None
        assert card.status is CardinalityStatus.UNKNOWN
        assert card.reason == "expression Terraform non résolue"

    def test_negative_count_unknown(self):
        resolver = CardinalityResolver(_make_parsed())
        card = resolver.resolve(_make_resource(count=-1))
        assert card.multiplier is None
        assert card.status is CardinalityStatus.UNKNOWN
        assert card.reason == "count négatif invalide"

    def test_count_and_for_each_conflict(self):
        resolver = CardinalityResolver(_make_parsed())
        card = resolver.resolve(_make_resource(count=2, for_each=["a"]))
        assert card.multiplier is None
        assert card.status is CardinalityStatus.UNKNOWN
        assert (
            card.reason == "count et for_each ne peuvent pas être définis simultanément"
        )

    def test_missing_module_prefix_unknown(self):
        resolver = CardinalityResolver(_make_parsed())
        card = resolver.resolve(_make_resource(address="module.a.aws_s3_bucket.this"))
        assert card.multiplier is None
        assert card.status is CardinalityStatus.UNKNOWN
        assert card.reason == "module introuvable : module.a"

    def test_missing_module_prefix_with_known_resource(self):
        resolver = CardinalityResolver(_make_parsed())
        card = resolver.resolve(
            _make_resource(address="module.a.aws_s3_bucket.this", count=2)
        )
        assert card.multiplier is None
        assert card.status is CardinalityStatus.UNKNOWN
        assert card.reason == "module introuvable : module.a"

    def test_resource_unknown_reason_takes_precedence(self):
        resolver = CardinalityResolver(_make_parsed())
        card = resolver.resolve(
            _make_resource(
                address="module.a.aws_s3_bucket.this", count="${var.replicas}"
            )
        )
        assert card.multiplier is None
        assert card.status is CardinalityStatus.UNKNOWN
        assert card.reason == "expression Terraform non résolue"

    def test_same_name_modules_in_different_contexts(self):
        parsed = _make_parsed(
            module_calls=[
                _make_module_call(address="module.a", count=2),
                _make_module_call(address="module.b", count=5),
            ]
        )
        resolver = CardinalityResolver(parsed)
        card_a = resolver.resolve(_make_resource(address="module.a.aws_s3_bucket.this"))
        card_b = resolver.resolve(_make_resource(address="module.b.aws_s3_bucket.this"))
        assert card_a.multiplier == 2
        assert card_b.multiplier == 5

    def test_same_leaf_module_name_in_different_parents(self):
        parsed = _make_parsed(
            module_calls=[
                _make_module_call(address="module.a"),
                _make_module_call(address="module.a.module.x", count=2),
                _make_module_call(address="module.b"),
                _make_module_call(address="module.b.module.x", count=5),
            ]
        )
        resolver = CardinalityResolver(parsed)
        card_a = resolver.resolve(
            _make_resource(address="module.a.module.x.aws_s3_bucket.this")
        )
        card_b = resolver.resolve(
            _make_resource(address="module.b.module.x.aws_s3_bucket.this")
        )
        assert card_a.multiplier == 2
        assert card_b.multiplier == 5
