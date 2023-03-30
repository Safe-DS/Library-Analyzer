from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

import astroid
from library_analyzer.processing.api.model import (
    BuiltInFunction,
    Call,
    ConcreteImpurityIndicator,
    FileRead,
    FileWrite,
    ImpurityCertainty,
    ImpurityIndicator,
    Reference,
    StringLiteral,
    SystemInteraction,
    VariableRead,
    VariableWrite,
    InstanceAccess,
)
from library_analyzer.utils import ASTWalker

BUILTIN_FUNCTIONS = {
    "open": BuiltInFunction(Reference("open"), ConcreteImpurityIndicator(), ImpurityCertainty.DEFINITELY_IMPURE),
    # TODO: how to replace the ... with the correct type?
    "print": BuiltInFunction(Reference("print"), SystemInteraction(), ImpurityCertainty.DEFINITELY_IMPURE),
    "read": BuiltInFunction(Reference("read"), ConcreteImpurityIndicator(), ImpurityCertainty.DEFINITELY_IMPURE),
    "write": BuiltInFunction(Reference("write"), ConcreteImpurityIndicator(), ImpurityCertainty.DEFINITELY_IMPURE),
    "readline": BuiltInFunction(
        Reference("readline"), ConcreteImpurityIndicator(), ImpurityCertainty.DEFINITELY_IMPURE
    ),
    "readlines": BuiltInFunction(
        Reference("readlines"), ConcreteImpurityIndicator(), ImpurityCertainty.DEFINITELY_IMPURE
    ),
    "writelines": BuiltInFunction(
        Reference("writelines"), ConcreteImpurityIndicator(), ImpurityCertainty.DEFINITELY_IMPURE
    ),
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
        self.reasons: list[ImpurityIndicator] = []


@dataclass
class DefinitelyPure(PurityResult):
    reasons = []


@dataclass
class MaybeImpure(PurityResult):
    reasons: list[ImpurityIndicator]

    # def __hash__(self) -> int:
    #     return hash(tuple(self.reasons))


@dataclass
class DefinitelyImpure(PurityResult):
    reasons: list[ImpurityIndicator]

    # def __hash__(self) -> int:
    #     return hash(tuple(self.reasons))


@dataclass
class PurityInformation:
    id: FunctionID
    # purity: PurityResult
    reasons: list[ImpurityIndicator]

    # def __hash__(self) -> int:
    #     return hash((self.id, self.reasons))

    # def __eq__(self, other: object) -> bool:
    #     if not isinstance(other, PurityInformation):
    #         return NotImplemented
    #     return self.id == other.id and self.reasons == other.reasons


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
        # print(f"Entering Assign node {node}, {node.as_string()}")
        # Handle the Assign node here
        if isinstance(node.value, astroid.Call):
            self.append_reason([VariableWrite(Reference(node.as_string()))])
        elif isinstance(node.value, astroid.Const):
            self.append_reason([VariableWrite(Reference(node.as_string()))])
        # else:  # default case
        #     for child in node.parent.get_children():
        #         if isinstance(child, astroid.Assign):
        #             target = child.value.attrname
        #         elif isinstance(child, astroid.Name):
        #             target = child.name
        #     self.append_reason([VariableWrite(InstanceAccess(
        #         receiver=Reference(node.parent.get_children().__next__().as_string()),
        #         target=Reference(target)
        #     ))])
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
                value = node.args[0]
                if isinstance(value, astroid.Name):
                    impurity_indicator = check_builtin_function(node, node.func.name, value.name, True)
                    self.append_reason(impurity_indicator)
                else:
                    impurity_indicator = check_builtin_function(node, node.func.name, value.value)
                    self.append_reason(impurity_indicator)

        self.append_reason([Call(Reference(node.as_string()))])
        # TODO: Call node needs further analysis to determine if it is pure or impure

    def enter_attribute(self, node: astroid.Attribute) -> None:
        # print(f"Entering Attribute node {node.as_string()}")
        # Handle the Attribute node here
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
        #print(f"Entering Name node {node.as_string()}")
        # Handle the Name node here
        # if isinstance(node.parent, astroid.AssignAttr) and node.parent.expr == node:
        #     print(f"{node.name} is an attribute")
        # elif isinstance(node.parent, astroid.Call) and node.parent.func == node:
        #     print(f"{node.name} is an instance")
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
    READ_WRITE = auto()


def determine_open_mode(args: list[str]) -> OpenMode:
    write_mode = {"w", "wb", "a", "ab", "x", "xb", "wt", "at", "xt"}
    read_mode = {"r", "rb", "rt"}
    read_and_write_mode = {
        "r+",
        "rb+",
        "w+",
        "wb+",
        "a+",
        "ab+",
        "x+",
        "xb+",
        "r+t",
        "rb+t",
        "w+t",
        "wb+t",
        "a+t",
        "ab+t",
        "x+t",
        "xb+t",
        "r+b",
        "rb+b",
        "w+b",
        "wb+b",
        "a+b",
        "ab+b",
        "x+b",
        "xb+b",
    }
    if len(args) == 1:
        return OpenMode.READ

    mode = args[1]
    if isinstance(mode, astroid.Const):
        mode = mode.value

    if mode in read_mode:
        return OpenMode.READ
    if mode in write_mode:
        return OpenMode.WRITE
    if mode in read_and_write_mode:
        return OpenMode.READ_WRITE

    raise ValueError(f"{mode} is not a valid mode for the open function")


def check_builtin_function(
    node: astroid.NodeNG, key: str, value: Optional[str] = None, is_var: bool = False
) -> list[ImpurityIndicator]:
    if isinstance(value, str):
        if key == "open":
            open_mode = determine_open_mode(node.args)
            match open_mode:
                case OpenMode.WRITE:
                    if is_var:
                        return [FileWrite(Reference(value))]
                    return [FileWrite(StringLiteral(value))]
                case OpenMode.READ:
                    if is_var:
                        return [FileRead(Reference(value))]
                    return [FileRead(StringLiteral(value))]
                case OpenMode.READ_WRITE:
                    if is_var:
                        return [FileRead(Reference(value)), FileWrite(Reference(value))]
                    return [FileRead(StringLiteral(value)), FileWrite(StringLiteral(value))]
        raise TypeError(f"Unknown builtin function {key}")

    if key in ("read", "readline", "readlines"):
        return [VariableRead(Reference(node.as_string()))]
    if key in ("write", "writelines"):
        return [VariableWrite(Reference(node.as_string()))]

    if key in ("print", "input"):
        return [SystemInteraction()]

    raise TypeError(f"Unknown builtin function {key}")


def infer_purity(code: str) -> list[PurityInformation]:
    module = astroid.parse(code)
    purity_handler: PurityHandler = PurityHandler()
    walker = ASTWalker(purity_handler)
    result = []
    for node in module.body:
        tree = astroid.extract_node(node.as_string())
        print(tree.repr_tree())
        print("\n\n")

    for node in module.body:
        walker.walk(node)
        purity_result = determine_purity(purity_handler.purity_reason)
        result.append(generate_purity_information(node, purity_result))
        purity_handler.purity_reason = []
    return result

    # for function in functions:
    #     # print(function)
    #     # print(f"Analyse {function.name}:")
    #     walker.walk(function)
    #     purity_result = determine_purity(purity_handler.purity_reason)
    #     # print(f"Result: {purity_result.__class__.__name__}")
    #     # if not isinstance(purity_result, DefinitelyPure):
    #     #    print(f"Reasons: {purity_result.reasons}")
    #     # print(f"Function {function.name} is done. \n")
    #     result.append(generate_purity_information(function, purity_result))
    #     purity_handler.purity_reason = []
    # return result


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


# deprecated
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


def extract_impurity_reasons(purity: PurityResult) -> list[ImpurityIndicator]:
    if isinstance(purity, DefinitelyPure):
        return []
    return purity.reasons


def generate_purity_information(function: astroid.FunctionDef, purity_result: PurityResult) -> PurityInformation:
    function_id = calc_function_id(function)
    reasons = extract_impurity_reasons(purity_result)
    purity_info = PurityInformation(function_id, reasons)
    return purity_info


def calc_function_id(node: astroid.NodeNG) -> FunctionID | None:
    if not isinstance(node, astroid.FunctionDef):
        return FunctionID("NODE (not a functionDef):", node.as_string(), 0, 0)
    # module = node.root().name   TODO: Use module correctly
    # module = "_infer_purity.py"
    # if module.endswith(".py"):
    #    module = module[:-3]
    name = node.name
    line = node.position.lineno
    col = node.position.col_offset
    return FunctionID("NODE:", name, line, col)
# TODO: This function should return a correct FunctionID object for a given function and an other ID for everything else


# this function is only for visualization purposes
def get_purity_result_str(indicators: list[ImpurityIndicator]) -> str:
    if len(indicators) == 0:
        return "Definitely Pure"
    if any(indicator.certainty == ImpurityCertainty.DEFINITELY_IMPURE for indicator in indicators):
        return "Definitely Impure"

    return "Maybe Impure"


if __name__ == "__main__":
    import astroid

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
       def instance_access():
           a = A()
           print(a.value) # InstanceAccess => pure ??

       class B:
           name = "test"
       b = B()

       def attribute_access():
           res = b.name # AttributeAccess => maybe impure
           print(res)

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
    for info in result_list:
        p = get_purity_result_str(info.reasons)
        print(f"{info.id.module} {info.id.name} is {p} because {info.reasons} \n")


