from abc import ABC
from copy import copy
from dataclasses import dataclass
from enum import Enum, auto

import astroid

from library_analyzer.processing.api.model import ImpurityIndicator, VariableRead, AttributeAccess, Call, FileWrite, \
    StringLiteral, ImpurityCertainty, Reference, FileRead, BuiltInFunction, SystemInteraction, VariableWrite, Expression
from library_analyzer.utils import ASTWalker

BUILTIN_FUNCTIONS = {
    "open": BuiltInFunction(Reference("open"), ..., ImpurityCertainty.DEFINITELY_IMPURE),
    # TODO: how to replace the ... with the correct type?
    "print": BuiltInFunction(Reference("print"), SystemInteraction(), ImpurityCertainty.DEFINITELY_IMPURE),

    "read": BuiltInFunction(Reference("read"), ..., ImpurityCertainty.DEFINITELY_IMPURE),
    "write": BuiltInFunction(Reference("write"), ..., ImpurityCertainty.DEFINITELY_IMPURE),
    "readline": BuiltInFunction(Reference("readline"), ..., ImpurityCertainty.DEFINITELY_IMPURE),
    "readlines": BuiltInFunction(Reference("readlines"), ..., ImpurityCertainty.DEFINITELY_IMPURE),
    "writelines": BuiltInFunction(Reference("writelines"), ..., ImpurityCertainty.DEFINITELY_IMPURE),
    "close": BuiltInFunction(Reference("close"), ..., ImpurityCertainty.DEFINITELY_PURE),
}


@dataclass
class FunctionID:
    module: str
    name: str
    line: int
    col: int

    def __str__(self):
        return f"{self.module}.{self.name}.{self.line}.{self.col}"


class PurityResult(ABC):
    def __init__(self):
        self.reasons = None


@dataclass
class DefinitelyPure(PurityResult):
    reasons = None


@dataclass
class MaybeImpure(PurityResult):
    reasons: list[ImpurityIndicator]

    def __hash__(self):
        return hash(tuple(self.reasons))


@dataclass
class DefinitelyImpure(PurityResult):
    reasons: list[ImpurityIndicator]

    def __hash__(self):
        return hash(tuple(self.reasons))


@dataclass
class PurityInformation:
    id: FunctionID
    # purity: PurityResult
    reasons: list[ImpurityIndicator]

    def __hash__(self):
        return hash((self.id, self.reasons))

    def __eq__(self, other):
        return self.id == other.id and self.reasons == other.reasons


_result_list = list[PurityInformation]()


class PurityHandler:
    def __init__(self):
        self.purity_reason = list[ImpurityIndicator]()

    def enter_functiondef(self, node: astroid.FunctionDef) -> None:
        # print(f"Enter functionDef node: {node.as_string()}")
        # Handle the FunctionDef node here
        pass  # Are we analyzing function defs within function defs? Yes, we are.

    def enter_assign(self, node: astroid.Assign) -> None:
        # print(f"Entering Assign node {node}")
        # Handle the Assign node here
        if isinstance(node.value, astroid.Call):
            pass
        if isinstance(node.value, astroid.Const):
            impurity_indicator: ImpurityIndicator = VariableWrite(node.as_string())
            self.purity_reason.append(impurity_indicator)
        else:  # default case
            impurity_indicator: ImpurityIndicator = VariableWrite(node.as_string())
            self.purity_reason.append(impurity_indicator)
        # TODO: Assign node needs further analysis to determine if it is pure or impure

    def enter_assignattr(self, node: astroid.AssignAttr) -> None:
        # print(f"Entering AssignAttr node {node.as_string()}")
        # Handle the AssignAtr node here
        impurity_indicator: ImpurityIndicator = VariableWrite(node.as_string())
        self.purity_reason.append(impurity_indicator)
        # TODO: AssignAttr node needs further analysis to determine if it is pure or impure

    def enter_call(self, node: astroid.Call) -> None:
        # print(f"Entering Call node {node.as_string()}")
        # Handle the Call node here
        # TODO: move analysis of built-in functions to a separate function
        if isinstance(node.func, astroid.Attribute):
            pass
        if isinstance(node.func, astroid.Name):
            if node.func.name in BUILTIN_FUNCTIONS.keys():
                impurity_indicator = check_builtin_function(node, node.func.name, node.args[0].value)
                self.purity_reason.append(impurity_indicator)
        # else:
            # impurity_indicator: ImpurityIndicator = Call(Reference(node.as_string()))
            # self.purity_reason.append(impurity_indicator)
        # TODO: Call node needs further analysis to determine if it is pure or impure

    def enter_attribute(self, node: astroid.Attribute) -> None:
        # print(f"Entering Attribute node {node.as_string()}")
        # Handle the Attribute node here
        if isinstance(node.expr, astroid.Name):
            if node.attrname in BUILTIN_FUNCTIONS.keys():
                impurity_indicator = check_builtin_function(node, node.attrname)
                self.purity_reason.append(impurity_indicator)
        else:
            impurity_indicator: ImpurityIndicator = Call(Reference(node.as_string()))
            self.purity_reason.append(impurity_indicator)

    def enter_arguments(self, node: astroid.Arguments) -> None:
        # print(f"Entering Arguments node {node.as_string()}")
        # Handle the Arguments node here
        pass

    def enter_expr(self, node: astroid.Expr) -> None:
        # print(f"Entering Expr node {node.as_string()}")
        # print(node.value)
        # Handle the Expr node here
        pass

    def enter_name(self, node: astroid.Name) -> None:
        # print(f"Entering Name node {node.as_string()}")
        # Handle the Name node here
        pass

    def enter_const(self, node: astroid.Const) -> None:
        # print(f"Entering Const node {node.as_string()}")
        # Handle the Const node here
        pass

    def enter_assignname(self, node: astroid.AssignName) -> None:
        # print(f"Entering AssignName node {node.as_string()}")
        # Handle the AssignName node here
        pass

    def enter_with(self, node: astroid.With) -> None:
        # print(f"Entering With node {node.as_string()}")
        # Handle the With node here
        pass


