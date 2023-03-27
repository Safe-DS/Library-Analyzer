from abc import ABC
from copy import copy
from dataclasses import dataclass
from enum import Enum, auto

import astroid

from library_analyzer.processing.api.model import ImpurityIndicator, VariableRead, Call, FileWrite, \
    StringLiteral, ImpurityCertainty, Reference, FileRead, BuiltInFunction, SystemInteraction, VariableWrite, \
    ConcreteImpurityIndicator
from library_analyzer.utils import ASTWalker

BUILTIN_FUNCTIONS = {
    "open": BuiltInFunction(Reference("open"), ConcreteImpurityIndicator(), ImpurityCertainty.DEFINITELY_IMPURE),
    # TODO: how to replace the ... with the correct type?
    "print": BuiltInFunction(Reference("print"), SystemInteraction(), ImpurityCertainty.DEFINITELY_IMPURE),

    "read": BuiltInFunction(Reference("read"), ConcreteImpurityIndicator(), ImpurityCertainty.DEFINITELY_IMPURE),
    "write": BuiltInFunction(Reference("write"), ConcreteImpurityIndicator(), ImpurityCertainty.DEFINITELY_IMPURE),
    "readline": BuiltInFunction(Reference("readline"), ConcreteImpurityIndicator(), ImpurityCertainty.DEFINITELY_IMPURE),
    "readlines": BuiltInFunction(Reference("readlines"), ConcreteImpurityIndicator(), ImpurityCertainty.DEFINITELY_IMPURE),
    "writelines": BuiltInFunction(Reference("writelines"), ConcreteImpurityIndicator(), ImpurityCertainty.DEFINITELY_IMPURE),
    "close": BuiltInFunction(Reference("close"), ConcreteImpurityIndicator(), ImpurityCertainty.DEFINITELY_PURE),
}


@dataclass
class FunctionID:
    module: str
    name: str
    line: int
    col: int

    def __str__(self) -> str:
        return f"{self.module}.{self.name}.{self.line}.{self.col}"


class PurityResult(ABC):
    def __init__(self) -> None:
        self.reasons = []


@dataclass
class DefinitelyPure(PurityResult):
    reasons = []


@dataclass
class MaybeImpure(PurityResult):
    reasons: list[ImpurityIndicator]

    def __hash__(self) -> int:
        return hash(tuple(self.reasons))


@dataclass
class DefinitelyImpure(PurityResult):
    reasons: list[ImpurityIndicator]

    def __hash__(self) -> int:
        return hash(tuple(self.reasons))


@dataclass
class PurityInformation:
    id: FunctionID
    # purity: PurityResult
    reasons: list[ImpurityIndicator]

    def __hash__(self) -> int:
        return hash((self.id, self.reasons))

    def __eq__(self, other) -> bool:
        return self.id == other.id and self.reasons == other.reasons


class PurityHandler:
    def __init__(self) -> None:
        self.purity_reason: list[ImpurityIndicator] = []

    def append_reason(self, reason: list[ImpurityIndicator]) -> None:
        for r in reason:
            self.purity_reason.append(r)

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
            self.append_reason([VariableWrite(Reference(node.as_string()))])
        else:  # default case
            self.append_reason([VariableWrite(Reference(node.as_string()))])
        # TODO: Assign node needs further analysis to determine if it is pure or impure

    def enter_assignattr(self, node: astroid.AssignAttr) -> None:
        # print(f"Entering AssignAttr node {node.as_string()}")
        # Handle the AssignAtr node here
        self.append_reason([VariableWrite(Reference(node.as_string()))])
        # TODO: AssignAttr node needs further analysis to determine if it is pure or impure

    def enter_call(self, node: astroid.Call) -> None:
        # print(f"Entering Call node {node.as_string()}")
        # Handle the Call node here
        if isinstance(node.func, astroid.Attribute):
            pass
        elif isinstance(node.func, astroid.Name):
            if node.func.name in BUILTIN_FUNCTIONS:
                impurity_indicator = check_builtin_function(node, node.func.name, node.args[0].value)
                self.append_reason(impurity_indicator)

        self.append_reason([Call(Reference(node.as_string()))])
        # TODO: Call node needs further analysis to determine if it is pure or impure

    def enter_attribute(self, node: astroid.Attribute) -> None:
        # print(f"Entering Attribute node {node.as_string()}")
        # Handle the Attribute node here
        impurity_indicator: list[ImpurityIndicator] = []
        if isinstance(node.expr, astroid.Name):
            if node.attrname in BUILTIN_FUNCTIONS:
                impurity_indicator = check_builtin_function(node, node.attrname)
                self.append_reason(impurity_indicator)
        else:
            self.append_reason([Call(Reference(node.as_string()))])

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
    BOTH = auto()
    UNKNOWN = auto()


