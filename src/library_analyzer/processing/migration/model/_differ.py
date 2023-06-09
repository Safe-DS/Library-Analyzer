from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeVar

from Levenshtein import distance

from library_analyzer.processing.api.model import (
    API,
    AbstractType,
    Attribute,
    Class,
    ClassDocstring,
    Function,
    FunctionDocstring,
    Parameter,
    ParameterAssignment,
    ParameterDocstring,
    Result,
    UnionType,
)

from ._get_unmapped_api_elements import _get_unmapped_api_elements

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from ._mapping import Mapping

api_element = Attribute | Class | Function | Parameter | Result


@dataclass
class AbstractDiffer(ABC):
    previous_base_differ: AbstractDiffer | None
    previous_mappings: list[Mapping]
    apiv1: API
    apiv2: API

    @abstractmethod
    def compute_attribute_similarity(
        self,
        attributev1: Attribute,
        attributev2: Attribute,
    ) -> float:
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

    @abstractmethod
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
            value between 0 and 1, where 1 means that the elements are equal.
        """

    @abstractmethod
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
            value between 0 and 1, where 1 means that the elements are equal.
        """

    @abstractmethod
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
            value between 0 and 1, where 1 means that the elements are equal.
        """

    @abstractmethod
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
            value between 0 and 1, where 1 means that the elements are equal.
        """

    @abstractmethod
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

    @abstractmethod
    def notify_new_mapping(self, mappings: list[Mapping]) -> None:
        """
        If previous mappings return None, the differ will be notified about a new mapping.

        Thereby the differ can calculate the similarity with more information.

        Parameters
        ----------
        mappings : list[Mapping]
            a list of mappings new appended mappings.
        """

    @abstractmethod
    def get_additional_mappings(self) -> list[Mapping]:
        """
        Allow the differ to add further mappings from previous differs.

        Returns
        -------
        mappings : list[Mapping]
            additional mappings that should be included in the result of the differentiation.
        """

    def is_base_differ(self) -> bool:
        return False


X = TypeVar("X")


