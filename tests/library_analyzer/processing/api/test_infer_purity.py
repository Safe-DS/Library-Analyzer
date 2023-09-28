import astroid
import pytest
from library_analyzer.processing.api.purity_analysis import (
    DefinitelyImpure,
    DefinitelyPure,
    MaybeImpure,
    OpenMode,
    PurityInformation,
    PurityResult,
    calc_function_id,
    determine_open_mode,
    determine_purity,
    extract_impurity_reasons,
    infer_purity,
)

from library_analyzer.processing.api.purity_analysis.model import (
    AttributeAccess,
    Call,
    FileRead,
    FileWrite,
    Reference,
    StringLiteral,
    VariableRead,
    VariableWrite,
    ImpurityIndicator,

)


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (
            """
                def fun1(a):
                    h(a)
                    return a
            """,
            ".fun1.2.0",
        ),
        (
            """

                def fun2(a):
                    a = 1
                    return a
            """,
            ".fun2.3.0",
        ),
        (
            """
                a += 1 # not a function => TypeError
            """,
            None,
        ),
    ],
)
def test_calc_function_id(code: str, expected: str) -> None:
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
    ("purity_result", "expected"),
    [
        (DefinitelyPure(), []),
        (
            DefinitelyImpure(reasons=[Call(expression=AttributeAccess(name="impure_call"))]),
            [Call(expression=AttributeAccess(name="impure_call"))],
        ),
        (
            MaybeImpure(reasons=[FileRead(source=StringLiteral(value="read_path"))]),
            [FileRead(source=StringLiteral(value="read_path"))],
        ),
        (
            MaybeImpure(reasons=[FileWrite(source=StringLiteral(value="write_path"))]),
            [FileWrite(source=StringLiteral(value="write_path"))],
        ),
        (
            MaybeImpure(reasons=[VariableRead(StringLiteral(value="var_read"))]),
            [VariableRead(StringLiteral(value="var_read"))],
        ),
        (
            MaybeImpure(reasons=[VariableWrite(StringLiteral(value="var_write"))]),
            [VariableWrite(StringLiteral(value="var_write"))],
        ),
    ],
)
def test_generate_purity_information(purity_result: PurityResult, expected: list[ImpurityIndicator]) -> None:
    purity_info = extract_impurity_reasons(purity_result)

    assert purity_info == expected


