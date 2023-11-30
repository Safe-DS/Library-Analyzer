from dataclasses import dataclass

import astroid
import pytest

from library_analyzer.processing.api.purity_analysis import (
    resolve_references,
    infer_purity,
)
from library_analyzer.processing.api.purity_analysis.model import (
    ImpurityReason,
    Pure,
    PurityResult,
    NonLocalVariableRead,
    NonLocalVariableWrite,
    FileWrite,
    FileRead,
    ParameterAccess,
)


@dataclass
class SimpleImpure:
    reasons: set[str]


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
        (  # language=Python "VariableWrite to InstanceVariable - but actually a LocalVariable"
            """
class A:
    def __init__(self):  # TODO: for init we need to filter out all reasons which are related to instance variables of the class (from the init function itself or propagated from called functions)
        self.instance_attr1 = 10

def fun():
    a = A()
    a.instance_attr1 = 20  # Pure: VariableWrite to InstanceVariable - but actually a LocalVariable
            """,  # language= None
            {"fun.line2": Pure()},
        ),
        (  # language=Python "VariableRead from InstanceVariable - but actually a LocalVariable"
            """
class A:
    def __init__(self):
        self.instance_attr1 = 10

def fun():
    a = A()
    res = a.instance_attr1  # Pure: VariableRead from InstanceVariable - but actually a LocalVariable
    return res
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
        (  # language=Python "Lambda function"
            """
def fun():
    res = (lambda x, y: x + y)(10, 20)  # Pure: Call of a Lambda Function and write to LocalVariable
    return res
            """,  # language= None
            {"fun.line2": Pure()},
        ),
        (  # language=Python "Assigned Lambda function"
            """
double = lambda x: 2 * x
            """,  # language= None
            {"double.line2": Pure()},
        ),
        (  # language=Python "Lambda as key"
            """
def fun():
    numbers = [1, 2, 3, 4]
    squared_numbers = map(lambda x: x**2, numbers)
    return squared_numbers
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
        "VariableWrite to InstanceVariable - but actually a LocalVariable",
        "VariableRead from InstanceVariable - but actually a LocalVariable",
        "Call of Pure Function",
        "Call of Pure Chain of Functions",
        "Call of Pure Chain of Functions with cycle - one entry point",
        "Call of Pure Chain of Functions with cycle - direct entry",
        "Call of Pure Builtin Function",
        "Lambda function",
        "Assigned Lambda function",
        "Lambda as key",
        "Multiple Calls of same Pure function (Caching)",
    ],  # TODO: chained instance variables/ classVariables, class methods, instance methods, static methods
)
def test_infer_purity_pure(code: str, expected: list[ImpurityReason]) -> None:
    references, function_references, call_graph = resolve_references(code)

    purity_results = infer_purity(references, function_references, call_graph)
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
        (  # language=Python "Call of Impure Chain of Functions with cycle - other calls in cycle"
            """
var1 = 1

def cycle1():
    other()
    cycle2()

def cycle2():
    cycle3()

def cycle3():
    print("test")  # Impure: FileWrite
    cycle1()

def other():
    global var1
    var1 = 2  # Impure: VariableWrite to GlobalVariable

def entry():
    cycle1()
            """,  # language= None
            {"cycle1.line4": SimpleImpure({"FileWrite.StringLiteral.stdout",
                                           "NonLocalVariableWrite.GlobalVariable.var1"}),
             "cycle2.line8": SimpleImpure({"FileWrite.StringLiteral.stdout",
                                           "NonLocalVariableWrite.GlobalVariable.var1"}),
             "cycle3.line11": SimpleImpure({"FileWrite.StringLiteral.stdout",
                                            "NonLocalVariableWrite.GlobalVariable.var1"}),
             "other.line15": SimpleImpure({"NonLocalVariableWrite.GlobalVariable.var1"}),
             "entry.line19": SimpleImpure({"FileWrite.StringLiteral.stdout",
                                           "NonLocalVariableWrite.GlobalVariable.var1"})
             },  # for cycles, we want to propagate the impurity of the cycle to all functions in the cycle
            # but only return the results for the real functions
        ),
        (  # language=Python "Call of Impure Chain of Functions with cycle - cycle in cycle"
            """
var1 = 1

def cycle1():
    cycle2()

def cycle2():
    cycle3()

def cycle3():
    inner_cycle1()
    print("enter inner cycle")  # Impure: FileWrite
    cycle1()

def inner_cycle1():
    inner_cycle2()

def inner_cycle2():
    inner_cycle1()
    global var1
    var1 = 2  # Impure: VariableWrite to GlobalVariable

def entry():
    cycle1()
            """,  # language= None
            {"cycle1.line4": SimpleImpure({"FileWrite.StringLiteral.stdout",
                                           "NonLocalVariableWrite.GlobalVariable.var1"}),
             "cycle2.line7": SimpleImpure({"FileWrite.StringLiteral.stdout",
                                           "NonLocalVariableWrite.GlobalVariable.var1"}),
             "cycle3.line10": SimpleImpure({"FileWrite.StringLiteral.stdout",
                                            "NonLocalVariableWrite.GlobalVariable.var1"}),
             "inner_cycle1.line15": SimpleImpure({"NonLocalVariableWrite.GlobalVariable.var1"}),
             "inner_cycle2.line18": SimpleImpure({"NonLocalVariableWrite.GlobalVariable.var1"}),
             "entry.line23": SimpleImpure({"FileWrite.StringLiteral.stdout",
                                           "NonLocalVariableWrite.GlobalVariable.var1"}),
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

        (  # language=Python "Lambda function"
            """
var1 = 1

def fun():
    global var1
    res = (lambda x: x + var1)(10)  # Impure: Call of Impure Function which has VariableRead from GlobalVariable
    return res
            """,  # language= None
            {"fun.line4": SimpleImpure({"NonLocalVariableRead.GlobalVariable.var1"})},
        ),
        (  # language=Python "Assigned Lambda function"
            """
var1 = 1
double = lambda x: var1 * x  # Impure: VariableRead from GlobalVariable
            """,  # language= None
            {"double.line2": SimpleImpure({"NonLocalVariableRead.GlobalVariable.var1"})},
        ),
        (  # language=Python "Lambda as key"
            """
var1 = "x"

def fun():
    global var1
    names = ["a", "abc", "ab", "abcd"]
    sort = sorted(names, key=lambda x: x + var1)
    return sort
            """,  # language= None
            {"fun.line4": SimpleImpure({"NonLocalVariableRead.GlobalVariable.var1"})},  # TODO: what do we want here? what is sorted?
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
        "Call of Impure Chain of Functions with cycle - other calls in cycle",
        "Call of Impure Chain of Functions with cycle - cycle in cycle",
        "Call of Impure Chain of Functions with cycle - direct entry",
        "Call of Impure BuiltIn Function",
        "Lambda function",
        "Assigned Lambda function",
        "Lambda as key",
        "Multiple Calls of same Impure function (Caching)",
        "Multiple Classes with same name and different purity",
        "Different Reasons for Impurity",
        "Unknown Call",
        # TODO: chained instance variables/ classVariables, class methods, instance methods, static methods, class instantiation?
    ],
)
def test_infer_purity_impure(code: str, expected: dict[str, SimpleImpure]) -> None:
    references, function_references, call_graph = resolve_references(code)

    purity_results = infer_purity(references, function_references, call_graph)

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
        if isinstance(reason.source, ParameterAccess):
            return f"FileRead.ParameterAccess.{reason.source.parameter}"
        return f"FileRead.{reason.source.__class__.__name__}.{reason.source.value}"
    elif isinstance(reason, FileWrite):
        if isinstance(reason.source, ParameterAccess):
            return f"FileWrite.ParameterAccess.{reason.source.parameter}"
        return f"FileWrite.{reason.source.__class__.__name__}.{reason.source.value}"
    else:
        raise NotImplementedError(f"Unknown reason: {reason}")


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (  # language=Python "Open with str default"
            """
def fun():
    open("text.txt")  # Impure: FileRead
            """,  # language= None
            {"fun.line2": SimpleImpure({"FileRead.StringLiteral.text.txt"})}
        ),
        (  # language=Python "Open with str read"
            """
def fun():
    open("text.txt", "r")  # Impure: FileRead
            """,  # language= None
            {"fun.line2": SimpleImpure({"FileRead.StringLiteral.text.txt"})}
        ),
        (  # language=Python "Open with str write"
            """
def fun():
    open("text.txt", "wb")  # Impure: FileWrite
            """,  # language= None
            {"fun.line2": SimpleImpure({"FileWrite.StringLiteral.text.txt"})}
        ),
        (  # language=Python "Open with str read and write"
            """
def fun():
    open("text.txt", "a+")  # Impure: FileRead and FileWrite
            """,  # language= None
            {"fun.line2": SimpleImpure({"FileRead.StringLiteral.text.txt",
                                        "FileWrite.StringLiteral.text.txt"})}
        ),
        (  # language=Python "Open with parameter default"
            """
def fun(pos_arg):
    open(pos_arg)  # Impure: FileRead
            """,  # language= None
            {"fun.line2": SimpleImpure({"FileRead.ParameterAccess.pos_arg"})}
        ),
        (  # language=Python "Open with parameter write"
            """
def fun(pos_arg):
    open(pos_arg, "a")  # Impure: FileWrite
            """,  # language= None
            {"fun.line2": SimpleImpure({"FileWrite.ParameterAccess.pos_arg"})}
        ),
        (  # language=Python "Read"
            """
def fun():
    f = open("text.txt")  # Impure: FileRead
    f.read()  # TODO: [Later] For now open is enough
            """,  # language= None
            {"fun.line2": SimpleImpure({"FileRead.StringLiteral.text.txt"})}
        ),
        (  # language=Python "Readline/ Readlines"
            """
def fun():
    f = open("text.txt")  # Impure: FileRead
    f.readline()  # TODO: [Later] For now open is enough
    f.readlines()  # TODO: [Later] For now open is enough
            """,  # language= None
            {"fun.line2": SimpleImpure({"FileRead.StringLiteral.text.txt"})}
        ),
        (  # language=Python "Write"
            """
def fun():
    f = open("text.txt", "w")  # Impure: FileWrite
    f.write("test")  # TODO: [Later] For now open is enough
            """,  # language= None
            {"fun.line2": SimpleImpure({"FileWrite.StringLiteral.text.txt"})}
        ),
        (  # language=Python "Writelines"
            """
def fun():
    f = open("text.txt", "w")  # Impure: FileWrite
    f.writelines(["test1", "test2"])  # TODO: [Later] For now open is enough
            """,  # language= None
            {"fun.line2": SimpleImpure({"FileWrite.StringLiteral.text.txt"})}
        ),
        (  # language=Python "With open str default"
            """
def fun():
    with open("text.txt") as f:  # Impure: FileRead
        f.read()
            """,  # language= None
            {"fun.line2": SimpleImpure({"FileRead.StringLiteral.text.txt"})}
        ),
        (  # language=Python "With open parameter default"
            """
def fun(pos_arg):
    with open(pos_arg) as f:  # Impure: FileRead
        f.read()
            """,  # language= None
            {"fun.line2": SimpleImpure({"FileRead.ParameterAccess.pos_arg"})}
        ),
        (  # language=Python "With open parameter read and write"
            """
def fun(pos_arg):
    with open(pos_arg, "wb+") as f:  # Impure: FileRead and FileWrite
        f.read()
            """,  # language= None
            {"fun.line2": SimpleImpure({"FileRead.ParameterAccess.pos_arg",
                                        "FileWrite.ParameterAccess.pos_arg"})}
        ),
        (  # language=Python "With open parameter and variable mode"
            """
def fun(pos_arg, mode):
    with open(pos_arg, mode) as f:  # Impure: FileRead and FileWrite
        f.read()
            """,  # language= None
            {"fun.line2": SimpleImpure({"FileRead.ParameterAccess.pos_arg",
                                        "FileWrite.ParameterAccess.pos_arg"})}
        ),  # TODO: do we want to expect the worst case here?
        (  # language=Python "With open close"
            """
def fun():
    with open("text.txt") as f:  # Impure: FileRead
        f.read()
        f.close()  # TODO: [Later] For now open is enough
            """,  # language= None
            {"fun.line2": SimpleImpure({"FileRead.StringLiteral.text.txt"})}
        ),
    ],
    ids=[
        "Open with str default",
        "Open with str read",
        "Open with str write",
        "Open with str read and write",
        "Open with parameter default",
        "Open with parameter write",
        "Read",
        "Readline/ Readlines",
        "Write",
        "Writelines",
        "With open str default",
        "With open parameter default",
        "With open parameter read and write",
        "With open parameter and variable mode",
        "With open close",
    ],
)
def test_infer_purity_open(code: str, expected: dict[str, SimpleImpure]) -> None:
    references, function_references, call_graph = resolve_references(code)

    purity_results = infer_purity(references, function_references, call_graph)

    transformed_purity_results = {to_string_call(call): to_simple_result(purity_result) for call, purity_result in
                                  purity_results.items()}

    assert transformed_purity_results == expected
