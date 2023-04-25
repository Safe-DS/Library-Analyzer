from __future__ import annotations

from enum import Enum
from typing import Any

from ._docstring import ParameterDocstring
from ._types import AbstractType, create_type


class Parameter:
    @staticmethod
    def from_dict(d: dict[str, Any]) -> Parameter:
        return Parameter(
            d["id"],
            d["name"],
            d["qname"],
            d.get("default_value", None),
            ParameterAssignment[d.get("assigned_by", "POSITION_OR_NAME")],
            d.get("is_public", True),
            ParameterDocstring.from_dict(d.get("docstring", {})),
        )

    def __hash__(self) -> int:
        return hash(
            (
                self.id,
                self.name,
                self.qname,
                self.default_value,
                self.assigned_by,
                self.is_public,
                self.documentation,
            ),
        )

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, Parameter)
            and self.id == other.id
            and self.name == other.name
            and self.qname == other.qname
            and self.default_value == other.default_value
            and self.assigned_by == other.assigned_by
            and self.is_public == other.is_public
            and self.documentation == other.documentation
            and self.type == other.type
        )

    def __init__(
        self,
        id_: str,
        name: str,
        qname: str,
        default_value: str | None,
        assigned_by: ParameterAssignment,
        is_public: bool,
        documentation: ParameterDocstring,
    ) -> None:
        self.id: str = id_
        self.name: str = name
        self.qname: str = qname
        self.default_value: str | None = default_value
        self.assigned_by: ParameterAssignment = assigned_by
        self.is_public: bool = is_public
        self.documentation = documentation
        self.type: AbstractType | None = create_type(documentation)

    def is_optional(self) -> bool:
        return self.default_value is not None

    def is_required(self) -> bool:
        return self.default_value is None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "qname": self.qname,
            "default_value": self.default_value,
            "assigned_by": self.assigned_by.name,
            "is_public": self.is_public,
            "docstring": self.documentation.to_dict(),
            "type": self.type.to_dict() if self.type is not None else {},
        }


class ParameterAssignment(Enum):
    """
    How arguments are assigned to parameters. The parameters must appear exactly in this order in a parameter list.

    IMPLICIT parameters appear on instance methods (usually called "self") and on class methods (usually called "cls").
    POSITION_ONLY parameters precede the "/" in a parameter list. NAME_ONLY parameters follow the "*" or the
    POSITIONAL_VARARGS parameter ("*args"). Between the "/" and the "*" the POSITION_OR_NAME parameters reside. Finally,
    the parameter list might optionally include a NAMED_VARARG parameter ("**kwargs").
    """

    IMPLICIT = "IMPLICIT"
    POSITION_ONLY = "POSITION_ONLY"
    POSITION_OR_NAME = "POSITION_OR_NAME"
    POSITIONAL_VARARG = ("POSITIONAL_VARARG",)
    NAME_ONLY = "NAME_ONLY"
    NAMED_VARARG = "NAMED_VARARG"
