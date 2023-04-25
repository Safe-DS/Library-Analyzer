from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from library_analyzer.processing.api.model import Parameter


@dataclass
class Action:
    action: str

    @classmethod
    def from_dict(cls, json: dict[str, Any]) -> Action:
        return cls(json["action"])

    def to_dict(self) -> dict[str, Any]:
        return {"action": self.action}


class RuntimeAction(Action):
    def __init__(self, action: str) -> None:
        super().__init__(action)


class StaticAction(Action):
    def __init__(self, action: str) -> None:
        super().__init__(action)


class ParameterIsIgnored(StaticAction):
    def __init__(self, action: str) -> None:
        super().__init__(action)


class ParameterIsIllegal(StaticAction):
    def __init__(self, action: str) -> None:
        super().__init__(action)


@dataclass
class Condition:
    condition: str

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Condition:
        return cls(d["condition"])

    def to_dict(self) -> dict[str, Any]:
        return {"condition": self.condition}


class RuntimeCondition(Condition):
    def __init__(self, condition: str) -> None:
        super().__init__(condition)


class StaticCondition(Condition):
    def __init__(self, condition: str) -> None:
        super().__init__(condition)


class ParameterHasValue(StaticCondition):
    def __init__(self, condition: str) -> None:
        super().__init__(condition)


class ParameterIsNone(StaticCondition):
    def __init__(self, condition: str) -> None:
        super().__init__(condition)


@dataclass
class Dependency:
    hasDependentParameter: Parameter  # noqa: N815
    isDependingOn: Parameter  # noqa: N815
    hasCondition: Condition  # noqa: N815
    hasAction: Action  # noqa: N815

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Dependency:
        return cls(
            Parameter.from_dict(d["hasDependentParameter"]),
            Parameter.from_dict(d["isDependingOn"]),
            Condition.from_dict(d["hasCondition"]),
            Action.from_dict(d["hasAction"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "hasDependentParameter": self.hasDependentParameter.to_dict(),
            "isDependingOn": self.isDependingOn.to_dict(),
            "hasCondition": self.hasCondition.to_dict(),
            "hasAction": self.hasAction.to_dict(),
        }


@dataclass
class APIDependencies:
    dependencies: dict

    def to_dict(self) -> dict[str, Any]:
        return {
            function_name: {
                parameter_name: [dependency.to_dict() for dependency in dependencies]
                for parameter_name, dependencies in parameter_name.items()
            }
            for function_name, parameter_name in self.dependencies.items()
        }
