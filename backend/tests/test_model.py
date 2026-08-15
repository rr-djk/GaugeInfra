"""Contrat des dataclasses du modèle : frozen, champs requis, factories."""

from dataclasses import FrozenInstanceError

import pytest

from backend.src.parser.model import ModuleCall, ParsedTerraform, Resource


def test_resource_required_fields():
    res = Resource(address="aws_s3_bucket.this", type="aws_s3_bucket", name="this")
    assert res.address == "aws_s3_bucket.this"
    assert res.type == "aws_s3_bucket"
    assert res.name == "this"


def test_resource_defaults():
    res = Resource(address="a", type="t", name="n")
    assert res.module_path == ()
    assert res.source_file == ""
    assert res.count is None
    assert res.for_each is None
    assert res.arguments == {}


def test_resource_is_frozen():
    res = Resource(address="a", type="t", name="n")
    with pytest.raises(FrozenInstanceError):
        res.address = "autre"  # type: ignore[misc]


def test_module_call_required_fields_and_defaults():
    call = ModuleCall(address="module.vpc", source="terraform-aws-modules/vpc/aws")
    assert call.arguments == {}
    assert call.count is None
    assert call.for_each is None


def test_module_call_is_frozen():
    call = ModuleCall(address="module.vpc", source="./vpc")
    with pytest.raises(FrozenInstanceError):
        call.source = "./autre"  # type: ignore[misc]


def test_parsed_terraform_defaults():
    parsed = ParsedTerraform()
    assert parsed.resources == []
    assert parsed.module_calls == []
    assert parsed.data_sources == []
    assert parsed.variables == {}
    assert parsed.outputs == {}
    assert parsed.locals == {}
    assert parsed.providers == []
    assert parsed.backend is None
    assert parsed.unparsed_files == []
    assert parsed.other_blocks == {}


def test_parsed_terraform_is_frozen():
    parsed = ParsedTerraform()
    with pytest.raises(FrozenInstanceError):
        parsed.resources = [Resource(address="a", type="t", name="n")]  # type: ignore[misc]


def test_parsed_terraform_accepts_all_fields():
    res = Resource(address="a", type="t", name="n")
    parsed = ParsedTerraform(
        resources=[res],
        module_calls=[ModuleCall(address="module.m", source="./m")],
        data_sources=[res],
        variables={"x": {"default": 1}},
        outputs={"o": {"value": "v"}},
        locals={"l": 1},
        providers=[{"name": "aws"}],
        backend={"type": "s3", "bucket": "b"},
        unparsed_files=[{"file": "f.tf", "error": "e"}],
        other_blocks={"moved": 1},
    )
    assert parsed.backend == {"type": "s3", "bucket": "b"}
    assert parsed.other_blocks == {"moved": 1}
