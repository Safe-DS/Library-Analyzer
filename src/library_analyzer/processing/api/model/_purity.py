from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto


# TODO each data model should have an unique ID,oo therefore we could possibly use the
#  function-/variable-/parameter-/etc.-name in combination with the line and column offset provided by astroid

# Type of access

class Expression(ABC):
    @abstractmethod
    def __hash__(self) -> int:
        pass


@dataclass
class AttributeAccess(Expression):
    """ Class for class attribute access """
    name: str

    def __hash__(self) -> int:
        return hash(self.name)


@dataclass
class GlobalAccess(Expression):
    """ Class for global variable access"""
    name: str
    module: str = None

    def __hash__(self):
        return hash(self.name)


@dataclass
class ParameterAccess(Expression):
    """ Class for function parameter access"""
    name: str
    function: str

    def __hash__(self):
        return hash(self.name)


@dataclass
class InstanceAccess(Expression):
    """ Class for field access of an instance attribute (receiver.target)"""
    receiver: Expression
    target: Expression

    def __hash__(self):
        return hash((self.receiver, self.target))


@dataclass
class StringLiteral(Expression):
    value: str

    def __hash__(self):
        return hash(self.value)


class ImpurityCertainty(Enum):
    maybe = auto()
    definitely = auto()


# Reasons for impurity
class ImpurityIndicator(ABC):
    certainty: ImpurityCertainty

    @abstractmethod
    def __hash__(self) -> int:
        pass

    @abstractmethod
    def is_side_effect(self) -> bool:
        pass


@dataclass
class VariableRead(ImpurityIndicator):
    expression: Expression
    certainty = ImpurityCertainty.maybe

    def __hash__(self):
        return hash(self.expression)

    def is_side_effect(self) -> bool:
        return False


@dataclass
class VariableWrite(ImpurityIndicator):
    expression: Expression
    certainty = ImpurityCertainty.maybe

    def __hash__(self):
        return hash(self.expression)

    def is_side_effect(self) -> bool:
        return True


@dataclass
class FileRead(ImpurityIndicator):
    path: Expression
    certainty = ImpurityCertainty.definitely

    def __hash__(self):
        return hash(self.path)

    def is_side_effect(self) -> bool:
        return False


@dataclass
class FileWrite(ImpurityIndicator):
    path: Expression
    certainty = ImpurityCertainty.definitely

    def __hash__(self):
        return hash(self.path)

    def is_side_effect(self) -> bool:
        return True


@dataclass
class UnknownCallTarget(ImpurityIndicator):
    expression: Expression
    certainty = ImpurityCertainty.definitely

    def __hash__(self):
        return hash(self.expression)

    def is_side_effect(self) -> bool:
        return True  # TODO: improve this to make analysis more precise


@dataclass
class Call(ImpurityIndicator):
    expression: Expression
    certainty = ImpurityCertainty

    def __hash__(self):
        return hash(self.expression)

    def is_side_effect(self) -> bool:
        return True  # TODO: improve this to make analysis more precise
