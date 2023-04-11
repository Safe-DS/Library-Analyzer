from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List

import astroid
from astroid import Name
from astroid.helpers import safe_infer

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
    list_is_complete: bool = False  # if True, then the list of potential references is completed
    # TODO: implement a methode to check if the list is complete: all references are found
    #  the list is only completed if every reference is found


@dataclass
class ReferenceHandler:
    # search_name_in_nodes: list[astroid.Assign]
    names_list: list[astroid.Name | astroid.AssignName] = field(default_factory=list)

    # AssignName is used to find the name if it is used as a value in an assignment
    def enter_name(self, node: astroid.Name) -> None:
        if isinstance(node.parent, astroid.Assign | astroid.AssignAttr | astroid.Attribute | astroid.AugAssign | astroid.Return | astroid.Compare | astroid.For):
            self.names_list.append(node)
        if isinstance(node.parent, astroid.Call):
            if isinstance(node.parent.func, astroid.Name):
                # append a node only then when it is not the name node of the function
                if node.parent.func.name != node.name:
                    self.names_list.append(node)

    # AssignName is used to find the name if it is used as a target in an assignment
    def enter_assignname(self, node: astroid.AssignName) -> None:
        if isinstance(node.parent, astroid.Assign | astroid.Arguments | astroid.AssignAttr | astroid.Attribute| astroid.AugAssign | astroid.AnnAssign | astroid.Return | astroid.Compare | astroid.For):
            self.names_list.append(node)

    # We do not need AugAssign, since it uses AssignName as a target and Name as value


def get_name_nodes(module: astroid.NodeNG) -> list[list[astroid.Name]]:
    reference_handler = ReferenceHandler()
    walker = ASTWalker(reference_handler)
    name_nodes: list[list[astroid.Name]] = []

    if isinstance(module, astroid.Module):
        for node in module.body:
            if isinstance(node, astroid.FunctionDef):  # filter all function definitions
                walker.walk(node)
                name_nodes.append(reference_handler.names_list)
                reference_handler.names_list = []
            if isinstance(node, astroid.ClassDef):  # filter all class definitions
                walker.walk(node)
                name_nodes.append(reference_handler.names_list)
                reference_handler.names_list = []
    # for i in name_nodes:
    #    print(i)

    return name_nodes


def construct_reference_list(names_list: list[astroid.Name | astroid.AssignName]) -> list[Reference]:
    """Construct a list of references from a list of name nodes."""
    references_without_potential_references: list[Reference] = []
    for name in names_list:
        if isinstance(name, astroid.Name):
            references_without_potential_references.append(Reference(name, Usage.TARGET, [], False))
        if isinstance(name, astroid.AssignName):
            references_without_potential_references.append(Reference(name, Usage.VALUE, [], False))

    return references_without_potential_references


def add_potential_references(references_without_potential_references: Reference) -> Reference:
    """Add all potential references to a reference."""
    pass


def resolve_references(module_names: list[astroid.Name]) -> None:
    """Resolve references in a node."""
    reference_list_complete: list[Reference] = []
    reference_list_proto = construct_reference_list(module_names)
    for reference in reference_list_proto:
        reference_complete = add_potential_references(reference)
        reference_list_complete.append(reference_complete)

        # TODO: since we have found all name Nodes, we need to find the scope of the current name node
        #  and then search for all name nodes in that scope where the name is used
        #  if the name is used as a value in an assignment, then we need to find the target of the assignment and then
        #  check all nodes further down the list where the name is used as a target
        #  if the name is used as a target in an assignment, then we need to find the value of the assignment?

    pass
