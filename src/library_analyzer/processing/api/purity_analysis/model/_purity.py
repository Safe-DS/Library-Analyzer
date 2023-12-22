from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from library_analyzer.processing.api.purity_analysis.model import (
        GlobalVariable,
        ClassVariable,
        InstanceVariable,
        Parameter
    )


class PurityResult(ABC):
    """Class for purity results."""

    @abstractmethod
    def update(self, other: PurityResult | None) -> PurityResult:
        return self._update(other)

    def _update(self, other: PurityResult | None) -> PurityResult:  # type: ignore[return] # all cases are handled
        """Update the current result with another result.

        Parameters
        ----------
        other : PurityResult
            The other result.

        Returns
        -------
        PurityResult
            The updated result.
        """
        if other is None:
            pass
        elif isinstance(self, Pure):
            if isinstance(other, Pure):
                return self
            elif isinstance(other, Impure):
                return other
        elif isinstance(self, Impure):
            if isinstance(other, Pure):
                return self
            elif isinstance(other, Impure):
                return Impure(reasons=self.reasons | other.reasons)
        else:
            raise TypeError(f"Cannot update {self} with {other}")


@dataclass
class Pure(PurityResult):
    """Class for pure results.

    A function is pure if it has no (External-, Internal-)Read nor (External-, Internal-)Write side effects.
    A pure function must also have no unknown reasons.
    """
    def update(self, other: PurityResult | None) -> PurityResult:
        return super()._update(other)


@dataclass
class Impure(PurityResult):
    """Class for impure results.

    A function is impure if it has at least one (External-, Internal-)Read OR (External-, Internal-)Write side effect.
    An impure function must also have no unknown reasons.

    Be aware that a function can be impure because of multiple reasons.
    Also, Impure != Pure since: not Pure would mean a function is either unknown or has at least one
    (External-, Internal-)Read (External-, Internal-) or Write side effect.
    """
    reasons: set[ImpurityReason]

    def update(self, other: PurityResult | None) -> PurityResult:
        return super()._update(other)


class ImpurityReason(ABC):  # noqa: B024 # this is just a base class, and it is important that it cannot be instantiated
    """Class for impurity reasons.

    If a funtion is impure it is because of one or more impurity reasons.
    """

    def __hash__(self) -> int:
        return hash(str(self))


class Read(ImpurityReason, ABC):
    """Class for read type impurity reasons."""


@dataclass
class NonLocalVariableRead(Read):
    """Class for internal variable reads (GlobalVariable / global Fields)."""
    symbol: GlobalVariable | ClassVariable | InstanceVariable

    def __hash__(self) -> int:
        return hash(str(self))


@dataclass
class FileRead(Read):
    """Class for external variable reads (File / Database)."""
    source: Expression | None = None

    def __hash__(self) -> int:
        return hash(str(self))


class Write(ImpurityReason, ABC):
    """Class for write type impurity reasons."""


@dataclass
class NonLocalVariableWrite(Write):
    """Class for internal variable writes (GlobalVariable / global Fields)."""
    symbol: GlobalVariable | ClassVariable | InstanceVariable

    def __hash__(self) -> int:
        return hash(str(self))


@dataclass
class FileWrite(Write):
    """Class for external variable writes (File / Database)."""
    source: Expression | None = None

    def __hash__(self) -> int:
        return hash(str(self))


class Unknown(ImpurityReason, ABC):
    """Class for unknown type impurity reasons."""


@dataclass
class UnknownCall(Unknown):
    """Class for calling unknown code.

    Since we cannot analyze unknown code, we mark it as unknown.
    """
    expression: Expression

    def __hash__(self) -> int:
        return hash(str(self))


@dataclass
class NativeCall(Unknown):  # ExternalCall
    """Class for calling native code.

    Since we cannot analyze native code, we mark it as unknown.
    """
    expression: Expression

    def __hash__(self) -> int:
        return hash(str(self))


@dataclass
class CallOfParameter(Unknown):  # ParameterCall
    """Class for parameter calls."""
    expression: Expression

    def __hash__(self) -> int:
        return hash(str(self))


# Type of access
class Expression(ABC):  # noqa: B024 # this is just a base class, and it is important that it cannot be instantiated
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
    """Class for string literals."""
    value: str


class OpenMode(Enum):
    READ = auto()
    WRITE = auto()
    READ_WRITE = auto()
