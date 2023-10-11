from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto

import astroid

from library_analyzer.processing.api.purity_analysis.model._scope import NodeID


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

    # def __hash__(self) -> int:


@dataclass
class GlobalAccess(Expression):
    """Class for global variable access."""

    name: str
    module: str = "None"

    # def __hash__(self) -> int:


@dataclass
class ParameterAccess(Expression):
    """Class for function parameter access."""

    name: str
    function: str

    # def __hash__(self) -> int:


@dataclass
class InstanceAccess(Expression):
    """Class for field access of an instance attribute (receiver.target)."""

    receiver: Expression
    target: Expression

    # def __hash__(self) -> int:


@dataclass
class StringLiteral(Expression):
    value: str

    # def __hash__(self) -> int:


@dataclass
class Reference(Expression):
    name: str

    # def __hash__(self) -> int:


class ImpurityCertainty(Enum):
    DEFINITELY_PURE = auto()
    MAYBE_IMPURE = auto()
    DEFINITELY_IMPURE = auto()


# Reasons for impurity
class ImpurityIndicator(ABC):
    certainty: ImpurityCertainty

    # @abstractmethod
    # def __hash__(self) -> int:
    #     pass

    @abstractmethod
    def is_side_effect(self) -> bool:
        pass


@dataclass
class ConcreteImpurityIndicator(ImpurityIndicator):
    # def __hash__(self) -> int:

    def is_side_effect(self) -> bool:
        return False


@dataclass
class VariableRead(ImpurityIndicator):
    expression: Expression
    certainty = ImpurityCertainty.MAYBE_IMPURE

    # def __hash__(self) -> int:

    def is_side_effect(self) -> bool:
        return False


@dataclass
class VariableWrite(ImpurityIndicator):
    expression: Expression
    certainty = ImpurityCertainty.MAYBE_IMPURE

    # def __hash__(self) -> int:

    def is_side_effect(self) -> bool:
        return True


@dataclass
class FileRead(ImpurityIndicator):
    source: Expression
    certainty = ImpurityCertainty.DEFINITELY_IMPURE

    # def __hash__(self) -> int:

    def is_side_effect(self) -> bool:
        return False


@dataclass
class FileWrite(ImpurityIndicator):
    source: Expression
    certainty = ImpurityCertainty.DEFINITELY_IMPURE

    # def __hash__(self) -> int:

    def is_side_effect(self) -> bool:
        return True


@dataclass
class UnknownCallTarget(ImpurityIndicator):
    expression: Expression
    certainty = ImpurityCertainty.DEFINITELY_IMPURE

    # def __hash__(self) -> int:

    def is_side_effect(self) -> bool:
        return True  # TODO: improve this to make analysis more precise


@dataclass
class Call(ImpurityIndicator):
    expression: Expression
    certainty = ImpurityCertainty.DEFINITELY_IMPURE

    # def __hash__(self) -> int:

    def is_side_effect(self) -> bool:
        return True  # TODO: improve this to make analysis more precise


@dataclass
class SystemInteraction(ImpurityIndicator):
    certainty = ImpurityCertainty.DEFINITELY_IMPURE

    # def __hash__(self) -> int:

    def is_side_effect(self) -> bool:
        return True


@dataclass
class BuiltInFunction(ImpurityIndicator):
    """Class for built-in functions."""

    expression: Expression
    indicator: ImpurityIndicator  # this should be a list to handle multiple reasons
    certainty: ImpurityCertainty

    # def __hash__(self) -> int:

    def is_side_effect(self) -> bool:
        return False


class PurityResult(ABC):  # noqa: B024
    def __init__(self) -> None:
        self.reasons: list[ImpurityIndicator] = []


@dataclass
class DefinitelyPure(PurityResult):
    reasons: list = field(default_factory=list)


@dataclass
class MaybeImpure(PurityResult):
    reasons: list[ImpurityIndicator]

    # def __hash__(self) -> int:


@dataclass
class DefinitelyImpure(PurityResult):
    reasons: list[ImpurityIndicator]

    # def __hash__(self) -> int:


@dataclass
class PurityInformation:
    id: NodeID
    reasons: list[ImpurityIndicator]

    # def __hash__(self) -> int:

    # def __eq__(self, other: object) -> bool:
    #     if not isinstance(other, PurityInformation):