class OpenMode(Enum):
    READ = auto()
    WRITE = auto()
    UNKNOWN = auto()


def determine_open_mode(node: astroid.NodeNG) -> OpenMode:
    write_mode = {"w", "wb", "a", "ab", "x", "xb", "w+", "wb+", "a+", "ab+", "x+", "xb+"}
    read_mode = {"r", "rb", "r+", "rb+"}
    if len(node.args) == 1:
        return OpenMode.READ
    for arg in node.args:
        if str(arg.value) in write_mode:
            return OpenMode.WRITE

        elif str(arg.value) in read_mode:
            return OpenMode.READ
    # TODO: check if the mode is both read and write
    return OpenMode.UNKNOWN


def check_builtin_function(node: astroid.NodeNG, key: str, value=None) -> ImpurityIndicator:
    impurity_indicator: ImpurityIndicator
    builtin_function = copy(BUILTIN_FUNCTIONS[key])

    if type(value) == str:
        if key == "open":
            open_mode = determine_open_mode(node)
            if open_mode == OpenMode.WRITE:  # write mode
                # set ImpurityIndicator to FileWrite
                builtin_function.indicator = FileWrite(StringLiteral(value))
                impurity_indicator = builtin_function.indicator

            elif open_mode == OpenMode.READ:  # read mode
                # set ImpurityIndicator to FileRead
                builtin_function.indicator = FileRead(StringLiteral(value))
                impurity_indicator = builtin_function.indicator
            else:
                pass

        else:
            print(f"Unknown builtin function {key}")
    # TODO: handle the case where the argument is not a string literal
    else:
        if key == "read":
            builtin_function.indicator = VariableRead(Reference(node.as_string()))
            impurity_indicator = builtin_function.indicator
        elif key == "write" or key == "writelines":
            builtin_function.indicator = VariableWrite(Reference(node.as_string()))
            impurity_indicator = builtin_function.indicator
        elif key == "readline" or key == "readlines":
            builtin_function.indicator = VariableRead(Reference(node.as_string()))
            impurity_indicator = builtin_function.indicator
        pass

    return impurity_indicator


def infer_purity(code: str) -> list[PurityInformation]:
    purity_handler: PurityHandler = PurityHandler()
    walker = ASTWalker(purity_handler)
    functions = get_function_defs(code)
    for function in functions:
        # print(function)
        # print(f"Analyse {function.name}:")
        walker.walk(function)
        purity_result = determine_purity(purity_handler.purity_reason)
        # print(f"Result: {purity_result.__class__.__name__}")
        # if not isinstance(purity_result, DefinitelyPure):
        #    print(f"Reasons: {purity_result.reasons}")
        # print(f"Function {function.name} is done. \n")
        _result_list.append(generate_purity_information(function, purity_result))
        purity_handler.purity_reason = []
    return _result_list


def determine_purity(indicators: list[ImpurityIndicator]) -> PurityResult:
    if len(indicators) == 0:
        return DefinitelyPure()
    if any(indicator.certainty == ImpurityCertainty.DEFINITELY_IMPURE for indicator in indicators):
        return DefinitelyImpure(reasons=indicators)
    else:
        return MaybeImpure(reasons=indicators)

    # print(f"Maybe check {(any(purity_reason.is_reason_for_impurity() for purity_reason in purity_reasons))}")
    # if any(reason.is_reason_for_impurity() for reason in purity_reasons):
    #     # print(f"Definitely check {any(isinstance(reason, Call) for reason in purity_reasons)}")
    #     result = MaybeImpure(reasons=purity_reasons)
    #     if any(isinstance(reason, Call) for reason in purity_reasons):
    #         return DefinitelyImpure(reasons=purity_reasons)
    #     return result
    # else:
    #     return DefinitelyPure()


