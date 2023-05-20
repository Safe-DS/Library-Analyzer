from library_analyzer.processing.annotations.model import (
    AnnotationStore,
    EnumReviewResult,
    RemoveAnnotation,
)
from library_analyzer.processing.api.model import API
from library_analyzer.processing.usages.model import UsageCountStore

from ._constants import autogen_author


def _generate_remove_annotations(api: API, usages: UsageCountStore, annotations: AnnotationStore) -> None:
    """
    Collect all functions and classes that are never used.

    Parameters
    ----------
    api: API
        Description of the API
    usages: UsageCountStore
        UsageStore object
    annotations: AnnotationStore
        AnnotationStore, that holds all annotations.
    """
    for class_ in api.classes.values():
        n_class_usages = usages.n_class_usages(class_.id)
        if n_class_usages == 0:
            annotations.removeAnnotations.append(
                RemoveAnnotation(
                    target=class_.id,
                    authors=[autogen_author],
                    reviewers=[],
                    comment=_create_explanation("class", n_class_usages),
                    reviewResult=EnumReviewResult.NONE,
                ),
            )

    for function in api.functions.values():
        n_function_usages = usages.n_function_usages(function.id)
        if n_function_usages == 0:
            annotations.removeAnnotations.append(
                RemoveAnnotation(
                    target=function.id,
                    authors=[autogen_author],
                    reviewers=[],
                    comment=_create_explanation("function", n_function_usages),
                    reviewResult=EnumReviewResult.NONE,
                ),
            )


def _create_explanation(declaration_type: str, n_usages: int) -> str:
    result = f"I removed this {declaration_type} because it has"

    if n_usages == 0:
        result += " no known usages."
    elif n_usages == 1:
        result += " only one known usage."
    else:
        result += f" only {n_usages} known usages."

    return result
