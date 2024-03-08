from dataclasses import dataclass

import pytest
from library_analyzer.processing.api.purity_analysis import (
    infer_purity,
)
from library_analyzer.processing.api.purity_analysis.model import (
    CallOfParameter,
    ClassVariable,
    FileRead,
    FileWrite,
    Import,
    Impure,
    ImpurityReason,
    InstanceVariable,
    NodeID,
    NonLocalVariableRead,
    NonLocalVariableWrite,
    ParameterAccess,
    Pure,
    PurityResult,
    StringLiteral,
    UnknownCall,
    UnknownClassInit,
    UnknownFunctionCall,
)


@dataclass
class SimpleImpure:
    """Class for simple impure results.

    A simplified class of the Impure class for testing purposes.

    Attributes
    ----------
    reasons : set[str]
        The set of reasons for impurity as strings.
    """

    reasons: set[str]


def to_string_function_id(node_id: NodeID | str) -> str:
    """Convert a function to a string representation.

    Parameters
    ----------
    node_id : NodeID | str
        The NodeID to convert.

    Returns
    -------
    str
        The string representation of the NodeID.
    """
    if isinstance(node_id, str):
        return f"{node_id}"
    return f"{node_id.name}.line{node_id.line}"


def to_simple_result(purity_result: PurityResult) -> Pure | SimpleImpure:  # type: ignore[return] # all cases are handled
    """Convert a purity result to a simple result.

    Parameters
    ----------
    purity_result : PurityResult
        The purity result to convert, either Pure or Impure.

    Returns
    -------
    Pure | SimpleImpure
        The converted purity result.
    """
    if isinstance(purity_result, Pure):
        return Pure()
    elif isinstance(purity_result, Impure):
        return SimpleImpure({to_string_reason(reason) for reason in purity_result.reasons})


def to_string_reason(reason: ImpurityReason) -> str:  # type: ignore[return] # all cases are handled
    """Convert an impurity reason to a string.

    Parameters
    ----------
    reason : ImpurityReason
        The impurity reason to convert.

    Returns
    -------
    str
        The converted impurity reason.
    """
    if reason is None:
        raise ValueError("Reason must not be None")
    if isinstance(reason, NonLocalVariableRead):
        if isinstance(reason.symbol, ClassVariable | InstanceVariable) and reason.symbol.klass is not None:
            return f"NonLocalVariableRead.{reason.symbol.__class__.__name__}.{reason.symbol.klass.name}.{reason.symbol.name}"
        if isinstance(reason.symbol, Import):
            if reason.symbol.name:
                return f"NonLocalVariableRead.{reason.symbol.__class__.__name__}.{reason.symbol.module}.{reason.symbol.name}"
            return f"NonLocalVariableRead.{reason.symbol.__class__.__name__}.{reason.symbol.module}"
        return f"NonLocalVariableRead.{reason.symbol.__class__.__name__}.{reason.symbol.name}"
    elif isinstance(reason, NonLocalVariableWrite):
        if isinstance(reason.symbol, ClassVariable | InstanceVariable) and reason.symbol.klass is not None:
            return f"NonLocalVariableWrite.{reason.symbol.__class__.__name__}.{reason.symbol.klass.name}.{reason.symbol.name}"
        if isinstance(reason.symbol, Import):
            if reason.symbol.name:
                return f"NonLocalVariableWrite.{reason.symbol.__class__.__name__}.{reason.symbol.module}.{reason.symbol.name}"
            return f"NonLocalVariableWrite.{reason.symbol.__class__.__name__}.{reason.symbol.module}"
        return f"NonLocalVariableWrite.{reason.symbol.__class__.__name__}.{reason.symbol.name}"
    elif isinstance(reason, FileRead):
        if isinstance(reason.source, ParameterAccess):
            return f"FileRead.{reason.source.__class__.__name__}.{reason.source.parameter}"
        if isinstance(reason.source, StringLiteral):
            return f"FileRead.{reason.source.__class__.__name__}.{reason.source.value}"
    elif isinstance(reason, FileWrite):
        if isinstance(reason.source, ParameterAccess):
            return f"FileWrite.{reason.source.__class__.__name__}.{reason.source.parameter}"
        if isinstance(reason.source, StringLiteral):
            return f"FileWrite.{reason.source.__class__.__name__}.{reason.source.value}"
    elif isinstance(reason, UnknownCall):
        if isinstance(reason.expression, StringLiteral):
            return f"UnknownCall.{reason.expression.__class__.__name__}.{reason.expression.value}"
        elif isinstance(reason.expression, ParameterAccess):
            return f"UnknownCall.{reason.expression.__class__.__name__}.{reason.expression.parameter.name}"
        elif isinstance(reason.expression, UnknownFunctionCall | UnknownClassInit):
            return f"UnknownCall.{reason.expression.__class__.__name__}.{reason.expression.name}"
    elif isinstance(reason, CallOfParameter):
        if isinstance(reason.expression, StringLiteral):
            return f"CallOfParameter.{reason.expression.__class__.__name__}.{reason.expression.value}"
        elif isinstance(reason.expression, ParameterAccess):
            return f"CallOfParameter.{reason.expression.__class__.__name__}.{reason.expression.parameter.name}"
    else:
        raise NotImplementedError(f"Unknown reason: {reason}")


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
    def __init__(self):
        self.instance_attr1 = 10

