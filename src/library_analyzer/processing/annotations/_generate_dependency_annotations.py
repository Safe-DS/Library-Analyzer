from library_analyzer.processing.annotations._constants import autogen_author
from library_analyzer.processing.annotations.model import AnnotationStore, DependencyAnnotation, EnumReviewResult
from library_analyzer.processing.api import (
    Action,
    Condition,
    ParameterHasValue,
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
        Paramter id of the found paramter.
        If the name is not found in either list, None is returned.

    """
    for param in parameter_list:
        if param.name == name:
            return param.id

    if init_func is not None:
        for param in init_func.parameters:
            if param.name == name:
                return param.id

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
    if param_id is not None and (param_id not in target_list):
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
        If the __init__ function could not be found, None is returned.

    """
    splitted = function_id.split("/")
    splitted[-1] = "__init__"
    new_id = "/".join(splitted)

    return functions.get(new_id, None)


def _create_dependency_annotation(
    target: str,
    condition: Condition | None = None,
    action: Action | None = None,
    is_depending_on: list[str] | None = None,
    has_dependent_parameter: list[str] | None = None,
) -> DependencyAnnotation:
    """Create a dependency annotation with the passed parameters.

    Parameters
    ----------
    target
        Parameter_id of the parameter belonging to the annotation.

    condition
        condition of the dependency annotation

    action
        action of the dependency annotation

    is_depending_on
        Parameter_ids of the parameters on which the considered parameter depends

    has_dependent_parameter
        Parameter_ids of the parameters that depend on the parameter under consideration

    Returns
    -------
        DependencyAnnotation

    """
    if condition is None:
        cond = Condition()
        comment = ""
    else:
        cond = condition
        comment = f"I turned this in a dependency because the phrase '{condition.condition}' was found."

    act = action if action is not None else Action()
    has_dependent = has_dependent_parameter if has_dependent_parameter is not None else []
    is_depending = is_depending_on if is_depending_on is not None else []

    return DependencyAnnotation(
        target=target,
        authors=[autogen_author],
        reviewers=[],
        comment=comment,
        reviewResult=EnumReviewResult.NONE,
        is_depending_on=is_depending,
        has_dependent_parameter=has_dependent,
        condition=cond,
        action=act,
    )


def _add_properties_to_existing_dependency(
    target: str,
    annotations: AnnotationStore,
    cond: Condition | None = None,
    act: Action | None = None,
    is_depending_on: list[str] | None = None,
    param_id: str = "",
) -> None:
    """Add more properties to an existing dependency annotation.

    Parameters
    ----------
    target
        target the existing dependency annotation

    annotations
        AnnotationStore that contains the dependency annotations

    cond
        condition to be added to a parameter that so far only has dependencies to itself

    act
        action to be added to a parameter that so far only has dependencies to itself

    is_depending_on
        Contains parameter_ids that represent dependencies to other parameters

    """
    for annotation in annotations.dependencyAnnotations:
        if annotation.target == target:
            if is_depending_on is not None:
                annotation.is_depending_on = is_depending_on
                annotation.condition = cond if (cond is not None) else Condition()
                annotation.action = act if (act is not None) else Action()
                annotation.comment = (
                    f"I turned this in a dependency because the phrase '{annotation.condition.condition}' was found."
                )
                break
            else:
                if param_id not in annotation.has_dependent_parameter:
                    annotation.has_dependent_parameter.append(param_id)
                break


def _add_depending_on_dependencies(
    param_id: str,
    dependency_targets: list[str],
    is_depending_on: list[str],
    annotations: AnnotationStore,
) -> None:
    """Add the depending_on dependencies to the annotation store.

    Parameters
    ----------
    param_id
        Depender of the is_depending_on paramter

    dependency_targets
        List of dependency annotation targets that have already been created

    is_depending_on
        List of depending_on parameters for which a dependency is to be created

    annotations
        AnnotationStore, which contains the dependency annotations

    """
    for dependee_id in is_depending_on:
        if dependee_id not in dependency_targets:
            dependee_annotation = _create_dependency_annotation(
                target=dependee_id,
                has_dependent_parameter=[param_id],
            )
            annotations.add_annotation(dependee_annotation)
        else:
            _add_properties_to_existing_dependency(dependee_id, annotations, param_id=param_id)


def _generate_dependency_annotations(api: API, annotations: AnnotationStore) -> None:
    """Generate the dependency annotations for the found dependencies.

    Parameters
    ----------
    api
        API to be examined for dependencies

    annotations
        AnnotationStore to which all dependency annotations will be added

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

                            if (
                                is_depending_on_param is None or is_depending_on_param.lower() in ["if", "when"]
                            ) and condition.check_dependee:
                                is_depending_on_param = _search_for_parameter(condition.value, parameters, init_func)

                            _add_dependency_parameter(is_depending_on_param, is_depending_on)

                        case ParametersInRelation():
                            left_dependee = _search_for_parameter(condition.left_dependee, parameters, init_func)
                            right_dependee = _search_for_parameter(condition.right_dependee, parameters, init_func)

                            _add_dependency_parameter(left_dependee, is_depending_on)
                            _add_dependency_parameter(right_dependee, is_depending_on)

                        case _:
                            is_depending_on_param = _search_for_parameter(condition.dependee, parameters, init_func)
                            _add_dependency_parameter(is_depending_on_param, is_depending_on)

                    if condition.combined_with is not None:
                        for cond in condition.combined_with:
                            is_depending_on_param = _search_for_parameter(cond.dependee, parameters, init_func)
                            _add_dependency_parameter(is_depending_on_param, is_depending_on)

                    if isinstance(action, ParameterWillBeSetTo):
                        has_dependent_parameter_id = _search_for_parameter(action.depender, parameters, init_func)
                        _add_dependency_parameter(has_dependent_parameter_id, has_dependent_parameter)

                    dependency_targets = [annotation.target for annotation in annotations.dependencyAnnotations]

                    if is_depending_on or has_dependent_parameter:
                        if param.id not in dependency_targets:
                            annotation = _create_dependency_annotation(
                                target=param.id,
                                condition=condition,
                                action=action,
                                is_depending_on=is_depending_on,
                            )
                            annotations.add_annotation(annotation)
                            dependency_targets.append(param.id)

                            _add_depending_on_dependencies(param.id, dependency_targets, is_depending_on, annotations)

                        else:
                            _add_properties_to_existing_dependency(
                                param.id,
                                annotations,
                                condition,
                                action,
                                is_depending_on,
                            )
                            _add_depending_on_dependencies(param.id, dependency_targets, is_depending_on, annotations)
