"""Contrat du modèle pricing : enums, defaults Decimal, objets frozen."""

import json
from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from backend.src.pricing.model import (
    DEFAULT_CURRENCY,
    Assumption,
    AssumptionSource,
    ComponentStatus,
    CostComponent,
    CostReport,
    QuantitySource,
    ReportStatus,
    ResourceCost,
)


def _make_component(**overrides) -> CostComponent:
    """Construit une composante valide, surchargeable par mot-clés."""
    base = {
        "resource_address": "aws_s3_bucket.this",
        "resource_type": "aws_s3_bucket",
        "component_id": "storage",
        "name": "Stockage",
        "quantity": Decimal("100"),
        "unit": "GB-month",
        "unit_price": Decimal("0.023"),
        "amount": Decimal("2.30"),
    }
    base.update(overrides)
    return CostComponent(**base)


class TestEnums:
    """Contrat des quatre StrEnum : valeurs, str, sérialisation JSON, exhaustivité."""

    @pytest.mark.parametrize(
        ("member", "expected"),
        [
            (ComponentStatus.KNOWN, "known"),
            (ComponentStatus.FREE, "free"),
            (ComponentStatus.ASSUMED, "assumed"),
            (ComponentStatus.UNKNOWN, "unknown"),
            (ComponentStatus.UNSUPPORTED, "unsupported"),
            (ComponentStatus.CATALOG_ERROR, "catalog_error"),
            (ReportStatus.COMPLETE, "complete"),
            (ReportStatus.PARTIAL, "partial"),
            (ReportStatus.UNAVAILABLE, "unavailable"),
            (QuantitySource.CONFIG, "config"),
            (QuantitySource.ASSUMED, "assumed"),
            (QuantitySource.UNKNOWN, "unknown"),
            (AssumptionSource.DEFAULT, "default"),
            (AssumptionSource.OVERRIDE, "override"),
        ],
    )
    def test_value_str_json(self, member, expected):
        assert member == expected
        assert str(member) == expected
        assert json.dumps(member) == f'"{expected}"'

    @pytest.mark.parametrize(
        ("enum_class", "expected"),
        [
            (
                ComponentStatus,
                {
                    "KNOWN": "known",
                    "FREE": "free",
                    "ASSUMED": "assumed",
                    "UNKNOWN": "unknown",
                    "UNSUPPORTED": "unsupported",
                    "CATALOG_ERROR": "catalog_error",
                },
            ),
            (
                ReportStatus,
                {
                    "COMPLETE": "complete",
                    "PARTIAL": "partial",
                    "UNAVAILABLE": "unavailable",
                },
            ),
            (
                QuantitySource,
                {"CONFIG": "config", "ASSUMED": "assumed", "UNKNOWN": "unknown"},
            ),
            (
                AssumptionSource,
                {"DEFAULT": "default", "OVERRIDE": "override"},
            ),
        ],
    )
    def test_exhaustive_members(self, enum_class, expected):
        assert issubclass(enum_class, str)
        assert {member.name: member.value for member in enum_class} == expected


class TestDEFAULT_CURRENCY:
    """Constante de devise par défaut du modèle."""

    def test_default_currency(self):
        assert DEFAULT_CURRENCY == "USD"


class TestCostComponent:
    """Contrat de CostComponent : champs requis, defaults, Decimal, frozen."""

    def test_full_construction(self):
        cc = CostComponent(
            resource_address="module.app.aws_s3_bucket.this",
            resource_type="aws_s3_bucket",
            component_id="storage",
            name="Stockage",
            quantity=Decimal("100"),
            unit="GB-month",
            unit_price=Decimal("0.023"),
            amount=Decimal("2.30"),
            currency="EUR",
            quantity_source=QuantitySource.CONFIG,
            status=ComponentStatus.KNOWN,
            assumptions_used=["s3.storage_gb"],
            catalog_key="AWS-S3:StandardStorage",
        )
        assert cc.resource_address == "module.app.aws_s3_bucket.this"
        assert cc.resource_type == "aws_s3_bucket"
        assert cc.component_id == "storage"
        assert cc.name == "Stockage"
        assert cc.quantity == Decimal("100")
        assert cc.unit == "GB-month"
        assert cc.unit_price == Decimal("0.023")
        assert cc.amount == Decimal("2.30")
        assert cc.currency == "EUR"
        assert cc.quantity_source is QuantitySource.CONFIG
        assert cc.status is ComponentStatus.KNOWN
        assert cc.assumptions_used == ["s3.storage_gb"]
        assert cc.catalog_key == "AWS-S3:StandardStorage"

    def test_defaults(self):
        cc = _make_component()
        assert cc.currency == "USD"
        assert cc.quantity_source is QuantitySource.UNKNOWN
        assert cc.status is ComponentStatus.UNKNOWN
        assert cc.assumptions_used == []
        assert cc.catalog_key is None

    def test_money_fields_are_decimal(self):
        cc = _make_component()
        assert type(cc.quantity) is Decimal
        assert type(cc.unit_price) is Decimal
        assert type(cc.amount) is Decimal

    @pytest.mark.parametrize("field_name", ["quantity", "status", "catalog_key"])
    def test_is_frozen(self, field_name):
        cc = _make_component()
        with pytest.raises(FrozenInstanceError):
            setattr(cc, field_name, "autre")


