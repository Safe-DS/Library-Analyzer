import astroid

from library_analyzer.processing.api.model import (
    ClassDocumentation,
    FunctionDocumentation,
    ParameterAssignment,
    ParameterDocumentation,
)

from ._abstract_documentation_parser import AbstractDocstringParser
from ._helpers import get_full_docstring


class PlaintextDocstringParser(AbstractDocstringParser):
    """Parses documentation in any format. Should not be used if there is another parser for the specific format."""

    def get_class_documentation(self, class_node: astroid.ClassDef) -> ClassDocumentation:
        return ClassDocumentation(
            description=get_full_docstring(class_node),
        )

    def get_function_documentation(self, function_node: astroid.FunctionDef) -> FunctionDocumentation:
        return FunctionDocumentation(
            description=get_full_docstring(function_node),
        )

    def get_parameter_documentation(
        self,
        function_node: astroid.FunctionDef,  # noqa: ARG002
        parameter_name: str,  # noqa: ARG002
        parameter_assigned_by: ParameterAssignment,  # noqa: ARG002
    ) -> ParameterDocumentation:
        return ParameterDocumentation()
