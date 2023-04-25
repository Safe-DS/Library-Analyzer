from inspect import cleandoc

import pytest
from library_analyzer.processing.api.model import (
    API,
    Attribute,
    Class,
    ClassDocstring,
    Function,
    FunctionDocstring,
    NamedType,
    Parameter,
    ParameterAssignment,
    ParameterDocstring,
    Result,
    ResultDocstring,
)
from library_analyzer.processing.migration.model import (
    AbstractDiffer,
    OneToOneMapping,
    StrictDiffer,
)

from .test_differ import differ_list


@pytest.mark.parametrize(
    "differ",
    differ_list,
)
def test_similarity(differ: AbstractDiffer) -> None:
    apiv1 = API("test-distribution", "test-package", "1.0")
    apiv2 = API("test-distribution", "test-package", "2.0")
    code_a = cleandoc(
        """
    class Test:
        pass""",
    )
    class_id_a = "test/test/Test"
    attribute_a = Attribute("new_test_string", NamedType("str"), class_id=class_id_a)
    class_a = Class(
        id=class_id_a,
        qname="test.Test",
        decorators=[],
        superclasses=[],
        is_public=True,
        reexported_by=[],
        documentation=ClassDocstring("This is a test"),
        code=code_a,
        instance_attributes=[attribute_a],
    )

    code_b = cleandoc(
        """
    class newTest:
        pass""",
    )
    class_id_b = "test/test/NewTest"
    attribute_b = Attribute("test_string", NamedType("str"), class_id=class_id_b)
    class_b = Class(
        id=class_id_b,
        qname="test.newTest",
        decorators=[],
        superclasses=[],
        is_public=True,
        reexported_by=[],
        documentation=ClassDocstring("This is a new test"),
        code=code_b,
        instance_attributes=[attribute_b],
    )
    apiv1.add_class(class_a)
    apiv2.add_class(class_b)

    function_id_a = class_id_a + "/test_function"
    parameter_a = Parameter(
        id_=function_id_a + "/test_parameter",
        name="test_parameter",
        qname="test.Test.test_function.test_parameter",
        default_value="'test_str_a'",
        assigned_by=ParameterAssignment.POSITION_OR_NAME,
        is_public=True,
        documentation=ParameterDocstring("'test_str_a'", "", ""),
    )
    result_a = Result("config", ResultDocstring("dict", ""), function_id=function_id_a)
    code_function_a = cleandoc(
        """
    def test(test_parameter: str):
        \"\"\"
        This test function is a work
        \"\"\"
        return "test"
    """,
    )
    function_a = Function(
        id=function_id_a,
        qname="test.Test.test",
        decorators=[],
        parameters=[parameter_a],
        results=[result_a],
        is_public=True,
        reexported_by=[],
        documentation=FunctionDocstring(
            "This test function is a for testing",
        ),
        code=code_function_a,
    )
    function_id_b = class_id_b + "/test_method"
    code_b = cleandoc(
        """
    def test_method(test_parameter: str):
        \"\"\"
        This test function is a concept.
        \"\"\"
        return "test"
    """,
    )
    parameter_b = Parameter(
        id_=function_id_b + "/test_parameter",
        name="test_parameter",
        qname="test.Test.test_method.test_parameter",
        default_value="'test_str_b'",
        assigned_by=ParameterAssignment.POSITION_OR_NAME,
        is_public=True,
        documentation=ParameterDocstring("'test_str_b'", "", ""),
    )
    result_b = Result(
        "new_config",
        ResultDocstring("dict", "A dictionary that includes the new configuration"),
        function_id=function_id_b,
    )
    function_b = Function(
        id=function_id_b,
        qname="test.Test.test_method",
        decorators=[],
        parameters=[parameter_b],
        results=[result_b],
        is_public=True,
        reexported_by=[],
        documentation=FunctionDocstring(
            "This test function is a test",
        ),
        code=code_b,
    )
    apiv1.add_function(function_a)
    apiv2.add_function(function_b)

    class_mapping = OneToOneMapping(1.0, class_a, class_b)
    function_mapping = OneToOneMapping(1.0, function_a, function_b)

    strict_differ = StrictDiffer(differ, [], apiv1, apiv2)
    assert strict_differ.compute_class_similarity(class_a, class_b) == 0
    assert strict_differ.compute_attribute_similarity(attribute_a, attribute_b) == 0
    assert strict_differ.compute_function_similarity(function_a, function_b) == 0
    assert strict_differ.compute_parameter_similarity(parameter_a, parameter_b) == 0
    assert strict_differ.compute_result_similarity(result_a, result_b) == 0

    strict_differ = StrictDiffer(differ, [class_mapping], apiv1, apiv2)
    assert strict_differ.compute_class_similarity(class_a, class_b) > 0
    strict_differ.notify_new_mapping([class_mapping])
    assert strict_differ.compute_attribute_similarity(attribute_a, attribute_b) > 0
    assert strict_differ.compute_function_similarity(function_a, function_b) > 0
    assert strict_differ.compute_parameter_similarity(parameter_a, parameter_b) == 0
    assert strict_differ.compute_result_similarity(result_a, result_b) == 0

    strict_differ_notify_all = StrictDiffer(
        differ,
        [
            class_mapping,
            OneToOneMapping(1.0, attribute_a, attribute_b),
            function_mapping,
            OneToOneMapping(1.0, parameter_a, parameter_b),
            OneToOneMapping(1.0, result_a, result_b),
        ],
        apiv1,
        apiv2,
    )
    assert strict_differ_notify_all.compute_class_similarity(class_a, class_b) > 0
    strict_differ_notify_all.notify_new_mapping([class_mapping])
    assert strict_differ_notify_all.compute_attribute_similarity(attribute_a, attribute_b) > 0
    assert strict_differ_notify_all.compute_function_similarity(function_a, function_b) > 0
    strict_differ_notify_all.notify_new_mapping([function_mapping])
    assert strict_differ_notify_all.compute_parameter_similarity(parameter_a, parameter_b) > 0
    assert strict_differ_notify_all.compute_result_similarity(result_a, result_b) > 0
