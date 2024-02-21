from __future__ import annotations

import builtins

import astroid

from library_analyzer.processing.api.purity_analysis import calc_node_id, get_module_data
from library_analyzer.processing.api.purity_analysis._build_call_graph import build_call_graph
from library_analyzer.processing.api.purity_analysis.model import (
    Builtin,
    ClassScope,
    ClassVariable,
    FunctionScope,
    InstanceVariable,
    MemberAccess,
    MemberAccessTarget,
    MemberAccessValue,
    ModuleAnalysisResult,
    ModuleData,
    NodeID,
    Reasons,
    Reference,
    ReferenceNode,
    Symbol,
    TargetReference,
    ValueReference,
)

_BUILTINS = dir(builtins)


# def _find_name_references(
#     target_nodes: dict[astroid.AssignName | astroid.Name | MemberAccessTarget, Scope | ClassScope],
#     value_nodes: dict[astroid.Name | MemberAccessValue, Scope | ClassScope],
#     classes: dict[str, ClassScope],
#     functions: dict[str, list[FunctionScope]],
#     parameters: dict[astroid.FunctionDef, tuple[Scope | ClassScope, list[astroid.AssignName]]],
#     global_variables: dict[str, Scope | ClassScope | FunctionScope]
# ) -> dict[str, list[ReferenceNode]]:
#     """Create a list of references from a list of name nodes.
#
#     Parameters
#     ----------
#     target_nodes : dict[astroid.AssignName | astroid.Name | MemberAccessTarget, Scope | ClassScope]
#         All target nodes and their Scope or ClassScope.
#     value_nodes : dict[astroid.Name | MemberAccessValue, Scope | ClassScope]
#         All value nodes and their Scope or ClassScope.
#     classes : dict[str, ClassScope]
#         All classes and their ClassScope.
#     functions : dict[str, list[FunctionScope]]
#         All functions and a list of their FunctionScopes.
#         The value is a list since there can be multiple functions with the same name.
#     parameters : dict[astroid.FunctionDef, tuple[Scope | ClassScope, list[astroid.AssignName]]]
#         All parameters of functions and a tuple of their Scope or ClassScope and a list of their target nodes.
#     global_variables : dict[str, Scope | ClassScope | FunctionScope]
#         All global variables and their Scope or ClassScope.
#
#     Returns
#     -------
#     final_references : dict[str, list[ReferenceNode]]
#         All target and value references and a list of their ReferenceNodes.
#     """
#     final_references: dict[str, list[ReferenceNode]] = {}
#
#     # TODO: is it possible to do this in a more efficient way?  maybe remove all target references that are locals
#     # maybe we can speed up the detection of references by using a dictionary instead of a list
#     # -> target_references = {node.name: ReferenceNode(node, scope, []) for node, scope in target_nodes.items()}
#     target_references = [TargetReference(node, scope, []) for node, scope in target_nodes.items()]
#     value_references = [ValueReference(node, scope, []) for node, scope in value_nodes.items()]
#
#     # TODO: this can possibly run on multiple threads and therefore boost the performance
#     # Detect all value references: references that are used as values (e.g., sth = value, return value)
#     for value_ref in value_references:
#         if isinstance(value_ref.node, astroid.Name | MemberAccessValue):
#             value_ref_complete = _find_value_references(value_ref, target_references, classes, functions, parameters, global_variables)
#             if value_ref_complete.node.name in final_references:
#                 final_references[value_ref_complete.node.name].append(value_ref_complete)
#             else:
#                 final_references[value_ref_complete.node.name] = [value_ref_complete]
#
#     # Detect all target references: references that are used as targets (e.g., target = sth)
#     for target_ref in target_references:
#         if isinstance(target_ref.node, astroid.AssignName | astroid.Name | MemberAccessTarget):
#             target_ref_complete = _find_target_references(target_ref, target_references, classes)
#             # Remove all references that are never referenced
#             if target_ref_complete.referenced_symbols:
#                 if target_ref_complete.node.name in final_references:
#                     final_references[target_ref_complete.node.name].append(target_ref_complete)
#                 else:
#                     final_references[target_ref_complete.node.name] = [target_ref_complete]
#
#     return final_references


