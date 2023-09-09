from __future__ import annotations

import astroid
import builtins

from library_analyzer.processing.api._get_module_data import _get_module_data  # Todo: can we import from .api?
from library_analyzer.processing.api.model import (
    MemberAccessTarget,
    MemberAccessValue,
    NodeID,
    Symbol,
    Scope,
    ClassScope,
    Builtin,
    ReferenceNode,
)


def _create_unspecified_references(target_nodes: dict[astroid.AssignName | astroid.Name | MemberAccessTarget, Scope | ClassScope],
                                   value_nodes: dict[astroid.Name | MemberAccessValue, Scope | ClassScope],
                                   scope: Scope,
                                   classes: dict[str, ClassScope],
                                   functions: dict[str, Scope | list[Scope]]) -> list[ReferenceNode]:
    """Create a list of references from a list of name nodes.

    Returns:
        * final_references: contains all references that are used as targets
    """
    final_references: list[ReferenceNode] = []

    # TODO: is it possible to do this in a more efficient way?
    target_references = [ReferenceNode(node, scope, []) for node, scope in target_nodes.items()]
    value_references = [ReferenceNode(node, scope, []) for node, scope in value_nodes.items()]

    for value_ref in value_references:
        if isinstance(value_ref.node, astroid.Name | MemberAccessValue):
            target_ref = _find_references(value_ref, target_references, classes, functions)
            final_references.append(target_ref)

    return final_references


def _find_references(value_reference: ReferenceNode,
                     all_target_list: list[ReferenceNode],
                     classes: dict[str, ClassScope],
                     functions: dict[str, Scope | list[Scope]]) -> ReferenceNode:
    """ Find all references for a node.

    Finds all references for a node in a list of references and adds them to the list of referenced_symbols of the node.

    Parameters:
        * value_reference: the node for which we want to find all references
        * all_target_list: a list of target references in the module
        * classes: a list of all classes in the module
    """
    complete_reference = value_reference
    for ref in all_target_list:
        if ref.node.name == value_reference.node.name:
            complete_reference.referenced_symbols = list(set(complete_reference.referenced_symbols) | set(_get_symbols(ref)))
        if isinstance(value_reference.node, MemberAccessValue):
            # Add ClassVariables if the name matches
            if isinstance(ref.scope, ClassScope) and ref.node.name == value_reference.node.member.attrname:
                complete_reference.referenced_symbols = list(set(complete_reference.referenced_symbols) | set(_get_symbols(ref)))

            # Add InstanceVariables if the name of the MemberAccessValue is the same as the name of the InstanceVariable
            if isinstance(ref.node, MemberAccessTarget):
                if ref.node.member.attrname == value_reference.node.member.attrname:
                    complete_reference.referenced_symbols = list(set(complete_reference.referenced_symbols) | set(_get_symbols(ref)))

    if classes:
        for klass in classes.values():
            if klass.symbol.node.name == value_reference.node.name:
                complete_reference.referenced_symbols.append(klass.symbol)
                break

    # Find functions that are passed as arguments to other functions (and therefor are not called directly)
    if functions:
        if value_reference.node.name in functions.keys():
            func = functions.get(value_reference.node.name)
            complete_reference.referenced_symbols.append(func.symbol)
        elif isinstance(value_reference.node, MemberAccessValue):
            if value_reference.node.member.attrname in functions.keys():
                func = functions.get(value_reference.node.member.attrname)
                if isinstance(func, list):
                    for f in func:
                        # If the Lambda function is assigned to a name, it can be called just as a normal function
                        # Since Lambdas normally do not have names, we need to add its assigned name manually
                        if isinstance(f.symbol.node, astroid.Lambda):
                            f.symbol.name = value_reference.node.member.attrname
                        complete_reference.referenced_symbols.append(f.symbol)
                else:
                    complete_reference.referenced_symbols.append(func.symbol)

    return complete_reference


def _get_symbols(node: ReferenceNode) -> list[Symbol]:
    refined_symbol: list[Symbol] = []
    current_scope = node.scope

    for child in current_scope.children:
        if child.symbol.node.name == node.node.name:
            refined_symbol.append(child.symbol)

    return refined_symbol


def _find_call_reference_new(function_calls: dict[astroid.Call, Scope | ClassScope],
                             classes: dict[str, ClassScope],
                             functions: dict[str, Scope | ClassScope],
                             parameters: dict[astroid.FunctionDef, tuple[Scope | ClassScope, set[astroid.AssignName]]]) -> list[ReferenceNode]:
    final_call_references: list[ReferenceNode] = []
    python_builtins = dir(builtins)

    call_references = [ReferenceNode(call, scope, []) for call, scope in function_calls.items()]

    for i, reference in enumerate(call_references):
        if isinstance(reference.node.func, astroid.Name):
            # Find functions that are called
            if reference.node.func.name in functions.keys():
                symbol = functions.get(reference.node.func.name)

                # If the Lambda function is assigned to a name, it can be called just as a normal function
                # Since Lambdas normally do not have names, we need to add its assigned name manually
                if isinstance(functions.get(reference.node.func.name).symbol.node, astroid.Lambda):
                    symbol.symbol.name = reference.node.func.name

                call_references[i].referenced_symbols.append(symbol.symbol)
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

    Parameters:
        * code: the code of the module for which we want to resolve the references

    Returns:
        * resolved_references: a list of all resolved references in the module
    """

    module_data = _get_module_data(code)
    resolved_references = _create_unspecified_references(module_data.target_nodes, module_data.value_nodes, module_data.scope,
                                                         module_data.classes, module_data.functions)

    if module_data.function_calls:
        references_call = _find_call_reference_new(module_data.function_calls, module_data.classes, module_data.functions,
                                                   module_data.parameters)
        resolved_references.extend(references_call)

    return resolved_references
