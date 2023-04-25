from inspect import cleandoc

import pytest
from library_analyzer.processing.api.model import (
    API,
    Attribute,
    Class,
    ClassDocstring,
    Function,
    FunctionDocumentation,
    NamedType,
    Parameter,
    ParameterAssignment,
    ParameterDocumentation,
    Result,
    ResultDocstring,
    UnionType,
)
from library_analyzer.processing.migration.model import AbstractDiffer, SimpleDiffer

differ_list = [
    SimpleDiffer(
        None,
        [],
        API(
            "test-distribution",
            "test-package",
            "1.0.0",
        ),
        API(
            "test-distribution",
            "test-package",
            "1.0.1",
        ),
    ),
]


@pytest.mark.parametrize(
    "differ",
    differ_list,
)
def test_attribute_similarity(differ: AbstractDiffer) -> None:
    attribute_a = Attribute("test_string", NamedType("str"))
    assert differ.compute_attribute_similarity(attribute_a, attribute_a) == 1

    attribute_b = Attribute("new_test_string", NamedType("str"))
    assert differ.compute_attribute_similarity(attribute_a, attribute_b) >= 0.5

    attribute_a = Attribute("value", UnionType([NamedType("str"), NamedType("int")]))
    attribute_b = Attribute("value", UnionType([NamedType("str"), NamedType("bool")]))
    assert differ.compute_attribute_similarity(attribute_a, attribute_b) >= 0.5


@pytest.mark.parametrize(
    "differ",
    differ_list,
)
def test_class_similarity(differ: AbstractDiffer) -> None:
    code_a = cleandoc(
        """
    class Test:
        pass""",
    )
    class_a = Class(
        id="test/test.Test",
        qname="Test",
        decorators=[],
        superclasses=[],
        is_public=True,
        reexported_by=[],
        documentation=ClassDocstring("This is a test"),
        code=code_a,
        instance_attributes=[],
    )
    assert differ.compute_class_similarity(class_a, class_a) == 1

    code_b = cleandoc(
        """
    class newTest:
        pass""",
    )
    class_b = Class(
        id="test/test.newTest",
        qname="newTest",
        decorators=[],
        superclasses=[],
        is_public=True,
        reexported_by=[],
        documentation=ClassDocstring("This is a new test"),
        code=code_b,
        instance_attributes=[],
    )
    assert differ.compute_class_similarity(class_a, class_b) > 0.6


@pytest.mark.parametrize(
    "differ",
    differ_list,
)
def test_function_similarity(differ: AbstractDiffer) -> None:
    parameters = [
        Parameter(
            id_="test/test.Test/test/test_parameter",
            name="test_parameter",
            qname="test.Test.test.test_parameter",
            default_value="'test_str'",
            assigned_by=ParameterAssignment.POSITION_OR_NAME,
            is_public=True,
            documentation=ParameterDocumentation("'test_str'", "", ""),
        ),
    ]
    results: list[Result] = []
    code_a = cleandoc(
        """
    def test(test_parameter: str):
        \"\"\"
        This test function is a work
        \"\"\"
        return "test"
    """,
    )
    function_a = Function(
        id="test/test.Test/test",
        qname="test.Test.test",
        decorators=[],
        parameters=parameters,
        results=results,
        is_public=True,
        reexported_by=[],
        documentation=FunctionDocumentation(
            "This test function is a proof of work",
        ),
        code=code_a,
    )
    assert differ.compute_function_similarity(function_a, function_a) == 1

    code_b = cleandoc(
        """
    def test_method(test_parameter: str):
        \"\"\"
        This test function is a concept.
        \"\"\"
        return "test"
    """,
    )
    parameters = [
        Parameter(
            id_="test/test.Test/test_method/test_parameter",
            name="test_parameter",
            qname="test.Test.test_method.test_parameter",
            default_value="'test_str'",
            assigned_by=ParameterAssignment.POSITION_OR_NAME,
            is_public=True,
            documentation=ParameterDocumentation("'test_str'", "", ""),
        ),
    ]
    function_b = Function(
        id="test/test.Test/test_method",
        qname="test.Test.test_method",
        decorators=[],
        parameters=parameters,
        results=results,
        is_public=True,
        reexported_by=[],
        documentation=FunctionDocumentation(
            "This test function is a proof of concept.",
        ),
        code=code_b,
    )
    assert differ.compute_function_similarity(function_a, function_b) > 0.5


@pytest.mark.parametrize(
    "differ",
    differ_list,
)
def test_parameter_similarity(differ: AbstractDiffer) -> None:
    parameter_a = Parameter(
        id_="test/test.Test/test_method/test_parameter",
        name="test_parameter",
        qname="test.Test.test_method.test_parameter",
        default_value="'str'",
        assigned_by=ParameterAssignment.POSITION_OR_NAME,
        is_public=True,
        documentation=ParameterDocumentation("'str'", "", ""),
    )
    parameter_b = Parameter(
        id_="test/test.Test/test_method/test_parameter",
        name="test_parameter",
        qname="test.Test.test_method.test_parameter",
        default_value="5",
        assigned_by=ParameterAssignment.POSITION_OR_NAME,
        is_public=True,
        documentation=ParameterDocumentation("int", "", ""),
    )
    assert 0.45 < differ.compute_parameter_similarity(parameter_a, parameter_b) < 0.7

    parameter_a = Parameter(
        id_="test/test.Test/test_method/test_parameter_new_name",
        name="test_parameter_new_name",
        qname="test.Test.test_method.test_parameter_new_name",
        default_value="9",
        assigned_by=ParameterAssignment.POSITION_OR_NAME,
        is_public=True,
        documentation=ParameterDocumentation("int", "", ""),
    )
    assert 0.75 < differ.compute_parameter_similarity(parameter_a, parameter_b) < 0.9


@pytest.mark.parametrize(
    "differ",
    differ_list,
)
def test_result_similarity(differ: AbstractDiffer) -> None:
    result_a = Result("config", ResultDocstring("dict", ""))
    assert differ.compute_result_similarity(result_a, result_a) == 1

    result_b = Result(
        "new_config",
        ResultDocstring("dict", "A dictionary that includes the new configuration"),
    )
    assert differ.compute_result_similarity(result_a, result_b) > 0.3


def test_simple_differ() -> None:
    simple_differ = SimpleDiffer(
        None,
        [],
        API(
            "test-distribution",
            "test-package",
            "1.0.0",
        ),
        API(
            "test-distribution",
            "test-package",
            "1.0.1",
        ),
    )
    for dict_ in simple_differ.assigned_by_look_up_similarity.values():
        for similarity in dict_.values():
            assert similarity >= 0


def test_weighted_levenshtein_distance() -> None:
    differ = SimpleDiffer(None, [], API("", "", ""), API("", "", ""))

    def cost_function(iteration: int, max_iteration: int) -> float:
        return (max_iteration - iteration + 1) / max_iteration

    cost, max_iteration = differ.distance_elements_with_cost_function(
        ["a", "b", "c"],
        ["x", "b", "c"],
        cost_function=cost_function,
    )
    assert cost == 1
    assert max_iteration == 3

    cost, max_iteration = differ.distance_elements_with_cost_function(
        ["a", "b", "c"],
        ["a", "b", "z"],
        cost_function=cost_function,
    )
    assert cost == 1 / 3
    assert max_iteration == 3

    assert differ._compute_id_similarity("api/test.test.text/a", "api/tests.tests.texts/b") < 0.1e-10