# # TODO: this function has a sideeffect, it changes the current_target_reference.referenced_symbols instead of returning them
# def _find_target_references(
#     current_target_reference: ReferenceNode,
#     all_target_list: list[ReferenceNode],
#     classes: dict[str, ClassScope],
# ) -> ReferenceNode:
#     """Find all references for a target node.
#
#     Finds all references for a target node in a list of references and adds them to the list of referenced_symbols of the node.
#     We only want to find references that are used as targets before the current target reference,
#     because all later references are not relevant for the current target reference.
#
#     Parameters
#     ----------
#     current_target_reference : ReferenceNode
#         The current target reference, for which we want to find all references.
#     all_target_list : list[ReferenceNode]
#         All target references in the module.
#     classes : dict[str, ClassScope]
#         All classes and their ClassScope.
#
#     Returns
#     -------
#     current_target_reference : ReferenceNode
#         The reference for the given node with all its target references added to its referenced_symbols.
#     """
#     if current_target_reference in all_target_list:
#         # TODO: this can be more efficient if we filter out all targets that do not have the same name as the current_target_reference
#         all_targets_before_current_target_reference = all_target_list[: all_target_list.index(current_target_reference)]
#         if not all_targets_before_current_target_reference:
#             return current_target_reference
#         result: list[Symbol] = []
#         for ref in all_targets_before_current_target_reference:
#             if isinstance(current_target_reference.node, MemberAccessTarget):
#                 # Add ClassVariables if the name matches.
#                 if isinstance(ref.scope, ClassScope) and ref.node.name == current_target_reference.node.member.attrname:
#                     result.extend(_get_symbols(ref))
#                     # This deals with the special case where the self-keyword is used.
#                     # Self indicates that we are inside a class and therefore only want to check the class itself for references.
#                     if result and current_target_reference.node.receiver.name == "self":
#                         result = [symbol for symbol in result if isinstance(symbol, ClassVariable) and symbol.klass == current_target_reference.scope.parent.symbol.node]  # type: ignore[union-attr] # "None" has no attribute "symbol" but since we check for the type before, this is fine
#
#                 # Add InstanceVariables if the name of the MemberAccessTarget is the same as the name of the InstanceVariable.
#                 if (
#                     isinstance(ref.node, MemberAccessTarget)
#                     and ref.node.member.attrname == current_target_reference.node.member.attrname
#                 ):
#                     result.extend(_get_symbols(ref))
#
#             # This deals with the receivers of the MemberAccess, e.g.: self.sth -> self
#             # When dealing with this case of receivers we only want to check the current scope because they are bound to the current scope, which is their class.
#             elif (
#                 isinstance(current_target_reference.node, astroid.Name)
#                 and ref.node.name == current_target_reference.node.name
#                 and ref.scope == current_target_reference.scope
#             ):
#                 result.extend(_get_symbols(ref))
#
#             # This deals with the case where a variable is reassigned.
#             elif (
#                 isinstance(current_target_reference.node, astroid.AssignName)
#                 and ref.node.name == current_target_reference.node.name  # check if the name of the target matches
#                 and not isinstance(current_target_reference.scope, ClassScope)  # check we deal with a function scope
#                 and (ref.scope == current_target_reference.scope or ref.node.name in current_target_reference.scope.globals_used)  # check if the scope of the target matches
#             ):
#                 symbol_list = _get_symbols(ref)
#                 all_targets_before_current_target_reference_nodes = [
#                     node.node for node in all_targets_before_current_target_reference
#                 ]
#
#                 if symbol_list:
#                     for symbol in symbol_list:
#                         if symbol.node in all_targets_before_current_target_reference_nodes:
#                             result.append(symbol)
#
#             if classes:
#                 for klass in classes.values():
#                     if klass.symbol.node.name == current_target_reference.node.name:
#                         result.append(klass.symbol)
#                         break
#
#         current_target_reference.referenced_symbols = list(
#             set(current_target_reference.referenced_symbols) | set(result),
#         )
#
#     return current_target_reference


