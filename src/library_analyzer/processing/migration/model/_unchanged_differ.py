from copy import deepcopy
from typing import TypeVar

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


class UnchangedDiffer(AbstractDiffer):
    def __init__(
        self,
        previous_base_differ: AbstractDiffer | None,
        previous_mappings: list[Mapping],
        apiv1: API,
        apiv2: API,
    ) -> None:
        super().__init__(previous_base_differ, previous_mappings, apiv1, apiv2)
        self.unchanged_api_mappings: list[Mapping] = []
        for classv1 in apiv1.classes.values():
            classv2 = apiv2.classes.get(classv1.id, None)
            if classv2 is not None and self.have_same_api(classv1, classv2):
                self.unchanged_api_mappings.append(OneToOneMapping(1.0, classv1, classv2))

        for functionv1 in apiv1.functions.values():
            functionv2 = apiv2.functions.get(functionv1.id, None)
            if functionv2 is not None and self.have_same_api(functionv1, functionv2):
                self.unchanged_api_mappings.append(OneToOneMapping(1.0, functionv1, functionv2))

        for parameterv1 in apiv1.parameters().values():
            parameterv2 = apiv2.parameters().get(parameterv1.id, None)
            if parameterv2 is not None and self.have_same_api(parameterv1, parameterv2):
                self.unchanged_api_mappings.append(OneToOneMapping(1.0, parameterv1, parameterv2))

        for attributev1 in apiv1.attributes().values():
            attributev2 = apiv2.attributes().get(f"{attributev1.class_id}/{attributev1.name}", None)
            if attributev2 is not None and self.have_same_api(attributev1, attributev2):
                self.unchanged_api_mappings.append(OneToOneMapping(1.0, attributev1, attributev2))

        for resultv1 in apiv1.results().values():
            resultv2 = apiv2.results().get(f"{resultv1.function_id}/{resultv1.name}", None)
            if resultv2 is not None and self.have_same_api(resultv1, resultv2):
                self.unchanged_api_mappings.append(OneToOneMapping(1.0, resultv1, resultv2))

    API_ELEMENTS = TypeVar("API_ELEMENTS", Attribute, Class, Function, Parameter, Result)

    def have_same_api(self, api_elementv1: API_ELEMENTS, api_elementv2: API_ELEMENTS) -> bool:
        if isinstance(api_elementv1, Class | Function):
            memo = {id(api_elementv1.code): "", id(api_elementv2.code): ""}
            api_elementv1 = deepcopy(api_elementv1, memo=memo)
            api_elementv2 = deepcopy(api_elementv2, memo=memo)
        return api_elementv1 == api_elementv2

    def compute_attribute_similarity(self, attributev1: Attribute, attributev2: Attribute) -> float:  # noqa: ARG002
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
            value between 0 and 1, where 1 means that the elements are equal.
        """
        return 0.0

    def compute_class_similarity(self, classv1: Class, classv2: Class) -> float:  # noqa: ARG002
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
            value between 0 and 1, where 1 means that the elements are equal.
        """
        return 0.0

    def compute_function_similarity(self, functionv1: Function, functionv2: Function) -> float:  # noqa: ARG002
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
            value between 0 and 1, where 1 means that the elements are equal.
        """
        return 0.0

    def compute_parameter_similarity(self, parameterv1: Parameter, parameterv2: Parameter) -> float:  # noqa: ARG002
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
            value between 0 and 1, where 1 means that the elements are equal.
        """
        return 0.0

    def compute_result_similarity(self, resultv1: Result, resultv2: Result) -> float:  # noqa: ARG002
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
            value between 0 and 1, where 1 means that the elements are equal.
        """
        return 0.0

    def get_related_mappings(self) -> list[Mapping] | None:
        """
        Whether all api elements should be compared to each other or just the ones that are mapped to each other.

        Returns
        -------
        mappings : list[Mapping] | None
            a list of Mappings if only previously mapped api elements should be mapped to each other or else None.
        """
        return []

    def notify_new_mapping(self, mappings: list[Mapping]) -> None:
        """
        If previous mappings return None, the differ will be notified about a new mapping.

        Thereby the differ can calculate the similarity with more information.

        Parameters
        ----------
        mappings : list[Mapping]
            a list of mappings new appended mappings.
        """

    def get_additional_mappings(self) -> list[Mapping]:
        """
        Allow the differ to add further mappings from previous differs.

        Returns
        -------
        mappings : list[Mapping]
            additional mappings that should be included in the result of the differentiation.
        """
        return self.unchanged_api_mappings
