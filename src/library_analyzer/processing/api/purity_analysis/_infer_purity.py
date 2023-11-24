from __future__ import annotations

from enum import Enum, auto

import astroid

from library_analyzer.processing.api.purity_analysis import calc_node_id
from library_analyzer.processing.api.purity_analysis.model import (
    FileWrite,
    ImpurityReason,
    StringLiteral,
    NonLocalVariableWrite,
    NodeID,
    PurityResult,
    Impure,
    Pure,
    ReferenceNode,
    FunctionReference,
    Builtin,
    Reasons,
    CallGraphForest, GlobalVariable, ClassVariable, InstanceVariable, NonLocalVariableRead, FileRead,
)

# TODO: check these for correctness and add reasons for impurity
BUILTIN_FUNCTIONS = {  # all errors and warnings are pure
    "ArithmeticError": Pure(),
    "AssertionError": Pure(),
    "AttributeError": Pure(),
    "BaseException": Impure([]),
    "BaseExceptionGroup": Impure([]),
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
    "Ellipsis": Impure([]),
    "EncodingWarning": Pure(),
    "EnvironmentError": Pure(),
    "Exception": Impure([]),
    "ExceptionGroup": Impure([]),
    "False": Impure([]),
    "FileExistsError": Pure(),
    "FileNotFoundError": Pure(),
    "FloatingPointError": Pure(),
    "FutureWarning": Pure(),
    "GeneratorExit": Impure([]),
    "IOError": Pure(),
    "ImportError": Pure(),
    "ImportWarning": Pure(),
    "IndentationError": Pure(),
    "IndexError": Pure(),
    "InterruptedError": Pure(),
    "IsADirectoryError": Pure(),
    "KeyError": Pure(),
    "KeyboardInterrupt": Impure([]),
    "LookupError": Pure(),
    "MemoryError": Pure(),
    "ModuleNotFoundError": Pure(),
    "NameError": Pure(),
    "None": Impure([]),
    "NotADirectoryError": Pure(),
    "NotImplemented": Impure([]),
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
    "StopAsyncIteration": Impure([]),
    "StopIteration": Impure([]),
    "SyntaxError": Pure(),
    "SyntaxWarning": Pure(),
    "SystemError": Pure(),
    "SystemExit": Impure([]),
    "TabError": Pure(),
    "TimeoutError": Pure(),
    "True": Impure([]),
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
    "__build_class__": Impure([]),
    "__debug__": Impure([]),
    "__doc__": Impure([]),
    "__import__": Impure([]),
    "__loader__": Impure([]),
    "__name__": Impure([]),
    "__package__": Impure([]),
    "__spec__": Impure([]),
    "abs": Pure(),
    "aiter": Impure([]),  # May raise exceptions or interact with external resources
    "all": Pure(),
    "anext": Impure([]),  # May raise exceptions or interact with external resources
    "any": Pure(),
    "ascii": Pure(),
    "bin": Pure(),
    "bool": Pure(),
    "breakpoint": Impure([]),  # Debugger-related, doesn't affect program behavior
    "bytearray": Impure([]),  # Can be modified
    "bytes": Impure([]),  # Can be modified
    "callable": Pure(),
    "chr": Pure(),
    "classmethod": Pure(),
    "compile": Impure([]),  # Can execute arbitrary code
    "complex": Pure(),
    "copyright": Impure([]),  # May interact with external resources
    "credits": Impure([]),  # May interact with external resources
    "delattr": Impure([]),  # Can modify objects
    "dict": Impure([]),  # Can be modified
    "dir": Impure([]),  # May interact with external resources
    "divmod": Pure(),
    "enumerate": Pure(),
    "eval": Impure([]),  # Can execute arbitrary code
    "exec": Impure([]),  # Can execute arbitrary code
    "exit": Impure([]),  # Exits the program
    "filter": Pure(),
    "float": Pure(),
    "format": Impure([]),  # Can produce variable output
    "frozenset": Pure(),
    "getattr": Impure([]),  # Can raise exceptions or interact with external resources
    "globals": Impure([]),  # May interact with external resources
    "hasattr": Pure(),
    "hash": Pure(),
    "help": Impure([]),  # May interact with external resources
    "hex": Pure(),
    "id": Pure(),
    "input": Impure([FileRead(StringLiteral("stdin"))]),  # Reads user input
    "int": Pure(),
    "isinstance": Pure(),
    "issubclass": Pure(),
    "iter": Pure(),
    "len": Pure(),
    "license": Impure([]),  # May interact with external resources
    "list": Impure([]),  # Can be modified
    "locals": Impure([]),  # May interact with external resources
    "map": Pure(),
    "max": Pure(),
    "memoryview": Impure([]),  # Can be modified
    "min": Pure(),
    "next": Impure([]),  # May raise exceptions or interact with external resources
    "object": Pure(),
    "oct": Pure(),
    "open": Impure([]),  # Can interact with external resources (write and read)
    "ord": Pure(),
    "pow": Pure(),
    "print": Impure([FileWrite(StringLiteral("stdout"))]),
    "property": Pure(),
    "quit": Impure([]),  # Exits the program
    "range": Pure(),
    "repr": Pure(),
    "reversed": Pure(),
    "round": Pure(),
    "set": Impure([]),  # Can be modified
    "setattr": Impure([]),  # Can modify objects
    "slice": Pure(),
    "sorted": Impure([]),  # Can produce variable output
    "staticmethod": Pure(),
    "str": Impure([]),  # Can be modified
    "sum": Pure(),
    "super": Impure([]),  # Can interact with classes
    "tuple": Impure([]),  # Can be modified
    "type": Pure(),
    "vars": Impure([]),  # May interact with external resources
    "zip": Pure(),
}
PURITY_CACHE: dict[str, PurityResult] = {}

