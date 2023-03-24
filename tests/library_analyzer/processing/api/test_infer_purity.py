from unittest.mock import ANY

import astroid
import pytest
from astroid import FunctionDef

from library_analyzer.processing.api import (
    calc_function_id,
    get_function_defs,
    generate_purity_information,
    determine_purity,
    extract_impurity_reasons,
    infer_purity,
    get_purity_result_str,

)

from library_analyzer.processing.api import (
    PurityInformation,
    DefinitelyImpure,
    DefinitelyPure,
    MaybeImpure,
    PurityResult,
    ImpurityIndicator,
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
    Reference,
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
def test_calc_function_id(code: str, expected):
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
def test_generate_purity_information(purity_result: PurityResult, expected: list[ImpurityIndicator]):
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
def test_determine_purity(purity_reasons: list[ImpurityIndicator], expected: PurityResult):
    result = determine_purity(purity_reasons)
    assert result == expected


@pytest.mark.parametrize(
    "code, expected",
    [
        (
            """
                def fun1():
                    open("test.txt")
            """,
            [FileRead(path=Reference("test.txt"))]
        ),
        (
            """
                def fun2():
                    open("test.txt", "r")
            """,
            [FileRead(path=Reference("test.txt"))]
        ),
        (
            """
                def fun3():
                    open("test.txt", "w")
            """,
            [FileWrite(path=Reference("test.txt"))]
        ),
        (
            """
                def fun4():
                    open("test.txt", "a")
            """,
            [FileWrite(path=Reference("test.txt"))]
        ),
        (
            """
                def fun5():
                    open("test.txt", "r+")
            """,
            [FileRead(path=Reference("test.txt")), FileWrite(path=Reference("test.txt"))]
        ),
        (
            """
                def fun6():
                    f = open("test.txt")
                    f.read()
            """,
            [FileRead(path=Reference("test.txt"))]
        ),
        (
            """
                def fun7():
                    f = open("test.txt")
                    f.readline([2])
            """,
            [FileRead(path=Reference("test.txt"))]
        ),
        (
            """
                def fun8():
                    f = open("test.txt")
                    f.write("message")
            """,
            [FileWrite(path=Reference("test.txt"))]
        ),
        (
            """
                def fun9():
                    f = open("test.txt")
                    f.writelines(["message1", "message2"])
            """,
            [FileWrite(path=Reference("test.txt"))]
        ),
        (
            """
                def fun10():
                    with open("test.txt") as f:
                        f.read()
            """,
            [FileRead(path=Reference("test.txt"))]  # @Lars ??
        )

    ]
)
def test_file_read(code: str, expected: list[ImpurityIndicator]):
    purity_info: list[PurityInformation] = infer_purity(code)
    for f in purity_info:
        p = get_purity_result_str(f.reasons)
        print(f"Function {f.id.name} with ID: {f.id} is {p} because {f.reasons}")
    assert purity_info[0].reasons == expected

