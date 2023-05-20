from copy import deepcopy

from library_analyzer.processing.annotations.model import (
    AbstractAnnotation,
    EnumReviewResult,
    RemoveAnnotation,
    TodoAnnotation,
)
from library_analyzer.processing.api.model import (
    Attribute,
    Class,
    Function,
    Parameter,
    Result,
)
from library_analyzer.processing.migration.model import (
    ManyToOneMapping,
    Mapping,
    OneToOneMapping,
)

from ._constants import migration_author
from ._get_annotated_api_element import get_annotated_api_element
from ._get_migration_text import get_migration_text


def is_removeable(element: Attribute | Class | Function | Parameter | Result) -> bool:
    return isinstance(element, Class | Function)


def migrate_remove_annotation(
    origin_annotation: RemoveAnnotation, mapping: Mapping
) -> list[AbstractAnnotation]:
    annotated_apiv1_element = get_annotated_api_element(
        origin_annotation, mapping.get_apiv1_elements()
    )
    if annotated_apiv1_element is None:
        return []

    remove_annotations: list[AbstractAnnotation] = []
    for element in mapping.get_apiv2_elements():
        remove_annotation = deepcopy(origin_annotation)
        authors = remove_annotation.authors
        authors.append(migration_author)
        remove_annotation.authors = authors
        if (
            isinstance(element, type(annotated_apiv1_element))
            and is_removeable(element)
            and not isinstance(element, Attribute | Result)
        ):
            remove_annotations.append(
                RemoveAnnotation(
                    element.id,
                    authors,
                    remove_annotation.reviewers,
                    remove_annotation.comment,
                    EnumReviewResult.NONE,
                ),
            )
        elif not isinstance(element, Attribute | Result):
            remove_annotations.append(
                TodoAnnotation(
                    element.id,
                    authors,
                    remove_annotation.reviewers,
                    remove_annotation.comment,
                    EnumReviewResult.NONE,
                    get_migration_text(remove_annotation, mapping, for_todo_annotation=True),
                ),
            )
    return remove_annotations
