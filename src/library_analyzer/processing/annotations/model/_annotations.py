from __future__ import annotations

from abc import ABC
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from library_analyzer.processing.api import Action, Condition

ANNOTATION_SCHEMA_VERSION = 2


class EnumReviewResult(Enum):
    CORRECT = "correct"
    UNSURE = "unsure"
    WRONG = "wrong"
    NONE = ""

    @staticmethod
    def to_dict(result: list[tuple[str, Any]]) -> dict[str, Any]:
        for item in result:
            if isinstance(item[1], EnumReviewResult):
                result.append((item[0], item[1].value))
                result.remove(item)
        return dict(result)


@dataclass
class AbstractAnnotation(ABC):
    target: str
    authors: list[str]
    reviewers: list[str]
    comment: str
    reviewResult: EnumReviewResult  # noqa: N815

    @staticmethod
    def from_dict(d: dict[str, Any]) -> AbstractAnnotation:
        review_result = EnumReviewResult(d.get("reviewResult", ""))

        return AbstractAnnotation(
            d["target"],
            d["authors"],
            d["reviewers"],
            d.get("comment", ""),
            review_result,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self, dict_factory=EnumReviewResult.to_dict)


@dataclass
class DependencyAnnotation(AbstractAnnotation):
    has_dependent_parameter: list[str]
    is_depending_on: list[str]
    condition: Condition
    action: Action

    @staticmethod
    def from_dict(d: dict[str, Any]) -> DependencyAnnotation:
        annotation = AbstractAnnotation.from_dict(d)
        return DependencyAnnotation(
            annotation.target,
            annotation.authors,
            annotation.reviewers,
            annotation.comment,
            annotation.reviewResult,
            d["has_dependent_parameter"],
            d["is_depending_on"],
            Condition.from_dict(d["condition"]),
            Action.from_dict(d["action"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "authors": self.authors,
            "reviewers": self.reviewers,
            "comment": self.comment,
            "reviewResult": self.reviewResult.value,
            "has_dependent_parameter": self.has_dependent_parameter,
            "is_depending_on": self.is_depending_on,
            "condition": self.condition.to_dict(),
            "action": self.action.to_dict(),
        }


@dataclass
class RemoveAnnotation(AbstractAnnotation):
    @staticmethod
    def from_dict(d: dict[str, Any]) -> RemoveAnnotation:
        annotation = AbstractAnnotation.from_dict(d)
        return RemoveAnnotation(
            annotation.target,
            annotation.authors,
            annotation.reviewers,
            annotation.comment,
            annotation.reviewResult,
        )


@dataclass
class Interval:
    lowerIntervalLimit: int | float | str  # noqa: N815
    lowerLimitType: int  # noqa: N815
    upperIntervalLimit: int | float | str  # noqa: N815
    upperLimitType: int  # noqa: N815
    isDiscrete: bool  # noqa: N815

    @staticmethod
    def from_dict(d: dict[str, Any]) -> Interval:
        return Interval(
            d["lowerIntervalLimit"],
            d["lowerLimitType"],
            d["upperIntervalLimit"],
            d["upperLimitType"],
            d["isDiscrete"],
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BoundaryAnnotation(AbstractAnnotation):
    interval: Interval

    @staticmethod
    def from_dict(d: dict[str, Any]) -> BoundaryAnnotation:
        annotation = AbstractAnnotation.from_dict(d)
        return BoundaryAnnotation(
            annotation.target,
            annotation.authors,
            annotation.reviewers,
            annotation.comment,
            annotation.reviewResult,
            Interval.from_dict(d["interval"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "authors": self.authors,
            "reviewers": self.reviewers,
            "comment": self.comment,
            "reviewResult": self.reviewResult.value,
            "interval": self.interval.to_dict(),
        }


@dataclass
class EnumPair:
    stringValue: str  # noqa: N815
    instanceName: str  # noqa: N815

    @staticmethod
    def from_dict(d: dict[str, Any]) -> EnumPair:
        return EnumPair(d["stringValue"], d["instanceName"])

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EnumAnnotation(AbstractAnnotation):
    enumName: str  # noqa: N815
    pairs: list[EnumPair]

    @staticmethod
    def from_dict(d: dict[str, Any]) -> EnumAnnotation:
        annotation = AbstractAnnotation.from_dict(d)
        pairs = [EnumPair.from_dict(enum_pair) for enum_pair in d["pairs"]]
        return EnumAnnotation(
            annotation.target,
            annotation.authors,
            annotation.reviewers,
            annotation.comment,
            annotation.reviewResult,
            d["enumName"],
            pairs,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "authors": self.authors,
            "reviewers": self.reviewers,
            "comment": self.comment,
            "reviewResult": self.reviewResult.value,
            "enumName": self.enumName,
            "pairs": [pair.to_dict() for pair in self.pairs],
        }


class ValueAnnotation(AbstractAnnotation, ABC):
    class Variant(Enum):
        CONSTANT = "constant"
        OMITTED = "omitted"
        OPTIONAL = "optional"
        REQUIRED = "required"

    class DefaultValueType(Enum):
        BOOLEAN = "boolean"
        NONE = "none"
        NUMBER = "number"
        STRING = "string"

    variant: Variant

    @staticmethod
    def from_dict(d: dict[str, Any]) -> ValueAnnotation:
        variant = d["variant"]
        if ValueAnnotation.Variant.CONSTANT.value == variant:
            return ConstantAnnotation.from_dict(d)
        if ValueAnnotation.Variant.OMITTED.value == variant:
            return OmittedAnnotation.from_dict(d)
        if ValueAnnotation.Variant.OPTIONAL.value == variant:
            return OptionalAnnotation.from_dict(d)
        if ValueAnnotation.Variant.REQUIRED.value == variant:
            return RequiredAnnotation.from_dict(d)
        raise KeyError("unkonwn variant found")


@dataclass
class ConstantAnnotation(ValueAnnotation):
    variant = ValueAnnotation.Variant.CONSTANT
    defaultValueType: ValueAnnotation.DefaultValueType  # noqa: N815
    defaultValue: Any  # noqa: N815

    @staticmethod
    def from_dict(d: dict[str, Any]) -> ConstantAnnotation:
        annotation = AbstractAnnotation.from_dict(d)
        return ConstantAnnotation(
            annotation.target,
            annotation.authors,
            annotation.reviewers,
            annotation.comment,
            annotation.reviewResult,
            ValueAnnotation.DefaultValueType(d["defaultValueType"]),
            d["defaultValue"],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "authors": self.authors,
            "reviewers": self.reviewers,
            "comment": self.comment,
            "reviewResult": self.reviewResult.value,
            "variant": self.variant.value,
            "defaultValueType": self.defaultValueType.value,
            "defaultValue": self.defaultValue,
        }


@dataclass
class OmittedAnnotation(ValueAnnotation):
    variant = ValueAnnotation.Variant.OMITTED

    @staticmethod
    def from_dict(d: dict[str, Any]) -> OmittedAnnotation:
        annotation = AbstractAnnotation.from_dict(d)
        return OmittedAnnotation(
            annotation.target,
            annotation.authors,
            annotation.reviewers,
            annotation.comment,
            annotation.reviewResult,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "authors": self.authors,
            "reviewers": self.reviewers,
            "comment": self.comment,
            "reviewResult": self.reviewResult.value,
            "variant": self.variant.value,
        }


@dataclass
class OptionalAnnotation(ValueAnnotation):
    variant = ValueAnnotation.Variant.OPTIONAL
    defaultValueType: ValueAnnotation.DefaultValueType  # noqa: N815
    defaultValue: Any  # noqa: N815

    @staticmethod
    def from_dict(d: dict[str, Any]) -> OptionalAnnotation:
        annotation = AbstractAnnotation.from_dict(d)
        return OptionalAnnotation(
            annotation.target,
            annotation.authors,
            annotation.reviewers,
            annotation.comment,
            annotation.reviewResult,
            ValueAnnotation.DefaultValueType(d["defaultValueType"]),
            d["defaultValue"],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "authors": self.authors,
            "reviewers": self.reviewers,
            "comment": self.comment,
            "reviewResult": self.reviewResult.value,
            "variant": self.variant.value,
            "defaultValueType": self.defaultValueType.value,
            "defaultValue": self.defaultValue,
        }


@dataclass
class RequiredAnnotation(ValueAnnotation):
    variant = ValueAnnotation.Variant.REQUIRED

    @staticmethod
    def from_dict(d: dict[str, Any]) -> RequiredAnnotation:
        annotation = AbstractAnnotation.from_dict(d)
        return RequiredAnnotation(
            annotation.target,
            annotation.authors,
            annotation.reviewers,
            annotation.comment,
            annotation.reviewResult,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "authors": self.authors,
            "reviewers": self.reviewers,
            "comment": self.comment,
            "reviewResult": self.reviewResult.value,
            "variant": self.variant.value,
        }


class ParameterType(Enum):
    Constant = 0
    Optional = 1
    Required = 2
    Unused = 3


class ParameterInfo:
    type: ParameterType
    value: str
    value_type: str

    def __init__(self, parameter_type: ParameterType, value: str = "", value_type: str = "") -> None:
        self.type = parameter_type
        self.value = value
        self.value_type = value_type


@dataclass
class CalledAfterAnnotation(AbstractAnnotation):
    calledAfterName: str  # noqa: N815

    @staticmethod
    def from_dict(d: Any) -> CalledAfterAnnotation:
        annotation = AbstractAnnotation.from_dict(d)
        return CalledAfterAnnotation(
            annotation.target,
            annotation.authors,
            annotation.reviewers,
            annotation.comment,
            annotation.reviewResult,
            d["calledAfterName"],
        )


class CompleteAnnotation(AbstractAnnotation):
    @staticmethod
    def from_dict(d: Any) -> CompleteAnnotation:
        annotation = AbstractAnnotation.from_dict(d)
        return CompleteAnnotation(
            annotation.target,
            annotation.authors,
            annotation.reviewers,
            annotation.comment,
            annotation.reviewResult,
        )


@dataclass
class DescriptionAnnotation(AbstractAnnotation):
    newDescription: str  # noqa: N815

    @staticmethod
    def from_dict(d: Any) -> DescriptionAnnotation:
        annotation = AbstractAnnotation.from_dict(d)
        return DescriptionAnnotation(
            annotation.target,
            annotation.authors,
            annotation.reviewers,
            annotation.comment,
            annotation.reviewResult,
            d["newDescription"],
        )


@dataclass
class ExpertAnnotation(AbstractAnnotation):
    @staticmethod
    def from_dict(d: Any) -> ExpertAnnotation:
        annotation = AbstractAnnotation.from_dict(d)
        return ExpertAnnotation(
            annotation.target,
            annotation.authors,
            annotation.reviewers,
            annotation.comment,
            annotation.reviewResult,
        )


@dataclass
class GroupAnnotation(AbstractAnnotation):
    groupName: str  # noqa: N815
    parameters: list[str]

    @staticmethod
    def from_dict(d: Any) -> GroupAnnotation:
        annotation = AbstractAnnotation.from_dict(d)
        return GroupAnnotation(
            annotation.target,
            annotation.authors,
            annotation.reviewers,
            annotation.comment,
            annotation.reviewResult,
            d["groupName"],
            d["parameters"],
        )


@dataclass
class MoveAnnotation(AbstractAnnotation):
    destination: str

    @staticmethod
    def from_dict(d: Any) -> MoveAnnotation:
        annotation = AbstractAnnotation.from_dict(d)
        return MoveAnnotation(
            annotation.target,
            annotation.authors,
            annotation.reviewers,
            annotation.comment,
            annotation.reviewResult,
            d["destination"],
        )


class PureAnnotation(AbstractAnnotation):
    @staticmethod
    def from_dict(d: Any) -> PureAnnotation:
        annotation = AbstractAnnotation.from_dict(d)
        return PureAnnotation(
            annotation.target,
            annotation.authors,
            annotation.reviewers,
            annotation.comment,
            annotation.reviewResult,
        )


@dataclass
class RenameAnnotation(AbstractAnnotation):
    newName: str  # noqa: N815

    @staticmethod
    def from_dict(d: Any) -> RenameAnnotation:
        annotation = AbstractAnnotation.from_dict(d)
        return RenameAnnotation(
            annotation.target,
            annotation.authors,
            annotation.reviewers,
            annotation.comment,
            annotation.reviewResult,
            d["newName"],
        )


@dataclass
class TodoAnnotation(AbstractAnnotation):
    newTodo: str  # noqa: N815

    @staticmethod
    def from_dict(d: Any) -> TodoAnnotation:
        annotation = AbstractAnnotation.from_dict(d)
        return TodoAnnotation(
            annotation.target,
            annotation.authors,
            annotation.reviewers,
            annotation.comment,
            annotation.reviewResult,
            d["newTodo"],
        )
