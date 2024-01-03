from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from library_analyzer.processing.api.purity_analysis.model import (
        ClassVariable,
        GlobalVariable,
        InstanceVariable,
        Parameter,
    )


class PurityResult(ABC):
    """Superclass for purity results.

    Purity results are either pure, impure or unknown.
    """

    @abstractmethod
    def update(self, other: PurityResult | None) -> PurityResult:
        """Update the current result with another result.

        See PurityResult._update
        """
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

        Raises
        ------
        TypeError
            If the result cannot be updated with the other result.
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
        """Update the current result with another result.

        See PurityResult._update
        """
        return super()._update(other)


@dataclass
class Impure(PurityResult):
    """Class for impure results.

    A function is impure if it has at least one
    (File-, NonLocalVariable-)Read OR (File-, NonLocalVariable-)Write side effect.
    An impure function must also have no unknown reasons.

    Be aware that a function can be impure because of multiple reasons.
    Also, Impure != Pure since: not Pure would mean a function is either unknown or has at least one
    (File-, NonLocalVariable-)Read OR (File-, NonLocalVariable-)Write side effect.

    Attributes
    ----------
    reasons : set[ImpurityReason]
        The reasons why the function is impure.
    """

    reasons: set[ImpurityReason]

    def update(self, other: PurityResult | None) -> PurityResult:
        """Update the current result with another result.

        See PurityResult._update
        """
        return super()._update(other)


class ImpurityReason(ABC):  # noqa: B024 # this is just a base class, and it is important that it cannot be instantiated
    """Superclass for impurity reasons.

    If a funtion is impure it is because of one or more impurity reasons.
    """

    def __hash__(self) -> int:
        return hash(str(self))


class Read(ImpurityReason, ABC):
    """Superclass for read type impurity reasons."""


@dataclass
class NonLocalVariableRead(Read):
    """Class for internal variable reads (GlobalVariable / global Fields).

    Attributes
    ----------
    symbol : GlobalVariable | ClassVariable | InstanceVariable
        The symbol that is read.
    """

    symbol: GlobalVariable | ClassVariable | InstanceVariable

    def __hash__(self) -> int:
        return hash(str(self))


@dataclass
class FileRead(Read):
    """Class for external variable reads (File / Database).

    Attributes
    ----------
    source : Expression | None
        The source of the read.
        This is None if the source is unknown.  # TODO: or should that be a of Type Unknown? LARS
    """

    source: Expression | None = None  # TODO: this should never be None? or should it? LARS

    def __hash__(self) -> int:
        return hash(str(self))


class Write(ImpurityReason, ABC):
    """Superclass for write type impurity reasons."""


@dataclass
class NonLocalVariableWrite(Write):
    """Class for internal variable writes (GlobalVariable / global Fields).

    Attributes
    ----------
    symbol : GlobalVariable | ClassVariable | InstanceVariable
        The symbol that is written to.
    """

    symbol: GlobalVariable | ClassVariable | InstanceVariable

    def __hash__(self) -> int:
        return hash(str(self))


@dataclass
class FileWrite(Write):
    """Class for external variable writes (File / Database).

    Attributes
    ----------
    source : Expression | None
        The source of the write.
        This is None if the source is unknown.  # TODO: see above LARS
    """

    source: Expression | None = None

    def __hash__(self) -> int:
        return hash(str(self))


class Unknown(ImpurityReason, ABC):
    """Superclass for unknown type impurity reasons."""


@dataclass
class UnknownCall(Unknown):
    """Class for calling unknown code.

    Since we cannot analyze unknown code, we mark it as unknown.

    Attributes
    ----------
    expression : Expression
        The expression that is called.
    """

    expression: Expression

    def __hash__(self) -> int:
        return hash(str(self))


@dataclass
class NativeCall(Unknown):  # ExternalCall
    """Class for calling native code.

    Since we cannot analyze native code, we mark it as unknown.

    Attributes
    ----------
    expression : Expression
        The expression that is called.
    """

    expression: Expression

    def __hash__(self) -> int:
        return hash(str(self))


@dataclass
class CallOfParameter(Unknown):  # ParameterCall
    """Class for parameter calls.

    Since we cannot analyze parameter calls, we mark it as unknown.
    A parameter call is a call of a function that is passed as a parameter to another function.
    E.g., def f(x):
                x()
    The call of x() is a parameter call only known at runtime.

    Attributes
    ----------
    expression : Expression
        The expression that is called.
    """

    expression: Expression

    def __hash__(self) -> int:
        return hash(str(self))


class Expression(ABC):  # noqa: B024 # this is just a base class, and it is important that it cannot be instantiated
    """Superclass for expressions.

    Expressions are used to represent code.
    """


@dataclass
class ParameterAccess(Expression):
    """Class for function parameter access.

    Attributes
    ----------
    parameter : Parameter
        The parameter that is accessed.
    """

    parameter: Parameter


@dataclass
class StringLiteral(Expression):
    """Class for string literals.

    Attributes
    ----------
    value : str
        The name of the string literal.
    """

    value: str


class OpenMode(Enum):
    """Enum for open modes.

    Attributes
    ----------
    READ : OpenMode
        Read mode.
    WRITE : OpenMode
        Write mode.
    READ_WRITE : OpenMode
        Read and write mode.
    """

    READ = auto()
    WRITE = auto()
    READ_WRITE = auto()
