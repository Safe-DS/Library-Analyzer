from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field

import astroid

from library_analyzer.processing.api.purity_analysis.model._scope import (
    ClassScope,
    FunctionScope,
    MemberAccessTarget,
    MemberAccessValue,
    NodeID,
    Reasons,
    Reference,
    Scope,
    Symbol,
)


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
class CallGraphNode:
    """Class for call graph nodes.

    A call graph node represents a function in the call graph.

    Attributes
    ----------
    function : FunctionScope | ClassScope | Reference
        The function that the node represents.
        This is a FunctionScope if we deal with a function,
        a ClassScope if we deal with a class initialization,
        and a Reference if we deal with a builtin function.
    reasons : Reasons
        The raw Reasons for the node.
    children : set[CallGraphNode]
        The set of children of the node, (i.e., the set of nodes that this node calls)
    combined_node_names : list[str]
        A list of the names of all nodes that are combined into this node.
        This is only set if the node is a combined node.
        This is later used for transferring the reasons of the combined node to the original nodes.
    is_builtin : bool
        True if the function is a builtin function, False otherwise.
    """

    function: FunctionScope | ClassScope | Reference
    reasons: Reasons
    children: set[CallGraphNode] = field(default_factory=set)
    combined_node_names: list[str] = field(default_factory=list)
    is_builtin: bool = False

    def __hash__(self) -> int:
        return hash(str(self))

    def __repr__(self) -> str:
        if isinstance(self.function, FunctionScope | ClassScope):
            return f"{self.function.symbol.id}"
        if isinstance(self.function, Reference):
            return f"{self.function.id}"
        return f"{self.function}"

    def add_child(self, child: CallGraphNode) -> None:
        """Add a child to the node.

        Parameters
        ----------
        child : CallGraphNode
            The child to add.
        """
        self.children.add(child)

    def is_leaf(self) -> bool:
        """Check if the node is a leaf node.

        Returns
        -------
        bool
            True if the node is a leaf node, False otherwise.
        """
        return len(self.children) == 0


@dataclass
class CallGraphForest:
    """Class for call graph forests.

    A call graph forest represents a collection of call graph trees.

    Attributes
    ----------
    graphs : dict[str, CallGraphNode]
        The dictionary of call graph trees.
        The key is the name of the tree, the value is the root CallGraphNode of the tree.
    """

    graphs: dict[NodeID, CallGraphNode] = field(default_factory=dict)

    def add_graph(self, graph_id: NodeID, graph: CallGraphNode) -> None:
        """Add a call graph tree to the forest.

        Parameters
        ----------
        graph_id : NodeID
            The NodeID of the tree node.
        graph : CallGraphNode
            The root of the tree.
        """
        self.graphs[graph_id] = graph

    def get_graph(self, graph_id: NodeID) -> CallGraphNode:  # type: ignore[return] # see TODO below
        """Get a call graph tree from the forest.

        Parameters
        ----------
        graph_id : NodeID
            The NodeID of the tree node to get.

        Returns
        -------
        CallGraphNode
            The CallGraphNode that is the root of the tree.
        """
        try:
            return self.graphs[graph_id]
        except KeyError:
            pass  # TODO: this is not a good idea, but it works -  LARS how to change this?

    def delete_graph(self, graph_id: NodeID) -> None:
        """Delete a call graph tree from the forest.

        Parameters
        ----------
        graph_id : NodeID
            The NodeID of the tree to delete.
        """
        del self.graphs[graph_id]


@dataclass
class ModuleAnalysisResult:
    """Class for module analysis results.

    After the references of aaa module have been resolved, all necessary information for the purity analysis is available in this class.

    Attributes
    ----------
    resolved_references : dict[str, list[ReferenceNode]]
        The dictionary of references.
        The key is the name of the reference node, the value is the list of ReferenceNodes.
    function_references : dict[NodeID, Reasons]
        The dictionary of function references.
        The key is the NodeID of the function, the value is the Reasons for the function.
    classes : dict[str, ClassScope]
        All classes and their ClassScope.
    call_graph : CallGraphForest
        The call graph forest of the module.
    """

    resolved_references: dict[str, list[ReferenceNode]]
    function_references: dict[NodeID, Reasons]
    classes: dict[str, ClassScope]
    call_graph: CallGraphForest
