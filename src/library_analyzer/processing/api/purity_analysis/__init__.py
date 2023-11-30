"""Analyse the purity of a library's API."""

from ._get_module_data import (
    ModuleDataBuilder,
    calc_node_id,
    get_base_expression,
    get_module_data,
)
from ._infer_purity import (  # TODO: rework this
    # OpenMode,
    # PurityHandler,
    # determine_open_mode,
    # determine_purity,
    # extract_impurity_reasons,
    # generate_purity_information,
    # get_function_defs,
    # get_purity_result_str,
    # infer_purity,
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
    # "PurityHandler",
    # "OpenMode",
    # "determine_open_mode",
    # "determine_purity",
    # "extract_impurity_reasons",
    # "generate_purity_information",
    # "get_function_defs",
    # "get_purity_result_str",
    # "infer_purity",
    "infer_purity",
    "build_call_graph",
]