# # TODO: this function has a sideeffect, it changes the current_target_reference.referenced_symbols instead of returning them
# def _find_value_references(
#     current_value_reference: ReferenceNode,
#     all_target_list: list[ReferenceNode],
#     classes: dict[str, ClassScope],
#     functions: dict[str, list[FunctionScope]],
#     parameters: dict[astroid.FunctionDef, tuple[Scope | ClassScope, list[astroid.AssignName]]],
#     global_variables: dict[str, Scope | ClassScope | FunctionScope]
# ) -> ReferenceNode:
#     """Find all references for a value node.
#
#     Finds all references for a node in a list of references and adds them to the list of referenced_symbols of the node.
#
#     Parameters
#     ----------
#     current_value_reference : ReferenceNode
#         The current value reference, for which we want to find all references.
#     all_target_list : list[ReferenceNode]
#         All target references in the module.
#     classes : dict[str, ClassScope]
#         All classes and their ClassScope.
#     functions : dict[str, list[FunctionScope]]
#         All functions and a list of their FunctionScopes.
#         The value is a list since there can be multiple functions with the same name.
#     parameters : dict[astroid.FunctionDef, tuple[Scope | ClassScope, list[astroid.AssignName]]]
#         All parameters of functions and a tuple of their Scope or ClassScope and a list of their target nodes.
#     global_variables : dict[str, Scope | ClassScope | FunctionScope]
#         All global variables and their Scope or ClassScope.
#
#     Returns
#     -------
#     complete_reference : ReferenceNode
#         The reference for the given node with all its value references added to its referenced_symbols.
#     """
#     complete_reference = current_value_reference
#     outer_continue: bool = False
#
#     for ref in all_target_list:
#         # Add all references (name)-nodes, that have the same name as the value_reference
#         # and are not the receiver of a MemberAccess (because they are already added)
#         if ref.node.name == current_value_reference.node.name and not isinstance(ref.node.parent, astroid.AssignAttr):
#             # Add parameters only if the name parameter is declared in the same scope as the value_reference
#             if ref.scope.symbol.node in parameters and ref.scope != current_value_reference.scope:
#                 continue
#
#             # This covers the case where a parameter has the same name as a class variable:
#             # class A:
#             #     a = 0
#             #     def f(self, a):
#             #         self.a = a
#             elif isinstance(ref.scope, ClassScope) and parameters:
#                 parameters_for_value_reference = parameters.get(current_value_reference.scope.symbol.node)[1]  # type: ignore[index] # "None" is not index-able, but we check for it
#                 for param in parameters_for_value_reference:
#                     if ref.node.name == param.name and not isinstance(_get_symbols(ref), Parameter):
#                         outer_continue = True  # the reference isn't a parameter, so don't add it
#                         break
#
#                 if outer_continue:
#                     outer_continue = False
#                     continue
#
#             # Only add a reference if it is declared in the same scope as the value_reference or if it is a global variable
#             if current_value_reference.scope == ref.scope or ref.node.name in global_variables:
#                 complete_reference.referenced_symbols = list(
#                     set(complete_reference.referenced_symbols) | set(_get_symbols(ref)),
#                 )
#
#         if isinstance(current_value_reference.node, MemberAccessValue):
#             # Add ClassVariables if the name matches
#             if isinstance(ref.scope, ClassScope) and ref.node.name == current_value_reference.node.member.attrname:
#                 complete_reference.referenced_symbols = list(
#                     set(complete_reference.referenced_symbols) | set(_get_symbols(ref)),
#                 )
#
#             # Add InstanceVariables if the name of the MemberAccessValue is the same as the name of the InstanceVariable
#             if (
#                 isinstance(ref.node, MemberAccessTarget)
#                 and ref.node.member.attrname == current_value_reference.node.member.attrname
#             ):
#                 complete_reference.referenced_symbols = list(
#                     set(complete_reference.referenced_symbols) | set(_get_symbols(ref)),
#                 )
#
#     # Find classes that are referenced
#     if classes:
#         for klass in classes.values():
#             if klass.symbol.node.name == current_value_reference.node.name:
#                 complete_reference.referenced_symbols.append(klass.symbol)
#                 break
#
#     # Find functions that are passed as arguments to other functions (and therefor are not called directly - hence we handle them here)
#     # def f():
#     #     pass
#     # def g(a):
#     #     a()
#     # g(f)
#     if functions:
#         if current_value_reference.node.name in functions:
#             function_def = functions.get(current_value_reference.node.name)
#             symbols = [func.symbol for func in function_def if function_def]  # type: ignore[union-attr] # "None" is not iterable, but we check for it
#             complete_reference.referenced_symbols.extend(symbols)
#         elif isinstance(current_value_reference.node, MemberAccessValue):
#             if current_value_reference.node.member.attrname in functions:
#                 function_def = functions.get(current_value_reference.node.member.attrname)
#                 symbols = [func.symbol for func in function_def if function_def]  # type: ignore[union-attr] # "None" is not iterable, but we check for it
#                 complete_reference.referenced_symbols.extend(symbols)
#
#     return complete_reference


# # TODO: move this to Symbol as a getter method
# def _get_symbols(node: ReferenceNode) -> list[Symbol]:
#     """Get all symbols for a node.
#
#     Parameters
#     ----------
#     node : ReferenceNode
#         The node for which we want to get all symbols.
#
#     Returns
#     -------
#     refined_symbol : list[Symbol]
#         All symbols for the given node.
#     """
#     refined_symbol: list[Symbol] = []
#     current_scope = node.scope
#
#     for child in current_scope.children:
#         # This excludes ListComps, because they are not referenced
#         if isinstance(child.symbol.node, astroid.ListComp):
#             continue
#         elif child.symbol.node.name == node.node.name:
#             refined_symbol.append(child.symbol)
#
#     return refined_symbol


