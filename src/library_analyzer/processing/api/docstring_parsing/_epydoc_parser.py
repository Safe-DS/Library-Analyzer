import astroid
from docstring_parser import Docstring, DocstringParam, DocstringStyle, DocstringMeta
from docstring_parser import parse as parse_docstring

from library_analyzer.processing.api.model import (
    ClassDocstring,
    FunctionDocstring,
    ParameterAssignment,
    ParameterDocstring,
    ResultDocstring
)

from ._abstract_docstring_parser import AbstractDocstringParser
from ._helpers import get_description, get_full_docstring


class EpydocParser(AbstractDocstringParser):
    """
    Parses documentation in the Epydoc format. See http://epydoc.sourceforge.net/epytext.html for more information.

    This class is not thread-safe. Each thread should create its own instance.
    """

    def __init__(self) -> None:
        self.__cached_function_node: astroid.FunctionDef | None = None
        self.__cached_docstring: DocstringParam | None = None

    def get_class_documentation(self, class_node: astroid.ClassDef) -> ClassDocstring:
        docstring = get_full_docstring(class_node)
        docstring_obj = parse_docstring(docstring, style=DocstringStyle.EPYDOC)

        return ClassDocstring(
            description=get_description(docstring_obj),
            full_docstring=docstring,
        )

    def get_function_documentation(self, function_node: astroid.FunctionDef) -> FunctionDocstring:
        docstring = get_full_docstring(function_node)
        docstring_obj = self.__get_cached_function_epydoc_string(function_node, docstring)

        return FunctionDocstring(
            description=get_description(docstring_obj),
            full_docstring=docstring,
        )

    # Todo: 1. Should we seperate params and attributes?
    #   A Problem with 1. is that the params parser ignores @ivar but takes theire @type and adds it to params
    #   2. Parse default value of attributes
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
        function_epydoc = self.__get_cached_function_epydoc_string(function_node, docstring)
        all_parameters_epydoc: list[DocstringParam] = function_epydoc.params
        matching_parameters_epydoc = [it for it in all_parameters_epydoc if it.arg_name == parameter_name]

        # Find matching attribute docstrings
        all_attributes_epydoc: list[DocstringMeta] = function_epydoc.meta
        matching_attributes_epydoc = [
            it for it in all_attributes_epydoc
            if it.args[0] == "ivar" and it.args[1] == parameter_name
        ]

        if len(matching_parameters_epydoc) == 0 and len(matching_attributes_epydoc) == 0:
            return ParameterDocstring(type="", default_value="", description="")

        # Only found parameters
        if len(matching_parameters_epydoc) != 0 and len(matching_attributes_epydoc) == 0:
            last_parameter_docstring_obj = matching_parameters_epydoc[-1]
            return ParameterDocstring(
                type=last_parameter_docstring_obj.type_name or "",
                default_value=last_parameter_docstring_obj.default or "",
                description=last_parameter_docstring_obj.description,
            )

        # Only found attributes
        if len(matching_parameters_epydoc) == 0 and len(matching_attributes_epydoc) != 0:
            last_attribute_docstring_obj = matching_attributes_epydoc[-1]
            return ParameterDocstring(
                type="",
                default_value="", # todo default value of attr
                description=last_attribute_docstring_obj.description,
            )

        # Found both, parameters and attributes
        last_attribute_docstring_obj = matching_attributes_epydoc[-1]
        last_parameter_docstring_obj = matching_parameters_epydoc[-1]
        return ParameterDocstring(
            type=last_parameter_docstring_obj.type_name or "",
            default_value=last_parameter_docstring_obj.default or "", # todo default value of attr
            description=last_attribute_docstring_obj.description,
        )

    def get_result_documentation(self, function_node: astroid.FunctionDef) -> ResultDocstring:
        if function_node.name == "__init__" and isinstance(function_node.parent, astroid.ClassDef):
            docstring = get_full_docstring(function_node.parent)
        else:
            docstring = get_full_docstring(function_node)

        # Find matching parameter docstrings
        function_epydoc = self.__get_cached_function_epydoc_string(function_node, docstring)
        function_returns = function_epydoc.returns

        if function_returns is None:
            return ResultDocstring(type="", description="")

        return ResultDocstring(
            type=function_returns.type_name or "",
            description=function_returns.description or ""
        )

    def __get_cached_function_epydoc_string(self, function_node: astroid.FunctionDef, docstring: str) -> Docstring:
        """
        Return the EpyDocString for the given function node.

        It is only recomputed when the function node differs from the previous one that was passed to this function.
        This avoids reparsing the docstring for the function itself and all of its parameters.

        On Lars's system this caused a significant performance improvement: Previously, 8.382s were spent inside the
        function get_parameter_documentation when parsing sklearn. Afterward, it was only 2.113s.
        """
        if self.__cached_function_node is not function_node:
            self.__cached_function_node = function_node
            self.__cached_docstring = parse_docstring(docstring, style=DocstringStyle.EPYDOC)

        return self.__cached_docstring
