from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List

import astroid

from library_analyzer.utils import ASTWalker


@dataclass
class Usage(Enum):
    TARGET = auto()
    VALUE = auto()


@dataclass
class Reference:
    name: astroid.Name | astroid.AssignName
    # scope: astroid.Module | astroid.FunctionDef | astroid.ClassDef  # TODO: implement scope
    usage: Usage
    potential_references: List[astroid.Name | astroid.AssignName] = field(default_factory=list)
    list_is_complete: bool = False  # if True, then the list potential_references is completed
    # TODO: implement a methode to check if the list is complete: all references are found
    #  the list is only completed if every reference is found


@dataclass
class NameNodeFinder:
    # search_name_in_nodes: list[astroid.Assign]
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
    name_nodes: list[list[astroid.Name]] = []

    if isinstance(module, astroid.Module):
        for node in module.body:
            if isinstance(node, astroid.FunctionDef):  # filter all function definitions
                walker.walk(node)
                name_nodes.append(name_node_handler.names_list)
                name_node_handler.names_list = []
            if isinstance(node, astroid.ClassDef):  # filter all class definitions
                walker.walk(node)
                name_nodes.append(name_node_handler.names_list)
                name_node_handler.names_list = []
    # for i in name_nodes:
    #    print(i)

    return name_nodes


def construct_reference_list(names_list: list[astroid.Name | astroid.AssignName]) -> list[Reference]:
    """Construct a list of references from a list of name nodes."""
    references_without_potential_references: list[Reference] = []
    for name in names_list:
        if isinstance(name, astroid.Name):
            references_without_potential_references.append(Reference(name, Usage.VALUE, [], False))
        if isinstance(name, astroid.AssignName):
            references_without_potential_references.append(Reference(name, Usage.TARGET, [], False))

    return references_without_potential_references


def add_potential_value_references(reference: Reference, reference_list: list[Reference]) -> Reference:
    """Add all potential value references to a reference.

    A potential value reference is a reference where the name is used as a value.
    Therefor we need to check all nodes further down the list where the name is used as a value.
    """
    references_complete = reference
    # check all nodes further down the list where the name is used as a value
    if reference in reference_list:
        for reference_next in reference_list[reference_list.index(reference):]:
            if reference_next.name.name == reference.name.name:
                if reference_next.usage.name == "VALUE":
                    references_complete.potential_references.append(reference_next.name)

    # TODO: check if the list is actually complete
    references_complete.list_is_complete = True

    return references_complete


def add_potential_target_references(reference: Reference, reference_list: list[Reference]) -> Reference:
    """Add all potential target references to a reference.

    A potential target reference is a reference where the name is used as a target.
    Therefor we need to check all nodes further up the list where the name is used as a target.
    """
    references_complete = reference
    # check all nodes further down the list where the name is used as a target
    if reference in reference_list:
        for reference_next in reference_list[:reference_list.index(reference)]:
            if reference_next.name.name == reference.name.name:
                if reference_next.usage.name == "TARGET":
                    references_complete.potential_references.append(reference_next.name)

    references_complete.list_is_complete = True

    return references_complete


def resolve_references(module_names: list[astroid.Name]) -> list[Reference]:
    """Resolve references in a node.

    The following methods are called:
    * construct_reference_list: construct a list of references from a list of name nodes but without potential references
    * add_potential_value_references: add all potential value references to a reference
    * add_potential_target_references: add all potential target references to a reference
    """

    reference_list_complete: list[Reference] = []
    reference_list_proto = construct_reference_list(module_names)
    for reference in reference_list_proto:
        if reference.usage.name == "TARGET":
            reference_complete = add_potential_value_references(reference, reference_list_proto)
            reference_list_complete.append(reference_complete)
        if reference.usage.name == "VALUE":
            reference_complete = add_potential_target_references(reference, reference_list_proto)
            reference_list_complete.append(reference_complete)

        # TODO: since we have found all name Nodes, we need to find the scope of the current name node
        #  and then search for all name nodes in that scope where the name is used
        #  if the name is used as a value in an assignment, then we need to find the target of the assignment and then
        #  check all nodes further down the list where the name is used as a target
        #  if the name is used as a target in an assignment, then we need to find the value of the assignment?

    return reference_list_complete
