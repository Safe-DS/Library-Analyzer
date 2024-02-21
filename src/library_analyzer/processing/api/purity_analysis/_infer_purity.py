from __future__ import annotations

import astroid

from library_analyzer.processing.api.purity_analysis import calc_node_id
from library_analyzer.processing.api.purity_analysis._resolve_references import resolve_references

from library_analyzer.processing.api.purity_analysis.model import (
    CallGraphNode,
    CallOfParameter,
    ClassScope,
    ClassVariable,
    FileRead,
    FileWrite,
    GlobalVariable,
    Impure,
    ImpurityReason,
    InstanceVariable,
    ModuleAnalysisResult,
    NodeID,
    NonLocalVariableRead,
    NonLocalVariableWrite,
    OpenMode,
    ParameterAccess,
    Pure,
    PurityResult,
    Reasons,
    ReferenceNode,
    StringLiteral,
    Symbol,
    UnknownCall,
)

# TODO: check these for correctness and add reasons for impurity
BUILTIN_FUNCTIONS = {  # all errors and warnings are pure
    "ArithmeticError": Pure(),
    "AssertionError": Pure(),
    "AttributeError": Pure(),
    "BaseException": Impure(set()),
    "BaseExceptionGroup": Impure(set()),
    "BlockingIOError": Pure(),
    "BrokenPipeError": Pure(),
    "BufferError": Pure(),
    "BytesWarning": Pure(),
    "ChildProcessError": Pure(),
    "ConnectionAbortedError": Pure(),
    "ConnectionError": Pure(),
    "ConnectionRefusedError": Pure(),
    "ConnectionResetError": Pure(),
    "DeprecationWarning": Pure(),
    "EOFError": Pure(),
    "Ellipsis": Impure(set()),
    "EncodingWarning": Pure(),
    "EnvironmentError": Pure(),
    "Exception": Impure(set()),
    "ExceptionGroup": Impure(set()),
    "False": Impure(set()),
    "FileExistsError": Pure(),
    "FileNotFoundError": Pure(),
    "FloatingPointError": Pure(),
    "FutureWarning": Pure(),
    "GeneratorExit": Impure(set()),
    "IOError": Pure(),
    "ImportError": Pure(),
    "ImportWarning": Pure(),
    "IndentationError": Pure(),
    "IndexError": Pure(),
    "InterruptedError": Pure(),
    "IsADirectoryError": Pure(),
    "KeyError": Pure(),
    "KeyboardInterrupt": Impure(set()),
    "LookupError": Pure(),
    "MemoryError": Pure(),
    "ModuleNotFoundError": Pure(),
    "NameError": Pure(),
    "None": Impure(set()),
    "NotADirectoryError": Pure(),
    "NotImplemented": Impure(set()),
    "NotImplementedError": Pure(),
    "OSError": Pure(),
    "OverflowError": Pure(),
    "PendingDeprecationWarning": Pure(),
    "PermissionError": Pure(),
    "ProcessLookupError": Pure(),
    "RecursionError": Pure(),
    "ReferenceError": Pure(),
    "ResourceWarning": Pure(),
    "RuntimeError": Pure(),
    "RuntimeWarning": Pure(),
    "StopAsyncIteration": Impure(set()),
    "StopIteration": Impure(set()),
    "SyntaxError": Pure(),
    "SyntaxWarning": Pure(),
    "SystemError": Pure(),
    "SystemExit": Impure(set()),
    "TabError": Pure(),
    "TimeoutError": Pure(),
    "True": Impure(set()),
    "TypeError": Pure(),
    "UnboundLocalError": Pure(),
    "UnicodeDecodeError": Pure(),
    "UnicodeEncodeError": Pure(),
    "UnicodeError": Pure(),
    "UnicodeTranslateError": Pure(),
    "UnicodeWarning": Pure(),
    "UserWarning": Pure(),
    "ValueError": Pure(),
    "Warning": Pure(),
    "WindowsError": Pure(),
    "ZeroDivisionError": Pure(),
    "__build_class__": Impure(set()),
    "__debug__": Impure(set()),
    "__doc__": Impure(set()),
    "__import__": Impure(set()),
    "__loader__": Impure(set()),
    "__name__": Impure(set()),
    "__package__": Impure(set()),
    "__spec__": Impure(set()),
    "abs": Pure(),
    "aiter": Impure(set()),  # May raise exceptions or interact with external resources
    "all": Pure(),
    "anext": Impure(set()),  # May raise exceptions or interact with external resources
    "any": Pure(),
    "ascii": Pure(),
    "bin": Pure(),
    "bool": Pure(),
    "breakpoint": Impure(set()),  # Debugger-related, doesn't affect program behavior
    "bytearray": Impure(set()),  # Can be modified
    "bytes": Impure(set()),  # Can be modified
    "callable": Pure(),
    "chr": Pure(),
    "classmethod": Pure(),
    "compile": Impure(set()),  # Can execute arbitrary code
    "complex": Pure(),
    "delattr": Impure(set()),  # Can modify objects
    "dict": Impure(set()),  # Can be modified
    "dir": Impure(set()),  # May interact with external resources
    "divmod": Pure(),
    "enumerate": Pure(),
    "eval": Impure(set()),  # Can execute arbitrary code
    "exec": Impure(set()),  # Can execute arbitrary code
    "filter": Pure(),
    "float": Pure(),
    "format": Impure(set()),  # Can produce variable output
    "frozenset": Pure(),
    "getattr": Impure(set()),  # Can raise exceptions or interact with external resources
    "globals": Impure(set()),  # May interact with external resources  # TODO: implement special case since this can modify the global namespace
    "hasattr": Pure(),
    "hash": Pure(),
    "help": Impure(set()),  # May interact with external resources
    "hex": Pure(),
    "id": Pure(),
    "input": Impure({FileRead(StringLiteral("stdin"))}),  # Reads user input
    "int": Pure(),
    "isinstance": Pure(),
    "issubclass": Pure(),
    "iter": Pure(),
    "len": Pure(),
    "list": Impure(set()),  # Can be modified
    "locals": Impure(set()),  # May interact with external resources
    "map": Pure(),
    "max": Pure(),
    "memoryview": Impure(set()),  # Can be modified
    "min": Pure(),
    "next": Impure(set()),  # May raise exceptions or interact with external resources
    "object": Pure(),
    "oct": Pure(),
    "open": Impure(set()),  # Can interact with external resources (write and read)
    "ord": Pure(),
    "pow": Pure(),
    "print": Impure({FileWrite(StringLiteral("stdout"))}),
    "property": Pure(),
    "range": Pure(),
    "repr": Pure(),
    "reversed": Pure(),
    "round": Pure(),
    "set": Impure(set()),  # Can be modified
    "setattr": Impure(set()),  # Can modify objects
    "slice": Pure(),
    "sorted": Pure(),
    "staticmethod": Pure(),
    "str": Impure(set()),  # Can be modified
    "sum": Pure(),
    "super": Impure(set()),  # Can interact with classes
    "tuple": Impure(set()),  # Can be modified
    "type": Pure(),
    "vars": Impure(set()),  # May interact with external resources
    "zip": Pure(),
}