def fun():
    a = A()
    a.instance_attr1 = 20  # Pure: VariableWrite to InstanceVariable - but actually a LocalVariable
            """,  # language= None
            {"__init__.line3": Pure(), "fun.line6": Pure()},
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
            {"__init__.line3": Pure(), "fun.line6": Pure()},
        ),
        (  # language=Python "VariableRead and VariableWrite in chained class attribute and instance attribute"
            """
class A:
    def __init__(self):
        self.name = 10

class B:
    upper_class: A = A()

def f():
    b = B()
    x = b.upper_class.name

def g():
    b = B()
    b.upper_class.name = 20
            """,  # language=none
            {
                "__init__.line3": Pure(),
                "f.line9": Pure(),
                "g.line13": Pure(),
            },
        ),
        (  # language=Python "Pure Class initialization"
            """
class A:
    pass

class B:
    def __init__(self):
        pass

class C:
    def __init__(self):
        self.name = "test"

def fun1():
    a = A()

def fun2():
    b = B()

            """,  # language= None
            {"__init__.line6": Pure(), "__init__.line10": Pure(), "fun1.line13": Pure(), "fun2.line16": Pure()},
        ),
        (  # language=Python "Pure Class initialization with propagated purity in init"
            """
class A:
    def __init__(self):
        self.name = self.fun1()
        self.value = self.fun2()
        self.test = None
        self.fun3()

    @staticmethod
    def fun1():
        return "test"

    def fun2(self):
        return self.name  # Impure: VariableRead from InstanceVariable

    def fun3(self):
        self.test = 10  # Impure: VariableWrite to InstanceVariable
            """,  # language= None
            {
                "__init__.line3": Pure(),  # For init we need to filter out all reasons which are related to instance variables of the class (from the init function itself or propagated from called functions)
                "fun1.line10": Pure(),
                "fun2.line13": SimpleImpure({"NonLocalVariableRead.InstanceVariable.A.name"}),
                "fun3.line16": SimpleImpure({"NonLocalVariableWrite.InstanceVariable.A.test"}),
            },
        ),
        (  # language=Python "Call of Pure Function"
            """
def fun1():
    res = fun2()  # Pure: Call of Pure Function
    return res

def fun2():
    return 1  # Pure
            """,  # language= None
            {"fun1.line2": Pure(), "fun2.line6": Pure()},
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
            {"fun1.line2": Pure(), "fun2.line6": Pure(), "fun3.line9": Pure()},
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
            {
                "cycle1.line2": Pure(),
                "cycle2.line5": Pure(),
                "cycle3.line8": Pure(),
                "entry.line11": Pure(),
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
            {"fun1.line2": Pure(), "fun2.line6": Pure()},
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
        (  # language=Python "Async Function"
            """
async def fun1():
    res = await fun2()  # Pure: Call of Pure Function

async def fun2():
    pass
            """,  # language= None
            {"fun1.line2": Pure(), "fun2.line5": Pure()},
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
        "VariableRead and VariableWrite in chained class attribute and instance attribute",
        "Pure Class initialization",
        "Pure Class initialization with propagated purity in init",
        "Call of Pure Function",
        "Call of Pure Chain of Functions",
        "Call of Pure Chain of Functions with cycle - one entry point",
        "Call of Pure Chain of Functions with cycle - direct entry",
        "Call of Pure Builtin Function",
        "Lambda function",
        "Assigned Lambda function",
        "Lambda as key",
        "Async Function",
        "Multiple Calls of same Pure function (Caching)",
    ],  # TODO: class inits in cycles
)
@pytest.mark.xfail(reason="Some cases disabled for merging")
def test_infer_purity_pure(code: str, expected: list[ImpurityReason]) -> None:
    purity_results = infer_purity(code)
    transformed_purity_results = {
        to_string_function_id(function_id): to_simple_result(purity_result)
        for function_id, purity_result in purity_results.items()
    }

    assert transformed_purity_results == expected


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (  # language=Python "Print with str"
            """
def fun():
    print("text.txt")  # Impure: FileWrite
            """,  # language= None
            {"fun.line2": SimpleImpure({"FileWrite.StringLiteral.stdout"})},
        ),
        (  # language=Python "Print with parameter"
            """
def fun(pos_arg):
    print(pos_arg)  # Impure: FileWrite
            """,  # language= None
            {"fun.line2": SimpleImpure({"FileWrite.StringLiteral.stdout"})},
        ),
        (  # language=Python "VariableWrite to shadowed GlobalVariable"
            """
var1 = 1
def fun():
    var1 = 2  # Pure: VariableWrite to LocalVariable because the global variable is shadowed
    return var1
            """,  # language= None
            {
                "fun.line3": Pure(),
            },
        ),
        (  # language=Python "VariableWrite to GlobalVariable
            """
var1 = 1
def fun(x):
    global var1
    var1 = x  # Impure: VariableWrite to GlobalVariable
    return var1  # Impure: VariableRead from GlobalVariable
            """,  # language= None
            {
                "fun.line3": SimpleImpure({
                    "NonLocalVariableWrite.GlobalVariable.var1",
                    "NonLocalVariableRead.GlobalVariable.var1",
                }),
            },
        ),
        (  # language=Python "VariableRead from GlobalVariable"
            """
