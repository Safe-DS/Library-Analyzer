import re

import astroid
from docstring_parser import Docstring, DocstringParam, DocstringStyle
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


class NumpyDocParser(AbstractDocstringParser):
    """
    Parse documentation in the NumpyDoc format.

    Notes
    -----
    This class is not thread-safe. Each thread should create its own instance.

    References
    ----------
    .. [1] https://numpydoc.readthedocs.io/en/latest/format.html
    """

    def __init__(self) -> None:
        self.__cached_function_node: astroid.FunctionDef | None = None
        self.__cached_docstring: Docstring | None = None

    def get_class_documentation(self, class_node: astroid.ClassDef) -> ClassDocstring:
        docstring = get_full_docstring(class_node)
        docstring_obj = parse_docstring(docstring, style=DocstringStyle.NUMPYDOC)

        return ClassDocstring(
            description=get_description(docstring_obj),
            full_docstring=docstring,
        )

    def get_function_documentation(self, function_node: astroid.FunctionDef) -> FunctionDocstring:
        docstring = get_full_docstring(function_node)
        docstring_obj = self.__get_cached_function_numpydoc_string(function_node, docstring)

        return FunctionDocstring(
            description=get_description(docstring_obj),
            full_docstring=docstring,
        )

    def get_parameter_documentation(
        self,
        function_node: astroid.FunctionDef,
        parameter_name: str,
        parameter_assigned_by: ParameterAssignment,
    ) -> ParameterDocstring:
        # For constructors (__init__ functions) the parameters are described on the class
        if function_node.name == "__init__" and isinstance(function_node.parent, astroid.ClassDef):
            docstring = get_full_docstring(function_node.parent)
        else:
            docstring = get_full_docstring(function_node)

        # Find matching parameter docstrings
        function_numpydoc = self.__get_cached_function_numpydoc_string(function_node, docstring)
        all_parameters_numpydoc: list[DocstringParam] = function_numpydoc.params
        matching_parameters_numpydoc = [
            it
            for it in all_parameters_numpydoc
            if _is_matching_parameter_numpydoc(it, parameter_name, parameter_assigned_by)
        ]

        if len(matching_parameters_numpydoc) == 0:
            # If we have a constructor we have to check both, the class and then the constructor (see issue #10)
            if function_node.name == "__init__":
                docstring_constructor = get_full_docstring(function_node)
                # Find matching parameter docstrings
                function_numpydoc = parse_docstring(docstring_constructor, style=DocstringStyle.NUMPYDOC)
                all_parameters_numpydoc: list[DocstringParam] = function_numpydoc.params

                # Overwrite previous matching_parameters_numpydoc list
                matching_parameters_numpydoc = [
                    it
                    for it in all_parameters_numpydoc
                    if _is_matching_parameter_numpydoc(it, parameter_name, parameter_assigned_by)
                ]

        if len(matching_parameters_numpydoc) == 0:
            return ParameterDocstring(type="", default_value="", description="")

        last_parameter_numpydoc = matching_parameters_numpydoc[-1]
        type_, default_value = _get_type_and_default_value(last_parameter_numpydoc)
        return ParameterDocstring(
            type=type_,
            default_value=default_value,
            description=last_parameter_numpydoc.description,
        )

    def get_result_documentation(self, function_node: astroid.FunctionDef):
        # For constructors (__init__ functions) the parameters are described on the class
        if function_node.name == "__init__" and isinstance(function_node.parent, astroid.ClassDef):
            docstring = get_full_docstring(function_node.parent)
        else:
            docstring = get_full_docstring(function_node)

        # Find matching parameter docstrings
        function_numpydoc = self.__get_cached_function_numpydoc_string(function_node, docstring)
        function_result = function_numpydoc.returns

        if function_result is None:
            return ResultDocstring(type="", description="")

        return ResultDocstring(
            type=function_result.type_name or "",
            description=function_result.description or "",
        )

    def __get_cached_function_numpydoc_string(
        self,
        function_node: astroid.FunctionDef,
        docstring: str,
    ) -> Docstring:
        """
        Return the NumpyDocString for the given function node.

        It is only recomputed when the function node differs from the previous one that was passed to this function.
        This avoids reparsing the docstring for the function itself and all of its parameters.

        On Lars's system this caused a significant performance improvement: Previously, 8.382s were spent inside the
        function `get_parameter_documentation` when parsing sklearn. Afterwards, it was only 2.113s.
        """
        if self.__cached_function_node is not function_node:
            self.__cached_function_node = function_node
            self.__cached_docstring = parse_docstring(docstring, style=DocstringStyle.NUMPYDOC)

        return self.__cached_docstring


def _is_matching_parameter_numpydoc(
    parameter_docstring_obj: DocstringParam,
    parameter_name: str,
    parameter_assigned_by: ParameterAssignment,
) -> bool:
    """Return whether the given docstring object applies to the parameter with the given name."""
    if parameter_assigned_by == ParameterAssignment.POSITIONAL_VARARG:
        lookup_name = f"*{parameter_name}"
    elif parameter_assigned_by == ParameterAssignment.NAMED_VARARG:
        lookup_name = f"**{parameter_name}"
    else:
        lookup_name = parameter_name

    # Numpydoc allows multiple parameters to be documented at once. See
    # https://numpydoc.readthedocs.io/en/latest/format.html#parameters for more information.
    return any(name.strip() == lookup_name for name in parameter_docstring_obj.arg_name.split(","))


def _get_type_and_default_value(
    parameter_docstring_obj: DocstringParam,
) -> tuple[str, str]:
    """Return the type and default value for the given NumpyDoc."""
    type_name = parameter_docstring_obj.type_name or ""
    parts = re.split(r",\s*optional|,\s*default\s*[:=]?", type_name)

    if len(parts) != 2:
        return type_name.strip(), parameter_docstring_obj.default or ""

    return parts[0].strip(), parts[1].strip()
