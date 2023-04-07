from dataclasses import dataclass, field
from typing import List

import astroid
from astroid import Name
from astroid.helpers import safe_infer

from library_analyzer.utils import ASTWalker


@dataclass
class ReferenceHandler:
    # search_name_in_nodes: list[astroid.Assign]
    names_list: list[astroid.Name | astroid.AssignName] = field(default_factory=list)

    # AssignName is used to find the name if it is used as a value in an assignment
    def enter_name(self, node: astroid.Name) -> None:
        if isinstance(node.parent, astroid.Assign | astroid.AssignAttr | astroid.Attribute | astroid.AugAssign | astroid.Return | astroid.Compare | astroid.For):
            self.names_list.append(node)

    # AssignName is used to find the name if it is used as a target in an assignment
    def enter_assignname(self, node: astroid.AssignName) -> None:
        if isinstance(node.parent, astroid.Assign | astroid.AssignAttr | astroid.Attribute| astroid.AugAssign | astroid.AnnAssign | astroid.Return | astroid.Compare | astroid.For):
            self.names_list.append(node)

    # We do not need AugAssign, since it uses AssignName as a target and Name as value
    # def enter_attribute(self, node: astroid.Attribute) -> None:
    #     self.names_list.append(node)

    # def enter_augassignname(self, node: astroid.AugAssignName) -> None:
    #     self.names_list.append(node.name)


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

    for i in name_nodes:
        print(i)

    return name_nodes


def resolve_references(node: list[astroid.Name]) -> None:
    """Resolve references in a node."""

    pass
