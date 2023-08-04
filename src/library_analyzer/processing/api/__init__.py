"""Analysis of the API of a Python library."""

from ._get_api import get_api
from ._get_instance_attributes import get_instance_attributes
from ._get_parameter_list import get_parameter_list
from ._infer_purity import (
    DefinitelyImpure,
    DefinitelyPure,
    ImpurityIndicator,
    MaybeImpure,
    OpenMode,
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
)
from ._package_metadata import (
    distribution,
    distribution_version,
    package_files,
    package_root,
)
from ._resolve_references import (
    ClassScope,
    NodeID,
    MemberAccess,
    MemberAccessTarget,
    MemberAccessValue,
    ReferenceNode,
    Scope,
    Variables,
    resolve_references,
    _add_target_references,
    _calc_node_id,
    _create_references,
    _find_references,
    _get_name_nodes,
    _get_module_data,
)

__all__ = [
    "DefinitelyImpure",
    "DefinitelyPure",
    "ImpurityIndicator",
    "MaybeImpure",
    "OpenMode",
    "PurityInformation",
    "PurityResult",
    "calc_function_id",
    "determine_open_mode",
    "determine_purity",
    "distribution",
    "distribution_version",
    "extract_impurity_reasons",
    "generate_purity_information",
    "get_api",
    "get_function_defs",
    "get_instance_attributes",
    "get_parameter_list",
    "get_purity_result_str",
    "infer_purity",
    "package_files",
    "package_root",
    "ReferenceNode",
    "Scope",
    "MemberAccess",
    "MemberAccessTarget",
    "MemberAccessValue",
    "_find_references",
    "_get_name_nodes",
    "_create_references",
    "_add_target_references",
    "_calc_node_id",
    "_get_module_data",
    "Variables",
    "ClassScope",
    "NodeID",
    "resolve_references",
]