OPEN_MODES = {
    "": OpenMode.READ,
    "r": OpenMode.READ,
    "rb": OpenMode.READ,
    "rt": OpenMode.READ,
    "w": OpenMode.WRITE,
    "wb": OpenMode.WRITE,
    "wt": OpenMode.WRITE,
    "a": OpenMode.WRITE,
    "ab": OpenMode.WRITE,
    "at": OpenMode.WRITE,
    "x": OpenMode.WRITE,
    "xb": OpenMode.WRITE,
    "xt": OpenMode.WRITE,
    "r+": OpenMode.READ_WRITE,
    "rb+": OpenMode.READ_WRITE,
    "w+": OpenMode.READ_WRITE,
    "wb+": OpenMode.READ_WRITE,
    "a+": OpenMode.READ_WRITE,
    "ab+": OpenMode.READ_WRITE,
    "x+": OpenMode.READ_WRITE,
    "xb+": OpenMode.READ_WRITE,
    "r+b": OpenMode.READ_WRITE,
    "rb+b": OpenMode.READ_WRITE,
    "w+b": OpenMode.READ_WRITE,
    "wb+b": OpenMode.READ_WRITE,
    "a+b": OpenMode.READ_WRITE,
    "ab+b": OpenMode.READ_WRITE,
    "x+b": OpenMode.READ_WRITE,
    "xb+b": OpenMode.READ_WRITE,
}


