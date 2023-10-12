from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto

import astroid

from library_analyzer.processing.api.purity_analysis.model._scope import NodeID


@dataclass
class PurityResult(ABC):
    """Class for purity results."""
    reasons: list[ImpurityReason]


@dataclass
class Pure(PurityResult):
    """Class for pure results.

    A function is pure if it has no (External-, Internal-)Read nor (External-, Internal-)Write side effects.
    A pure function must also have no unknown reasons.
    """
    reasons: list = field(default_factory=list)


@dataclass
class Impure(PurityResult):
    """Class for impure results.

    A function is impure if it has at least one (External-, Internal-)Read OR (External-, Internal-)Write side effect.
    An impure function must also have no unknown reasons.

    Be aware that a function can be impure because of multiple reasons.
    Also, Impure != Pure since: not Pure would mean a function is either unknown or has at least one
    (External-, Internal-)Read (External-, Internal-) or Write side effect.
    """
    reasons: list[ImpurityReason]


@dataclass
class ImpurityReason(ABC):
    """Class for impurity reasons.

    If a funtion is impure it is because of one or more impurity reasons.
    """
    pass


@dataclass
class InternalRead(ImpurityReason):  # VariableRead
    """Class for internal variable reads (GlobalVariable / global Fields)."""
    source: Expression


@dataclass
class ExternalRead(ImpurityReason):  # FileRead
    """Class for external variable reads (File / Database)."""
    source: Expression


@dataclass
class InternalWrite(ImpurityReason):  # VariableWrite
    """Class for internal variable writes (GlobalVariable / global Fields)."""
    expression: Expression


@dataclass
class ExternalWrite(ImpurityReason):  # FileWrite
    """Class for external variable writes (File / Database)."""
    source: Expression


@dataclass
class Call(ImpurityReason):
    """Class for impure function calls."""
    expression: Expression


@dataclass
class SystemInteraction(ImpurityReason):
    """Class for system interactions (e.g. print)."""
    kind = str  # SystemIn / SystemOut / SystemErr


@dataclass
class Unknown(ImpurityReason):
    """Class for unknown impurity reasons."""
    kind = str


# Type of access
class Expression(astroid.NodeNG, ABC):
    # @abstractmethod
    # def __hash__(self) -> int:
    #    pass
    ...


@dataclass
class AttributeAccess(Expression):
    """Class for class attribute access."""

    name: str


@dataclass
class GlobalAccess(Expression):
    """Class for global variable access."""

    name: str
    module: str = "None"


@dataclass
class ParameterAccess(Expression):
    """Class for function parameter access."""

    name: str
    function: str


@dataclass
class InstanceAccess(Expression):
    """Class for field access of an instance attribute (receiver.target)."""
    receiver: Expression
    target: Expression



@dataclass
class StringLiteral(Expression):
    value: str


@dataclass
class Reference(Expression):
    name: str

