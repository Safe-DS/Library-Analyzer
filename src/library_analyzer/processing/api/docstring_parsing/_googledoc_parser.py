import astroid
from docstring_parser import Docstring, DocstringParam, DocstringStyle
from docstring_parser import parse as parse_docstring

from library_analyzer.processing.api.model import (
    AttributeAssignment,
    AttributeDocstring,
    ClassDocstring,
    FunctionDocstring,
    ParameterAssignment,
    ParameterDocstring,
    ResultDocstring,
)

from ._abstract_docstring_parser import AbstractDocstringParser
from ._helpers import get_description, get_full_docstring


class GoogleDocParser(AbstractDocstringParser):
    """
    Parses documentation in the Googledoc format. See https://google.github.io/styleguide/pyguide.html#381-docstrings for more information.

    This class is not thread-safe. Each thread should create its own instance.
    """

    def __init__(self) -> None:
        self.__cached_function_node: astroid.FunctionDef | None = None
        self.__cached_docstring: DocstringParam | None = None

    def get_class_documentation(self, class_node: astroid.ClassDef) -> ClassDocstring:
        docstring = get_full_docstring(class_node)
        docstring_obj = parse_docstring(docstring, style=DocstringStyle.GOOGLE)

        return ClassDocstring(
            description=get_description(docstring_obj),
            full_docstring=docstring,
        )

    def get_function_documentation(self, function_node: astroid.FunctionDef) -> FunctionDocstring:
        docstring = get_full_docstring(function_node)
        docstring_obj = self.__get_cached_function_googledoc_string(function_node, docstring)

        return FunctionDocstring(
            description=get_description(docstring_obj),
            full_docstring=docstring,
        )

    def get_parameter_documentation(
        self,
        function_node: astroid.FunctionDef,
        parameter_name: str,
        parameter_assigned_by: ParameterAssignment,  # noqa: ARG002
    ) -> ParameterDocstring:
        # For constructors (__init__ functions) the parameters are described on the class
        if function_node.name == "__init__" and isinstance(function_node.parent, astroid.ClassDef):
            docstring = get_full_docstring(function_node.parent)
        else:
            docstring = get_full_docstring(function_node)

        # Find matching parameter docstrings
        function_googledoc = self.__get_cached_function_googledoc_string(function_node, docstring)
        all_parameters_googledoc: list[DocstringParam] = function_googledoc.params
        matching_parameters_googledoc = [
            it for it in all_parameters_googledoc if it.arg_name == parameter_name and it.args[0] == "param"
        ]

        if len(matching_parameters_googledoc) == 0:
            return ParameterDocstring(type="", default_value="", description="")

        last_parameter_docstring_obj = matching_parameters_googledoc[-1]
        return ParameterDocstring(
            type=last_parameter_docstring_obj.type_name or "",
            default_value=last_parameter_docstring_obj.default or "",
            description=last_parameter_docstring_obj.description or "",
        )

    def get_attribute_documentation(
        self,
        function_node: astroid.FunctionDef,
        attribute_name: str,
        attribute_assigned_by: AttributeAssignment,  # noqa: ARG002
    ) -> AttributeDocstring:
        # For constructors (__init__ functions) the attributes are described on the class
        if function_node.name == "__init__" and isinstance(function_node.parent, astroid.ClassDef):
            docstring = get_full_docstring(function_node.parent)
        else:
            docstring = get_full_docstring(function_node)

        # Find matching attribute docstrings
        function_googledoc = self.__get_cached_function_googledoc_string(function_node, docstring)
        all_attributes_googledoc: list[DocstringParam] = function_googledoc.params
        matching_attributes_googledoc = [
            it for it in all_attributes_googledoc if it.arg_name == attribute_name and it.args[0] == "attribute"
        ]

        if len(matching_attributes_googledoc) == 0:
            return AttributeDocstring(type="", default_value="", description="")

        last_attribute_docstring_obj = matching_attributes_googledoc[-1]
        return AttributeDocstring(
            type=last_attribute_docstring_obj.type_name or "",
            default_value=last_attribute_docstring_obj.default or "",
            description=last_attribute_docstring_obj.description,
        )

    def get_result_documentation(self, function_node: astroid.FunctionDef) -> ResultDocstring:
        if function_node.name == "__init__" and isinstance(function_node.parent, astroid.ClassDef):
            docstring = get_full_docstring(function_node.parent)
        else:
            docstring = get_full_docstring(function_node)

        # Find matching parameter docstrings
        function_googledoc = self.__get_cached_function_googledoc_string(function_node, docstring)
        function_returns = function_googledoc.returns

        if function_returns is None:
            return ResultDocstring(type="", description="")

        return ResultDocstring(type=function_returns.type_name or "", description=function_returns.description or "")

    def __get_cached_function_googledoc_string(self, function_node: astroid.FunctionDef, docstring: str) -> Docstring:
        """
        Return the GoogleDocString for the given function node.

        It is only recomputed when the function node differs from the previous one that was passed to this function.
        This avoids reparsing the docstring for the function itself and all of its parameters.

        On Lars's system this caused a significant performance improvement: Previously, 8.382s were spent inside the
        function get_parameter_documentation when parsing sklearn. Afterward, it was only 2.113s.
        """
        if self.__cached_function_node is not function_node:
            self.__cached_function_node = function_node
            self.__cached_docstring = parse_docstring(docstring, style=DocstringStyle.GOOGLE)

        return self.__cached_docstring
