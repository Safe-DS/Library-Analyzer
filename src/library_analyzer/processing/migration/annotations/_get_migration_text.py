from collections.abc import Sequence
from typing import Any

from library_analyzer.processing.annotations.model import (
    AbstractAnnotation,
    BoundaryAnnotation,
    CalledAfterAnnotation,
    CompleteAnnotation,
    ConstantAnnotation,
    DescriptionAnnotation,
    EnumAnnotation,
    ExpertAnnotation,
    GroupAnnotation,
    MoveAnnotation,
    OptionalAnnotation,
    PureAnnotation,
    RemoveAnnotation,
    RenameAnnotation,
    TodoAnnotation,
    ValueAnnotation,
)
from library_analyzer.processing.api.model import (
    Attribute,
    Class,
    Function,
    Parameter,
    Result,
)
from library_analyzer.processing.migration.model import Mapping


def _get_further_information(annotation: AbstractAnnotation) -> str:
    if isinstance(
        annotation,
        CompleteAnnotation | ExpertAnnotation | PureAnnotation | RemoveAnnotation,
    ):
        return ""
    if isinstance(annotation, BoundaryAnnotation):
        return " with the interval '" + str(annotation.interval.to_dict()) + "'"
    if isinstance(annotation, CalledAfterAnnotation):
        return " with the method '" + annotation.calledAfterName + "' that should be called before"
    if isinstance(annotation, DescriptionAnnotation):
        return " with the new description '" + annotation.newDescription + "'"
    if isinstance(annotation, EnumAnnotation):
        return (
            " with the new enum '"
            + annotation.enumName
            + " ("
            + ", ".join(enum_pair.stringValue + ", " + enum_pair.instanceName for enum_pair in annotation.pairs)
            + ")'"
        )
    if isinstance(annotation, GroupAnnotation):
        return (
            " with the group name '"
            + annotation.groupName
            + "' and the grouped parameters: '"
            + ", ".join(annotation.parameters)
            + "'"
        )
    if isinstance(annotation, MoveAnnotation):
        return " with the destination: '" + annotation.destination + "'"
    if isinstance(annotation, RenameAnnotation):
        return " with the new name '" + annotation.newName + "'"
    if isinstance(annotation, TodoAnnotation):
        return " with the todo '" + annotation.newTodo + "'"
    if isinstance(annotation, ValueAnnotation):
        value = " with the variant '" + annotation.variant.value
        if isinstance(annotation, ConstantAnnotation | OptionalAnnotation):
            value += (
                "' and the default Value '"
                + str(annotation.defaultValue)
                + " ( type: "
                + str(annotation.defaultValueType.value)
                + " )"
            )
        value += "'"
        return value
    return " with the data '" + str(annotation.to_dict()) + "'"


def get_migration_text(
    annotation: AbstractAnnotation,
    mapping: Mapping,
    for_todo_annotation: bool = False,
    additional_information: Any = None,
) -> str:
    class_name = str(annotation.__class__.__name__)
    if class_name.endswith("Annotation"):
        class_name = class_name[:-10]
    if issubclass(type(annotation), ValueAnnotation):
        class_name = "Value"
    migrate_text = "The @" + class_name + " Annotation" + _get_further_information(annotation)
    migrate_text += (
        " from the previous version was at '"
        + annotation.target
        + "' and the possible alternatives in the new version of the api are: "
        + _list_api_elements(mapping.get_apiv2_elements())
    )
    if additional_information is not None and isinstance(additional_information, list):
        functions = [function for function in additional_information if isinstance(function, Function)]
        if len(functions) > 0:
            migrate_text += " and the possible replacements (" + _list_api_elements(functions) + ")"

        parameters = [parameter for parameter in additional_information if isinstance(parameter, Parameter)]
        if len(parameters) > 0:
            migrate_text += " and the possible replacements (" + _list_api_elements(parameters) + ")"
    migration_text = migrate_text
    if for_todo_annotation:
        return migration_text
    if len(annotation.comment) == 0:
        return migration_text
    return annotation.comment + "\n" + migration_text


def _list_api_elements(
    api_elements: Sequence[Attribute | Class | Function | Parameter | Result],
) -> str:
    return ", ".join(api_element.id if hasattr(api_element, "id") else api_element.name for api_element in api_elements)
