from __future__ import annotations

import builtins

import astroid

from library_analyzer.processing.api.purity_analysis import get_module_data
from library_analyzer.processing.api.purity_analysis._build_call_graph import build_call_graph
from library_analyzer.processing.api.purity_analysis.model import (
    Builtin,
    CallGraphForest,
    ClassScope,
    ClassVariable,
    FunctionScope,
    MemberAccessTarget,
    MemberAccessValue,
    NodeID,
    Parameter,
    Reasons,
    ReferenceNode,
    Scope,
    Symbol,
)


def _find_name_references(
    target_nodes: dict[astroid.AssignName | astroid.Name | MemberAccessTarget, Scope | ClassScope],
    value_nodes: dict[astroid.Name | MemberAccessValue, Scope | ClassScope],
    classes: dict[str, ClassScope],
    functions: dict[str, list[FunctionScope]],
    parameters: dict[astroid.FunctionDef, tuple[Scope | ClassScope, set[astroid.AssignName]]],
) -> dict[str, list[ReferenceNode]]:
    """Create a list of references from a list of name nodes.

    Parameters
    ----------
    target_nodes : dict[astroid.AssignName | astroid.Name | MemberAccessTarget, Scope | ClassScope]
        All target nodes and their Scope or ClassScope.
    value_nodes : dict[astroid.Name | MemberAccessValue, Scope | ClassScope]
        All value nodes and their Scope or ClassScope.
    classes : dict[str, ClassScope]
        All classes and their ClassScope.
    functions : dict[str, list[FunctionScope]]
        All functions and a list of their FunctionScopes.
        The value is a list since there can be multiple functions with the same name.
    parameters : dict[astroid.FunctionDef, tuple[Scope | ClassScope, set[astroid.AssignName]]]
        All parameters of functions and a tuple of their Scope or ClassScope and a set of their target nodes.

    Returns
    -------
    final_references : dict[str, list[ReferenceNode]]
        All target and value references and a list of their ReferenceNodes.
    """
    final_references: dict[str, list[ReferenceNode]] = {}

    # TODO: is it possible to do this in a more efficient way?
    # maybe we can speed up the detection of references by using a dictionary instead of a list
    # -> target_references = {node.name: ReferenceNode(node, scope, []) for node, scope in target_nodes.items()}
    target_references = [ReferenceNode(node, scope, []) for node, scope in target_nodes.items()]
    value_references = [ReferenceNode(node, scope, []) for node, scope in value_nodes.items()]

    # Detect all value references: references that are used as values (e.g., sth = value, return value)
    for value_ref in value_references:
        if isinstance(value_ref.node, astroid.Name | MemberAccessValue):
            value_ref_complete = _find_value_references(value_ref, target_references, classes, functions, parameters)
            if value_ref_complete.node.name in final_references:
                if value_ref_complete.node.name in final_references:
                final_references[value_ref_complete.node.name].append(value_ref_complete)
            else:
                final_references[value_ref_complete.node.name] = [value_ref_complete]

    # Detect all target references: references that are used as targets (e.g., target = sth)
    for target_ref in target_references:
        if isinstance(target_ref.node, astroid.AssignName | astroid.Name | MemberAccessTarget):
            target_ref_complete = _find_target_references(target_ref, target_references, classes)
            # Remove all references that are never referenced
            if target_ref_complete.referenced_symbols:
                if target_ref_complete.node.name in final_references:
                    final_references[target_ref_complete.node.name].append(target_ref_complete)
                else:
                    final_references[target_ref_complete.node.name] = [target_ref_complete]

    return final_references


