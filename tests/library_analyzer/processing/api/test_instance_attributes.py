import inspect

import astroid
import pytest
from library_analyzer.processing.api import get_instance_attributes
from library_analyzer.processing.api.model import Attribute, NamedType


@pytest.mark.parametrize(
    ("class_code", "expected_attributes"),
    [
        (
            inspect.cleandoc(
                """
                             import dataclass

                             @dataclass.dataclass()
                             class TestClass:
                                 string_value : str

                             """,
            ),
            [Attribute("test/string_value", "string_value", NamedType("str"))],
        ),
        (
            inspect.cleandoc(
                """
                             class TestClass2:
                                 pass
                             """,
            ),
            [],
        ),
        (
            inspect.cleandoc(
                """
                             import dataclass

                             @dataclass.dataclass()
                             class TestClass3:
                                 \"\"\"A test class

                                 Parameters
                                 ----------
                                 other_class : object
                                 int_value : int, default=5
                                 \"\"\"
                                 other_class : object
                                 int_value : int = 5
                             """,
            ),
            [
                Attribute("test/other_class", "other_class", NamedType("object")),
                Attribute("test/int_value", "int_value", NamedType("int")),
            ],
        ),
        (
            inspect.cleandoc(
                """
                             class TestClass4:
                                 def __init__(self, int_value: int = 5) -> None:
                                     self.int_value = int_value
                                     self.bool_value: bool = True
                             """,
            ),
            [
                Attribute("test/int_value", "int_value", NamedType("int")),
                Attribute("test/bool_value", "bool_value", NamedType("bool")),
            ],
        ),
    ],
)
def test_instance_attributes(class_code: str, expected_attributes: list[Attribute]) -> None:
    module = astroid.parse(class_code)
    classes = [class_ for class_ in module.body if isinstance(class_, astroid.ClassDef)]
    assert len(classes) == 1
    assert get_instance_attributes(classes[0], "test") == expected_attributes
