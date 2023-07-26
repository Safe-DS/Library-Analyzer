from library_analyzer.processing.annotations._constants import autogen_author
from library_analyzer.processing.annotations.model import AnnotationStore, DependencyAnnotation, EnumReviewResult
from library_analyzer.processing.api import (
    ParameterHasValue,
    ParameterIsNone,
    ParametersInRelation,
    ParameterWillBeSetTo,
    extract_param_dependencies,
)
from library_analyzer.processing.api.model import API, Function, Parameter


def _search_for_parameter(name: str, parameter_list: list[Parameter], init_func: Function | None) -> str | None:
    """Search for the passed parameter name.

    The parameter name is searched in the list of function parameters.
    If the function should belong to a class, the parameters of the __init__ function are additionally examined.
    If no corresponding parameter is found, None is returned.

    Parameters
    ----------
    name
        Parameter name to be searched

    parameter_list
        Parameter list to be searched for the parameter to be found.

    init_func
        __init__ function to be additionally examined

    Returns
    -------
    str | None
        Paramter id of the found paramter

    """
    if init_func is not None:
        test_params = parameter_list + init_func.parameters
    else:
        test_params = parameter_list

    for param_ in test_params:
        if param_.name == name:
            return param_.id

    return None


def _add_dependency_parameter(param_id: str | None, target_list: list[str]) -> None:
    """Add the parameter to the passed list.

    Parameters
    ----------
    param_id
        Id of the parameter to be added.

    target_list
        The passed parameter ID will be added to this list.

    """
    if param_id is not None:
        target_list.append(param_id)


def _get_init_func(function_id: str, functions: dict[str, Function]) -> Function | None:
    """Find the __init_ function of the class.

    Parameters
    ----------
    function_id
        Function ID of the function that additionally requires the parameters
        of the __init__ function for the dependency analysis.

    functions
        Function list to be searched for the __init__ function to be found.

    Returns
    -------
    Function | None
        __init__ function of the class to which the function to be examined also belongs.

    """
    splitted = function_id.split("/")
    splitted[-1] = "__init__"
    new_id = "/".join(splitted)

    return functions.get(new_id, None)


def _generate_dependency_annotations(api: API, annotations: AnnotationStore) -> None:
    """Generate the dependency annotations for the found dependencies.

    Parameters
    ----------
    api
        API to be examined for dependencies

    annotations
        AnnotationStore to which all dependency annotations will be added.

    """
    init_func: Function | None

    functions = api.functions

    for func in functions.values():
        parameters = func.parameters

        for param in parameters:
            dependencies = extract_param_dependencies(param.qname, param.docstring.description)

            if dependencies:
                for _, condition, action in dependencies:
                    is_depending_on: list[str] = []
                    has_dependent_parameter: list[str] = []
                    init_func = _get_init_func(func.id, functions)

                    match condition:
                        case ParameterHasValue():
                            is_depending_on_param = _search_for_parameter(condition.dependee, parameters, init_func)

                            if is_depending_on_param is None and condition.check_dependee:
                                is_depending_on_param = _search_for_parameter(condition.value, parameters, init_func)

                            _add_dependency_parameter(is_depending_on_param, is_depending_on)

                        case ParameterIsNone():
                            is_depending_on_param = _search_for_parameter(condition.dependee, parameters, init_func)
                            _add_dependency_parameter(is_depending_on_param, is_depending_on)

                        case ParametersInRelation():
                            left_dependee = _search_for_parameter(condition.left_dependee, parameters, init_func)
                            right_dependee = _search_for_parameter(condition.right_dependee, parameters, init_func)

                            _add_dependency_parameter(left_dependee, is_depending_on)
                            _add_dependency_parameter(right_dependee, is_depending_on)

                        case ParameterWillBeSetTo():
                            depending_on_param = _search_for_parameter(condition.depender, parameters, init_func)
                            _add_dependency_parameter(depending_on_param, is_depending_on)

                        case _:
                            has_dependent_parameter_id = _search_for_parameter(
                                condition.dependee, parameters, init_func,
                            )

                            _add_dependency_parameter(has_dependent_parameter_id, has_dependent_parameter)

                    if is_depending_on or has_dependent_parameter:
                        annotations.add_annotation(
                            DependencyAnnotation(
                                target=param.id,
                                authors=[autogen_author],
                                reviewers=[],
                                comment=(
                                    f"I turned this in a dependency because the phrase '{condition.condition}' "
                                    "was found."
                                ),
                                reviewResult=EnumReviewResult.NONE,
                                is_depending_on=is_depending_on,
                                has_dependent_parameter=has_dependent_parameter,
                                condition=condition,
                                action=action,
                            ),
                        )
