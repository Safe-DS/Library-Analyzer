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
    boundaryAnnotations: list[BoundaryAnnotation] = field(default_factory=list)
    calledAfterAnnotations: list[CalledAfterAnnotation] = field(default_factory=list)
    completeAnnotations: list[CompleteAnnotation] = field(default_factory=list)
    descriptionAnnotations: list[DescriptionAnnotation] = field(default_factory=list)
    enumAnnotations: list[EnumAnnotation] = field(default_factory=list)
    expertAnnotations: list[ExpertAnnotation] = field(default_factory=list)
    groupAnnotations: list[GroupAnnotation] = field(default_factory=list)
    moveAnnotations: list[MoveAnnotation] = field(default_factory=list)
    pureAnnotations: list[PureAnnotation] = field(default_factory=list)
    removeAnnotations: list[RemoveAnnotation] = field(default_factory=list)
    renameAnnotations: list[RenameAnnotation] = field(default_factory=list)
    todoAnnotations: list[TodoAnnotation] = field(default_factory=list)
    valueAnnotations: list[ValueAnnotation] = field(default_factory=list)

    @staticmethod
    def from_json(json: Any) -> AnnotationStore:
        if json["schemaVersion"] == 1:
            raise Exception("Incompatible Annotation File: This file is not compatible with the current version.")

        boundary_annotations = []
        for annotation in json["boundaryAnnotations"].values():
            boundary_annotations.append(BoundaryAnnotation.from_json(annotation))

        called_after_annotations = []
        for annotation in json["calledAfterAnnotations"].values():
            called_after_annotations.append(CalledAfterAnnotation.from_json(annotation))

        complete_annotations = []
        for annotation in json["completeAnnotations"].values():
            complete_annotations.append(CompleteAnnotation.from_json(annotation))

        description_annotations = []
        for annotation in json["descriptionAnnotations"].values():
            description_annotations.append(DescriptionAnnotation.from_json(annotation))

        enum_annotations = []
        for annotation in json["enumAnnotations"].values():
            enum_annotations.append(EnumAnnotation.from_json(annotation))

        expert_annotations = []
        for annotation in json["expertAnnotations"].values():
            expert_annotations.append(ExpertAnnotation.from_json(annotation))

        group_annotations = []
        for annotation in json["groupAnnotations"].values():
            group_annotations.append(GroupAnnotation.from_json(annotation))

        move_annotations = []
        for annotation in json["moveAnnotations"].values():
            move_annotations.append(MoveAnnotation.from_json(annotation))

        pure_annotations = []
        for annotation in json["pureAnnotations"].values():
            pure_annotations.append(PureAnnotation.from_json(annotation))

        remove_annotations = []
        for annotation in json["removeAnnotations"].values():
            remove_annotations.append(RemoveAnnotation.from_json(annotation))

        rename_annotations = []
        for annotation in json["renameAnnotations"].values():
            rename_annotations.append(RenameAnnotation.from_json(annotation))

        todo_annotations = []
        for annotation in json["todoAnnotations"].values():
            todo_annotations.append(TodoAnnotation.from_json(annotation))

        value_annotations = []
        for annotation in json["valueAnnotations"].values():
            value_annotations.append(ValueAnnotation.from_json(annotation))

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

    def to_json(self) -> dict:
        return {
            "schemaVersion": ANNOTATION_SCHEMA_VERSION,
            "boundaryAnnotations": {annotation.target: annotation.to_json() for annotation in self.boundaryAnnotations},
            "calledAfterAnnotations": {
                annotation.target: annotation.to_json() for annotation in self.calledAfterAnnotations
            },
            "completeAnnotations": {annotation.target: annotation.to_json() for annotation in self.completeAnnotations},
            "descriptionAnnotations": {
                annotation.target: annotation.to_json() for annotation in self.descriptionAnnotations
            },
            "enumAnnotations": {annotation.target: annotation.to_json() for annotation in self.enumAnnotations},
            "expertAnnotations": {annotation.target: annotation.to_json() for annotation in self.expertAnnotations},
            "groupAnnotations": {annotation.target: annotation.to_json() for annotation in self.groupAnnotations},
            "moveAnnotations": {annotation.target: annotation.to_json() for annotation in self.moveAnnotations},
            "pureAnnotations": {annotation.target: annotation.to_json() for annotation in self.pureAnnotations},
            "renameAnnotations": {annotation.target: annotation.to_json() for annotation in self.renameAnnotations},
            "removeAnnotations": {annotation.target: annotation.to_json() for annotation in self.removeAnnotations},
            "todoAnnotations": {annotation.target: annotation.to_json() for annotation in self.todoAnnotations},
            "valueAnnotations": {annotation.target: annotation.to_json() for annotation in self.valueAnnotations},
        }
