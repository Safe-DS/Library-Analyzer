#
# from library_analyzer.processing.api.model import (
#     API,
#     Attribute,
#     Class,
#     Function,
#     Parameter,
#     Result,
# from library_analyzer.processing.migration.model import (
#     AbstractDiffer,
#     Mapping,
#     OneToOneMapping,
#     merge_mappings,
#
#
#
# class APIMapping:
#
#     def __init__(
#         self,
#         apiv1: API,
#         apiv2: API,
#         differ: AbstractDiffer,
#     ) -> None:
#
#     def _get_mappings_for_api_elements(
#         self,
#         api_elementv1_list: list[API_ELEMENTS],
#         api_elementv2_list: list[API_ELEMENTS],
#         compute_similarity: Callable[[API_ELEMENTS, API_ELEMENTS], float],
#     ) -> list[Mapping]:
#         for api_elementv1 in api_elementv1_list:
#             for api_elementv2 in api_elementv2_list:
#                 if similarity >= self.threshold_of_similarity_for_creation_of_mappings:
#             if new_mapping is not None:
#
#     def map_api(self) -> list[Mapping]:
#         if related_mappings is not None:
#             for mapping in related_mappings:
#                 if isinstance(mapping.get_apiv1_elements()[0], Attribute) and isinstance(
#                 ):
#                         self.differ.compute_attribute_similarity,
#                 elif isinstance(mapping.get_apiv1_elements()[0], Class) and isinstance(
#                 ):
#                         self.differ.compute_class_similarity,
#                 elif isinstance(mapping.get_apiv1_elements()[0], Function) and isinstance(
#                 ):
#                         self.differ.compute_function_similarity,
#                 elif isinstance(mapping.get_apiv1_elements()[0], Parameter) and isinstance(
#                 ):
#                         self.differ.compute_parameter_similarity,
#                 elif isinstance(mapping.get_apiv1_elements()[0], Result) and isinstance(
#                 ):
#                         self.differ.compute_result_similarity,
#                 if new_mapping is not None and len(new_mapping) > 0:
#             mappings.extend(
#                 self._get_mappings_for_api_elements(
#                     self.differ.compute_class_similarity,
#                 ),
#             mappings.extend(
#                 self._get_mappings_for_api_elements(
#                     self.differ.compute_function_similarity,
#                 ),
#             mappings.extend(
#                 self._get_mappings_for_api_elements(
#                     self.differ.compute_parameter_similarity,
#                 ),
#
#             mappings.extend(
#                 self._get_mappings_for_api_elements(
#                     self.differ.compute_attribute_similarity,
#                 ),
#
#             mappings.extend(
#                 self._get_mappings_for_api_elements(
#                     self.differ.compute_result_similarity,
#                 ),
#
#     def _merge_similar_mappings(self, mappings: list[Mapping]) -> Mapping | None:
#         """
#         Given a list of OneToOne(Many)Mappings which apiv1 element is the same, this method returns the best mapping
#         from this apiv1 element to apiv2 elements by merging the first and second elements recursively,
#         if the difference in similarity is smaller than THRESHOLD_OF_SIMILARITY_BETWEEN_MAPPINGS.
#
#         :param mappings: mappings sorted by decreasing similarity, which apiv1 element is the same
#         :return: the first element of the sorted list that could be a result of merged similar mappings
#         """
#         if len(mappings) == 0:
#         if len(mappings) == 1:
#         while (len(mappings) > 1) and (
#         ):
#
#     def _merge_mappings_with_same_elements(self, mapping_to_be_appended: Mapping, mappings: list[Mapping]) -> None:
#         """
#         Prevent that an element in a mapping appears multiple times in a list of mappings.
#
#         Affected mappings are merged and the results included in the list. If there is no such element, the mapping will
#         be included without any merge.
#
#         Parameters
#         ----------
#             the mapping that should be included in mappings
#             the list, in which mapping_to_be_appended should be appended
#         """
#         for mapping in mappings:
#             for element in mapping.get_apiv2_elements():
#                 for element_2 in mapping_to_be_appended.get_apiv2_elements():
#                     if element == element_2:
#             if duplicated_element:
#
#         if len(duplicated) == 0:
#
#         for conflicted_mapping in duplicated:
#