# class OpenMode(Enum):
#     READ = auto()
#     WRITE = auto()
#     READ_WRITE = auto()
#
#
# def determine_open_mode(args: list[str]) -> OpenMode:
#     write_mode = {"w", "wb", "a", "ab", "x", "xb", "wt", "at", "xt"}
#     read_mode = {"r", "rb", "rt"}
#     read_and_write_mode = {
#         "r+",
#         "rb+",
#         "w+",
#         "wb+",
#         "a+",
#         "ab+",
#         "x+",
#         "xb+",
#         "r+t",
#         "rb+t",
#         "w+t",
#         "wb+t",
#         "a+t",
#         "ab+t",
#         "x+t",
#         "xb+t",
#         "r+b",
#         "rb+b",
#         "w+b",
#         "wb+b",
#         "a+b",
#         "ab+b",
#         "x+b",
#         "xb+b",
#     }
#     if len(args) == 1:
#         return OpenMode.READ
#
#     mode = args[1]
#     if isinstance(mode, astroid.Const):
#         mode = mode.value
#
#     if mode in read_mode:
#         return OpenMode.READ
#     if mode in write_mode:
#         return OpenMode.WRITE
#     if mode in read_and_write_mode:
#         return OpenMode.READ_WRITE
#
#     raise ValueError(f"{mode} is not a valid mode for the open function")
#
#
# def check_builtin_function(
#     node: astroid.NodeNG,
#     key: str,
#     value: str | None = None,
#     is_var: bool = False,
# ) -> list[ImpurityReason]:
#     if is_var:
#         if key == "open":
#             open_mode = determine_open_mode(node.args)
#             if open_mode == OpenMode.WRITE:
#                 return [ExternalWrite(Reference(value))]
#
#             if open_mode == OpenMode.READ:
#                 return [ExternalRead(Reference(value))]
#
#             if open_mode == OpenMode.READ_WRITE:
#                 return [ExternalRead(Reference(value)), ExternalWrite(Reference(value))]
#
#     elif isinstance(value, str):
#         if key == "open":
#             open_mode = determine_open_mode(node.args)
#             if open_mode == OpenMode.WRITE:  # write mode
#                 return [ExternalWrite(StringLiteral(value))]
#
#             if open_mode == OpenMode.READ:  # read mode
#                 return [ExternalRead(StringLiteral(value))]
#
#             if open_mode == OpenMode.READ_WRITE:  # read and write mode
#                 return [ExternalRead(StringLiteral(value)), ExternalWrite(StringLiteral(value))]
#
#         raise TypeError(f"Unknown builtin function {key}")
#
#     if key in ("read", "readline", "readlines"):
#         return [InternalRead(Reference(node.as_string()))]
#     if key in ("write", "writelines"):
#         return [InternalWrite(Reference(node.as_string()))]
#
#     raise TypeError(f"Unknown builtin function {key}")
#
#


