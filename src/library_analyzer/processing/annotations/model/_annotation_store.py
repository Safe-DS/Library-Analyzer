from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ._annotations import (
    ANNOTATION_SCHEMA_VERSION,
    AbstractAnnotation,
    BoundaryAnnotation,
    CalledAfterAnnotation,
    CompleteAnnotation,
    DescriptionAnnotation,
    EnumAnnotation,
    ExpertAnnotation,
    GroupAnnotation,
    MoveAnnotation,
    PureAnnotation,
    RemoveAnnotation,
    RenameAnnotation,
    TodoAnnotation,
    ValueAnnotation,
)


@dataclass
class AnnotationStore:
    boundaryAnnotations: list[BoundaryAnnotation] = field(default_factory=list)  # noqa: N815
    calledAfterAnnotations: list[CalledAfterAnnotation] = field(default_factory=list)  # noqa: N815
    completeAnnotations: list[CompleteAnnotation] = field(default_factory=list)  # noqa: N815
    descriptionAnnotations: list[DescriptionAnnotation] = field(default_factory=list)  # noqa: N815
    enumAnnotations: list[EnumAnnotation] = field(default_factory=list)  # noqa: N815
    expertAnnotations: list[ExpertAnnotation] = field(default_factory=list)  # noqa: N815
    groupAnnotations: list[GroupAnnotation] = field(default_factory=list)  # noqa: N815
    moveAnnotations: list[MoveAnnotation] = field(default_factory=list)  # noqa: N815
    pureAnnotations: list[PureAnnotation] = field(default_factory=list)  # noqa: N815
    removeAnnotations: list[RemoveAnnotation] = field(default_factory=list)  # noqa: N815
    renameAnnotations: list[RenameAnnotation] = field(default_factory=list)  # noqa: N815
    todoAnnotations: list[TodoAnnotation] = field(default_factory=list)  # noqa: N815
    valueAnnotations: list[ValueAnnotation] = field(default_factory=list)  # noqa: N815

    @staticmethod
    def from_dict(d: dict[str, Any]) -> AnnotationStore:
        if d["schemaVersion"] == 1:
            raise ValueError("Incompatible Annotation File: This file is not compatible with the current version.")

        boundary_annotations = []
        for annotation in d["boundaryAnnotations"].values():
            boundary_annotations.append(BoundaryAnnotation.from_dict(annotation))

        called_after_annotations = []
        for annotation in d["calledAfterAnnotations"].values():
            called_after_annotations.append(CalledAfterAnnotation.from_dict(annotation))

        complete_annotations = []
        for annotation in d["completeAnnotations"].values():
            complete_annotations.append(CompleteAnnotation.from_dict(annotation))

        description_annotations = []
        for annotation in d["descriptionAnnotations"].values():
            description_annotations.append(DescriptionAnnotation.from_dict(annotation))

        enum_annotations = []
        for annotation in d["enumAnnotations"].values():
            enum_annotations.append(EnumAnnotation.from_dict(annotation))

        expert_annotations = []
        for annotation in d["expertAnnotations"].values():
            expert_annotations.append(ExpertAnnotation.from_dict(annotation))

        group_annotations = []
        for annotation in d["groupAnnotations"].values():
            group_annotations.append(GroupAnnotation.from_dict(annotation))

        move_annotations = []
        for annotation in d["moveAnnotations"].values():
            move_annotations.append(MoveAnnotation.from_dict(annotation))

        pure_annotations = []
        for annotation in d["pureAnnotations"].values():
            pure_annotations.append(PureAnnotation.from_dict(annotation))

        remove_annotations = []
        for annotation in d["removeAnnotations"].values():
            remove_annotations.append(RemoveAnnotation.from_dict(annotation))

        rename_annotations = []
        for annotation in d["renameAnnotations"].values():
            rename_annotations.append(RenameAnnotation.from_dict(annotation))

        todo_annotations = []
        for annotation in d["todoAnnotations"].values():
            todo_annotations.append(TodoAnnotation.from_dict(annotation))

        value_annotations = []
        for annotation in d["valueAnnotations"].values():
            value_annotations.append(ValueAnnotation.from_dict(annotation))

        return AnnotationStore(
            boundary_annotations,
            called_after_annotations,
            complete_annotations,
            description_annotations,
            enum_annotations,
            expert_annotations,
            group_annotations,
            move_annotations,
            pure_annotations,
            remove_annotations,
            rename_annotations,
            todo_annotations,
            value_annotations,
        )

    def add_annotation(self, annotation: AbstractAnnotation) -> None:
        if isinstance(annotation, BoundaryAnnotation):
            self.boundaryAnnotations.append(annotation)
        elif isinstance(annotation, CalledAfterAnnotation):
            self.calledAfterAnnotations.append(annotation)
        elif isinstance(annotation, CompleteAnnotation):
            self.completeAnnotations.append(annotation)
        elif isinstance(annotation, DescriptionAnnotation):
            self.descriptionAnnotations.append(annotation)
        elif isinstance(annotation, EnumAnnotation):
            self.enumAnnotations.append(annotation)
        elif isinstance(annotation, ExpertAnnotation):
            self.expertAnnotations.append(annotation)
        elif isinstance(annotation, GroupAnnotation):
            self.groupAnnotations.append(annotation)
        elif isinstance(annotation, MoveAnnotation):
            self.moveAnnotations.append(annotation)
        elif isinstance(annotation, PureAnnotation):
            self.pureAnnotations.append(annotation)
        elif isinstance(annotation, RemoveAnnotation):
            self.removeAnnotations.append(annotation)
        elif isinstance(annotation, RenameAnnotation):
            self.renameAnnotations.append(annotation)
        elif isinstance(annotation, TodoAnnotation):
            self.todoAnnotations.append(annotation)
        elif isinstance(annotation, ValueAnnotation):
            self.valueAnnotations.append(annotation)

    def to_dict(self) -> dict:
        return {
            "schemaVersion": ANNOTATION_SCHEMA_VERSION,
            "boundaryAnnotations": {annotation.target: annotation.to_dict() for annotation in self.boundaryAnnotations},
            "calledAfterAnnotations": {
                annotation.target: annotation.to_dict() for annotation in self.calledAfterAnnotations
            },
            "completeAnnotations": {annotation.target: annotation.to_dict() for annotation in self.completeAnnotations},
            "descriptionAnnotations": {
                annotation.target: annotation.to_dict() for annotation in self.descriptionAnnotations
            },
            "enumAnnotations": {annotation.target: annotation.to_dict() for annotation in self.enumAnnotations},
            "expertAnnotations": {annotation.target: annotation.to_dict() for annotation in self.expertAnnotations},
            "groupAnnotations": {annotation.target: annotation.to_dict() for annotation in self.groupAnnotations},
            "moveAnnotations": {annotation.target: annotation.to_dict() for annotation in self.moveAnnotations},
            "pureAnnotations": {annotation.target: annotation.to_dict() for annotation in self.pureAnnotations},
            "renameAnnotations": {annotation.target: annotation.to_dict() for annotation in self.renameAnnotations},
            "removeAnnotations": {annotation.target: annotation.to_dict() for annotation in self.removeAnnotations},
            "todoAnnotations": {annotation.target: annotation.to_dict() for annotation in self.todoAnnotations},
            "valueAnnotations": {annotation.target: annotation.to_dict() for annotation in self.valueAnnotations},
        }