def determine_open_mode(node: astroid.NodeNG) -> OpenMode:
    write_mode = {"w", "wb", "a", "ab", "x", "xb"}
    read_mode = {"r", "rb"}
    read_and_write_mode = {"r+", "rb+", "w+", "wb+", "a+", "ab+", "x+", "xb+"}
    if len(node.args) == 1:
        return OpenMode.READ
    for arg in node.args:
        if str(arg.value) in write_mode:
            return OpenMode.WRITE

        if str(arg.value) in read_mode:
            return OpenMode.READ

        if str(arg.value) in read_and_write_mode:
            return OpenMode.BOTH

    return OpenMode.UNKNOWN


def check_builtin_function(node: astroid.NodeNG, key: str, value: str = None) -> list[ImpurityIndicator]:
    impurity_indicator: list[ImpurityIndicator] = []
    builtin_function = copy(BUILTIN_FUNCTIONS[key])

    if isinstance(value, str):
        if key == "open":
            open_mode = determine_open_mode(node)
            if open_mode == OpenMode.WRITE:  # write mode
                # set ImpurityIndicator to FileWrite
                builtin_function.indicator = FileWrite(StringLiteral(value))
                impurity_indicator = [builtin_function.indicator]

            elif open_mode == OpenMode.READ:  # read mode
                # set ImpurityIndicator to FileRead
                builtin_function.indicator = FileRead(StringLiteral(value))
                impurity_indicator = [builtin_function.indicator]

            elif open_mode == OpenMode.BOTH:  # read and write mode
                # set ImpurityIndicator to FileReadWrite and FileWrite
                builtin_function.indicator = [FileRead(StringLiteral(value)), FileWrite(StringLiteral(value))]
                impurity_indicator = list(builtin_function.indicator)

        else:
            print(f"Unknown builtin function {key}")
    # TODO: handle the case where the argument is not a string literal
    else:
        if key == "read":
            builtin_function.indicator = VariableRead(Reference(node.as_string()))
            impurity_indicator = [builtin_function.indicator]
        elif key in ("write", "writelines"):
            builtin_function.indicator = VariableWrite(Reference(node.as_string()))
            impurity_indicator = [builtin_function.indicator]
        elif key in ("readline", "readlines"):
            builtin_function.indicator = VariableRead(Reference(node.as_string()))
            impurity_indicator = [builtin_function.indicator]

    return impurity_indicator


def infer_purity(code: str) -> list[PurityInformation]:
    purity_handler: PurityHandler = PurityHandler()
    walker = ASTWalker(purity_handler)
    functions = get_function_defs(code)
    result = []
    for function in functions:
        # print(function)
        # print(f"Analyse {function.name}:")
        walker.walk(function)
        purity_result = determine_purity(purity_handler.purity_reason)
        # print(f"Result: {purity_result.__class__.__name__}")
        # if not isinstance(purity_result, DefinitelyPure):
        #    print(f"Reasons: {purity_result.reasons}")
        # print(f"Function {function.name} is done. \n")
        result.append(generate_purity_information(function, purity_result))
        purity_handler.purity_reason = []
    return result


def determine_purity(indicators: list[ImpurityIndicator]) -> PurityResult:
    if len(indicators) == 0:
        return DefinitelyPure()
    if any(indicator.certainty == ImpurityCertainty.DEFINITELY_IMPURE for indicator in indicators):
        return DefinitelyImpure(reasons=indicators)

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


def get_function_defs(code: str) -> list[astroid.FunctionDef]:
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
    return list(purity.reasons)


def generate_purity_information(function: astroid.FunctionDef, purity_result: PurityResult) -> PurityInformation:
    function_id = calc_function_id(function)
    reasons = extract_impurity_reasons(purity_result)
    purity_info = PurityInformation(function_id, reasons)
    return purity_info


def calc_function_id(node: astroid.NodeNG) -> FunctionID:
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
    result_list = infer_purity(sourcecode)
    for f in result_list:
        p = get_purity_result_str(f.reasons)
        print(f"Function {f.id.name} with ID: {f.id} is {p} because {f.reasons}")
