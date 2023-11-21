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
    CallGraphForest,
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
    "input": Impure([]),  # Reads user input
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

#
#
# class PurityHandler:
#     def __init__(self) -> None:
#         self.purity_reason: list[ImpurityReason] = []
#
#     def append_reason(self, reason: list[ImpurityReason]) -> None:
#         for r in reason:
#             self.purity_reason.append(r)
#
#     def enter_functiondef(self, node: astroid.FunctionDef) -> None:
#         # Handle the FunctionDef node here
#         pass  # Are we analyzing function defs within function defs? Yes, we are.
#
#     def enter_assign(self, node: astroid.Assign) -> None:
#         # Handle the Assign node here
#         if isinstance(node.value, astroid.Call):
#             pass
#         if isinstance(node.value, astroid.Const):
#             self.append_reason([InternalWrite(Reference(node.as_string()))])
#         else:  # default case
#             self.append_reason([InternalWrite(Reference(node.as_string()))])
#         # TODO: Assign node needs further analysis to determine if it is pure or impure
#
#     def enter_assignattr(self, node: astroid.AssignAttr) -> None:
#         # Handle the AssignAtr node here
#         self.append_reason([InternalWrite(Reference(node.as_string()))])
#         # TODO: AssignAttr node needs further analysis to determine if it is pure or impure
#
#     def enter_call(self, node: astroid.Call) -> None:
#         # Handle the Call node here
#         if isinstance(node.func, astroid.Attribute):
#             pass
#         elif isinstance(node.func, astroid.Name) and node.func.name in BUILTIN_FUNCTIONS:
#             value = node.args[0]
#             if isinstance(value, astroid.Name):
#                 impurity_indicator = check_builtin_function(node, node.func.name, value.name, is_var=True)
#                 self.append_reason(impurity_indicator)
#             else:
#                 impurity_indicator = check_builtin_function(node, node.func.name, value.value)
#                 self.append_reason(impurity_indicator)
#
#         self.append_reason([Call(Reference(node.as_string()))])
#         # TODO: Call node needs further analysis to determine if it is pure or impure
#
#     def enter_attribute(self, node: astroid.Attribute) -> None:
#         # Handle the Attribute node here
#         if isinstance(node.expr, astroid.Name):
#             if node.attrname in BUILTIN_FUNCTIONS:
#                 impurity_indicator = check_builtin_function(node, node.attrname)
#                 self.append_reason(impurity_indicator)
#         else:
#             self.append_reason([Call(Reference(node.as_string()))])
#
#
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
# def infer_purity(code: str) -> list[PurityInformation]:
#     purity_handler: PurityHandler = PurityHandler()
#     walker = ASTWalker(purity_handler)
#     functions = get_function_defs(code)
#     result = []
#     for function in functions:
#         walker.walk(function)
#         purity_result = determine_purity(purity_handler.purity_reason)
#         # if not isinstance(purity_result, DefinitelyPure):
#         result.append(generate_purity_information(function, purity_result))
#         purity_handler.purity_reason = []
#     return result
#
#
# def determine_purity(indicators: list[ImpurityIndicator]) -> PurityResult:
#     if len(indicators) == 0:
#         return DefinitelyPure()
#     if any(indicator.certainty == ImpurityCertainty.DEFINITELY_IMPURE for indicator in indicators):
#         return DefinitelyImpure(reasons=indicators)
#
#     return MaybeImpure(reasons=indicators)
#
#
# def get_function_defs(code: str) -> list[astroid.FunctionDef]:
#     try:
#         module = astroid.parse(code)
#     except SyntaxError as error:
#         raise ValueError("Invalid Python code") from error
#
#     function_defs = list[astroid.FunctionDef]()
#     for node in module.body:
#         if isinstance(node, astroid.FunctionDef):
#             function_defs.append(node)
#     return function_defs
#
#
# def extract_impurity_reasons(purity: PurityResult) -> list[ImpurityIndicator]:
#     if isinstance(purity, DefinitelyPure):
#         return []
#     return purity.reasons
#
#
# def generate_purity_information(function: astroid.FunctionDef, purity_result: PurityResult) -> PurityInformation:
#     function_id = calc_node_id(function)
#     reasons = extract_impurity_reasons(purity_result)
#     return PurityInformation(function_id, reasons)

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


def infer_purity_new(references: list[ReferenceNode], call_graph: CallGraphForest) -> dict[astroid.Call, PurityResult]:
    global BUILTIN_FUNCTIONS
    purity_results: dict[astroid.Call, PurityResult] = {}

    for reference in references:
        # guard clause for non function calls (should not happen)
        if not isinstance(reference.node, astroid.Call):
            continue

        # check if the purity of the function is already determined
        if reference.node.func.name in call_graph.graphs.keys():
            if call_graph.get_graph(reference.node.func.name).reasons.result:
                purity_results[reference.node] = call_graph.get_graph(symbol.node.name).reasons.result
                continue

        try:
            # Look at all function references and check their (reasons for) impurity
            for symbol in reference.referenced_symbols:
                # Check if we deal with a builtin function
                if isinstance(symbol, Builtin):
                    # If it is a builtin we can look up the impurity (reasons) directly
                    if reference.node.func.name in BUILTIN_FUNCTIONS.keys():
                        # call_graph.get_graph(reference.node.func.name).reasons.result = BUILTIN_FUNCTIONS[reference.node.func.name]
                        # TODO: do we want the builtins as nodes in the forest? -> if not how do we store their purity results?
                        #  right now we do not store them as calls because no nodes are created for them

                        # TODO: add checks for open - like functions to determine if they are read or write
                        purity_results[reference.node] = BUILTIN_FUNCTIONS[reference.node.func.name]

                # Check if we deal with a self defined function
                elif isinstance(symbol.node, astroid.FunctionDef) and symbol.node.name in call_graph.graphs.keys():
                    # check if the function calls other functions
                    if call_graph.graphs[symbol.node.name].is_leaf():
                        # if the function does not call other functions (it is a leaf), we can check its reasons for impurity directly
                        if call_graph.graphs[symbol.node.name].reasons:
                            reasons = transform_reasons_to_impurity_result(call_graph.graphs[symbol.node.name].reasons)
                            if reasons:
                                purity = Impure(reasons)
                            else:
                                purity = Pure()

                        # store the results in the forest, add a flag to the node to indicate that the result is already computed completely
                        call_graph.get_graph(reference.node.func.name).reasons.result = purity
                        # call_graph.get_graph(reference.node.func.name).is_done = True

                        purity_results[reference.node] = purity

                    # otherwise we need to calculate the purity of the called functions first
                    else:
                        # check if the purity of the called function is already determined
                        if call_graph.get_graph(symbol.node.name).reasons.result:
                            purity_results[reference.node] = call_graph.get_graph(symbol.node.name).reasons.result
                            continue
                        # if not, we need to calculate the purity of the called function first
                        else:
                            pass  # TODO: implement this recursively to deal with the children

        except KeyError:
            raise KeyError(f"Function {reference.node.func.name} not found in function_references")

    return purity_results


def transform_reasons_to_impurity_result(reasons: Reasons) -> list[ImpurityReason]:
    if not reasons:
        return []
    # TODO: transform reasons to impurity reason
