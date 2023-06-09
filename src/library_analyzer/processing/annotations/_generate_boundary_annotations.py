from library_analyzer.processing.annotations.model import (
    AnnotationStore,
    BoundaryAnnotation,
    EnumReviewResult,
    Interval,
    ValueAnnotation,
)
from library_analyzer.processing.api.model import API, BoundaryType, UnionType

from ._constants import autogen_author


def _generate_boundary_annotations(api: API, annotations: AnnotationStore) -> None:
    """
    Annotates all parameters which are a boundary.

    Parameters
    ----------
    api: API
        Description of the API
    annotations: AnnotationStore
        AnnotationStore, that holds all annotations.
    """
    for _, parameter in api.parameters().items():
        # Don't add boundary annotation to constant parameters
        if parameter.id in {
            annotation.target
            for annotation in annotations.valueAnnotations
            if annotation.variant == ValueAnnotation.Variant.CONSTANT
        }:
            continue

        parameter_type = parameter.type
        if parameter_type is None:
            continue

        boundary_type: BoundaryType | None = None

        if isinstance(parameter_type, UnionType):
            for type_in_union in parameter_type.types:
                if isinstance(type_in_union, BoundaryType):
                    boundary_type = type_in_union

        if isinstance(parameter_type, BoundaryType):
            boundary_type = parameter_type

        if boundary_type is not None:
            min_value = boundary_type.min
            max_value = boundary_type.max

            is_discrete = boundary_type.base_type == "int"

            min_limit_type = 0
            max_limit_type = 0
            if not boundary_type.min_inclusive:
                min_limit_type = 1
            if not boundary_type.max_inclusive:
                max_limit_type = 1
            if min_value == "NegativeInfinity":
                min_value = 0
                min_limit_type = 2
            if max_value == "Infinity":
                max_value = 0
                max_limit_type = 2

            interval = Interval(
                lowerIntervalLimit=min_value,
                upperIntervalLimit=max_value,
                lowerLimitType=min_limit_type,
                upperLimitType=max_limit_type,
                isDiscrete=is_discrete,
            )
            boundary = BoundaryAnnotation(
                target=parameter.id,
                authors=[autogen_author],
                reviewers=[],
                comment=f"I turned this into a bounded number because the description contained {boundary_type.full_match}.",
                interval=interval,
                reviewResult=EnumReviewResult.NONE,
            )
            annotations.boundaryAnnotations.append(boundary)
