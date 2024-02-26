from __future__ import annotations

import builtins

import astroid

from library_analyzer.processing.api.purity_analysis import get_module_data
from library_analyzer.processing.api.purity_analysis._build_call_graph import build_call_graph
from library_analyzer.processing.api.purity_analysis.model import (
    Builtin,
    ClassScope,
    ClassVariable,
    FunctionScope,
    GlobalVariable,
    InstanceVariable,
    MemberAccessTarget,
    MemberAccessValue,
    ModuleAnalysisResult,
    NodeID,
    Reasons,
    Reference,
    ReferenceNode,
    Symbol,
    TargetReference,
    ValueReference,
)

_BUILTINS = dir(builtins)


def _find_call_references(call_reference: Reference,
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
        if class_def:
            value_reference.referenced_symbols.append(class_def.symbol)

    # Find builtins that are called, this includes open-like functions.
    if call_reference.name in _BUILTINS or call_reference.name in ("open", "read", "readline", "readlines", "write", "writelines", "close"):
        builtin_call = Builtin(
            call_reference.node,  # Since we do not have a FunctionDef node for the builtin, we use the Call node
            NodeID("builtins", call_reference.name, -1, -1),
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


def _find_value_references(value_reference: Reference,
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
        # Check if all symbols are refined (refined means that they are of any subtyp of Symbol)
        if any(isinstance(symbol, Symbol) for symbol in symbols):
            # This currently is mostly the case for ClassVariables and InstanceVariables that are used as targets

            missing_refined = [symbol for symbol in symbols if type(symbol) is Symbol]
            # Because we add the missing refined symbols separately above,
            # we need to remove the unrefined symbols from the list to avoid duplicates.
            symbols = list(set(symbols) - set(missing_refined))

            for symbol in missing_refined:
                if isinstance(symbol.node, MemberAccessTarget):
                    for klass in classes.values():
                        if klass.class_variables:
                            if value_reference.node.member in klass.class_variables:
                                symbols.append(ClassVariable(symbol.node, symbol.id, symbol.node.member, klass.symbol.node))
                        if klass.instance_variables:
                            if value_reference.node.member in klass.instance_variables:
                                symbols.append(InstanceVariable(symbol.node, symbol.id, symbol.node.member, klass.symbol.node))

        # Only add symbols that are defined before the value is used.
        for symbol in symbols:
            if symbol.id.line <= value_reference.id.line:
                result_value_reference.referenced_symbols.append(symbol)

    # Find parameters that are referenced.
    if value_reference.name in function.parameters:
        local_symbols = [function.parameters[value_reference.name]]
        result_value_reference.referenced_symbols.extend(local_symbols)

    # Find global variables that are referenced.
    if value_reference.name in function.globals_used:
        global_symbols = function.globals_used[value_reference.name]  # type: ignore[assignment] # globals_used contains GlobalVariable which are a subtype of Symbol.
        result_value_reference.referenced_symbols.extend(global_symbols)

    # Find functions that are referenced (as value).
    if value_reference.name in functions:
        function_def = functions.get(value_reference.name)
        if function_def:
            function_symbols = [func.symbol for func in function_def if function_def]
            result_value_reference.referenced_symbols.extend(function_symbols)

    # Find classes that are referenced (as value).
    if value_reference.name in classes:
        class_def = classes.get(value_reference.name)
        if class_def:
            result_value_reference.referenced_symbols.append(class_def.symbol)

    # Find class and instance variables that are referenced.
    if isinstance(value_reference.node, MemberAccessValue):
        for klass in classes.values():
            if klass.class_variables:
                if value_reference.node.member in klass.class_variables and value_reference.node.member not in function.call_references:
                    result_value_reference.referenced_symbols.extend(klass.class_variables[value_reference.node.member])
            if klass.instance_variables:
                if value_reference.node.member in klass.instance_variables and value_reference.node.member not in function.call_references:
                    result_value_reference.referenced_symbols.extend(klass.instance_variables[value_reference.node.member])

    return result_value_reference


def _find_target_references(target_reference: Symbol,
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
        # Only check for symbols that are defined before the current target_reference.
        local_symbols = function.target_symbols[target_reference.name][: function.target_symbols[target_reference.name].index(target_reference)]
        result_target_reference.referenced_symbols.extend(local_symbols)

    # Find global variables that are referenced.
    if target_reference.name in function.globals_used:
        global_symbols = function.globals_used[target_reference.name]
        result_target_reference.referenced_symbols.extend(global_symbols)

    # Find classes that are referenced (as value).
    if target_reference.name in classes:
        class_def = classes.get(target_reference.name)
        if class_def:
            result_target_reference.referenced_symbols.append(class_def.symbol)

    # Find class and instance variables that are referenced.
    if isinstance(target_reference.node, MemberAccessTarget):
        for klass in classes.values():
            if klass.class_variables:
                if target_reference.node.member in klass.class_variables:
                    # Do not add class variables from other classes
                    if target_reference.node.receiver is not None:
                        if (function.symbol.name == "__init__" and function.parent != klass
                            or target_reference.node.receiver.name == "self" and function.parent != klass
                        ):
                            continue
                    result_target_reference.referenced_symbols.extend(
                        klass.class_variables[target_reference.node.member])
            if klass.instance_variables:
                if (target_reference.node.member in klass.instance_variables
                    and target_reference.node != klass.instance_variables[target_reference.node.member][0].node):  # This excludes the case where the instance variable is assigned
                    result_target_reference.referenced_symbols.extend(
                        klass.instance_variables[target_reference.node.member])

    return result_target_reference


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

    def add_result_to_references(result: ValueReference | TargetReference, target: dict[str, list[ValueReference | TargetReference]]) -> None:
        if result.node.name not in target:
            target[result.node.name] = [result]
        else:
            target[result.node.name].append(result)

        add_raw_reason(result.referenced_symbols)

    def add_raw_reason(referenced_symbols: list[Symbol]) -> None:
        for ref_symbol in referenced_symbols:
            if isinstance(ref_symbol, GlobalVariable | ClassVariable | Builtin):
                if ref_symbol not in raw_reasons[function.symbol.id].calls:
                    raw_reasons[function.symbol.id].calls.add(ref_symbol)
                else:
                    raw_reasons[function.symbol.id].calls = {ref_symbol}

    raw_reasons: dict[NodeID, Reasons] = {}
    call_references: dict[str, list[ValueReference]] = {}
    value_references: dict[str, list[ValueReference]] = {}
    target_references: dict[str, list[TargetReference]] = {}
    # The call_references value is a list because we only analyze the functions by name, therefor a call can reference more than one function.
    # In the future, we maybe want to differentiate between calls with the same name.
    # This could be done by further specifying the call_references for a function (by analyzing the signature, etc.)
    # If we could analyze it with 100% certainty, we could also remove the list and use a single ValueReference.

    # reasons = _collect_reasons(module_data)
    for function_list in module_data.functions.values():
        # iterate over all functions with the same name
        for function in function_list:

            # Collect the reasons while iterating over the functions, so we don't need to iterate over them again later.
            raw_reasons[function.symbol.id] = Reasons(function)

            # TODO: these steps can be done parallel - is it necessary
            # Check if the function has call_references (References from a call to the function definition itself).
            if function.call_references:
                # TODO: move this to a function called: _find_references
                # TODO: give the result into the function to use it as a cache to look up already determined references
                for call_list in function.call_references.values():
                    for call_reference in call_list:
                        call_references_result = _find_call_references(call_reference, function, module_data.functions, module_data.classes)

                        # If referenced symbols are found, add them to the list of symbols in the dict by the name of the node.
                        # If the name does not yet exist, create a new list with the reference.
                        if call_references_result.referenced_symbols:
                            if call_references_result.node.name not in call_references:
                                call_references[call_references_result.node.name] = [call_references_result]
                            else:
                                call_references[call_references_result.node.name].append(call_references_result)

                            # Add the referenced symbols to the calls of the raw_reasons dict for this function
                            for referenced_symbol in call_references_result.referenced_symbols:
                                if isinstance(referenced_symbol, GlobalVariable | ClassVariable | Builtin):
                                    if referenced_symbol not in raw_reasons[function.symbol.id].calls:
                                        raw_reasons[function.symbol.id].calls.add(referenced_symbol)

            # Check if the function has value_references (References from a value node to a target node).
            if function.value_references:
                for value_list in function.value_references.values():
                    for value_reference in value_list:
                        value_reference_result = _find_value_references(value_reference, function, module_data.functions, module_data.classes)

                        # If referenced symbols are found, add them to the list of symbols in the dict by the name of the node.
                        # If the name does not yet exist, create a new list with the reference.
                        if value_reference_result.referenced_symbols:
                            if value_reference_result.node.name not in value_references:
                                value_references[value_reference_result.node.name] = [value_reference_result]
                            else:
                                value_references[value_reference_result.node.name].append(value_reference_result)

                            # Add the referenced symbols to the reads_from of the raw_reasons dict for this function
                            for referenced_symbol in value_reference_result.referenced_symbols:
                                if isinstance(referenced_symbol, GlobalVariable | ClassVariable | InstanceVariable):
                                    # Since we define classes and functions as immutable Reading from them is not a reason for impurity.
                                    if isinstance(referenced_symbol.node, astroid.ClassDef | astroid.FunctionDef):
                                        continue
                                    # Add the referenced symbol to the list of symbols whom are read from.
                                    if referenced_symbol not in raw_reasons[function.symbol.id].reads_from:
                                        raw_reasons[function.symbol.id].reads_from.add(referenced_symbol)

            # Check if the function has target_references (References from a target node to another target node).
            if function.target_symbols:
                for target_list in function.target_symbols.values():
                    for target_reference in target_list:
                        target_reference_result = _find_target_references(target_reference, function, module_data.classes)

                        # If referenced symbols are found, add them to the list of symbols in the dict by the name of the node.
                        # If the name does not yet exist, create a new list with the reference.
                        if target_reference_result.referenced_symbols:
                            if target_reference_result.node.name not in target_references:
                                target_references[target_reference_result.node.name] = [target_reference_result]
                            else:
                                target_references[target_reference_result.node.name].append(target_reference_result)

                            # Add the referenced symbols to the writes_to of the raw_reasons dict for this function
                            for referenced_symbol in target_reference_result.referenced_symbols:
                                if isinstance(referenced_symbol, GlobalVariable | ClassVariable | InstanceVariable):
                                    # Since we define classes and functions as immutable, writing to them is not a reason for impurity.
                                    # Also, it is not common to do so anyway.
                                    if isinstance(referenced_symbol.node, astroid.ClassDef | astroid.FunctionDef):
                                        continue
                                    # Add the referenced symbol to the list of symbols whom are written to.
                                    if referenced_symbol not in raw_reasons[function.symbol.id].writes_to:
                                        raw_reasons[function.symbol.id].writes_to.add(referenced_symbol)

    name_references = merge_dicts(value_references, target_references)
    resolved_references = merge_dicts(call_references, name_references)

    call_graph = build_call_graph(module_data.functions, module_data.classes, raw_reasons)

    # The resolved_references are not needed in the next step anymore since raw_reasons contains all the information.
    # We do need them for testing though, so we return them.
    return ModuleAnalysisResult(resolved_references, raw_reasons, module_data.classes, call_graph)


def merge_dicts(
    d1: dict[str, list[ValueReference | TargetReference]],
    d2: dict[str, list[ValueReference | TargetReference]],
) -> dict[str, list[ValueReference | TargetReference]]:
    """Merge two dicts of lists of ReferenceNodes.

    Parameters
    ----------
    d1 : dict[str, list[ValueReference | TargetReference]]
        The first dict.
    d2 : dict[str, list[ValueReference | TargetReference]]
        The second dict.

    Returns
    -------
    d3 : dict[str, list[ValueReference | TargetReference]]
        The merged dict.
    """
    d3 = d1.copy()
    for key, value in d2.items():
        if key in d3:
            d3[key].extend(value)
        else:
            d3[key] = value
    return d3
