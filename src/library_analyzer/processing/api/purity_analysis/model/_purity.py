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
    Reference,
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

    is_class :
        Whether the result is for a class or not.
    """

    is_class: bool = False

    def __hash__(self) -> int:
        return hash(str(self))

    @abstractmethod
    def to_dict(self, shorten: bool = False) -> dict[str, Any]:
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
    is_class :
        Whether the result is for a class or not.
    """

    is_class: bool = False

    def update(self, other: PurityResult | None) -> PurityResult:
        """Update the current result with another result.

        Parameters
        ----------
        other :
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

    def to_dict(self, shorten: bool = False) -> dict[str, Any]:  # noqa: ARG002
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
    reasons :
        The reasons why the function is impure.
    is_class :
        Whether the result is for a class or not.
    """

    reasons: set[ImpurityReason]
    is_class: bool = False

    def update(self, other: PurityResult | None) -> PurityResult:
        """Update the current result with another result.

        Parameters
        ----------
        other :
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

    def to_dict(self, shorten: bool = False) -> dict[str, Any]:
        seen = set()
        non_local_variable_reads = []
        non_local_variable_writes = []
        file_reads = []
        file_writes = []
        unknown_calls = []
        native_calls = []
        parameter_calls = []
        for reason in self.reasons:
            if str(reason) not in seen:
                seen.add(str(reason))
                match reason:
                    case NonLocalVariableRead():
                        non_local_variable_reads.append(reason.to_dict())
                    case NonLocalVariableWrite():
                        non_local_variable_writes.append(reason.to_dict())
                    case FileRead():
                        file_reads.append(reason.to_dict())
                    case FileWrite():
                        file_writes.append(reason.to_dict())
                    case UnknownCall():
                        unknown_calls.append(reason.to_dict())
                    case NativeCall():
                        native_calls.append(reason.to_dict())
                    case CallOfParameter():
                        parameter_calls.append(reason.to_dict())
                    case _:
                        raise TypeError(f"Unknown reason type: {reason}")
        if not shorten:
            combined_reasons: dict[str, Any] = {
                "NonLocalVariableRead": non_local_variable_reads,
                "NonLocalVariableWrite": non_local_variable_writes,
                "FileRead": file_reads,
                "FileWrite": file_writes,
                "UnknownCall": unknown_calls,
                "NativeCall": native_calls,
                "CallOfParameter": parameter_calls,
            }
        else:
            combined_reasons = {
                "NonLocalVariableRead": len(non_local_variable_reads),
                "NonLocalVariableWrite": len(non_local_variable_writes),
                "FileRead": len(file_reads),
                "FileWrite": len(file_writes),
                "UnknownCall": len(unknown_calls),
                "NativeCall": len(native_calls),
                "CallOfParameter": len(parameter_calls),
            }
        return {
            "purity": self.__class__.__name__,
            "reasons": {reason: value for reason, value in combined_reasons.items() if value},
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
    symbol :
        The symbol that is read.
    origin :
        The origin of the read.
    """

    symbol: GlobalVariable | ClassVariable | InstanceVariable | Import | UnknownSymbol
    origin: Symbol | NodeID | None = field(default=None)

    def __hash__(self) -> int:
        return hash(str(self))

    def __str__(self) -> str:
        return f"{self.__class__.__name__}: {self.symbol.__class__.__name__}.{self.symbol.name}"

    def to_dict(self) -> dict[str, Any]:
        origin = (
            self.origin.id if isinstance(self.origin, Symbol) else (self.origin if self.origin is not None else None)
        )
        return {
            "origin": f"{origin}",
            "reason": f"{self.symbol.__class__.__name__}.{self.symbol.name}",
        }


