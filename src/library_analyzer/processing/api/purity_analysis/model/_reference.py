from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import astroid

from library_analyzer.processing.api.purity_analysis.model._module_data import (
    ClassScope,
    MemberAccessTarget,
    MemberAccessValue,
    NodeID,
    Reasons,
    Reference,
    Scope,
    Symbol,
)

if TYPE_CHECKING:
    from library_analyzer.processing.api.purity_analysis.model import CallGraphForest


@dataclass
class ReferenceNode(ABC):
    """Class for reference nodes.

    A reference node represents a reference to a list of its referenced symbols.


    Attributes
    ----------
    node : astroid.Name | astroid.AssignName | astroid.Call | MemberAccessTarget | MemberAccessValue
        The node that references the symbols.
    scope : Scope
        The scope of the node.
    referenced_symbols : list[Symbol]
        The list of referenced symbols.
        These are the symbols of the nodes that node references.
    """

    node: Symbol | Reference
    scope: Scope
    referenced_symbols: list[Symbol] = field(default_factory=list)

    def __repr__(self) -> str:
        if isinstance(self.node, astroid.Call):
            return f"{self.node.func.name}.line{self.node.lineno}"
        if isinstance(self.node, MemberAccessTarget | MemberAccessValue):
            return f"{self.node.name}.line{self.node.member.lineno}"
        return f"{self.node.name}.line{self.node.lineno}"


@dataclass
class TargetReference(ReferenceNode):
    """Class for target reference nodes.

    A TargetReference represents a reference from a target (=Symbol) to a list of Symbols.
    This is used to represent a Reference from a reassignment to the original assignment
    (or another previous assignment) of the same variable.
    """

    node: Symbol

    def __hash__(self) -> int:
        return hash(str(self))


@dataclass
class ValueReference(ReferenceNode):
    """Class for value reference nodes.

    A ValueReference represents a reference from a value to a list of Symbols.
    This is used to represent a Reference from a function call to the function definition.
    """

    node: Reference

    def __hash__(self) -> int:
        return hash(str(self))


@dataclass
class ModuleAnalysisResult:
    """Class for module analysis results.

    After the references of aaa module have been resolved, all necessary information for the purity analysis is available in this class.

    Attributes
    ----------
    resolved_references : dict[str, list[ReferenceNode]]
        The dictionary of references.
        The key is the name of the reference node, the value is the list of ReferenceNodes.
    raw_reasons : dict[NodeID, Reasons]
        The dictionary of function references.
        The key is the NodeID of the function, the value is the Reasons for the function.
    classes : dict[str, ClassScope]
        All classes and their ClassScope.
    call_graph : CallGraphForest
        The call graph forest of the module.
    """

    resolved_references: dict[str, list[ReferenceNode]]
    raw_reasons: dict[NodeID, Reasons]
    classes: dict[str, ClassScope]
    call_graph: CallGraphForest
