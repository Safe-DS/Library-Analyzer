from __future__ import annotations

import json
import typing
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

import astroid

from library_analyzer.processing.api.purity_analysis.model._module_data import (
    MemberAccessValue,
    NodeID,
    Symbol,
    UnknownSymbol,
)
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

    is_class : bool
        Whether the result is for a class or not.
    """

    is_class: bool = False

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

    Attributes
    ----------
    is_class : bool
        Whether the result is for a class or not.
    """

    is_class: bool = False

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
            return self.clone()
        elif isinstance(self, Pure):
            if isinstance(other, Pure):
                return self.clone()
            elif isinstance(other, Impure):
                return other.clone()
        elif isinstance(self, Impure):
            if isinstance(other, Pure):
                return self.clone()
            elif isinstance(other, Impure):
                return Impure(reasons=self.reasons | other.reasons).clone()

        raise TypeError(f"Cannot update {self} with {other}")

    @staticmethod
    def clone() -> Pure:
        return Pure()

    def to_dict(self) -> dict[str, Any]:
        return {"purity": self.__class__.__name__}

    def __hash__(self) -> int:
        return hash(str(self))

    def __str__(self) -> str:
        return f"{self.__class__.__name__}"


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
    is_class : bool
        Whether the result is for a class or not.
    """

    reasons: set[ImpurityReason]
    is_class: bool = False

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
            return self.clone()
        elif isinstance(self, Pure):
            if isinstance(other, Pure):
                return self.clone()
            elif isinstance(other, Impure):
                return other.clone()
        elif isinstance(self, Impure):
            if isinstance(other, Pure):
                return self.clone()
            elif isinstance(other, Impure):
                return Impure(reasons=self.reasons | other.reasons).clone()
        raise TypeError(f"Cannot update {self} with {other}")

    def clone(self) -> Impure:
        return Impure(reasons=self.reasons.copy())

    def to_dict(self) -> dict[str, Any]:
        reasons = []
        seen = set()
        for reason in self.reasons:
            if str(reason) not in seen:
                reasons.append(reason.to_dict())
                seen.add(str(reason))

        return {
            "purity": self.__class__.__name__,
            "reasons": reasons,
        }

    def __hash__(self) -> int:
        return hash(str(self))

    def __str__(self) -> str:
        return f"{self.__class__.__name__}"


class ImpurityReason(ABC):  # this is just a base class, and it is important that it cannot be instantiated
    """Superclass for impurity reasons.

    If a function is impure it is because of one or more impurity reasons.
    """

    @abstractmethod
    def __str__(self) -> str:
        pass

    def __hash__(self) -> int:
        return hash(str(self))

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        pass

class Read(ImpurityReason, ABC):
    """Superclass for read type impurity reasons."""


@dataclass
class NonLocalVariableRead(Read):
    """Class for internal variable reads (GlobalVariable / global Fields).

    Attributes
    ----------
    symbol : GlobalVariable | ClassVariable | InstanceVariable | Import
        The symbol that is read.
    origin : Symbol | NodeID | None
        The origin of the read.
    """

    symbol: GlobalVariable | ClassVariable | InstanceVariable | Import | UnknownSymbol
    origin: Symbol | NodeID | None = field(default=None)

    def __hash__(self) -> int:
        return hash(str(self))

    def __str__(self) -> str:
        return f"{self.__class__.__name__}: {self.symbol.__class__.__name__}.{self.symbol.name}"

    def to_dict(self) -> dict[str, Any]:
        origin = self.origin.id if isinstance(self.origin, Symbol) else (self.origin if self.origin is not None else None)
        return {
            "result": f"{self.__class__.__name__}",
            "origin": f"{origin}",
            "reason": f"{self.symbol.__class__.__name__}.{self.symbol.name}",
        }


@dataclass
class FileRead(Read):
    """Class for external variable reads (File / Database).

    Attributes
    ----------
    source : Expression | None
        The source of the read.
        This is None if the source is unknown.
    origin : Symbol | NodeID | None
        The origin of the read.
    """

    source: Expression | None = None  # TODO: this should never be None
    origin: Symbol | NodeID | None = field(default=None)

    def __hash__(self) -> int:
        return hash(str(self))

    def __str__(self) -> str:
        if isinstance(self.source, Expression):
            return f"{self.__class__.__name__}: {self.source.__str__()}"
        return f"{self.__class__.__name__}: UNKNOWN EXPRESSION"

    def to_dict(self) -> dict[str, Any]:
        origin = self.origin.id if isinstance(self.origin, Symbol) else (self.origin if self.origin is not None else None)
        return {
            "result": f"{self.__class__.__name__}",
            "origin": f"{origin}",
            "reason": f"{self.source.__str__()}",
        }


class Write(ImpurityReason, ABC):
    """Superclass for write type impurity reasons."""


@dataclass
class NonLocalVariableWrite(Write):
    """Class for internal variable writes (GlobalVariable / global Fields).

    Attributes
    ----------
    symbol : GlobalVariable | ClassVariable | InstanceVariable | Import
        The symbol that is written to.
    origin : Symbol | NodeID | None
        The origin of the write.
    """

    symbol: GlobalVariable | ClassVariable | InstanceVariable | Import | UnknownSymbol
    origin: Symbol | NodeID | None = field(default=None)

    def __hash__(self) -> int:
        return hash(str(self))

    def __str__(self) -> str:
        return f"{self.__class__.__name__}: {self.symbol.__class__.__name__}.{self.symbol.name}"

    def to_dict(self) -> dict[str, Any]:
        origin = self.origin.id if isinstance(self.origin, Symbol) else (self.origin if self.origin is not None else None)
        return {
            "result": f"{self.__class__.__name__}",
            "origin": f"{origin}",
            "reason": f"{self.symbol.__class__.__name__}.{self.symbol.name}",
        }


@dataclass
class FileWrite(Write):
    """Class for external variable writes (File / Database).

    Attributes
    ----------
    source : Expression | None
        The source of the write.
        This is None if the source is unknown.  # TODO: see above LARS
    origin : Symbol | NodeID | None
        The origin of the write.
    """

    source: Expression | None = None
    origin: Symbol | NodeID | None = field(default=None)

    def __hash__(self) -> int:
        return hash(str(self))

    def __str__(self) -> str:
        if isinstance(self.source, Expression):
            return f"{self.__class__.__name__}: {self.source.__str__()}"
        return f"{self.__class__.__name__}: UNKNOWN EXPRESSION"

    def to_dict(self) -> dict[str, Any]:
        origin = self.origin.id if isinstance(self.origin, Symbol) else (self.origin if self.origin is not None else None)
        return {
            "result": f"{self.__class__.__name__}",
            "origin": f"{origin}",
            "reason": f"{self.source.__str__()}",
        }


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
    origin : Symbol | NodeID | None
        The origin of the call.
    """

    expression: Expression
    origin: Symbol | NodeID | None = field(default=None)

    def __hash__(self) -> int:
        return hash(str(self))

    def __str__(self) -> str:
        return f"{self.__class__.__name__}: {self.expression.__str__()}"

    def to_dict(self) -> dict[str, Any]:
        origin = self.origin.id if isinstance(self.origin, Symbol) else (self.origin if self.origin is not None else None)
        return {
            "result": f"{self.__class__.__name__}",
            "origin": f"{origin}",
            "reason": f"{self.expression.__str__()}",
        }


