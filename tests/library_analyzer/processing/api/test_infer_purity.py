import astroid
import pytest
from library_analyzer.processing.api import (
    Impure,
    Pure,
    ImpurityIndicator,
    Unknown,
    PurityInformation,
    PurityResult,
    OpenMode,
    calc_function_id,
    determine_purity,
    extract_impurity_reasons,
    infer_purity,
    determine_open_mode,
    remove_irrelevant_information,
    get_purity_result_str,
)

from library_analyzer.processing.api.model import (
    AttributeAccess,
    Call,
    FileRead,
    FileWrite,
    Reference,
    StringLiteral,
    VariableRead,
    VariableWrite,
    GlobalAccess,
    InstanceAccess,
    ParameterAccess,
)


# @pytest.mark.parametrize(
#     "code, expected",
#     [
#         (
#             """
#                 def fun1(a):
#                     h(a)
#                     return a
#             """,
#             ".fun1.2.0",
#         ),
#         (
#             """
#
#                 def fun2(a):
#                     a = 1
#                     return a
#             """,
#             ".fun2.3.0",
#         ),
#         (
#             """
#                 a += 1 # not a function => TypeError
#             """,
#             "None",
#         ),
#     ],
# )  # TODO: redo this test after we can handle more than FunctionDefs
# def test_calc_function_id(code: str, expected: str) -> None:
#     module = astroid.parse(code)
#     function_node = module.body[0]
#     # if expected is None:
#     #     with pytest.raises(TypeError):
#     #         calc_function_id(function_node)
#
#     #else:
#     result = calc_function_id(function_node)
#     assert str(result) == expected


# since we only look at FunctionDefs we can not use other types of CodeSnippets
@pytest.mark.parametrize(
    "purity_result, expected",
    [
        (Pure(), []),
        (
            Impure(reasons=[Call(expression=AttributeAccess(name="impure_call"))]),
            [Call(expression=AttributeAccess(name="impure_call"))],
        ),
        (
            Unknown(reasons=[FileRead(source=StringLiteral(value="read_path"))]),
            [FileRead(source=StringLiteral(value="read_path"))],
        ),
        (
            Unknown(reasons=[FileWrite(source=StringLiteral(value="write_path"))]),
            [FileWrite(source=StringLiteral(value="write_path"))],
        ),
        (
            Unknown(reasons=[VariableRead(StringLiteral(value="var_read"))]),
            [VariableRead(StringLiteral(value="var_read"))],
        ),
        (
            Unknown(reasons=[VariableWrite(StringLiteral(value="var_write"))]),
            [VariableWrite(StringLiteral(value="var_write"))],
        ),
    ],
)
def test_generate_purity_information(purity_result: PurityResult, expected: list[ImpurityIndicator]) -> None:
    purity_info = extract_impurity_reasons(purity_result)

    assert purity_info == expected


@pytest.mark.parametrize(
    "purity_reasons, expected",
    [
        ([], Pure()),
        (
            [Call(expression=AttributeAccess(name="impure_call"))],
            Impure(reasons=[Call(expression=AttributeAccess(name="impure_call"))]),
        ),
        # TODO: improve analysis so this test does not fail:
        # (
        #    [Call(expression=AttributeAccess(name="pure_call"))],
        #    DefinitelyPure()
        # ),
        (
            [FileRead(source=StringLiteral(value="read_path"))],
            Impure(reasons=[FileRead(source=StringLiteral(value="read_path"))]),
        ),
        (
            [FileWrite(source=StringLiteral(value="write_path"))],
            Impure(reasons=[FileWrite(source=StringLiteral(value="write_path"))]),
        ),
        (
            [VariableRead(StringLiteral(value="var_read"))],
            Unknown(reasons=[VariableRead(StringLiteral(value="var_read"))]),
        ),
        (
            [VariableWrite(StringLiteral(value="var_write"))],
            Unknown(reasons=[VariableWrite(StringLiteral(value="var_write"))]),
        ),
    ],
)
def test_determine_purity(purity_reasons: list[ImpurityIndicator], expected: PurityResult) -> None:
    result = determine_purity(purity_reasons)
    assert result == expected


