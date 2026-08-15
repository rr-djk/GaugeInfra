"""Contrat de extractors.py : Strategy Pattern, registre, dispatch.

Comportements figés (source = référence) :
- count/for_each exclus de `arguments`, stockés dans des champs dédiés ;
- ProviderExtractor ne merge pas (aliases multiples conservés) ;
- blocs inconnus (moved/import/check) comptés via DefaultExtractor ;
- TerraformExtractor : backend et required_providers extraits depuis la
  forme liste de hcl2 (blocs imbriqués), forme dict acceptée par défense.
"""

from backend.src.parser.extractors import (
    REGISTRY,
    DataExtractor,
    DefaultExtractor,
    ExtractionContext,
    LocalsExtractor,
    ModuleExtractor,
    OutputExtractor,
    ProviderExtractor,
    ResourceExtractor,
    TerraformExtractor,
    VariableExtractor,
    extract_all,
)
from backend.src.parser.model import ParsedTerraform, Resource


class TestRegistry:
    def test_registry_has_all_known_block_types(self):
        assert set(REGISTRY) == {
            "resource",
            "data",
            "module",
            "variable",
            "output",
            "locals",
            "provider",
            "terraform",
        }

    def test_registry_entries_are_extractors(self):
        # BlockExtractor est un Protocol non runtime_checkable : on vérifie
        # le contrat (méthode extract) plutôt que isinstance.
        for extractor in REGISTRY.values():
            assert callable(getattr(extractor, "extract", None))

    def test_registry_instances(self):
        assert isinstance(REGISTRY["resource"], ResourceExtractor)
        assert isinstance(REGISTRY["data"], DataExtractor)
        assert isinstance(REGISTRY["module"], ModuleExtractor)
        assert isinstance(REGISTRY["variable"], VariableExtractor)
        assert isinstance(REGISTRY["output"], OutputExtractor)
        assert isinstance(REGISTRY["locals"], LocalsExtractor)
        assert isinstance(REGISTRY["provider"], ProviderExtractor)
        assert isinstance(REGISTRY["terraform"], TerraformExtractor)


class TestExtractionContext:
    def test_defaults(self):
        ctx = ExtractionContext()
        assert ctx.module_path == ()
        assert ctx.source_file == ""
        assert ctx.resources == []
        assert ctx.data_sources == []
        assert ctx.module_calls == []
        assert ctx.variables == {}
        assert ctx.outputs == {}
        assert ctx.locals == {}
        assert ctx.providers == []
        assert ctx.backend is None
        assert ctx.other_blocks == {}

    def test_build_result_maps_all_fields(self):
        ctx = ExtractionContext(module_path=("module.a",), source_file="m.tf")
        ctx.resources.append(
            Resource(
                address="module.a.t.n",
                type="t",
                name="n",
                module_path=("module.a",),
                source_file="m.tf",
            )
        )
        result = ctx.build_result()
        assert isinstance(result, ParsedTerraform)
        assert result.resources[0].module_path == ("module.a",)
        assert result.resources[0].source_file == "m.tf"


