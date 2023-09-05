"""Analysis of the API of a Python library."""

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
from ._resolve_references import (
    resolve_references,
    _add_target_references,
    _create_unspecified_references,
    _find_references,
)

from ._get_module_data import (
    ScopeFinder,
    _get_module_data,
    get_base_expression,
    _calc_node_id,
    _construct_member_access,
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
    "_find_references",
    "_create_unspecified_references",
    "_add_target_references",
    "_calc_node_id",
    "_get_module_data",
    "_construct_member_access",
    "resolve_references",
    "get_base_expression",
    "extract_called_after_functions",
    "CalledAfterValues",

]
