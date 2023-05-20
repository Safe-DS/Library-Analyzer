from copy import deepcopy

from library_analyzer.processing.annotations.model import (
    AbstractAnnotation,
    EnumReviewResult,
    RenameAnnotation,
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


def migrate_rename_annotation(rename_annotation_: RenameAnnotation, mapping: Mapping) -> list[AbstractAnnotation]:
    annotated_apiv1_element = get_annotated_api_element(
        rename_annotation_, mapping.get_apiv1_elements()
    )
    if annotated_apiv1_element is None:
        return []

    annotations: list[AbstractAnnotation] = []
    for element in mapping.get_apiv2_elements():
        rename_annotation = deepcopy(rename_annotation_)
        authors = rename_annotation.authors
        authors.append(migration_author)
        rename_annotation.authors = authors
        if isinstance(element, type(annotated_apiv1_element)) and not isinstance(element, Attribute | Result):
            if element.name not in (
                rename_annotation_.newName,
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
