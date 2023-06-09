from copy import deepcopy

from library_analyzer.processing.annotations.model import (
    AbstractAnnotation,
    EnumReviewResult,
    GroupAnnotation,
    TodoAnnotation,
)
from library_analyzer.processing.api.model import Attribute, Function, Parameter, Result
from library_analyzer.processing.migration.model import Mapping

from ._constants import migration_author
from ._get_migration_text import get_migration_text


def migrate_group_annotation(
    origin_annotation: GroupAnnotation,
    mapping: Mapping,
    mappings: list[Mapping],
) -> list[AbstractAnnotation]:
    migrated_annotations: list[AbstractAnnotation] = []

    for functionv2 in mapping.get_apiv2_elements():
        group_annotation = deepcopy(origin_annotation)
        authors = group_annotation.authors
        authors.append(migration_author)
        group_annotation.authors = authors
        if isinstance(functionv2, Attribute | Result):
            continue
        if not isinstance(functionv2, Function):
            migrated_annotations.append(
                TodoAnnotation(
                    target=functionv2.id,
                    authors=authors,
                    reviewers=group_annotation.reviewers,
                    comment=group_annotation.comment,
                    reviewResult=EnumReviewResult.NONE,
                    newTodo=get_migration_text(group_annotation, mapping, for_todo_annotation=True),
                ),
            )
        else:
            parameter_replacements = _get_mappings_for_grouped_parameters(group_annotation, mappings, functionv2)
            grouped_parameters: list[Parameter] = []
            name_modifier = ""

            for parameter_list in parameter_replacements:
                if len(parameter_list) == 0:
                    name_modifier = "0" + name_modifier
                else:
                    grouped_parameters.extend(parameter_list)
                    if len(parameter_list) == 1:
                        name_modifier = "1" + name_modifier
                    else:
                        name_modifier = "0" + name_modifier

            remove_duplicates_and_preserve_order = [
                i for n, i in enumerate(grouped_parameters) if i not in grouped_parameters[:n]
            ]
            grouped_parameters = remove_duplicates_and_preserve_order

            if len(grouped_parameters) < 2 <= len(group_annotation.parameters):
                migrated_annotations.append(
                    TodoAnnotation(
                        target=functionv2.id,
                        authors=authors,
                        reviewers=group_annotation.reviewers,
                        comment=group_annotation.comment,
                        reviewResult=EnumReviewResult.NONE,
                        newTodo=get_migration_text(
                            group_annotation,
                            mapping,
                            for_todo_annotation=True,
                            additional_information=grouped_parameters,
                        ),
                    ),
                )
                continue

            if len(grouped_parameters) != len(group_annotation.parameters):
                group_name = group_annotation.groupName + str(int(name_modifier, base=2))
                migrated_annotations.append(
                    GroupAnnotation(
                        target=functionv2.id,
                        authors=authors,
                        reviewers=group_annotation.reviewers,
                        comment=get_migration_text(
                            group_annotation,
                            mapping,
                            additional_information=grouped_parameters,
                        ),
                        reviewResult=EnumReviewResult.UNSURE,
                        groupName=group_name,
                        parameters=[parameter.name for parameter in grouped_parameters],
                    ),
                )
            else:
                group_annotation.target = functionv2.id
                group_annotation.parameters = [parameter.name for parameter in grouped_parameters]
                migrated_annotations.append(group_annotation)

    return migrated_annotations


def _get_mappings_for_grouped_parameters(
    group_annotation: GroupAnnotation,
    mappings: list[Mapping],
    functionv2: Function,
) -> list[list[Parameter]]:
    parameter_ids = [group_annotation.target + "/" + parameter_name for parameter_name in group_annotation.parameters]

    matched_parameters: list[list[Parameter]] = []
    for parameter_id in parameter_ids:
        for mapping in mappings:
            for parameterv1 in mapping.get_apiv1_elements():
                if isinstance(parameterv1, Parameter) and parameterv1.id == parameter_id:
                    mapped_parameters: list[Parameter] = []
                    for parameterv2 in mapping.get_apiv2_elements():
                        if isinstance(parameterv2, Parameter) and parameterv2.id.startswith(functionv2.id + "/"):
                            mapped_parameters.append(parameterv2)
                    matched_parameters.append(mapped_parameters)
                    break
    return matched_parameters
