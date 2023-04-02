from typing import TypeVar

from library_analyzer.processing.annotations.model import AbstractAnnotation
from library_analyzer.processing.api.model import (
    Attribute,
    Class,
    Function,
    Parameter,
    Result,
)

API_ELEMENTS = TypeVar("API_ELEMENTS", Class, Function, Parameter)


def get_annotated_api_element(
    annotation: AbstractAnnotation,
    api_element_list: list[Attribute | Class | Function | Parameter | Result],
) -> Class | Function | Parameter | None:
    for element in api_element_list:
        if isinstance(element, Class | Function | Parameter) and element.id == annotation.target:
            return element
    return None


def get_annotated_api_element_by_type(
    annotation: AbstractAnnotation,
    api_element_list: list[Attribute | Class | Function | Parameter | Result],
    api_type: type[API_ELEMENTS],
) -> API_ELEMENTS | None:
    for element in api_element_list:
        if isinstance(element, api_type) and element.id == annotation.target:
            return element
    return None