def _find_target_references(
    current_target_reference: ReferenceNode,
    all_target_list: list[ReferenceNode],
    classes: dict[str, ClassScope],
) -> ReferenceNode:
    """Find all references for a target node.

    Finds all references for a target node in a list of references and adds them to the list of referenced_symbols of the node.
    We only want to find references that are used as targets before the current target reference,
    because all later references are not relevant for the current target reference.

    Parameters
    ----------
    current_target_reference : ReferenceNode
        The current target reference, for which we want to find all references.
    all_target_list : list[ReferenceNode]
        All target references in the module.
    classes : dict[str, ClassScope]
        All classes and their ClassScope.

    Returns
    -------
    current_target_reference : ReferenceNode
        The reference for the given node with all its target references added to its referenced_symbols.
    """
    if current_target_reference in all_target_list:
        all_targets_before_current_target_reference = all_target_list[: all_target_list.index(current_target_reference)]
        result: list[Symbol] = []
        for ref in all_targets_before_current_target_reference:
            if isinstance(current_target_reference.node, MemberAccessTarget):
                # Add ClassVariables if the name matches.
                if isinstance(ref.scope, ClassScope) and ref.node.name == current_target_reference.node.member.attrname:
                    result.extend(_get_symbols(ref))
                    # This deals with the special case where the self-keyword is used.
                    # Self indicates that we are inside a class and therefore only want to check the class itself for references.
                    if result and current_target_reference.node.receiver.name == "self":
                        result = [symbol for symbol in result if isinstance(symbol, ClassVariable) and symbol.klass == current_target_reference.scope.parent.symbol.node]  # type: ignore[union-attr] # "None" has no attribute "symbol" but since we check for the type before, this is fine

                # Add InstanceVariables if the name of the MemberAccessTarget is the same as the name of the InstanceVariable.
                if (
                    isinstance(ref.node, MemberAccessTarget)
                    and ref.node.member.attrname == current_target_reference.node.member.attrname
                ):
                    result.extend(_get_symbols(ref))

            # This deals with the receivers of the MemberAccess, e.g.: self.sth -> self
            # When dealing with this case of receivers we only want to check the current scope because they are bound to the current scope, which is their class.
            elif (
                isinstance(current_target_reference.node, astroid.Name)
                and ref.node.name == current_target_reference.node.name
                and ref.scope == current_target_reference.scope
            ):
                result.extend(_get_symbols(ref))

            # This deals with the case where a variable is reassigned.
            elif (
                isinstance(current_target_reference.node, astroid.AssignName)
                and ref.node.name == current_target_reference.node.name
                and not isinstance(current_target_reference.scope.symbol.node, astroid.Lambda)
                and not isinstance(current_target_reference.scope, ClassScope)
            ):
                symbol_list = _get_symbols(ref)
                all_targets_before_current_target_reference_nodes = [
                    node.node for node in all_targets_before_current_target_reference
                ]

                if symbol_list:
                    for symbol in symbol_list:
                        if symbol.node in all_targets_before_current_target_reference_nodes:
                            result.append(symbol)

            if classes:
                for klass in classes.values():
                    if klass.symbol.node.name == current_target_reference.node.name:
                        result.append(klass.symbol)
                        break

        current_target_reference.referenced_symbols = list(
            set(current_target_reference.referenced_symbols) | set(result),
        )

    return current_target_reference


