from __future__ import annotations

from dataclasses import dataclass, field

import astroid

from library_analyzer.processing.api.model import Expression, Reference
from library_analyzer.utils import ASTWalker


@dataclass
class MemberAccess(Expression):
    expression: astroid.NodeNG
    value: MemberAccess | Reference
    parent: astroid.NodeNG | None = field(default=None)


@dataclass
class NodeScope:
    node: astroid.Module | astroid.FunctionDef | astroid.ClassDef | astroid.AssignName | astroid.AssignAttr | astroid.Attribute | astroid.Call | astroid.Import | astroid.ImportFrom | MemberAccess
    children: list[NodeScope] | None = None
    parent: NodeScope | None = None


@dataclass
class ScopeFinder:
    current_node_stack: list[NodeScope] = field(default_factory=list)
    children: list[NodeScope] = field(default_factory=list)

    def enter_module(self, node: astroid.Module) -> None:
        self.current_node_stack.append(NodeScope(node=node, children=None, parent=None))

    def leave_module(self, node: astroid.Module) -> None:
        current_scope = node
        outer_scope_children: list[NodeScope] = []
        module_scope_children: list[NodeScope] = []
        for child in self.children:
            if child.parent.node is None:
                pass
            if child.parent.node is not None and child.parent.node != current_scope:
                outer_scope_children.append(child)  # select all children from the outer scope
            else:
                module_scope_children.append(child)  # select all children from this scope

        self.current_node_stack[-1].children = module_scope_children
        self.children = outer_scope_children
        self.children.append(self.current_node_stack[-1])
        self.current_node_stack.pop()

    def enter_classdef(self, node: astroid.ClassDef) -> None:
        self.current_node_stack.append(
            NodeScope(node=node, children=None, parent=self.current_node_stack[-1]),
        )

    def leave_classdef(self, node: astroid.ClassDef) -> None:
        current_scope = node
        outer_scope_children: list[NodeScope] = []
        class_scope_children: list[NodeScope] = []
        for child in self.children:
            if child.parent.node is None:
                pass
            if child.parent.node is not None and child.parent.node != current_scope:
                outer_scope_children.append(child)  # select all children from the outer scope
            else:
                class_scope_children.append(child)  # select all children from this scope

        self.current_node_stack[-1].children = class_scope_children
        self.children = outer_scope_children
        self.children.append(self.current_node_stack[-1])
        self.current_node_stack.pop()

    def enter_functiondef(self, node: astroid.FunctionDef) -> None:
        self.current_node_stack.append(
            NodeScope(node=node, children=None, parent=self.current_node_stack[-1]),
        )
        # TODO: Special treatment for __init__ function

    def leave_functiondef(self, node: astroid.FunctionDef) -> None:
        current_scope = node
        outer_scope_children: list[NodeScope] = []
        function_scope_children: list[NodeScope] = []
        for child in self.children:
            if child.parent.node is None:
                pass
            if child.parent.node is not None and child.parent.node != current_scope:
                outer_scope_children.append(child)  # select all children from the outer scope
            else:
                function_scope_children.append(child)  # select all children from this scope

        self.current_node_stack[-1].children = function_scope_children  # add all children from this scope to the parent
        self.children = outer_scope_children
        self.children.append(self.current_node_stack[-1])
        self.current_node_stack.pop()

    def enter_assignname(self, node: astroid.AssignName) -> None:
        if isinstance(node.parent, astroid.Arguments):
            if node.name == "self":
                pass
            else:
                parent = self.current_node_stack[-1]
                scope_node = NodeScope(node=node, children=None, parent=parent)
                self.children.append(scope_node)

        elif isinstance(
            node.parent,
            astroid.Assign
            | astroid.Arguments
            | astroid.AssignAttr
            | astroid.Attribute
            | astroid.AugAssign
            | astroid.AnnAssign,
        ):
            parent = self.current_node_stack[-1]
            scope_node = NodeScope(node=node, children=None, parent=parent)
            self.children.append(scope_node)

    def enter_assignattr(self, node: astroid.Attribute) -> None:
        parent = self.current_node_stack[-1]
        scope_node = NodeScope(node=node, children=None, parent=parent)
        self.children.append(scope_node)

    def enter_import(self, node: astroid.Import) -> None:
        parent = self.current_node_stack[-1]
        scope_node = NodeScope(node=node, children=None, parent=parent)
        self.children.append(scope_node)

    def enter_importfrom(self, node: astroid.ImportFrom) -> None:
        parent = self.current_node_stack[-1]
        scope_node = NodeScope(node=node, children=None, parent=parent)
        self.children.append(scope_node)


def get_scope(code: str) -> list[NodeScope]:
    scope_handler = ScopeFinder()
    walker = ASTWalker(scope_handler)
    module = astroid.parse(code)
    walker.walk(module)

    scopes = scope_handler.children
    scope_handler.children = []
    scope_handler.current_node_stack = []

    return scopes