# def _find_call_references(
#     function_calls: dict[astroid.Call, Scope | ClassScope],
#     classes: dict[str, ClassScope],
#     functions: dict[str, list[FunctionScope]],
#     parameters: dict[astroid.FunctionDef, tuple[Scope | ClassScope, list[astroid.AssignName]]],
# ) -> dict[str, list[ReferenceNode]]:
#     """Find all references for a function call.
#
#     Parameters
#     ----------
#     function_calls : dict[astroid.Call, Scope | ClassScope]
#         All function calls and their Scope or ClassScope.
#     classes : dict[str, ClassScope]
#         All classes and their ClassScope.
#     functions : dict[str, list[FunctionScope]]
#         All functions and a list of their FunctionScopes.
#         The value is a list since there can be multiple functions with the same name.
#     parameters : dict[astroid.FunctionDef, tuple[Scope | ClassScope, list[astroid.AssignName]]]
#         All parameters of functions and a tuple of their Scope or ClassScope and a list of their target nodes.
#
#     Returns
#     -------
#     final_call_references : dict[str, list[ReferenceNode]]
#         All references for a function call.
#     """
#
#     def add_reference() -> None:
#         """Add a reference to the final_call_references dict."""
#         if call_references[i].node.func.name in final_call_references:
#             final_call_references[call_references[i].node.func.name].append(call_references[i])
#         else:
#             final_call_references[call_references[i].node.func.name] = [call_references[i]]
#
#     final_call_references: dict[str, list[ReferenceNode]] = {}
#     python_builtins = dir(builtins)
#
#     call_references = [ReferenceNode(call, scope, []) for call, scope in function_calls.items()]
#
#     for i, reference in enumerate(call_references):
#         # make sure we do not get an AttributeError because of the inconsistent names in the astroid API
#         if isinstance(reference.node.func, astroid.Attribute):
#             reference_node_name = reference.node.func.attrname
#         else:
#             reference_node_name = reference.node.func.name
#
#         # Find functions that are called
#         if isinstance(reference.node.func, astroid.Name) and reference_node_name in functions:
#             function_def = functions.get(reference_node_name)
#             symbols = [func.symbol for func in function_def if function_def]  # type: ignore[union-attr] # "None" is not iterable, but we check for it
#             call_references[i].referenced_symbols.extend(symbols)
#             add_reference()
#
#         # Find classes that are called (initialized)
#         elif reference_node_name in classes:
#             symbol = classes.get(reference_node_name)
#             if symbol:
#                 call_references[i].referenced_symbols.append(symbol.symbol)
#             add_reference()
#
#         # Find builtins that are called
#         if reference_node_name in python_builtins:
#             builtin_call = Builtin(
#                 reference.node,
#                 NodeID("builtins", reference_node_name, 0, 0),
#                 reference_node_name,
#             )
#             call_references[i].referenced_symbols.append(builtin_call)
#             add_reference()
#
#         # Find function parameters that are called (passed as arguments), like:
#         # def f(a):
#         #     a()
#         # For now: it is not possible to analyze this any further before runtime
#         if parameters:
#             for func_def, (_scope, parameter_set) in parameters.items():
#                 for param in parameter_set:
#                     if reference_node_name == param.name and reference.scope.symbol.node == func_def:
#                         for child in parameters.get(func_def)[0].children:  # type: ignore[index] # "None" is not index-able, but we check for it
#                             if child.symbol.node.name == param.name:
#                                 call_references[i].referenced_symbols.append(child.symbol)
#                                 add_reference()
#                                 break
#
#     return final_call_references


