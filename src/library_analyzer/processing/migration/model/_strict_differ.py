from typing import TypeVar, Union

from library_analyzer.processing.api.model import (
    API,
    Attribute,
    Class,
    Function,
    Parameter,
    Result,
)

from ._differ import AbstractDiffer
from ._mapping import Mapping, OneToOneMapping

DEPENDENT_API_ELEMENTS = TypeVar("DEPENDENT_API_ELEMENTS", Function, Attribute, Parameter, Result)
api_element = Attribute | Class | Function | Parameter | Result


class StrictDiffer(AbstractDiffer):
    new_mappings: dict[
        type[Attribute] | type[Class] | type[Function] | type[Parameter] | type[Result],
        list[Mapping],
    ]
    differ: AbstractDiffer

    def __init__(
        self,
        previous_base_differ: AbstractDiffer,
        previous_mappings: list[Mapping],
        apiv1: API,
        apiv2: API,
        *,
        unchanged_mappings: list[Mapping] | None = None,
    ) -> None:
        super().__init__(previous_base_differ, previous_mappings, apiv1, apiv2)
        if unchanged_mappings is None:
            unchanged_mappings = []
        self.differ = previous_base_differ
        self.new_mappings = {
            Class: [],
            Attribute: [],
            Function: [],
            Parameter: [],
            Result: [],
        }
        sort_order = {
            Class: 0,
            Attribute: 1,
            Function: 2,
            Parameter: 3,
            Result: 4,
        }
        self.related_mappings = sorted(
            self.previous_mappings,
            key=lambda mapping: sort_order[type(mapping.get_apiv1_elements()[0])],
        )
        self.related_mappings = [
            mapping
            for mapping in self.related_mappings
            if mapping not in unchanged_mappings and not isinstance(mapping, OneToOneMapping)
        ]
        for mapping_list in [self.previous_mappings, unchanged_mappings]:
            for mapping in mapping_list:
                if mapping not in self.related_mappings:
                    self.new_mappings[type(mapping.get_apiv1_elements()[0])].append(mapping)
        self.unchanged_mappings = unchanged_mappings

    def get_related_mappings(
        self,
    ) -> list[Mapping] | None:
        """
        Whether all api elements should be compared to each other or just the ones that are mapped to each other.

        Returns
        -------
        mappings : list[Mapping] | None
            a list of Mappings if only previously mapped api elements should be mapped to each other or else None.
        """
        return self.related_mappings

    def notify_new_mapping(self, mappings: list[Mapping]) -> None:
        """
        If previous mappings return None, the differ will be notified about a new mapping.

        Thereby the differ can calculate the similarity with more information.

        Parameters
        ----------
        mappings : list[Mapping]
            a list of mappings new appended mappings.
        """
        for mapping in mappings:
            self.new_mappings[type(mapping.get_apiv1_elements()[0])].extend(mappings)

    def get_additional_mappings(self) -> list[Mapping]:
        """
        Allow the differ to add further mappings from previous differs.

        Returns
        -------
        mappings : list[Mapping]
            additional mappings that should be included in the result of the differentiation.
        """
        return self.unchanged_mappings

    def _api_elements_are_mapped_to_each_other(
        self,
        api_elementv1: DEPENDENT_API_ELEMENTS,
        api_elementv2: DEPENDENT_API_ELEMENTS,
    ) -> bool:
        parentv1 = self.get_parent(api_elementv1, self.apiv1)
        if parentv1 is None:
            return False
        parentv2 = self.get_parent(api_elementv2, self.apiv2)
        if parentv2 is None:
            return False
        for mapping in self.new_mappings[self.get_parent_class(api_elementv1)]:
            if parentv1 in mapping.get_apiv1_elements() and parentv2 in mapping.get_apiv2_elements():
                return True
            if parentv1 in mapping.get_apiv1_elements() or parentv2 in mapping.get_apiv2_elements():
                return False
        return False

    def compute_class_similarity(self, classv1: Class, classv2: Class) -> float:
        """
        Compute the similarity between classes from apiv1 and apiv2.

        Parameters
        ----------
        classv1 : Class
            class from apiv1
        classv2 : Class
            class from apiv2

        Returns
        -------
        similarity : float
            if the classes are mapped together, the similarity of the previous differ, or else 0.
        """
        for mapping in self.previous_mappings:
            if classv1 in mapping.get_apiv1_elements() and classv2 in mapping.get_apiv2_elements():
                return self.differ.compute_class_similarity(classv1, classv2)
        return 0

    def compute_function_similarity(self, functionv1: Function, functionv2: Function) -> float:
        """
        Compute the similarity between functions from apiv1 and apiv2.

        Parameters
        ----------
        functionv1 : Function
            function from apiv1
        functionv2 : Function
            function from apiv2

        Returns
        -------
        similarity : float
            if their parents are mapped together, the similarity of the previous differ, or else 0.
        """
        is_global_functionv1 = len(functionv1.id.split("/")) == 3
        is_global_functionv2 = len(functionv2.id.split("/")) == 3
        if is_global_functionv1 and is_global_functionv2:
            for mapping in self.previous_mappings:
                if functionv1 in mapping.get_apiv1_elements() and functionv2 in mapping.get_apiv2_elements():
                    return self.differ.compute_function_similarity(functionv1, functionv2)
        elif (not is_global_functionv1 and not is_global_functionv2) and self._api_elements_are_mapped_to_each_other(
            functionv1,
            functionv2,
        ):
            return self.differ.compute_function_similarity(functionv1, functionv2)
        return 0.0

    def compute_parameter_similarity(self, parameterv1: Parameter, parameterv2: Parameter) -> float:
        """
        Compute similarity between parameters from apiv1 and apiv2.

        Parameters
        ----------
        parameterv1 : Parameter
            parameter from apiv1
        parameterv2 : Parameter
            parameter from apiv2

        Returns
        -------
        similarity : float
            if their parents are mapped together, the similarity of the previous differ, or else 0.
        """
        if self._api_elements_are_mapped_to_each_other(parameterv1, parameterv2):
            return self.differ.compute_parameter_similarity(parameterv1, parameterv2)
        return 0.0

    def compute_result_similarity(self, resultv1: Result, resultv2: Result) -> float:
        """
        Compute similarity between results from apiv1 and apiv2.

        Parameters
        ----------
        resultv1 : Result
            result from apiv1
        resultv2 : Result
            result from apiv2

        Returns
        -------
        similarity : float
            if their parents are mapped together, the similarity of the previous differ, or else 0.
        """
        if self._api_elements_are_mapped_to_each_other(resultv1, resultv2):
            return self.differ.compute_result_similarity(resultv1, resultv2)
        return 0.0

    def compute_attribute_similarity(self, attributev1: Attribute, attributev2: Attribute) -> float:
        """
        Compute the similarity between attributes from apiv1 and apiv2.

        Parameters
        ----------
        attributev1 : Attribute
            attribute from apiv1
        attributev2 : Attribute
            attribute from apiv2

        Returns
        -------
        similarity : float
            if their parents are mapped together, the similarity of the previous differ, or else 0.
        """
        if self._api_elements_are_mapped_to_each_other(attributev1, attributev2):
            return self.differ.compute_attribute_similarity(attributev1, attributev2)
        return 0.0

    def get_parent(self, element: DEPENDENT_API_ELEMENTS, api: API) -> api_element | None:
        if isinstance(element, Function):
            return api.classes.get(element.id[: element.id.rfind("/")])
        if isinstance(element, Parameter):
            return api.functions.get(element.id[: element.id.rfind("/")])
        if isinstance(element, Result):
            if element.function_id is None:
                return None
            return api.functions.get(element.function_id)
        if isinstance(element, Attribute):
            if element.class_id is None:
                return None
            return api.classes.get(element.class_id)
        return None

    def get_parent_class(
        self,
        element: DEPENDENT_API_ELEMENTS,
    ) -> type[Attribute] | type[Class] | type[Function] | type[Parameter] | type[Result]:
        if isinstance(element, Function | Attribute):
            return Class
        return Function
