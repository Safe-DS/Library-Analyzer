from __future__ import annotations

from types import NoneType

import astroid

from library_analyzer.processing.api.purity_analysis.model import (
    FileWrite,
    ImpurityReason,
    StringLiteral,
    NonLocalVariableWrite,
    PurityResult,
    Impure,
    Pure,
    ReferenceNode,
    FunctionReference,
    Reasons,
    CallGraphForest,
    GlobalVariable,
    ClassVariable,
    InstanceVariable,
    NonLocalVariableRead,
    FileRead,
    OpenMode,
    ParameterAccess
)

# TODO: check these for correctness and add reasons for impurity
BUILTIN_FUNCTIONS = {  # all errors and warnings are pure
    "ArithmeticError": Pure(),
    "AssertionError": Pure(),
    "AttributeError": Pure(),
    "BaseException": Impure({}),
    "BaseExceptionGroup": Impure({}),
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
    "Ellipsis": Impure({}),
    "EncodingWarning": Pure(),
    "EnvironmentError": Pure(),
    "Exception": Impure({}),
    "ExceptionGroup": Impure({}),
    "False": Impure({}),
    "FileExistsError": Pure(),
    "FileNotFoundError": Pure(),
    "FloatingPointError": Pure(),
    "FutureWarning": Pure(),
    "GeneratorExit": Impure({}),
    "IOError": Pure(),
    "ImportError": Pure(),
    "ImportWarning": Pure(),
    "IndentationError": Pure(),
    "IndexError": Pure(),
    "InterruptedError": Pure(),
    "IsADirectoryError": Pure(),
    "KeyError": Pure(),
    "KeyboardInterrupt": Impure({}),
    "LookupError": Pure(),
    "MemoryError": Pure(),
    "ModuleNotFoundError": Pure(),
    "NameError": Pure(),
    "None": Impure({}),
    "NotADirectoryError": Pure(),
    "NotImplemented": Impure({}),
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
    "StopAsyncIteration": Impure({}),
    "StopIteration": Impure({}),
    "SyntaxError": Pure(),
    "SyntaxWarning": Pure(),
    "SystemError": Pure(),
    "SystemExit": Impure({}),
    "TabError": Pure(),
    "TimeoutError": Pure(),
    "True": Impure({}),
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
    "__build_class__": Impure({}),
    "__debug__": Impure({}),
    "__doc__": Impure({}),
    "__import__": Impure({}),
    "__loader__": Impure({}),
    "__name__": Impure({}),
    "__package__": Impure({}),
    "__spec__": Impure({}),
    "abs": Pure(),
    "aiter": Impure({}),  # May raise exceptions or interact with external resources
    "all": Pure(),
    "anext": Impure({}),  # May raise exceptions or interact with external resources
    "any": Pure(),
    "ascii": Pure(),
    "bin": Pure(),
    "bool": Pure(),
    "breakpoint": Impure({}),  # Debugger-related, doesn't affect program behavior
    "bytearray": Impure({}),  # Can be modified
    "bytes": Impure({}),  # Can be modified
    "callable": Pure(),
    "chr": Pure(),
    "classmethod": Pure(),
    "compile": Impure({}),  # Can execute arbitrary code
    "complex": Pure(),
    "delattr": Impure({}),  # Can modify objects
    "dict": Impure({}),  # Can be modified
    "dir": Impure({}),  # May interact with external resources
    "divmod": Pure(),
    "enumerate": Pure(),
    "eval": Impure({}),  # Can execute arbitrary code
    "exec": Impure({}),  # Can execute arbitrary code
    "filter": Pure(),
    "float": Pure(),
    "format": Impure({}),  # Can produce variable output
    "frozenset": Pure(),
    "getattr": Impure({}),  # Can raise exceptions or interact with external resources
    "globals": Impure({}),  # May interact with external resources
    "hasattr": Pure(),
    "hash": Pure(),
    "help": Impure({}),  # May interact with external resources
    "hex": Pure(),
    "id": Pure(),
    "input": Impure({FileRead(StringLiteral("stdin"))}),  # Reads user input
    "int": Pure(),
    "isinstance": Pure(),
    "issubclass": Pure(),
    "iter": Pure(),
    "len": Pure(),
    "list": Impure({}),  # Can be modified
    "locals": Impure({}),  # May interact with external resources
    "map": Pure(),
    "max": Pure(),
    "memoryview": Impure({}),  # Can be modified
    "min": Pure(),
    "next": Impure({}),  # May raise exceptions or interact with external resources
    "object": Pure(),
    "oct": Pure(),
    "open": Impure({}),  # Can interact with external resources (write and read)
    "ord": Pure(),
    "pow": Pure(),
    "print": Impure({FileWrite(StringLiteral("stdout"))}),
    "property": Pure(),
    "range": Pure(),
    "repr": Pure(),
    "reversed": Pure(),
    "round": Pure(),
    "set": Impure({}),  # Can be modified
    "setattr": Impure({}),  # Can modify objects
    "slice": Pure(),
    "sorted": Impure({}),  # Can produce variable output
    "staticmethod": Pure(),
    "str": Impure({}),  # Can be modified
    "sum": Pure(),
    "super": Impure({}),  # Can interact with classes
    "tuple": Impure({}),  # Can be modified
    "type": Pure(),
    "vars": Impure({}),  # May interact with external resources
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

# input(): Reads user input.
# print(): Used to print objects to the standard output device.
# open(): Used to open files for reading, writing, or appending.
# read(): Reads the content of a file.
# write(): Writes data to a file.
# close(): Closes the opened file.
# readline(): Reads a single line from a file.
# readlines(): Reads all lines from a file into a list.
# writelines(): Writes a list of lines to a file.
# with: Provides a context manager for file operations, ensuring the file is properly closed.


def check_open_like_functions(func_ref: FunctionReference) -> PurityResult:
    """
    Checks if the function is an open-like function.

    This includes functions like open, read, readline, readlines, write, writelines.

    Parameters
    ----------
        * func_ref: the function reference

    Returns
    -------
        * PurityResult: the purity result of the function

    """
    # Check if we deal with the open function
    if isinstance(func_ref.node, astroid.Call) and func_ref.node.func.name == "open":
        open_mode_str: str = "r"
        if len(func_ref.node.args) >= 2 and isinstance(func_ref.node.args[1], astroid.Const):
            if func_ref.node.args[1].value in OPEN_MODES.keys():
                open_mode_str = func_ref.node.args[1].value

        # We need to check if the file name is a variable or a string literal
        if isinstance(func_ref.node.args[0], astroid.Name):
            file_var = func_ref.node.args[0].name
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
            file_str = func_ref.node.args[0].value
            open_mode = OPEN_MODES[open_mode_str]
            match open_mode:
                case OpenMode.READ:
                    return Impure({FileRead(StringLiteral(file_str))})
                case OpenMode.WRITE:
                    return Impure({FileWrite(StringLiteral(file_str))})
                case OpenMode.READ_WRITE:
                    return Impure({FileRead(StringLiteral(file_str)), FileWrite(StringLiteral(file_str))})


def infer_purity(references: list[ReferenceNode], function_references: dict[str, Reasons],
                 call_graph: CallGraphForest) -> dict[astroid.FunctionDef, PurityResult]:
    """
    Infers the purity of functions.

    Given a list of references, a dict of function references and a callgraph, this function infers the purity of the functions inside a module.
    It therefore iterates over the function references and processes the nodes in the call graph.

    Parameters
    ----------
        * references: a list of all references in the module
        * function_references: a dict of function references
        * call_graph: the call graph of the module

    Returns
    -------
        * purity_results: a dict of the function nodes and purity results of the functions
    """

    global BUILTIN_FUNCTIONS
    purity_results: dict[
        astroid.FunctionDef, PurityResult] = {}  # We use astroid.FunctionDef instead of str as a key so we can access the node later

    references = {
        reference.node.func.name if isinstance(reference.node, astroid.Call) else reference.node.name: reference
        for reference in references  # TODO: MemberAccessTarget and MemberAccessValue are not handled here
    }  # TODO: return a dict of references instead of a list in resolve_references

    for reasons in function_references.values():
        process_node(reasons, references, function_references, call_graph, purity_results)

    # Cleanup the purity results: We do not want the combined nodes in the results
    purity_results = {key: value for key, value in purity_results.items() if not isinstance(key, str)}

    return purity_results


def process_node(reason: Reasons, references: dict[str, ReferenceNode], function_references: dict[str, Reasons],
                 call_graph: CallGraphForest,
                 purity_results: dict[astroid.FunctionDef, PurityResult]) -> PurityResult:
    """
    Processes a node in the call graph.

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
        * reason: the node to process containing the reasons for impurity collected
        * references: a dict of all references in the module
        * function_references: a dict of all function references in the module
        * call_graph: the call graph of the module
        * purity_results: a dict of the function nodes and purity results of the functions

    Returns
    -------
        * purity_results: a dict of the function nodes and purity results of the functions
    """

    # Check the forest if the purity of the function is already determined
    if reason.function.name in call_graph.graphs.keys():
        if call_graph.get_graph(reason.function.name).reasons.result:
            purity_results[reason.function] = call_graph.get_graph(reason.function.name).reasons.result
            return purity_results[reason.function]

    # Check if the referenced function is a builtin function
    elif reason.function.name in BUILTIN_FUNCTIONS.keys():  # TODO: check if this works correctly in all cases
        # TODO: Deal with open - like functions separately to determine if they are read or write
        if reason.function.name in ("open", "read", "readline", "readlines", "write", "writelines"):
            purity_results[reason.function] = check_open_like_functions(reason.get_call_by_name(reason.function.name))
        else:
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
                    # Check if we deal with a combined node (would throw a KeyError otherwise)  # TODO: check if combined nodes are still a problem with the new approach
                    if not child.combined_node_names:
                        if child.data.symbol.name in ("open", "read", "readline", "readlines", "write", "writelines"):
                            purity_result_child = check_open_like_functions(reason.get_call_by_name(child.data.symbol.name))
                        elif child.data.symbol.name in BUILTIN_FUNCTIONS.keys():
                            purity_result_child = BUILTIN_FUNCTIONS[child.data.symbol.name]
                        else:
                            purity_result_child = process_node(function_references[child.data.symbol.name], references,
                                                               function_references, call_graph, purity_results)
                        if purity_result_child:
                            if reason.function not in purity_results.keys():
                                purity_results[reason.function] = purity_result_child
                            else:
                                purity_results[reason.function] = purity_results[reason.function].update(
                                    purity_result_child)
                    # The child is a combined node and therefore not part of the reference dict
                    else:
                        if reason.function not in purity_results.keys():
                            purity_results[reason.function] = child.reasons.result
                        else:
                            purity_results[reason.function] = purity_results[reason.function].update(
                                child.reasons.result)

                # After all children are handled, we can propagate the purity of the called functions to the calling function
                call_graph.get_graph(reason.function.name).reasons.result = purity_results[reason.function]

        # If the node is not part of the call graph, we need to check if it is a combined node
        else:
            # Check if we deal with a combined node since they need to be handled differently
            combined_nodes = {node.data.symbol.name: node for node in call_graph.graphs.values() if
                              node.combined_node_names}
            for combined_node in combined_nodes.values():
                if reason.function.name in combined_node.combined_node_names:
                    # Check if the purity result was already determined
                    if combined_node.reasons.result:
                        purity_results[reason.function] = combined_node.reasons.result
                        return purity_results[reason.function]
                    else:
                        reasons = transform_reasons_to_impurity_result(
                            call_graph.graphs[combined_node.data.symbol.name].reasons, references)
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
            # also check that all children are handled (have a result)
            if call_graph.graphs[reason.function.name].is_leaf() or all(
                c.reasons.result for c in call_graph.graphs[reason.function.name].children if
                c.data.symbol.name not in BUILTIN_FUNCTIONS.keys()):
                purity: PurityResult = Pure()
                if call_graph.graphs[reason.function.name].reasons:
                    reasons = transform_reasons_to_impurity_result(call_graph.graphs[reason.function.name].reasons,
                                                                   references)
                    if reasons:
                        purity = Impure(reasons)

                # If a result was propagated from the children, it needs to be kept and updated with more reasons if the function itself has more reasons
                if isinstance(call_graph.get_graph(reason.function.name).reasons.result,
                              NoneType):  # TODO: this should never happen - check that and remove if statement
                    purity_results[reason.function] = purity
                else:
                    purity_results[reason.function] = purity_results[reason.function].update(purity)

                # Store the results in the forest, this also deals as a flag to indicate that the result is already computed completely
                call_graph.get_graph(reason.function.name).reasons.result = purity_results[reason.function]

                return purity_results[reason.function]
            else:
                return purity_results[reason.function]

    except KeyError:
        raise KeyError(f"Function {reason.function.name} not found in function_references")


# TODO: this is not working correctly: whenever a variable is referenced, it is marked as read/written if its is not inside the current function
def transform_reasons_to_impurity_result(reasons: Reasons, references: dict[str, ReferenceNode]) -> set[ImpurityReason]:
    """
    Transforms the reasons for impurity to an impurity result.

    Given a Reasons object and a dict of references,
    this function transforms the collected reasons from a Reasons object to a set of ImpurityReasons.

    Parameters
    ----------
        * reasons: the reasons for impurity
        * references: a dict of all references in the module

    Returns
    -------
        * impurity_reasons: a set of impurity reasons

    """
    impurity_reasons: set[ImpurityReason] = set()

    if not reasons:
        return impurity_reasons
    else:
        if reasons.writes:
            for write in reasons.writes:
                write_ref = references[write.node.name]
                for sym_ref in write_ref.referenced_symbols:
                    if isinstance(sym_ref, GlobalVariable | ClassVariable | InstanceVariable):
                        impurity_reasons.add(NonLocalVariableWrite(sym_ref))
                    else:
                        raise TypeError(f"Unknown symbol reference type: {sym_ref.__class__.__name__}")
        if reasons.reads:
            for read in reasons.reads:
                read_ref = references[read.node.name]
                for sym_ref in read_ref.referenced_symbols:
                    if isinstance(sym_ref, GlobalVariable | ClassVariable | InstanceVariable):
                        impurity_reasons.add(NonLocalVariableRead(sym_ref))
                    else:
                        raise TypeError(f"Unknown symbol reference type: {sym_ref.__class__.__name__}")

        return impurity_reasons