class TestResourceExtractor:
    def test_extracts_resource_with_namespaced_address(self):
        ctx = ExtractionContext(module_path=("module.a",), source_file="m.tf")
        blocks = [{"aws_s3_bucket": {"this": {"bucket": "b"}}}]
        ResourceExtractor().extract(blocks, ctx)
        res = ctx.resources[0]
        assert res.address == "module.a.aws_s3_bucket.this"
        assert res.type == "aws_s3_bucket"
        assert res.name == "this"
        assert res.module_path == ("module.a",)
        assert res.source_file == "m.tf"
        assert res.arguments == {"bucket": "b"}

    def test_count_and_for_each_excluded_from_arguments(self):
        ctx = ExtractionContext()
        blocks = [
            {
                "aws_x": {
                    "a": {
                        "count": 2,
                        "for_each": "${toset(var.items)}",
                        "bucket": "b",
                    }
                }
            }
        ]
        ResourceExtractor().extract(blocks, ctx)
        res = ctx.resources[0]
        assert res.count == 2
        assert res.for_each == "${toset(var.items)}"
        assert res.arguments == {"bucket": "b"}

    def test_count_expression_kept_as_string(self):
        ctx = ExtractionContext()
        blocks = [{"aws_x": {"a": {"count": "${length(var.list)}"}}}]
        ResourceExtractor().extract(blocks, ctx)
        assert ctx.resources[0].count == "${length(var.list)}"

    def test_non_dict_body_becomes_empty_arguments(self):
        ctx = ExtractionContext()
        blocks = [{"aws_x": {"a": "pas-un-dict"}}]
        ResourceExtractor().extract(blocks, ctx)
        res = ctx.resources[0]
        assert res.arguments == {}
        assert res.count is None

    def test_multiple_resources_same_type(self):
        ctx = ExtractionContext()
        blocks = [{"aws_x": {"a": {"v": 1}, "b": {"v": 2}}}]
        ResourceExtractor().extract(blocks, ctx)
        assert [r.address for r in ctx.resources] == ["aws_x.a", "aws_x.b"]

    def test_non_dict_type_value_skipped(self):
        # Garde défensive : un type de ressource dont la valeur n'est pas un
        # dict (forme inattendue de normalize_block) est ignoré.
        ctx = ExtractionContext()
        blocks = [{"aws_x": "pas-un-dict"}]
        ResourceExtractor().extract(blocks, ctx)
        assert ctx.resources == []


class TestDataExtractor:
    def test_extracts_data_source_with_data_prefix(self):
        ctx = ExtractionContext(module_path=("module.a",))
        blocks = [{"aws_ami": {"ubuntu": {"most_recent": True}}}]
        DataExtractor().extract(blocks, ctx)
        ds = ctx.data_sources[0]
        assert ds.address == "module.a.data.aws_ami.ubuntu"
        assert ds.type == "aws_ami"
        assert ds.name == "ubuntu"
        assert ds.arguments == {"most_recent": True}

    def test_count_for_each_excluded(self):
        ctx = ExtractionContext()
        blocks = [{"aws_ami": {"u": {"count": 2, "for_each": "${var.x}", "a": 1}}}]
        DataExtractor().extract(blocks, ctx)
        ds = ctx.data_sources[0]
        assert ds.count == 2
        assert ds.for_each == "${var.x}"
        assert ds.arguments == {"a": 1}

    def test_non_dict_type_value_skipped(self):
        ctx = ExtractionContext()
        blocks = [{"aws_ami": "pas-un-dict"}]
        DataExtractor().extract(blocks, ctx)
        assert ctx.data_sources == []


class TestModuleExtractor:
    def test_extracts_module_call(self):
        ctx = ExtractionContext(module_path=("module.parent",))
        blocks = [{"vpc": {"source": "./vpc", "name": "n"}}]
        ModuleExtractor().extract(blocks, ctx)
        call = ctx.module_calls[0]
        assert call.address == "module.parent.module.vpc"
        assert call.source == "./vpc"
        assert call.arguments == {"name": "n"}

    def test_source_count_for_each_excluded_from_arguments(self):
        ctx = ExtractionContext()
        blocks = [{"vpc": {"source": "./vpc", "count": 3, "name": "n"}}]
        ModuleExtractor().extract(blocks, ctx)
        call = ctx.module_calls[0]
        assert call.source == "./vpc"
        assert call.count == 3
        assert call.arguments == {"name": "n"}

    def test_missing_source_defaults_to_empty_string(self):
        ctx = ExtractionContext()
        blocks = [{"vpc": {"name": "n"}}]
        ModuleExtractor().extract(blocks, ctx)
        assert ctx.module_calls[0].source == ""

    def test_non_dict_body_skipped(self):
        ctx = ExtractionContext()
        blocks = [{"vpc": "pas-un-dict"}]
        ModuleExtractor().extract(blocks, ctx)
        assert ctx.module_calls == []


