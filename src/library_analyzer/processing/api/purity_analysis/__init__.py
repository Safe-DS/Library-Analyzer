"""Analyze the purity of a library's API."""

from ._get_module_data import (
    ModuleDataBuilder,
    calc_node_id,
    get_base_expression,
    get_module_data,
)
from ._infer_purity import (
    infer_purity,
)
from ._resolve_references import (
    resolve_references,
)

from ._build_call_graph import (
    build_call_graph,
)

__all__ = [
    "get_module_data",
    "calc_node_id",
    "get_base_expression",
    "ModuleDataBuilder",
    "resolve_references",
    "infer_purity",
    "build_call_graph",
]
