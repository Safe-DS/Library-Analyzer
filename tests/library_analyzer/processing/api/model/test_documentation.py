import pytest
from library_analyzer.processing.api.model import (
    ClassDocstring,
    FunctionDocstring,
    ParameterDocstring,
)


@pytest.mark.parametrize(
    "class_documentation",
    [
        ClassDocstring(),
        ClassDocstring(description="foo"),
    ],
)
def test_dict_conversion_for_class_documentation(
    class_documentation: ClassDocstring,
) -> None:
    assert ClassDocstring.from_dict(class_documentation.to_dict()) == class_documentation


@pytest.mark.parametrize(
    "function_documentation",
    [
        FunctionDocstring(),
        FunctionDocstring(description="foo"),
    ],
)
def test_dict_conversion_for_function_documentation(
    function_documentation: FunctionDocstring,
) -> None:
    assert FunctionDocstring.from_dict(function_documentation.to_dict()) == function_documentation


@pytest.mark.parametrize(
    "parameter_documentation",
    [
        ParameterDocstring(),
        ParameterDocstring(type="int", default_value="1", description="foo bar"),
    ],
)
def test_dict_conversion_for_parameter_documentation(
    parameter_documentation: ParameterDocstring,
) -> None:
    assert ParameterDocstring.from_dict(parameter_documentation.to_dict()) == parameter_documentation
