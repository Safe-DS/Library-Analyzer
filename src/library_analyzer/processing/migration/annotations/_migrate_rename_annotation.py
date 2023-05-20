from copy import deepcopy

from library_analyzer.processing.annotations.model import (
    AbstractAnnotation,
    EnumReviewResult,
    RenameAnnotation,
    TodoAnnotation,
)
from library_analyzer.processing.api.model import Attribute, Result
from library_analyzer.processing.migration.model import (
    Mapping,
)

from ._constants import migration_author
from ._get_annotated_api_element import get_annotated_api_element
from ._get_migration_text import get_migration_text


def migrate_rename_annotation(origin_annotation: RenameAnnotation, mapping: Mapping) -> list[AbstractAnnotation]:
    annotated_apiv1_element = get_annotated_api_element(origin_annotation, mapping.get_apiv1_elements())
    if annotated_apiv1_element is None:
        return []

    annotations: list[AbstractAnnotation] = []
    for element in mapping.get_apiv2_elements():
        rename_annotation = deepcopy(origin_annotation)
        authors = rename_annotation.authors
        authors.append(migration_author)
        rename_annotation.authors = authors
        if isinstance(element, type(annotated_apiv1_element)) and not isinstance(element, Attribute | Result):
            if element.name not in (
                origin_annotation.newName,
                rename_annotation.target.split("/")[-1],
            ):
                rename_annotation.comment = get_migration_text(rename_annotation, mapping)
                rename_annotation.reviewResult = EnumReviewResult.UNSURE
                rename_annotation.target = element.id
                annotations.append(rename_annotation)
            else:
                rename_annotation.target = element.id
                annotations.append(rename_annotation)
        elif not isinstance(element, Attribute | Result):
            annotations.append(
                TodoAnnotation(
                    element.id,
                    authors,
                    rename_annotation.reviewers,
                    rename_annotation.comment,
                    EnumReviewResult.NONE,
                    get_migration_text(rename_annotation, mapping, for_todo_annotation=True),
                ),
            )
    return annotations
