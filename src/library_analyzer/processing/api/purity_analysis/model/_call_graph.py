from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from library_analyzer.processing.api.purity_analysis.model._module_data import (
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
    forest : dict[str, NewCallGraphNode]
        The dictionary of call graph trees.
        The key is the name of the tree, the value is the root CallGraphNode of the tree.
    """

    forest: dict[NodeID, NewCallGraphNode] = field(default_factory=dict)

    def add_graph(self, graph_id: NodeID, graph: NewCallGraphNode) -> None:
        """Add a call graph tree to the forest.

        Parameters
        ----------
        graph_id : NodeID
            The NodeID of the tree node.
        graph : NewCallGraphNode
            The root of the tree.
        """
        # if graph_id in self.forest:
        #     raise ValueError(f"Graph with id {graph_id} already exists inside the call graph.")
        self.forest[graph_id] = graph

    def get_graph(self, graph_id: NodeID) -> NewCallGraphNode:
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
        result = self.forest.get(graph_id)
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
        return graph_id in self.forest

    def delete_graph(self, graph_id: NodeID) -> None:
        """Delete a call graph tree from the forest.

        Parameters
        ----------
        graph_id : NodeID
            The NodeID of the tree to delete.
        """
        del self.forest[graph_id]


@dataclass
class NewCallGraphNode:
    """Class for call graph nodes.

    A call graph node represents a function in the call graph.

    Attributes
    ----------
    symbol : Symbol
        The of the function that the node represents.
    reasons : Reasons
        The raw Reasons for the node.
        After the call graph is built, this only contains reads_from and writes_to as well as unknown_calls.
    children : dict[NodeID, NewCallGraphNode]
        The set of children of the node, (i.e., the set of nodes that this node calls)
    """

    symbol: Symbol
    reasons: Reasons
    children: dict[NodeID, NewCallGraphNode] = field(default_factory=dict)

    def __hash__(self) -> int:
        return hash(str(self))

    def __str__(self) -> str:
        return f"{self.symbol.id}"

    def __repr__(self) -> str:
        return f"{self.symbol.name}: {id(self)}"

    def add_child(self, child: NewCallGraphNode) -> None:
        """Add a child to the node.

        Parameters
        ----------
        child : NewCallGraphNode
            The child to add.
        """
        self.children[child.symbol.id] = child

    def get_child(self, child_id: NodeID) -> NewCallGraphNode:
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
        return len(self.reasons.calls) == 0


@dataclass
class CombinedCallGraphNode(NewCallGraphNode):
    """Class for call graph nodes.

    A call graph node represents a function in the call graph.

    Attributes
    ----------
    combines : dict[NodeID, NewCallGraphNode]
        A dictionary of all nodes that are combined into this node.
        This is later used for transferring the reasons of the combined node to the original nodes.
    """

    combines: dict[NodeID, NewCallGraphNode] = field(default_factory=dict)

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
