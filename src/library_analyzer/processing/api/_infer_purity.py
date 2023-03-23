from abc import ABC
from dataclasses import dataclass

import astroid

from library_analyzer.processing.api.model import ImpurityIndicator, VariableRead, AttributeAccess, Call, FileWrite, \
    StringLiteral, ImpurityCertainty, Reference
from library_analyzer.utils import ASTWalker


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

    def enter_functiondef(self, node):
        # print(f"Enter function node: {node.name} of Class: {node.__class__.__name__}")
        # Handle the FunctionDef node here
        pass  # Are we analyzing function defs within function defs? Yes, we are.

    def enter_assign(self, node):
        print(f"Entering Assign node {node.as_string()}")
        # Handle the Assign node here
        if isinstance(node.value, astroid.Call):
            print("This is a call within an assign node:")
            impurity_reason = Call(Reference(node))
            self.purity_reason.append(impurity_reason)
        else:
            impurity_reason = VariableRead(node)
            self.purity_reason.append(impurity_reason)
            # TODO: Assign node needs further analysis to determine if it is pure or impure

    def enter_assignattr(self, node):
        print(f"Entering AssignAttr node {node.as_string()}")
        # Handle the AssignAtr node here
        impurity_reason = VariableRead(node)
        self.purity_reason.append(impurity_reason)
        # TODO: AssignAttr node needs further analysis to determine if it is pure or impure

    def enter_call(self, node):
        print(f"Entering Call node {node.as_string()}")
        # Handle the Call node here
        impurity_reason = Call(Reference(node))
        self.purity_reason.append(impurity_reason)
        # TODO: Call node needs further analysis to determine if it is pure or impure


def infer_purity(code):
    purity_handler: PurityHandler = PurityHandler()
    walker = ASTWalker(purity_handler)
    functions = get_function_defs(code)
    for function in functions:
        print(f"Analyse {function.name}:")
        walker.walk(function)
        purity_result = determine_purity(purity_handler.purity_reason)
        print(f"Result: {purity_result.__class__.__name__}")
        if not isinstance(purity_result, DefinitelyPure):
            print(f"Reasons: {purity_result.reasons}")
        print(f"Function {function.name} is done. \n")
        _result_list.append(generate_purity_information(function, purity_result))
        purity_handler.purity_reason = []


def determine_purity(indicators: list[ImpurityIndicator]) -> PurityResult:
    if len(indicators) == 0:
        return DefinitelyPure()
    if any(indicator.certainty == ImpurityCertainty.definitely for indicator in indicators):
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


def calc_function_id(node):
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
    if any(indicator.certainty == ImpurityCertainty.definitely for indicator in indicators):
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

    glob = g(1) #TODO: This will get filtered out because it is not a function call, but a variable assignment with a
    # function call and therefore further analysis is needed

    def fun(a):
        h(a)
        b =  g(a) # call => impure
        b += 1
        return b
    """

    infer_purity(sourcecode)
    for f in _result_list:
        p = get_purity_result_str(f.reasons)
        print(f"Function {f.id.name} with ID: {f.id} is {p} because {f.reasons}")
