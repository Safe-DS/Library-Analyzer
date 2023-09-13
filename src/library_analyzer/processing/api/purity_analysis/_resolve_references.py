from __future__ import annotations

import astroid
import builtins

from library_analyzer.processing.api.purity_analysis._get_module_data import get_module_data  # Todo: can we import from .api?
from library_analyzer.processing.api.purity_analysis.model import (
    MemberAccessTarget,
    MemberAccessValue,
    NodeID,
    Symbol,
    Scope,
    ClassScope,
    Builtin,
    ReferenceNode, Parameter,
)


def _find_name_references(
    target_nodes: dict[astroid.AssignName | astroid.Name | MemberAccessTarget, Scope | ClassScope],
    value_nodes: dict[astroid.Name | MemberAccessValue, Scope | ClassScope],
    classes: dict[str, ClassScope],
    functions: dict[str, list[Scope]],
    parameters: dict[astroid.FunctionDef, tuple[Scope | ClassScope, set[astroid.AssignName]]]) -> list[ReferenceNode]:
    """Create a list of references from a list of name nodes.

    Parameters:
        * target_nodes: a list of all target nodes in the module and their scope
        * value_nodes: a list of all value nodes in the module and their scope
        * classes: a list of all classes in the module and their scope
        * functions: a list of all functions in the module and their scope

    Returns:
        * final_references: contains all references that are used as targets
    """
    final_references: list[ReferenceNode] = []

    # TODO: is it possible to do this in a more efficient way?
    # maybe we can speed up the detection of references by using a dictionary instead of a list
    # -> target_references = {node.name: ReferenceNode(node, scope, []) for node, scope in target_nodes.items()}
    target_references = [ReferenceNode(node, scope, []) for node, scope in target_nodes.items()]
    value_references = [ReferenceNode(node, scope, []) for node, scope in value_nodes.items()]

    for value_ref in value_references:
        if isinstance(value_ref.node, astroid.Name | MemberAccessValue):
            target_ref = _find_references(value_ref, target_references, classes, functions, parameters)
            final_references.append(target_ref)
        # elif isinstance(value_ref.node, astroid.AssignName | MemberAccessTarget):
            # TODO: handle MemberAccessTarget/ AssignName
    return final_references


def _find_references(value_reference: ReferenceNode,
                     all_target_list: list[ReferenceNode],
                     classes: dict[str, ClassScope],
                     functions: dict[str, list[Scope]],
                     parameters: dict[astroid.FunctionDef, tuple[Scope | ClassScope, set[astroid.AssignName]]]) -> ReferenceNode:
    """ Find all references for a node.

    Finds all references for a node in a list of references and adds them to the list of referenced_symbols of the node.

    Parameters:
        * value_reference: the node for which we want to find all references
        * all_target_list: a list of target references in the module
        * classes: a dict of all classes in the module
        * functions: a dict of all functions in the module
        * parameters: a dict of all parameters for each functions in the module

    Returns:
        * complete_reference: the reference for the given node with all references added to its referenced_symbols
    """
    complete_reference = value_reference
    outer_continue: bool = False

    for ref in all_target_list:
        # Add all references (name)-nodes, that have the same name as the value_reference
        # and are not the receiver of a MemberAccess (because they are already added)
        if ref.node.name == value_reference.node.name and not isinstance(ref.node.parent, astroid.AssignAttr):
            # Add parameters only if the name parameter is declared in the same scope as the value_reference
            if ref.scope.symbol.node in parameters.keys():
                if not ref.scope == value_reference.scope:
                    continue

            # this covers the case where a parameter has the same name as a class variable:
            # class A:
            #     a = 0
            #     def f(self, a):
            #         self.a = a
            elif isinstance(ref.scope, ClassScope) and parameters:
                parameters_for_value_reference = parameters.get(value_reference.scope.symbol.node)[1]
                for param in parameters_for_value_reference:
                    if ref.node.name == param.name and not isinstance(_get_symbols(ref), Parameter):
                        outer_continue = True  # the reference isn't a parameter, so don't add it
                        break

                if outer_continue:
                    outer_continue = False
                    continue

            complete_reference.referenced_symbols = list(set(complete_reference.referenced_symbols) | set(_get_symbols(ref)))

        if isinstance(value_reference.node, MemberAccessValue):
            # Add ClassVariables if the name matches
            if isinstance(ref.scope, ClassScope) and ref.node.name == value_reference.node.member.attrname:
                complete_reference.referenced_symbols = list(
                    set(complete_reference.referenced_symbols) | set(_get_symbols(ref)))

            # Add InstanceVariables if the name of the MemberAccessValue is the same as the name of the InstanceVariable
            if isinstance(ref.node, MemberAccessTarget) and ref.node.member.attrname == value_reference.node.member.attrname:
                complete_reference.referenced_symbols = list(
                    set(complete_reference.referenced_symbols) | set(_get_symbols(ref)))

    # Find classes that are referenced
    if classes:
        for klass in classes.values():
            if klass.symbol.node.name == value_reference.node.name:
                complete_reference.referenced_symbols.append(klass.symbol)
                break

    # Find functions that are passed as arguments to other functions (and therefor are not called directly - hence we handle them here)
    # def f():
    #     pass
    # def g(a):
    #     a()
    # g(f)
    if functions:
        if value_reference.node.name in functions.keys():
            function_def = functions.get(value_reference.node.name)
            symbols = [func.symbol for func in function_def]
            complete_reference.referenced_symbols.extend(symbols)
        elif isinstance(value_reference.node, MemberAccessValue):
            if value_reference.node.member.attrname in functions.keys():
                function_def = functions.get(value_reference.node.member.attrname)
                symbols = [func.symbol for func in function_def]
                complete_reference.referenced_symbols.extend(symbols)

    return complete_reference