# print(): Used to print objects to the standard output device.
# open(): Used to open files for reading, writing, or appending.
# read(): Reads the content of a file.
# write(): Writes data to a file.
# close(): Closes the opened file.
# seek(): Moves the file pointer to a specific position in the file.
# tell(): Returns the current file pointer position.
# readline(): Reads a single line from a file.
# readlines(): Reads all lines from a file into a list.
# writelines(): Writes a list of lines to a file.
# flush(): Flushes the internal buffer to the file.
# with: Provides a context manager for file operations, ensuring the file is properly closed.


def infer_purity_new(references: list[ReferenceNode], function_references: dict[str, Reasons], call_graph: CallGraphForest) -> dict[astroid.FunctionDef, list[PurityResult]]:
    global BUILTIN_FUNCTIONS
    purity_results: dict[astroid.FunctionDef, list[PurityResult]] = {}  # We use astroid.FunctionDef as a key so we can access the node later

    references = {
        reference.node.func.name if isinstance(reference.node, astroid.Call) else reference.node.name: reference
        for reference in references  # TODO: MemberAccessTarget and MemberAccessValue are not handled here
    }  # TODO: return a dict of references instead of a list in resolve_references

    # for reference in references.values():
    #     # Guard clause for non-function calls: We only want to analyze function calls
    #     if not isinstance(reference.node, astroid.Call):
    #         continue
    #
    #     process_node(reference, references, call_graph, purity_results)

    for reasons in function_references.values():
        process_node(reasons, references, function_references, call_graph, purity_results)

    # Cleanup the purity results: We do not want the combined nodes in the results
    purity_results = {key: value for key, value in purity_results.items() if not isinstance(key, str)}

    return purity_results


