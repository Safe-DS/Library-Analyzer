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
    reasons: set[str]


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
        (  # language=Python "Trivial function"
            """
def fun():
    pass  # Pure
            """,  # language= None
            {"fun.line2": Pure()},
        ),
        (  # language=Python "Trivial function with parameter and return"
            """
def fun(x):
    return 2 * x  # Pure: VariableRead from LocalVariable
            """,  # language= None
            {"fun.line2": Pure()},
        ),
        (  # language=Python "VariableWrite to LocalVariable"
            """
def fun():
    var1 = 2  # Pure: VariableWrite to LocalVariable
    return var1
            """,  # language= None
            {"fun.line2": Pure()},
        ),
        (  # language=Python "VariableWrite to LocalVariable with parameter"
            """
def fun(x):
    var1 = x  # Pure: VariableWrite to LocalVariable
    return var1
            """,  # language= None
            {"fun.line2": Pure()},
        ),
        (  # language=Python "VariableRead from LocalVariable"
            """
def fun():
    var1 = 1  # Pure: VariableRead from LocalVariable
    return var1
            """,  # language= None
            {"fun.line2": Pure()},
        ),
        (  # language=Python "Call of Pure Function"
            """
def fun1():
    res = fun2()  # Pure: Call of Pure Function
    return res

def fun2():
    return 1  # Pure
            """,  # language= None
            {"fun1.line2": Pure(),
             "fun2.line6": Pure()},
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
            """,  # language= None
            {"fun1.line2": Pure(),
             "fun2.line6": Pure(),
             "fun3.line9": Pure()},
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
            """,  # language= None
            {"cycle1.line2": Pure(),
             "cycle2.line5": Pure(),
             "cycle3.line8": Pure(),
             "entry.line11": Pure()
             },  # for cycles, we want to propagate the purity of the cycle to all functions in the cycle
            # but only return the results for the real functions
        ),
        (  # language=Python "Call of Pure Chain of Functions with cycle - direct entry"
            """
def fun1(count):
    if count > 0:
        fun2(count - 1)

def fun2(count):
    if count > 0:
        fun1(count - 1)
            """,  # language= None
            {"fun1.line2": Pure(),
             "fun2.line6": Pure()},
        ),
        (  # language=Python "Call of Pure Builtin Function"
            """
def fun():
    res = range(2)  # Pure: Call of Pure Builtin Function and write to LocalVariable
    return res
            """,  # language= None
            {"fun.line2": Pure()},
        ),
        (  # language=Python "Multiple Calls of the same Pure function (Caching)"
            """
def fun1():
    return 1

a = fun1()
b = fun1()
c = fun1()
            """,  # language= None
            {"fun1.line2": Pure()},
        ),  # here the purity for fun1 can be cached for the other calls
    ],
    ids=[
        "Trivial function",
        "Trivial function with parameter and return",
        "VariableWrite to LocalVariable",
        "VariableWrite to LocalVariable with parameter",
        "VariableRead from LocalVariable",
        "Call of Pure Function",
        "Call of Pure Chain of Functions",
        "Call of Pure Chain of Functions with cycle - one entry point",
        "Call of Pure Chain of Functions with cycle - direct entry",
        "Call of Pure Builtin Function",
        "Multiple Calls of same Pure function (Caching)",
    ],  # TODO: ClassVariables, InstanceVariables, Lambda with name
)
def test_infer_purity_pure(code: str, expected: list[ImpurityReason]) -> None:
    references, function_references, call_graph = resolve_references(code)

    purity_results = infer_purity_new(references, function_references, call_graph)
    transformed_purity_results = {to_string_call(call): to_simple_result(purity_result) for call, purity_result in purity_results.items()}

    assert transformed_purity_results == expected


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (  # language=Python "Print with str"
            """
def fun():
    print("text.txt")  # Impure: FileWrite
            """,  # language= None
            {"fun.line2": SimpleImpure({"FileWrite.StringLiteral.stdout"})}
        ),
        (  # language=Python "Print with parameter"
            """
def fun(pos_arg):
    print(pos_arg)  # Impure: FileWrite
            """,  # language= None
            {"fun.line2": SimpleImpure({"FileWrite.StringLiteral.stdout"})}
        ),
        (  # language=Python "Open with str"
            """
def fun():
    open("text.txt")  # Impure: FileWrite
            """,  # language= None
            {"fun.line2": SimpleImpure({"FileWrite.StringLiteral.text.txt"})}
        ),
        (  # language=Python "Open with parameter"
            """
def fun(pos_arg):
    open(pos_arg)  # Impure: FileWrite
            """,  # language= None
            {"fun.line2": SimpleImpure({"FileWrite.ParameterAccess.pos_arg"})}
        ),
        (  # language=Python "With open"
            """
def fun(pos_arg):
    with open(pos_arg) as f:  # Impure: FileWrite
        f.read()
            """,  # language= None
            {"fun.line2": SimpleImpure({"FileWrite.ParameterAccess.pos_arg"})}
        ),
        (  # language=Python "VariableWrite to GlobalVariable"
            """
var1 = 1
def fun():
    var1 = 2  # Impure: VariableWrite to GlobalVariable
    return var1  # Impure: VariableRead from GlobalVariable  # TODO: [Later] technically this is a local variable read but we handle var1 as global for now
            """,  # language= None
            {"fun.line3": SimpleImpure({"NonLocalVariableWrite.GlobalVariable.var1",
                                        "NonLocalVariableRead.GlobalVariable.var1"})},
        ),
        (  # language=Python "VariableWrite to GlobalVariable with parameter"
            """
var1 = 1
def fun(x):
    var1 = x  # Impure: VariableWrite to GlobalVariable
    return var1  # Impure: VariableRead from GlobalVariable  # TODO: [Later] technically this is a local variable read but we handle var1 as global for now
            """,  # language= None
            {"fun.line3": SimpleImpure({"NonLocalVariableWrite.GlobalVariable.var1",
                                        "NonLocalVariableRead.GlobalVariable.var1"})},
        ),
        (  # language=Python "VariableRead from GlobalVariable"
            """
var1 = 1
def fun():
    res = var1  # Impure: VariableRead from GlobalVariable
    return res
            """,  # language= None
            {"fun.line3": SimpleImpure({"NonLocalVariableRead.GlobalVariable.var1"})}
        ),
        (  # language=Python "VariableWrite to ClassVariable"
            """
class A:
    class_attr1 = 20

def fun():
    A.class_attr1 = 30  # Impure: VariableWrite to ClassVariable
            """,  # language= None
            {"fun.line5": SimpleImpure({"NonLocalVariableWrite.ClassVariable.A.class_attr1"})},
        ),
        (  # language=Python "VariableRead from ClassVariable"
            """
class A:
    class_attr1 = 20

def fun():
    res = A.class_attr1  # Impure: VariableRead from ClassVariable
    return res
            """,  # language= None
            {"fun.line5": SimpleImpure({"NonLocalVariableRead.ClassVariable.A.class_attr1"})},
        ),
        (  # language=Python "VariableWrite to InstanceVariable"
            """
class B:
    def __init__(self):
        self.instance_attr1 = 10

def fun(c):
    c.instance_attr1 = 20  # Impure: VariableWrite to InstanceVariable

b = B()
fun(b)
            """,  # language= None
            {"fun.line6": SimpleImpure({"NonLocalVariableWrite.InstanceVariable.B.instance_attr1"})},
        ),
        (  # language=Python "VariableRead from InstanceVariable"
            """
class B:
    def __init__(self):
        self.instance_attr1 = 10

def fun(c):
    res = c.instance_attr1  # Impure: VariableRead from InstanceVariable
    return res

b = B()
a = fun(b)
            """,  # language= None
            {"fun.line6": SimpleImpure({"NonLocalVariableRead.InstanceVariable.B.instance_attr1"})},
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
            """,  # language= None
            {"fun1.line3": SimpleImpure({"NonLocalVariableRead.GlobalVariable.var1"}),
             "fun2.line7": SimpleImpure({"NonLocalVariableRead.GlobalVariable.var1"})},
        ),   # here the reason of impurity for fun2 is propagated to fun1, therefore, fun1 is impure

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
            """,  # language= None
            {"fun1.line3": SimpleImpure({"NonLocalVariableRead.GlobalVariable.var1"}),
             "fun2.line7": SimpleImpure({"NonLocalVariableRead.GlobalVariable.var1"}),
             "fun3.line10": SimpleImpure({"NonLocalVariableRead.GlobalVariable.var1"})},
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
            """,  # language= None
            {"cycle1.line2": SimpleImpure({"FileWrite.StringLiteral.stdout"}),
             "cycle2.line5": SimpleImpure({"FileWrite.StringLiteral.stdout"}),
             "cycle3.line8": SimpleImpure({"FileWrite.StringLiteral.stdout"}),
             "entry.line12": SimpleImpure({"FileWrite.StringLiteral.stdout"})
             },  # for cycles, we want to propagate the impurity of the cycle to all functions in the cycle
            # but only return the results for the real functions
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
            """,  # language= None
            {"fun1.line2": SimpleImpure({"FileWrite.StringLiteral.stdout"}),
             "fun2.line8": SimpleImpure({"FileWrite.StringLiteral.stdout"})},
        ),
        (  # language=Python "Call of Impure Builtin Function"
            """
def fun():
    res = input()  # Impure: Call of Impure Builtin Function - User input is requested
    return res
            """,  # language= None
            {"fun.line2": SimpleImpure({"FileRead.StringLiteral.stdin"})},
        ),
        (  # language=Python "Multiple Calls of the same Impure function (Caching)"
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
            {"fun1.line3": SimpleImpure({"NonLocalVariableRead.GlobalVariable.var1"})},
        ),  # here the reason of impurity for fun1 can be cached for the other calls
        (  # language=Python "Multiple Classes with the same name and different purity"
            """
class A:
    @staticmethod
    def add(a, b):
        print("test")  # Impure: FileWrite
        return a + b

class B:
    @staticmethod
    def add(a, b):
        return a + 2 * b

A.add(1, 2)
B.add(1, 2)
            """,  # language=none
            {"TODO"}
        ),
        (  # language=Python "Different Reasons for Impurity",
            """
var1 = 1

def fun1():
    global var1
    if var1 > 0:
        var1 = fun2()  # Impure: Call of Impure Function / VariableWrite to GlobalVariable
    var1 = 2   # Impure: VariableWrite to GlobalVariable
    print("test")  # Impure: FileWrite
    return var1  # Impure: VariableRead from GlobalVariable

def fun2():
    res = input()
    return res  # Impure: Call of Impure Builtin Function - User input is requested
            """,  # language=none
            {"fun1.line4": SimpleImpure({"NonLocalVariableRead.GlobalVariable.var1",
                                         "NonLocalVariableWrite.GlobalVariable.var1",
                                         "FileWrite.StringLiteral.stdout",
                                         "FileRead.StringLiteral.stdin"}),  # this is propagated from fun2
             "fun2.line12": SimpleImpure({"FileRead.StringLiteral.stdin"})}
        ),
        (  # language=Python "Unknown Call",
            """
def fun1():
    call()
            """,  # language=none
            {
                "fun1": "Unknown({})",
                "call": "Unknown({})",
            },
        ),
    ],
    ids=[
        "Print with str",
        "Print with parameter",
        "Open with str",
        "Open with parameter",
        "With open",
        "VariableWrite to GlobalVariable",  # TODO: this just passes due to the conversion to a set
        "VariableWrite to GlobalVariable with parameter",  # TODO: this just passes due to the conversion a set
        "VariableRead from GlobalVariable",
        "VariableWrite to ClassVariable",
        "VariableRead from ClassVariable",
        "VariableWrite to InstanceVariable",
        "VariableRead from InstanceVariable",
        "Call of Impure Function",
        "Call of Impure Chain of Functions",
        "Call of Impure Chain of Functions with cycle - one entry point",
        "Call of Impure Chain of Functions with cycle - direct entry",
        "Call of Impure BuiltIn Function",
        "Multiple Calls of same Impure function (Caching)",
        "Multiple Classes with same name and different purity",
        "Different Reasons for Impurity",
        "Unknown Call",
        # TODO: pure cycle within impure cycle, Lambda with name, chained instance variables/ classVariables
    ],
)
def test_infer_purity_impure(code: str, expected: dict[str, SimpleImpure]) -> None:
    references, function_references, call_graph = resolve_references(code)

    purity_results = infer_purity_new(references, function_references, call_graph)

    transformed_purity_results = {to_string_call(call): to_simple_result(purity_result) for call, purity_result in purity_results.items()}

    assert transformed_purity_results == expected


def to_string_call(func: astroid.FunctionDef | str) -> str:
    if isinstance(func, str):
        return f"{func}"
    return f"{func.name}.line{func.lineno}"


def to_simple_result(purity_result: PurityResult) -> Pure | SimpleImpure:
    if isinstance(purity_result, Pure):
        return Pure()
    else:
        return SimpleImpure({to_string_reason(reason) for reason in purity_result.reasons})


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