@pytest.mark.parametrize(
    "args, expected",
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
        with pytest.raises(ValueError):
            determine_open_mode(args)
    else:
        result = determine_open_mode(args)
        assert result == expected


@pytest.mark.parametrize(
    "code, expected",
    [
        (
            """
                def fun1():
                    open("test1.txt") # default mode: read only
            """,
            [FileRead(source=StringLiteral(value="test1.txt")),
             Call(expression=Reference(name="open('test1.txt')"))],
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
                FileRead(source=StringLiteral(value="test6.txt")),
                Call(expression=Reference(name="open('test6.txt')")),
                Call(expression=Reference(name="f.read()")),
            ],
        ),
        (
            """
                def fun7():
                    f = open("test7.txt") # default mode: read only
                    f.readline([2])
            """,
            [
                FileRead(source=StringLiteral(value="test7.txt")),
                Call(expression=Reference(name="open('test7.txt')")),
                Call(expression=Reference(name="f.readline([2])")),
            ],
        ),
        (
            """
                def fun8():
                    f = open("test8.txt", "w") # write only
                    f.write("message")
            """,
            [
                FileWrite(source=StringLiteral(value="test8.txt")),
                Call(expression=Reference(name="open('test8.txt', 'w')")),
                Call(expression=Reference(name="f.write('message')")),
            ],
        ),
        (
            """
                def fun9():
                    f = open("test9.txt", "w") # write only
                    f.writelines(["message1", "message2"])
            """,
            [
                FileWrite(source=StringLiteral(value="test9.txt")),
                Call(expression=Reference(name="open('test9.txt', 'w')")),
                Call(expression=Reference(name="f.writelines(['message1', 'message2'])")),
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
            ],
        ),
        (
            """
                def fun11(path11): # open with variable
                    open(path11)
            """,
            [Call(expression=ParameterAccess(parameter='path11', function='open')),
             FileRead(source=Reference(name='path11', expression=None)),
             Call(expression=Reference(name='open(path11)', expression=None))],
        ),
        (
            """
                def fun12(path12): # open with variable write mode
                    open(path12, "w")
            """,
            [
                Call(expression=ParameterAccess(parameter='path12', function='open')),
                FileWrite(source=Reference(name='path12', expression=None)),
                Call(expression=Reference(name="open(path12, 'w')", expression=None))],  # ??
        ),
        (
            """
                def fun13(path13): # open with variable write mode
                    open(path13, "wb+")
            """,
            [
                Call(expression=ParameterAccess(parameter='path13', function='open')),
                FileRead(source=Reference(name='path13', expression=None)),
                FileWrite(source=Reference(name='path13', expression=None)),
                Call(expression=Reference(name="open(path13, 'wb+')", expression=None))],
        ),
        (
            """
                def fun14(path14):
                    with open(path14) as f:
                        f.read()
            """,
            [
                Call(expression=ParameterAccess(parameter='path14',
                                                function='open')),
                FileRead(source=Reference("path14")),
                Call(expression=Reference(name="open(path14)")),
                Call(expression=Reference(name="f.read()")),
            ],
        ),
        (
            """
                def fun15(path15):
                    with open(path15, "w") as f:
                        f.write("test")
            """,
            [
                Call(expression=ParameterAccess(parameter='path15',
                                                function='open')),
                FileWrite(source=Reference(name='path15')),
                Call(expression=Reference(name="open(path15, 'w')")),
                Call(expression=Reference(name="f.write('test')")),
            ],
        ),
        (
            """
                def fun16(path16): # open with variable and wrong mode
                    open(path16, "test")
            """,
            ValueError,
        ),
        (
            """
                def fun17(): # this does not belong here but is needed for code coverage
                    print("test")
            """,
            TypeError,
        ),
    ],
)
# TODO: test for wrong arguments and Errors
def test_file_interaction(code: str, expected: list[ImpurityIndicator]) -> None:
    if expected is ValueError:
        with pytest.raises(ValueError):
            infer_purity(code)
    elif expected is TypeError:
        with pytest.raises(TypeError):
            infer_purity(code)
    else:
        purity_info: list[PurityInformation] = infer_purity(code)
        for info in purity_info:
            p = get_purity_result_str(info.reasons)
            print(f"{info.id.module} {info.id.name} is {p} because {info.reasons} \n")
        assert purity_info[0].reasons == expected


