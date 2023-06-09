import astroid

from library_analyzer.processing.api.model import (
    ClassDocstring,
    FunctionDocstring,
    ParameterAssignment,
    ParameterDocstring,
)

from ._abstract_docstring_parser import AbstractDocstringParser
from ._helpers import get_full_docstring


class PlaintextDocstringParser(AbstractDocstringParser):
    """Parses documentation in any format. Should not be used if there is another parser for the specific format."""

    def get_class_documentation(self, class_node: astroid.ClassDef) -> ClassDocstring:
        docstring = get_full_docstring(class_node)

        return ClassDocstring(
            description=docstring,
            full_docstring=docstring,
        )

    def get_function_documentation(self, function_node: astroid.FunctionDef) -> FunctionDocstring:
        docstring = get_full_docstring(function_node)

        return FunctionDocstring(
            description=docstring,
            full_docstring=docstring,
        )

    def get_parameter_documentation(
        self,
        function_node: astroid.FunctionDef,  # noqa: ARG002
        parameter_name: str,  # noqa: ARG002
        parameter_assigned_by: ParameterAssignment,  # noqa: ARG002
    ) -> ParameterDocstring:
        return ParameterDocstring()