@pytest.mark.parametrize(
    ("purity_reasons", "expected"),
    [
        ([], DefinitelyPure()),
        (
            [Call(expression=AttributeAccess(name="impure_call"))],
            DefinitelyImpure(reasons=[Call(expression=AttributeAccess(name="impure_call"))]),
        ),
        # TODO: improve analysis so this test does not fail:
        # ),
        (
            [FileRead(source=StringLiteral(value="read_path"))],
            DefinitelyImpure(reasons=[FileRead(source=StringLiteral(value="read_path"))]),
        ),
        (
            [FileWrite(source=StringLiteral(value="write_path"))],
            DefinitelyImpure(reasons=[FileWrite(source=StringLiteral(value="write_path"))]),
        ),
        (
            [VariableRead(StringLiteral(value="var_read"))],
            MaybeImpure(reasons=[VariableRead(StringLiteral(value="var_read"))]),
        ),
        (
            [VariableWrite(StringLiteral(value="var_write"))],
            MaybeImpure(reasons=[VariableWrite(StringLiteral(value="var_write"))]),
        ),
    ],
)
def test_determine_purity(purity_reasons: list[ImpurityIndicator], expected: PurityResult) -> None:
    result = determine_purity(purity_reasons)
    assert result == expected


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        (["test"], OpenMode.READ),
        (["test", "r"], OpenMode.READ),
        (["test", "rb"], OpenMode.READ),
        (["test", "rt"], OpenMode.READ),
        (["test", "r+"], OpenMode.READ_WRITE),
        (["test", "w"], OpenMode.WRITE),
        (["test", "wb"], OpenMode.WRITE),
        (["test", "wt"], OpenMode.WRITE),
        (["test", "w+"], OpenMode.READ_WRITE),
        (["test", "x"], OpenMode.WRITE),
        (["test", "xb"], OpenMode.WRITE),
        (["test", "xt"], OpenMode.WRITE),
        (["test", "x+"], OpenMode.READ_WRITE),
        (["test", "a"], OpenMode.WRITE),
        (["test", "ab"], OpenMode.WRITE),
        (["test", "at"], OpenMode.WRITE),
        (["test", "a+"], OpenMode.READ_WRITE),
        (["test", "r+b"], OpenMode.READ_WRITE),
        (["test", "w+b"], OpenMode.READ_WRITE),
        (["test", "x+b"], OpenMode.READ_WRITE),
        (["test", "a+b"], OpenMode.READ_WRITE),
        (["test", "r+t"], OpenMode.READ_WRITE),
        (["test", "w+t"], OpenMode.READ_WRITE),
        (["test", "x+t"], OpenMode.READ_WRITE),
        (["test", "a+t"], OpenMode.READ_WRITE),
        (["test", "error"], ValueError),
    ],
)
def test_determine_open_mode(args: list[str], expected: OpenMode) -> None:
    if expected is ValueError:
        with pytest.raises(ValueError, match="is not a valid mode for the open function"):
            determine_open_mode(args)
    else:
        result = determine_open_mode(args)
        assert result == expected


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (
            """
                def fun1():
                    open("test1.txt") # default mode: read only
            """,
            [FileRead(source=StringLiteral(value="test1.txt")), Call(expression=Reference(name="open('test1.txt')"))],
        ),
        (
            """
                def fun2():
                    open("test2.txt", "r") # read only
            """,
            [
                FileRead(source=StringLiteral(value="test2.txt")),
                Call(expression=Reference(name="open('test2.txt', 'r')")),
            ],
        ),
        (
            """
                def fun3():
                    open("test3.txt", "w") # write only
            """,
            [
                FileWrite(source=StringLiteral(value="test3.txt")),
                Call(expression=Reference(name="open('test3.txt', 'w')")),
            ],
        ),
        (
            """
                def fun4():
                    open("test4.txt", "a") # append
            """,
            [
                FileWrite(source=StringLiteral(value="test4.txt")),
                Call(expression=Reference(name="open('test4.txt', 'a')")),
            ],
        ),
        (
            """
                def fun5():
                    open("test5.txt", "r+")  # read and write
            """,
            [
                FileRead(source=StringLiteral(value="test5.txt")),
                FileWrite(source=StringLiteral(value="test5.txt")),
                Call(expression=Reference(name="open('test5.txt', 'r+')")),
            ],
        ),
        (
            """
                def fun6():
                    f = open("test6.txt") # default mode: read only
                    f.read()
            """,
            [
                VariableWrite(expression=Reference(name="f = open('test6.txt')")),
                FileRead(source=StringLiteral(value="test6.txt")),
                Call(expression=Reference(name="open('test6.txt')")),
                Call(expression=Reference(name="f.read()")),
                VariableRead(expression=Reference(name="f.read")),
            ],
        ),
        (
            """
                def fun7():
                    f = open("test7.txt") # default mode: read only
                    f.readline([2])
            """,
            [
                VariableWrite(expression=Reference(name="f = open('test7.txt')")),
                FileRead(source=StringLiteral(value="test7.txt")),
                Call(expression=Reference(name="open('test7.txt')")),
                Call(expression=Reference(name="f.readline([2])")),
                VariableRead(expression=Reference(name="f.readline")),
            ],
        ),
        (
            """
                def fun8():
                    f = open("test8.txt", "w") # write only
                    f.write("message")
            """,
            [
                VariableWrite(expression=Reference(name="f = open('test8.txt', 'w')")),
                FileWrite(source=StringLiteral(value="test8.txt")),
                Call(expression=Reference(name="open('test8.txt', 'w')")),
                Call(expression=Reference(name="f.write('message')")),
                VariableWrite(expression=Reference(name="f.write")),
            ],
        ),
        (
            """
                def fun9():
                    f = open("test9.txt", "w") # write only
                    f.writelines(["message1", "message2"])
            """,
            [
                VariableWrite(expression=Reference(name="f = open('test9.txt', 'w')")),
                FileWrite(source=StringLiteral(value="test9.txt")),
                Call(expression=Reference(name="open('test9.txt', 'w')")),
                Call(expression=Reference(name="f.writelines(['message1', 'message2'])")),
                VariableWrite(expression=Reference(name="f.writelines")),
            ],
        ),
        (
            """
                def fun10():
                    with open("test10.txt") as f: # default mode: read only
                        f.read()
            """,
            [
                FileRead(source=StringLiteral(value="test10.txt")),
                Call(expression=Reference(name="open('test10.txt')")),
                Call(expression=Reference(name="f.read()")),
                VariableRead(expression=Reference(name="f.read")),
            ],
        ),
        (
            """
                def fun11(path11): # open with variable
                    open(path11)
            """,
            [FileRead(source=Reference("path11")), Call(expression=Reference(name="open(path11)"))],  # ??
        ),
        (
            """
                def fun12(path12): # open with variable write mode
                    open(path12, "w")
            """,
            [FileWrite(source=Reference(name="path12")), Call(expression=Reference(name="open(path12, 'w')"))],  # ??
        ),
        (
            """
                def fun13(path13): # open with variable write mode
                    open(path13, "wb+")
            """,
            [
                FileRead(source=Reference(name="path13")),
                FileWrite(source=Reference(name="path13")),
                Call(expression=Reference(name="open(path13, 'wb+')")),
            ],  # ??
        ),
        (
            """
                def fun14(path14):
                    with open(path14) as f:
                        f.read()
            """,
            [
                FileRead(source=Reference("path14")),
                Call(expression=Reference(name="open(path14)")),
                Call(expression=Reference(name="f.read()")),
                VariableRead(expression=Reference(name="f.read")),
            ],  # ??
        ),
        (
            """
                def fun15(path15): # open with variable and wrong mode
                    open(path15, "test")
            """,
            ValueError,
        ),
        (
            """
                def fun16(): # this does not belong here but is needed for code coverage
                    print("test")
            """,
            TypeError,
        ),
    ],
)
# TODO: test for wrong arguments and Errors
def test_file_interaction(code: str, expected: list[ImpurityIndicator]) -> None:
    if expected is ValueError:
        with pytest.raises(ValueError, match="is not a valid mode for the open function"):
            infer_purity(code)
    elif expected is TypeError:
        with pytest.raises(TypeError):
            infer_purity(code)
    else:
        purity_info: list[PurityInformation] = infer_purity(code)
        assert purity_info[0].reasons == expected