@dataclass
class NativeCall(Unknown):  # ExternalCall
    """Class for calling native code.

    Since we cannot analyze native code, we mark it as unknown.

    Attributes
    ----------
    expression : Expression
        The expression that is called.
    origin : Symbol | NodeID | None
        The origin of the call.
    """

    expression: Expression
    origin: Symbol | NodeID | None = field(default=None)

    def __hash__(self) -> int:
        return hash(str(self))

    def __str__(self) -> str:
        return f"{self.__class__.__name__}: {self.expression.__str__()}"

    def to_dict(self) -> dict[str, Any]:
        origin = self.origin.id if isinstance(self.origin, Symbol) else (self.origin if self.origin is not None else None)
        return {
            "result": f"{self.__class__.__name__}",
            "origin": f"{origin}",
            "reason": f"{self.expression.__str__()}",
        }

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
    origin : Symbol | NodeID | None
        The origin of the call.
    """

    expression: Expression
    origin: Symbol | NodeID | None = field(default=None)

    def __hash__(self) -> int:
        return hash(str(self))

    def __str__(self) -> str:
        return f"{self.__class__.__name__}: {self.expression.__str__()}"

    def to_dict(self) -> dict[str, Any]:
        origin = self.origin.id if isinstance(self.origin, Symbol) else (self.origin if self.origin is not None else None)
        return {
            "result": f"{self.__class__.__name__}",
            "origin": f"{origin}",
            "reason": f"{self.expression.__str__()}",
        }


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
            return f"{self.__class__.__name__}.{self.parameter}"
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

    call: astroid.Call | None = None
    inferred_def: astroid.FunctionDef | None = None
    name: str = field(init=False)

    def __post_init__(self) -> None:
        if self.inferred_def is not None:
            self.name = f"{self.inferred_def.root().name}.{self.inferred_def.name}"
        elif self.call is None:
            self.name = "UNKNOWN"
        elif isinstance(self.call, MemberAccessValue):
            self.name = self.call.name
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
    purity_results : dict[NodeID, dict[NodeID, PurityResult]]
        The purity results of all functions of the API.
        The key is the NodeID of the module,
        the value is a dictionary of the purity results of the functions in the module.
    """

    purity_results: typing.ClassVar[dict[NodeID, dict[NodeID, PurityResult]]] = {}

    def to_json_file(self, path: Path) -> None:
        ensure_file_exists(path)
        with path.open("w") as f:
            json.dump(self.to_dict(), f, indent=2)

    def to_dict(self) -> dict[str, Any]:
        return {
            module_name.__str__(): {function_id.__str__(): purity.to_dict()
                                    for function_id, purity in purity_result.items() if not purity.is_class}
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