# TODO: remove type ignore after implementing all cases
def check_open_like_functions(symbol: Symbol) -> PurityResult:  # type: ignore[return] # all cases are handled
    """Check open-like function for impurity.

    This includes functions like open, read, readline, readlines, write, writelines.

    Parameters
    ----------
    symbol: Symbol
        The symbol to check.

    Returns
    -------
    PurityResult
        The purity result of the function.

    """
    # Check if we deal with the open function
    if isinstance(symbol.node, astroid.Call):
        # make sure we do not get an AttributeError because of the inconsistent names in the astroid API
        if isinstance(symbol.node.func, astroid.Attribute):
            func_ref_node_func_name = symbol.node.func.attrname
        else:
            func_ref_node_func_name = symbol.node.func.name

        if func_ref_node_func_name == "open":
            open_mode_str: str = "r"
            open_mode: OpenMode | None = None
            # Check if a mode is set and if the value is a string literal
            if len(symbol.node.args) >= 2 and isinstance(symbol.node.args[1], astroid.Const):
                if symbol.node.args[1].value in OPEN_MODES:
                    open_mode_str = symbol.node.args[1].value
            # We exclude the case where the mode is a variable since we cannot determine the mode in this case,
            # therefore, we set it to be the worst case (read and write)
            elif len(symbol.node.args) == 2 and not isinstance(symbol.node.args[1], astroid.Const):
                open_mode = OpenMode.READ_WRITE

            # We need to check if the file name is a variable or a string literal
            if isinstance(symbol.node.args[0], astroid.Name):
                file_var = symbol.node.args[0].name
                if not open_mode:
                    open_mode = OPEN_MODES[open_mode_str]
                match open_mode:
                    case OpenMode.READ:
                        return Impure({FileRead(ParameterAccess(file_var))})
                    case OpenMode.WRITE:
                        return Impure({FileWrite(ParameterAccess(file_var))})
                    case OpenMode.READ_WRITE:
                        return Impure({FileRead(ParameterAccess(file_var)), FileWrite(ParameterAccess(file_var))})

            # The file name is a string literal
            else:
                file_str = symbol.node.args[0].value
                open_mode = OPEN_MODES[open_mode_str]
                match open_mode:
                    case OpenMode.READ:
                        return Impure({FileRead(StringLiteral(file_str))})
                    case OpenMode.WRITE:
                        return Impure({FileWrite(StringLiteral(file_str))})
                    case OpenMode.READ_WRITE:
                        return Impure({FileRead(StringLiteral(file_str)), FileWrite(StringLiteral(file_str))})
        else:
            pass  # TODO: [Later] for now it is good enough to deal with open() only, but we MAYBE need to deal with the other open-like functions too


def infer_purity(
    code: str
) -> dict[astroid.FunctionDef, PurityResult]:
    """
    Infer the purity of functions.

    Given a ModuleAnalysisResult (resolved references, call graph, classes, etc.)
    this function infers the purity of the functions inside a module.
    It therefore iterates over the function references and processes the nodes in the call graph.

    Parameters
    ----------
    code : str
        The source code of the module.

    Returns
    -------
    purity_results : dict[astroid.FunctionDef, PurityResult]
        The purity results of the functions in the module.
        Keys are the function nodes, values are the purity results.
    """
    # Analyze the code, resolve the references in the module and build the call graph for the module
    analysis_result = resolve_references(code)

    purity_results: dict[astroid.FunctionDef, PurityResult] = (
        {}
    )  # We use astroid.FunctionDef instead of str as a key so we can access the node later

    for reasons in analysis_result.function_references.values():
        process_node(reasons, analysis_result, purity_results)

    # Cleanup the purity results: We do not want the combined nodes in the results
    return {key: value for key, value in purity_results.items() if not isinstance(key, str)}


