from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypeVar, Generic

import astroid

from library_analyzer.processing.api.purity_analysis.model._scope import (
    MemberAccessTarget,
    MemberAccessValue,
    Scope,
    Symbol,
    FunctionScope,
    Reasons,
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
    data: _T | None = field(default=None)  # TODO: save purity information here too: cache result of purity analysis for each function
    children: set[CallGraphNode] = field(default_factory=set)
    reasons: Reasons | None = field(default=None)

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

    def add_graph(self, graph_name, graph):
        self.graphs[graph_name] = graph

    def get_graph(self, graph_name):
        return self.graphs.get(graph_name)

    def delete_graph(self, graph_name):
        del self.graphs[graph_name]