def _find_call_references_single_call(call_reference: Reference,
                                      function: FunctionScope,
                                      functions: dict[str, list[FunctionScope]],
                                      classes: dict[str, ClassScope]) -> ValueReference:
    """Find all references for a function call.

    This function finds all referenced Symbols for a call reference.
    A reference for a call node can be either a FunctionDef or a ClassDef node.
    We also analyze builtins calls and calls of function parameters.

    Parameters
    ----------
    call_reference : Reference
        The call reference we want to analyze.
    function : FunctionScope
        The function in which the call is made.
    functions : dict[str, list[FunctionScope]]
        A dictionary of all functions and a list of their FunctionScopes.
        Since there can be multiple functions with the same name, the value is a list.
    classes : dict[str, ClassScope]
        A dictionary of all classes and their ClassScopes.

    Returns
    -------
    ValueReference
        A ValueReference for the given call reference.
        This contains all referenced symbols for the call reference.
    """
    if not isinstance(call_reference, Reference):
        raise TypeError(f"call is not of type Reference, but of type {type(call_reference)}")

    value_reference = ValueReference(call_reference, function, [])

    # Find functions that are called.
    if call_reference.name in functions:
        function_def = functions.get(call_reference.name)
        function_symbols = [func.symbol for func in function_def if function_def]  # type: ignore[union-attr] # "None" is not iterable, but we check for it
        value_reference.referenced_symbols.extend(function_symbols)

    # Find classes that are called (initialized).
    elif call_reference.name in classes:
        class_def = classes.get(call_reference.name)
        value_reference.referenced_symbols.append(class_def.symbol)

    # Find builtins that are called, this includes open-like functions.
    if call_reference.name in _BUILTINS or call_reference.name in ("open", "read", "readline", "readlines", "write", "writelines", "close"):
        builtin_call = Builtin(
            call_reference.node,
            NodeID("builtins", call_reference.name, 0, 0),
            call_reference.name,
        )
        value_reference.referenced_symbols.append(builtin_call)

    # Find function parameters that are called (passed as arguments), like:
    # def f(a):
    #     a()
    # It is not possible to analyze this any further before runtime, so they will later be marked as unknown.
    if call_reference.name in function.parameters:
        param = function.parameters[call_reference.name]
        value_reference.referenced_symbols.append(param)

    return value_reference


def _find_value_references_new(value_reference: Reference,
                               function: FunctionScope,
                               functions: dict[str, list[FunctionScope]],
                               classes: dict[str, ClassScope]) -> ValueReference:
    """Find all references for a value node.

    This functions finds all referenced Symbols for a value reference.
    A reference for a value node can be a GlobalVariable, a LocalVariable,
    a Parameter, a ClassVariable or an InstanceVariable.
    It Also deals with the case where a class or a function is used as a value.

    Parameters
    ----------
    value_reference : Reference
        The value reference we want to analyze.
    function : FunctionScope
        The function in which the value is used.
    functions : dict[str, list[FunctionScope]]
        A dictionary of all functions and a list of their FunctionScopes.
        Since there can be multiple functions with the same name, the value is a list.
    classes : dict[str, ClassScope]
        A dictionary of all classes and their ClassScopes.

    Returns
    -------
    ValueReference
        A ValueReference for the given value reference.
        This contains all referenced symbols for the value reference.
    """
    if not isinstance(value_reference, Reference):
        raise TypeError(f"call is not of type Reference, but of type {type(value_reference)}")

    result_value_reference = ValueReference(value_reference, function, [])

    # Find local variables that are referenced.
    if value_reference.name in function.target_symbols and value_reference.name not in function.parameters:
        symbols = function.target_symbols[value_reference.name]
        # Check if all symbols are refined
        if any(isinstance(symbol, Symbol) for symbol in symbols):
            # This currently is mostly the case for ClassVariables and InstanceVariables that atr used as targets
            missing_refined = [symbol for symbol in symbols if type(symbol) is Symbol]
            for symbol in missing_refined:
                # TODO: this will not work when more than one class has the same class variable name
                if isinstance(symbol.node, MemberAccessTarget):
                    for klass in classes.values():
                        if klass.class_variables:
                            if value_reference.node.member.attrname in klass.class_variables:
                                result_value_reference.referenced_symbols.append(ClassVariable(symbol.node, symbol.id, symbol.node.member.attrname, klass.symbol.node))
                        if klass.instance_variables:
                            if value_reference.node.member.attrname in klass.instance_variables:
                                result_value_reference.referenced_symbols.append(InstanceVariable(symbol.node, symbol.id, symbol.node.member.attrname, klass.symbol.node))

            symbols = list(set(symbols) - set(missing_refined))

        result_value_reference.referenced_symbols.extend(symbols)

    # Find parameters that are referenced.
    if value_reference.name in function.parameters:
        symbols = [function.parameters[value_reference.name]]
        result_value_reference.referenced_symbols.extend(symbols)

    # Find global variables that are referenced.
    if value_reference.name in function.globals_used:
        symbols = function.globals_used[value_reference.name]
        result_value_reference.referenced_symbols.extend(symbols)

    # Find functions that are referenced (as value).
    if value_reference.name in functions:
        function_def = functions.get(value_reference.name)
        function_symbols = [func.symbol for func in function_def if function_def]
        result_value_reference.referenced_symbols.extend(function_symbols)

    # Find classes that are referenced (as value).
    if value_reference.name in classes:
        class_def = classes.get(value_reference.name)
        result_value_reference.referenced_symbols.append(class_def.symbol)

    # Find class and instance variables that are referenced.
    if isinstance(value_reference.node, MemberAccessValue):
        for klass in classes.values():
            if klass.class_variables:
                if value_reference.node.member.attrname in klass.class_variables and value_reference.node.member.attrname not in function.call_references:
                    result_value_reference.referenced_symbols.extend(klass.class_variables[value_reference.node.member.attrname])
            if klass.instance_variables:
                if value_reference.node.member.attrname in klass.instance_variables and value_reference.node.member.attrname not in function.call_references:
                    result_value_reference.referenced_symbols.extend(klass.instance_variables[value_reference.node.member.attrname])

    return result_value_reference


