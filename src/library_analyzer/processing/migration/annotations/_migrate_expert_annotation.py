from copy import deepcopy

from library_analyzer.processing.annotations.model import (
    AbstractAnnotation,
    EnumReviewResult,
    ExpertAnnotation,
    TodoAnnotation,
)
from library_analyzer.processing.api.model import Attribute, Result
from library_analyzer.processing.migration.model import (
    Mapping,
)

from ._constants import migration_author
from ._get_annotated_api_element import get_annotated_api_element
from ._get_migration_text import get_migration_text


def migrate_expert_annotation(origin_annotation: ExpertAnnotation, mapping: Mapping) -> list[AbstractAnnotation]:
    expert_annotation = deepcopy(origin_annotation)
    authors = expert_annotation.authors
    authors.append(migration_author)
    expert_annotation.authors = authors

    annotated_apiv1_element = get_annotated_api_element(expert_annotation, mapping.get_apiv1_elements())
    if annotated_apiv1_element is None:
        return []

    expert_annotations: list[AbstractAnnotation] = []
    for element in mapping.get_apiv2_elements():
        if isinstance(element, type(annotated_apiv1_element)) and not isinstance(element, Attribute | Result):
            expert_annotations.append(
                ExpertAnnotation(
                    element.id,
                    authors,
                    expert_annotation.reviewers,
                    expert_annotation.comment,
                    EnumReviewResult.NONE,
                ),
            )
        elif not isinstance(element, Attribute | Result):
            expert_annotations.append(
                TodoAnnotation(
                    element.id,
                    authors,
                    expert_annotation.reviewers,
                    expert_annotation.comment,
                    EnumReviewResult.NONE,
                    get_migration_text(expert_annotation, mapping, for_todo_annotation=True),
                ),
            )
    return expert_annotations
