import astroid
import pytest

from library_analyzer.processing.api import (
    calc_function_id,
    determine_purity,
    extract_impurity_reasons,
    infer_purity,

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
    StringLiteral,
    VariableRead,
    VariableWrite,
    FileRead,
    FileWrite,
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
def test_calc_function_id(code: str, expected) -> None:
    module = astroid.parse(code)
    function_node = module.body[0]
    if expected is None:
        with pytest.raises(TypeError):
            calc_function_id(function_node)

    else:
        result = calc_function_id(function_node)
        assert str(result) == expected


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
            MaybeImpure(reasons=[FileRead(source=StringLiteral(value="read_path"))]),
            [FileRead(source=StringLiteral(value="read_path"))]
        ),
        (
            MaybeImpure(reasons=[FileWrite(source=StringLiteral(value="write_path"))]),
            [FileWrite(source=StringLiteral(value="write_path"))]
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
def test_generate_purity_information(purity_result: PurityResult, expected: list[ImpurityIndicator]) -> None:
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
            [FileRead(source=StringLiteral(value="read_path"))],
            DefinitelyImpure(reasons=[FileRead(source=StringLiteral(value="read_path"))])
        ),
        (
            [FileWrite(source=StringLiteral(value="write_path"))],
            DefinitelyImpure(reasons=[FileWrite(source=StringLiteral(value="write_path"))])
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
def test_determine_purity(purity_reasons: list[ImpurityIndicator], expected: PurityResult) -> None:
    result = determine_purity(purity_reasons)
    assert result == expected


@pytest.mark.parametrize(
    "code, expected",
    [
        (
            """
                def fun1():
                    open("test1.txt") # default mode: read only
            """,
            [FileRead(source=StringLiteral(value='test1.txt')),
             Call(expression=Reference(name="open('test1.txt')"))]
        ),
        (
            """
                def fun2():
                    open("test2.txt", "r") # read only
            """,
            [FileRead(source=StringLiteral(value='test2.txt')),
             Call(expression=Reference(name="open('test2.txt', 'r')"))]
        ),
        (
            """
                def fun3():
                    open("test3.txt", "w") # write only
            """,
            [FileWrite(source=StringLiteral(value='test3.txt')),
             Call(expression=Reference(name="open('test3.txt', 'w')"))]
        ),
        (
            """
                def fun4():
                    open("test4.txt", "a") # append
            """,
            [FileWrite(source=StringLiteral(value='test4.txt')),
             Call(expression=Reference(name="open('test4.txt', 'a')"))]
        ),
        (
            """
                def fun5():
                    open("test5.txt", "r+")  # read and write
            """,
            [FileRead(source=StringLiteral(value='test5.txt')),
             FileWrite(source=StringLiteral(value='test5.txt')),
             Call(expression=Reference(name="open('test5.txt', 'r+')"))]
        ),  # TODO: do we need to distinguish between read and write?
        (
            """
                def fun6():
                    f = open("test6.txt") # default mode: read only
                    f.read()
            """,
            [VariableWrite(expression=Reference(name="f = open('test6.txt')")),
             FileRead(source=StringLiteral(value='test6.txt')),
             Call(expression=Reference(name="open('test6.txt')")),
             Call(expression=Reference(name='f.read()')),
             VariableRead(expression=Reference(name='f.read'))]
        ),
        (
            """
                def fun7():
                    f = open("test7.txt") # default mode: read only
                    f.readline([2])
            """,
            [VariableWrite(expression=Reference(name="f = open('test7.txt')")),
             FileRead(source=StringLiteral(value='test7.txt')),
             Call(expression=Reference(name="open('test7.txt')")),
             Call(expression=Reference(name='f.readline([2])')),
             VariableRead(expression=Reference(name='f.readline'))]
        ),
        (
            """
                def fun8():
                    f = open("test8.txt", "w") # write only
                    f.write("message")
            """,
            [VariableWrite(expression=Reference(name="f = open('test8.txt', 'w')")),
             FileWrite(source=StringLiteral(value='test8.txt')),
             Call(expression=Reference(name="open('test8.txt', 'w')")),
             Call(expression=Reference(name="f.write('message')")),
             VariableWrite(expression=Reference(name='f.write'))]
        ),
        (
            """
                def fun9():
                    f = open("test9.txt", "w") # write only
                    f.writelines(["message1", "message2"])
            """,
            [VariableWrite(expression=Reference(name="f = open('test9.txt', 'w')")),
             FileWrite(source=StringLiteral(value='test9.txt')),
             Call(expression=Reference(name="open('test9.txt', 'w')")),
             Call(expression=Reference(name="f.writelines(['message1', 'message2'])")),
             VariableWrite(expression=Reference(name='f.writelines'))]
        ),
        (
            """
                def fun10():
                    with open("test10.txt") as f: # default mode: read only
                        f.read()
            """,
            [FileRead(source=StringLiteral(value='test10.txt')),
             Call(expression=Reference(name="open('test10.txt')")),
             Call(expression=Reference(name='f.read()')),
             VariableRead(expression=Reference(name='f.read'))]
        ),
        (
            """
                def fun11(path11): # open with variable
                    open(path11)
            """,
            [FileRead(source=Reference("path11"))]  # ??
        ),
        (
            """
                def fun12(path12):
                    with open(path12) as f:
                        f.read()
            """,
            [FileRead(source=Reference("path12"))]  # ??
        )

    ]
)
def test_file_read(code: str, expected: list[ImpurityIndicator]) -> None:
    purity_info: list[PurityInformation] = infer_purity(code)
    assert purity_info[0].reasons == expected
