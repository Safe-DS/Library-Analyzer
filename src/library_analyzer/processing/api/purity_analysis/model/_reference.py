from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import astroid

from library_analyzer.processing.api.purity_analysis.model._module_data import (
    ClassScope,
    FunctionScope,
    MemberAccessTarget,
    MemberAccessValue,
    NodeID,
    Reference,
    Scope,
    Symbol,
)

if TYPE_CHECKING:

    from library_analyzer.processing.api.purity_analysis.model import (
        CallGraphForest,
        NonLocalVariableRead,
        NonLocalVariableWrite,
        PurityResult,
        UnknownProto,
    )


@dataclass
class ReferenceNode(ABC):
    """Class for reference nodes.

    A reference node represents a reference to a list of its referenced symbols.


    Attributes
    ----------
    node :
        The node that references the symbols.
    scope :
        The scope of the node.
    referenced_symbols :
        The list of referenced symbols.
        These are the symbols of the nodes that node references.
    """

    node: Symbol | Reference
    scope: Scope
    referenced_symbols: list[Symbol] = field(default_factory=list)

    def __repr__(self) -> str:
        if isinstance(self.node, astroid.Call) and isinstance(self.node.func, astroid.Name):
            return f"{self.node.func.name}.line{self.node.lineno}"
        if isinstance(self.node, MemberAccessTarget | MemberAccessValue):
            return f"{self.node.name}.line{self.node.node.lineno}"
        return f"{self.node.name}.line{self.node.node.lineno}"


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
    This is used to represent a reference from a function call to the function definition.
    """

    node: Reference

    def __hash__(self) -> int:
        return hash(str(self))


@dataclass
class ModuleAnalysisResult:
    """Class for module analysis results.

    After the references of a module have been resolved, all necessary information for the purity analysis is available in this class.

    Attributes
    ----------
    resolved_references :
        The dictionary of references.
        The key is the name of the reference node, the value is the list of ReferenceNodes.
    raw_reasons :
        The dictionary of function references.
        The key is the NodeID of the function, the value is the Reasons for the function.
    classes :
        All classes and their ClassScope.
    call_graph_forest : CallGraphForest
        The call graph forest of the module.
    module_id :
        The NodeID of the module which the analysis result belongs to.
    """

    resolved_references: dict[str, list[ReferenceNode]] = field(default_factory=dict)
    raw_reasons: dict[NodeID, Reasons] = field(default_factory=dict)
    classes: dict[str, ClassScope] = field(default_factory=dict)
    call_graph_forest: CallGraphForest | None = None
    module_id: NodeID | None = None


@dataclass
class Reasons:
    """
    Represents a function and the raw reasons for impurity.

    Raw reasons means that the reasons are just collected and not yet processed.

    Attributes
    ----------
    function_scope :
        The scope of the function which the reasons belong to.
        Is None if the reasons are not for a FunctionDef node.
        This is the case when either a builtin or a combined node is created,
        or a ClassScope is used to propagate reasons.
    writes_to :
        A dict of all nodes that are written to.
    reads_from :
        A dict of all nodes that are read from.
    calls :
        A set of all nodes that are called.
    result :
        The result of the purity analysis
        This also works as a flag to determine if the purity analysis has already been performed:
        If it is None, the purity analysis has not been performed
    unknown_calls :
        A dict of all unknown calls.
        Unknown calls are calls to functions that are not defined in the module or are parameters.
    """

    id: NodeID
    function_scope: FunctionScope | None = field(default=None)
    writes_to: dict[NodeID, NonLocalVariableWrite] = field(default_factory=dict)
    reads_from: dict[NodeID, NonLocalVariableRead] = field(default_factory=dict)
    calls: set[Symbol] = field(default_factory=set)  # TODO: SORTED SET oder LIST
    result: PurityResult | None = field(default=None)
    unknown_calls: dict[NodeID, UnknownProto] = field(default_factory=dict)

    def join_reasons_list(self, reasons_list: list[Reasons]) -> Reasons:
        """Join a list of Reasons objects.

        Combines a list of Reasons objects into one Reasons object.

        Parameters
        ----------
        reasons_list :
            The list of Reasons objects.


        Returns
        -------
        Reasons
            The combined Reasons object.

        Raises
        ------
        ValueError
            If the list of Reasons objects is empty.
        """
        if not reasons_list:
            raise ValueError("List of Reasons is empty.")

        result = self
        for reason in reasons_list:
            result.join_reasons(reason)
        return result

    def join_reasons(self, other: Reasons) -> Reasons:
        """Join two Reasons objects.

        When a function has multiple reasons for impurity, the Reasons objects are joined.
        This means that the writes, reads, calls and unknown_calls are merged.

        Parameters
        ----------
        other :
            The other Reasons object.

        Returns
        -------
        Reasons
            The updated Reasons object.
        """
        self.writes_to.update(other.writes_to)
        self.reads_from.update(other.reads_from)
        self.calls.update(other.calls)
        self.unknown_calls.update(other.unknown_calls)

        return self

    def remove_unknown_call(self, node_id: NodeID) -> None:
        """Remove an unknown call from the reasons.

        Parameters
        ----------
        node_id :
            The NodeID of the unknown call to remove.
        """
        del self.unknown_calls[node_id]
