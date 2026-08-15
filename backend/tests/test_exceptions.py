"""Contrat de TerraformParseError : une Exception standard, levable et
attrapable comme telle par les appelants."""

import pytest

from backend.src.parser.exceptions import TerraformParseError


def test_terraform_parse_error_is_exception():
    assert issubclass(TerraformParseError, Exception)


def test_terraform_parse_error_can_be_raised_and_caught():
    with pytest.raises(TerraformParseError, match="fichier.tf: boom"):
        raise TerraformParseError("fichier.tf: boom")


def test_terraform_parse_error_chains_cause():
    cause = ValueError("cause racine")
    with pytest.raises(TerraformParseError) as exc_info:
        raise TerraformParseError("fichier.tf: échec") from cause
    assert exc_info.value.__cause__ is cause
