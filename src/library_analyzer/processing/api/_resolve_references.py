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
class NodeID:
    module: astroid.Module  # | None  # TODO: can we use ScopeNode here
    name: str
    line: int
    col: int
    node_type: str | None

    def __str__(self) -> str:
        return f"{self.module.name}.{self.name}.{self.line}.{self.col}"


@dataclass
class Variables:
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

    node: astroid.Module | astroid.FunctionDef | astroid.ClassDef | astroid.Name | astroid.AssignName | astroid.AssignAttr | astroid.Attribute | astroid.Import | astroid.ImportFrom | MemberAccess
    children: list[ScopeNode] | None = None
    parent: ScopeNode | None = None


@dataclass
class Scopes:
    module_scope: list[ScopeNode]
    class_scope: list[ScopeNode]
    function_scope: list[ScopeNode]


@dataclass
class NodeReference:
    name: astroid.Name | astroid.AssignName | str
    node_id: str
    scope: ScopeNode
    referenced_declarations: list[astroid.Name | astroid.AssignName] = field(default_factory=list)


# TODO: how to deal with astroid.Lambda and astroid.GeneratorExp in scope?
# TODO: how to deal with the __init__ function of a class? It must be looked at separately
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


@dataclass
class NameNodeFinder:
    names_list: list[astroid.Name | astroid.AssignName | MemberAccess] = field(default_factory=list)

    # AssignName is used to find the name if it is used as a value in an assignment
    def enter_name(self, node: astroid.Name) -> None:
        if isinstance(
            node.parent,
            astroid.Assign
            | astroid.AugAssign
            | astroid.Return
            | astroid.Compare
            | astroid.For
            | astroid.BinOp
            | astroid.BoolOp,
        ):
            self.names_list.append(node)
        if (
            isinstance(node.parent, astroid.Call)
            and isinstance(node.parent.func, astroid.Name)
            and node.parent.func.name != node.name
        ):
            # append a node only then when it is not the name node of the function
            self.names_list.append(node)

    # AssignName is used to find the name if it is used as a target in an assignment
    def enter_assignname(self, node: astroid.AssignName) -> None:
        if isinstance(
            node.parent,
            astroid.Assign
            | astroid.Arguments
            | astroid.AssignAttr
            | astroid.Attribute
            | astroid.AugAssign
            | astroid.AnnAssign
            | astroid.Return
            | astroid.Compare
            | astroid.For,
        ):
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


def get_name_nodes(code: str) -> list[astroid.Name | astroid.AssignName]:
    module = astroid.parse(code)
    name_node_handler = NameNodeFinder()
    walker = ASTWalker(name_node_handler)
    name_nodes: list[astroid.Name | astroid.AssignName] = []

    if isinstance(module, astroid.Module):
        for node in module.body:
            # print(node.as_string())
            walker.walk(node)
            name_nodes.extend(name_node_handler.names_list)
            name_node_handler.names_list = []

    return name_nodes


# THIS FUNCTION IS THE CORRECT ONE - MERGE THIS (over calc_function_id)
def calc_node_id(
    node: astroid.Module | astroid.ClassDef | astroid.FunctionDef | astroid.AssignName | astroid.Name | MemberAccess
) -> NodeID | None:
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
        case MemberAccess():
            return NodeID(module, node.expression.as_string(), node.expression.lineno, node.expression.col_offset, node.expression.__class__.__name__)
        case _:
            raise ValueError(f"Node type {node.__class__.__name__} is not supported yet.")

    # TODO: add fitting default case


def create_references(names_list: list[astroid.Name | astroid.AssignName]) -> list[NodeReference]:
    """Construct a list of references from a list of name nodes.

    These references are prototypes, since they do not have any potential value references nor potential target references yet.
    They also do not have any scope nodes yet.
    """
    references_proto: list[NodeReference] = []
    for name in names_list:
        node_id = calc_node_id(name)
        scope_node = ScopeNode(name, None, None)

        if isinstance(name, astroid.Name):
            references_proto.append(NodeReference(name, node_id.__str__(), scope_node, []))
        if isinstance(name, astroid.AssignName):
            references_proto.append(NodeReference(name, node_id.__str__(), scope_node, []))

    return references_proto


def add_potential_value_references(reference: NodeReference, reference_list: list[NodeReference]) -> NodeReference:
    """Add all potential value references to a reference.

    A potential value reference is a reference where the name is used as a value.
    Therefor we need to check all nodes further down the list where the name is used as a value.
    """
    complete_references = reference
    if reference in reference_list:
        for next_reference in reference_list[reference_list.index(reference):]:
            if next_reference.name.name == reference.name.name and isinstance(next_reference.name, astroid.Name):
                complete_references.referenced_declarations.append(next_reference.name)

    return complete_references


def add_potential_target_references(reference: NodeReference, reference_list: list[NodeReference]) -> NodeReference:
    """Add all potential target references to a reference.

    A potential target reference is a reference where the name is used as a target.
    Therefor we need to check all nodes further up the list where the name is used as a target.
    """
    complete_references = reference
    if reference in reference_list:
        for next_reference in reference_list[:reference_list.index(reference)]:
            if next_reference.name.name == reference.name.name and isinstance(next_reference.name, astroid.AssignName):
                complete_references.referenced_declarations.append(next_reference.name)

    return complete_references


# TODO: rework this function to respect the scope of the name
def find_references(scope: list[ScopeNode], variable: Variables, name_node_list: list[astroid.Name | astroid.AssignName]) -> list[NodeReference]:
    """Find references in a node.

    The following methods are called:
    * construct_reference_list: construct a list of references from a list of name nodes but without potential references
    * add_potential_value_references: add all potential value references to a reference
    * add_potential_target_references: add all potential target references to a reference
    """

    reference_list_proto = create_references(name_node_list)
    reference_list: list[NodeReference] = []
    # Collect all references in the module
    for reference in reference_list_proto:
        if isinstance(reference.name, astroid.AssignName):
            reference_complete = add_potential_value_references(reference, reference_list_proto)
            reference_list.append(reference_complete)
        elif isinstance(reference.name, astroid.Name):
            reference_complete = add_potential_target_references(reference, reference_list_proto)
            reference_list.append(reference_complete)

    # TODO: since we have found all name Nodes, we need to find the scope of the current name node
    #  and then search for all name nodes in that scope where the name is used
    #  if the name is used as a value in an assignment, then we need to find the target of the assignment and then
    #  check all nodes further down the list where the name is used as a target
    #  if the name is used as a target in an assignment, then we need to find the value of the assignment?

    return reference_list


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


def resolve_reference(code: str) -> list[NodeReference]:
    scope, variables = get_scope(code)
    name_nodes_list = get_name_nodes(code)

    references = find_references(scope, variables, name_nodes_list)

    return references
