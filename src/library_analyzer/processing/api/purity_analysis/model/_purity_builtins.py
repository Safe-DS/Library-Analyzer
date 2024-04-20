import astroid

from library_analyzer.processing.api.purity_analysis.model import (
    ClassScope,
    ClassVariable,
    FileRead,
    FileWrite,
    GlobalVariable,
    Impure,
    NodeID,
    NonLocalVariableRead,
    NonLocalVariableWrite,
    OpenMode,
    Pure,
    PurityResult,
    StringLiteral,
    UnknownSymbol,
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
    "False": Pure(),
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
    "True": Pure(),
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
    "aiter": Pure(),
    "all": Pure(),
    "anext": Pure(),
    "any": Pure(),
    "ascii": Pure(),
    "bin": Pure(),
    "bool": Pure(),
    "breakpoint": Impure(
        {
            NonLocalVariableRead(UnknownSymbol()),
            NonLocalVariableWrite(UnknownSymbol()),
            FileRead(StringLiteral("UNKNOWN")),
            FileWrite(StringLiteral("UNKNOWN")),
        },
    ),
    "bytearray": Pure(),
    "bytes": Pure(),
    "callable": Pure(),
    "chr": Pure(),
    "classmethod": Pure(),
    "compile": Impure(
        {
            NonLocalVariableRead(UnknownSymbol()),
            NonLocalVariableWrite(UnknownSymbol()),
            FileRead(StringLiteral("UNKNOWN")),
            FileWrite(StringLiteral("UNKNOWN")),
        },
    ),  # Can execute arbitrary code
    "complex": Pure(),
    "delattr": Impure(
        {
            NonLocalVariableRead(UnknownSymbol()),
            NonLocalVariableWrite(UnknownSymbol()),
        },
    ),  # Can modify objects
    "dict": Pure(),
    "dir": Pure(),
    "divmod": Pure(),
    "enumerate": Pure(),
    "eval": Impure(
        {
            NonLocalVariableRead(UnknownSymbol()),
            NonLocalVariableWrite(UnknownSymbol()),
            FileRead(StringLiteral("UNKNOWN")),
            FileWrite(StringLiteral("UNKNOWN")),
        },
    ),  # Can execute arbitrary code
    "exec": Impure(
        {
            NonLocalVariableRead(UnknownSymbol()),
            NonLocalVariableWrite(UnknownSymbol()),
            FileRead(StringLiteral("UNKNOWN")),
            FileWrite(StringLiteral("UNKNOWN")),
        },
    ),  # Can execute arbitrary code
    "filter": Pure(),
    "float": Pure(),
    "format": Pure(),
    "frozenset": Pure(),
    "getattr": Impure(
        {
            NonLocalVariableRead(UnknownSymbol()),
        },
    ),  # Can raise exceptions or interact with external resources
    "globals": Impure(
        {
            NonLocalVariableRead(UnknownSymbol()),
            NonLocalVariableWrite(UnknownSymbol()),
        },
    ),  # May interact with external resources
    "hasattr": Impure(
        {
            NonLocalVariableRead(UnknownSymbol()),
        },
    ),  # Calls the getattr function
    "hash": Pure(),
    "help": Impure({FileWrite(StringLiteral("stdout"))}),  # Interacts with external resources
    "hex": Pure(),
    "id": Pure(),
    "input": Impure({FileRead(StringLiteral("stdin"))}),  # Reads user input
    "int": Pure(),
    "isinstance": Pure(),
    "issubclass": Pure(),
    "iter": Pure(),
    "len": Pure(),
    "list": Pure(),
    "locals": Impure(
        {
            NonLocalVariableRead(UnknownSymbol()),
            NonLocalVariableWrite(UnknownSymbol()),
        },
    ),  # May interact with external resources
    "map": Pure(),
    "max": Pure(),
    "memoryview": Pure(),
    "min": Pure(),
    "next": Pure(),
    "object": Pure(),
    "oct": Pure(),
    "ord": Pure(),
    "pow": Pure(),
    "print": Impure({FileWrite(StringLiteral("stdout"))}),
    "property": Pure(),
    "range": Pure(),
    "repr": Pure(),
    "reversed": Pure(),
    "round": Pure(),
    "set": Pure(),
    "setattr": Impure(
        {
            NonLocalVariableRead(UnknownSymbol()),
            NonLocalVariableWrite(UnknownSymbol()),
        },
    ),  # Can modify objects
    "slice": Pure(),
    "sorted": Pure(),
    "staticmethod": Pure(),
    "str": Pure(),
    "sum": Pure(),
    "super": Pure(),
    "tuple": Pure(),
    "type": Pure(),
    "vars": Impure(
        {
            NonLocalVariableRead(UnknownSymbol()),
            NonLocalVariableWrite(UnknownSymbol()),
        },
    ),  # May interact with external resources
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


BUILTIN_CLASSSCOPES = {
    "BaseException": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="BaseException"), NodeID("BUILTIN", "BaseException", 859, 0), "BaseException",
        ),
        [],
        None,
        {
            "add_note": [
                ClassVariable(
                    astroid.FunctionDef(name="add_note"),
                    NodeID("BUILTIN", "add_note", 861, 4),
                    "add_note",
                    astroid.ClassDef(name="BaseException"),
                ),
            ],
            "with_traceback": [
                ClassVariable(
                    astroid.FunctionDef(name="with_traceback"),
                    NodeID("BUILTIN", "with_traceback", 868, 4),
                    "with_traceback",
                    astroid.ClassDef(name="BaseException"),
                ),
            ],
            "__delattr__": [
                ClassVariable(
                    astroid.FunctionDef(name="__delattr__"),
                    NodeID("BUILTIN", "__delattr__", 875, 4),
                    "__delattr__",
                    astroid.ClassDef(name="BaseException"),
                ),
            ],
            "__getattribute__": [
                ClassVariable(
                    astroid.FunctionDef(name="__getattribute__"),
                    NodeID("BUILTIN", "__getattribute__", 879, 4),
                    "__getattribute__",
                    astroid.ClassDef(name="BaseException"),
                ),
            ],
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 883, 4),
                    "__init__",
                    astroid.ClassDef(name="BaseException"),
                ),
            ],
            "__new__": [
                ClassVariable(
                    astroid.FunctionDef(name="__new__"),
                    NodeID("BUILTIN", "__new__", 886, 4),
                    "__new__",
                    astroid.ClassDef(name="BaseException"),
                ),
            ],
            "__reduce__": [
                ClassVariable(
                    astroid.FunctionDef(name="__reduce__"),
                    NodeID("BUILTIN", "__reduce__", 891, 4),
                    "__reduce__",
                    astroid.ClassDef(name="BaseException"),
                ),
            ],
            "__repr__": [
                ClassVariable(
                    astroid.FunctionDef(name="__repr__"),
                    NodeID("BUILTIN", "__repr__", 894, 4),
                    "__repr__",
                    astroid.ClassDef(name="BaseException"),
                ),
            ],
            "__setattr__": [
                ClassVariable(
                    astroid.FunctionDef(name="__setattr__"),
                    NodeID("BUILTIN", "__setattr__", 898, 4),
                    "__setattr__",
                    astroid.ClassDef(name="BaseException"),
                ),
            ],
            "__setstate__": [
                ClassVariable(
                    astroid.FunctionDef(name="__setstate__"),
                    NodeID("BUILTIN", "__setstate__", 902, 4),
                    "__setstate__",
                    astroid.ClassDef(name="BaseException"),
                ),
            ],
            "__str__": [
                ClassVariable(
                    astroid.FunctionDef(name="__str__"),
                    NodeID("BUILTIN", "__str__", 905, 4),
                    "__str__",
                    astroid.ClassDef(name="BaseException"),
                ),
            ],
        },
    ),
    "Exception": ClassScope(
        GlobalVariable(astroid.ClassDef(name="Exception"), NodeID("BUILTIN", "Exception", 925, 0), "Exception"),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 927, 4),
                    "__init__",
                    astroid.ClassDef(name="Exception"),
                ),
            ],
            "__new__": [
                ClassVariable(
                    astroid.FunctionDef(name="__new__"),
                    NodeID("BUILTIN", "__new__", 930, 4),
                    "__new__",
                    astroid.ClassDef(name="Exception"),
                ),
            ],
        },
    ),
    "ArithmeticError": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="ArithmeticError"), NodeID("BUILTIN", "ArithmeticError", 936, 0), "ArithmeticError",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 938, 4),
                    "__init__",
                    astroid.ClassDef(name="ArithmeticError"),
                ),
            ],
            "__new__": [
                ClassVariable(
                    astroid.FunctionDef(name="__new__"),
                    NodeID("BUILTIN", "__new__", 941, 4),
                    "__new__",
                    astroid.ClassDef(name="ArithmeticError"),
                ),
            ],
        },
    ),
    "AssertionError": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="AssertionError"), NodeID("BUILTIN", "AssertionError", 947, 0), "AssertionError",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 949, 4),
                    "__init__",
                    astroid.ClassDef(name="AssertionError"),
                ),
            ],
            "__new__": [
                ClassVariable(
                    astroid.FunctionDef(name="__new__"),
                    NodeID("BUILTIN", "__new__", 952, 4),
                    "__new__",
                    astroid.ClassDef(name="AssertionError"),
                ),
            ],
        },
    ),
    "AttributeError": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="AttributeError"), NodeID("BUILTIN", "AttributeError", 958, 0), "AttributeError",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 960, 4),
                    "__init__",
                    astroid.ClassDef(name="AttributeError"),
                ),
            ],
            "__str__": [
                ClassVariable(
                    astroid.FunctionDef(name="__str__"),
                    NodeID("BUILTIN", "__str__", 963, 4),
                    "__str__",
                    astroid.ClassDef(name="AttributeError"),
                ),
            ],
        },
    ),
    "BaseExceptionGroup": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="BaseExceptionGroup"),
            NodeID("BUILTIN", "BaseExceptionGroup", 975, 0),
            "BaseExceptionGroup",
        ),
        [],
        None,
        {
            "derive": [
                ClassVariable(
                    astroid.FunctionDef(name="derive"),
                    NodeID("BUILTIN", "derive", 977, 4),
                    "derive",
                    astroid.ClassDef(name="BaseExceptionGroup"),
                ),
            ],
            "split": [
                ClassVariable(
                    astroid.FunctionDef(name="split"),
                    NodeID("BUILTIN", "split", 980, 4),
                    "split",
                    astroid.ClassDef(name="BaseExceptionGroup"),
                ),
            ],
            "subgroup": [
                ClassVariable(
                    astroid.FunctionDef(name="subgroup"),
                    NodeID("BUILTIN", "subgroup", 983, 4),
                    "subgroup",
                    astroid.ClassDef(name="BaseExceptionGroup"),
                ),
            ],
            "__class_getitem__": [
                ClassVariable(
                    astroid.FunctionDef(name="__class_getitem__"),
                    NodeID("BUILTIN", "__class_getitem__", 986, 4),
                    "__class_getitem__",
                    astroid.ClassDef(name="BaseExceptionGroup"),
                ),
            ],
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 990, 4),
                    "__init__",
                    astroid.ClassDef(name="BaseExceptionGroup"),
                ),
            ],
            "__new__": [
                ClassVariable(
                    astroid.FunctionDef(name="__new__"),
                    NodeID("BUILTIN", "__new__", 993, 4),
                    "__new__",
                    astroid.ClassDef(name="BaseExceptionGroup"),
                ),
            ],
            "__str__": [
                ClassVariable(
                    astroid.FunctionDef(name="__str__"),
                    NodeID("BUILTIN", "__str__", 998, 4),
                    "__str__",
                    astroid.ClassDef(name="BaseExceptionGroup"),
                ),
            ],
        },
    ),
    "WindowsError": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="WindowsError"), NodeID("BUILTIN", "WindowsError", 1010, 0), "WindowsError",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 1012, 4),
                    "__init__",
                    astroid.ClassDef(name="WindowsError"),
                ),
            ],
            "__new__": [
                ClassVariable(
                    astroid.FunctionDef(name="__new__"),
                    NodeID("BUILTIN", "__new__", 1015, 4),
                    "__new__",
                    astroid.ClassDef(name="WindowsError"),
                ),
            ],
            "__reduce__": [
                ClassVariable(
                    astroid.FunctionDef(name="__reduce__"),
                    NodeID("BUILTIN", "__reduce__", 1020, 4),
                    "__reduce__",
                    astroid.ClassDef(name="WindowsError"),
                ),
            ],
            "__str__": [
                ClassVariable(
                    astroid.FunctionDef(name="__str__"),
                    NodeID("BUILTIN", "__str__", 1023, 4),
                    "__str__",
                    astroid.ClassDef(name="WindowsError"),
                ),
            ],
        },
    ),
    "BlockingIOError": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="BlockingIOError"), NodeID("BUILTIN", "BlockingIOError", 1055, 0), "BlockingIOError",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 1057, 4),
                    "__init__",
                    astroid.ClassDef(name="BlockingIOError"),
                ),
            ],
        },
    ),
    "ConnectionError": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="ConnectionError"), NodeID("BUILTIN", "ConnectionError", 1450, 0), "ConnectionError",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 1452, 4),
                    "__init__",
                    astroid.ClassDef(name="ConnectionError"),
                ),
            ],
        },
    ),
    "BrokenPipeError": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="BrokenPipeError"), NodeID("BUILTIN", "BrokenPipeError", 1456, 0), "BrokenPipeError",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 1458, 4),
                    "__init__",
                    astroid.ClassDef(name="BrokenPipeError"),
                ),
            ],
        },
    ),
    "BufferError": ClassScope(
        GlobalVariable(astroid.ClassDef(name="BufferError"), NodeID("BUILTIN", "BufferError", 1462, 0), "BufferError"),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 1464, 4),
                    "__init__",
                    astroid.ClassDef(name="BufferError"),
                ),
            ],
            "__new__": [
                ClassVariable(
                    astroid.FunctionDef(name="__new__"),
                    NodeID("BUILTIN", "__new__", 1467, 4),
                    "__new__",
                    astroid.ClassDef(name="BufferError"),
                ),
            ],
        },
    ),
    "Warning": ClassScope(
        GlobalVariable(astroid.ClassDef(name="Warning"), NodeID("BUILTIN", "Warning", 2688, 0), "Warning"),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 2690, 4),
                    "__init__",
                    astroid.ClassDef(name="Warning"),
                ),
            ],
            "__new__": [
                ClassVariable(
                    astroid.FunctionDef(name="__new__"),
                    NodeID("BUILTIN", "__new__", 2693, 4),
                    "__new__",
                    astroid.ClassDef(name="Warning"),
                ),
            ],
        },
    ),
    "BytesWarning": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="BytesWarning"), NodeID("BUILTIN", "BytesWarning", 2699, 0), "BytesWarning",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 2704, 4),
                    "__init__",
                    astroid.ClassDef(name="BytesWarning"),
                ),
            ],
            "__new__": [
                ClassVariable(
                    astroid.FunctionDef(name="__new__"),
                    NodeID("BUILTIN", "__new__", 2707, 4),
                    "__new__",
                    astroid.ClassDef(name="BytesWarning"),
                ),
            ],
        },
    ),
    "ChildProcessError": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="ChildProcessError"),
            NodeID("BUILTIN", "ChildProcessError", 2713, 0),
            "ChildProcessError",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 2715, 4),
                    "__init__",
                    astroid.ClassDef(name="ChildProcessError"),
                ),
            ],
        },
    ),
    "ConnectionAbortedError": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="ConnectionAbortedError"),
            NodeID("BUILTIN", "ConnectionAbortedError", 2903, 0),
            "ConnectionAbortedError",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 2905, 4),
                    "__init__",
                    astroid.ClassDef(name="ConnectionAbortedError"),
                ),
            ],
        },
    ),
    "ConnectionRefusedError": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="ConnectionRefusedError"),
            NodeID("BUILTIN", "ConnectionRefusedError", 2909, 0),
            "ConnectionRefusedError",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 2911, 4),
                    "__init__",
                    astroid.ClassDef(name="ConnectionRefusedError"),
                ),
            ],
        },
    ),
    "ConnectionResetError": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="ConnectionResetError"),
            NodeID("BUILTIN", "ConnectionResetError", 2915, 0),
            "ConnectionResetError",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 2917, 4),
                    "__init__",
                    astroid.ClassDef(name="ConnectionResetError"),
                ),
            ],
        },
    ),
    "DeprecationWarning": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="DeprecationWarning"),
            NodeID("BUILTIN", "DeprecationWarning", 2921, 0),
            "DeprecationWarning",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 2923, 4),
                    "__init__",
                    astroid.ClassDef(name="DeprecationWarning"),
                ),
            ],
            "__new__": [
                ClassVariable(
                    astroid.FunctionDef(name="__new__"),
                    NodeID("BUILTIN", "__new__", 2926, 4),
                    "__new__",
                    astroid.ClassDef(name="DeprecationWarning"),
                ),
            ],
        },
    ),
    "EncodingWarning": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="EncodingWarning"), NodeID("BUILTIN", "EncodingWarning", 3111, 0), "EncodingWarning",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 3113, 4),
                    "__init__",
                    astroid.ClassDef(name="EncodingWarning"),
                ),
            ],
            "__new__": [
                ClassVariable(
                    astroid.FunctionDef(name="__new__"),
                    NodeID("BUILTIN", "__new__", 3116, 4),
                    "__new__",
                    astroid.ClassDef(name="EncodingWarning"),
                ),
            ],
        },
    ),
    "EOFError": ClassScope(
        GlobalVariable(astroid.ClassDef(name="EOFError"), NodeID("BUILTIN", "EOFError", 3165, 0), "EOFError"),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 3167, 4),
                    "__init__",
                    astroid.ClassDef(name="EOFError"),
                ),
            ],
            "__new__": [
                ClassVariable(
                    astroid.FunctionDef(name="__new__"),
                    NodeID("BUILTIN", "__new__", 3170, 4),
                    "__new__",
                    astroid.ClassDef(name="EOFError"),
                ),
            ],
        },
    ),
    "ExceptionGroup": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="ExceptionGroup"), NodeID("BUILTIN", "ExceptionGroup", 3176, 0), "ExceptionGroup",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 3178, 4),
                    "__init__",
                    astroid.ClassDef(name="ExceptionGroup"),
                ),
            ],
        },
    ),
    "FileExistsError": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="FileExistsError"), NodeID("BUILTIN", "FileExistsError", 3186, 0), "FileExistsError",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 3188, 4),
                    "__init__",
                    astroid.ClassDef(name="FileExistsError"),
                ),
            ],
        },
    ),
    "FileNotFoundError": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="FileNotFoundError"),
            NodeID("BUILTIN", "FileNotFoundError", 3192, 0),
            "FileNotFoundError",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 3194, 4),
                    "__init__",
                    astroid.ClassDef(name="FileNotFoundError"),
                ),
            ],
        },
    ),
    "FloatingPointError": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="FloatingPointError"),
            NodeID("BUILTIN", "FloatingPointError", 3463, 0),
            "FloatingPointError",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 3465, 4),
                    "__init__",
                    astroid.ClassDef(name="FloatingPointError"),
                ),
            ],
            "__new__": [
                ClassVariable(
                    astroid.FunctionDef(name="__new__"),
                    NodeID("BUILTIN", "__new__", 3468, 4),
                    "__new__",
                    astroid.ClassDef(name="FloatingPointError"),
                ),
            ],
        },
    ),
    "FutureWarning": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="FutureWarning"), NodeID("BUILTIN", "FutureWarning", 3631, 0), "FutureWarning",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 3636, 4),
                    "__init__",
                    astroid.ClassDef(name="FutureWarning"),
                ),
            ],
            "__new__": [
                ClassVariable(
                    astroid.FunctionDef(name="__new__"),
                    NodeID("BUILTIN", "__new__", 3639, 4),
                    "__new__",
                    astroid.ClassDef(name="FutureWarning"),
                ),
            ],
        },
    ),
    "GeneratorExit": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="GeneratorExit"), NodeID("BUILTIN", "GeneratorExit", 3645, 0), "GeneratorExit",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 3647, 4),
                    "__init__",
                    astroid.ClassDef(name="GeneratorExit"),
                ),
            ],
            "__new__": [
                ClassVariable(
                    astroid.FunctionDef(name="__new__"),
                    NodeID("BUILTIN", "__new__", 3650, 4),
                    "__new__",
                    astroid.ClassDef(name="GeneratorExit"),
                ),
            ],
        },
    ),
    "ImportError": ClassScope(
        GlobalVariable(astroid.ClassDef(name="ImportError"), NodeID("BUILTIN", "ImportError", 3656, 0), "ImportError"),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 3658, 4),
                    "__init__",
                    astroid.ClassDef(name="ImportError"),
                ),
            ],
            "__reduce__": [
                ClassVariable(
                    astroid.FunctionDef(name="__reduce__"),
                    NodeID("BUILTIN", "__reduce__", 3661, 4),
                    "__reduce__",
                    astroid.ClassDef(name="ImportError"),
                ),
            ],
            "__str__": [
                ClassVariable(
                    astroid.FunctionDef(name="__str__"),
                    NodeID("BUILTIN", "__str__", 3664, 4),
                    "__str__",
                    astroid.ClassDef(name="ImportError"),
                ),
            ],
        },
    ),
    "ImportWarning": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="ImportWarning"), NodeID("BUILTIN", "ImportWarning", 3679, 0), "ImportWarning",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 3681, 4),
                    "__init__",
                    astroid.ClassDef(name="ImportWarning"),
                ),
            ],
            "__new__": [
                ClassVariable(
                    astroid.FunctionDef(name="__new__"),
                    NodeID("BUILTIN", "__new__", 3684, 4),
                    "__new__",
                    astroid.ClassDef(name="ImportWarning"),
                ),
            ],
        },
    ),
    "SyntaxError": ClassScope(
        GlobalVariable(astroid.ClassDef(name="SyntaxError"), NodeID("BUILTIN", "SyntaxError", 3690, 0), "SyntaxError"),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 3692, 4),
                    "__init__",
                    astroid.ClassDef(name="SyntaxError"),
                ),
            ],
            "__str__": [
                ClassVariable(
                    astroid.FunctionDef(name="__str__"),
                    NodeID("BUILTIN", "__str__", 3695, 4),
                    "__str__",
                    astroid.ClassDef(name="SyntaxError"),
                ),
            ],
        },
    ),
    "IndentationError": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="IndentationError"),
            NodeID("BUILTIN", "IndentationError", 3725, 0),
            "IndentationError",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 3727, 4),
                    "__init__",
                    astroid.ClassDef(name="IndentationError"),
                ),
            ],
        },
    ),
    "LookupError": ClassScope(
        GlobalVariable(astroid.ClassDef(name="LookupError"), NodeID("BUILTIN", "LookupError", 3731, 0), "LookupError"),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 3733, 4),
                    "__init__",
                    astroid.ClassDef(name="LookupError"),
                ),
            ],
            "__new__": [
                ClassVariable(
                    astroid.FunctionDef(name="__new__"),
                    NodeID("BUILTIN", "__new__", 3736, 4),
                    "__new__",
                    astroid.ClassDef(name="LookupError"),
                ),
            ],
        },
    ),
    "IndexError": ClassScope(
        GlobalVariable(astroid.ClassDef(name="IndexError"), NodeID("BUILTIN", "IndexError", 3742, 0), "IndexError"),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 3744, 4),
                    "__init__",
                    astroid.ClassDef(name="IndexError"),
                ),
            ],
            "__new__": [
                ClassVariable(
                    astroid.FunctionDef(name="__new__"),
                    NodeID("BUILTIN", "__new__", 3747, 4),
                    "__new__",
                    astroid.ClassDef(name="IndexError"),
                ),
            ],
        },
    ),
    "InterruptedError": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="InterruptedError"),
            NodeID("BUILTIN", "InterruptedError", 3753, 0),
            "InterruptedError",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 3755, 4),
                    "__init__",
                    astroid.ClassDef(name="InterruptedError"),
                ),
            ],
        },
    ),
    "IsADirectoryError": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="IsADirectoryError"),
            NodeID("BUILTIN", "IsADirectoryError", 3759, 0),
            "IsADirectoryError",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 3761, 4),
                    "__init__",
                    astroid.ClassDef(name="IsADirectoryError"),
                ),
            ],
        },
    ),
    "KeyboardInterrupt": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="KeyboardInterrupt"),
            NodeID("BUILTIN", "KeyboardInterrupt", 3765, 0),
            "KeyboardInterrupt",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 3767, 4),
                    "__init__",
                    astroid.ClassDef(name="KeyboardInterrupt"),
                ),
            ],
            "__new__": [
                ClassVariable(
                    astroid.FunctionDef(name="__new__"),
                    NodeID("BUILTIN", "__new__", 3770, 4),
                    "__new__",
                    astroid.ClassDef(name="KeyboardInterrupt"),
                ),
            ],
        },
    ),
    "KeyError": ClassScope(
        GlobalVariable(astroid.ClassDef(name="KeyError"), NodeID("BUILTIN", "KeyError", 3776, 0), "KeyError"),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 3778, 4),
                    "__init__",
                    astroid.ClassDef(name="KeyError"),
                ),
            ],
            "__str__": [
                ClassVariable(
                    astroid.FunctionDef(name="__str__"),
                    NodeID("BUILTIN", "__str__", 3781, 4),
                    "__str__",
                    astroid.ClassDef(name="KeyError"),
                ),
            ],
        },
    ),
    "MemoryError": ClassScope(
        GlobalVariable(astroid.ClassDef(name="MemoryError"), NodeID("BUILTIN", "MemoryError", 3997, 0), "MemoryError"),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 3999, 4),
                    "__init__",
                    astroid.ClassDef(name="MemoryError"),
                ),
            ],
            "__new__": [
                ClassVariable(
                    astroid.FunctionDef(name="__new__"),
                    NodeID("BUILTIN", "__new__", 4002, 4),
                    "__new__",
                    astroid.ClassDef(name="MemoryError"),
                ),
            ],
        },
    ),
    "ModuleNotFoundError": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="ModuleNotFoundError"),
            NodeID("BUILTIN", "ModuleNotFoundError", 4174, 0),
            "ModuleNotFoundError",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 4176, 4),
                    "__init__",
                    astroid.ClassDef(name="ModuleNotFoundError"),
                ),
            ],
        },
    ),
    "NameError": ClassScope(
        GlobalVariable(astroid.ClassDef(name="NameError"), NodeID("BUILTIN", "NameError", 4180, 0), "NameError"),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 4182, 4),
                    "__init__",
                    astroid.ClassDef(name="NameError"),
                ),
            ],
            "__str__": [
                ClassVariable(
                    astroid.FunctionDef(name="__str__"),
                    NodeID("BUILTIN", "__str__", 4185, 4),
                    "__str__",
                    astroid.ClassDef(name="NameError"),
                ),
            ],
        },
    ),
    "NotADirectoryError": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="NotADirectoryError"),
            NodeID("BUILTIN", "NotADirectoryError", 4194, 0),
            "NotADirectoryError",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 4196, 4),
                    "__init__",
                    astroid.ClassDef(name="NotADirectoryError"),
                ),
            ],
        },
    ),
    "RuntimeError": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="RuntimeError"), NodeID("BUILTIN", "RuntimeError", 4200, 0), "RuntimeError",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 4202, 4),
                    "__init__",
                    astroid.ClassDef(name="RuntimeError"),
                ),
            ],
            "__new__": [
                ClassVariable(
                    astroid.FunctionDef(name="__new__"),
                    NodeID("BUILTIN", "__new__", 4205, 4),
                    "__new__",
                    astroid.ClassDef(name="RuntimeError"),
                ),
            ],
        },
    ),
    "NotImplementedError": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="NotImplementedError"),
            NodeID("BUILTIN", "NotImplementedError", 4211, 0),
            "NotImplementedError",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 4213, 4),
                    "__init__",
                    astroid.ClassDef(name="NotImplementedError"),
                ),
            ],
            "__new__": [
                ClassVariable(
                    astroid.FunctionDef(name="__new__"),
                    NodeID("BUILTIN", "__new__", 4216, 4),
                    "__new__",
                    astroid.ClassDef(name="NotImplementedError"),
                ),
            ],
        },
    ),
    "OverflowError": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="OverflowError"), NodeID("BUILTIN", "OverflowError", 4222, 0), "OverflowError",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 4224, 4),
                    "__init__",
                    astroid.ClassDef(name="OverflowError"),
                ),
            ],
            "__new__": [
                ClassVariable(
                    astroid.FunctionDef(name="__new__"),
                    NodeID("BUILTIN", "__new__", 4227, 4),
                    "__new__",
                    astroid.ClassDef(name="OverflowError"),
                ),
            ],
        },
    ),
    "PendingDeprecationWarning": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="PendingDeprecationWarning"),
            NodeID("BUILTIN", "PendingDeprecationWarning", 4233, 0),
            "PendingDeprecationWarning",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 4238, 4),
                    "__init__",
                    astroid.ClassDef(name="PendingDeprecationWarning"),
                ),
            ],
            "__new__": [
                ClassVariable(
                    astroid.FunctionDef(name="__new__"),
                    NodeID("BUILTIN", "__new__", 4241, 4),
                    "__new__",
                    astroid.ClassDef(name="PendingDeprecationWarning"),
                ),
            ],
        },
    ),
    "PermissionError": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="PermissionError"), NodeID("BUILTIN", "PermissionError", 4247, 0), "PermissionError",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 4249, 4),
                    "__init__",
                    astroid.ClassDef(name="PermissionError"),
                ),
            ],
        },
    ),
    "ProcessLookupError": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="ProcessLookupError"),
            NodeID("BUILTIN", "ProcessLookupError", 4253, 0),
            "ProcessLookupError",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 4255, 4),
                    "__init__",
                    astroid.ClassDef(name="ProcessLookupError"),
                ),
            ],
        },
    ),
    "RecursionError": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="RecursionError"), NodeID("BUILTIN", "RecursionError", 4480, 0), "RecursionError",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 4482, 4),
                    "__init__",
                    astroid.ClassDef(name="RecursionError"),
                ),
            ],
            "__new__": [
                ClassVariable(
                    astroid.FunctionDef(name="__new__"),
                    NodeID("BUILTIN", "__new__", 4485, 4),
                    "__new__",
                    astroid.ClassDef(name="RecursionError"),
                ),
            ],
        },
    ),
    "ReferenceError": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="ReferenceError"), NodeID("BUILTIN", "ReferenceError", 4491, 0), "ReferenceError",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 4493, 4),
                    "__init__",
                    astroid.ClassDef(name="ReferenceError"),
                ),
            ],
            "__new__": [
                ClassVariable(
                    astroid.FunctionDef(name="__new__"),
                    NodeID("BUILTIN", "__new__", 4496, 4),
                    "__new__",
                    astroid.ClassDef(name="ReferenceError"),
                ),
            ],
        },
    ),
    "ResourceWarning": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="ResourceWarning"), NodeID("BUILTIN", "ResourceWarning", 4502, 0), "ResourceWarning",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 4504, 4),
                    "__init__",
                    astroid.ClassDef(name="ResourceWarning"),
                ),
            ],
            "__new__": [
                ClassVariable(
                    astroid.FunctionDef(name="__new__"),
                    NodeID("BUILTIN", "__new__", 4507, 4),
                    "__new__",
                    astroid.ClassDef(name="ResourceWarning"),
                ),
            ],
        },
    ),
    "RuntimeWarning": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="RuntimeWarning"), NodeID("BUILTIN", "RuntimeWarning", 4548, 0), "RuntimeWarning",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 4550, 4),
                    "__init__",
                    astroid.ClassDef(name="RuntimeWarning"),
                ),
            ],
            "__new__": [
                ClassVariable(
                    astroid.FunctionDef(name="__new__"),
                    NodeID("BUILTIN", "__new__", 4553, 4),
                    "__new__",
                    astroid.ClassDef(name="RuntimeWarning"),
                ),
            ],
        },
    ),
    "StopAsyncIteration": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="StopAsyncIteration"),
            NodeID("BUILTIN", "StopAsyncIteration", 4914, 0),
            "StopAsyncIteration",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 4916, 4),
                    "__init__",
                    astroid.ClassDef(name="StopAsyncIteration"),
                ),
            ],
            "__new__": [
                ClassVariable(
                    astroid.FunctionDef(name="__new__"),
                    NodeID("BUILTIN", "__new__", 4919, 4),
                    "__new__",
                    astroid.ClassDef(name="StopAsyncIteration"),
                ),
            ],
        },
    ),
    "StopIteration": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="StopIteration"), NodeID("BUILTIN", "StopIteration", 4925, 0), "StopIteration",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 4927, 4),
                    "__init__",
                    astroid.ClassDef(name="StopIteration"),
                ),
            ],
        },
    ),
    "SyntaxWarning": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="SyntaxWarning"), NodeID("BUILTIN", "SyntaxWarning", 5593, 0), "SyntaxWarning",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 5595, 4),
                    "__init__",
                    astroid.ClassDef(name="SyntaxWarning"),
                ),
            ],
            "__new__": [
                ClassVariable(
                    astroid.FunctionDef(name="__new__"),
                    NodeID("BUILTIN", "__new__", 5598, 4),
                    "__new__",
                    astroid.ClassDef(name="SyntaxWarning"),
                ),
            ],
        },
    ),
    "SystemError": ClassScope(
        GlobalVariable(astroid.ClassDef(name="SystemError"), NodeID("BUILTIN", "SystemError", 5604, 0), "SystemError"),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 5611, 4),
                    "__init__",
                    astroid.ClassDef(name="SystemError"),
                ),
            ],
            "__new__": [
                ClassVariable(
                    astroid.FunctionDef(name="__new__"),
                    NodeID("BUILTIN", "__new__", 5614, 4),
                    "__new__",
                    astroid.ClassDef(name="SystemError"),
                ),
            ],
        },
    ),
    "SystemExit": ClassScope(
        GlobalVariable(astroid.ClassDef(name="SystemExit"), NodeID("BUILTIN", "SystemExit", 5620, 0), "SystemExit"),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 5622, 4),
                    "__init__",
                    astroid.ClassDef(name="SystemExit"),
                ),
            ],
        },
    ),
    "TabError": ClassScope(
        GlobalVariable(astroid.ClassDef(name="TabError"), NodeID("BUILTIN", "TabError", 5630, 0), "TabError"),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 5632, 4),
                    "__init__",
                    astroid.ClassDef(name="TabError"),
                ),
            ],
        },
    ),
    "TimeoutError": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="TimeoutError"), NodeID("BUILTIN", "TimeoutError", 5636, 0), "TimeoutError",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 5638, 4),
                    "__init__",
                    astroid.ClassDef(name="TimeoutError"),
                ),
            ],
        },
    ),
    "TypeError": ClassScope(
        GlobalVariable(astroid.ClassDef(name="TypeError"), NodeID("BUILTIN", "TypeError", 5853, 0), "TypeError"),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 5855, 4),
                    "__init__",
                    astroid.ClassDef(name="TypeError"),
                ),
            ],
            "__new__": [
                ClassVariable(
                    astroid.FunctionDef(name="__new__"),
                    NodeID("BUILTIN", "__new__", 5858, 4),
                    "__new__",
                    astroid.ClassDef(name="TypeError"),
                ),
            ],
        },
    ),
    "UnboundLocalError": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="UnboundLocalError"),
            NodeID("BUILTIN", "UnboundLocalError", 5864, 0),
            "UnboundLocalError",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 5866, 4),
                    "__init__",
                    astroid.ClassDef(name="UnboundLocalError"),
                ),
            ],
        },
    ),
    "ValueError": ClassScope(
        GlobalVariable(astroid.ClassDef(name="ValueError"), NodeID("BUILTIN", "ValueError", 5870, 0), "ValueError"),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 5872, 4),
                    "__init__",
                    astroid.ClassDef(name="ValueError"),
                ),
            ],
            "__new__": [
                ClassVariable(
                    astroid.FunctionDef(name="__new__"),
                    NodeID("BUILTIN", "__new__", 5875, 4),
                    "__new__",
                    astroid.ClassDef(name="ValueError"),
                ),
            ],
        },
    ),
    "UnicodeError": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="UnicodeError"), NodeID("BUILTIN", "UnicodeError", 5881, 0), "UnicodeError",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 5883, 4),
                    "__init__",
                    astroid.ClassDef(name="UnicodeError"),
                ),
            ],
            "__new__": [
                ClassVariable(
                    astroid.FunctionDef(name="__new__"),
                    NodeID("BUILTIN", "__new__", 5886, 4),
                    "__new__",
                    astroid.ClassDef(name="UnicodeError"),
                ),
            ],
        },
    ),
    "UnicodeDecodeError": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="UnicodeDecodeError"),
            NodeID("BUILTIN", "UnicodeDecodeError", 5892, 0),
            "UnicodeDecodeError",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 5894, 4),
                    "__init__",
                    astroid.ClassDef(name="UnicodeDecodeError"),
                ),
            ],
            "__new__": [
                ClassVariable(
                    astroid.FunctionDef(name="__new__"),
                    NodeID("BUILTIN", "__new__", 5897, 4),
                    "__new__",
                    astroid.ClassDef(name="UnicodeDecodeError"),
                ),
            ],
            "__str__": [
                ClassVariable(
                    astroid.FunctionDef(name="__str__"),
                    NodeID("BUILTIN", "__str__", 5902, 4),
                    "__str__",
                    astroid.ClassDef(name="UnicodeDecodeError"),
                ),
            ],
        },
    ),
    "UnicodeEncodeError": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="UnicodeEncodeError"),
            NodeID("BUILTIN", "UnicodeEncodeError", 5923, 0),
            "UnicodeEncodeError",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 5925, 4),
                    "__init__",
                    astroid.ClassDef(name="UnicodeEncodeError"),
                ),
            ],
            "__new__": [
                ClassVariable(
                    astroid.FunctionDef(name="__new__"),
                    NodeID("BUILTIN", "__new__", 5928, 4),
                    "__new__",
                    astroid.ClassDef(name="UnicodeEncodeError"),
                ),
            ],
            "__str__": [
                ClassVariable(
                    astroid.FunctionDef(name="__str__"),
                    NodeID("BUILTIN", "__str__", 5933, 4),
                    "__str__",
                    astroid.ClassDef(name="UnicodeEncodeError"),
                ),
            ],
        },
    ),
    "UnicodeTranslateError": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="UnicodeTranslateError"),
            NodeID("BUILTIN", "UnicodeTranslateError", 5954, 0),
            "UnicodeTranslateError",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 5956, 4),
                    "__init__",
                    astroid.ClassDef(name="UnicodeTranslateError"),
                ),
            ],
            "__new__": [
                ClassVariable(
                    astroid.FunctionDef(name="__new__"),
                    NodeID("BUILTIN", "__new__", 5959, 4),
                    "__new__",
                    astroid.ClassDef(name="UnicodeTranslateError"),
                ),
            ],
            "__str__": [
                ClassVariable(
                    astroid.FunctionDef(name="__str__"),
                    NodeID("BUILTIN", "__str__", 5964, 4),
                    "__str__",
                    astroid.ClassDef(name="UnicodeTranslateError"),
                ),
            ],
        },
    ),
    "UnicodeWarning": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="UnicodeWarning"), NodeID("BUILTIN", "UnicodeWarning", 5985, 0), "UnicodeWarning",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 5990, 4),
                    "__init__",
                    astroid.ClassDef(name="UnicodeWarning"),
                ),
            ],
            "__new__": [
                ClassVariable(
                    astroid.FunctionDef(name="__new__"),
                    NodeID("BUILTIN", "__new__", 5993, 4),
                    "__new__",
                    astroid.ClassDef(name="UnicodeWarning"),
                ),
            ],
        },
    ),
    "UserWarning": ClassScope(
        GlobalVariable(astroid.ClassDef(name="UserWarning"), NodeID("BUILTIN", "UserWarning", 5999, 0), "UserWarning"),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 6001, 4),
                    "__init__",
                    astroid.ClassDef(name="UserWarning"),
                ),
            ],
            "__new__": [
                ClassVariable(
                    astroid.FunctionDef(name="__new__"),
                    NodeID("BUILTIN", "__new__", 6004, 4),
                    "__new__",
                    astroid.ClassDef(name="UserWarning"),
                ),
            ],
        },
    ),
    "ZeroDivisionError": ClassScope(
        GlobalVariable(
            astroid.ClassDef(name="ZeroDivisionError"),
            NodeID("BUILTIN", "ZeroDivisionError", 6010, 0),
            "ZeroDivisionError",
        ),
        [],
        None,
        {
            "__init__": [
                ClassVariable(
                    astroid.FunctionDef(name="__init__"),
                    NodeID("BUILTIN", "__init__", 6012, 4),
                    "__init__",
                    astroid.ClassDef(name="ZeroDivisionError"),
                ),
            ],
            "__new__": [
                ClassVariable(
                    astroid.FunctionDef(name="__new__"),
                    NodeID("BUILTIN", "__new__", 6015, 4),
                    "__new__",
                    astroid.ClassDef(name="ZeroDivisionError"),
                ),
            ],
        },
    ),
}

