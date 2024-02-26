from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from library_analyzer.processing.api.purity_analysis.model._module_data import (
    ClassScope,
    FunctionScope,
    NodeID,
    Reference,
)

if TYPE_CHECKING:
    from library_analyzer.processing.api.purity_analysis.model._reference import Reasons


@dataclass
class CallGraphNode:
    """Class for call graph nodes.

    A call graph node represents a function in the call graph.

    Attributes
    ----------
    function : FunctionScope | ClassScope
        The function that the node represents.
        This is a ClassScope if the class has a __init__ method.
        In this case, the node is used for propagating the reasons of the
        __init__ method to function calling the class.
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

    function: FunctionScope | ClassScope
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
