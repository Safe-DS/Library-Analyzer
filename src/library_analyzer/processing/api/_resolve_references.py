from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional

import astroid

from library_analyzer.processing.api.model import Expression, Reference
from library_analyzer.utils import ASTWalker


@dataclass
class MemberAccess(Expression):
    expression: astroid.NodeNG
    value: MemberAccess | Reference
    parent: astroid.NodeNG | None = field(default=None)


@dataclass
class NodeID:
    module: astroid.Module  # | None  # TODO: can we use NodeScope here
    name: str
    line: int
    col: int
    node_type: Optional[str]

    def __str__(self) -> str:
        return f"{self.module.name}.{self.name}.{self.line}.{self.col}"


@dataclass
class NodeScope:
    node: astroid.Module | astroid.FunctionDef | astroid.ClassDef | astroid.AssignName | astroid.AssignAttr | astroid.Attribute | astroid.Call | astroid.Import | astroid.ImportFrom | MemberAccess
    children: list[NodeScope] | None = None
    parent_scope: astroid.NodeNG | None = None


@dataclass
class Scopes:
    module_scope: list[NodeScope]
    class_scope: list[NodeScope]
    function_scope: list[NodeScope]


@dataclass
class NodeReference:
    name: astroid.Name | astroid.AssignName | str
    node_id: str
    scope: NodeScope
    potential_references: List[astroid.Name | astroid.AssignName] = field(default_factory=list)
    list_is_complete: bool = False  # if True, then the list potential_references is completed
    # TODO: implement a methode to check if the list is complete: all references are found
    #  the list is only completed if every reference is found


@dataclass
class ScopeDepth(Enum):
    MODULE = auto()
    CLASS = auto()
    FUNCTION = auto()


# TODO: how to deal with astroid.Lambda and astroid.GeneratorExp in scope?
# TODO: how to deal with the __init__ function of a class? It must be looked at separately
@dataclass
class ScopeFinder:
    current_node_stack: list[NodeScope] = field(default_factory=list)
    children: list[NodeScope] = field(default_factory=list)

    def enter_module(self, node: astroid.Module) -> None:
        self.current_node_stack.append(NodeScope(node=node, children=None, parent_scope=None))

    def leave_module(self, node: astroid.Module) -> None:
        current_scope = node
        outer_scope_children: list[NodeScope] = []
        module_scope_children: list[NodeScope] = []
        for child in self.children:
            if not child.parent_scope == current_scope:
                outer_scope_children.append(child)  # select all children from the outer scope
            else:
                module_scope_children.append(child)  # select all children from this scope

        self.current_node_stack[-1].children = module_scope_children
        self.children = outer_scope_children
        self.children.append(self.current_node_stack[-1])
        self.current_node_stack.pop()

    def enter_classdef(self, node: astroid.ClassDef) -> None:
        self.current_node_stack.append(NodeScope(node=node, children=None, parent_scope=self.current_node_stack[-1].node))

    def leave_classdef(self, node: astroid.ClassDef) -> None:
        current_scope = node
        outer_scope_children: list[NodeScope] = []
        class_scope_children: list[NodeScope] = []
        for child in self.children:
            if not child.parent_scope == current_scope:
                outer_scope_children.append(child)  # select all children from the outer scope
            else:
                class_scope_children.append(child)  # select all children from this scope

        self.current_node_stack[-1].children = class_scope_children
        self.children = outer_scope_children
        self.children.append(self.current_node_stack[-1])
        self.current_node_stack.pop()

    def enter_functiondef(self, node: astroid.FunctionDef) -> None:
        self.current_node_stack.append(NodeScope(node=node, children=None, parent_scope=self.current_node_stack[-1].node))
        # TODO: Special treatment for __init__ function

    def leave_functiondef(self, node: astroid.FunctionDef) -> None:
        current_scope = node
        outer_scope_children: list[NodeScope] = []
        function_scope_children: list[NodeScope] = []
        for child in self.children:
            if not child.parent_scope == current_scope:
                outer_scope_children.append(child)  # select all children from the outer scope
            else:
                function_scope_children.append(child)  # select all children from this scope

        self.current_node_stack[-1].children = function_scope_children  # add all children from this scope to the parent
        self.children = outer_scope_children
        self.children.append(self.current_node_stack[-1])
        self.current_node_stack.pop()

    # def enter_lambda(self, node: astroid.Lambda) -> None: self.scopes.function_scope.append(NodeReference(
    # name=node.name, node_id=node.name, scope=NodeScope(scope=node)))
    #
    # def enter_generatorexp(self, node: astroid.GeneratorExp) -> None:
    #     self.scopes.function_scope.append(NodeReference(name=node.name, node_id=node.name, scope=NodeScope(scope=node)))

    def enter_call(self, node: astroid.Call) -> None:
        if isinstance(node.parent, astroid.AssignName | astroid.Expr) and isinstance(node.func, astroid.Name | astroid.Attribute):
            parent = self.current_node_stack[-1].node
            scope_node = NodeScope(node=node, children=None, parent_scope=parent)
            self.children.append(scope_node)

    def enter_assignname(self, node: astroid.AssignName) -> None:
        if isinstance(node.parent, astroid.Arguments):
            if node.name == "self":
                pass
            else:
                parent = self.current_node_stack[-1].node
                scope_node = NodeScope(node=node, children=None, parent_scope=parent)
                self.children.append(scope_node)

        elif isinstance(node.parent, astroid.Assign | astroid.Arguments | astroid.AssignAttr | astroid.Attribute | astroid.AugAssign | astroid.AnnAssign):
            parent = self.current_node_stack[-1].node
            scope_node = NodeScope(node=node, children=None, parent_scope=parent)
            self.children.append(scope_node)

    def enter_assignattr(self, node: astroid.Attribute) -> None:  # TODO: check if Attribute is correct here
        # member_access = construct_member_access(node)
        parent = self.current_node_stack[-1].node
        scope_node = NodeScope(node=node, children=None, parent_scope=parent)
        self.children.append(scope_node)

    def enter_import(self, node: astroid.Import) -> None:
        parent = self.current_node_stack[-1].node
        scope_node = NodeScope(node=node, children=None, parent_scope=parent)
        self.children.append(scope_node)

    def enter_importfrom(self, node: astroid.ImportFrom) -> None:
        parent = self.current_node_stack[-1].node
        scope_node = NodeScope(node=node, children=None, parent_scope=parent)
        self.children.append(scope_node)