class SimpleDiffer(AbstractDiffer):
    assigned_by_look_up_similarity: dict[ParameterAssignment, dict[ParameterAssignment, float]]
    previous_parameter_similarity: dict[str, dict[str, float]] = {}
    previous_function_similarity: dict[str, dict[str, float]] = {}
    formatted_code: dict[str, dict[str, list[str]]] = {"apiv1": {}, "apiv2": {}}

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

    def notify_new_mapping(self, mappings: list[Mapping]) -> None:  # noqa: ARG002
        """
        If previous mappings return None, the differ will be notified about a new mapping.

        Thereby the differ can calculate the similarity with more information.

        Parameters
        ----------
        mappings : list[Mapping]
            a list of mappings new appended mappings.
        """
        return

    def get_additional_mappings(self) -> list[Mapping]:
        """
        Allow the differ to add further mappings from previous differs.

        Returns
        -------
        mappings : list[Mapping]
            additional mappings that should be included in the result of the differentiation.
        """
        return self.previous_mappings

    def __init__(
        self,
        previous_base_differ: AbstractDiffer | None,
        previous_mappings: list[Mapping],
        apiv1: API,
        apiv2: API,
    ) -> None:
        super().__init__(previous_base_differ, previous_mappings, apiv1, apiv2)
        self.related_mappings = _get_unmapped_api_elements(self.previous_mappings, self.apiv1, self.apiv2)
        distance_between_implicit_and_explicit = 0.3
        distance_between_vararg_and_normal = 0.3
        distance_between_position_and_named = 0.3
        distance_between_both_to_one = distance_between_position_and_named / 2
        distance_between_one_to_both = distance_between_position_and_named / 2
        self.assigned_by_look_up_similarity = {
            ParameterAssignment.IMPLICIT: {
                ParameterAssignment.IMPLICIT: 1.0,
                ParameterAssignment.NAMED_VARARG: (
                    1.0
                    - distance_between_implicit_and_explicit
                    - distance_between_vararg_and_normal
                    - distance_between_position_and_named
                ),
                ParameterAssignment.POSITIONAL_VARARG: (
                    1.0 - distance_between_implicit_and_explicit - distance_between_vararg_and_normal
                ),
                ParameterAssignment.POSITION_OR_NAME: 1.0 - distance_between_implicit_and_explicit,
                ParameterAssignment.NAME_ONLY: 1.0 - distance_between_implicit_and_explicit,
                ParameterAssignment.POSITION_ONLY: 1.0 - distance_between_implicit_and_explicit,
            },
            ParameterAssignment.NAMED_VARARG: {
                ParameterAssignment.IMPLICIT: (
                    1.0
                    - distance_between_implicit_and_explicit
                    - distance_between_vararg_and_normal
                    - distance_between_position_and_named
                ),
                ParameterAssignment.NAMED_VARARG: 1.0,
                ParameterAssignment.POSITIONAL_VARARG: 1.0 - distance_between_position_and_named,
                ParameterAssignment.POSITION_OR_NAME: (
                    1.0 - distance_between_vararg_and_normal - distance_between_one_to_both
                ),
                ParameterAssignment.NAME_ONLY: 1.0 - distance_between_vararg_and_normal,
                ParameterAssignment.POSITION_ONLY: (
                    1.0 - distance_between_vararg_and_normal - distance_between_position_and_named
                ),
            },
            ParameterAssignment.POSITIONAL_VARARG: {
                ParameterAssignment.IMPLICIT: (
                    1.0 - distance_between_implicit_and_explicit - distance_between_vararg_and_normal
                ),
                ParameterAssignment.NAMED_VARARG: 1.0 - distance_between_position_and_named,
                ParameterAssignment.POSITIONAL_VARARG: 1.0,
                ParameterAssignment.POSITION_OR_NAME: (
                    1.0 - distance_between_vararg_and_normal - distance_between_one_to_both
                ),
                ParameterAssignment.NAME_ONLY: (
                    1.0 - distance_between_vararg_and_normal - distance_between_position_and_named
                ),
                ParameterAssignment.POSITION_ONLY: 1.0 - distance_between_vararg_and_normal,
            },
            ParameterAssignment.POSITION_OR_NAME: {
                ParameterAssignment.IMPLICIT: 1.0 - distance_between_implicit_and_explicit,
                ParameterAssignment.NAMED_VARARG: (
                    1.0 - distance_between_vararg_and_normal - distance_between_both_to_one
                ),
                ParameterAssignment.POSITIONAL_VARARG: (
                    1.0 - distance_between_vararg_and_normal - distance_between_both_to_one
                ),
                ParameterAssignment.POSITION_OR_NAME: 1.0,
                ParameterAssignment.NAME_ONLY: 1.0 - distance_between_both_to_one,
                ParameterAssignment.POSITION_ONLY: 1.0 - distance_between_both_to_one,
            },
            ParameterAssignment.NAME_ONLY: {
                ParameterAssignment.IMPLICIT: 1.0 - distance_between_implicit_and_explicit,
                ParameterAssignment.NAMED_VARARG: 1.0 - distance_between_vararg_and_normal,
                ParameterAssignment.POSITIONAL_VARARG: (
                    1.0 - distance_between_vararg_and_normal - distance_between_position_and_named
                ),
                ParameterAssignment.POSITION_OR_NAME: 1.0 - distance_between_one_to_both,
                ParameterAssignment.NAME_ONLY: 1.0,
                ParameterAssignment.POSITION_ONLY: 1.0 - distance_between_position_and_named,
            },
            ParameterAssignment.POSITION_ONLY: {
                ParameterAssignment.IMPLICIT: 1.0 - distance_between_implicit_and_explicit,
                ParameterAssignment.NAMED_VARARG: (
                    1.0 - distance_between_vararg_and_normal - distance_between_position_and_named
                ),
                ParameterAssignment.POSITIONAL_VARARG: 1.0 - distance_between_vararg_and_normal,
                ParameterAssignment.POSITION_OR_NAME: 1.0 - distance_between_one_to_both,
                ParameterAssignment.NAME_ONLY: 1.0 - distance_between_position_and_named,
                ParameterAssignment.POSITION_ONLY: 1.0,
            },
        }

    def compute_class_similarity(self, classv1: Class, classv2: Class) -> float:
        """
        Compute the similarity between classes from apiv1 and apiv2.

        Similarity is computed with respect to their name, id, code, and attributes.

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
        normalize_similarity = 6

        code_similarity = self._compute_code_similarity(classv1, classv2)
        name_similarity = self._compute_name_similarity(classv1.name, classv2.name)

        attributes_similarity = distance(classv1.instance_attributes, classv2.instance_attributes)
        attributes_similarity = attributes_similarity / (
            max(len(classv1.instance_attributes), len(classv2.instance_attributes), 1)
        )
        attributes_similarity = 1 - attributes_similarity

        function_similarity = distance(
            classv1.methods,
            classv2.methods,
        ) / max(len(classv1.methods), len(classv2.methods), 1)
        function_similarity = 1 - function_similarity

        id_similarity = self._compute_id_similarity(classv1.id, classv2.id)

        documentation_similarity = self._compute_documentation_similarity(classv1.docstring, classv2.docstring)
        if documentation_similarity < 0:
            documentation_similarity = 0
            normalize_similarity -= 1

        return (
            name_similarity
            + attributes_similarity
            + function_similarity
            + code_similarity
            + id_similarity
            + documentation_similarity
        ) / normalize_similarity

    def _compute_name_similarity(self, namev1: str, namev2: str) -> float:
        name_similarity = distance(namev1, namev2) / max(len(namev1), len(namev2), 1)
        return 1 - name_similarity

    def compute_attribute_similarity(
        self,
        attributev1: Attribute,
        attributev2: Attribute,
    ) -> float:
        """
        Compute the similarity between attributes from apiv1 and apiv2.

        Similarity is computed with respect to their name and type.

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
        name_similarity = self._compute_name_similarity(attributev1.name, attributev2.name)
        type_listv1 = self._create_list_from_type(attributev1.types)
        type_listv2 = self._create_list_from_type(attributev2.types)
        type_similarity = distance(type_listv1, type_listv2) / max(len(type_listv1), len(type_listv2), 1)
        type_similarity = 1 - type_similarity
        return (name_similarity + type_similarity) / 2

    def compute_function_similarity(self, functionv1: Function, functionv2: Function) -> float:
        """
        Compute the similarity between functions from apiv1 and apiv2.

        Similarity is computed with respect to their code, name, id, and parameters.

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
        if (
            functionv1.id in self.previous_function_similarity
            and functionv2.id in self.previous_function_similarity[functionv1.id]
        ):
            return self.previous_function_similarity[functionv1.id][functionv2.id]

        normalize_similarity = 5

        code_similarity = self._compute_code_similarity(functionv1, functionv2)
        name_similarity = self._compute_name_similarity(functionv1.name, functionv2.name)

        parameter_similarity = distance(
            functionv1.parameters,
            functionv2.parameters,
        ) / max(len(functionv1.parameters), len(functionv2.parameters), 1)
        parameter_similarity = 1 - parameter_similarity

        id_similarity = self._compute_id_similarity(functionv1.id, functionv2.id)

        documentation_similarity = self._compute_documentation_similarity(
            functionv1.docstring,
            functionv2.docstring,
        )
        if documentation_similarity < 0:
            documentation_similarity = 0
            normalize_similarity -= 1

        result = (
            code_similarity + name_similarity + parameter_similarity + id_similarity + documentation_similarity
        ) / normalize_similarity
        if functionv1.id not in self.previous_function_similarity:
            self.previous_function_similarity[functionv1.id] = {}
        self.previous_function_similarity[functionv1.id][functionv2.id] = result
        return result

    CODE_CONTAINING_API_ELEMENT = TypeVar("CODE_CONTAINING_API_ELEMENT", Class, Function)

    def _compute_code_similarity(
        self,
        elementv1: CODE_CONTAINING_API_ELEMENT,
        elementv2: CODE_CONTAINING_API_ELEMENT,
    ) -> float:
        if elementv1.id in self.formatted_code["apiv1"]:
            splitv1 = self.formatted_code["apiv1"][elementv1.id]
        else:
            codev1 = elementv1.get_formatted_code(cut_documentation=True)
            splitv1 = codev1.split("\n")
            self.formatted_code["apiv1"][elementv1.id] = splitv1

        if elementv2.id in self.formatted_code["apiv2"]:
            splitv2 = self.formatted_code["apiv2"][elementv2.id]
        else:
            codev2 = elementv2.get_formatted_code(cut_documentation=True)
            splitv2 = codev2.split("\n")
            self.formatted_code["apiv2"][elementv2.id] = splitv2
        diff_code = distance(splitv1, splitv2) / max(len(splitv1), len(splitv2), 1)
        return 1 - diff_code

    def compute_parameter_similarity(self, parameterv1: Parameter, parameterv2: Parameter) -> float:
        """
        Compute similarity between parameters from apiv1 and apiv2.

        The similarity is computed with respect to their name, type, assignment, default value, documentation, and id.

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
        if (
            parameterv1.id in self.previous_parameter_similarity
            and parameterv2.id in self.previous_parameter_similarity[parameterv1.id]
        ):
            return self.previous_parameter_similarity[parameterv1.id][parameterv2.id]

        normalize_similarity = 6
        parameter_name_similarity = self._compute_name_similarity(parameterv1.name, parameterv2.name)
        parameter_type_similarity = self._compute_type_similarity(parameterv1.type, parameterv2.type)
        parameter_assignment_similarity = self._compute_assignment_similarity(
            parameterv1.assigned_by,
            parameterv2.assigned_by,
        )
        if parameter_assignment_similarity < 0:
            parameter_assignment_similarity = 0
        parameter_default_value_similarity = self._compute_default_value_similarity(
            parameterv1.default_value,
            parameterv2.default_value,
        )
        if parameter_default_value_similarity < 0:
            parameter_default_value_similarity = 0
            normalize_similarity -= 1
        parameter_documentation_similarity = self._compute_documentation_similarity(
            parameterv1.docstring,
            parameterv2.docstring,
        )
        if parameter_documentation_similarity < 0:
            parameter_documentation_similarity = 0
            normalize_similarity -= 1

        id_similarity = self._compute_id_similarity(parameterv1.id, parameterv2.id)

        result = (
            parameter_name_similarity
            + parameter_type_similarity
            + parameter_assignment_similarity
            + parameter_default_value_similarity
            + parameter_documentation_similarity
            + id_similarity
        ) / normalize_similarity
        if parameterv1.id not in self.previous_parameter_similarity:
            self.previous_parameter_similarity[parameterv1.id] = {}
        self.previous_parameter_similarity[parameterv1.id][parameterv2.id] = result
        return result

    def _compute_type_similarity(self, typev1: AbstractType | None, typev2: AbstractType | None) -> float:
        if typev1 is None:
            if typev2 is None:
                return 1
            return 0
        if typev2 is None:
            return 0

        type_listv1 = self._create_list_from_type(typev1)
        type_listv2 = self._create_list_from_type(typev2)
        diff_elements = distance(type_listv1, type_listv2) / max(len(type_listv1), len(type_listv2), 1)
        return 1 - diff_elements

    def _create_list_from_type(self, abstract_type: AbstractType | None) -> Sequence[AbstractType | None]:
        if abstract_type is not None and isinstance(abstract_type, UnionType):
            return abstract_type.types
        return [abstract_type]

    def _compute_assignment_similarity(
        self,
        assigned_byv1: ParameterAssignment,
        assigned_byv2: ParameterAssignment,
    ) -> float:
        return self.assigned_by_look_up_similarity[assigned_byv1][assigned_byv2]

    def compute_result_similarity(self, resultv1: Result, resultv2: Result) -> float:
        """
        Compute similarity between results from apiv1 and apiv2 with the respect to their name.

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
        return self._compute_name_similarity(resultv1.name, resultv2.name)

    def _compute_default_value_similarity(
        self,
        default_valuev1: str | None,
        default_valuev2: str | None,
    ) -> float:
        if default_valuev1 is None and default_valuev2 is None:
            return -1.0
        if default_valuev1 is None or default_valuev2 is None:
            return 0.0
        if default_valuev1 == "None" and default_valuev2 == "None":
            return 1.0
        try:
            intv1_value = int(default_valuev1)
            intv2_value = int(default_valuev2)
        except ValueError:
            try:
                floatv1_value = float(default_valuev1)
                floatv2_value = float(default_valuev2)
            except ValueError:
                try:
                    if float(int(default_valuev1)) == float(default_valuev2):
                        return 0.75
                except ValueError:
                    try:
                        if float(int(default_valuev2)) == float(default_valuev1):
                            return 0.75
                    except ValueError:
                        pass
            else:
                if floatv1_value == floatv2_value:
                    return 1.0
        else:
            if intv1_value == intv2_value:
                return 1.0
            return 0.5

        if default_valuev1 in (
            "True",
            "False",
        ) and default_valuev2 in ("True", "False"):
            if bool(default_valuev1) == bool(default_valuev2):
                return 1.0
            return 0.5
        valuev1_is_in_quotation_marks = (default_valuev1.startswith("'") and default_valuev1.endswith("'")) or (
            default_valuev1.startswith('"') and default_valuev1.endswith('"')
        )
        valuev2_is_in_quotation_marks = (default_valuev2.startswith("'") and default_valuev2.endswith("'")) or (
            default_valuev2.startswith('"') and default_valuev2.endswith('"')
        )
        if valuev1_is_in_quotation_marks and valuev2_is_in_quotation_marks:
            if default_valuev1[1:-1] == default_valuev2[1:-1]:
                return 1.0
            return 0.5
        return 0.0

    def _compute_documentation_similarity(
        self,
        documentationv1: ClassDocstring | FunctionDocstring | ParameterDocstring,
        documentationv2: ClassDocstring | FunctionDocstring | ParameterDocstring,
    ) -> float:
        if len(documentationv1.description) == len(documentationv2.description) == 0:
            return -1.0
        descriptionv1 = re.split("[\n ]", documentationv1.description)
        descriptionv2 = re.split("[\n ]", documentationv2.description)

        documentation_similarity = distance(descriptionv1, descriptionv2) / max(
            len(descriptionv1),
            len(descriptionv2),
            1,
        )
        return 1 - documentation_similarity

    def _compute_id_similarity(self, idv1: str, idv2: str) -> float:
        module_pathv1 = idv1.split("/")[1].split(".")
        additional_module_pathv1 = idv1.split("/")[2:-1]
        if len(additional_module_pathv1) > 0:
            module_pathv1.extend(additional_module_pathv1)
        module_pathv2 = idv2.split("/")[1].split(".")
        additional_module_pathv2 = idv2.split("/")[2:-1]
        if len(additional_module_pathv2) > 0:
            module_pathv2.extend(additional_module_pathv2)

        def cost_function(iteration: int, max_iteration: int) -> float:
            return (max_iteration - iteration + 1) / max_iteration

        total_costs, max_iterations = self.distance_elements_with_cost_function(
            module_pathv1,
            module_pathv2,
            cost_function,
        )
        return 1 - (total_costs / (sum(range(1, max_iterations + 1)) / max_iterations))

    def distance_elements_with_cost_function(
        self,
        listv1: list[str],
        listv2: list[str],
        cost_function: Callable[[int, int], float],
    ) -> tuple[float, int]:
        m = len(listv1)
        n = len(listv2)
        if m == n and listv1 == listv2:
            return 0, m
        if m > n:
            listv1, listv2 = listv2, listv1
            m, n = n, m
        table = [[0] * (n + 1) for _ in range(m + 1)]
        str_table = [[""] * (n + 1) for _ in range(m + 1)]

        for i in range(m + 1):
            table[i][0] = i
            str_table[i][0] = "-" * i
        for j in range(n + 1):
            table[0][j] = j
            str_table[0][j] = "+" * j

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if listv1[i - 1] == listv2[j - 1]:
                    table[i][j] = table[i - 1][j - 1]
                    str_table[i][j] = str_table[i - 1][j - 1] + "="
                else:
                    table[i][j] = 1 + min(table[i - 1][j], table[i][j - 1], table[i - 1][j - 1])
                    list_ = [table[i - 1][j], table[i][j - 1], table[i - 1][j - 1]]
                    min_ = [i for i, j in enumerate(list_) if j == min(list_)][0]
                    if min_ == 0:
                        str_table[i][j] = str_table[i - 1][j] + "+"
                    if min_ == 1:
                        str_table[i][j] = str_table[i][j - 1] + "-"
                    if min_ == 2:
                        str_table[i][j] = str_table[i - 1][j - 1] + "o"
        edit_string = str_table[-1][-1]
        total_costs = 0.0
        max_iteration = len(edit_string)
        for index, char_ in enumerate(list(edit_string)):
            if char_ != "=":
                total_costs += cost_function(index + 1, max_iteration)
        return total_costs, max_iteration

    def is_base_differ(self) -> bool:
        return True
