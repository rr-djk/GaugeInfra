"""Contrat de normalizer.py : fonctions pures de nettoyage HCL2.

Formes encodées : labels quotés, marqueurs __is_block__/__comments__,
valeurs brutes (templates, littéraux quotés, bool, int), merge shallow.
"""

from backend.src.parser.normalizer import clean_value, normalize_block, strip_quotes


class TestStripQuotes:
    def test_strips_outer_quotes(self):
        assert strip_quotes('"aws_s3_bucket"') == "aws_s3_bucket"

    def test_idempotent(self):
        assert strip_quotes(strip_quotes('"x"')) == "x"

    def test_no_quotes_passthrough(self):
        assert strip_quotes("x") == "x"

    def test_non_string_passthrough(self):
        assert strip_quotes(42) == 42
        assert strip_quotes(True) is True
        assert strip_quotes(None) is None

    def test_only_outer_quotes_stripped(self):
        assert strip_quotes('"a"b"') == 'a"b'

    def test_single_quote_not_stripped(self):
        assert strip_quotes('"x') == '"x'
        assert strip_quotes('x"') == 'x"'


class TestCleanValue:
    def test_filters_internal_markers(self):
        value = {"__is_block__": True, "__comments__": [{"value": "x"}], "a": 1}
        assert clean_value(value) == {"a": 1}

    def test_strips_quotes_from_keys_and_values(self):
        value = {'"key"': '"value"'}
        assert clean_value(value) == {"key": "value"}

    def test_recursive_on_nested_dicts_and_lists(self):
        value = {
            '"outer"': {
                '"inner"': ['"a"', 2, True, None],
                "__is_block__": True,
            }
        }
        assert clean_value(value) == {"outer": {"inner": ["a", 2, True, None]}}

    def test_template_strings_kept_brut(self):
        assert clean_value("${var.x}") == "${var.x}"

    def test_scalars_passthrough(self):
        assert clean_value(2) == 2
        assert clean_value(True) is True
        assert clean_value(None) is None

    def test_required_providers_key_not_quoted_anyway(self):
        # La clé provider n'est pas quotée par hcl2 ; clean_value ne doit
        # pas la casser (strip_quotes est idempotent sur les non-quotés).
        value = {"aws": {"source": '"hashicorp/aws"'}}
        assert clean_value(value) == {"aws": {"source": "hashicorp/aws"}}


class TestNormalizeBlock:
    def test_merges_list_of_dicts_into_single_dict(self):
        blocks = [{"a": 1}, {"b": 2}]
        assert normalize_block(blocks) == {"a": 1, "b": 2}

    def test_shallow_merge_of_duplicate_dict_keys(self):
        blocks = [{"a": {"x": 1}}, {"a": {"y": 2}}]
        assert normalize_block(blocks) == {"a": {"x": 1, "y": 2}}

    def test_last_wins_for_non_dict_duplicates(self):
        blocks = [{"a": 1}, {"a": 2}]
        assert normalize_block(blocks) == {"a": 2}

    def test_skips_non_dict_items(self):
        blocks = [{"a": 1}, "pas-un-dict", None, 42]
        assert normalize_block(blocks) == {"a": 1}

    def test_cleans_values_through_clean_value(self):
        blocks = [{"__is_block__": True, '"k"': '"v"'}]
        assert normalize_block(blocks) == {"k": "v"}

    def test_empty_input(self):
        assert normalize_block([]) == {}
