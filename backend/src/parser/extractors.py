from typing import Any, Protocol

from .model import ModuleCall, ParsedTerraform, Resource
from .normalizer import normalize_block


class ExtractionContext:
    """Conteneur mutable passé aux extracteurs pour accumuler les résultats.

    `providers` contient deux formes de dict :
    - {"name": ..., ...} pour les blocs provider (ProviderExtractor)
    - {"required_providers": {...}} pour le bloc terraform (TerraformExtractor)
    """

    def __init__(
        self,
        module_path: tuple[str, ...] = (),
        source_file: str = "",
    ) -> None:
        self.module_path = module_path
        self.source_file = source_file
        self.resources: list[Resource] = []
        self.data_sources: list[Resource] = []
        self.module_calls: list[ModuleCall] = []
        self.variables: dict[str, Any] = {}
        self.outputs: dict[str, Any] = {}
        self.locals: dict[str, Any] = {}
        self.providers: list[dict[str, Any]] = []
        self.backend: dict[str, Any] | None = None
        self.other_blocks: dict[str, int] = {}

    def build_result(self) -> ParsedTerraform:
        return ParsedTerraform(
            resources=self.resources,
            data_sources=self.data_sources,
            module_calls=self.module_calls,
            variables=self.variables,
            outputs=self.outputs,
            locals=self.locals,
            providers=self.providers,
            backend=self.backend,
            other_blocks=self.other_blocks,
        )


class BlockExtractor(Protocol):
    """Interface des stratégies d'extraction."""

    def extract(self, blocks: list, ctx: ExtractionContext) -> None: ...


class ResourceExtractor:
    def extract(self, blocks: list, ctx: ExtractionContext) -> None:
        normalized = normalize_block(blocks)
        for rtype, rnames in normalized.items():
            if not isinstance(rnames, dict):
                continue
            for rname, rbody in rnames.items():
                rbody = rbody if isinstance(rbody, dict) else {}
                address = ".".join(ctx.module_path + (f"{rtype}.{rname}",))
                ctx.resources.append(
                    Resource(
                        address=address,
                        type=rtype,
                        name=rname,
                        module_path=ctx.module_path,
                        source_file=ctx.source_file,
                        count=rbody.get("count"),
                        for_each=rbody.get("for_each"),
                        # count/for_each sont des meta-arguments Terraform qui
                        # contrôlent le nombre d'instances créées. Ils sont
                        # extraits dans des champs dédiés (Resource.count,
                        # Resource.for_each) pour un accès direct en Phase 2
                        # (pricing : count=2 → coût ×2), et exclus de
                        # `arguments` pour éviter la duplication.
                        arguments={
                            k: v
                            for k, v in rbody.items()
                            if k not in ("count", "for_each")
                        },
                    )
                )


class DataExtractor:
    def extract(self, blocks: list, ctx: ExtractionContext) -> None:
        normalized = normalize_block(blocks)
        for dtype, dnames in normalized.items():
            if not isinstance(dnames, dict):
                continue
            for dname, dbody in dnames.items():
                dbody = dbody if isinstance(dbody, dict) else {}
                address = ".".join(ctx.module_path + (f"data.{dtype}.{dname}",))
                ctx.data_sources.append(
                    Resource(
                        address=address,
                        type=dtype,
                        name=dname,
                        module_path=ctx.module_path,
                        source_file=ctx.source_file,
                        count=dbody.get("count"),
                        for_each=dbody.get("for_each"),
                        arguments={
                            k: v
                            for k, v in dbody.items()
                            if k not in ("count", "for_each")
                        },
                    )
                )


class ModuleExtractor:
    def extract(self, blocks: list, ctx: ExtractionContext) -> None:
        normalized = normalize_block(blocks)
        for mname, mbody in normalized.items():
            if not isinstance(mbody, dict):
                continue
            address = ".".join(ctx.module_path + (f"module.{mname}",))
            ctx.module_calls.append(
                ModuleCall(
                    address=address,
                    source=mbody.get("source", ""),
                    arguments={
                        k: v
                        for k, v in mbody.items()
                        if k not in ("source", "count", "for_each")
                    },
                    count=mbody.get("count"),
                    for_each=mbody.get("for_each"),
                )
            )


