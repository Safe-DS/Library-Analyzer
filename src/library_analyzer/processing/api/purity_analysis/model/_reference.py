from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypeVar, Generic

import astroid

from library_analyzer.processing.api.purity_analysis.model._scope import (
    MemberAccessTarget,
    MemberAccessValue,
    Scope,
    Symbol,
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
    data: _T | None = field(default=None)
    children: set[CallGraphNode] = field(default_factory=set)
    missing_children: bool = field(default=False)

    def __hash__(self) -> int:
        return hash(str(self))

    def add_child(self, child: CallGraphNode) -> None:
        self.children.add(child)

    def is_leaf(self) -> bool:
        return len(self.children) == 0


@dataclass
class CallGraphForest:
    trees: dict[str, CallGraphNode] = field(default_factory=dict)

    def add_tree(self, tree_name, tree):
        self.trees[tree_name] = tree

    def get_tree(self, tree_name):
        return self.trees.get(tree_name)

    def delete_tree(self, tree_name):
        del self.trees[tree_name]