def _find_target_references_new(target_reference: Symbol,
                                function: FunctionScope,
                                classes: dict[str, ClassScope]) -> TargetReference:
    """Find all references for a target node.

    This functions finds all referenced Symbols for a target reference.
    TargetReferences occur whenever a Symbol is reassigned.
    A reference for a target node can be a GlobalVariable, a LocalVariable, a ClassVariable or an InstanceVariable.
    It Also deals with the case where a class is used as a target.

    Parameters
    ----------
    target_reference : Symbol
        The target reference we want to analyze.
    function : FunctionScope
        The function in which the value is used.
    classes : dict[str, ClassScope]
        A dictionary of all classes and their ClassScopes.

    Returns
    -------
    TargetReference
        A TargetReference for the given target reference.
        This contains all referenced symbols for the value reference.
    """
    if not isinstance(target_reference, Symbol):
        raise TypeError(f"call is not of type Reference, but of type {type(target_reference)}")

    result_target_reference = TargetReference(target_reference, function, [])

    # Find local variables that are referenced.
    if target_reference.name in function.target_symbols:
        symbols = function.target_symbols[target_reference.name][: function.target_symbols[target_reference.name].index(target_reference)]
        result_target_reference.referenced_symbols.extend(symbols)

    # Find global variables that are referenced.
    if target_reference.name in function.globals_used:
        symbols = function.globals_used[target_reference.name]
        result_target_reference.referenced_symbols.extend(symbols)

    # Find classes that are referenced (as value).
    if target_reference.name in classes:
        class_def = classes.get(target_reference.name)
        result_target_reference.referenced_symbols.append(class_def.symbol)

    # Find class and instance variables that are referenced.
    if isinstance(target_reference.node, MemberAccessTarget):
        for klass in classes.values():
            if klass.class_variables:
                if target_reference.node.member.attrname in klass.class_variables:
                    # Do not add class variables from other classes
                    if (function.symbol.name == "__init__" and function.parent != klass
                        or target_reference.node.receiver.name == "self" and function.parent !=klass
                    ):
                        continue
                    result_target_reference.referenced_symbols.extend(
                        klass.class_variables[target_reference.node.member.attrname])
            if klass.instance_variables:
                if (target_reference.node.member.attrname in klass.instance_variables
                    and target_reference.node != klass.instance_variables[target_reference.node.member.attrname][0].node):  # This excludes the case where the instance variable is assigned
                    result_target_reference.referenced_symbols.extend(
                        klass.instance_variables[target_reference.node.member.attrname])

    return result_target_reference


