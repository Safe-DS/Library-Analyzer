from __future__ import annotations

import dataclasses
from dataclasses import dataclass


@dataclass(frozen=True)
class ClassDocumentation:
    description: str = ""
    full_docstring: str = ""

    @staticmethod
    def from_dict(d: dict) -> ClassDocumentation:
        return ClassDocumentation(**d)

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class FunctionDocumentation:
    description: str = ""
    full_docstring: str = ""

    @staticmethod
    def from_dict(d: dict) -> FunctionDocumentation:
        return FunctionDocumentation(**d)

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class ParameterDocumentation:
    type: str = ""
    default_value: str = ""
    description: str = ""

    @staticmethod
    def from_dict(d: dict) -> ParameterDocumentation:
        return ParameterDocumentation(**d)

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)