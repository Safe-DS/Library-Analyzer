from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import astroid

    from library_analyzer.processing.api.model import (
        ClassDocumentation,
        FunctionDocumentation,
        ParameterAssignment,
        ParameterDocumentation,
    )


class AbstractDocumentationParser(ABC):
    @abstractmethod
    def get_class_documentation(self, class_node: astroid.ClassDef) -> ClassDocumentation:
        pass

    @abstractmethod
    def get_function_documentation(self, function_node: astroid.FunctionDef) -> FunctionDocumentation:
        pass

    @abstractmethod
    def get_parameter_documentation(
        self,
        function_node: astroid.FunctionDef,
        parameter_name: str,
        parameter_assigned_by: ParameterAssignment,
    ) -> ParameterDocumentation:
        pass