class TestVariableOutputLocalsExtractors:
    def test_variable_extractor(self):
        ctx = ExtractionContext()
        blocks = [{"region": {"default": "us-east-1", "type": "string"}}]
        VariableExtractor().extract(blocks, ctx)
        assert ctx.variables == {"region": {"default": "us-east-1", "type": "string"}}

    def test_variable_non_dict_body_becomes_empty(self):
        ctx = ExtractionContext()
        blocks = [{"x": "pas-un-dict"}]
        VariableExtractor().extract(blocks, ctx)
        assert ctx.variables == {"x": {}}

    def test_output_extractor(self):
        ctx = ExtractionContext()
        blocks = [{"id": {"value": "${aws_x.a.id}"}}]
        OutputExtractor().extract(blocks, ctx)
        assert ctx.outputs == {"id": {"value": "${aws_x.a.id}"}}

    def test_output_non_dict_body_becomes_empty(self):
        ctx = ExtractionContext()
        blocks = [{"o": 42}]
        OutputExtractor().extract(blocks, ctx)
        assert ctx.outputs == {"o": {}}

    def test_locals_extractor_updates(self):
        ctx = ExtractionContext()
        blocks = [{"tags": {"Project": "gaugeinfra"}, "x": 1}]
        LocalsExtractor().extract(blocks, ctx)
        assert ctx.locals == {"tags": {"Project": "gaugeinfra"}, "x": 1}


class TestProviderExtractor:
    def test_keeps_multiple_aliases_without_merging(self):
        ctx = ExtractionContext()
        blocks = [
            {"aws": {"region": "us-east-1", "__is_block__": True}},
            {"aws": {"alias": "west", "region": "us-west-2", "__is_block__": True}},
        ]
        ProviderExtractor().extract(blocks, ctx)
        assert len(ctx.providers) == 2
        assert ctx.providers[0]["name"] == "aws"
        assert ctx.providers[1]["alias"] == "west"

    def test_skips_non_dict_items(self):
        ctx = ExtractionContext()
        ProviderExtractor().extract(["pas-un-dict", None], ctx)
        assert ctx.providers == []


class TestTerraformExtractor:
    def test_unknown_key_counted_in_other_blocks(self):
        ctx = ExtractionContext()
        blocks = [{"required_version": "1.15.8", "__is_block__": True}]
        TerraformExtractor().extract(blocks, ctx)
        assert ctx.other_blocks == {"terraform": 1}

    def test_backend_extracted(self):
        # hcl2 représente les blocs imbriqués en liste :
        # {'backend': [{'s3': {...}}]}. L'extracteur itère sur la liste et
        # extrait le type (label) + le corps en une passe.
        ctx = ExtractionContext()
        blocks = [
            {
                "backend": [
                    {"s3": {"bucket": "x", "use_lockfile": True, "__is_block__": True}}
                ],
                "__is_block__": True,
            }
        ]
        TerraformExtractor().extract(blocks, ctx)
        assert ctx.backend == {"bucket": "x", "use_lockfile": True, "type": "s3"}

    def test_backend_skipped_when_item_not_dict(self):
        # Garde défensive : un élément de liste non-dict (forme inattendue)
        # est ignoré sans erreur.
        ctx = ExtractionContext()
        blocks = [{"backend": ["pas-un-dict"]}]
        TerraformExtractor().extract(blocks, ctx)
        assert ctx.backend is None

    def test_backend_skipped_when_body_not_dict(self):
        # Garde défensive : un corps de backend non-dict (forme inattendue)
        # est ignoré sans erreur.
        ctx = ExtractionContext()
        blocks = [{"backend": [{"s3": "pas-un-dict"}]}]
        TerraformExtractor().extract(blocks, ctx)
        assert ctx.backend is None

    def test_required_providers_extracted(self):
        # Même forme liste que backend : {'required_providers': [{'aws': {...}}]}.
        ctx = ExtractionContext()
        blocks = [
            {
                "required_providers": [
                    {
                        "aws": {"source": "hashicorp/aws", "version": "6.58.0"},
                        "__is_block__": True,
                    }
                ],
                "__is_block__": True,
            }
        ]
        TerraformExtractor().extract(blocks, ctx)
        assert ctx.providers == [
            {
                "required_providers": {
                    "aws": {"source": "hashicorp/aws", "version": "6.58.0"}
                }
            }
        ]

    def test_backend_extracted_when_body_is_dict(self):
        # Forme dict (idéalisée) : acceptée par la garde défensive
        # `else [tbody]`, même si hcl2 produit toujours une liste.
        ctx = ExtractionContext()
        blocks = [{"backend": {"s3": {"bucket": "x", "use_lockfile": True}}}]
        TerraformExtractor().extract(blocks, ctx)
        assert ctx.backend == {"bucket": "x", "use_lockfile": True, "type": "s3"}

    def test_required_providers_extracted_when_body_is_dict(self):
        # Forme dict (idéalisée) : acceptée par la garde défensive
        # `else [tbody]`, même si hcl2 produit toujours une liste.
        ctx = ExtractionContext()
        blocks = [
            {
                "required_providers": {
                    "aws": {"source": "hashicorp/aws", "version": "6.58.0"}
                }
            }
        ]
        TerraformExtractor().extract(blocks, ctx)
        assert ctx.providers == [
            {
                "required_providers": {
                    "aws": {"source": "hashicorp/aws", "version": "6.58.0"}
                }
            }
        ]


