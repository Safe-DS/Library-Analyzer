from abc import ABC
from dataclasses import dataclass

import astroid

from library_analyzer.processing.api.model import ImpurityReason, VariableRead, AttributeAccess, Call, FileWrite, \
    StringLiteral
from library_analyzer.utils import ASTWalker


class PurityResult(ABC):
    pass


class DefinitelyPure(PurityResult):
    pass


@dataclass
class MaybeImpure(PurityResult):
    reasons: list[ImpurityReason]

    def __hash__(self):
        return hash(tuple(self.reasons))


@dataclass
class DefinitelyImpure(PurityResult):
    reasons: list[ImpurityReason]

    def __hash__(self):
        return hash(tuple(self.reasons))


@dataclass
class PurityInformation:
    function: astroid.FunctionDef
    id: str
    purity: PurityResult

    # reason: ImpurityReason  # the reason why it is impure, if it is impure (added later)
    # last_accessed: str  # for later use in memoization

    def __hash__(self):
        return hash((self.function, self.id, self.purity))


purity_list = list[PurityInformation]()

dummy_reason1 = VariableRead(AttributeAccess("dummy until further improvements"))
dummy_reason2 = FileWrite(StringLiteral("test.txt"))


class PurityHandler:
    def __init__(self):
        self.purity_reason = list[ImpurityReason]()

    def enter_functiondef(self, node):
        # print(f"Enter function node: {node.name} of Class: {node.__class__.__name__}")
        # Handle the FunctionDef node here
        pass  # Are we analyzing function defs within function defs? Yes, we are.

    def enter_assign(self, node):
        print(f"Entering Assign node {node.as_string()}")
        # Handle the Assign node here
        if isinstance(node.value, astroid.Call):
            print("This is a call within an assign node:")
            impurity_reason = Call(node)
            self.purity_reason.append(impurity_reason)
        else:
            # impurity_reason = VariableRead(node)
            self.purity_reason.append(dummy_reason1)
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
        impurity_reason = Call(node)
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
        purity_list.append(generate_purity_information(function, purity_result))
        purity_handler.purity_reason.clear()


def determine_purity(purity_reasons: list[ImpurityReason]) -> PurityResult:

    # print(f"Maybe check {(any(purity_reason.is_reason_for_impurity() for purity_reason in purity_reasons))}")
    if any(reason.is_reason_for_impurity() for reason in purity_reasons):
        # print(f"Definitely check {any(isinstance(reason, Call) for reason in purity_reasons)}")
        if any(isinstance(reason, Call) for reason in purity_reasons):
            return DefinitelyImpure(reasons=purity_reasons)
        return MaybeImpure(reasons=purity_reasons)
    else:
        return DefinitelyPure()


def get_function_defs(code) -> list[astroid.FunctionDef]:
    module = astroid.parse(code)
    function_defs = list[astroid.FunctionDef]()
    for node in module.body:
        if isinstance(node, astroid.FunctionDef):
            function_defs.append(node)
    return function_defs


def generate_purity_information(function: astroid.FunctionDef, purity: PurityResult) -> PurityInformation:
    function_id = calc_function_id(function)
    purity_info = PurityInformation(function, function_id, purity)
    return purity_info


def calc_function_id(node):
    if node.is_function:
        module = node.root().name
        #  module = "_infer_purity.py"
        if module.endswith(".py"):
            module = module[:-3]
        name = node.name
        pos = node.position
        line = pos.lineno
        col = pos.col_offset
    else:
        module = name = line = col = "fail"

    function_id = f"{module}.{name}.{line}.{col}"
    return function_id


if __name__ == '__main__':
    sourcecode = """
    def my_function(x):
        g(x)

    def fun(a):
            h(a)
            b =  g(a) # call => impure
            b += 1
            return b

    glob = fun(42)

    def h(a):
        a = glob.name
        return a

    def g(a):
        return a + 1
    """
    # TODO: Write more test cases

    infer_purity(sourcecode)
    for f in purity_list:
        print(f"Function {f.function.name} with ID {f.id} is {f.purity.__class__.__name__}")

x = """
    def my_function(x):
        x = 1

    def fun(a):
            h(a)
            b =  g(a) # call => impure
            b += 1
            return b

    glob = fun(42)

    def h(a):
        a = glob.name
        return a

    def g(a):
        return a + 1
    """