def process_node(  # type: ignore[return] # all cases are handled
    reason: Reasons,
    analysis_result: ModuleAnalysisResult,
    purity_results: dict[astroid.FunctionDef, PurityResult],
) -> PurityResult:
    """
    Process a node in the call graph.

    Given a node in the call graph, this function processes the node and its children to determine the purity of the function.
    It checks if a node was already processed, and if so, it returns the result directly.
    If the node is not processed yet, it checks if the node is a builtin function or a self-defined function.
    If the node is a builtin function, it checks if it is an open-like function and returns the result.
    If the node is a self-defined function, it checks if the function is a leaf node (has no children) and if so, it checks the reasons for impurity.
    It deals with combined nodes separately.
    If the function is not a leaf node, it processes the children first and propagates the results afterward.
    The results are stored in the purity_results dict and in the call graph (for caching).

    Parameters
    ----------
    reason : Reasons
        The node to process containing the raw reasons for impurity collected.
    analysis_result : ModuleAnalysisResult
        The result of the analysis of the module.
    purity_results : PurityResult
        The function nodes as keys and purity results of the functions as values.
        Since we collect them iteratively, we need to pass them as a parameter to check for duplicates.

    Returns
    -------
    PurityResult
        The purity result of the function node.
    """
    if not isinstance(reason, Reasons):
        raise TypeError(f"Expected Reasons, got {reason.__class__.__name__}") from None

    # This is the case whenever a combined node is processed
    if isinstance(reason.function, str) or reason.function is None:
        reason.function = astroid.FunctionDef(name=reason.function)  # This is a hack to make the code work but it is not nice
        reason_id = NodeID(None, reason.function.name)
    else:  # Normally, the ID can be calculated from the function node as usual
        reason_id = calc_node_id(reason.function)

    # Check the forest if the purity of the function is already determined
    if reason_id in analysis_result.call_graph.graphs:
        if analysis_result.call_graph.get_graph(reason_id).reasons.result:
            purity_results[reason.function] = analysis_result.call_graph.get_graph(reason_id).reasons.result  # type: ignore[assignment] # None is not possible here
            return purity_results[reason.function]

    # Check if the referenced function is a builtin function
    elif reason.function.name in BUILTIN_FUNCTIONS:
        if reason.function.name in ("open", "read", "readline", "readlines", "write", "writelines", "close"):
            purity_results[reason.function] = check_open_like_functions(
                reason.get_call_by_name(reason.function.name),
            )
        else:
            purity_results[reason.function] = BUILTIN_FUNCTIONS[reason.function.name]
        return purity_results[reason.function]

    # The purity of the function is not determined yet
    try:
        # Check if the function has any child nodes if so we need to check their purity first and propagate the results afterward
        # First we need to check if the reference actually is inside the call graph because it might be a builtin function or a combined node
        if reason_id in analysis_result.call_graph.graphs:
            # If the node is part of the call graph, we can check if it has any children (called functions) = not a leaf
            if not analysis_result.call_graph.get_graph(reason_id).is_leaf():
                for child in analysis_result.call_graph.get_graph(reason_id).children:
                    # Check if we deal with a combined node (would throw a KeyError otherwise) # TODO: is this still the case with the changed analysis??
                    if not child.combined_node_names:
                        get_purity_of_child(
                            child,
                            reason,
                            analysis_result,
                            purity_results,
                        )
                    # The child is a combined node and therefore not part of the reference dict
                    else:  # noqa: PLR5501 # better for readability
                        if reason.function not in purity_results:  # better for readability
                            purity_results[reason.function] = analysis_result.call_graph.get_graph(child.function.symbol.id).reasons.result
                        else:
                            purity_results[reason.function] = purity_results[reason.function].update(
                                analysis_result.call_graph.get_graph(child.function.symbol.id).reasons.result,
                            )

                # After all children are handled, we can propagate the purity of the called functions to the calling function
                analysis_result.call_graph.get_graph(reason_id).reasons.result = purity_results[reason.function]

        # If the node is not part of the call graph, we need to check if it is a combined node
        else:
            # Check if we deal with a combined node since they need to be handled differently
            combined_nodes = {
                node.function.symbol.name: node for node in analysis_result.call_graph.graphs.values() if node.combined_node_names
            }
            for combined_node in combined_nodes.values():
                # Check if the current node is part of the combined node (therefore part of the cycle)
                if reason_id.__str__() in combined_node.combined_node_names:
                    # Check if the purity result was already determined
                    if combined_node.reasons.result and reason.function in purity_results:
                        purity_results[reason.function] = combined_node.reasons.result
                        return purity_results[reason.function]
                    else:
                        # We need to check if the combined node has any children that are not part of the cycle
                        # By design all children of a combined node are NOT part of the cycle
                        for child_of_combined in combined_node.children:
                            get_purity_of_child(
                                child_of_combined,
                                reason,
                                analysis_result,
                                purity_results,
                            )

                        # TODO: refactor this so it is cleaner
                        purity = transform_reasons_to_impurity_result(
                            analysis_result.call_graph.graphs[combined_node.function.symbol.id].reasons,
                            analysis_result
                        )

                        if not combined_node.reasons.result:
                            combined_node.reasons.result = purity
                        else:
                            combined_node.reasons.result = combined_node.reasons.result.update(purity)
                        if reason.function not in purity_results:
                            purity_results[reason.function] = purity
                        else:
                            purity_results[reason.function] = purity_results[reason.function].update(purity)
                        if combined_node.function.symbol.name not in purity_results:
                            purity_results[combined_node.function.symbol.name] = purity
                        else:
                            purity_results[combined_node.function.symbol.name] = purity_results[
                                combined_node.function.symbol.name
                            ].update(purity)

                    return purity_results[reason.function]

        # Check if we deal with a self-defined function
        if (
            isinstance(reason.function, astroid.FunctionDef | astroid.Lambda)
            and reason_id in analysis_result.call_graph.graphs
        ):
            # Check if the function does not call other functions (it is a leaf), we can check its (reasons for) impurity directly
            # also check that all children are already handled (have a result)
            if analysis_result.call_graph.graphs[reason_id].is_leaf() or all(
                c.reasons.result
                for c in analysis_result.call_graph.graphs[reason_id].children
                if not c.is_builtin
            ):
                purity_self_defined: PurityResult = Pure()
                if analysis_result.call_graph.graphs[reason_id].reasons:
                    purity_self_defined = transform_reasons_to_impurity_result(
                        analysis_result.call_graph.graphs[reason_id].reasons,
                        analysis_result
                    )

                # If a result was propagated from the children, it needs to be kept and updated with more reasons if the function itself has more reasons
                if (
                    analysis_result.call_graph.get_graph(reason_id).reasons.result is None
                ):  # TODO: this should never happen - check that and remove if statement -> this does happen... but it works
                    purity_results[reason.function] = purity_self_defined
                else:
                    purity_results[reason.function] = purity_results[reason.function].update(purity_self_defined)

                # Store the results in the forest, this also deals as a flag to indicate that the result is already computed completely
                analysis_result.call_graph.get_graph(reason_id).reasons.result = purity_results[reason.function]

                return purity_results[reason.function]
            else:
                return purity_results[reason.function]

    except KeyError:
        raise KeyError(f"Function {reason_id} not found in function_references") from None