@pytest.mark.parametrize(
    "code, expected",
    [
        (
            """
                def impure_fun(a):
                    impure_call(a) # call => impure
                    impure_call(a) # call => impure - check if the analysis is correct for multiple calls - done
                    return a
            """,
            [Call(expression=Reference(name='impure_call(a)')),
             Call(expression=Reference(name='impure_call(a)'))],
        ),  # TODO: there is no way to distinguish between the two calls
        (
            """
                def pure_fun(a):
                    a += 1
                    return a
            """,
            []
        ),
        (
            """
                class A:
                    def __init__(self):
                        self.number = 42

                a = A()

                def instance(a):
                    res = a.number # InstanceAccess => impure
                    return res
            """,
            [
                InstanceAccess(
                    receiver=Reference(name='a'),
                    target=Reference(name='number'))
            ],
        ),
        (
            """
                class B:
                    name = "test"

                b = B()

                def attribute(b):
                    res = b.name # AttributeAccess => impure
                    return res
            """,
            [AttributeAccess(name='b.name')],
        ),
        (
            """
                glob = g(1)  # call => impure
            """,
            # TODO: Nur wenn wir auf Modul ebene arbeiten soll für "globale Variablen"
            #  die PurityInformation gespeichert werde, sonst nicht
            # in this case this analysis would be correct, since this testcase represents a "module"-scope
            [VariableWrite(expression=Reference(name="glob", expression=Reference(name="g(1)"))),
             Call(expression=Reference(name="g(1)"))],
        ),
        (
            """
                def fun(a):
                    h(a)
                    b =  g(a) # call => impure
                    b += 1
                    return b
            """,
            [Call(expression=Reference(name='h(a)')),
             Call(expression=Reference(name='g(a)'))],
        ),
        (
            """
                glob = 1
                def global_fun():
                    global glob
                    glob += 1   # GlobalWrite => impure
            """,
            [GlobalAccess(name='glob')],
        ),
        (
            """
                def pure_fun(a):
                    return a

                def impure_fun(a):
                    impure_call(a) # call => impure

                def access(fun):    # function as parameter
                    fun() # call => impure

                access(pure_fun)
                access(impure_fun)
            """,  # TODO: just for now it is impure: further analysis of fun is needed
            [Call(expression=Reference(name='fun()')),
             Call(expression=Reference(name='access(pure_fun)')),
             Call(expression=Reference(name='access(impure_fun)'))],
        ),
        (
            """
                def pure_fun(a):
                    return a

                def impure_fun(a):
                    impure_call(a) # call => impure

                if True:
                    access(pure_fun)
                else:
                    access(impure_fun)
            """,  # TODO: just for now it is impure: further analysis of fun is needed
            [Call(expression=Reference(name='access(pure_fun)')),
             Call(expression=Reference(name='access(impure_fun)'))],
        ),
        (
            """
                def impure_fun(a):
                    impure_call(a) # call => impure

                for i in range(10):
                    impure_fun(i)
            """,  # TODO: just for now it is impure: further analysis of fun is needed
            [Call(expression=Reference(name='impure_call(a)')),
             Call(expression=Reference(name='impure_fun(i)'))],
        )
    ]

)
def test_infer_purity_basics(code: str, expected: list[ImpurityIndicator]) -> None:
    result_list = infer_purity(code)
    for info in result_list:
        p = get_purity_result_str(info.reasons)
        print(f"{info.id.module} {info.id.name} is {p} because {info.reasons} \n")

    assert result_list[0].reasons == expected


