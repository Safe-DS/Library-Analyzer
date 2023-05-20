from copy import deepcopy

from library_analyzer.processing.annotations.model import (
    AbstractAnnotation,
    EnumReviewResult,
    MoveAnnotation,
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


def is_moveable(element: Attribute | Class | Function | Parameter | Result) -> bool:
    if isinstance(element, Attribute | Result):
        return False
    if isinstance(element, Function):
        # check for global function
        element_parents = element.id.split("/")
        return len(element_parents) == 3
    return isinstance(element, Class)


def _was_moved(
    elementv1: Attribute | Class | Function | Parameter | Result | None,
    elementv2: Attribute | Class | Function | Parameter | Result | None,
    move_annotation: MoveAnnotation,
) -> bool:
    if (
        not isinstance(elementv1, Class | Function)
        or elementv1 is None
        or not isinstance(elementv2, Class | Function)
        or elementv2 is None
    ):
        return True
    return (
        elementv1.id.split("/")[1] != elementv2.id.split("/")[1]
        and move_annotation.destination != elementv2.id.split("/")[1]
    )


def migrate_move_annotation(move_annotation_: MoveAnnotation, mapping: Mapping) -> list[AbstractAnnotation]:
    annotated_apiv1_element = get_annotated_api_element(
        move_annotation_, mapping.get_apiv1_elements()
    )
    if annotated_apiv1_element is None:
        return []

    migrated_annotations: list[AbstractAnnotation] = []
    for element in mapping.get_apiv2_elements():
        move_annotation = deepcopy(move_annotation_)
        authors = move_annotation.authors
        authors.append(migration_author)
        move_annotation.authors = authors
        if (
            isinstance(element, type(annotated_apiv1_element))
            and is_moveable(element)
            and not isinstance(element, Attribute | Result)
        ):
            review_result = (
                EnumReviewResult.UNSURE
                if _was_moved(
                    get_annotated_api_element(move_annotation, mapping.get_apiv1_elements()),
                    element,
                    move_annotation,
                )
                else EnumReviewResult.NONE
            )
            move_annotation.target = element.id
            move_annotation.reviewResult = review_result
            migrated_annotations.append(move_annotation)
        elif not isinstance(element, Attribute | Result):
            migrated_annotations.append(
                TodoAnnotation(
                    element.id,
                    authors,
                    move_annotation.reviewers,
                    move_annotation.comment,
                    EnumReviewResult.NONE,
                    get_migration_text(move_annotation, mapping, for_todo_annotation=True),
                ),
            )
    return migrated_annotations
