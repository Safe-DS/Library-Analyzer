from unittest.mock import ANY

import astroid
import pytest
from astroid import FunctionDef

from library_analyzer.processing.api import (
    calc_function_id,
    get_function_defs,
    generate_purity_information,
    determine_purity,
    extract_impurity_reasons
)

from library_analyzer.processing.api import (
    PurityInformation,
    DefinitelyImpure,
    DefinitelyPure,
    MaybeImpure,
)

from library_analyzer.processing.api.model import (
    AttributeAccess,
    GlobalAccess,
    ParameterAccess,
    InstanceAccess,
    StringLiteral,
    VariableRead,
    VariableWrite,
    FileRead,
    FileWrite,
    UnknownCallTarget,
    Call,
)


@pytest.mark.parametrize(
    "code, expected",
    [
        (
            """
                def fun1(a):
                    h(a)
                    return a
            """,
            ".fun1.2.0"
        ),
        (
            """

                def fun2(a):
                    a = 1
                    return a
            """,
            ".fun2.3.0"
        ),
        (
            """
                a += 1 # not a function => TypeError
            """,
            None
        ),

    ]
)
def test_calc_function_id(code, expected):
    module = astroid.parse(code)
    function_node = module.body[0]
    if expected is None:
        with pytest.raises(TypeError):
            calc_function_id(function_node)

    else:
        result = calc_function_id(function_node)
        assert result.__str__() == expected


# since we only look at FunctionDefs we can not use other types of CodeSnippets
@pytest.mark.parametrize(
    "purity_result, expected",
    [
        (
            DefinitelyPure(),
            []
        ),
        (
            DefinitelyImpure(reasons=[Call(expression=AttributeAccess(name="impure_call"))]),
            [Call(expression=AttributeAccess(name="impure_call"))]
        ),
        (
            MaybeImpure(reasons=[FileRead(path=StringLiteral(value="read_path"))]),
            [FileRead(path=StringLiteral(value="read_path"))]
        ),
        (
            MaybeImpure(reasons=[FileWrite(path=StringLiteral(value="write_path"))]),
            [FileWrite(path=StringLiteral(value="write_path"))]
        ),
        (
            MaybeImpure(reasons=[VariableRead(StringLiteral(value="var_read"))]),
            [VariableRead(StringLiteral(value="var_read"))]
        ),
        (
            MaybeImpure(reasons=[VariableWrite(StringLiteral(value="var_write"))]),
            [VariableWrite(StringLiteral(value="var_write"))]
        )
    ]
)
def test_generate_purity_information(purity_result, expected):
    purity_info = extract_impurity_reasons(purity_result)

    assert purity_info == expected


@pytest.mark.parametrize(
    "purity_reasons, expected",
    [
        (
            [],
            DefinitelyPure()
        ),
        (
            [Call(expression=AttributeAccess(name="impure_call"))],
            DefinitelyImpure(reasons=[Call(expression=AttributeAccess(name="impure_call"))])
        ),
        # TODO: improve analysis so this test does not fail:
        # (
        #    [Call(expression=AttributeAccess(name="pure_call"))],
        #    DefinitelyPure()
        # ),
        (
            [FileRead(path=StringLiteral(value="read_path"))],
            DefinitelyImpure(reasons=[FileRead(path=StringLiteral(value="read_path"))])
        ),
        (
            [FileWrite(path=StringLiteral(value="write_path"))],
            DefinitelyImpure(reasons=[FileWrite(path=StringLiteral(value="write_path"))])
        ),
        (
            [VariableRead(StringLiteral(value="var_read"))],
            MaybeImpure(reasons=[VariableRead(StringLiteral(value="var_read"))])
        ),
        (
            [VariableWrite(StringLiteral(value="var_write"))],
            MaybeImpure(reasons=[VariableWrite(StringLiteral(value="var_write"))])
        )
    ]
)
def test_determine_purity(purity_reasons, expected):
    result = determine_purity(purity_reasons)
    assert result == expected

# "code, expected",
#     [
#         (
#             """
#                 def impure_fun(a):
#                     impure_call(a) # call => impure
#                     return a
#             """,
#             [Call(expression=AttributeAccess(name="impure_call"))],
#         ),
#         (
#             """
#                 def pure_fun(a):
#                     a += 1
#                     return a
#             """,
#             []
#         ),
#         (
#             """
#                 class A:
#                     def __init__(self):
#                         self.value = 42
#
#                 a = A()
#
#                 def instance(a):
#                     res = a.value # InstanceAccess => pure??
#                     return res
#             """,
#             [VariableRead(InstanceAccess(
#                 receiver=StringLiteral(value="a"),
#                 target=StringLiteral(value="value")))]
#         ),
#         (
#             """
#                 Class B:
#                     name = "test"
#
#                 b = B()
#
#                 def attribute(b):
#                     res = b.name # AttributeAccess => maybe impure
#                     return res
#             """,
#             [VariableRead(AttributeAccess(name="name"))]
#         ),
#         (
#             """
#                 global_var = 17
#
#                 def global_access():
#                     res = global_var # GlobalAccess => impure
#                     return res
#             """,
#             [VariableRead(GlobalAccess(name="global_var"))],
#         ),
#         (
#             """
#                 def parameter_access(a):
#                     res = a # ParameterAccess => pure
#                     return res
#             """,
#             []
#         ),
#     ]
# )
