from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Union

import astroid

from library_analyzer.utils import ASTWalker


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
    scope: astroid.Module | astroid.FunctionDef | astroid.ClassDef | astroid.Lambda | astroid.GeneratorExp
    parent_scope: NodeScope | None = field(default=None)
    # TODO: how to deal with astroid.Lambda and astroid.GeneratorExp in scope?


@dataclass
class Scopes:
    module_scope: list[Reference]
    class_scope: list[Reference]
    function_scope: list[Reference]


@dataclass
class Reference:
    name: astroid.Name | astroid.AssignName
    node_id: str
    scope: NodeScope
    # usage: str
    potential_references: List[astroid.Name | astroid.AssignName] = field(default_factory=list)
    list_is_complete: bool = False  # if True, then the list potential_references is completed
    # TODO: implement a methode to check if the list is complete: all references are found
    #  the list is only completed if every reference is found


@dataclass
class NameNodeFinder:
    names_list: list[astroid.Name | astroid.AssignName] = field(default_factory=list)

    # AssignName is used to find the name if it is used as a value in an assignment
    def enter_name(self, node: astroid.Name) -> None:
        if isinstance(node.parent, astroid.Assign | astroid.AssignAttr | astroid.Attribute | astroid.AugAssign | astroid.Return | astroid.Compare | astroid.For | astroid.BinOp | astroid.BoolOp):
            self.names_list.append(node)
        if isinstance(node.parent, astroid.Call):
            if isinstance(node.parent.func, astroid.Name):
                # append a node only then when it is not the name node of the function
                if node.parent.func.name != node.name:
                    self.names_list.append(node)

    # AssignName is used to find the name if it is used as a target in an assignment
    def enter_assignname(self, node: astroid.AssignName) -> None:
        if isinstance(node.parent, astroid.Assign | astroid.Arguments | astroid.AssignAttr | astroid.Attribute | astroid.AugAssign | astroid.AnnAssign | astroid.Return | astroid.Compare | astroid.For):
            self.names_list.append(node)

    # We do not need AugAssign, since it uses AssignName as a target and Name as value


def get_name_nodes(module: astroid.NodeNG) -> list[list[astroid.Name]]:
    name_node_handler = NameNodeFinder()
    walker = ASTWalker(name_node_handler)
    name_nodes: list[list[astroid.Name | astroid.AssignName]] = []

    if isinstance(module, astroid.Module):
        for node in module.body:
            # print(node.as_string())
            walker.walk(node)
            name_nodes.append(name_node_handler.names_list)
            name_node_handler.names_list = []

            # if isinstance(node, astroid.FunctionDef):  # filter all function definitions
            #     walker.walk(node)
            #     name_nodes.append(name_node_handler.names_list)
            #     name_node_handler.names_list = []
            # if isinstance(node, astroid.ClassDef):  # filter all class definitions
            #     walker.walk(node)
            #     name_nodes.append(name_node_handler.names_list)
            #     name_node_handler.names_list = []
            # if isinstance(node, astroid.Module):
            #     walker.walk(node)
            #     name_nodes.append(name_node_handler.names_list)
            #     name_node_handler.names_list = []
    # for i in name_nodes:
    #    print(i)

    return name_nodes


# THIS FUNCTION IS THE CORRECT ONE - MERGE THIS (over calc_function_id)
def calc_node_id(node: Union[astroid.Module, astroid.ClassDef, astroid.FunctionDef, astroid.AssignName, astroid.Name])-> NodeID | None:
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


def create_references(names_list: list[astroid.Name | astroid.AssignName]) -> list[Reference]:
    """Construct a list of references from a list of name nodes."""
    references_proto: list[Reference] = []
    for name in names_list:
        node_id = calc_node_id(name)
        if name.scope() == "Module":
            node_scope = NodeScope(name.scope(), None) # TODO: check if this works correct when working with real data
        else:
            node_scope = NodeScope(name.scope(), name.scope().parent)
        if isinstance(name, astroid.Name):
            references_proto.append(Reference(name, node_id.__str__(), node_scope, [], False))
        if isinstance(name, astroid.AssignName):
            references_proto.append(Reference(name, node_id.__str__(), node_scope, [], False))

    return references_proto


def add_potential_value_references(reference: Reference, reference_list: list[Reference]) -> Reference:
    """Add all potential value references to a reference.

    A potential value reference is a reference where the name is used as a value.
    Therefor we need to check all nodes further down the list where the name is used as a value.
    """
    complete_references = reference
    if reference in reference_list:
        for next_reference in reference_list[reference_list.index(reference):]:
            if next_reference.name.name == reference.name.name and isinstance(next_reference.name, astroid.Name):
                complete_references.potential_references.append(next_reference.name)

    # TODO: check if the list is actually complete
    complete_references.list_is_complete = True

    return complete_references


def add_potential_target_references(reference: Reference, reference_list: list[Reference]) -> Reference:
    """Add all potential target references to a reference.

    A potential target reference is a reference where the name is used as a target.
    Therefor we need to check all nodes further up the list where the name is used as a target.
    """
    complete_references = reference
    if reference in reference_list:
        for next_reference in reference_list[:reference_list.index(reference)]:
            if next_reference.name.name == reference.name.name and isinstance(next_reference.name, astroid.AssignName):
                complete_references.potential_references.append(next_reference.name)

    # TODO: check if the list is actually complete
    complete_references.list_is_complete = True

    return complete_references


def find_references(module_names: list[astroid.Name]) -> list[Reference]:
    """Resolve references in a node.

    The following methods are called:
    * construct_reference_list: construct a list of references from a list of name nodes but without potential references
    * add_potential_value_references: add all potential value references to a reference
    * add_potential_target_references: add all potential target references to a reference
    """

    reference_list_complete: list[Reference] = []
    reference_list_proto = create_references(module_names)
    for reference in reference_list_proto:
        if isinstance(reference.name, astroid.AssignName):
            reference_complete = add_potential_value_references(reference, reference_list_proto)
            reference_list_complete.append(reference_complete)
        elif isinstance(reference.name, astroid.Name):
            reference_complete = add_potential_target_references(reference, reference_list_proto)
            reference_list_complete.append(reference_complete)

    scope_list = get_nodes_for_scope(reference_list_complete)

    # TODO: since we have found all name Nodes, we need to find the scope of the current name node
    #  and then search for all name nodes in that scope where the name is used
    #  if the name is used as a value in an assignment, then we need to find the target of the assignment and then
    #  check all nodes further down the list where the name is used as a target
    #  if the name is used as a target in an assignment, then we need to find the value of the assignment?

    return reference_list_complete


# build a function that returns a list of nodes fot a given scope
def get_nodes_for_scope(reference_list: list[Reference]) -> Scopes:
    all_scopes = Scopes([], [], [])

    for reference in reference_list:
        if reference.scope.scope.__class__.__name__ == "Module" or reference.scope.parent_scope is None:
            all_scopes.module_scope.append(reference)
        elif reference.scope.scope is not None and reference.scope.scope.__class__.__name__ == "ClassDef":
            all_scopes.class_scope.append(reference)
        elif reference.scope.scope is not None and reference.scope.scope.__class__.__name__ == "FunctionDef":
            all_scopes.function_scope.append(reference)
    return all_scopes