@dataclass
class NameNodeFinder:
    names_list: list[astroid.Name | astroid.AssignName | MemberAccess] = field(default_factory=list)

    # AssignName is used to find the name if it is used as a value in an assignment
    def enter_name(self, node: astroid.Name) -> None:
        if isinstance(node.parent, astroid.Assign | astroid.AugAssign | astroid.Return | astroid.Compare | astroid.For | astroid.BinOp | astroid.BoolOp):
            self.names_list.append(node)
        if isinstance(node.parent, astroid.Call) and isinstance(node.parent.func, astroid.Name) and node.parent.func.name != node.name:
            # append a node only then when it is not the name node of the function
            self.names_list.append(node)

    # AssignName is used to find the name if it is used as a target in an assignment
    def enter_assignname(self, node: astroid.AssignName) -> None:
        if isinstance(node.parent, astroid.Assign | astroid.Arguments | astroid.AssignAttr | astroid.Attribute | astroid.AugAssign | astroid.AnnAssign | astroid.Return | astroid.Compare | astroid.For):
            self.names_list.append(node)
    # We do not need AugAssign, since it uses AssignName as a target and Name as value

    def enter_attribute(self, node: astroid.Attribute) -> None:
        member_access = construct_member_access(node)
        self.names_list.append(member_access)

    def enter_assignattr(self, node: astroid.AssignAttr) -> None:
        member_access = construct_member_access(node)
        self.names_list.append(member_access)

    # def enter_import(self, node: astroid.Import) -> None:
    #     for name in node.names:
    #         self.names_list.append(name[0])


def construct_member_access(node: astroid.Attribute | astroid.AssignAttr) -> MemberAccess:
    if isinstance(node.expr, astroid.Attribute | astroid.AssignAttr):
        return MemberAccess(construct_member_access(node.expr), Reference(node.attrname))
    else:
        return MemberAccess(node.expr, Reference(node.attrname))


def get_name_nodes(module: astroid.NodeNG) -> list[list[astroid.Name | astroid.AssignName]]:
    name_node_handler = NameNodeFinder()
    walker = ASTWalker(name_node_handler)
    name_nodes: list[list[astroid.Name | astroid.AssignName]] = []

    if isinstance(module, astroid.Module):
        for node in module.body:
            # print(node.as_string())
            walker.walk(node)
            name_nodes.append(name_node_handler.names_list)
            name_node_handler.names_list = []

    return name_nodes


