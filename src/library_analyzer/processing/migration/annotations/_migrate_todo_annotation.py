from copy import deepcopy

from library_analyzer.processing.annotations.model import (
    AbstractAnnotation,
    EnumReviewResult,
    TodoAnnotation,
)
from library_analyzer.processing.api.model import Attribute, Result
from library_analyzer.processing.migration.model import (
    ManyToOneMapping,
    Mapping,
    OneToOneMapping,
)

from ._constants import migration_author
from ._get_annotated_api_element import get_annotated_api_element
from ._get_migration_text import get_migration_text


# pylint: disable=duplicate-code
def migrate_todo_annotation(
    todo_annotation_: TodoAnnotation, mapping: Mapping
) -> list[AbstractAnnotation]:

    annotated_apiv1_element = get_annotated_api_element(
        todo_annotation_, mapping.get_apiv1_elements()
    )
    if annotated_apiv1_element is None:
        return []

    todo_annotations: list[AbstractAnnotation] = []
    for element in mapping.get_apiv2_elements():
        todo_annotation = deepcopy(todo_annotation_)
        authors = todo_annotation.authors
        authors.append(migration_author)
        todo_annotation.authors = authors
        if isinstance(element, type(annotated_apiv1_element)) and not isinstance(
            element, (Attribute, Result)
        ):
            todo_annotations.append(
                TodoAnnotation(
                    element.id,
                    authors,
                    todo_annotation.reviewers,
                    todo_annotation.comment,
                    EnumReviewResult.NONE,
                    todo_annotation.newTodo,
                )
            )
        elif not isinstance(element, (Attribute, Result)):
            todo_annotations.append(
                TodoAnnotation(
                    element.id,
                    authors,
                    todo_annotation.reviewers,
                    todo_annotation.comment,
                    EnumReviewResult.UNSURE,
                    get_migration_text(
                        todo_annotation, mapping, for_todo_annotation=True
                    ),
                )
            )
    return todo_annotations