BUILTIN_SPECIALS = {
    "get": Pure(),  # dict
    "update": Pure(),  # dict, set
    "pop": Pure(),  # dict, list, set
    "popitem": Pure(),  # dict
    "clear": Pure(),  # dict, # list, set
    "copy": Pure(),  # dict, # list, set
    "fromkeys": Pure(),  # dict
    "items": Pure(),  # dict
    "keys": Pure(),  # dict
    "values": Pure(),  # dict
    "setdefault": Pure(),  # dict
    "append": Pure(),  # list
    "count": Pure(),  # list, str
    "extend": Pure(),  # list
    "index": Pure(),  # list, str
    "insert": Pure(),  # list
    "remove": Pure(),  # list, set
    "reverse": Pure(),  # list
    "sort": Pure(),  # list
    "add": Pure(),  # set
    "difference": Pure(),  # set
    "difference_update": Pure(),  # set
    "discard": Pure(),  # set
    "intersection": Pure(),  # set
    "intersection_update": Pure(),  # set
    "isdisjoint": Pure(),  # set
    "issubset": Pure(),  # set
    "issuperset": Pure(),  # set
    "symmetric_difference": Pure(),  # set
    "symmetric_difference_update": Pure(),  # set
    "union": Pure(),  # set
    "capitalize": Pure(),  # str
    "casefold": Pure(),  # str
    "center": Pure(),  # str
    "encode": Pure(),  # str
    "endswith": Pure(),  # str
    "expandtabs": Pure(),  # str
    "find": Pure(),  # str
    "format": Pure(),  # str
    "format_map": Pure(),  # str
    "isalnum": Pure(),  # str
    "isalpha": Pure(),  # str
    "isascii": Pure(),  # str
    "isdecimal": Pure(),  # str
    "isdigit": Pure(),  # str
    "isidentifier": Pure(),  # str
    "islower": Pure(),  # str
    "isnumeric": Pure(),  # str
    "isprintable": Pure(),  # str
    "isspace": Pure(),  # str
    "istitle": Pure(),  # str
    "isupper": Pure(),  # str
    "join": Pure(),  # str
    "ljust": Pure(),  # str
    "lower": Pure(),  # str
    "lstrip": Pure(),  # str
    "maketrans": Pure(),  # str
    "partition": Pure(),  # str
    "removeprefix": Pure(),  # str
    "removesuffix": Pure(),  # str
    "replace": Pure(),  # str
    "rfind": Pure(),  # str
    "rindex": Pure(),  # str
    "rjust": Pure(),  # str
    "rpartition": Pure(),  # str
    "rsplit": Pure(),  # str
    "rstrip": Pure(),  # str
    "split": Pure(),  # str
    "splitlines": Pure(),  # str
    "startswith": Pure(),  # str
    "strip": Pure(),  # str
    "swapcase": Pure(),  # str
    "title": Pure(),  # str
    "translate": Pure(),  # str
    "upper": Pure(),  # str
    "zfill": Pure(),  # str
    "GenericAlias": Pure(),
    "UnionType": Pure(),
    "EllipsisType": Pure(),
    "NoneType": Pure(),
    "NotImplementedType": Pure(),
}
