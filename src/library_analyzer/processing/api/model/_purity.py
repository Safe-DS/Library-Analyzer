from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


# TODO each data model should have an unique ID,oo therefore we could possibly use the
#  function-/variable-/parameter-/etc.-name in combination with the line and column offset provided by astroid

# Type of access

class Expression(ABC):
    @abstractmethod
    def __hash__(self) -> int:
        pass

    @abstractmethod
    def is_reason_for_impurity(self) -> bool:
        pass  # TODO: check if this is correct
    ...


@dataclass
class AttributeAccess(Expression):
    """ Class for class attribute access """
    name: str

    def __hash__(self) -> int:
        return hash(self.name)

    def is_reason_for_impurity(self) -> bool:
        return False  # TODO: check if this is correct


@dataclass
class GlobalAccess(Expression):
    """ Class for global variable access"""
    name: str
    module: str = None

    def __hash__(self):
        return hash(self.name)

    def is_reason_for_impurity(self) -> bool:
        return True


@dataclass
class ParameterAccess(Expression):
    """ Class for function parameter access"""
    name: str
    function: str

    def __hash__(self):
        return hash(self.name)

    def is_reason_for_impurity(self) -> bool:
        return False


@dataclass
class InstanceAccess(Expression):
    """ Class for field access of an instance attribute (receiver.target)"""
    receiver: Expression
    target: Expression

    def __hash__(self):
        return hash((self.receiver, self.target))

    def is_reason_for_impurity(self) -> bool:
        return True  # TODO: check if this is correct


@dataclass
class StringLiteral(Expression):
    value: str

    def __hash__(self):
        return hash(self.value)

    def is_reason_for_impurity(self) -> bool:
        return True  # TODO: check if this is correct


# Reasons for impurity
class ImpurityReason(ABC):
    @abstractmethod
    def __hash__(self) -> int:
        pass

    @abstractmethod
    def is_reason_for_impurity(self) -> bool:
        pass


@dataclass
class VariableRead(ImpurityReason):
    expression: Expression

    def __hash__(self):
        return hash(self.expression)

    def is_reason_for_impurity(self) -> bool:
        return self.expression.is_reason_for_impurity()


@dataclass
class VariableWrite(ImpurityReason):
    expression: Expression

    def __hash__(self):
        return hash(self.expression)

    def is_reason_for_impurity(self) -> bool:
        return self.expression.is_reason_for_impurity()


@dataclass
class FileRead(ImpurityReason):
    path: Expression

    def __hash__(self):
        return hash(self.path)

    def is_reason_for_impurity(self) -> bool:
        return self.path.is_reason_for_impurity()


@dataclass
class FileWrite(ImpurityReason):
    path: Expression

    def __hash__(self):
        return hash(self.path)

    def is_reason_for_impurity(self) -> bool:
        return self.path.is_reason_for_impurity()


@dataclass
class UnknownCallTarget(ImpurityReason):
    expression: Expression

    def __hash__(self):
        return hash(self.expression)

    def is_reason_for_impurity(self) -> bool:
        return True  # TODO: improve this to make analysis more precise


@dataclass
class Call(ImpurityReason):
    expression: Expression

    def __hash__(self):
        return hash(self.expression)

    def is_reason_for_impurity(self) -> bool:
        return True  # TODO: improve this to make analysis more precise
