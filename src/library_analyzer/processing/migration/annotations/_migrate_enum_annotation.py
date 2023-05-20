from copy import deepcopy

from library_analyzer.processing.annotations.model import (
    AbstractAnnotation,
    EnumAnnotation,
    EnumPair,
    EnumReviewResult,
    TodoAnnotation,
)
from library_analyzer.processing.api.model import (
    AbstractType,
    Attribute,
    NamedType,
    Parameter,
    Result,
    UnionType,
)
from library_analyzer.processing.migration.model import Mapping

from ._constants import migration_author
from ._get_annotated_api_element import get_annotated_api_element
from ._get_migration_text import get_migration_text


def _contains_string(type_: AbstractType) -> bool:
    if isinstance(type_, NamedType):
        return type_.name == "str"
    if isinstance(type_, UnionType):
        for element in type_.types:
            if _contains_string(element):
                return True
    return False


def _default_value_is_in_instance_values_or_is_empty(default_value: str | None, pairs: list[EnumPair]) -> bool:
    return default_value is None or default_value in (pair.stringValue for pair in pairs) or len(default_value) == 0


def migrate_enum_annotation(origin_annotation: EnumAnnotation, mapping: Mapping) -> list[AbstractAnnotation]:
    annotated_apiv1_element = get_annotated_api_element(
        origin_annotation, mapping.get_apiv1_elements())
    if annotated_apiv1_element is None or not isinstance(annotated_apiv1_element, Parameter):
        return []

    migrated_annotations: list[AbstractAnnotation] = []
    for parameter in mapping.get_apiv2_elements():
        enum_annotation = deepcopy(origin_annotation)
        authors = enum_annotation.authors
        authors.append(migration_author)
        enum_annotation.authors = authors
        if isinstance(parameter, Attribute | Result):
            return []
        if isinstance(parameter, Parameter):
            if (
                parameter.type is not None
                and _contains_string(parameter.type)
                and _default_value_is_in_instance_values_or_is_empty(parameter.default_value, enum_annotation.pairs)
            ) or (parameter.type is None and annotated_apiv1_element.type is None):
                enum_annotation.target = parameter.id
                migrated_annotations.append(enum_annotation)
                continue
            if isinstance(parameter.type, NamedType) and not _contains_string(parameter.type) and not (isinstance(annotated_apiv1_element.type, NamedType) and parameter.type.name == annotated_apiv1_element):
                # assuming api has been chanced to an enum type:
                # do not migrate annotation
                continue
            enum_annotation.reviewResult = EnumReviewResult.UNSURE
            enum_annotation.comment = get_migration_text(enum_annotation, mapping)
            enum_annotation.target = parameter.id
            migrated_annotations.append(enum_annotation)
            continue
        migrated_annotations.append(
            TodoAnnotation(
                parameter.id,
                authors,
                enum_annotation.reviewers,
                enum_annotation.comment,
                EnumReviewResult.NONE,
                get_migration_text(enum_annotation, mapping, for_todo_annotation=True),
            )
        )
    return migrated_annotations