@dataclass
class FileRead(Read):
    """Class for external variable reads (File / Database).

    Attributes
    ----------
    source :
        The source of the read.
    origin :
        The origin of the read.
    """

    source: Expression
    origin: Symbol | NodeID | None = field(default=None)

    def __hash__(self) -> int:
        return hash(str(self))

    def __str__(self) -> str:
        if isinstance(self.source, Expression):
            return f"{self.__class__.__name__}: {self.source.__str__()}"
        return f"{self.__class__.__name__}: UNKNOWN EXPRESSION"

    def to_dict(self) -> dict[str, Any]:
        origin = (
            self.origin.id if isinstance(self.origin, Symbol) else (self.origin if self.origin is not None else None)
        )
        return {
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
    symbol :
        The symbol that is written to.
    origin :
        The origin of the write.
    """

    symbol: GlobalVariable | ClassVariable | InstanceVariable | Import | UnknownSymbol
    origin: Symbol | NodeID | None = field(default=None)

    def __hash__(self) -> int:
        return hash(str(self))

    def __str__(self) -> str:
        return f"{self.__class__.__name__}: {self.symbol.__class__.__name__}.{self.symbol.name}"

    def to_dict(self) -> dict[str, Any]:
        origin = (
            self.origin.id if isinstance(self.origin, Symbol) else (self.origin if self.origin is not None else None)
        )
        return {
            "origin": f"{origin}",
            "reason": f"{self.symbol.__class__.__name__}.{self.symbol.name}",
        }


@dataclass
class FileWrite(Write):
    """Class for external variable writes (File / Database).

    Attributes
    ----------
    source :
        The source of the write.
    origin :
        The origin of the write.
    """

    source: Expression
    origin: Symbol | NodeID | None = field(default=None)

    def __hash__(self) -> int:
        return hash(str(self))

    def __str__(self) -> str:
        if isinstance(self.source, Expression):
            return f"{self.__class__.__name__}: {self.source.__str__()}"
        return f"{self.__class__.__name__}: UNKNOWN EXPRESSION"

    def to_dict(self) -> dict[str, Any]:
        origin = (
            self.origin.id if isinstance(self.origin, Symbol) else (self.origin if self.origin is not None else None)
        )
        return {
            "origin": f"{origin}",
            "reason": f"{self.source.__str__()}",
        }


class Unknown(ImpurityReason, ABC):
    """Superclass for unknown type impurity reasons."""


@dataclass
class UnknownProto(Unknown):
    """Class for UnknownCalls which are not fully determined.

    Attributes
    ----------
    symbol :
        The symbol or reference object which is not fully determined.
    origin :
        The origin of the unknown call.
    """

    symbol: Symbol | Reference
    origin: Symbol | NodeID | None = field(default=None)  # TODO: remove NodeID

    def __hash__(self) -> int:
        return hash(str(self))

    def __str__(self) -> str:
        return f"{self.__class__.__name__}: {self.symbol.__class__.__name__}.{self.symbol.name}"

    def to_dict(self) -> dict[str, Any]:
        origin = (
            self.origin.id if isinstance(self.origin, Symbol) else (self.origin if self.origin is not None else None)
        )
        return {
            "origin": f"{origin}",
            "reason": f"{self.symbol.name}",
        }


@dataclass
class UnknownCall(Unknown):
    """Class for calling unknown code.

    Since we cannot analyze unknown code, we mark it as unknown.

    Attributes
    ----------
    expression :
        The expression that is called.
    origin :
        The origin of the call.
    """

    expression: Expression
    origin: Symbol | NodeID | None = field(default=None)

    def __hash__(self) -> int:
        return hash(str(self))

    def __str__(self) -> str:
        return f"{self.__class__.__name__}: {self.expression.__str__()}"

    def to_dict(self) -> dict[str, Any]:
        origin = (
            self.origin.id if isinstance(self.origin, Symbol) else (self.origin if self.origin is not None else None)
        )
        return {
            "origin": f"{origin}",
            "reason": f"{self.expression.__str__()}",
        }


@dataclass
class NativeCall(Unknown):  # ExternalCall
    """Class for calling native code.

    Since we cannot analyze native code, we mark it as unknown.

    Attributes
    ----------
    expression :
        The expression that is called.
    origin :
        The origin of the call.
    """

    expression: Expression
    origin: Symbol | NodeID | None = field(default=None)

    def __hash__(self) -> int:
        return hash(str(self))

    def __str__(self) -> str:
        return f"{self.__class__.__name__}: {self.expression.__str__()}"

    def to_dict(self) -> dict[str, Any]:
        origin = (
            self.origin.id if isinstance(self.origin, Symbol) else (self.origin if self.origin is not None else None)
        )
        return {
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
    expression :
        The expression that is called.
    origin :
        The origin of the call.
    """

    expression: Expression
    origin: Symbol | NodeID | None = field(default=None)

    def __hash__(self) -> int:
        return hash(str(self))

    def __str__(self) -> str:
        return f"{self.__class__.__name__}: {self.expression.__str__()}"

    def to_dict(self) -> dict[str, Any]:
        origin = (
            self.origin.id if isinstance(self.origin, Symbol) else (self.origin if self.origin is not None else None)
        )
        return {
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
    parameter :
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
    value :
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
    call :
        The call node.
    inferred_def :
        The inferred function definition for the call if it is known.
    name :
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
    call :
        The call node.
    inferred_def :
        The inferred class definition for the call if it is known.
    name :
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

    def to_json_file(self, path: Path, shorten: bool = True) -> None:
        ensure_file_exists(path)
        with path.open("w") as f:
            json.dump(self.to_dict(shorten), f, indent=2)

    def to_dict(self, shorten: bool = False) -> dict[str, Any]:
        return {
            module_name.__str__(): {
                function_id.__str__(): purity.to_dict(shorten)
                for function_id, purity in purity_result.items()
                if not purity.is_class
            }
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