# @pytest.mark.parametrize(
#     "code, expected",
#             """
#                 def impure_fun(a):
#             """,
#             [Call(expression=Reference(name='impure_call(a)')),
#              Call(expression=Reference(name='impure_call(a)'))],
#         ),
#             """
#                 def pure_fun(a):
#             """,
#         ),
#             """
#                 class A:
#                     def __init__(self):
#
#
#                 def instance(a):
#             """,
#             [VariableWrite(expression=InstanceAccess(
#             ))],  # TODO: is this correct?
#         ),
#             """
#                 class B:
#
#
#                 def attribute(b):
#             """,
#         ),
#             """
#                 def global_access():
#             """,
#         ),
#             """
#                 def parameter_access(a):
#             """,
#             [Call(expression=ParameterAccess(
#                 function="parameter_access"),
#             )],  # TODO: is this correct?
#         ),
#             """
#                 # function call and therefore further analysis is needed
#             """,
#             [VariableWrite(expression=Reference(name='b = g(a)')),
#              Call(expression=Reference(name="g(1)"))],  # TODO: is this correct?
#         ),
#             """
#                 def fun(a):
#             """,
#             [Call(expression=Reference(name='h(a)')),
#              Call(expression=Reference(name='g(a)'))],  # TODO: is this correct?
#         ),
#
#
# def test_infer_purity_basics(code: str, expected: list[ImpurityIndicator]) -> None:
