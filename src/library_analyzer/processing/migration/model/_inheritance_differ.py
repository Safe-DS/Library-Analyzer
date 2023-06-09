from typing import Union

from library_analyzer.processing.api.model import (
    API,
    Attribute,
    Class,
    Function,
    Parameter,
    Result,
)

from ._differ import AbstractDiffer
from ._get_unmapped_api_elements import _get_unmapped_api_elements
from ._mapping import Mapping

api_element = Union[Attribute, Class, Function, Parameter, Result]


class InheritanceDiffer(AbstractDiffer):
    boost_value: float
    differ: AbstractDiffer
    inheritance: dict[str, list[str]]
    new_mappings: list[Mapping]

    def __init__(
        self,
        previous_base_differ: AbstractDiffer,
        previous_mappings: list[Mapping],
        apiv1: API,
        apiv2: API,
        boost_value: float = 0.15,
    ) -> None:
        super().__init__(previous_base_differ, previous_mappings, apiv1, apiv2)
        self.differ = previous_base_differ
        self.boost_value = boost_value
        self.inheritance = {}
        self.new_mappings = []
        self.related_mappings = _get_unmapped_api_elements(self.previous_mappings, self.apiv1, self.apiv2)
        for class_v2 in self.apiv2.classes.values():
            additional_v1_elements = []
            for mapping in previous_mappings:
                if isinstance(mapping.get_apiv2_elements()[0], Class):
                    is_inheritance_mapping = class_v2.id in (
                        class_.id if isinstance(class_, Class) else "" for class_ in mapping.get_apiv2_elements()
                    )
                    if not is_inheritance_mapping:
                        for inheritance_class_v2 in mapping.get_apiv2_elements():
                            if isinstance(inheritance_class_v2, Class) and (
                                inheritance_class_v2.name in class_v2.superclasses
                                or class_v2.name in inheritance_class_v2.superclasses
                            ):
                                is_inheritance_mapping = True
                                break
                    if is_inheritance_mapping:
                        for class_v1 in mapping.get_apiv1_elements():
                            if isinstance(class_v1, Class):
                                additional_v1_elements.append(class_v1.id)
            if len(additional_v1_elements) > 0:
                self.inheritance[class_v2.id] = additional_v1_elements

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
            if the parent of the attributes are mapped onto each other or onto a super- or subclass, the normalized
            similarity of the previous differ plus boost_value, or else 0.
        """
        if attributev2.class_id in self.inheritance and attributev1.class_id in self.inheritance[attributev2.class_id]:
            return (
                self.differ.compute_attribute_similarity(attributev1, attributev2) * (1 - self.boost_value)
            ) + self.boost_value
        return 0.0

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
            if the classes are mapped onto each other or onto a super- or subclass, the normalized similarity of the
            previous differ plus boost_value, or else 0.
        """
        if classv2.id in self.inheritance:
            for mapping in self.previous_mappings:
                for elementv2 in mapping.get_apiv2_elements():
                    if isinstance(elementv2, Class) and elementv2.id in self.inheritance[classv2.id]:
                        return (
                            self.differ.compute_class_similarity(classv1, classv2) * (1 - self.boost_value)
                        ) + self.boost_value
        return 0.0

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
            if functions are not global functions and its parent are mapped onto each other or onto a super- or
            subclass, the normalized similarity of the previous differ plus boost_value, or else 0.
        """
        functionv1_is_global = len(functionv1.id.split("/")) == 3
        functionv2_is_global = len(functionv2.id.split("/")) == 3
        if functionv1_is_global or functionv2_is_global:
            return 0.0
        class_id_functionv1 = "/".join(functionv1.id.split("/")[:-1])
        class_id_functionv2 = "/".join(functionv2.id.split("/")[:-1])
        if class_id_functionv2 in self.inheritance and class_id_functionv1 in self.inheritance[class_id_functionv2]:
            base_similarity = self.differ.compute_function_similarity(functionv1, functionv2)
            return (base_similarity * (1 - self.boost_value)) + self.boost_value
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
            if their parents are mapped together, the normalized similarity of the previous differ plus boost_value,
            or else 0.
        """
        parameterv2_id_splitted = parameterv2.id.split("/")
        if "/".join(parameterv2_id_splitted[:-2]) in self.inheritance:
            functionv1_id = "/".join(parameterv1.id.split("/")[:-1])
            for mapping in self.new_mappings:
                for functionv1 in mapping.get_apiv1_elements():
                    if isinstance(functionv1, Function) and functionv1_id == functionv1.id:
                        for functionv2 in mapping.get_apiv2_elements():
                            if (
                                isinstance(functionv2, Function)
                                and "/".join(parameterv2_id_splitted[:-1]) == functionv2.id
                            ):
                                return (
                                    self.differ.compute_parameter_similarity(parameterv1, parameterv2)
                                    * (1 - self.boost_value)
                                ) + self.boost_value
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
            if their parents are mapped together, the normalized similarity of the previous differ plus boost_value,
            or else 0.
        """
        if resultv2.function_id is not None and "/".join(resultv2.function_id.split("/")[:-1]) in self.inheritance:
            for mapping in self.new_mappings:
                for functionv1 in mapping.get_apiv1_elements():
                    if isinstance(functionv1, Function) and resultv1.function_id == functionv1.id:
                        for functionv2 in mapping.get_apiv2_elements():
                            if isinstance(functionv2, Function) and resultv2.function_id == functionv2.id:
                                return (
                                    self.differ.compute_result_similarity(resultv1, resultv2) * (1 - self.boost_value)
                                ) + self.boost_value
        return 0.0

    def get_related_mappings(self) -> list[Mapping] | None:
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
        self.new_mappings.extend(mappings)

    def get_additional_mappings(self) -> list[Mapping]:
        """
        Allow the differ to add further mappings from previous differs.

        Returns
        -------
        mappings : list[Mapping]
            additional mappings that should be included in the result of the differentiation.
        """
        return self.previous_mappings