# TODO: GET PURITY RESULTS FOR FUNCTIONS NOT FUNCTION CALLS (use function references to "store" results)
def process_node(reason: Reasons, references: dict[str, ReferenceNode], function_references: dict[str, Reasons], call_graph: CallGraphForest,
                 purity_results: dict[astroid.FunctionDef, list[PurityResult]]) -> list[PurityResult]:
    # Check the forest if the purity of the function is already determined
    if reason.function.name in call_graph.graphs.keys():
        if call_graph.get_graph(reason.function.name).reasons.result:
            purity_results[reason.function] = call_graph.get_graph(reason.function.name).reasons.result
            return purity_results[reason.function]

    # Check if the referenced function is a builtin function
    elif reason.function.name in BUILTIN_FUNCTIONS.keys():  # TODO: check if this works correctly in all cases
        # TODO: Deal with open - like functions separately to determine if they are read or write
        purity_results[reason.function] = BUILTIN_FUNCTIONS[reason.function.name]
        return purity_results[reason.function]

    # The purity of the function is not determined yet
    try:
        # Check if the function has any child nodes if so we need to check their purity first and propagate the results afterward
        # First we need to check if the reference actually is inside the call graph because it might be a builtin function or a combined node
        if reason.function.name in call_graph.graphs.keys():
            # If the node is part of the call graph, we can check if it has any children (called functions) = not a leaf
            if not call_graph.get_graph(reason.function.name).is_leaf():
                for child in call_graph.get_graph(reason.function.name).children:
                    # Check if we deal with a combined node (would throw a KeyError otherwise)
                    if not child.combined_node_names:
                        if child.data.symbol.name in BUILTIN_FUNCTIONS:
                            purity_results_child = BUILTIN_FUNCTIONS[child.data.symbol.name]
                        else:
                            purity_results_child = process_node(function_references[child.data.symbol.name], references, function_references, call_graph, purity_results)
                        if purity_results_child:
                            if reason.function not in purity_results.keys():
                                purity_results[reason.function] = purity_results_child
                            else:
                                purity_results[reason.function].extend(purity_results_child)
                    # The child is a combined node and therefore not part of the reference dict
                    else:
                        if reason.function not in purity_results.keys():
                            purity_results[reason.function] = child.reasons.result
                        else:
                            purity_results[reason.function].extend(child.reasons.result)

                # After all children are handled, we can propagate the purity of the called functions to the calling function
                call_graph.get_graph(reason.function.name).reasons.result = purity_results[reason.function]

        # If the node is not part of the call graph, we need to check if it is a combined node
        else:
            # Check if we deal with a combined node since they need to be handled differently
            combined_nodes = {node.data.symbol.name: node for node in call_graph.graphs.values() if node.combined_node_names}
            for combined_node in combined_nodes.values():
                if reason.function.name in combined_node.combined_node_names:
                    # Check if the purity result was already determined
                    if combined_node.reasons.result:
                        purity_results[reason.function] = combined_node.reasons.result
                        return purity_results[reason.function]
                    else:
                        reasons = transform_reasons_to_impurity_result(call_graph.graphs[combined_node.data.symbol.name].reasons, references)
                        if reasons:
                            purity = Impure(reasons)
                        else:
                            purity = Pure()

                        combined_node.reasons.result = purity
                        purity_results[reason.function] = purity
                        purity_results[combined_node.data.symbol.name] = purity
                        return purity_results[reason.function]

        # Check if we deal with a self-defined function
        if isinstance(reason.function, astroid.FunctionDef) and reason.function.name in call_graph.graphs.keys():
            # Check if the function does not call other functions (it is a leaf), we can check its (reasons for) impurity directly
            if call_graph.graphs[reason.function.name].is_leaf():
                if call_graph.graphs[reason.function.name].reasons:
                    reasons = transform_reasons_to_impurity_result(call_graph.graphs[reason.function.name].reasons, references)
                    if reasons:
                        purity = Impure(reasons)
                    else:
                        purity = Pure()

                # Store the results in the forest, this also deals as a flag to indicate that the result is already computed completely
                call_graph.get_graph(reason.function.name).reasons.result = purity

                purity_results[reason.function] = purity

                return purity_results[reason.function]

    except KeyError:
        raise KeyError(f"Function {reason.function.name} not found in function_references")


def transform_reasons_to_impurity_result(reasons: Reasons, references: dict[str, ReferenceNode]) -> list[ImpurityReason]:
    impurity_reasons: list[ImpurityReason] = []  # TODO: LARS should this be a set, since we dont need to know how many times a reference is accessed - if it is impure it stays impure

    if not reasons:
        return []
    else:
        if reasons.writes:
            for write in reasons.writes:
                write_ref = references[write.node.name]
                for sym_ref in write_ref.referenced_symbols:
                    if isinstance(sym_ref, GlobalVariable | ClassVariable | InstanceVariable):
                        impurity_reasons.append(NonLocalVariableWrite(sym_ref))
                    else:
                        raise TypeError(f"Unknown symbol reference type: {sym_ref.__class__.__name__}")
        if reasons.reads:
            for read in reasons.reads:
                read_ref = references[read.node.name]
                for sym_ref in read_ref.referenced_symbols:
                    if isinstance(sym_ref, GlobalVariable | ClassVariable | InstanceVariable):
                        impurity_reasons.append(NonLocalVariableRead(sym_ref))
                    else:
                        raise TypeError(f"Unknown symbol reference type: {sym_ref.__class__.__name__}")

        return impurity_reasons