def _collect_reasons(module_data: ModuleData) -> dict[NodeID, Reasons]:
    """Collect all function references in the module.

    This function must only be called after the scope of all nodes has been determined,
    and the module scope is the current node.
    Iterate over all functions and find all function references in the module.
    Therefore, we loop over all target nodes and check if they are used in the function body of each function.
    The same is done for all value nodes and all calls/class initializations.

    Returns
    -------
    dict[NodeID, Reasons]
        A dict containing all function references in the module.
        The dict is structured as follows:
        {
            "NodeID_of_function": Reasons(
                function_def_node,
                {Symbol}, # writes
                {Symbol}, # reads
                {Symbol}, # calls
            )
            ...
        }
    """
    def find_first_parent_function(node: astroid.NodeNG | MemberAccess) -> astroid.NodeNG:
        """Find the first parent of a call node that is a function.

        Parameters
        ----------
        node : astroid.NodeNG
            The node to start the search from.

        Returns
        -------
        astroid.NodeNG
            The first parent of the node that is a function.
            If the parent is a module, return the module.
        """
        if isinstance(node, MemberAccess):
            node = node.member
        if isinstance(node.parent, astroid.FunctionDef | astroid.Lambda | astroid.Module | None):
            return node.parent
        return find_first_parent_function(node.parent)

    python_builtins = dir(builtins)
    function_references: dict[NodeID, Reasons] = {}

    for function_scopes in module_data.functions.values():
        for function_node in function_scopes:  # iterate over all functions with the same name
            function_id = calc_node_id(function_node.symbol.node)
            function_def_node = function_node.symbol.node

            # Look at all target nodes and check if they are used in the function body
            for target in module_data.target_nodes:
                # Only look at global variables (for global reads)
                if target.name in module_data.global_variables or isinstance(target,
                                                                             MemberAccessTarget):  # Filter out all non-global variables
                    for child in function_node.children:
                        if target.name == child.symbol.name and child in function_node.children:
                            ref = child.symbol

                            if function_id in function_references:  # check if the function is already in the dict
                                if ref not in function_references[function_id]:
                                    function_references[function_id].writes.add(ref)
                            else:  # create a new entry in the dict
                                function_references[function_id] = Reasons(
                                    function_def_node,
                                    {ref},
                                    set(),
                                    set(),
                                )  # Add writes

            # Look at all value nodes and check if they are used in the function body
            for value in module_data.value_nodes:
                if isinstance(module_data.functions[function_id.name][0], FunctionScope):
                    # Since we do not differentiate between functions with the same name, we can choose the first one
                    # TODO: this is not correct. also cache this since it is called multiple times
                    function_values = module_data.functions[function_id.name][0].value_references
                    if value.name in function_values:
                        if value.name in module_data.global_variables or isinstance(value, MemberAccessValue):
                            # Get the correct symbol
                            sym = None
                            if isinstance(module_data.value_nodes[value], FunctionScope):
                                for val_list in module_data.value_nodes[
                                    value].value_references.values():  # type: ignore[union-attr] # we can ignore the linter error because of the if statement above
                                    for val in val_list:
                                        if val.node == value:
                                            sym = val
                                            break
                            else:
                                # raise TypeError(f"{self.value_nodes[value]} is not of type FunctionScope")
                                continue

                            ref = sym

                            if function_id in function_references:  # check if the function is already in the dict
                                function_references[function_id].reads.add(ref)
                            else:  # create a new entry in the dict
                                function_references[function_id] = Reasons(
                                    function_def_node,
                                    set(),
                                    {ref},
                                    set(),
                                )  # Add reads

            # Look at all calls and check if they are used in the function body
            unknown = []
            for call in module_data.function_calls:
                # make sure we do not get an AttributeError because of the inconsistent names in the astroid API
                if isinstance(call.func, astroid.Attribute):
                    call_func_name = call.func.attrname
                else:
                    call_func_name = call.func.name

                parent_function = find_first_parent_function(call)
                function_scopes_calls_names = list(function_node.call_references.keys())
                if call_func_name in function_scopes_calls_names and parent_function.name == function_id.name:
                    # get the correct symbol
                    sym = None
                    ref = None
                    # check all self defined functions
                    if call_func_name in module_data.functions:
                        sym = module_data.functions[call_func_name][0].symbol
                    # check all self defined classes
                    elif call_func_name in module_data.classes:
                        sym = module_data.classes[call_func_name].symbol
                    # check all builtins
                    elif call_func_name in python_builtins:
                        sym = Builtin(call, NodeID("builtins", call_func_name, 0, 0), call_func_name)
                    # check if a parameter of the function is called
                    # elif isinstance(parent_function, astroid.FunctionDef) and parent_function in self.parameters:
                    #     for i, p in enumerate(self.parameters[parent_function][1]):
                    #         if p.name == call_func_name:
                    #             sym = self.parameters[parent_function][1][i]
                    #             break
                    elif isinstance(parent_function, astroid.FunctionDef):
                        fun_list = module_data.functions[parent_function.name]
                        fun = None
                        for f in fun_list:
                            if f.symbol.node == parent_function:
                                fun = f
                                break
                        if fun is not None:
                            for par_name, par in fun.parameters.items():
                                if par_name == call_func_name:
                                    sym = par
                                    break

                    if sym is None:
                        unknown.append(call)
                    else:
                        ref = Symbol(call, calc_node_id(call), call_func_name)

                    if function_id in function_references and ref:  # check if the function is already in the dict
                        function_references[function_id].calls.add(ref)
                    else:  # create a new entry in the dict
                        function_references[function_id] = Reasons(
                            function_def_node,
                        )  # Add calls
                        if ref:
                            function_references[function_id].calls.add(ref)
                        if unknown:
                            function_references[function_id].unknown_calls = unknown

            # Add function to function_references dict if no reason (write, read nor call) was found
            if function_id not in function_references:
                function_references[function_id] = Reasons(function_def_node, set(), set(), set())

    # remove duplicate calls from reads
    if module_data.function_calls:
        for ref in function_references.values():
            if not isinstance(ref, Reasons):
                raise TypeError("ref is not of type Reasons")
            if ref.calls and ref.reads:
                ref.remove_class_method_calls_from_reads()
    return function_references


