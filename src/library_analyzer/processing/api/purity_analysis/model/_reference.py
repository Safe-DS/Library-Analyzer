from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, TypeVar

import astroid

from library_analyzer.processing.api.purity_analysis.model._scope import (
    FunctionScope,
    MemberAccessTarget,
    MemberAccessValue,
    Reasons,
    Scope,
    Symbol,
)


@dataclass
class ReferenceNode:
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

    node: astroid.Name | astroid.AssignName | astroid.Call | MemberAccessTarget | MemberAccessValue
    scope: Scope
    referenced_symbols: list[Symbol] = field(default_factory=list)

    def __repr__(self) -> str:
        if isinstance(self.node, astroid.Call):
            return f"{self.node.func.name}.line{self.node.lineno}"
        if isinstance(self.node, MemberAccessTarget | MemberAccessValue):
            return f"{self.node.name}.line{self.node.member.lineno}"
        return f"{self.node.name}.line{self.node.lineno}"


_T = TypeVar("_T")


@dataclass
class CallGraphNode(Generic[_T]):
    """Class for call graph nodes.

    A call graph node represents a function call.

    Attributes
    ----------
    data : _T
        The data of the node.
        This is normally a FunctionScope but can be any type.
    reasons : Reasons
        The raw Reasons for the node.
    children : set[CallGraphNode]
        The set of children of the node, (i.e., the set of nodes that this node calls)
    combined_node_names : list[str]
        A list of the names of all nodes that are combined into this node.
        This is only set if the node is a combined node.
        This is later used for transferring the reasons of the combined node to the original nodes.
    """

    data: _T
    reasons: Reasons
    children: set[CallGraphNode] = field(default_factory=set)
    combined_node_names: list[str] = field(default_factory=list)

    def __hash__(self) -> int:
        return hash(str(self))

    def __repr__(self) -> str:
        if isinstance(self.data, FunctionScope):
            return f"{self.data.symbol.name}"
        return f"{self.data}"

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

    graphs: dict[str, CallGraphNode] = field(default_factory=dict)

    def add_graph(self, graph_name: str, graph: CallGraphNode) -> None:
        """Add a call graph tree to the forest.

        Parameters
        ----------
        graph_name : str
            The name of the tree.
        graph : CallGraphNode
            The root of the tree.
        """
        self.graphs[graph_name] = graph

    def get_graph(self, graph_name: str) -> CallGraphNode:  # type: ignore[return] # see TODO below
        """Get a call graph tree from the forest.

        Parameters
        ----------
        graph_name : str
            The name of the tree to get.

        Returns
        -------
        CallGraphNode
            The CallGraphNode that is the root of the tree.
        """
        try:
            return self.graphs[graph_name]
        except KeyError:
            pass  # TODO: this is not a good idea, but it works -  LARS how to change this?

    def delete_graph(self, graph_name: str) -> None:
        """Delete a call graph tree from the forest.

        Parameters
        ----------
        graph_name : str
            The name of the tree to delete.
        """
        del self.graphs[graph_name]