class TestResourceCost:
    """Contrat de ResourceCost : champs requis, cardinalité, defaults, frozen."""

    def test_full_construction(self):
        rc = ResourceCost(
            address="module.app.aws_lambda_function.this",
            type="aws_lambda_function",
            source_file="../../modules/lambda/main.tf",
            cardinality=2,
            components=[_make_component(component_id="requests", name="Requêtes")],
            monthly_cost=Decimal("0.40"),
            status=ComponentStatus.KNOWN,
            warnings=["dimension non tarifée"],
        )
        assert rc.address == "module.app.aws_lambda_function.this"
        assert rc.type == "aws_lambda_function"
        assert rc.source_file == "../../modules/lambda/main.tf"
        assert rc.cardinality == 2
        assert rc.components[0].component_id == "requests"
        assert rc.monthly_cost == Decimal("0.40")
        assert rc.status is ComponentStatus.KNOWN
        assert rc.warnings == ["dimension non tarifée"]

    def test_cardinality_accepts_int(self):
        rc = ResourceCost(address="a", type="t", source_file="s.tf", cardinality=3)
        assert type(rc.cardinality) is int
        assert rc.cardinality == 3

    def test_cardinality_accepts_none(self):
        rc = ResourceCost(address="a", type="t", source_file="s.tf", cardinality=None)
        assert rc.cardinality is None

    def test_defaults(self):
        rc = ResourceCost(address="a", type="t", source_file="s.tf", cardinality=1)
        assert rc.components == []
        assert type(rc.monthly_cost) is Decimal
        assert rc.monthly_cost == Decimal("0")
        assert rc.status is ComponentStatus.UNKNOWN
        assert rc.warnings == []

    @pytest.mark.parametrize("field_name", ["address", "cardinality", "monthly_cost"])
    def test_is_frozen(self, field_name):
        rc = ResourceCost(address="a", type="t", source_file="s.tf", cardinality=1)
        with pytest.raises(FrozenInstanceError):
            setattr(rc, field_name, "autre")


class TestAssumption:
    """Contrat de Assumption : champs requis, defaults, source, frozen."""

    def test_full_construction(self):
        a = Assumption(
            key="lambda.requests_month",
            value=Decimal("1000000"),
            unit="requests/month",
            source=AssumptionSource.OVERRIDE,
            resource_address="module.app.aws_lambda_function.this",
            component_id="requests",
        )
        assert a.key == "lambda.requests_month"
        assert type(a.value) is Decimal
        assert a.value == Decimal("1000000")
        assert a.unit == "requests/month"
        assert a.source is AssumptionSource.OVERRIDE
        assert a.resource_address == "module.app.aws_lambda_function.this"
        assert a.component_id == "requests"

    def test_defaults(self):
        a = Assumption(key="s3.storage_gb", value=Decimal("10"), unit="GB")
        assert a.source is AssumptionSource.DEFAULT
        assert a.resource_address is None
        assert a.component_id is None

    @pytest.mark.parametrize("field_name", ["key", "value", "source"])
    def test_is_frozen(self, field_name):
        a = Assumption(key="k", value=Decimal("1"), unit="u")
        with pytest.raises(FrozenInstanceError):
            setattr(a, field_name, "autre")


class TestCostReport:
    """Contrat de CostReport : defaults, construction complète, frozen."""

    def test_defaults(self):
        report = CostReport()
        assert type(report.known_monthly_total) is Decimal
        assert report.known_monthly_total == Decimal("0")
        assert type(report.estimated_monthly_total) is Decimal
        assert report.estimated_monthly_total == Decimal("0")
        assert report.currency == "USD"
        assert report.status is ReportStatus.UNAVAILABLE
        assert report.resources == []
        assert report.assumptions == []
        assert report.unsupported_resources == []
        assert report.unknown_resources == []
        assert report.catalog_errors == []
        assert report.unparsed_files == []
        assert report.coverage == {}

    def test_full_construction(self):
        resource = ResourceCost(
            address="aws_s3_bucket.this",
            type="aws_s3_bucket",
            source_file="main.tf",
            cardinality=1,
            components=[_make_component()],
            monthly_cost=Decimal("2.30"),
            status=ComponentStatus.KNOWN,
        )
        assumption = Assumption(key="s3.storage_gb", value=Decimal("10"), unit="GB")
        report = CostReport(
            known_monthly_total=Decimal("2.30"),
            estimated_monthly_total=Decimal("2.30"),
            currency="USD",
            status=ReportStatus.COMPLETE,
            resources=[resource],
            assumptions=[assumption],
            unsupported_resources=["aws_sns_topic.alerts"],
            unknown_resources=["module.x.aws_ec2_instance.web"],
            catalog_errors=["aws_lambda_function.this"],
            unparsed_files=[{"file": "broken.tf", "error": "parse error"}],
            coverage={"analyzed": 1, "unsupported": 1},
        )
        assert report.known_monthly_total == Decimal("2.30")
        assert report.estimated_monthly_total == Decimal("2.30")
        assert report.currency == "USD"
        assert report.status is ReportStatus.COMPLETE
        assert report.resources == [resource]
        assert report.assumptions == [assumption]
        assert report.unsupported_resources == ["aws_sns_topic.alerts"]
        assert report.unknown_resources == ["module.x.aws_ec2_instance.web"]
        assert report.catalog_errors == ["aws_lambda_function.this"]
        assert report.unparsed_files == [{"file": "broken.tf", "error": "parse error"}]
        assert report.coverage == {"analyzed": 1, "unsupported": 1}

    @pytest.mark.parametrize(
        "field_name", ["known_monthly_total", "status", "coverage"]
    )
    def test_is_frozen(self, field_name):
        report = CostReport()
        with pytest.raises(FrozenInstanceError):
            setattr(report, field_name, "autre")