def resolve_references(
    code: str,
) -> ModuleAnalysisResult:
    """
    Resolve all references in a module.

    This function is the entry point for the reference resolving.
    It calls all other functions that are needed to resolve the references.
    First, we get the module data for the given (module) code.
    Then we call the functions to find all references in the module.

    Parameters
    ----------
    code : str
        The source code of the module.

    Returns
    -------
    ModuleAnalysisResult
        The result of the reference resolving as well as all other information
        that is needed for the purity analysis.
    """
    module_data = get_module_data(code)
    # name_references = _find_name_references(
    #     module_data.target_nodes,
    #     module_data.value_nodes,
    #     module_data.classes,
    #     module_data.functions,
    #     module_data.parameters,
    #     module_data.global_variables
    # )

    # if module_data.function_calls:
    #     call_references_old = _find_call_references(
    #         module_data.function_calls,
    #         module_data.classes,
    #         module_data.functions,
    #         module_data.parameters,
    #     )
    # else:
    #     call_references_old = {}

    # instead of iterating over all function calls, we can iterate over all functions and their call_references
    # since we do not need to look at other calls outside the functions.
    # -> this leads to an improvement since we do not need to iterate over all function calls
    value_references_new = {}
    target_references_new = {}
    call_references_new: dict[NodeID, list[ValueReference]] = {}
    # This is a list because we only analyze the functions by name, therefor a call can reference more than one function.
    # In the future, we maybe want to differentiate between calls with the same name.
    # This could be done by further specifying the call_references for a function (by analyzing the signature, etc.)
    for function_list in module_data.functions.values():
        # iterate over all functions with the same name
        for function in function_list:
            # Check if the function has call_references (References from a call to the function definition itself).
            # TODO: these steps can be done parallel
            if function.call_references:
                # TODO: move this to a function called: _find_references
                # TODO: give the result into the function to use it as a cache to look up already determined references
                for call_list in function.call_references.values():
                    for call_reference in call_list:
                        call_references = _find_call_references_single_call(call_reference, function, module_data.functions, module_data.classes)

                        if call_references.node.id.__str__() not in call_references_new:
                            call_references_new[call_references.node.id.__str__()] = [call_references]  # TODO: remove str()
                        else:
                            call_references_new[call_references.node.id.__str__()].append(call_references)

            # Check if the function has value_references (References from a value node to a target node).
            if function.value_references:
                for value_list in function.value_references.values():
                    for value_reference in value_list:
                        value_reference_result = _find_value_references_new(value_reference, function, module_data.functions, module_data.classes)

                        if value_reference_result.referenced_symbols:
                            if value_reference_result.node.id.__str__() not in value_references_new:
                                value_references_new[value_reference_result.node.id.__str__()] = [value_reference_result]
                            else:
                                value_references_new[value_reference_result.node.id.__str__()].append(value_reference_result)

            # Check if the function has target_references (References from a target node to another target node).
            if function.target_symbols:
                for target_list in function.target_symbols.values():
                    for target_reference in target_list:
                        target_reference_result = _find_target_references_new(target_reference, function, module_data.classes)

                        if target_reference_result.referenced_symbols:
                            if target_reference_result.node.id.__str__() not in target_references_new:
                                target_references_new[target_reference_result.node.id.__str__()] = [target_reference_result]
                            else:
                                target_references_new[target_reference_result.node.id.__str__()].append(target_reference_result)

    # TODO: we should collect the reasons while iterating over the functions so that we do not need to iterate over them again
    reasons = _collect_reasons(module_data)

    name_references_new = merge_dicts(value_references_new, target_references_new)

    resolved_references = merge_dicts(call_references_new, name_references_new)

    call_graph = build_call_graph(module_data.functions, module_data.classes, reasons)

    return ModuleAnalysisResult(resolved_references, reasons, module_data.classes, call_graph)


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
