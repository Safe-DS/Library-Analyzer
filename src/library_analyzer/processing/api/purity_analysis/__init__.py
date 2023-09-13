"""Analyse the purity of a library's API"""

from ._get_module_data import (
    get_module_data,
    calc_node_id,
    get_base_expression,
    ModuleDataBuilder,
)

from ._resolve_references import (
    resolve_references,
)

from ._infer_purity import (  # TODO: rework this
    FunctionID,
    PurityInformation,
    PurityResult,
    DefinitelyPure,
    MaybeImpure,
    DefinitelyImpure,
    PurityHandler,
    OpenMode,
    determine_open_mode,
    determine_purity,
    extract_impurity_reasons,
    generate_purity_information,
    get_function_defs,
    get_purity_result_str,
    infer_purity,
    calc_function_id,
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
    "calc_function_id",
]
