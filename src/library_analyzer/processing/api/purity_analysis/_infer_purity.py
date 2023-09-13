from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from enum import Enum, auto

import astroid

from library_analyzer.processing.api.purity_analysis.model import (
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
)
from library_analyzer.utils import ASTWalker

BUILTIN_FUNCTIONS = {
    "open": BuiltInFunction(Reference("open"), ConcreteImpurityIndicator(), ImpurityCertainty.DEFINITELY_IMPURE),
    # TODO: how to replace the ... with the correct type?
    "print": BuiltInFunction(Reference("print"), SystemInteraction(), ImpurityCertainty.DEFINITELY_IMPURE),
    "read": BuiltInFunction(Reference("read"), ConcreteImpurityIndicator(), ImpurityCertainty.DEFINITELY_IMPURE),
    "write": BuiltInFunction(Reference("write"), ConcreteImpurityIndicator(), ImpurityCertainty.DEFINITELY_IMPURE),
    "readline": BuiltInFunction(
        Reference("readline"),
        ConcreteImpurityIndicator(),
        ImpurityCertainty.DEFINITELY_IMPURE,
    ),
    "readlines": BuiltInFunction(
        Reference("readlines"),
        ConcreteImpurityIndicator(),
        ImpurityCertainty.DEFINITELY_IMPURE,
    ),
    "writelines": BuiltInFunction(
        Reference("writelines"),
        ConcreteImpurityIndicator(),
        ImpurityCertainty.DEFINITELY_IMPURE,
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


class PurityResult(ABC):  # noqa: B024
    def __init__(self) -> None:
        self.reasons: list[ImpurityIndicator] = []


@dataclass
class DefinitelyPure(PurityResult):
    reasons = []


@dataclass
class MaybeImpure(PurityResult):
    reasons: list[ImpurityIndicator]

    # def __hash__(self) -> int:


@dataclass
class DefinitelyImpure(PurityResult):
    reasons: list[ImpurityIndicator]

    # def __hash__(self) -> int:


@dataclass
class PurityInformation:
    id: FunctionID
    reasons: list[ImpurityIndicator]

    # def __hash__(self) -> int:

    # def __eq__(self, other: object) -> bool:
    #     if not isinstance(other, PurityInformation):


class PurityHandler:
    def __init__(self) -> None:
        self.purity_reason: list[ImpurityIndicator] = []

    def append_reason(self, reason: list[ImpurityIndicator]) -> None:
        for r in reason:
            self.purity_reason.append(r)

    def enter_functiondef(self, node: astroid.FunctionDef) -> None:
        # Handle the FunctionDef node here
        pass  # Are we analyzing function defs within function defs? Yes, we are.

    def enter_assign(self, node: astroid.Assign) -> None:
        # Handle the Assign node here
        if isinstance(node.value, astroid.Call):
            pass
        if isinstance(node.value, astroid.Const):
            self.append_reason([VariableWrite(Reference(node.as_string()))])
        else:  # default case
            self.append_reason([VariableWrite(Reference(node.as_string()))])
        # TODO: Assign node needs further analysis to determine if it is pure or impure

    def enter_assignattr(self, node: astroid.AssignAttr) -> None:
        # Handle the AssignAtr node here
        self.append_reason([VariableWrite(Reference(node.as_string()))])
        # TODO: AssignAttr node needs further analysis to determine if it is pure or impure

    def enter_call(self, node: astroid.Call) -> None:
        # Handle the Call node here
        if isinstance(node.func, astroid.Attribute):
            pass
        elif isinstance(node.func, astroid.Name) and node.func.name in BUILTIN_FUNCTIONS:
            value = node.args[0]
            if isinstance(value, astroid.Name):
                impurity_indicator = check_builtin_function(node, node.func.name, value.name, is_var=True)
                self.append_reason(impurity_indicator)
            else:
                impurity_indicator = check_builtin_function(node, node.func.name, value.value)
                self.append_reason(impurity_indicator)

        self.append_reason([Call(Reference(node.as_string()))])
        # TODO: Call node needs further analysis to determine if it is pure or impure

    def enter_attribute(self, node: astroid.Attribute) -> None:
        # Handle the Attribute node here
        if isinstance(node.expr, astroid.Name):
            if node.attrname in BUILTIN_FUNCTIONS:
                impurity_indicator = check_builtin_function(node, node.attrname)
                self.append_reason(impurity_indicator)
        else:
            self.append_reason([Call(Reference(node.as_string()))])

    def enter_arguments(self, node: astroid.Arguments) -> None:
        # Handle the Arguments node here
        pass

    def enter_expr(self, node: astroid.Expr) -> None:
        # Handle the Expr node here
        pass

    def enter_name(self, node: astroid.Name) -> None:
        # Handle the Name node here
        pass

    def enter_const(self, node: astroid.Const) -> None:
        # Handle the Const node here
        pass

    def enter_assignname(self, node: astroid.AssignName) -> None:
        # Handle the AssignName node here
        pass

    def enter_with(self, node: astroid.With) -> None:
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
    node: astroid.NodeNG,
    key: str,
    value: str | None = None,
    is_var: bool = False,
) -> list[ImpurityIndicator]:
    if is_var:
        if key == "open":
            open_mode = determine_open_mode(node.args)
            if open_mode == OpenMode.WRITE:
                return [FileWrite(Reference(value))]

            if open_mode == OpenMode.READ:
                return [FileRead(Reference(value))]

            if open_mode == OpenMode.READ_WRITE:
                return [FileRead(Reference(value)), FileWrite(Reference(value))]

    elif isinstance(value, str):
        if key == "open":
            open_mode = determine_open_mode(node.args)
            if open_mode == OpenMode.WRITE:  # write mode
                return [FileWrite(StringLiteral(value))]

            if open_mode == OpenMode.READ:  # read mode
                return [FileRead(StringLiteral(value))]

            if open_mode == OpenMode.READ_WRITE:  # read and write mode
                return [FileRead(StringLiteral(value)), FileWrite(StringLiteral(value))]

        raise TypeError(f"Unknown builtin function {key}")

    if key in ("read", "readline", "readlines"):
        return [VariableRead(Reference(node.as_string()))]
    if key in ("write", "writelines"):
        return [VariableWrite(Reference(node.as_string()))]

    raise TypeError(f"Unknown builtin function {key}")


def infer_purity(code: str) -> list[PurityInformation]:
    purity_handler: PurityHandler = PurityHandler()
    walker = ASTWalker(purity_handler)
    functions = get_function_defs(code)
    result = []
    for function in functions:
        walker.walk(function)
        purity_result = determine_purity(purity_handler.purity_reason)
        # if not isinstance(purity_result, DefinitelyPure):
        result.append(generate_purity_information(function, purity_result))
        purity_handler.purity_reason = []
    return result


def determine_purity(indicators: list[ImpurityIndicator]) -> PurityResult:
    if len(indicators) == 0:
        return DefinitelyPure()
    if any(indicator.certainty == ImpurityCertainty.DEFINITELY_IMPURE for indicator in indicators):
        return DefinitelyImpure(reasons=indicators)

    return MaybeImpure(reasons=indicators)

    # if any(reason.is_reason_for_impurity() for reason in purity_reasons):
    #     if any(isinstance(reason, Call) for reason in purity_reasons):


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
    return purity.reasons


def generate_purity_information(function: astroid.FunctionDef, purity_result: PurityResult) -> PurityInformation:
    function_id = calc_function_id(function)
    reasons = extract_impurity_reasons(purity_result)
    return PurityInformation(function_id, reasons)


def calc_function_id(node: astroid.NodeNG) -> FunctionID:
    if not isinstance(node, astroid.FunctionDef):
        raise TypeError("Node is not a function")
    module = node.root().name
    # if module.endswith(".py"):
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