# THIS FUNCTION IS THE CORRECT ONE - MERGE THIS (over calc_function_id)
def calc_node_id(node: astroid.Module | astroid.ClassDef | astroid.FunctionDef | astroid.AssignName | astroid.Name) -> NodeID | None:
    # TODO: there is problem: when a name node is used within a real module, the module is not calculated correctly
    module = node.root()
    match node:
        case astroid.Module():
            return NodeID(module, node.name, 0, 0, node.__class__.__name__)
        case astroid.ClassDef():
            return NodeID(module, node.name, node.lineno, node.col_offset, node.__class__.__name__)
        case astroid.FunctionDef():
            return NodeID(module, node.name, node.lineno, node.col_offset, node.__class__.__name__)
        case astroid.AssignName():
            return NodeID(module, node.name, node.lineno, node.col_offset, node.__class__.__name__)
        case astroid.Name():
            return NodeID(module, node.name, node.lineno, node.col_offset, node.__class__.__name__)
        case _:
            raise ValueError(f"Node type {node.__class__.__name__} is not supported yet.")

    # TODO: add fitting default case


# TODO: remove the commented for this function
def create_references() -> None:
    pass


# def create_references(names_list: list[astroid.Name | astroid.AssignName]) -> list[NodeReference]:
#     """Construct a list of references from a list of name nodes."""
#     references_proto: list[NodeReference] = []
#     for name in names_list:
#         node_id = calc_node_id(name)
#         if name.scope() == "Module":
#             node_scope = NodeScope(name, name.scope(), None)  # TODO: check if this works correct when working with real data
#         else:
#             node_scope = NodeScope(name, name.scope(), name.scope().parent)
#         if isinstance(name, astroid.Name):
#             references_proto.append(NodeReference(name, node_id.__str__(), node_scope, [], False))
#         if isinstance(name, astroid.AssignName):
#             references_proto.append(NodeReference(name, node_id.__str__(), node_scope, [], False))
#
#     return references_proto


# TODO: remove the commented for this function
def add_potential_value_references() -> None:
    pass


# def add_potential_value_references(reference: NodeReference, reference_list: list[NodeReference]) -> NodeReference:
#     """Add all potential value references to a reference.
#
#     A potential value reference is a reference where the name is used as a value.
#     Therefor we need to check all nodes further down the list where the name is used as a value.
#     """
#     complete_references = reference
#     if reference in reference_list:
#         for next_reference in reference_list[reference_list.index(reference):]:
#             if next_reference.name.name == reference.name.name and isinstance(next_reference.name, astroid.Name):
#                 complete_references.potential_references.append(next_reference.name)
#
#     # TODO: check if the list is actually complete
#     complete_references.list_is_complete = True
#
#     return complete_references

def add_potential_target_references() -> None:
    pass


# TODO: remove the commented for this function
# def add_potential_target_references(reference: NodeReference, reference_list: list[NodeReference]) -> NodeReference:
#     """Add all potential target references to a reference.
#
#     A potential target reference is a reference where the name is used as a target.
#     Therefor we need to check all nodes further up the list where the name is used as a target.
#     """
#     complete_references = reference
#     if reference in reference_list:
#         for next_reference in reference_list[:reference_list.index(reference)]:
#             if next_reference.name.name == reference.name.name and isinstance(next_reference.name, astroid.AssignName):
#                 complete_references.potential_references.append(next_reference.name)
#
#     # TODO: check if the list is actually complete
#     complete_references.list_is_complete = True
#
#     return complete_references


# TODO: remove the commented for this function
def find_references() -> None:
    pass

# def find_references(module_names: list[astroid.Name]) -> list[NodeReference]:
#     """Resolve references in a node.
#
#     The following methods are called:
#     * construct_reference_list: construct a list of references from a list of name nodes but without potential references
#     * add_potential_value_references: add all potential value references to a reference
#     * add_potential_target_references: add all potential target references to a reference
#     """
#
#     reference_list_complete: list[NodeReference] = []
#     reference_list_proto = create_references(module_names)
#     for reference in reference_list_proto:
#         if isinstance(reference.name, astroid.AssignName):
#             reference_complete = add_potential_value_references(reference, reference_list_proto)
#             reference_list_complete.append(reference_complete)
#         elif isinstance(reference.name, astroid.Name):
#             reference_complete = add_potential_target_references(reference, reference_list_proto)
#             reference_list_complete.append(reference_complete)
#
#     # scope_list = get_nodes_for_scope(reference_list_complete)
#
#     # TODO: since we have found all name Nodes, we need to find the scope of the current name node
#     #  and then search for all name nodes in that scope where the name is used
#     #  if the name is used as a value in an assignment, then we need to find the target of the assignment and then
#     #  check all nodes further down the list where the name is used as a target
#     #  if the name is used as a target in an assignment, then we need to find the value of the assignment?
#
#     return reference_list_complete


def get_scope(code: str) -> list[NodeScope]:
    scope_handler = ScopeFinder()
    walker = ASTWalker(scope_handler)
    module = astroid.parse(code)
    # print(module.repr_tree())
    walker.walk(module)

    scopes = scope_handler.children
    scope_handler.children = []
    scope_handler.current_node_stack = []

    return scopes
