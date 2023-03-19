from copy import deepcopy
from typing import Optional, Tuple

from library_analyzer.processing.annotations.model import (
    AbstractAnnotation,
    BoundaryAnnotation,
    EnumReviewResult,
    Interval,
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
from library_analyzer.processing.migration.model import (
    ManyToManyMapping,
    ManyToOneMapping,
    Mapping,
    OneToManyMapping,
    OneToOneMapping,
)

from ._constants import migration_author
from ._get_annotated_api_element import get_annotated_api_element
from ._get_migration_text import get_migration_text


def migrate_interval_to_fit_parameter_type(
    intervalv1: Interval, is_discrete: bool
) -> Interval:
    intervalv2 = deepcopy(intervalv1)
    if intervalv2.isDiscrete == is_discrete:
        return intervalv2
    if is_discrete:
        intervalv2.isDiscrete = True
        if intervalv1.upperLimitType in (0, 1):
            intervalv2.upperIntervalLimit = int(intervalv1.upperIntervalLimit)
            intervalv2.upperLimitType = 1
            if intervalv2.upperIntervalLimit == intervalv1.upperIntervalLimit:
                intervalv2.upperLimitType = intervalv1.upperLimitType
        if intervalv1.lowerLimitType in (0, 1):
            intervalv2.lowerIntervalLimit = int(intervalv1.lowerIntervalLimit)
            intervalv2.lowerLimitType = 1
            if intervalv2.lowerIntervalLimit == intervalv1.lowerIntervalLimit:
                intervalv2.lowerLimitType = intervalv1.lowerLimitType
            else:
                intervalv2.lowerIntervalLimit += 1
    else:
        intervalv2.isDiscrete = False
        if intervalv1.upperLimitType in (0, 1):
            intervalv2.upperIntervalLimit = float(intervalv1.upperIntervalLimit)
        if intervalv1.lowerLimitType in (0, 1):
            intervalv2.lowerIntervalLimit = float(intervalv1.lowerIntervalLimit)
    return intervalv2


def _contains_number_and_is_discrete(
    type_: Optional[AbstractType],
) -> Tuple[bool, bool]:
    if type_ is None:
        return False, False
    if isinstance(type_, NamedType):
        return type_.name in ("int", "float"), type_.name == "int"
    if isinstance(type_, UnionType):
        for element in type_.types:
            is_number, is_discrete = _contains_number_and_is_discrete(element)
            if is_number:
                return is_number, is_discrete
    return False, False


# pylint: disable=duplicate-code
def migrate_boundary_annotation(
    boundary_annotation: BoundaryAnnotation, mapping: Mapping
) -> list[AbstractAnnotation]:
    boundary_annotation = deepcopy(boundary_annotation)
    authors = boundary_annotation.authors
    authors.append(migration_author)
    boundary_annotation.authors = authors

    annotated_apiv1_element = get_annotated_api_element(
        boundary_annotation, mapping.get_apiv1_elements()
    )
    if annotated_apiv1_element is None or not isinstance(
        annotated_apiv1_element, Parameter
    ):
        return []

    if isinstance(mapping, (OneToOneMapping, ManyToOneMapping)):
        parameter = mapping.get_apiv2_elements()[0]
        if isinstance(parameter, (Attribute, Result)):
            return []
        if isinstance(parameter, Parameter):
            (
                parameter_expects_number,
                parameter_type_is_discrete,
            ) = _contains_number_and_is_discrete(parameter.type)
            if parameter.type is None and annotated_apiv1_element.type is not None:
                boundary_annotation.reviewResult = EnumReviewResult.UNSURE
                boundary_annotation.comment = get_migration_text(
                    boundary_annotation, mapping
                )
                boundary_annotation.target = parameter.id
                return [boundary_annotation]
            if parameter_expects_number or (
                parameter.type is None and annotated_apiv1_element.type is None
            ):
                if (
                    parameter_type_is_discrete
                    != boundary_annotation.interval.isDiscrete
                ) and not (
                    parameter.type is None and annotated_apiv1_element.type is None
                ):
                    boundary_annotation.reviewResult = EnumReviewResult.UNSURE
                    boundary_annotation.comment = get_migration_text(
                        boundary_annotation, mapping
                    )
                    if parameter_expects_number:
                        boundary_annotation.interval = (
                            migrate_interval_to_fit_parameter_type(
                                boundary_annotation.interval, parameter_type_is_discrete
                            )
                        )
                boundary_annotation.target = parameter.id
                return [boundary_annotation]
        return [
            TodoAnnotation(
                parameter.id,
                authors,
                boundary_annotation.reviewers,
                boundary_annotation.comment,
                EnumReviewResult.NONE,
                get_migration_text(
                    boundary_annotation, mapping, for_todo_annotation=True
                ),
            )
        ]
    migrated_annotations: list[AbstractAnnotation] = []
    if isinstance(mapping, (OneToManyMapping, ManyToManyMapping)):
        for parameter in mapping.get_apiv2_elements():
            if isinstance(parameter, Parameter):
                is_number, is_discrete = _contains_number_and_is_discrete(
                    parameter.type
                )
                if (
                    parameter.type is not None
                    and is_number
                    and is_discrete == boundary_annotation.interval.isDiscrete
                ) or (parameter.type is None and annotated_apiv1_element.type is None):
                    migrated_annotations.append(
                        BoundaryAnnotation(
                            parameter.id,
                            authors,
                            boundary_annotation.reviewers,
                            boundary_annotation.comment,
                            EnumReviewResult.NONE,
                            boundary_annotation.interval,
                        )
                    )
                elif parameter.type is not None and is_number:
                    migrated_annotations.append(
                        BoundaryAnnotation(
                            parameter.id,
                            authors,
                            boundary_annotation.reviewers,
                            get_migration_text(boundary_annotation, mapping),
                            EnumReviewResult.UNSURE,
                            migrate_interval_to_fit_parameter_type(
                                boundary_annotation.interval,
                                is_discrete,
                            ),
                        )
                    )
                elif parameter.type is None:
                    migrated_annotations.append(
                        BoundaryAnnotation(
                            parameter.id,
                            authors,
                            boundary_annotation.reviewers,
                            get_migration_text(boundary_annotation, mapping),
                            EnumReviewResult.UNSURE,
                            boundary_annotation.interval,
                        )
                    )
                continue
            if not isinstance(parameter, (Attribute, Result)):
                migrated_annotations.append(
                    TodoAnnotation(
                        parameter.id,
                        authors,
                        boundary_annotation.reviewers,
                        boundary_annotation.comment,
                        EnumReviewResult.NONE,
                        get_migration_text(
                            boundary_annotation, mapping, for_todo_annotation=True
                        ),
                    )
                )
    return migrated_annotations