@pytest.mark.parametrize(
    "code, expected",
    [
        (
            """
                def parameter_access1(a):
                    res = a # ParameterAccess => pure
                    return res
            """,  # function with one parameter, one accessed parameter
            [],
        ),
        (
            """
                def parameter_access(a, b):
                    res1 = a  # ParameterAccess => pure
                    res2 = b  # ParameterAccess => pure
                    return res1, res2
            """,  # function with two parameters, two accessed parameters
            [],
        ),
        (
            """
                def parameter_access(a, b):
                    res1 = a  # ParameterAccess => pure
                    return res1
            """,  # function with two parameters, one accessed parameter and one not accessed parameter
            []
        ),
        (
            """
                def parameter_access(a, b):
                    res1 = 1234
                    return res1
            """,  # function with two parameters, two not accessed parameters
            [],
        ),
        (
            """
                def parameter_access(a):
                    res1 = f(a)  # ParameterAccess => pure but Call => impure
                    return res1
            """,  # function with one parameter, one accessed parameter via a call argument
            [Call(expression=ParameterAccess(parameter='a',
                                             function='f')),
             Call(expression=Reference(name='f(a)',
                                       expression=None))  # TODO: remove this when Call is fixed
             ],
        ),
        (
            """
                def parameter_access(a, b):
                    res1 = f(a, b)  # ParameterAccess => pure but Call => impure
                    return res1
            """,  # function with two arguments, two accessed parameters via a call argument
            [Call(expression=ParameterAccess(parameter='a',
                                             function='f')),
             Call(expression=ParameterAccess(parameter='b',
                                             function='f')),
             Call(expression=Reference(name='f(a, b)',
                                       expression=None))  # TODO: remove this when Call is fixed
             ],
        ),
        (
            """
                def parameter_access(a, b):
                    res1 = f(a)  # ParameterAccess => pure but Call => impure
                    return res1
            """,  # function with two arguments, two accessed parameters via a call argument
            [Call(expression=ParameterAccess(parameter='a',
                                             function='f')),
             Call(expression=Reference(name='f(a)',
                                       expression=None))  # TODO: remove this when Call is fixed

             ],
        ),
        (
            """
                def parameter_access(a, b):
                    res1 = f(a)  # ParameterAccess => pure but Call => impure
                    res2 = g(b)  # ParameterAccess => pure but Call => impure
                    return res1, res2
            """,  # function with two arguments, two accessed parameters via a call argument
            [Call(expression=ParameterAccess(parameter='a',
                                             function='f')),
             Call(expression=ParameterAccess(parameter='b',
                                             function='g')),
             Call(expression=Reference(name='f(a)',
                                       expression=None)),  # TODO: remove this when Call is fixed
             Call(expression=Reference(name='g(b)',
                                       expression=None))  # TODO: remove this when Call is fixed
             ],
        ),
    ]
)
def test_infer_purity_parameter_access(code: str, expected: list[ImpurityIndicator]) -> None:
    result_list = infer_purity(code)
    for info in result_list:
        p = get_purity_result_str(info.reasons)
        print(f"{info.id.module} {info.id.name} is {p} because {info.reasons} \n")

    assert result_list[0].reasons == expected


@pytest.mark.parametrize(
    "code, expected",
    [
        (
            """
                glob = 17
                def global_access():
                    global glob
                    res = glob # GlobalAccess => impure
                    return res
            """,
            [VariableWrite(expression=GlobalAccess(name='glob', module=''))],
        ),
        (
            """
                glob1 = 17
                glob2 = 18
                def global_access():
                    global glob1
                    global glob2
                    res = glob1 # GlobalAccess => impure
                    return res
            """,
            [VariableWrite(expression=GlobalAccess(name='glob1', module=''))],
            #  TODO: to fix this, we need to check if the global is accessed in the function body
        ),
        (
            """
                glob = 19
                def global_access():
                    global glob
                    glob = "test"  # GlobalAccess => impure
                    return res
            """,
            [VariableWrite(expression=GlobalAccess(name='glob', module=''))],
        ),
        (
            """
                glob = 20
                def global_access():
                    global glob
                    glob = h(1)  # GlobalAccess + Call => impure
                    return res
            """,
            [VariableWrite(expression=GlobalAccess(name='glob', module='')),
             Call(expression=Reference(name='h(1)', expression=None))],
        ),
    ]
)
def test_infer_purity_global_access(code: str, expected: list[ImpurityIndicator]) -> None:
    result_list = infer_purity(code)
    result_list = remove_irrelevant_information(result_list)
    for info in result_list:
        p = get_purity_result_str(info.reasons)
        print(f"{info.id.module} {info.id.name} is {p} because {info.reasons} \n")

    assert result_list[0].reasons == expected
