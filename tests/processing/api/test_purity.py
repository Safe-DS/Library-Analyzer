from unittest.mock import ANY

import astroid
import pytest
from astroid import FunctionDef

from library_analyzer.processing.api import (
    calc_function_id,
    get_function_defs,
    generate_purity_information,
    determine_purity,
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
    FieldAccess,
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
                def fun(a):
                    h(a)
                    b =  g(a) # call => impure
                    b += 1
                    return b
            """,
            ".fun.2.0"
        ),
        (
            """
                def x(a):
                    a = 1
                    return a
            """,
            ".x.2.0"
        ),
        (
            """
                a += 1
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
        assert result == expected


# since we only look at FunctionDefs we can not use other types of CodeSnippets
@pytest.mark.parametrize(
    "code, purity, expected",
    [
        (
            """
                def impure_fun(a):
                    impure_call(a) # call => impure
                    return a
            """,
            DefinitelyImpure(reasons=[Call(expression=AttributeAccess(name="impure_call"))]),
            PurityInformation(
                function=FunctionDef(name="impure_fun", lineno=2),  # TODO: how to ignore address?
                id=".impure_fun.2.0",
                purity=DefinitelyImpure(reasons=[Call(expression=AttributeAccess(name="impure_call"))]),
                reasons=[Call(expression=AttributeAccess(name='impure_call'))]
                )
        ),
        (
            """
                def pure_fun(a):
                    a += 1
                    return a
            """,
            DefinitelyPure(),
            PurityInformation(
                function=FunctionDef(name="pure_fun", lineno=2),  # TODO: how to ignore address?
                id=".pure_fun.2.0",
                purity=DefinitelyPure(),
                reasons=[]
            )
        ),

    ]
)
def test_generate_purity_information(code, purity, expected):
    function_node = get_function_defs(code)[0]
    purity_info = generate_purity_information(function_node, purity)

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
            MaybeImpure(reasons=[FileRead(path=StringLiteral(value="read_path"))])
        ),
        (
            [FileWrite(path=StringLiteral(value="write_path"))],
            MaybeImpure(reasons=[FileWrite(path=StringLiteral(value="write_path"))])
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