class VariableExtractor:
    def extract(self, blocks: list, ctx: ExtractionContext) -> None:
        normalized = normalize_block(blocks)
        for vname, vbody in normalized.items():
            ctx.variables[vname] = vbody if isinstance(vbody, dict) else {}


class OutputExtractor:
    def extract(self, blocks: list, ctx: ExtractionContext) -> None:
        normalized = normalize_block(blocks)
        for oname, obody in normalized.items():
            ctx.outputs[oname] = obody if isinstance(obody, dict) else {}


class LocalsExtractor:
    def extract(self, blocks: list, ctx: ExtractionContext) -> None:
        normalized = normalize_block(blocks)
        ctx.locals.update(normalized)


class ProviderExtractor:
    def extract(self, blocks: list, ctx: ExtractionContext) -> None:
        # Contrairement aux autres extracteurs, on n'utilise PAS normalize_block() :
        # plusieurs blocs provider "aws" avec des alias différents sont valides en
        # Terraform, et normalize_block() les mergerait en écrasant les précédents.
        # On itère donc sur la liste brute pour conserver chaque provider.
        for item in blocks:
            if not isinstance(item, dict):
                continue
            for pname, pbody in item.items():
                entry = pbody if isinstance(pbody, dict) else {}
                entry["name"] = pname
                ctx.providers.append(entry)


class TerraformExtractor:
    def extract(self, blocks: list, ctx: ExtractionContext) -> None:
        normalized = normalize_block(blocks)
        for tname, tbody in normalized.items():
            # hcl2 représente les blocs imbriqués (backend, required_providers)
            # comme des LISTES de dicts : {'backend': [{'s3': {...}}]}.
            # normalize_block() n'aplatit pas ces listes (SRP : nettoyage pur,
            # pas d'interprétation de structure Terraform).
            if tname == "backend":
                # Terraform valide garantit un seul bloc backend par module :
                # la boucle ne tourne qu'une fois ; elle reste défensive.
                entries = tbody if isinstance(tbody, list) else [tbody]
                for item in entries:
                    if isinstance(item, dict):
                        for btype, bbody in item.items():
                            if isinstance(bbody, dict):
                                ctx.backend = dict(bbody)
                                ctx.backend["type"] = btype
            elif tname == "required_providers":
                entries = tbody if isinstance(tbody, list) else [tbody]
                for item in entries:
                    if isinstance(item, dict):
                        ctx.providers.append({"required_providers": dict(item)})
            else:
                ctx.other_blocks.setdefault("terraform", 0)
                ctx.other_blocks["terraform"] += 1


class DefaultExtractor:
    """Pour les blocs inconnus (moved, import, check...)."""

    def __init__(self, block_type: str) -> None:
        self.block_type = block_type

    def extract(self, blocks: list, ctx: ExtractionContext) -> None:
        ctx.other_blocks.setdefault(self.block_type, 0)
        ctx.other_blocks[self.block_type] += len(blocks)


# Registre global des stratégies
# Pour ajouter un nouveau type de bloc Terraform : créer une classe
# implémentant BlockExtractor et l'enregistrer ici.
REGISTRY: dict[str, BlockExtractor] = {
    "resource": ResourceExtractor(),
    "data": DataExtractor(),
    "module": ModuleExtractor(),
    "variable": VariableExtractor(),
    "output": OutputExtractor(),
    "locals": LocalsExtractor(),
    "provider": ProviderExtractor(),
    "terraform": TerraformExtractor(),
}


def extract_all(
    body: dict[str, Any],
    module_path: tuple[str, ...] = (),
    source_file: str = "",
) -> ParsedTerraform:
    """Extrait tous les blocs Terraform d'un body HCL2 nettoyé."""
    ctx = ExtractionContext(module_path=module_path, source_file=source_file)

    for block_type, block_list in body.items():
        if block_type.startswith("__"):
            # Marqueurs internes hcl2 (__comments__, __is_block__) : filtrés
            # en racine comme clean_value le fait déjà à l'intérieur des dicts.
            continue
        if not isinstance(block_list, list):
            continue
        extractor = REGISTRY.get(block_type)
        if extractor is not None:
            extractor.extract(block_list, ctx)
        else:
            DefaultExtractor(block_type).extract(block_list, ctx)

    return ctx.build_result()