# TODO: [Refactor] make this return a PurityResult??
# TODO: add statement, that adds the result to the purity_results dict before returning
def get_purity_of_child(
    child: CallGraphNode,
    reason: Reasons,
    analysis_result: ModuleAnalysisResult,
    purity_results: dict[astroid.FunctionDef, PurityResult],
) -> None:
    """
    Get the purity of a child node.

    Given a child node, this function handles the purity of the child node.

    Parameters
    ----------
    child: CallGraphNode
        The child node to process.
    reason : Reasons
        The node to process containing the raw reasons for impurity collected.
    analysis_result : ModuleAnalysisResult
        The result of the analysis of the module.
    purity_results : PurityResult
        The function nodes as keys and purity results of the functions as values.
        Since we collect them iteratively, we need to pass them as a parameter to check for duplicates.
    """
    if child.is_builtin:
        child_name = child.function.name
    else:
        child_name = child.function.symbol.name

    if child_name in ("open", "read", "readline", "readlines", "write", "writelines"):
        purity_result_child = check_open_like_functions(reason.get_call_by_name(child_name))
    elif child_name in BUILTIN_FUNCTIONS:
        purity_result_child = BUILTIN_FUNCTIONS[child_name]
    elif child_name in analysis_result.classes:
        if child.reasons.calls:
            init_fun_id = calc_node_id(child.reasons.calls.pop().node)  # TODO: make sure that there is only one call in the set of the class def reasons object
            purity_result_child = process_node(
                analysis_result.function_references[init_fun_id],
                analysis_result,
                purity_results,
            )
        else:
            purity_result_child = Pure()
    else:
        purity_result_child = process_node(
            analysis_result.function_references[child.function.symbol.id],
            analysis_result,
            purity_results,
        )

    # If a result for the child was found, we need to propagate it to the parent
    if purity_result_child:
        if reason.function not in purity_results:
            purity_results[reason.function] = purity_result_child
        else:
            purity_results[reason.function] = purity_results[reason.function].update(purity_result_child)