def _find_value_references(
    current_value_reference: ReferenceNode,
    all_target_list: list[ReferenceNode],
    classes: dict[str, ClassScope],
    functions: dict[str, list[FunctionScope]],
    parameters: dict[astroid.FunctionDef, tuple[Scope | ClassScope, set[astroid.AssignName]]],
) -> ReferenceNode:
    """Find all references for a value node.

    Finds all references for a node in a list of references and adds them to the list of referenced_symbols of the node.

    Parameters
    ----------
    current_value_reference : ReferenceNode
        The current value reference, for which we want to find all references.
    all_target_list : list[ReferenceNode]
        All target references in the module.
    classes : dict[str, ClassScope]
        All classes and their ClassScope.
    functions : dict[str, list[FunctionScope]]
        All functions and a list of their FunctionScopes.
        The value is a list since there can be multiple functions with the same name.
    parameters : dict[astroid.FunctionDef, tuple[Scope | ClassScope, set[astroid.AssignName]]]
        All parameters of functions and a tuple of their Scope or ClassScope and a set of their target nodes.

    Returns
    -------
    complete_reference : ReferenceNode
        The reference for the given node with all its value references added to its referenced_symbols.
    """
    complete_reference = current_value_reference
    outer_continue: bool = False

    for ref in all_target_list:
        # Add all references (name)-nodes, that have the same name as the value_reference
        # and are not the receiver of a MemberAccess (because they are already added)
        if ref.node.name == current_value_reference.node.name and not isinstance(ref.node.parent, astroid.AssignAttr):
            # Add parameters only if the name parameter is declared in the same scope as the value_reference
            if ref.scope.symbol.node in parameters and ref.scope != current_value_reference.scope:
                continue

            # This covers the case where a parameter has the same name as a class variable:
            # class A:
            #     a = 0
            #     def f(self, a):
            #         self.a = a
            elif isinstance(ref.scope, ClassScope) and parameters:
                parameters_for_value_reference = parameters.get(current_value_reference.scope.symbol.node)[1]  # type: ignore[index] # "None" is not index-able, but we check for it
                for param in parameters_for_value_reference:
                    if ref.node.name == param.name and not isinstance(_get_symbols(ref), Parameter):
                        outer_continue = True  # the reference isn't a parameter, so don't add it
                        break

                if outer_continue:
                    outer_continue = False
                    continue

            complete_reference.referenced_symbols = list(
                set(complete_reference.referenced_symbols) | set(_get_symbols(ref)),
            )

        if isinstance(current_value_reference.node, MemberAccessValue):
            # Add ClassVariables if the name matches
            if isinstance(ref.scope, ClassScope) and ref.node.name == current_value_reference.node.member.attrname:
                complete_reference.referenced_symbols = list(
                    set(complete_reference.referenced_symbols) | set(_get_symbols(ref)),
                )

            # Add InstanceVariables if the name of the MemberAccessValue is the same as the name of the InstanceVariable
            if (
                isinstance(ref.node, MemberAccessTarget)
                and ref.node.member.attrname == current_value_reference.node.member.attrname
            ):
                complete_reference.referenced_symbols = list(
                    set(complete_reference.referenced_symbols) | set(_get_symbols(ref)),
                )

    # Find classes that are referenced
    if classes:
        for klass in classes.values():
            if klass.symbol.node.name == current_value_reference.node.name:
                complete_reference.referenced_symbols.append(klass.symbol)
                break

    # Find functions that are passed as arguments to other functions (and therefor are not called directly - hence we handle them here)
    # def f():
    #     pass
    # def g(a):
    #     a()
    # g(f)
    if functions:
        if current_value_reference.node.name in functions:
            function_def = functions.get(current_value_reference.node.name)
            symbols = [func.symbol for func in function_def if function_def]  # type: ignore[union-attr] # "None" is not iterable, but we check for it
            complete_reference.referenced_symbols.extend(symbols)
        elif isinstance(current_value_reference.node, MemberAccessValue):
            if current_value_reference.node.member.attrname in functions:
                function_def = functions.get(current_value_reference.node.member.attrname)
                symbols = [func.symbol for func in function_def if function_def]  # type: ignore[union-attr] # "None" is not iterable, but we check for it
                complete_reference.referenced_symbols.extend(symbols)

    return complete_reference


# TODO: move this to Symbol as a getter method
def _get_symbols(node: ReferenceNode) -> list[Symbol]:
    """Get all symbols for a node.

    Parameters
    ----------
    node : ReferenceNode
        The node for which we want to get all symbols.

    Returns
    -------
    refined_symbol : list[Symbol]
        All symbols for the given node.
    """
    refined_symbol: list[Symbol] = []
    current_scope = node.scope

    for child in current_scope.children:
        # This excludes ListComps, because they are not referenced
        if isinstance(child.symbol.node, astroid.ListComp):
            continue
        elif child.symbol.node.name == node.node.name:
            refined_symbol.append(child.symbol)

    return refined_symbol


