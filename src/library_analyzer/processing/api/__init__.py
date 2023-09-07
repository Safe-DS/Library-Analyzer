"""Analysis of the API of a Python library."""


from library_analyzer.processing.api._extract_boundary_values import extract_boundary
from library_analyzer.processing.api._extract_valid_values import extract_valid_literals
from ._extract_called_after_functions import CalledAfterValues, extract_called_after_functions
from ._extract_dependencies import (
    Action,
    Condition,
    ParameterDoesNotHaveType,
    ParameterHasType,
    ParameterHasValue,
    ParameterIsIgnored,
    ParameterIsIllegal,
    ParameterIsNone,
    ParameterIsRestricted,
    ParametersInRelation,
    ParameterWillBeSetTo,
    extract_param_dependencies,
)
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
from ._resolve_references import ClassScopeNode, MemberAccess, ScopeNode, get_scope

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
    "extract_param_dependencies",
    "Action",
    "Condition",
    "ParameterHasValue",
    "ParameterIsIgnored",
    "ParameterIsNone",
    "ParameterDoesNotHaveType",
    "ParameterIsRestricted",
    "ParameterWillBeSetTo",
    "ParameterIsIllegal",
    "ParameterHasType",
    "ParametersInRelation",
    "ScopeNode",
    "MemberAccess",
    "get_scope",
    "ClassScopeNode",
    "extract_called_after_functions",
    "CalledAfterValues",
    "extract_boundary",
    "extract_valid_literals"
]
