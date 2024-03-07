from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from library_analyzer.processing.api.purity_analysis.model._module_data import (
        Import,
        NodeID,
        Symbol,
    )
    from library_analyzer.processing.api.purity_analysis.model._reference import Reasons


# @dataclass
# class CallGraphNode:
#     """Class for call graph nodes.
#
#     A call graph node represents a function in the call graph.
#
#     Attributes
#     ----------
#     scope : FunctionScope | ClassScope
#         The function that the node represents.
#         This is a ClassScope if the class has a __init__ method.
#         In this case, the node is used for propagating the reasons of the
#         __init__ method to function calling the class.
#     reasons : Reasons
#         The raw Reasons for the node.
#     children : set[CallGraphNode]
#         The set of children of the node, (i.e., the set of nodes that this node calls)
#     combined_node_ids : list[NodeID]
#         A list of the names of all nodes that are combined into this node.
#         This is only set if the node is a combined node.
#         This is later used for transferring the reasons of the combined node to the original nodes.
#     is_builtin : bool
#         True if the function is a builtin function, False otherwise.
#     """
#
#     scope: FunctionScope | ClassScope  # TODO: change to symbol
#     reasons: (
#         Reasons  # TODO: remove calls from reasons after they were added to the call graph (except for unknown calls)
#     )
#     children: set[CallGraphNode] = field(default_factory=set)
#     combined_node_ids: list[NodeID] = field(default_factory=list)
#     is_builtin: bool = False
#
#     def __hash__(self) -> int:
#         return hash(str(self))
#
#     def __repr__(self) -> str:
#         return f"{self.scope.symbol.id}"
#
#     def add_child(self, child: CallGraphNode) -> None:
#         """Add a child to the node.
#
#         Parameters
#         ----------
#         child : CallGraphNode
#             The child to add.
#         """
#         self.children.add(child)
#
#     def is_leaf(self) -> bool:
#         """Check if the node is a leaf node.
#
#         Returns
#         -------
#         bool
#             True if the node is a leaf node, False otherwise.
#         """
#         return len(self.children) == 0
#
#     def combined_node_id_to_string(self) -> list[str]:
#         """Return the combined node IDs as a string.
#
#         Returns
#         -------
#         str
#             The combined node IDs as a string.
#         """
#         return [str(node_id) for node_id in self.combined_node_ids]


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
        # if graph_id in self.forest:
        #     raise ValueError(f"Graph with id {graph_id} already exists inside the call graph.")
        self.graphs[graph_id] = graph

    def get_graph(self, graph_id: NodeID) -> CallGraphNode:
        """Get a call graph tree from the forest.

        Parameters
        ----------
        graph_id : NodeID
            The NodeID of the tree node to get.

        Raises
        ------
        KeyError
            If the graph_id is not in the forest.
        """
        result = self.graphs.get(graph_id)
        if result is None:
            raise KeyError(f"Graph with id {graph_id} not found inside the call graph.")
        return result

    def has_graph(self, graph_id: NodeID) -> bool:
        """Check if the forest contains a call graph tree with the given NodeID.

        Parameters
        ----------
        graph_id : NodeID
            The NodeID of the tree to check for.

        Returns
        -------
        bool
            True if the forest contains a tree with the given NodeID, False otherwise.
        """
        return graph_id in self.graphs

    def delete_graph(self, graph_id: NodeID) -> None:
        """Delete a call graph tree from the forest.

        Parameters
        ----------
        graph_id : NodeID
            The NodeID of the tree to delete.
        """
        del self.graphs[graph_id]


@dataclass
class CallGraphNode:
    """Class for call graph nodes.

    A call graph node represents a function in the call graph.

    Attributes
    ----------
    symbol : Symbol
        The symbol of the function that the node represents.
    reasons : Reasons
        The raw Reasons for the node.
        After the call graph is built, this only contains reads_from and writes_to as well as unknown_calls.
    children : dict[NodeID, CallGraphNode]
        The set of children of the node, (i.e., the set of nodes that this node calls)
    """

    symbol: Symbol
    reasons: Reasons
    children: dict[NodeID, CallGraphNode] = field(default_factory=dict)

    def __hash__(self) -> int:
        return hash(str(self))

    def __str__(self) -> str:
        return f"{self.symbol.id}"

    def __repr__(self) -> str:
        return f"{self.symbol.name}: {id(self)}"

    def add_child(self, child: CallGraphNode) -> None:
        """Add a child to the node.

        Parameters
        ----------
        child : CallGraphNode
            The child to add.
        """
        self.children[child.symbol.id] = child

    def get_child(self, child_id: NodeID) -> CallGraphNode:
        """Get a child from the node.

        Parameters
        ----------
        child_id : NodeID
            The NodeID of the child to get.

        Raises
        ------
        KeyError
            If the child_id is not in the children.
        """
        result = self.children.get(child_id)
        if result is None:
            raise KeyError(f"Child with id {child_id} not found inside the call graph.")
        return result

    def has_child(self, child_id: NodeID) -> bool:
        """Check if the node has a child with the given NodeID.

        Parameters
        ----------
        child_id : NodeID
            The NodeID of the child to check for.

        Returns
        -------
        bool
            True if the node has a child with the given NodeID, False otherwise.
        """
        return child_id in self.children

    def delete_child(self, child_id: NodeID) -> None:
        """Delete a child from the node.

        Parameters
        ----------
        child_id : NodeID
            The NodeID of the child to delete.
        """
        del self.children[child_id]

    def is_leaf(self) -> bool:
        """Check if the node is a leaf node.

        Returns
        -------
        bool
            True if the node is a leaf node, False otherwise.
        """
        return len(self.children) == 0

    def is_inferred(self) -> bool:
        """Check if the result is already inferred."""
        return self.reasons.result is not None


@dataclass
class CombinedCallGraphNode(CallGraphNode):
    """Class for combined call graph nodes.

    A CombinedCallGraphNode represents a combined cycle of functions in the call graph.

    Attributes
    ----------
    combines : dict[NodeID, CallGraphNode]
        A dictionary of all nodes that are combined into this node.
        This is later used for transferring the reasons of the combined node to the original nodes.
    """

    combines: dict[NodeID, CallGraphNode] = field(default_factory=dict)

    def __hash__(self) -> int:
        return hash(str(self))

    def __str__(self) -> str:
        return f"{self.symbol.id}"

    def __repr__(self) -> str:
        return f"{self.symbol.name}: {id(self)}"

    def combined_node_id_to_string(self) -> list[str]:
        """Return the combined node IDs as a string.

        Returns
        -------
        str
            The combined node IDs as a string.
        """
        return [str(node_id) for node_id in self.combines]

    def decombine(self) -> dict[NodeID, CallGraphNode]:
        """Decombine the node.

        After the purity of a combined node is inferred,
        the reasons of the combined node are transferred to the original nodes.

        Returns
        -------
        dict[NodeID, CallGraphNode]
            The original nodes with the transferred reasons.
        """
        original_nodes: dict[NodeID, CallGraphNode] = {}
        for node_id, node in self.combines.items():
            original_nodes[node_id] = node
            original_nodes[node_id].reasons = self.reasons
        return original_nodes


@dataclass
class ImportedCallGraphNode(CallGraphNode):
    """Class for imported call graph nodes.

    This class represents functions that are imported from other modules in the call graph.
    """

    symbol: Import

    def __hash__(self) -> int:
        return hash(str(self))

    def __str__(self) -> str:
        return f"{self.symbol.id}"

    def __repr__(self) -> str:
        return f"{self.symbol.name}: {id(self)}"