# TODO: this is not working correctly: whenever a variable is referenced, it is marked as read/written if its is not inside the current function
def transform_reasons_to_impurity_result(
    reasons: Reasons,
    analysis_result: ModuleAnalysisResult,
) -> PurityResult:
    """
    Transform the reasons for impurity to an impurity result.

    Given a Reasons object and a dict of references,
    this function transforms the collected reasons from a Reasons object to a set of ImpurityReasons.

    Parameters
    ----------
    reasons : Reasons
        The node to process containing the raw reasons for impurity collected.
    analysis_result : ModuleAnalysisResult
        The result of the analysis of the module.

    Returns
    -------
    ImpurityReason
        The impurity result of the function (Pure, Impure or Unknown).

    """
    impurity_reasons: set[ImpurityReason] = set()

    if not reasons:
        return Pure()
    else:
        if reasons.writes:
            for write in reasons.writes:
                write_ref_list = analysis_result.resolved_references[write.name]
                for write_ref in write_ref_list:
                    for sym_ref in write_ref.referenced_symbols:
                        if isinstance(sym_ref, GlobalVariable | ClassVariable | InstanceVariable):
                            impurity_reasons.add(NonLocalVariableWrite(sym_ref))
                        else:
                            raise TypeError(f"Unknown symbol reference type: {sym_ref.__class__.__name__}")

        if reasons.reads:
            for read in reasons.reads:
                read_ref_list = analysis_result.resolved_references[read.name]
                for read_ref in read_ref_list:
                    for sym_ref in read_ref.referenced_symbols:
                        if isinstance(sym_ref, GlobalVariable | ClassVariable | InstanceVariable):
                            impurity_reasons.add(NonLocalVariableRead(sym_ref))
                        else:
                            raise TypeError(f"Unknown symbol reference type: {sym_ref.__class__.__name__}")

        if reasons.unknown_calls:
            for unknown_call in reasons.unknown_calls:
                # make sure we do not get an AttributeError because of the inconsistent names in the astroid API
                if isinstance(unknown_call.func, astroid.Attribute):
                    unknown_call_func_name = unknown_call.func.attrname
                else:
                    unknown_call_func_name = unknown_call.func.name
                reason_id = calc_node_id(reasons.function)  # TODO: maybe add ID to Reasons?
                if reason_id in analysis_result.call_graph.graphs:
                    graph = analysis_result.call_graph.get_graph(reason_id)
                    if unknown_call_func_name in graph.function.parameters:
                        impurity_reasons.add(CallOfParameter(ParameterAccess(unknown_call_func_name)))
                    else:
                        impurity_reasons.add(UnknownCall(StringLiteral(unknown_call_func_name)))
                elif not analysis_result.classes:
                    impurity_reasons.add(UnknownCall(StringLiteral(unknown_call_func_name)))
                else:  # noqa: PLR5501 # better for readability
                    if unknown_call_func_name in analysis_result.classes:  # better for readability
                        pass
                    else:
                        impurity_reasons.add(UnknownCall(StringLiteral(unknown_call_func_name)))
        if impurity_reasons:
            return Impure(impurity_reasons)
        return Pure()