var1 = 1
def fun():
    res = var1  # Impure: VariableRead from GlobalVariable
    return res
            """,  # language= None
            {"fun.line3": SimpleImpure({"NonLocalVariableRead.GlobalVariable.var1"})},
        ),
        (  # language=Python "Impure Class initialization"
            """
class A:
    def __init__(self):
        print("test")  # Impure: FileWrite

def fun():
    a = A()
            """,  # language= None
            {
                "__init__.line3": SimpleImpure({"FileWrite.StringLiteral.stdout"}),
                "fun.line6": SimpleImpure({"FileWrite.StringLiteral.stdout"}),
            },
        ),
        (  # language=Python "Class methode call"
            """
class A:
    state: str = "A"

class C:
    state: int = 0

    @classmethod
    def set_state(cls, state):
        cls.state = state

def fun1():
    c = C()
    c.set_state(1)

def fun2():
    C().set_state(1)
            """,  # language= None
            {
                "set_state.line9": SimpleImpure({"NonLocalVariableWrite.ClassVariable.C.state"}),
                "fun1.line12": SimpleImpure({"NonLocalVariableWrite.ClassVariable.C.state"}),
                "fun2.line16": SimpleImpure({"NonLocalVariableWrite.ClassVariable.C.state"}),
            },
        ),
        (  # language=Python "Class methode call of superclass"  # TODO: propagate methods from super class to sub class
            """
class A:
    state: str = "A"

    @classmethod
    def set_state(cls, state):
        cls.state = state

class C(A):
    state: int = 0

def fun1():
    c = C()
    c.set_state(1)

def fun2():
    C().set_state(1)
            """,  # language= None
            {
                "set_state.line6": SimpleImpure({"NonLocalVariableWrite.ClassVariable.A.state"}),
                "fun1.line12": SimpleImpure({"NonLocalVariableWrite.ClassVariable.C.state"}),
                "fun2.line16": SimpleImpure({"NonLocalVariableWrite.ClassVariable.C.state"}),
            },
        ),
        (  # language=Python "Class methode call of superclass (overwritten method)"
            """
class A:
    state: str = "A"

    @classmethod
    def set_state(cls, state):
        cls.state = state

class C(A):
    state: int = 0

    @classmethod
    def set_state(cls, state):
        cls.state = state
        print("test")  # Impure: FileWrite

def fun1():
    a = A()
    a.set_state(1)

def fun2():
    C().set_state(1)
            """,  # language= None
            {
                "set_state.line6": SimpleImpure({"NonLocalVariableWrite.ClassVariable.A.state"}),
                "set_state.line13": SimpleImpure(
                    {"NonLocalVariableWrite.ClassVariable.C.state", "FileWrite.StringLiteral.stdout"},
                ),
                "fun1.line17": SimpleImpure({"NonLocalVariableWrite.ClassVariable.A.state"}),
                "fun2.line21": SimpleImpure(
                    {"NonLocalVariableWrite.ClassVariable.C.state", "FileWrite.StringLiteral.stdout"},
                ),
            },
        ),
        (  # language=Python "Instance methode call"
            """
class A:
    def __init__(self):
        self.a_inst = B()

class B:
    def __init__(self):
        pass

    def b_fun(self):
        print("test")  # Impure: FileWrite

def fun1():
    a = A()
    b = a.a_inst

def fun2():
    a = A()
    a.a_inst.b_fun()

def fun3():
    a = A().a_inst.b_fun()
            """,  # language= None
            {
                "__init__.line3": Pure(),
                "__init__.line7": Pure(),
                "b_fun.line10": SimpleImpure({"FileWrite.StringLiteral.stdout"}),
                "fun1.line13": Pure(),
                "fun2.line17": SimpleImpure({"FileWrite.StringLiteral.stdout"}),
                "fun3.line21": SimpleImpure({"FileWrite.StringLiteral.stdout"}),
            },
        ),
        (  # language=Python "VariableWrite to ClassVariable"
            """
class A:
    class_attr1 = 20

def fun1():
    A.class_attr1 = 30  # Impure: VariableWrite to ClassVariable

def fun2():
    A().class_attr1 = 30  # Impure: VariableWrite to ClassVariable
            """,  # language= None
            {
                "fun1.line5": SimpleImpure({"NonLocalVariableWrite.ClassVariable.A.class_attr1"}),
                "fun2.line8": SimpleImpure({"NonLocalVariableWrite.ClassVariable.A.class_attr1"}),
            },
        ),
        (  # language=Python "VariableRead from ClassVariable"
            """
class A:
    class_attr1 = 20

def fun1():
    res = A.class_attr1  # Impure: VariableRead from ClassVariable
    return res

def fun2():
    res = A().class_attr1  # Impure: VariableRead from ClassVariable
    return res
            """,  # language= None
            {
                "fun1.line5": SimpleImpure({"NonLocalVariableRead.ClassVariable.A.class_attr1"}),
                "fun2.line9": SimpleImpure({"NonLocalVariableRead.ClassVariable.A.class_attr1"}),
            },
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
            {
                "__init__.line3": Pure(),
                "fun.line6": SimpleImpure({"NonLocalVariableWrite.InstanceVariable.B.instance_attr1"}),
            },
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
            {
                "__init__.line3": Pure(),
                "fun.line6": SimpleImpure({"NonLocalVariableRead.InstanceVariable.B.instance_attr1"}),
            },  # TODO: LARS is this corrct?
        ),
        (  # language=Python "VariableRead and VariableWrite in chained class attribute and instance attribute"
            """