def _find_call_references(
    function_calls: dict[astroid.Call, Scope | ClassScope],
    classes: dict[str, ClassScope],
    functions: dict[str, list[FunctionScope]],
    parameters: dict[astroid.FunctionDef, tuple[Scope | ClassScope, set[astroid.AssignName]]],
) -> dict[str, list[ReferenceNode]]:
    """Find all references for a function call.

    Parameters
    ----------
    function_calls : dict[astroid.Call, Scope | ClassScope]
        All function calls and their Scope or ClassScope.
    classes : dict[str, ClassScope]
        All classes and their ClassScope.
    functions : dict[str, list[FunctionScope]]
        All functions and a list of their FunctionScopes.
        The value is a list since there can be multiple functions with the same name.
    parameters : dict[astroid.FunctionDef, tuple[Scope | ClassScope, set[astroid.AssignName]]]
        All parameters of functions and a tuple of their Scope or ClassScope and a set of their target nodes.

    Returns
    -------
    final_call_references : dict[str, list[ReferenceNode]]
        All references for a function call.
    """

    def add_reference() -> None:
        """Add a reference to the final_call_references dict."""
        if call_references[i].node.func.name in final_call_references:
            final_call_references[call_references[i].node.func.name].append(call_references[i])
        else:
            final_call_references[call_references[i].node.func.name] = [call_references[i]]

    final_call_references: dict[str, list[ReferenceNode]] = {}
    python_builtins = dir(builtins)

    call_references = [ReferenceNode(call, scope, []) for call, scope in function_calls.items()]

    for i, reference in enumerate(call_references):
        # Find functions that are called
        if isinstance(reference.node.func, astroid.Name) and reference.node.func.name in functions:
            function_def = functions.get(reference.node.func.name)
            symbols = [func.symbol for func in function_def if function_def]  # type: ignore[union-attr] # "None" is not iterable, but we check for it
            call_references[i].referenced_symbols.extend(symbols)
            add_reference()

        # Find classes that are called (initialized)
        elif reference.node.func.name in classes:
            symbol = classes.get(reference.node.func.name)
            if symbol:
                call_references[i].referenced_symbols.append(symbol.symbol)
            add_reference()

        # Find builtins that are called
        if reference.node.func.name in python_builtins:
            builtin_call = Builtin(
                reference.node,
                NodeID("builtins", reference.node.func.name, 0, 0),
                reference.node.func.name,
            )
            call_references[i].referenced_symbols.append(builtin_call)
            add_reference()

        # Find function parameters that are called (passed as arguments), like:
        # def f(a):
        #     a()
        # For now: it is not possible to analyze this any further before runtime
        if parameters:
            for func_def, (_scope, parameter_set) in parameters.items():
                for param in parameter_set:
                    if reference.node.func.name == param.name and reference.scope.symbol.node == func_def:
                        for child in parameters.get(func_def)[0].children:  # type: ignore[index] # "None" is not index-able, but we check for it
                            if child.symbol.node.name == param.name:
                                call_references[i].referenced_symbols.append(child.symbol)
                                add_reference()
                                break

    return final_call_references


def resolve_references(
    code: str,
) -> tuple[dict[str, list[ReferenceNode]], dict[str, Reasons], dict[str, ClassScope], CallGraphForest]:
    # TODO: add a class for this return type then fix the docstring
    """
    Resolve all references in a module.

    This function is the entry point for the reference resolving.
    It calls all other functions that are needed to resolve the references.
    First, we get the module data for the given (module) code.
    Then we call the functions to find all references in the module.

    Returns
    -------
        * resolved_references: a dict of all resolved references in the module
        * function_references: a dict of all function references in the module and their Reasons object
        * classes: a dict of all classes in the module and their scope
        * call_graph: a CallGraphForest object that represents the call graph of the module
    """
    module_data = get_module_data(code)
    name_references = _find_name_references(
        module_data.target_nodes,
        module_data.value_nodes,
        module_data.classes,
        module_data.functions,
        module_data.parameters,
    )

    if module_data.function_calls:
        call_references = _find_call_references(
            module_data.function_calls,
            module_data.classes,
            module_data.functions,
            module_data.parameters,
        )
    else:
        call_references = {}

    resolved_references = merge_dicts(call_references, name_references)

    call_graph = build_call_graph(module_data.functions, module_data.function_references)

    return resolved_references, module_data.function_references, module_data.classes, call_graph


def merge_dicts(
    d1: dict[str, list[ReferenceNode]],
    d2: dict[str, list[ReferenceNode]],
) -> dict[str, list[ReferenceNode]]:
    """Merge two dicts of lists of ReferenceNodes.

    Parameters
    ----------
    d1 : dict[str, list[ReferenceNode]]
        The first dict.
    d2 : dict[str, list[ReferenceNode]]
        The second dict.

    Returns
    -------
    d3 : dict[str, list[ReferenceNode]]
        The merged dict.
    """
    d3 = d1.copy()
    for key, value in d2.items():
        if key in d3:
            d3[key].extend(value)
        else:
            d3[key] = value
    return d3
