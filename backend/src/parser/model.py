from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Resource:
    address: str
    type: str
    name: str
    module_path: tuple[str, ...] = ()
    source_file: str = ""
    count: Any = None
    for_each: Any = None
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModuleCall:
    address: str
    source: str
    arguments: dict[str, Any] = field(default_factory=dict)
    count: Any = None
    for_each: Any = None


@dataclass(frozen=True)
class ParsedTerraform:
    resources: list[Resource] = field(default_factory=list)
    module_calls: list[ModuleCall] = field(default_factory=list)
    data_sources: list[Resource] = field(default_factory=list)
    variables: dict[str, dict[str, Any]] = field(default_factory=dict)
    outputs: dict[str, dict[str, Any]] = field(default_factory=dict)
    locals: dict[str, Any] = field(default_factory=dict)
    providers: list[dict[str, Any]] = field(default_factory=list)
    backend: dict[str, Any] | None = None
    unparsed_files: list[dict[str, Any]] = field(default_factory=list)
    other_blocks: dict[str, int] = field(default_factory=dict)
