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
class Variables:
    """Stores the variables that are defined in a class.

    Attributes
    ----------
        class_variables     is a list of AssignName nodes that define class variables
        instance_variables  is a list of AssignAttr nodes that define instance variables
    """

    class_variables: list[astroid.AssignName] | None
    instance_variables: list[astroid.NodeNG] | None


@dataclass
class ScopeNode:
    """Represents a node in the scope tree.

    The scope tree is a tree that represents the scope of a module. It is used to determine the scope of a reference.
    On the top level, there is a ScopeNode for the module. Each ScopeNode has a list of children, which are the nodes
    that are defined in the scope of the node. Each ScopeNode also has a reference to its parent node.

    Attributes
    ----------
        node        is the node in the AST that defines the scope of the node.
        children    is a list of ScopeNodes that are defined in the scope of the node, is None if the node is a leaf node.
        parent      is the parent node in the scope tree, is None if the node is the root node.
    """

    node: astroid.Module | astroid.FunctionDef | astroid.ClassDef | astroid.AssignName | astroid.AssignAttr | astroid.Attribute | astroid.Call | astroid.Import | astroid.ImportFrom | MemberAccess
    children: list[ScopeNode] | None = None
    parent: ScopeNode | None = None


@dataclass
class ScopeFinder:
    """
    A ScopeFinder instance is used to find the scope of a reference.

    The scope of a reference is the node in the scope tree that defines the reference.
    It is determined by walking the AST and checking if the reference is defined in the scope of the current node.

    Attributes
    ----------
        current_node_stack      stack of nodes that are currently visited by the ASTWalker .
        children:               All found children nodes are stored in children until their scope is determined.
    """

    current_node_stack: list[ScopeNode] = field(default_factory=list)
    children: list[ScopeNode] = field(default_factory=list)
    variables: list[Variables] = field(default_factory=list)

    def detect_scope(self, node: astroid.NodeNG) -> None:
        """
        Detect the scope of the given node.

        Detecting the scope of a node means finding the node in the scope tree that defines the scope of the given node.
        The scope of a node is defined by the parent node in the scope tree.
        """
        current_scope = node
        outer_scope_children: list[ScopeNode] = []
        inner_scope_children: list[ScopeNode] = []
        for child in self.children:
            if (
                child.parent is not None and child.parent.node != current_scope
            ):  # check if the child is in the scope of the current node
                outer_scope_children.append(child)  # add the child to the outer scope
            else:
                inner_scope_children.append(child)  # add the child to the inner scope

        self.current_node_stack[-1].children = inner_scope_children  # set the children of the current node
        self.children = outer_scope_children  # keep the children that are not in the scope of the current node
        self.children.append(self.current_node_stack[-1])  # add the current node to the children
        self.current_node_stack.pop()  # remove the current node from the stack

    def analyze_constructor(self, node: astroid.FunctionDef) -> None:
        """Analyze the constructor of a class.

        The constructor of a class is a special function that is called when an instance of the class is created.
        """
        for child in node.body:
            if isinstance(child, astroid.Assign):
                if self.variables[-1].instance_variables is None:
                    self.variables[-1].instance_variables = []
                self.variables[-1].instance_variables.append(child.targets[0])
            elif isinstance(child, astroid.AnnAssign):
                if self.variables[-1].instance_variables is None:
                    self.variables[-1].instance_variables = []
                self.variables[-1].instance_variables.append(child.target)
            else:
                raise TypeError(f"Unexpected node type {type(child)}")

    def enter_module(self, node: astroid.Module) -> None:
        """
        Enter a module node.

        The module node is the root node, so it has no parent (parent is None).
        The module node is also the first node that is visited, so the current_node_stack is empty before entering the module node.
        """
        self.current_node_stack.append(
            ScopeNode(node=node, children=None, parent=None),
        )

    def leave_module(self, node: astroid.Module) -> None:
        self.detect_scope(node)

    def enter_classdef(self, node: astroid.ClassDef) -> None:
        self.current_node_stack.append(
            ScopeNode(node=node, children=None, parent=self.current_node_stack[-1]),
        )
        # initialize the variable lists for the current class
        self.variables.append(Variables(class_variables=[], instance_variables=[]))

    def leave_classdef(self, node: astroid.ClassDef) -> None:
        self.detect_scope(node)

    def enter_functiondef(self, node: astroid.FunctionDef) -> None:
        self.current_node_stack.append(
            ScopeNode(node=node, children=None, parent=self.current_node_stack[-1]),
        )
        if node.name == "__init__":
            self.analyze_constructor(node)

    def leave_functiondef(self, node: astroid.FunctionDef) -> None:
        self.detect_scope(node)

    def enter_assignname(self, node: astroid.AssignName) -> None:
        if isinstance(node.parent, astroid.Arguments) and node.name == "self":
            pass  # TODO: Special treatment for self parameter?

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
            scope_node = ScopeNode(node=node, children=None, parent=parent)
            self.children.append(scope_node)

        # add class variables to the class variables list
        if isinstance(node.parent.parent, astroid.ClassDef):
            if self.variables[-1].class_variables is None:
                self.variables[-1].class_variables = []
            self.variables[-1].class_variables.append(node)

    def enter_assignattr(self, node: astroid.AssignAttr) -> None:
        parent = self.current_node_stack[-1]
        scope_node = ScopeNode(node=node, children=None, parent=parent)
        self.children.append(scope_node)

    def enter_import(self, node: astroid.Import) -> None:
        parent = self.current_node_stack[-1]
        scope_node = ScopeNode(node=node, children=None, parent=parent)
        self.children.append(scope_node)

    def enter_importfrom(self, node: astroid.ImportFrom) -> None:
        parent = self.current_node_stack[-1]
        scope_node = ScopeNode(node=node, children=None, parent=parent)
        self.children.append(scope_node)


def get_scope(code: str) -> tuple[list[ScopeNode], list[Variables]]:
    """Get the scope of the given code.

    In order to get the scope of the given code, the code is parsed into an AST and then walked by an ASTWalker.
    The ASTWalker detects the scope of each node and builds a scope tree by using an instance of ScopeFinder.

    Returns
    -------
        scopes:     list of ScopeNode instances that represent the scope tree of the given code.
        variables:  list of class variables and list of instance variables for all classes in the given code.
    """
    scope_handler = ScopeFinder()
    walker = ASTWalker(scope_handler)
    module = astroid.parse(code)
    walker.walk(module)

    scopes = scope_handler.children  # get the children of the root node, which are the scopes of the module
    variables = scope_handler.variables  # lists of class variables and instance variables
    scope_handler.children = []  # reset the children
    scope_handler.current_node_stack = []  # reset the stack
    scope_handler.variables = []  # reset the variables

    return scopes, variables
