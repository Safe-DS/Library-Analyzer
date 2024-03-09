"""Analyze the purity of a library's API."""

from ._build_call_graph import (
    build_call_graph,
)
from ._get_module_data import (
    get_module_data,
)
from ._infer_purity import (
    get_purity_results,
    infer_purity,
)
from ._resolve_references import (
    resolve_references,
)

__all__ = [
    "get_module_data",
    "resolve_references",
    "infer_purity",
    "build_call_graph",
    "get_purity_results"
]