def _get_symbols(node: ReferenceNode) -> list[Symbol]:
    """Get all symbols for a node.

    Parameters:
        * node: the node for which we want to get all symbols

    Returns:
        * refined_symbol: a list of all symbols for the given node
    """

    refined_symbol: list[Symbol] = []
    current_scope = node.scope

    for child in current_scope.children:
        if isinstance(child.symbol.node, astroid.ListComp):
            continue
        elif child.symbol.node.name == node.node.name:
            refined_symbol.append(child.symbol)

    return refined_symbol


def _find_call_reference(function_calls: dict[astroid.Call, Scope | ClassScope],
                         classes: dict[str, ClassScope],
                         functions: dict[str, list[Scope]],
                         parameters: dict[astroid.FunctionDef, tuple[Scope | ClassScope, set[astroid.AssignName]]]) -> list[ReferenceNode]:
    """Find all references for a function call.

    Parameters:
        * function_calls: a dict of all function calls in the module and their scope
        * classes: a dict of all classes in the module and their scope
        * functions: a dict of all functions in the module and their scope
        * parameters: a dict of all parameters of functions in the module and their scope

    Returns:
        * final_call_references: a list of all references for a function call
    """

    final_call_references: list[ReferenceNode] = []
    python_builtins = dir(builtins)

    call_references = [ReferenceNode(call, scope, []) for call, scope in function_calls.items()]

    for i, reference in enumerate(call_references):
        if isinstance(reference.node.func, astroid.Name):
            # Find functions that are called
            if reference.node.func.name in functions.keys():
                function_def = functions.get(reference.node.func.name)
                symbols = [func.symbol for func in function_def]
                call_references[i].referenced_symbols.extend(symbols)

                final_call_references.append(call_references[i])

            # Find classes that are called (initialized)
            elif reference.node.func.name in classes.keys():
                symbol = classes.get(reference.node.func.name)
                call_references[i].referenced_symbols.append(symbol.symbol)

                final_call_references.append(call_references[i])

            # Find builtins that are called
            if reference.node.func.name in python_builtins:
                builtin_call = Builtin(reference.scope, NodeID("builtins", reference.node.func.name, 0, 0),
                                       reference.node.func.name)
                call_references[i].referenced_symbols.append(builtin_call)
                final_call_references.append(call_references[i])

            # Find function parameters that are called (passed as arguments), like:
            # def f(a):
            #     a()
            # For now: it is not possible to analyse this any further before runtime
            if parameters:
                for func_def, (scope, parameter_set) in parameters.items():
                    for param in parameter_set:
                        if reference.node.func.name == param.name and reference.scope.symbol.node == func_def:
                            for child in parameters.get(func_def)[0].children:
                                if child.symbol.node.name == param.name:
                                    call_references[i].referenced_symbols.append(child.symbol)
                                    final_call_references.append(call_references[i])
                                    break

    return final_call_references


def resolve_references(code: str) -> list[ReferenceNode]:
    """
    Resolve all references in a module.

    This function is the entry point for the reference resolving.
    It calls all other functions that are needed to resolve the references.
    First we get the module data for the given (module) code.
    Then we call the functions to find all references in the module.

    Parameters:
        * code: the code of the module for which we want to resolve the references

    Returns:
        * resolved_references: a list of all resolved references in the module
    """

    module_data = get_module_data(code)
    resolved_references = _find_name_references(module_data.target_nodes, module_data.value_nodes,
                                                module_data.classes, module_data.functions, module_data.parameters)

    if module_data.function_calls:
        references_call = _find_call_reference(module_data.function_calls, module_data.classes, module_data.functions,
                                               module_data.parameters)
        resolved_references.extend(references_call)

    return resolved_references