class A:
    def __init__(self):
        self.name = 10

    def a_fun(self):
        print(self.name)  # Impure: FileWrite

class B:
    upper_class: A = A()

    def b_fun(self):
        inp = input()  # Impure: FileRead
        return self.upper_class

def f():
    b = B()
    b.upper_class.a_fun()

def g():
    b = B()
    x = b.b_fun().name
            """,  # language=none
            {
                "__init__.line3": Pure(),
                "a_fun.line6": SimpleImpure({"FileWrite.StringLiteral.stdout"}),
                "b_fun.line12": SimpleImpure({"FileRead.StringLiteral.stdin"}),
                "f.line16": SimpleImpure({"FileWrite.StringLiteral.stdout"}),
                "g.line20": SimpleImpure({"FileRead.StringLiteral.stdin"}),
            },
        ),
        (  # language=Python "Function call of functions with same name and different purity"
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

def fun1():
    A.add(1, 2)
    B.add(1, 2)

def fun2():
    B.add(1, 2)
            """,  # language=none
            {
                "add.line4": SimpleImpure({"FileWrite.StringLiteral.stdout"}),
                "add.line10": Pure(),
                "fun1.line13": SimpleImpure({"FileWrite.StringLiteral.stdout"}),
                "fun2.line17": SimpleImpure(
                    {"FileWrite.StringLiteral.stdout"},
                ),  # here we need to be conservative and assume that the call is impure
            },
        ),
        (  # language=Python "Function call of functions with same name (different signatures)"
            """
class A:
    @staticmethod
    def add(a, b):
        return a + b

class B:
    @staticmethod
    def add(a, b, c):
        print(c)  # Impure: FileWrite
        return a + b + c

def fun1():
    A.add(1, 2)

def fun2():
    B.add(1, 2, 3)
            """,  # language=none
            {
                "add.line4": Pure(),
                "add.line9": SimpleImpure({"FileWrite.StringLiteral.stdout"}),
                "fun1.line13": SimpleImpure(
                    {"FileWrite.StringLiteral.stdout"},
                ),  # here we need to be conservative and assume that the call is impure
                "fun2.line16": SimpleImpure({"FileWrite.StringLiteral.stdout"}),
            },  # TODO: [Later] we could also check the signature of the function and see that the call is actually pure
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
            {
                "fun1.line3": SimpleImpure({"NonLocalVariableRead.GlobalVariable.var1"}),
                "fun2.line7": SimpleImpure({"NonLocalVariableRead.GlobalVariable.var1"}),
            },
        ),  # here the reason of impurity for fun2 is propagated to fun1, therefore, fun1 is impure
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
            {
                "fun1.line3": SimpleImpure({"NonLocalVariableRead.GlobalVariable.var1"}),
                "fun2.line7": SimpleImpure({"NonLocalVariableRead.GlobalVariable.var1"}),
                "fun3.line10": SimpleImpure({"NonLocalVariableRead.GlobalVariable.var1"}),
            },
        ),
        (  # language=Python "Call of Impure Chain of Functions with cycle - one entry point"
            """
var1 = 1

def cycle1():
    cycle2()

def cycle2():
    global var1
    res = var1  # Impure: VariableRead from GlobalVariable
    cycle3()

def cycle3():
    print("test")  # Impure: FileWrite
    cycle1()

def entry():
    cycle1()
            """,  # language= None
            {
                "cycle1.line4": SimpleImpure(
                    {"FileWrite.StringLiteral.stdout", "NonLocalVariableRead.GlobalVariable.var1"},
                ),
                "cycle2.line7": SimpleImpure(
                    {"FileWrite.StringLiteral.stdout", "NonLocalVariableRead.GlobalVariable.var1"},
                ),
                "cycle3.line12": SimpleImpure(
                    {"FileWrite.StringLiteral.stdout", "NonLocalVariableRead.GlobalVariable.var1"},
                ),
                "entry.line16": SimpleImpure(
                    {"FileWrite.StringLiteral.stdout", "NonLocalVariableRead.GlobalVariable.var1"},
                ),
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
            {
                "cycle1.line4": SimpleImpure(
                    {"FileWrite.StringLiteral.stdout", "NonLocalVariableWrite.GlobalVariable.var1"},
                ),
                "cycle2.line8": SimpleImpure(
                    {"FileWrite.StringLiteral.stdout", "NonLocalVariableWrite.GlobalVariable.var1"},
                ),
                "cycle3.line11": SimpleImpure(
                    {"FileWrite.StringLiteral.stdout", "NonLocalVariableWrite.GlobalVariable.var1"},
                ),
                "other.line15": SimpleImpure({"NonLocalVariableWrite.GlobalVariable.var1"}),
                "entry.line19": SimpleImpure(
                    {"FileWrite.StringLiteral.stdout", "NonLocalVariableWrite.GlobalVariable.var1"},
                ),
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
            {
                "cycle1.line4": SimpleImpure(
                    {"FileWrite.StringLiteral.stdout", "NonLocalVariableWrite.GlobalVariable.var1"},
                ),
                "cycle2.line7": SimpleImpure(
                    {"FileWrite.StringLiteral.stdout", "NonLocalVariableWrite.GlobalVariable.var1"},
                ),
                "cycle3.line10": SimpleImpure(
                    {"FileWrite.StringLiteral.stdout", "NonLocalVariableWrite.GlobalVariable.var1"},
                ),
                "inner_cycle1.line15": SimpleImpure({"NonLocalVariableWrite.GlobalVariable.var1"}),
                "inner_cycle2.line18": SimpleImpure({"NonLocalVariableWrite.GlobalVariable.var1"}),
                "entry.line23": SimpleImpure(
                    {"FileWrite.StringLiteral.stdout", "NonLocalVariableWrite.GlobalVariable.var1"},
                ),
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
            {
                "fun1.line2": SimpleImpure({"FileWrite.StringLiteral.stdout"}),
                "fun2.line8": SimpleImpure({"FileWrite.StringLiteral.stdout"}),
            },
        ),
        (  # language=Python "Call of Impure Builtin Function"
            """
def fun():
    res = input()  # Impure: Call of Impure Builtin Function - User input is requested
    return res
            """,  # language= None
            {"fun.line2": SimpleImpure({"FileRead.StringLiteral.stdin"})},
        ),
        (  # language=Python "Call of Impure Builtin type class methode"
            """
class A:
    pass

def fun():
    a = A()
    res = a.__class__.__name__  # TODO: this is class methode call
    return res
            """,  # language= None
            {"fun.line5": SimpleImpure({""})},  # TODO: correct result
        ),
        (  # language=Python "Lambda function"
            """
var1 = 1

def fun():
    global var1
    res = (lambda x: x + var1)(10)  # Impure: Call of Lambda Function which has VariableRead from GlobalVariable
    return res
            """,  # language= None
            {"fun.line4": SimpleImpure({"NonLocalVariableRead.GlobalVariable.var1"})},
        ),
        (  # language=Python "Lambda function with Impure Call"
            """
var1 = 1

def fun1():
    res = (lambda x: x + fun2())(10)  # Impure: Call of Lambda Function which calls an Impure function
    return res

def fun2():
    global var1
    return var1  # Impure: VariableRead from GlobalVariable
            """,  # language= None
            {
                "fun1.line4": SimpleImpure({"NonLocalVariableRead.GlobalVariable.var1"}),
                "fun2.line8": SimpleImpure({"NonLocalVariableRead.GlobalVariable.var1"}),
            },
        ),
        (  # language=Python "Assigned Lambda function"
            """
var1 = 1
double = lambda x: var1 * x  # Impure: VariableRead from GlobalVariable
            """,  # language= None
            {"double.line3": SimpleImpure({"NonLocalVariableRead.GlobalVariable.var1"})},
        ),
        (  # language=Python "Lambda as key"
            """
var1 = "x"

def fun():
    global var1
    names = ["a", "abc", "ab", "abcd"]
    sort = sorted(names, key=lambda x: x + var1)  # Impure: Call of Lambda Function which has VariableRead from GlobalVariable
    return sort
            """,  # language= None
            {
                "fun.line4": SimpleImpure(
                    {"NonLocalVariableRead.GlobalVariable.var1", "CallOfParameter.ParameterAccess.key"},
                ),
            },
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
            {
                "fun1.line4": SimpleImpure({
                    "NonLocalVariableRead.GlobalVariable.var1",
                    "NonLocalVariableWrite.GlobalVariable.var1",
                    "FileWrite.StringLiteral.stdout",
                    "FileRead.StringLiteral.stdin",
                }),  # this is propagated from fun2
                "fun2.line12": SimpleImpure({"FileRead.StringLiteral.stdin"}),
            },
        ),
        (  # language=Python "Impure Write to Local and Global",
            """
var1 = 1
var2 = 2
var3 = 3

def fun1(a):
    global var1, var2, var3
    inp = input()  # Impure: Call of Impure Builtin Function - User input is requested
    var1 = a = inp  # Impure: VariableWrite to GlobalVariable
    a = var2 = inp  # Impure: VariableWrite to GlobalVariable
    inp = a = var3  # Impure: VariableRead from GlobalVariable

            """,  # language=none
            {
                "fun1.line6": SimpleImpure({
                    "FileRead.StringLiteral.stdin",
                    "NonLocalVariableWrite.GlobalVariable.var1",
                    "NonLocalVariableWrite.GlobalVariable.var2",
                    "NonLocalVariableRead.GlobalVariable.var3",
                }),
            },
        ),
        (  # language=Python "Call of Function with function as return",
            """
def fun1(a):
    print(a)  # Impure: FileWrite
    return fun1

def fun2():
    x = fun1(1)
            """,  # language=none
            {
                "fun1.line2": SimpleImpure({
                    "FileWrite.StringLiteral.stdout",
                }),
                "fun2.line6": SimpleImpure({
                    "FileWrite.StringLiteral.stdout",
                }),
            },
        ),
        (  # language=Python "Call within a call",
            """
def fun1(a):
    print(a)  # Impure: FileWrite
    return a

def fun2(a):
    return a * 2

def fun3():
    x = fun2(fun1(2))
            """,  # language=none
            {
                "fun1.line2": SimpleImpure({
                    "FileWrite.StringLiteral.stdout",
                }),
                "fun2.line6": Pure(),
                "fun3.line9": SimpleImpure({
                    "FileWrite.StringLiteral.stdout",
                }),
            },
        ),
        (  # language=Python "Async Function"
            """
async def fun1():
    res = await fun2()  # Pure: Call of Pure Function

async def fun2():
    print("test")  # Impure: FileWrite
            """,  # language= None
            {
                "fun1.line2": SimpleImpure({"FileWrite.StringLiteral.stdout"}),
                "fun2.line5": SimpleImpure({"FileWrite.StringLiteral.stdout"}),
            },
        ),
    ],
    ids=[
        "Print with str",
        "Print with parameter",
        "VariableWrite to shadowed GlobalVariable",
        "VariableWrite to GlobalVariable",
        "VariableRead from GlobalVariable",
        "Impure Class initialization",
        "Class methode call",
        "Class methode call of superclass",
        "Class methode call of superclass (overwritten method)",
        "Instance methode call",
        "VariableWrite to ClassVariable",
        "VariableRead from ClassVariable",
        "VariableWrite to InstanceVariable",
        "VariableRead from InstanceVariable",
        "VariableRead and VariableWrite in chained class attribute and instance attribute",
        "Function call of functions with same name and different purity",
        "Function call of functions with same name (different signatures)",
        "Call of Impure Function",
        "Call of Impure Chain of Functions",
        "Call of Impure Chain of Functions with cycle - one entry point",
        "Call of Impure Chain of Functions with cycle - other calls in cycle",
        "Call of Impure Chain of Functions with cycle - cycle in cycle",
        "Call of Impure Chain of Functions with cycle - direct entry",
        "Call of Impure BuiltIn Function",
        "Call of Impure Builtin type class methode",
        "Lambda function",
        "Lambda function with Impure Call",
        "Assigned Lambda function",
        "Lambda as key",
        "Multiple Calls of same Impure function (Caching)",
        "Different Reasons for Impurity",
        "Impure Write to Local and Global",
        "Call of Function with function as return",
        "Call within a call",
        "Async Function",
    ],
)
@pytest.mark.xfail(reason="Some cases disabled for merging")
def test_infer_purity_impure(code: str, expected: dict[str, SimpleImpure]) -> None:
    purity_results = infer_purity(code)

    transformed_purity_results = {
        to_string_function_id(function_id): to_simple_result(purity_result)
        for function_id, purity_result in purity_results.items()
    }

    assert transformed_purity_results == expected


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (  # language=Python "Unknown Call",
            """
def fun1():
    call()
            """,  # language=none
            {
                "fun1.line2": SimpleImpure({"UnknownCall.UnknownFunctionCall.call"}),
            },
        ),
        (  # language=Python "Three Unknown Call",
            """
def fun1():
    call1()
    call2()
    call3()
            """,  # language=none
            {
                "fun1.line2": SimpleImpure({
                    "UnknownCall.UnknownFunctionCall.call1",
                    "UnknownCall.UnknownFunctionCall.call2",
                    "UnknownCall.UnknownFunctionCall.call3",
                }),
            },
        ),
        (  # language=Python "Unknown Call of Parameter",
            """
def fun1(a):
    a()
            """,  # language=none
            {
                "fun1.line2": SimpleImpure({"CallOfParameter.ParameterAccess.a"}),
            },
        ),
        (  # language=Python "Unknown Call of Parameter with many Parameters",
            """
def fun1(function, a, b , c, **kwargs):
    res = function(a, b, c, **kwargs)
            """,  # language=none
            {
                "fun1.line2": SimpleImpure({"CallOfParameter.ParameterAccess.function"}),
            },
        ),
        (  # language=Python "Unknown Callable",
            """
from typing import Callable

def fun1():
    fun = import_fun("functions.py", "fun1")
    fun()

def import_fun(file: str, f_name: str) -> Callable:
    print("test")
    return lambda x: x
            """,  # language=none
            {
                "fun1.line4": SimpleImpure({"FileWrite.StringLiteral.stdout", "UnknownCall.UnknownFunctionCall.fun"}),
                "import_fun.line8": SimpleImpure({"FileWrite.StringLiteral.stdout"}),
            },
        ),
        (  # language=Python "Unknown Call of Function with function as return",
            """
def fun1(a):
    print("Fun1")  # Impure: FileWrite
    if a < 2:
        return fun1
    else:
        return fun2

def fun2(a):
    print("Fun2")  # Impure: FileWrite

def fun3():
    x = fun1(1)(2)(3)  # Here the call is unknown - since fun1 returns a function
            """,  # language=none
            {
                "fun1.line2": SimpleImpure({
                    "FileWrite.StringLiteral.stdout",
                }),
                "fun2.line9": SimpleImpure({
                    "FileWrite.StringLiteral.stdout",
                }),
                "fun3.line12": SimpleImpure({
                    "FileWrite.StringLiteral.stdout",
                    "UnknownCall.UnknownFunctionCall.UNKNOWN",  # This is the worst case where the call node is unknown.
                }),
            },
        ),
    ],
    ids=[
        "Unknown Call",
        "Three Unknown Call",
        "Unknown Call of Parameter",
        "Unknown Call of Parameter with many Parameters",
        "Unknown Callable",
        "Unknown Call of Function with function as return",
    ],
)
# @pytest.mark.xfail(reason="Some cases disabled for merging")
def test_infer_purity_unknown(code: str, expected: dict[str, SimpleImpure]) -> None:
    purity_results = infer_purity(code)

    transformed_purity_results = {
        to_string_function_id(function_id): to_simple_result(purity_result)
        for function_id, purity_result in purity_results.items()
    }

    assert transformed_purity_results == expected


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (  # language=Python "Import module - constant"
            """
import math

def fun1():
    a = math.pi
            """,  # language=none
            {"fun1.line4": SimpleImpure({"NonLocalVariableRead.Import.math.pi"})},
        ),
        (  # language=Python "Import module with alias - constant"
            """
import math as m

def fun1():
    a = m.pi
            """,  # language=none
            {"fun1.line4": SimpleImpure({"NonLocalVariableRead.Import.math.pi"})},
        ),
        (  # language=Python "Import module - function"
            """
import math

def fun1(a):
    math.sqrt(a)
            """,  # language=none
            {"fun1.line4": SimpleImpure({"UnknownCall.UnknownFunctionCall.math.sqrt"})},
        ),
        (  # language=Python "Import module with alias - function"
            """
import math as m

def fun1(a):
    m.sqrt(a)
            """,  # language=none
            {"fun1.line4": SimpleImpure({"UnknownCall.UnknownFunctionCall.math.sqrt"})},
        ),
        (  # language=Python "Import module with alias - function and constant"
            """
import math as m

def fun1(a):
    a = m.pi
    m.sqrt(a)
            """,  # language=none
            {
                "fun1.line4": SimpleImpure(
                    {"UnknownCall.UnknownFunctionCall.math.sqrt", "NonLocalVariableRead.Import.math.pi"},
                ),
            },
        ),
        (  # language=Python "FromImport - constant"
            """
from math import pi

def fun1():
    a = pi
            """,  # language=none
            {"fun1.line4": SimpleImpure({"NonLocalVariableRead.Import.math.pi"})},
        ),
        (  # language=Python "FromImport with alias - constant"
            """
from math import pi as p

def fun1():
    a = p
            """,  # language=none
            {"fun1.line4": SimpleImpure({"NonLocalVariableRead.Import.math.pi"})},
        ),
        (  # language=Python "FromImport - function"
            """
from math import sqrt

def fun1(a):
    sqrt(a)
            """,  # language=none
            {"fun1.line4": SimpleImpure({"UnknownCall.UnknownFunctionCall.math.sqrt"})},
        ),
        (  # language=Python "FromImport with alias - function"
            """
from math import sqrt as s

def fun1(a):
    s(a)
            """,  # language=none
            {"fun1.line4": SimpleImpure({"UnknownCall.UnknownFunctionCall.math.sqrt"})},
        ),
        (  # language=Python "FromImport with alias - function and constant"
            """
from math import sqrt as s, pi as p

def fun1(a):
    a = p
    s(a)
            """,  # language=none
            {
                "fun1.line4": SimpleImpure(
                    {"UnknownCall.UnknownFunctionCall.math.sqrt", "NonLocalVariableRead.Import.math.pi"},
                ),
            },
        ),
        (  # language=Python "FromImport MemberAccess with alias - class"
            """
from collections.abc import Callable

def fun1(a):
    a = Callable()
            """,  # language=none
            {"fun1.line4": SimpleImpure({"UnknownCall.UnknownClassInit._collections_abc.Callable"})},
        ),
        (  # language=Python "Local Import - function"
            """
def fun1(a):
    import math
    a = math.sqrt(a)
            """,  # language=none
            {"fun1.line2": SimpleImpure({"UnknownCall.UnknownFunctionCall.math.sqrt"})},
        ),
        (  # language=Python "Local FromImport - constant"
            """
def fun1(a):
    from math import pi
    a = pi
            """,  # language=none
            {"fun1.line2": SimpleImpure({"NonLocalVariableRead.Import.math.pi"})},
        ),
        (  # language=Python "Local FromImport - function"
            """
def fun1(a):
    from math import sqrt
    sqrt(a)
            """,  # language=none
            {"fun1.line2": SimpleImpure({"UnknownCall.UnknownFunctionCall.math.sqrt"})},
        ),
        (  # language=Python "Write to Import"
            """
import math as m

def fun1():
    m.pi = 1
            """,  # language=none
            {"fun1.line4": SimpleImpure({"NonLocalVariableWrite.Import.math.pi"})},
        ),
    ],
    ids=[
        "Import module - constant",
        "Import module with alias - constant",
        "Import module - function",
        "Import module with alias - function",
        "Import module with alias - function and constant",
        "FromImport - constant",
        "FromImport with alias - constant",
        "FromImport - function",
        "FromImport with alias - function",
        "FromImport with alias - function and constant",
        "FromImport MemberAccess with alias - class",
        "Local Import - function",
        "Local FromImport - constant",
        "Local FromImport - function",
        "Write to Import",
    ],
)  # TODO: to test this correctly we need real imports from modules that are no dubs
def test_infer_purity_import(code: str, expected: dict[str, SimpleImpure]) -> None:
    purity_results = infer_purity(code)

    transformed_purity_results = {
        to_string_function_id(function_id): to_simple_result(purity_result)
        for function_id, purity_result in purity_results.items()
    }

    assert transformed_purity_results == expected


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (  # language=Python "Open with str default"
            """
def fun():
    open("text.txt")  # Impure: FileRead
            """,  # language= None
            {"fun.line2": SimpleImpure({"FileRead.StringLiteral.text.txt"})},
        ),
        (  # language=Python "Open with str read"
            """
def fun():
    open("text.txt", "r")  # Impure: FileRead
            """,  # language= None
            {"fun.line2": SimpleImpure({"FileRead.StringLiteral.text.txt"})},
        ),
        (  # language=Python "Open with str write"
            """
def fun():
    open("text.txt", "wb")  # Impure: FileWrite
            """,  # language= None
            {"fun.line2": SimpleImpure({"FileWrite.StringLiteral.text.txt"})},
        ),
        (  # language=Python "Open with str read and write"
            """
def fun():
    open("text.txt", "a+")  # Impure: FileRead and FileWrite
            """,  # language= None
            {"fun.line2": SimpleImpure({"FileRead.StringLiteral.text.txt", "FileWrite.StringLiteral.text.txt"})},
        ),
        (  # language=Python "Open with parameter default"
            """
def fun(pos_arg):
    open(pos_arg)  # Impure: FileRead
            """,  # language= None
            {"fun.line2": SimpleImpure({"FileRead.ParameterAccess.pos_arg"})},
        ),
        (  # language=Python "Open with parameter write"
            """
def fun(pos_arg):
    open(pos_arg, "a")  # Impure: FileWrite
            """,  # language= None
            {"fun.line2": SimpleImpure({"FileWrite.ParameterAccess.pos_arg"})},
        ),
        (  # language=Python "Read"
            """
def fun():
    f = open("text.txt")  # Impure: FileRead
    f.read()  # TODO: [Later] For now open is enough
            """,  # language= None
            {"fun.line2": SimpleImpure({"FileRead.StringLiteral.text.txt"})},
        ),
        (  # language=Python "Readline/ Readlines"
            """
def fun():
    f = open("text.txt")  # Impure: FileRead
    f.readline()  # TODO: [Later] For now open is enough
    f.readlines()  # TODO: [Later] For now open is enough
            """,  # language= None
            {"fun.line2": SimpleImpure({"FileRead.StringLiteral.text.txt"})},
        ),
        (  # language=Python "Write"
            """
def fun():
    f = open("text.txt", "w")  # Impure: FileWrite
    f.write("test")  # TODO: [Later] For now open is enough
            """,  # language= None
            {"fun.line2": SimpleImpure({"FileWrite.StringLiteral.text.txt"})},
        ),
        (  # language=Python "Writelines"
            """
def fun():
    f = open("text.txt", "w")  # Impure: FileWrite
    f.writelines(["test1", "test2"])  # TODO: [Later] For now open is enough
            """,  # language= None
            {"fun.line2": SimpleImpure({"FileWrite.StringLiteral.text.txt"})},
        ),
        (  # language=Python "With open str default"
            """
def fun():
    with open("text.txt") as f:  # Impure: FileRead
        f.read()
            """,  # language= None
            {"fun.line2": SimpleImpure({"FileRead.StringLiteral.text.txt"})},
        ),
        (  # language=Python "With open parameter default"
            """
def fun(pos_arg):
    with open(pos_arg) as f:  # Impure: FileRead
        f.read()
            """,  # language= None
            {"fun.line2": SimpleImpure({"FileRead.ParameterAccess.pos_arg"})},
        ),
        (  # language=Python "With open parameter read and write"
            """
def fun(pos_arg):
    with open(pos_arg, "wb+") as f:  # Impure: FileRead and FileWrite
        f.read()
            """,  # language= None
            {"fun.line2": SimpleImpure({"FileRead.ParameterAccess.pos_arg", "FileWrite.ParameterAccess.pos_arg"})},
        ),
        (  # language=Python "With open parameter and variable mode"
            """
def fun(pos_arg, mode):
    with open(pos_arg, mode) as f:  # Impure: FileRead and FileWrite
        f.read()
            """,  # language= None
            {"fun.line2": SimpleImpure({"FileRead.ParameterAccess.pos_arg", "FileWrite.ParameterAccess.pos_arg"})},
        ),  # TODO: do we want to expect the worst case here?
        (  # language=Python "With open close"
            """
def fun():
    with open("text.txt") as f:  # Impure: FileRead
        f.read()
        f.close()  # TODO: [Later] For now open is enough
            """,  # language= None
            {"fun.line2": SimpleImpure({"FileRead.StringLiteral.text.txt"})},
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
    purity_results = infer_purity(code)

    transformed_purity_results = {
        to_string_function_id(function_id): to_simple_result(purity_result)
        for function_id, purity_result in purity_results.items()
    }

    assert transformed_purity_results == expected
