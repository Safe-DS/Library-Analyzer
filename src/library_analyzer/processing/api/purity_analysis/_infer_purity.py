from __future__ import annotations

from pathlib import Path

import astroid

from library_analyzer.processing.api.purity_analysis import calc_node_id
from library_analyzer.processing.api.purity_analysis._resolve_references import resolve_references
from library_analyzer.processing.api.purity_analysis.model import (
    APIPurity,
    Builtin,
    BuiltinOpen,
    CallGraphForest,
    CallOfFunction,
    CallOfParameter,
    ClassInit,
    CombinedCallGraphNode,
    FileRead,
    FileWrite,
    Import,
    ImportedCallGraphNode,
    Impure,
    ImpurityReason,
    NewCallGraphNode,
    NodeID,
    NonLocalVariableRead,
    NonLocalVariableWrite,
    OpenMode,
    ParameterAccess,
    Pure,
    PurityResult,
    Reasons,
    StringLiteral,
    UnknownCall,
)

# TODO: check these for correctness and add reasons for impurity
BUILTIN_FUNCTIONS: dict[str, PurityResult] = {  # all errors and warnings are pure
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
    "globals": Impure(
        set(),
    ),  # May interact with external resources  # TODO: implement special case since this can modify the global namespace
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


# # TODO: remove type ignore after implementing all cases
# def check_open_like_functions(call: astroid.Call) -> PurityResult:  # type: ignore[return] # all cases are handled
#     """Check open-like function for impurity.
#
#     This includes functions like open, read, readline, readlines, write, writelines.
#
#     Parameters
#     ----------
#     call: astrid.Call
#         The call to check.
#
#     Returns
#     -------
#     PurityResult
#         The purity result of the function.
#
#     """
#     if not isinstance(call, astroid.Call):
#         raise TypeError(f"Expected astroid.Call, got {call.__class__.__name__}") from None
#
#     # Make sure there is no AttributeError because of the inconsistent names in the astroid API.
#     if isinstance(call.func, astroid.Attribute):
#         func_ref_node_func_name = call.func.attrname
#     else:
#         func_ref_node_func_name = call.func.name
#
#     # Check if the function is open
#     if func_ref_node_func_name == "open":
#         open_mode_str: str = "r"
#         open_mode: OpenMode | None = None
#         # Check if a mode is set and if the value is a string literal
#         if len(call.args) >= 2 and isinstance(call.args[1], astroid.Const):
#             if call.args[1].value in OPEN_MODES:
#                 open_mode_str = call.args[1].value
#         # Exclude the case where the mode is a variable since it cannot be determined in this case,
#         # therefore, set it to be the worst case (read and write).
#         elif len(call.args) == 2 and not isinstance(call.args[1], astroid.Const):
#             open_mode = OpenMode.READ_WRITE
#
#         # Check if the file name is a variable or a string literal
#         if isinstance(call.args[0], astroid.Name):
#             file_var = call.args[0].name
#             if not open_mode:
#                 open_mode = OPEN_MODES[open_mode_str]
#             match open_mode:
#                 case OpenMode.READ:
#                     return Impure({FileRead(ParameterAccess(file_var))})
#                 case OpenMode.WRITE:
#                     return Impure({FileWrite(ParameterAccess(file_var))})
#                 case OpenMode.READ_WRITE:
#                     return Impure({FileRead(ParameterAccess(file_var)), FileWrite(ParameterAccess(file_var))})
#
#         # The file name is a string literal
#         else:
#             file_str = call.args[0].value
#             open_mode = OPEN_MODES[open_mode_str]
#             match open_mode:
#                 case OpenMode.READ:
#                     return Impure({FileRead(StringLiteral(file_str))})
#                 case OpenMode.WRITE:
#                     return Impure({FileWrite(StringLiteral(file_str))})
#                 case OpenMode.READ_WRITE:
#                     return Impure({FileRead(StringLiteral(file_str)), FileWrite(StringLiteral(file_str))})
#     else:
#         pass  # TODO: [Later] for now it is good enough to deal with open() only, but we MAYBE need to deal with the other open-like functions too
#
#
# def infer_purity(code: str) -> dict[NodeID, PurityResult]:
#     """
#     Infer the purity of functions.
#
#     Given a ModuleAnalysisResult (resolved references, call graph, classes, etc.)
#     this function infers the purity of the functions inside a module.
#     It therefore iterates over the function references and processes the nodes in the call graph.
#
#     Parameters
#     ----------
#     code : str
#         The source code of the module.
#
#     Returns
#     -------
#     purity_results : dict[astroid.FunctionDef, PurityResult]
#         The purity results of the functions in the module.
#         Keys are the function nodes, values are the purity results.
#     """
#     pur = PurityAnalyzer(code).purity_results
#
#     # Analyze the code, resolve the references in the module and build the call graph for the module
#     # analysis_result = resolve_references(code)
#     #
#     # purity_results: dict[NodeID, PurityResult] = {}
#     # combined_node_names: set[str] = set()
#     #
#     # for reasons in analysis_result.raw_reasons.values():
#     #     process_node(reasons, analysis_result, purity_results)
#     #
#     # for graph in analysis_result.call_graph_forest.forest.values():
#     #     if isinstance(graph, CombinedCallGraphNode):
#     #         combined_node_name = "+".join(
#     #             sorted(combined_node_id_str for combined_node_id_str in graph.combined_node_id_to_string()),
#     #         )
#     #         combined_node_names.add(combined_node_name)
#
#    # TODO: can we do this more efficiently?
#    # Cleanup the purity results: combined nodes are not needed in the result
#    # return {key: value for key, value in purity_results.items() if key.name not in combined_node_names}
#    return pur
#
# def process_node(  # type: ignore[return] # all cases are handled
#     reason: Reasons,
#     analysis_result: ModuleAnalysisResult,
#     purity_results: dict[NodeID, PurityResult],
# ) -> PurityResult:
#     """
#     Process a node in the call graph.
#
#     Given a node in the call graph, this function processes the node and its children to determine the purity of the function.
#     It checks if a node was already processed, and if so, it returns the result directly.
#     If the node is not processed yet, it checks if the node is a builtin function or a self-defined function.
#     If the node is a builtin function, it checks if it is an open-like function and returns the result.
#     If the node is a self-defined function, it checks if the function is a leaf node (has no children) and if so, it checks the reasons for impurity.
#     It deals with combined nodes separately.
#     If the function is not a leaf node, it processes the children first and propagates the results afterward.
#     The results are stored in the purity_results dict and in the call graph (for caching).
#
#     Parameters
#     ----------
#     reason : Reasons
#         The node to process containing the raw reasons for impurity collected.
#     analysis_result : ModuleAnalysisResult
#         The result of the analysis of the module.
#     purity_results : dict[NodeID, PurityResult]
#         The function ids as keys and purity results of the functions as values.
#         Since the collection runs recursively, pass them as a parameter to check for already determined results.
#
#     Returns
#     -------
#     PurityResult
#         The purity result of the function node.
#     """
#     if not isinstance(reason, Reasons) or not isinstance(reason.function_scope, FunctionScope):
#         raise TypeError(f"Expected Reasons, got {reason.__class__.__name__}") from None
#
#     # Check the forest if the purity of the function is already determined
#     if analysis_result.call_graph_forest.has_graph(reason.id):
#         if analysis_result.call_graph_forest.get_graph(reason.id).reasons.result:
#             result = analysis_result.call_graph_forest.get_graph(reason.id).reasons.result
#             if result is not None:
#                 purity_results[reason.id] = result
#                 return purity_results[reason.id]
#
#     # The purity of the function is not determined yet.
#     try:
#         # Check if the function has any child nodes and if so, check their purity first and propagate the results afterward.
#         # First check if the reference actually is inside the call graph because it might be a builtin function or a combined node.
#         if reason.id in analysis_result.call_graph_forest.forest:
#             # If the node is part of the call graph, check if it has any children (called functions) = not a leaf.
#             if not analysis_result.call_graph_forest.get_graph(reason.id).is_leaf():
#                 for child in analysis_result.call_graph_forest.get_graph(reason.id).children:
#                     child_id = child.scope.symbol.id
#                     # Check if the node is a combined node (would throw a KeyError otherwise).
#                     if not isinstance(child, CombinedCallGraphNode):
#                         get_purity_of_child(
#                             child,
#                             reason,
#                             analysis_result,
#                             purity_results,
#                         )
#                     # The child is a combined node and therefore not part of the reference dict.
#                     else:  # noqa: PLR5501 # better for readability
#                         if reason.id not in purity_results:  # better for readability
#                             res = analysis_result.call_graph_forest.get_graph(child_id).reasons.result
#                             if res:
#                                 purity_results[reason.id] = res
#                         else:
#                             purity_results[reason.id] = purity_results[reason.id].update(
#                                 analysis_result.call_graph_forest.get_graph(child_id).reasons.result,
#                             )
#
#                 # After all children are handled, propagate the purity of the called functions to the calling function.
#                 analysis_result.call_graph_forest.get_graph(reason.id).reasons.result = purity_results[reason.id]
#
#         # If the node is not part of the call graph, check if it is a combined node.
#         else:
#             # Check if the node is a combined node since they need to be handled differently.
#             combined_nodes = {
#                 node.scope.symbol.name: node
#                 for node in analysis_result.call_graph_forest.forest.values()
#                 if node.combined_node_ids
#             }
#             for combined_node in combined_nodes.values():
#                 # Check if the current node is part of the combined node (therefore part of the cycle).
#                 if reason.id.__str__() in combined_node.combined_node_id_to_string():
#                     # Check if the purity result was already determined
#                     if combined_node.reasons.result and reason.id in purity_results:
#                         purity_results[reason.id] = combined_node.reasons.result
#                         return purity_results[reason.id]
#                     else:
#                         # Check if the combined node has any children that are not part of the cycle.
#                         # By design, all children of a combined node are NOT part of the cycle.
#                         for child_of_combined in combined_node.children:
#                             get_purity_of_child(
#                                 child_of_combined,
#                                 reason,
#                                 analysis_result,
#                                 purity_results,
#                             )
#
#                         # TODO: refactor this so it is cleaner
#                         purity = transform_reasons_to_impurity_result(
#                             analysis_result.call_graph_forest.forest[combined_node.scope.symbol.id].reasons,
#                         )
#
#                         if not combined_node.reasons.result:
#                             combined_node.reasons.result = purity
#                         else:
#                             combined_node.reasons.result = combined_node.reasons.result.update(purity)
#
#                         if reason.id not in purity_results:
#                             purity_results[reason.id] = purity
#                         else:
#                             purity_results[reason.id] = purity_results[reason.id].update(purity)
#
#                         if combined_node.scope.symbol.name not in purity_results:
#                             purity_results[combined_node.scope.symbol.id] = purity
#                         else:
#                             purity_results[combined_node.scope.symbol.id] = purity_results[
#                                 combined_node.scope.symbol.id
#                             ].update(purity)
#
#                     return purity_results[reason.id]
#
#         # Check if the node represents a self-defined function.
#         if (
#             isinstance(reason.function_scope, FunctionScope)
#             and isinstance(reason.function_scope.symbol.node, astroid.FunctionDef | astroid.Lambda)
#             and reason.id in analysis_result.call_graph_forest.forest
#         ):
#             # Check if the function does not call other functions (it is a leaf),
#             # therefore is is possible to check its (reasons for) impurity directly.
#             # Also check that all children are already handled (have a result).
#             if analysis_result.call_graph_forest.forest[reason.id].is_leaf() or all(
#                 c.reasons.result for c in analysis_result.call_graph_forest.forest[reason.id].children if not c.is_builtin
#             ):
#                 purity_self_defined: PurityResult = Pure()
#                 if analysis_result.call_graph_forest.forest[reason.id].reasons:
#                     purity_self_defined = transform_reasons_to_impurity_result(
#                         analysis_result.call_graph_forest.forest[reason.id].reasons,
#                     )
#
#                 # If a result was propagated from the children,
#                 # it needs to be kept and updated with more reasons if the function itself has more reasons.
#                 if (
#                     analysis_result.call_graph_forest.get_graph(reason.id).reasons.result is None
#                 ):  # TODO: this should never happen - check that and remove if statement -> this does happen... but it works
#                     purity_results[reason.id] = purity_self_defined
#                 else:
#                     purity_results[reason.id] = purity_results[reason.id].update(purity_self_defined)
#
#                 # Store the results in the forest, this also deals as a flag to indicate that the result is already computed completely.
#                 analysis_result.call_graph_forest.get_graph(reason.id).reasons.result = purity_results[reason.id]
#
#                 return purity_results[reason.id]
#             else:
#                 return purity_results[reason.id]
#
#     except KeyError:
#         raise KeyError(f"Function {reason.id} not found in function_references") from None
#
#
# # TODO: [Refactor] make this return a PurityResult??
# # TODO: add statement, that adds the result to the purity_results dict before returning
# def get_purity_of_child(
#     child: NewCallGraphNode,
#     reason: Reasons,
#     analysis_result: ModuleAnalysisResult,
#     purity_results: dict[NodeID, PurityResult],
# ) -> None:
#     """
#     Get the purity of a child node.
#
#     Given a child node, this function handles the purity of the child node.
#
#     Parameters
#     ----------
#     child: CallGraphNode
#         The child node to process.
#     reason : Reasons
#         The node to process containing the raw reasons for impurity collected.
#     analysis_result : ModuleAnalysisResult
#         The result of the analysis of the module.
#     purity_results : dict[NodeID, PurityResult]
#         The function ids as keys and purity results of the functions as values.
#         Since the collection runs recursively, pass them as a parameter to check for already determined results.
#     """
#     child_name = child.scope.symbol.name
#     child_id = child.scope.symbol.id
#
#     if isinstance(child.scope.symbol, BuiltinOpen):
#         purity_result_child = check_open_like_functions(child.scope.symbol.call)
#     elif child_name in BUILTIN_FUNCTIONS:
#         purity_result_child = BUILTIN_FUNCTIONS[child_name]
#     elif child_name in analysis_result.classes:
#         if child.reasons.calls:
#             init_fun_id = calc_node_id(
#                 child.reasons.calls.pop().node,
#             )  # TODO: make sure that there is only one call in the set of the class def reasons object
#             purity_result_child = process_node(
#                 analysis_result.raw_reasons[init_fun_id],
#                 analysis_result,
#                 purity_results,
#             )
#         else:
#             purity_result_child = Pure()
#     else:
#         purity_result_child = process_node(
#             analysis_result.raw_reasons[child_id],
#             analysis_result,
#             purity_results,
#         )
#
#     # Add the result to the child node in the call graph
#     if not child.is_builtin:
#         analysis_result.call_graph_forest.get_graph(child_id).reasons.result = purity_result_child
#     # If a result for the child was found, propagate it to the parent.
#     if purity_result_child and reason.function_scope is not None:
#         function_node = reason.function_scope.symbol.id
#         if function_node not in purity_results:
#             purity_results[function_node] = purity_result_child
#         else:
#             purity_results[function_node] = purity_results[function_node].update(purity_result_child)
#
#
# def transform_reasons_to_impurity_result(
#     reasons: Reasons,
# ) -> PurityResult:
#     """
#     Transform the reasons for impurity to an impurity result.
#
#     Given a Reasons object and a dict of references,
#     this function transforms the collected reasons from a Reasons object to a set of ImpurityReasons.
#
#     Parameters
#     ----------
#     reasons : Reasons
#         The node to process containing the raw reasons for impurity collected.
#
#     Returns
#     -------
#     ImpurityReason
#         The impurity result of the function (Pure, Impure or Unknown).
#
#     """
#     impurity_reasons: set[ImpurityReason] = set()
#
#     if not reasons:
#         return Pure()
#     else:
#         if reasons.writes_to:
#             for write in reasons.writes_to:
#                 # Write is of the correct type since only the correct type is added to the set.
#                 impurity_reasons.add(NonLocalVariableWrite(write))
#
#         if reasons.reads_from:
#             for read in reasons.reads_from:
#                 # Read is of the correct type since only the correct type is added to the set.
#                 impurity_reasons.add(NonLocalVariableRead(read))
#
#         if impurity_reasons:
#             return Impure(impurity_reasons)
#         return Pure()


class PurityAnalyzer:
    """
    The PurityAnalyzer class.

    This class is used to analyze the purity of a given module.
    It uses the infer_purity function to determine the purity of the functions in a module.

    Attributes
    ----------
    call_graph_forest : CallGraphForest
        The call graph forest of the module.
    purity_results : dict[NodeID, PurityResult]
        The purity results of the functions in the module.
    decombinded_nodes : dict[NodeID, NewCallGraphNode]
        If the module has cycles, they will be found by the CallGraphBuilder and combined to a single node.
        Since these combined nodes are not part of the module but needed for the analysis,
        their purity results will be propagated to the original nodes during the analysis.
        This attribute stores the original nodes inside after the combined node was analyzed.
    """

    def __init__(self, code: str) -> None:
        """
        Initialize the PurityAnalyzer.

        Parameters
        ----------
        code : str
            The source code of the module.
        """
        self.call_graph_forest: CallGraphForest = resolve_references(code).call_graph_forest
        self.purity_results: dict[NodeID, PurityResult] = {}
        self.decombinded_nodes: dict[NodeID, NewCallGraphNode] = {}
        self.purity_cache_imported_modules: dict[NodeID, dict[NodeID, PurityResult]] = {}

        if self.call_graph_forest:
            self._analyze_purity()
        else:
            raise ValueError("The call graph forest is empty.")

    @staticmethod
    def _handle_open_like_functions(call: astroid.Call) -> PurityResult:
        """Check open-like function for impurity.

        This includes functions like open, read, readline, readlines, write, writelines.

        Parameters
        ----------
        call: astrid.Call
            The call to check.

        Returns
        -------
        PurityResult
            The purity result of the function.

        """
        if not isinstance(call, astroid.Call):
            raise TypeError(f"Expected astroid.Call, got {call.__class__.__name__}") from None

        func_ref_node_func_name = call.func.attrname if isinstance(call.func, astroid.Attribute) else call.func.name

        # Check if the function is open
        if func_ref_node_func_name == "open":
            open_mode_str = "r"
            open_mode = None

            # Check if a mode is set and if the value is a string literal
            if len(call.args) >= 2 and isinstance(call.args[1], astroid.Const):
                if call.args[1].value in OPEN_MODES:
                    open_mode_str = call.args[1].value
            # Exclude the case where the mode is a variable since it cannot be determined in this case,
            # therefore, set it to be the worst case (read and write).
            elif len(call.args) == 2 and not isinstance(call.args[1], astroid.Const):
                open_mode = OpenMode.READ_WRITE

            # Check if the file name is a variable or a string literal
            file_var = call.args[0].name if isinstance(call.args[0], astroid.Name) else None
            file_str = call.args[0].value if not file_var else None

            # The file name is a variable
            if file_var:
                open_mode = open_mode or OPEN_MODES[open_mode_str]
                return Impure({FileRead(ParameterAccess(file_var))} if open_mode is OpenMode.READ
                              else {FileWrite(ParameterAccess(file_var))} if open_mode is OpenMode.WRITE
                else {FileRead(ParameterAccess(file_var)), FileWrite(ParameterAccess(file_var))})

            # The file name is a string literal
            elif file_str:
                open_mode = OPEN_MODES[open_mode_str]
                return Impure({FileRead(StringLiteral(file_str))} if open_mode is OpenMode.READ
                              else {FileWrite(StringLiteral(file_str))} if open_mode is OpenMode.WRITE
                else {FileRead(StringLiteral(file_str)), FileWrite(StringLiteral(file_str))})
        else:
            return Pure()

    def _get_impurity_result(self, reasons: Reasons) -> PurityResult:
        """
        Get the reasons for impurity from the reasons.

        Given a Reasons object, this function transforms the collected reasons
        from a Reasons object to a set of ImpurityReason and returns a PurityResult.
        If any ImpurityReason is found in the reasons, the function returns an Impure result.
        If no ImpurityReason is found, the function returns a Pure result.
        If any unknown calls are found, the function returns an Unknown result.

        Parameters
        ----------
        reasons : Reasons
            The node to process containing the raw reasons for impurity collected.

        Returns
        -------
        ImpurityReason
            The impurity result of the function (Pure, Impure or Unknown).
        """
        impurity_reasons: set[ImpurityReason] = set()

        # If no reasons are found, the function is pure.
        if not reasons.reads_from and not reasons.writes_to and not reasons.unknown_calls:
            return Pure()

        # Check if the function has any non-local variable writes.
        if reasons.writes_to:
            for write in reasons.writes_to:
                impurity_reasons.add(NonLocalVariableWrite(write))

        # Check if the function has any non-local variable reads.
        if reasons.reads_from:
            for read in reasons.reads_from:
                # Check if the read reads from an imported module.
                if isinstance(read, Import):
                    if read.inferred_node:
                        # If the inferred node is a function, it must be analyzed to determine its purity.
                        if isinstance(read.inferred_node, astroid.FunctionDef):
                            impurity_reasons.add(UnknownCall(CallOfFunction(call=read.call,
                                                                            inferred_def=read.inferred_node)))
                        elif isinstance(read.inferred_node, astroid.ClassDef):
                            impurity_reasons.add(UnknownCall(ClassInit(call=read.call,
                                                                       inferred_def=read.inferred_node)))
                        # If the inferred node is a module, it will not count towards the impurity of the function.
                        # If this was added, nearly anything would be impure.
                        # Also, since the imported symbols are analyzed in much more detail, this can be omitted.
                        elif isinstance(read.inferred_node, astroid.Module):
                            pass
                        # Default case for symbols that could not be inferred.
                        else:  # TODO: what type of nodes are allowed here?
                            impurity_reasons.add(NonLocalVariableRead(read))
                    else:
                        raise ValueError(f"Imported node {read.name} has no inferred node.") from None

                else:
                    impurity_reasons.add(NonLocalVariableRead(read))

        # TODO: remove safe infer (after new call graph is implemented)
        if reasons.unknown_calls:
            # for unknown_call in reasons.unknown_calls:
            #     # Make sure there is no AttributeError because of the inconsistent names in the astroid API.
            #     if isinstance(unknown_call.node.func, astroid.Attribute):
            #         unknown_call_func_name = unknown_call.node.func.attrname
            #     else:
            #         unknown_call_func_name = unknown_call.node.func.name
            #
            #     if reasons.function_scope is None:
            #         print(reasons)
            #
            #     inferred_result = safe_infer(unknown_call.node.func)
            #     # print(inferred_result)
            #
            #     if reasons.id in self.call_graph_forest.forest:
            #         graph = self.call_graph_forest.get_graph(reasons.id)
            #         # Check if the unknown call is a call of a parameter of that function.
            #         if unknown_call_func_name in graph.symbol:  # TODO: get parameters
            #             impurity_reasons.add(CallOfParameter(ParameterAccess(unknown_call_func_name)))
            #
            #         # The unknown call is a call of a function that is not defined in the module.
            #         # In this case, the function can either be a builtin function (which is not in the builtin dir)
            #         # or an imported function from another module.
            #         elif inferred_result and isinstance(inferred_result, astroid.FunctionDef):
            #             impurity_reasons.add(
            #                 UnknownCall(CallOfFunction(call=unknown_call, inferred_def=inferred_result)))
            #         elif inferred_result and isinstance(inferred_result, astroid.ClassDef):
            #             impurity_reasons.add(
            #                 UnknownCall(ClassInit(call=unknown_call, inferred_def=inferred_result)))
            #         else:
            #             impurity_reasons.add(UnknownCall(CallOfFunction(unknown_call)))
            print("ERROR")
        if impurity_reasons:
            return Impure(impurity_reasons)
        return Pure()

    def _process_imported_node(self, imported_node: ImportedCallGraphNode) -> PurityResult:
        """Process an imported node.

        Since imported nodes are not part of the module, they need to be analyzed separately.
        Therefore, the inferred node of the imported node is analyzed to determine its purity.
        If the module can be determined, a purity analysis is run on the imported module.
        If the module cannot be determined,
        or the function def is not found inside the module, the function is impure.
        Since it is possible that a module is used more than once,
        the results are cached after the first time analyzing the module.

        Parameters
        ----------
        imported_node : ImportedCallGraphNode
            The imported node to process.

        Returns
        -------
        PurityResult
            The purity result of the imported node.
        """
        imported_module = imported_node.symbol.inferred_node.root()
        if not isinstance(imported_module, astroid.Module):
            return Impure({UnknownCall(CallOfFunction(imported_node.symbol.call))})
        imported_module_id = calc_node_id(imported_module)
        inferred_node_id = calc_node_id(imported_node.symbol.inferred_node)

        # Check the cache for the purity results of the imported module and return the result for the imported node.
        if (imported_module_id in self.purity_cache_imported_modules
            and inferred_node_id in self.purity_cache_imported_modules[imported_module_id]
        ):
            return self.purity_cache_imported_modules[imported_module_id].get(inferred_node_id)

        # Get the source code of the imported module and the purity result for all functions of that module.
        source_code = imported_module.as_string()
        all_purity_result = infer_purity(source_code)

        # Save the purity results for the imported module in the cache.
        self.purity_cache_imported_modules[imported_module_id] = all_purity_result

        # In some cases, the inferred_node does not have any line number since astroid sometimes doesn't return it.
        # Therefore the correct function def cannot be found in the result.
        # In this case the fallback is to return an unknown call.
        # TODO: we could however find it and store it by its name. (This would find multiple tho) LARS
        if inferred_node_id in all_purity_result:
            return all_purity_result[inferred_node_id]
        else:
            return Impure({UnknownCall(CallOfFunction(call=imported_node.symbol.call,
                                                      inferred_def=imported_node.symbol.inferred_node))})

    def _process_node(self, node: NewCallGraphNode) -> PurityResult:
        """Process a node in the call graph.

        Process a node in the call graph to determine the purity of the function.
        Therefore, recursively process the children of the node (if any) and propagate the results afterward.
        First check if the purity of the function is already determined.
        Works with builtin functions and combined function nodes.

        Parameters
        ----------
        node : NewCallGraphNode
            The node to process.

        Returns
        -------
        PurityResult
            The purity result of the function node (combined with the results of its children).
        """
        # Check the forest if the purity of the function is already determined
        if node.is_inferred():
            # The purity of the function is determined already.
            return node.reasons.result

        # Check if the node is a builtin function.
        if isinstance(node.symbol, Builtin | BuiltinOpen):
            if isinstance(node.symbol, BuiltinOpen):
                return self._handle_open_like_functions(node.symbol.call)
            else:
                return BUILTIN_FUNCTIONS[node.symbol.name]

        # The purity of the node is not determined yet, but the node has children.
        # Check their purity first and propagate the results afterward.
        if not node.is_leaf():
            purity_result_children: PurityResult = Pure()
            for child in node.children.values():
                # Check imported nodes separately.
                if isinstance(child, ImportedCallGraphNode):
                    purity_result_child = self._process_imported_node(child)
                # Check combined nodes separately.
                elif isinstance(child, CombinedCallGraphNode):
                    purity_result_child = self._process_node(child)
                    self.decombinded_nodes.update(child.decombine())
                else:
                    purity_result_child = self._process_node(child)
                # Combine the reasons of all children.
                purity_result_children = purity_result_children.update(purity_result_child)

            node.reasons.result = self._get_impurity_result(node.reasons)
            # if node.reasons.result is None:
            #     print(node.reasons)
            node.reasons.result = node.reasons.result.update(purity_result_children)

        # The purity of the node is not determined yet, and it has no children.
        # Therefore, it is possible to check its (reasons for) impurity directly.
        # TODO: what about combined nodes here? Add testcase for that!
        else:
            node.reasons.result = self._get_impurity_result(node.reasons)

        return node.reasons.result

    def _analyze_purity(self) -> None:
        """
        Analyze the purity of the module.

        While traversing the forest, it saves the purity results in the purity_results attribute.
        """
        for graph in self.call_graph_forest.forest.values():
            if isinstance(graph, CombinedCallGraphNode):
                self._process_node(graph)
                self.decombinded_nodes.update(graph.decombine())
            elif isinstance(graph, ImportedCallGraphNode):
                pass
            elif isinstance(graph, NewCallGraphNode) and not isinstance(graph.symbol.node, astroid.ClassDef):
                self.purity_results[graph.symbol.id] = self._process_node(graph)

        if self.decombinded_nodes:
            for graph_id, graph in self.decombinded_nodes.items():
                self.purity_results[graph_id] = graph.reasons.result


def infer_purity(code: str) -> dict[NodeID, PurityResult]:
    """
    Infer the purity of functions.

    Given the code of a module, this function infers the purity of the functions inside a module.
    It uses the PurityAnalyzer to determine the purity of the functions in a module.

    Parameters
    ----------
    code : str
        The source code of the module.

    Returns
    -------
    purity_results : dict[NodeID, PurityResult]
        The purity results of the functions in the module.
        Keys are the node ids, values are the purity results.
    """
    return PurityAnalyzer(code).purity_results


def get_purity_results(
    # package: str,
    src_dir_path: Path,
) -> APIPurity:
    """Get the purity results of a package.

    This function is the entry to the purity analysis of a package.
    It iterates over all modules in the package and infers the purity of the functions in the modules.

    Parameters
    ----------
    src_dir_path : Path
       The path of the source directory of the package.

    Returns
    -------
    APIPurity
        The purity results of the package.
    """
    modules = list(src_dir_path.glob("**/*.py"))
    package_purity = APIPurity()

    for module in modules:
        with module.open("r") as file:
            code = file.read()
            # TODO: add logging infos!
            # TODO: add module_name and path to astroid.parse?
            # TODO: remove test files? -> yes
            # TODO: what about modules with the same name in different directories? -> see api
            module_purity_results = infer_purity(code)
            # TODO: do we want the function name or the function def node as result? -> NodeID
            #  if we want the name we need to use ID or else functions with the same name will be lost
            # TODO: do we want to differentiate between classes -> hierarchical result with classes
            module_purity_results_str = {func_id.__str__(): value for func_id, value in module_purity_results.items()}

        package_purity.purity_results[module.name] = module_purity_results_str

    return package_purity