def get_function_defs(code) -> list[astroid.FunctionDef]:
    try:
        module = astroid.parse(code)
    except SyntaxError as error:
        raise ValueError("Invalid Python code") from error

    function_defs = list[astroid.FunctionDef]()
    for node in module.body:
        if isinstance(node, astroid.FunctionDef):
            function_defs.append(node)
    return function_defs
    # TODO: This function should read from a python file (module) and return a list of FunctionDefs


def extract_impurity_reasons(purity: PurityResult) -> list[ImpurityIndicator]:
    if isinstance(purity, DefinitelyPure):
        return []
    return purity.reasons


def generate_purity_information(function: astroid.FunctionDef, purity_result: PurityResult) -> PurityInformation:
    function_id = calc_function_id(function)
    reasons = extract_impurity_reasons(purity_result)
    purity_info = PurityInformation(function_id, reasons)
    return purity_info


def calc_function_id(node) -> FunctionID:
    if not isinstance(node, astroid.FunctionDef):
        raise TypeError("Node is not a function")
    module = node.root().name
    # module = "_infer_purity.py"
    if module.endswith(".py"):
        module = module[:-3]
    name = node.name
    line = node.position.lineno
    col = node.position.col_offset
    return FunctionID(module, name, line, col)


# this function is only for visualization purposes
def get_purity_result_str(indicators: list[ImpurityIndicator]) -> str:
    if len(indicators) == 0:
        return "Definitely Pure"
    if any(indicator.certainty == ImpurityCertainty.DEFINITELY_IMPURE for indicator in indicators):
        return "Definitely Impure"
    else:
        return "Maybe Impure"


if __name__ == '__main__':
    sourcecode = """
    def impure_fun(a):
        impure_call(a) # call => impure
        impure_call(a) # call => impure - check if the analysis is correct for multiple calls - done
        return a

    def pure_fun(a):
        a += 1
        return a

    class A:
        def __init__(self):
            self.value = 42

        a = A()

        def instance(a):
            res = a.value # InstanceAccess => pure??
            return res

    class B:
        name = "test"
    b = B()
    def attribute(b):
        res = b.name # AttributeAccess => maybe impure
        return res

    global_var = 17
    def global_access():
        res = global_var # GlobalAccess => impure
        return res

    def parameter_access(a):
        res = a # ParameterAccess => pure
        return res

    glob = g(1)  # TODO: This will get filtered out because it is not a function call, but a variable assignment with a
    # function call and therefore further analysis is needed

    def fun(a):  # TODO: this function oddly has three calls in the results
        h(a)
        b =  g(a) # call => impure
        b += 1
        return b

    """
    a = """

    def fun1():
        open("test1.txt") # default mode: read only

    def fun2():
        open("test2.txt", "r") # read only

    def fun3():
        open("test3.txt", "w") # write only

    def fun4():
        open("test4.txt", "a") # append

    def fun5():
        open("test5.txt", "r+")  # read and write

    def fun6():
        f = open("test6.txt") # default mode: read only
        f.read()

    def fun7():
        f = open("test7.txt") # default mode: read only
        f.readline([2])

    def fun8():
        f = open("test8.txt", "w") # write only
        f.write("message")

    def fun9():
        f = open("test9.txt", "w") # write only
        f.writelines(["message1", "message2"])


    """

    infer_purity(a)
    for f in _result_list:
        p = get_purity_result_str(f.reasons)
        print(f"Function {f.id.name} with ID: {f.id} is {p} because {f.reasons}")

    a = """
    def fun1():
        open("test1.txt") # default mode: read only

    def fun2():
        open("test2.txt", "r") # read only

    def fun3():
        open("test3.txt", "w") # write only

    def fun4():
        open("test4.txt", "a") # append

    def fun5():
        open("test5.txt", "r+")  # read and write

    def fun6():
        f = open("test6.txt") # default mode: read only
        f.read()

    def fun7():
        f = open("test7.txt") # default mode: read only
        f.readline([2])

    def fun8():
        f = open("test8.txt", "w") # write only
        f.write("message")

    def fun9():
        f = open("test9.txt", "w") # write only
        f.writelines(["message1", "message2"])

    def fun10():
        with open("test10.txt") as f: # default mode: read only
            f.read()

    def fun11(path11): # open with variable
        open(path11)

    def fun12(path12):
        with open(path12) as f:
            f.read()

    """
