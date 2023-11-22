from dataclasses import dataclass

import astroid
import pytest

from library_analyzer.processing.api.purity_analysis import (
    # OpenMode,
    # determine_open_mode,
    # determine_purity,
    # extract_impurity_reasons,
    # infer_purity,
    resolve_references,
    infer_purity_new,
)
from library_analyzer.processing.api.purity_analysis.model import (
    ImpurityReason,
    Pure,
    PurityResult,
    NonLocalVariableRead,
    NonLocalVariableWrite,
    FileWrite,
    FileRead,
)


@dataclass
class SimpleImpure:
    reasons: list[str]


# @pytest.mark.parametrize(
#     ("args", "expected"),
#     [
#         (["test"], OpenMode.READ),
#         (["test", "r"], OpenMode.READ),
#         (["test", "rb"], OpenMode.READ),
#         (["test", "rt"], OpenMode.READ),
#         (["test", "r+"], OpenMode.READ_WRITE),
#         (["test", "w"], OpenMode.WRITE),
#         (["test", "wb"], OpenMode.WRITE),
#         (["test", "wt"], OpenMode.WRITE),
#         (["test", "w+"], OpenMode.READ_WRITE),
#         (["test", "x"], OpenMode.WRITE),
#         (["test", "xb"], OpenMode.WRITE),
#         (["test", "xt"], OpenMode.WRITE),
#         (["test", "x+"], OpenMode.READ_WRITE),
#         (["test", "a"], OpenMode.WRITE),
#         (["test", "ab"], OpenMode.WRITE),
#         (["test", "at"], OpenMode.WRITE),
#         (["test", "a+"], OpenMode.READ_WRITE),
#         (["test", "r+b"], OpenMode.READ_WRITE),
#         (["test", "w+b"], OpenMode.READ_WRITE),
#         (["test", "x+b"], OpenMode.READ_WRITE),
#         (["test", "a+b"], OpenMode.READ_WRITE),
#         (["test", "r+t"], OpenMode.READ_WRITE),
#         (["test", "w+t"], OpenMode.READ_WRITE),
#         (["test", "x+t"], OpenMode.READ_WRITE),
#         (["test", "a+t"], OpenMode.READ_WRITE),
#         (["test", "error"], ValueError),
#     ],
# )
# def test_determine_open_mode(args: list[str], expected: OpenMode) -> None:
#     if expected is ValueError:
#         with pytest.raises(ValueError, match="is not a valid mode for the open function"):
#             determine_open_mode(args)
#     else:
#         result = determine_open_mode(args)
#         assert result == expected
#
#
# @pytest.mark.parametrize(
#     ("code", "expected"),
#     [
#         (
#             """
#                 def fun1():
#                     open("test1.txt") # default mode: read only
#             """,
#             [ExternalRead(source=StringLiteral(value="test1.txt")), Call(expression=Reference(name="open('test1.txt')"))],
#         ),
#         (
#             """
#                 def fun2():
#                     open("test2.txt", "r") # read only
#             """,
#             [
#                 ExternalRead(source=StringLiteral(value="test2.txt")),
#                 Call(expression=Reference(name="open('test2.txt', 'r')")),
#             ],
#         ),
#         (
#             """
#                 def fun3():
#                     open("test3.txt", "w") # write only
#             """,
#             [
#                 ExternalWrite(source=StringLiteral(value="test3.txt")),
#                 Call(expression=Reference(name="open('test3.txt', 'w')")),
#             ],
#         ),
#         (
#             """
#                 def fun4():
#                     open("test4.txt", "a") # append
#             """,
#             [
#                 ExternalWrite(source=StringLiteral(value="test4.txt")),
#                 Call(expression=Reference(name="open('test4.txt', 'a')")),
#             ],
#         ),
#         (
#             """
#                 def fun5():
#                     open("test5.txt", "r+")  # read and write
#             """,
#             [
#                 ExternalRead(source=StringLiteral(value="test5.txt")),
#                 ExternalWrite(source=StringLiteral(value="test5.txt")),
#                 Call(expression=Reference(name="open('test5.txt', 'r+')")),
#             ],
#         ),
#         (
#             """
#                 def fun6():
#                     f = open("test6.txt") # default mode: read only
#                     f.read()
#             """,
#             [
#                 InternalWrite(expression=Reference(name="f = open('test6.txt')")),
#                 ExternalRead(source=StringLiteral(value="test6.txt")),
#                 Call(expression=Reference(name="open('test6.txt')")),
#                 Call(expression=Reference(name="f.read()")),
#                 InternalRead(expression=Reference(name="f.read")),
#             ],
#         ),
#         (
#             """
#                 def fun7():
#                     f = open("test7.txt") # default mode: read only
#                     f.readline([2])
#             """,
#             [
#                 InternalWrite(expression=Reference(name="f = open('test7.txt')")),
#                 ExternalRead(source=StringLiteral(value="test7.txt")),
#                 Call(expression=Reference(name="open('test7.txt')")),
#                 Call(expression=Reference(name="f.readline([2])")),
#                 InternalRead(expression=Reference(name="f.readline")),
#             ],
#         ),
#         (
#             """
#                 def fun8():
#                     f = open("test8.txt", "w") # write only
#                     f.write("message")
#             """,
#             [
#                 InternalWrite(expression=Reference(name="f = open('test8.txt', 'w')")),
#                 ExternalWrite(source=StringLiteral(value="test8.txt")),
#                 Call(expression=Reference(name="open('test8.txt', 'w')")),
#                 Call(expression=Reference(name="f.write('message')")),
#                 InternalWrite(expression=Reference(name="f.write")),
#             ],
#         ),
#         (
#             """
#                 def fun9():
#                     f = open("test9.txt", "w") # write only
#                     f.writelines(["message1", "message2"])
#             """,
#             [
#                 InternalWrite(expression=Reference(name="f = open('test9.txt', 'w')")),
#                 ExternalWrite(source=StringLiteral(value="test9.txt")),
#                 Call(expression=Reference(name="open('test9.txt', 'w')")),
#                 Call(expression=Reference(name="f.writelines(['message1', 'message2'])")),
#                 InternalWrite(expression=Reference(name="f.writelines")),
#             ],
#         ),
#         (
#             """
#                 def fun10():
#                     with open("test10.txt") as f: # default mode: read only
#                         f.read()
#             """,
#             [
#                 ExternalRead(source=StringLiteral(value="test10.txt")),
#                 Call(expression=Reference(name="open('test10.txt')")),
#                 Call(expression=Reference(name="f.read()")),
#                 InternalRead(expression=Reference(name="f.read")),
#             ],
#         ),
#         (
#             """
#                 def fun11(path11): # open with variable
#                     open(path11)
#             """,
#             [ExternalRead(source=Reference("path11")), Call(expression=Reference(name="open(path11)"))],  # ??
#         ),
#         (
#             """
#                 def fun12(path12): # open with variable write mode
#                     open(path12, "w")
#             """,
#             [ExternalWrite(source=Reference(name="path12")), Call(expression=Reference(name="open(path12, 'w')"))],  # ??
#         ),
#         (
#             """
#                 def fun13(path13): # open with variable write mode
#                     open(path13, "wb+")
#             """,
#             [
#                 ExternalRead(source=Reference(name="path13")),
#                 ExternalWrite(source=Reference(name="path13")),
#                 Call(expression=Reference(name="open(path13, 'wb+')")),
#             ],  # ??
#         ),
#         (
#             """
#                 def fun14(path14):
#                     with open(path14) as f:
#                         f.read()
#             """,
#             [
#                 ExternalRead(source=Reference("path14")),
#                 Call(expression=Reference(name="open(path14)")),
#                 Call(expression=Reference(name="f.read()")),
#                 InternalRead(expression=Reference(name="f.read")),
#             ],  # ??
#         ),
#         (
#             """
#                 def fun15(path15): # open with variable and wrong mode
#                     open(path15, "test")
#             """,
#             ValueError,
#         ),
#         (
#             """
#                 def fun16(): # this does not belong here but is needed for code coverage
#                     print("test")
#             """,
#             TypeError,
#         ),
#     ],
# )
# # TODO: test for wrong arguments and Errors
# def test_file_interaction(code: str, expected: list[ImpurityIndicator]) -> None:
#     if expected is ValueError:
#         with pytest.raises(ValueError, match="is not a valid mode for the open function"):
#             infer_purity(code)
#     elif expected is TypeError:
#         with pytest.raises(TypeError):
#             infer_purity(code)
#     else:
#         purity_info: list[PurityInformation] = infer_purity(code)
#         assert purity_info[0].reasons == expected


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (  # language=Python "Pure function"
            """
def fun():
    pass  # Pure

fun()
            """,  # language= None
            {"Call.fun.line5": Pure()},
        ),
        (  # language=Python "Pure function with parameter"
            """
def fun(x):
    return 2 * x  # Pure: VariableRead from LocalVariable

a = fun(1)
            """,  # language= None
            {"Call.fun.line5": Pure()},
        ),
        (  # language=Python "VariableWrite to LocalVariable"
            """
def fun():
    var1 = 2  # Pure: VariableWrite to LocalVariable
    return var1

a = fun()
            """,  # language= None
            {"Call.fun.line6": Pure()},
        ),
        (  # language=Python "VariableWrite to LocalVariable with parameter"
            """
def fun(x):
    var1 = x  # Pure: VariableWrite to LocalVariable
    return var1

a = fun(2)
            """,  # language= None
            {"Call.fun.line6": Pure()},
        ),
        (  # language=Python "VariableRead from LocalVariable"
            """
def fun():
    var1 = 1  # Pure: VariableRead from LocalVariable
    return var1

a = fun()
            """,  # language= None
            {"Call.fun.line6": Pure()},
        ),
        (  # language=Python "Call of Pure Function"
            """
def fun1():
    res = fun2()  # Pure: Call of Pure Function
    return res

def fun2():
    return 1  # Pure

a = fun1()
            """,  # language= None
            {"Call.fun1.line9": Pure(),
             "Call.fun2.line3": Pure()},
        ),
        (  # language=Python "Call of Pure Chain of Functions"
            """
def fun1():
    res = fun2()  # Pure: Call of Pure Function
    return res

def fun2():
    return fun3()  # Pure: Call of Pure Function

def fun3():
    return 1  # Pure

a = fun1()
            """,  # language= None
            {"Call.fun1.line12": Pure(),
             "Call.fun2.line3": Pure(),
             "Call.fun3.line7": Pure()},
        ),
        (  # language=Python "Call of Pure Chain of Functions with cycle - one entry point"
            """
def cycle1():
    cycle2()

def cycle2():
    cycle3()

def cycle3():
    cycle1()

def entry():
    cycle1()

entry()
            """,  # language= None
            {},  # TODO: LARS how should the results look here? do we want the functions inside of cycles to be returned
        ),
        (  # language=Python "Call of Pure Chain of Functions with cycle - direct entry"
            """
def fun1(count):
    if count > 0:
        fun2(count - 1)

def fun2(count):
    if count > 0:
        fun1(count - 1)

fun1(3)
            """,  # language= None
            {"Call.fun1.line8": Pure(),
             "Call.fun1.line10": Pure(),
             "Call.fun2.line4": Pure()},
        ),
        (  # language=Python "Call of Pure Builtin Function"
            """
def fun():
    res = range(2)  # Pure: Call of Pure Builtin Function and write to LocalVariable
    return res

a = fun()
            """,  # language= None
            {"Call.fun.line6": Pure()},  # TODO: LARS do we want builtins in the result? -> if not do a cleanup and remove them before returning the result
        ),
        (  # language=Python "Multiple Calls of same Pure function (Caching)"
            """
def fun1():
    return 1

a = fun1()
b = fun1()
c = fun1()
            """,  # language= None
            {"Call.fun1.line5": Pure(),
             "Call.fun1.line6": Pure(),
             "Call.fun1.line7": Pure()},  # TODO: LARS do we want to get multiple outputs for multiple calls - since the function is always pure/impure
        ),  # here the purity for fun1 can be cached for the other calls
    ],
    ids=[
        "pure function",
        "pure function with parameter",
        "VariableWrite to LocalVariable",
        "VariableWrite to LocalVariable with parameter",
        "VariableRead from LocalVariable",
        "Call of Pure Function",
        "Call of Pure Chain of Functions",
        "Call of Pure Chain of Functions with cycle - one entry point",
        "Call of Pure Chain of Functions with cycle - direct entry",
        "Call of Pure Builtin Function",
        "Multiple Calls of same Pure function (Caching)",
    ],  # TODO: ClassVariables, InstanceVariables,
)
def test_infer_purity_pure(code: str, expected: list[ImpurityReason]) -> None:
    references, function_references, call_graph = resolve_references(code)

    purity_results = infer_purity_new(references, call_graph)
    transformed_purity_results = {to_string_call(call): to_simple_result(purity_result) for call, purity_result in purity_results.items()}

    assert transformed_purity_results == expected


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (  # language=Python "SystemInteraction"
            """
def fun():
    print("text.txt")  # Impure: FileWrite

fun()
            """,  # language= None
            {"Call.fun.line5": SimpleImpure(["FileWrite.StringLiteral.stdout"])}
        ),
        (  # language=Python "SystemInteraction with parameter"
            """
def fun(pos_arg):
    print(pos_arg)  # Impure: FileWrite

fun(1)
            """,  # language= None
            {"Call.fun.line5": SimpleImpure(["FileWrite.StringLiteral.stdout"])}  # TODO: LARS  FileWrite.ParameterAccess.pos_arg ??
        ),
        (  # language=Python "SystemInteraction"
            """
def fun():
    open("text.txt")  # Impure: FileWrite

fun()
            """,  # language= None
            {"Call.fun.line5": SimpleImpure(["FileWrite.StringLiteral.text.txt"])}
        ),
        (  # language=Python "SystemInteraction with parameter"
            """
def fun(pos_arg):
    open(pos_arg)  # Impure: FileWrite

fun(1)
            """,  # language= None
            {"Call.fun.line5": SimpleImpure(["FileWrite.ParameterAccess.pos_arg"])}
        ),
        (  # language=Python "VariableWrite to GlobalVariable"
            """
var1 = 1
def fun():
    var1 = 2  # Impure: VariableWrite to GlobalVariable
    return var1

a = fun()
            """,  # language= None
            {"Call.fun.line7": SimpleImpure(["NonLocalVariableWrite.GlobalVariable.var1"])},
        ),
        (  # language=Python "VariableWrite to GlobalVariable with parameter"
            """
var1 = 1
def fun(x):
    var1 = x  # Impure: VariableWrite to GlobalVariable
    return var1

a = fun(2)
            """,  # language= None
            {"Call.fun.line7": SimpleImpure(["NonLocalVariableWrite.GlobalVariable.var1"])},
        ),
        (  # language=Python "VariableRead from GlobalVariable"
            """
var1 = 1
def fun():
    res = var1  # Impure: VariableRead from GlobalVariable
    return res

a = fun()
            """,  # language= None
            {"Call.fun.line7": SimpleImpure(["NonLocalVariableRead.GlobalVariable.var1"])}
        ),
        (  # language=Python "Call of Impure Function"
            """
var1 = 1
def fun1():
    res = fun2()  # Impure: Call of Impure Function
    return res

def fun2():
    global var1
    return var1  # Impure: VariableRead from GlobalVariable

a = fun1()
            """,  # language= None
            {"Call.fun1.line11": SimpleImpure(["NonLocalVariableRead.GlobalVariable.var1"]),
             "Call.fun2.line4": SimpleImpure(["NonLocalVariableRead.GlobalVariable.var1"])},
        ),   # here the reason of impurity for fun2 is propagated to fun1, therefore fun1 is impure

        (  # language=Python "Call of Impure Chain of Functions"
            """
var1 = 1
def fun1():
    res = fun2()  # Impure: Call of Impure Function
    return res

def fun2():
    return fun3()  # Impure: Call of Impure Function

def fun3():
    res = var1
    return res  # Impure: VariableRead from GlobalVariable

a = fun1()
            """,  # language= None
            {"Call.fun1.line14": SimpleImpure(["NonLocalVariableRead.GlobalVariable.var1"]),
             "Call.fun2.line4": SimpleImpure(["NonLocalVariableRead.GlobalVariable.var1"]),
             "Call.fun3.line8": SimpleImpure(["NonLocalVariableRead.GlobalVariable.var1"])},
        ),
        (  # language=Python "Call of Impure Chain of Functions with cycle - one entry point"
            """
def cycle1():
    cycle2()

def cycle2():
    cycle3()

def cycle3():
    print("test")  # Impure: FileWrite
    cycle1()

def entry():
    cycle1()

entry()
            """,  # language= None
            {},  # TODO: LARS how should the results look here? do we want the functions inside of cycles to be returned
        ),
        (  # language=Python "Call of Impure Chain of Functions with cycle - direct entry"
            """
def fun1(count):
    if count > 0:
        fun2(count - 1)
    else:
        print("end")  # Impure: FileWrite

def fun2(count):
    if count > 0:
        fun1(count - 1)
    else:
        print("end")  # Impure: FileWrite

fun1(3)
            """,  # language= None
            {},
        ),
        (  # language=Python "Call of Impure Builtin Function"
            """
def fun():
    res = input()  # Impure: Call of Impure Builtin Function - User input is requested
    return res

a = fun()
            """,  # language= None
            {"Call.fun.line6": SimpleImpure(["FileRead.StringLiteral.stdin"])},  # TODO: LARS what is this - since we no longer have User interaction
        ),
        (  # language=Python "Multiple Calls of same Impure function (Caching)"
            """
var1 = 1
def fun1():
    global var1
    res = var1  # Impure: VariableRead from GlobalVariable
    return res

a = fun1()
b = fun1()
c = fun1()
            """,  # language= None
            {"Call.fun1.line8": SimpleImpure(["NonLocalVariableRead.GlobalVariable.var1"]),
             "Call.fun2.line9": SimpleImpure(["NonLocalVariableRead.GlobalVariable.var1"]),
             "Call.fun3.line10": SimpleImpure(["NonLocalVariableRead.GlobalVariable.var1"])},
        ),  # here the reason of impurity for fun1 can be cached for the other calls
    ],
    ids=[
        "Print with str",
        "Print with parameter",
        "Open with str",
        "Open with parameter",
        "VariableWrite to GlobalVariable",
        "VariableWrite to GlobalVariable with parameter",
        "VariableRead from GlobalVariable",
        "Call of Impure Function",
        "Call of Impure Chain of Functions",
        "Call of Impure Chain of Functions with cycle - one entry point",
        "Call of Impure Chain of Functions with cycle - direct entry",
        "Call of Impure BuiltIn Function",
        "Multiple Calls of same Impure function (Caching)",
        # TODO: "Unknown" pure cycle within impure cycle, many reasons in one function, ClassVariables, InstanceVariables, Multiple Classes with same name and different purity
    ],
)
def test_infer_purity_impure(code: str, expected: dict[str, SimpleImpure]) -> None:
    references, function_references, call_graph = resolve_references(code)

    purity_results = infer_purity_new(references, call_graph)

    transformed_purity_results = {to_string_call(call): to_simple_result(purity_result) for call, purity_result in purity_results.items()}

    assert transformed_purity_results == expected


def to_string_call(call: astroid.Call) -> str:
    if isinstance(call, str):
        return f"{call}"
    return f"Call.{call.func.name}.line{call.lineno}"


def to_simple_result(purity_result: PurityResult) -> Pure | SimpleImpure:
    if isinstance(purity_result, Pure):
        return Pure()
    else:
        return SimpleImpure([to_string_reason(reason) for reason in purity_result.reasons])


def to_string_reason(reason: ImpurityReason) -> str:
    if isinstance(reason, NonLocalVariableRead):
        return f"NonLocalVariableRead.{reason.symbol.__class__.__name__}.{reason.symbol.name}"
    elif isinstance(reason, NonLocalVariableWrite):
        return f"NonLocalVariableWrite.{reason.symbol.__class__.__name__}.{reason.symbol.name}"
    elif isinstance(reason, FileRead):
        return f"FileRead.{reason.source.__class__.__name__}.{reason.source.value}"
    elif isinstance(reason, FileWrite):
        return f"FileWrite.{reason.source.__class__.__name__}.{reason.source.value}"
    else:
        raise NotImplementedError(f"Unknown reason: {reason}")