class TestDefaultExtractor:
    def test_counts_blocks(self):
        ctx = ExtractionContext()
        DefaultExtractor("moved").extract([{"a": 1}, {"b": 2}], ctx)
        assert ctx.other_blocks == {"moved": 2}

    def test_accumulates_across_calls(self):
        ctx = ExtractionContext()
        DefaultExtractor("moved").extract([{"a": 1}], ctx)
        DefaultExtractor("moved").extract([{"b": 2}], ctx)
        assert ctx.other_blocks == {"moved": 2}


class TestExtractAll:
    def test_dispatch_known_blocks(self):
        body = {
            "resource": [{"aws_x": {"a": {"v": 1}}}],
            "data": [{"aws_ami": {"u": {}}}],
            "module": [{"vpc": {"source": "./vpc"}}],
            "variable": [{"x": {"default": 1}}],
            "output": [{"o": {"value": "v"}}],
            "locals": [{"l": 1}],
            "provider": [{"aws": {"region": "us-east-1"}}],
            "terraform": [{"required_version": "1.15.8"}],
        }
        result = extract_all(body)
        assert len(result.resources) == 1
        assert len(result.data_sources) == 1
        assert len(result.module_calls) == 1
        assert result.variables == {"x": {"default": 1}}
        assert result.outputs == {"o": {"value": "v"}}
        assert result.locals == {"l": 1}
        assert len(result.providers) == 1
        assert result.other_blocks == {"terraform": 1}

    def test_dispatch_unknown_block_to_default(self):
        body = {"moved": [{"from": "${aws_x.a}", "to": "${aws_x.b}"}]}
        result = extract_all(body)
        assert result.other_blocks == {"moved": 1}

    def test_skips_non_list_top_level_values(self):
        body = {"foo": 1, "resource": [{"aws_x": {"a": {}}}]}
        result = extract_all(body)
        assert len(result.resources) == 1
        assert result.other_blocks == {}

    def test_module_path_and_source_file_threaded(self):
        body = {"resource": [{"aws_x": {"a": {}}}]}
        result = extract_all(body, module_path=("module.m",), source_file="m.tf")
        assert result.resources[0].address == "module.m.aws_x.a"
        assert result.resources[0].source_file == "m.tf"

    def test_empty_body(self):
        result = extract_all({})
        assert isinstance(result, ParsedTerraform)
        assert result.resources == []
        assert result.other_blocks == {}
