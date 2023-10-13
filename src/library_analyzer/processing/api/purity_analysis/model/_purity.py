from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto

import astroid

from library_analyzer.processing.api.purity_analysis.model._scope import NodeID, GlobalVariable, ClassVariable, \
    InstanceVariable, Parameter


class PurityResult(ABC):
    """Class for purity results."""


@dataclass
class Pure(PurityResult):
    """Class for pure results.

    A function is pure if it has no (External-, Internal-)Read nor (External-, Internal-)Write side effects.
    A pure function must also have no unknown reasons.
    """


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


class ImpurityReason(ABC):
    """Class for impurity reasons.

    If a funtion is impure it is because of one or more impurity reasons.
    """


class Read(ImpurityReason, ABC):
    """Class for external variable reads (File / Database)."""


@dataclass
class NonLocalVariableRead(Read):
    """Class for internal variable reads (GlobalVariable / global Fields)."""
    symbol: GlobalVariable | ClassVariable | InstanceVariable


@dataclass
class FileRead(Read):
    """Class for external variable reads (File / Database)."""
    source: Expression


class Write(ImpurityReason, ABC):
    """Class for external variable writes (File / Database)."""


@dataclass
class NonLocalVariableWrite(Write):
    """Class for internal variable writes (GlobalVariable / global Fields)."""
    symbol: GlobalVariable | ClassVariable | InstanceVariable


@dataclass
class FileWrite(Write):
    """Class for external variable writes (File / Database)."""
    source: Expression


class Unknown(ImpurityReason, ABC):
    """Class for unknown impurity reasons."""


@dataclass
class NativeCall(Unknown):  # ExternalCall
    """Class for impure function calls."""
    expression: Expression


@dataclass
class CallOfParameter(Unknown):  # ExternalCall
    """Class for impure function calls."""
    expression: Expression


# Type of access
class Expression(ABC):
    # @abstractmethod
    # def __hash__(self) -> int:
    #    pass
    ...


@dataclass
class ParameterAccess(Expression):
    """Class for function parameter access."""
    parameter: Parameter


@dataclass
class StringLiteral(Expression):
    value: str


