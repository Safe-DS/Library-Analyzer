from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

import astroid

# for testing purposes only
# __y = 42
# __version__ = "0.1.0"
# x = "rest"
# y = 23
# y = 34


# Type of access
class Expression(astroid.NodeNG, ABC):
    # @abstractmethod
    # def __hash__(self) -> int:
    #    pass
    ...


@dataclass
class AttributeAccess(Expression):
    """Class for class attribute access"""

    name: str

    # def __hash__(self) -> int:
    #    return hash(self.name)


@dataclass
class GlobalAccess(Expression):
    """Class for global variable access"""

    name: str
    module: str = "None"

    # def __hash__(self) -> int:
    #    return hash(self.name)


@dataclass
class ParameterAccess(Expression):
    """Class for function parameter access"""

    parameter: str
    function: str

    # def __hash__(self) -> int:
    #    return hash(self.name)


@dataclass
class InstanceAccess(Expression):
    """Class for field access of an instance attribute (receiver.target)"""

    receiver: Expression
    target: Expression

    # def __hash__(self) -> int:
    #   return hash((self.receiver, self.target))


@dataclass
class StringLiteral(Expression):
    value: str

    # def __hash__(self) -> int:
    #    return hash(self.value)


@dataclass
class Reference(Expression):
    name: str
    expression: Optional[Expression] = None

    # def __hash__(self) -> int:
    #     return hash(self.name)


class ImpurityCertainty(Enum):
    DEFINITELY_PURE = auto()
    MAYBE_IMPURE = auto()
    DEFINITELY_IMPURE = auto()


# Reasons for impurity
class IntraProceduralDataFlow(ABC):
    certainty: ImpurityCertainty

    # @abstractmethod
    # def __hash__(self) -> int:
    #     pass

    @abstractmethod
    def is_side_effect(self) -> bool:
        pass


@dataclass
class ConcreteIntraProceduralDataFlow(IntraProceduralDataFlow):
    # def __hash__(self) -> int:
    #     return hash(self.certainty)

    def is_side_effect(self) -> bool:
        return False


@dataclass
class VariableRead(IntraProceduralDataFlow):
    expression: Expression
    certainty = ImpurityCertainty.MAYBE_IMPURE

    # def __hash__(self) -> int:
    #     return hash(self.expression)

    def is_side_effect(self) -> bool:
        return False


@dataclass
class VariableWrite(IntraProceduralDataFlow):
    expression: Expression
    certainty = ImpurityCertainty.MAYBE_IMPURE

    # def __hash__(self) -> int:
    #     return hash(self.expression)

    def is_side_effect(self) -> bool:
        return True


@dataclass
class FileRead(IntraProceduralDataFlow):
    source: Expression
    certainty = ImpurityCertainty.DEFINITELY_IMPURE

    # def __hash__(self) -> int:
    #     return hash(self.source)

    def is_side_effect(self) -> bool:
        return False


@dataclass
class FileWrite(IntraProceduralDataFlow):
    source: Expression
    certainty = ImpurityCertainty.DEFINITELY_IMPURE

    # def __hash__(self) -> int:
    #     return hash(self.source)

    def is_side_effect(self) -> bool:
        return True


@dataclass
class UnknownCallTarget(IntraProceduralDataFlow):
    expression: Expression
    certainty = ImpurityCertainty.DEFINITELY_IMPURE

    # def __hash__(self) -> int:
    #     return hash(self.expression)

    def is_side_effect(self) -> bool:
        return True  # TODO: improve this to make analysis more precise


@dataclass
class Call(IntraProceduralDataFlow):
    expression: Expression
    # TODO: add the arguments to better display dependencies in a call
    # callee: Expression
    # arguments: list[Expression]
    certainty = ImpurityCertainty.DEFINITELY_IMPURE

    # def __hash__(self) -> int:
    #     return hash(self.expression)

    def is_side_effect(self) -> bool:
        return True  # TODO: improve this to make analysis more precise


@dataclass
class SystemInteraction(IntraProceduralDataFlow):
    certainty = ImpurityCertainty.DEFINITELY_IMPURE

    # def __hash__(self) -> int:
    #     return hash("SystemInteraction")

    def is_side_effect(self) -> bool:
        return True


@dataclass
class BuiltInFunction(IntraProceduralDataFlow):
    """Class for built-in functions"""

    expression: Expression
    indicator: IntraProceduralDataFlow  # this should be a list to handle multiple reasons
    certainty: ImpurityCertainty

    # def __hash__(self) -> int:
    #     return hash(self.indicator)

    def is_side_effect(self) -> bool:
        return False
