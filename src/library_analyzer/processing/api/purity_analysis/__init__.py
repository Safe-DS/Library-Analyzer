"""Analyse the purity of a library's API."""

from ._get_module_data import (
    ModuleDataBuilder,
    calc_node_id,
    get_base_expression,
    get_module_data,
)
from ._infer_purity import (  # TODO: rework this
    DefinitelyImpure,
    DefinitelyPure,
    FunctionID,
    MaybeImpure,
    OpenMode,
    PurityHandler,
    PurityInformation,
    PurityResult,
    calc_function_id,
    determine_open_mode,
    determine_purity,
    extract_impurity_reasons,
    generate_purity_information,
    get_function_defs,
    get_purity_result_str,
    infer_purity,
    infer_purity_new,
)
from ._resolve_references import (
    resolve_references,
)

__all__ = [
    "get_module_data",
    "calc_node_id",
    "get_base_expression",
    "ModuleDataBuilder",
    "resolve_references",
    "FunctionID",
    "PurityInformation",
    "PurityResult",
    "DefinitelyPure",
    "MaybeImpure",
    "DefinitelyImpure",
    "PurityHandler",
    "OpenMode",
    "determine_open_mode",
    "determine_purity",
    "extract_impurity_reasons",
    "generate_purity_information",
    "get_function_defs",
    "get_purity_result_str",
    "infer_purity",
    "infer_purity_new",
    "calc_function_id",
]
