from __future__ import annotations

import json
import typing
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

import astroid

from library_analyzer.utils import ensure_file_exists

if TYPE_CHECKING:
    from pathlib import Path

    from library_analyzer.processing.api.purity_analysis.model import (
        ClassVariable,
        GlobalVariable,
        Import,
        InstanceVariable,
        Parameter,
    )


class PurityResult(ABC):
    """Superclass for purity results.

    Purity results are either pure, impure or unknown.
    """

    def __hash__(self) -> int:
        return hash(str(self))

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        pass

    @abstractmethod
    def update(self, other: PurityResult | None) -> PurityResult:
        """Update the current result with another result."""


@dataclass
class Pure(PurityResult):
    """Class for pure results.

    A function is pure if it has no (External-, Internal-)Read nor (External-, Internal-)Write side effects.
    A pure function must also have no unknown reasons.
    """

    def update(self, other: PurityResult | None) -> PurityResult:
        """Update the current result with another result.

        Parameters
        ----------
        other : PurityResult | None
            The result to update with.

        Returns
        -------
        PurityResult
            The updated result.

        Raises
        ------
        TypeError
            If the result cannot be updated with the given result.
        """
        if other is None:
            return self
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

        raise TypeError(f"Cannot update {self} with {other}")

    def to_dict(self) -> dict[str, Any]:
        return {"purity": self.__class__.__name__}


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

        Parameters
        ----------
        other : PurityResult | None
            The result to update with.

        Returns
        -------
        PurityResult
            The updated result.

        Raises
        ------
        TypeError
            If the result cannot be updated with the given result.
        """
        if other is None:
            return self
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
        raise TypeError(f"Cannot update {self} with {other}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "purity": self.__class__.__name__,
            "reasons": [reason.__str__() for reason in self.reasons],
        }


class ImpurityReason(ABC):  # this is just a base class, and it is important that it cannot be instantiated
    """Superclass for impurity reasons.

    If a function is impure it is because of one or more impurity reasons.
    """

    # TODO:
    # origin
    # neighbor

    @abstractmethod
    def __str__(self) -> str:
        pass

    def __hash__(self) -> int:
        return hash(str(self))


class Read(ImpurityReason, ABC):
    """Superclass for read type impurity reasons."""


@dataclass
class NonLocalVariableRead(Read):
    """Class for internal variable reads (GlobalVariable / global Fields).

    Attributes
    ----------
    symbol : GlobalVariable | ClassVariable | InstanceVariable | Import
        The symbol that is read.
    """

    symbol: GlobalVariable | ClassVariable | InstanceVariable | Import

    def __hash__(self) -> int:
        return hash(str(self))

    def __str__(self) -> str:
        return f"{self.__class__.__name__}: {self.symbol.__class__.__name__}.{self.symbol.name}"


@dataclass
class FileRead(Read):
    """Class for external variable reads (File / Database).

    Attributes
    ----------
    source : Expression | None
        The source of the read.
        This is None if the source is unknown.
    """

    source: Expression | None = None  # TODO: this should never be None

    def __hash__(self) -> int:
        return hash(str(self))

    def __str__(self) -> str:
        if isinstance(self.source, Expression):
            return f"{self.__class__.__name__}: {self.source.__str__()}"
        return f"{self.__class__.__name__}: UNKNOWN EXPRESSION"


class Write(ImpurityReason, ABC):
    """Superclass for write type impurity reasons."""


@dataclass
class NonLocalVariableWrite(Write):
    """Class for internal variable writes (GlobalVariable / global Fields).

    Attributes
    ----------
    symbol : GlobalVariable | ClassVariable | InstanceVariable | Import
        The symbol that is written to.
    """

    symbol: GlobalVariable | ClassVariable | InstanceVariable | Import

    def __hash__(self) -> int:
        return hash(str(self))

    def __str__(self) -> str:
        return f"{self.__class__.__name__}: {self.symbol.__class__.__name__}.{self.symbol.name}"


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

    def __str__(self) -> str:
        if isinstance(self.source, Expression):
            return f"{self.__class__.__name__}: {self.source.__str__()}"
        return f"{self.__class__.__name__}: UNKNOWN EXPRESSION"


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

    def __str__(self) -> str:
        return f"{self.__class__.__name__}: {self.expression.__str__()}"


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

    def __str__(self) -> str:
        return f"{self.__class__.__name__}: {self.expression.__str__()}"


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

    def __str__(self) -> str:
        return f"{self.__class__.__name__}: {self.expression.__str__()}"


class Expression(ABC):  # this is just a base class, and it is important that it cannot be instantiated
    """Superclass for expressions.

    Expressions are used to represent code.
    """

    @abstractmethod
    def __str__(self) -> str:
        pass


@dataclass
class ParameterAccess(Expression):
    """Class for function parameter access.

    Attributes
    ----------
    parameter : Parameter
        The parameter that is accessed.
    """

    parameter: Parameter

    def __str__(self) -> str:
        if isinstance(self.parameter, str):
            return self.parameter
        return f"{self.__class__.__name__}.{self.parameter.name}"


@dataclass
class StringLiteral(Expression):
    """Class for string literals.

    Attributes
    ----------
    value : str
        The name of the string literal.
    """

    value: str

    def __str__(self) -> str:
        return f"StringLiteral.{self.value}"


@dataclass
class UnknownFunctionCall(Expression):
    """Class for unknown function calls.

    Attributes
    ----------
    call : astroid.Call
        The call node.
    inferred_def : astroid.FunctionDef | None
        The inferred function definition for the call if it is known.
    name : str
        The name of the call.
    """

    call: astroid.Call
    inferred_def: astroid.FunctionDef | None = None
    name: str = field(init=False)

    def __post_init__(self) -> None:
        if self.inferred_def is not None:
            self.name = f"{self.inferred_def.root().name}.{self.inferred_def.name}"
        elif isinstance(self.call.func, astroid.Attribute):
            self.name = self.call.func.attrname
        elif isinstance(self.call.func, astroid.Name):
            self.name = self.call.func.name
        else:
            self.name = "UNKNOWN"

    def __str__(self) -> str:
        return f"{self.__class__.__name__}.{self.name}"


@dataclass
class UnknownClassInit(Expression):
    """Class for unknown class initializations.

    Attributes
    ----------
    call : astroid.Call
        The call node.
    inferred_def : astroid.ClassDef | None
        The inferred class definition for the call if it is known.
    name : str
        The name of the call.
    """

    call: astroid.Call
    inferred_def: astroid.ClassDef | None = None
    name: str = field(init=False)

    def __post_init__(self) -> None:
        if self.inferred_def is not None:
            self.name = f"{self.inferred_def.root().name}.{self.inferred_def.name}"
        elif isinstance(self.call.func, astroid.Attribute):
            self.name = self.call.func.attrname
        else:
            self.name = self.call.func.name

    def __str__(self) -> str:
        return f"{self.__class__.__name__}.{self.name}"


class APIPurity:
    """Class for API purity.

    The API purity is used to represent the purity result of an API.

    Attributes
    ----------
    purity_results : dict[str, dict[str, PurityResult]]
        The purity results of the API.
        The first key is the name of the module, and the second key is the function id.
    """

    purity_results: typing.ClassVar[dict[str, dict[str, PurityResult]]] = {}

    def to_json_file(self, path: Path) -> None:
        ensure_file_exists(path)
        with path.open("w") as f:
            json.dump(self.to_dict(), f, indent=2)

    def to_dict(self) -> dict[str, Any]:
        return {
            module_name: {function_def: purity.to_dict() for function_def, purity in purity_result.items()}
            for module_name, purity_result in self.purity_results.items()
        }


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
