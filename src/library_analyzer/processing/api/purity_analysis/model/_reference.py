from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypeVar, Generic, TYPE_CHECKING

import astroid

from library_analyzer.processing.api.purity_analysis.model._scope import (
    MemberAccessTarget,
    MemberAccessValue,
    Scope,
    Symbol,
    FunctionScope,
    Reasons,
)

if TYPE_CHECKING:
    from library_analyzer.processing.api.purity_analysis.model import (
        PurityResult,
    )


@dataclass
class ReferenceNode:
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

    Parameters
    ----------
        * data:
        * children: a set of call graph nodes that are called by this node
        * reasons: a Reasons or PurityResult object that represents the reasons why this node is impure
                   if the purity analysis has been performed on this node reasons is a PurityResult object otherwise it is a Reasons object
    """

    data: _T
    children: set[CallGraphNode] = field(default_factory=set)
    reasons: Reasons | PurityResult | None = field(default=None)
    combined_node_names: list[str] = field(default_factory=list)

    def __hash__(self) -> int:
        return hash(str(self))

    def __repr__(self) -> str:
        if isinstance(self.data, FunctionScope):
            return f"{self.data.symbol.name}"
        return f"{self.data}"

    def add_child(self, child: CallGraphNode) -> None:
        self.children.add(child)

    def is_leaf(self) -> bool:
        return len(self.children) == 0


@dataclass
class CallGraphForest:
    graphs: dict[str, CallGraphNode] = field(default_factory=dict)

    def add_graph(self, graph_name: str, graph: CallGraphNode) -> None:
        self.graphs[graph_name] = graph

    def get_graph(self, graph_name: str) -> CallGraphNode:
        try:
            return self.graphs[graph_name]
        except KeyError:
            raise KeyError(f"Graph with name {graph_name} does not exist.") from None

    def delete_graph(self, graph_name: str) -> None:
        del self.graphs[graph_name]
