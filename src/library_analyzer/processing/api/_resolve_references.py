from __future__ import annotations

from abc import ABC
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
    module: astroid.Module
    name: str
    line: int
    col: int
    node_type: str | None  # TODO: this can be removed after Symbol is implemented since it will be redundant

    def __str__(self) -> str:
        return f"{self.module.name}.{self.name}.{self.line}.{self.col}"


@dataclass
class Variables:
    class_variables: list[astroid.AssignName] | None
    instance_variables: list[astroid.NodeNG] | None


@dataclass
class Symbol(ABC):
    node: astroid.NodeNG
    name: str  # class A = name = "A"


@dataclass
class Parameter(Symbol):
    node: astroid.AssignName #?? richtige einschränkung
    pass


@dataclass
class LocalVariable(Symbol):
    pass


@dataclass
class GlobalVariable(Symbol):
    pass


@dataclass
class ClassVariable(Symbol):
    pass


@dataclass
class InstanceVariable(Symbol):
    pass


@dataclass
class ScopeNode:
    """Represents a node in the scope tree.

    The scope tree is a tree that represents the scope of a module. It is used to determine the scope of a reference.
    On the top level, there is a ScopeNode for the module. Each ScopeNode has a list of children, which are the nodes
    that are defined in the scope of the node. Each ScopeNode also has a reference to its parent node.

    Attributes
    ----------
        node        is the node in the AST that defines the scope of the node.
        node_id     is the id of the node.
        children    is a list of ScopeNodes that are defined in the scope of the node, is None if the node is a leaf node.
        parent      is the parent node in the scope tree, is None if the node is the root node.
        symbol      is a list of symbols that are defined in the scope of the node.
    """

    node: astroid.Module | astroid.FunctionDef | astroid.ClassDef | astroid.Name | astroid.AssignName | astroid.AssignAttr | astroid.Attribute | astroid.Import | astroid.ImportFrom | MemberAccess
    id: NodeID  # TODO: rename to id and implement it
    children: list[ScopeNode | ClassScopeNode] = field(default_factory=list)
    parent: ScopeNode  | ClassScopeNode | None = None
    # _symbol: dict[Symbol] = field(default_factory=dict)
    # TODO: make fields private (_name)

    # def __contains__(self, item):
    #     return item in self._symbol


@dataclass
class ClassScopeNode(ScopeNode):
    """Represents a ScopeNode that defines the scope of a class.

    Attributes
    ----------
        class_variables     is a list of AssignName nodes that define class variables
        instance_variables  is a list of AssignAttr nodes that define instance variables
    """

    class_variables: list[astroid.AssignName] = field(default_factory=list)
    instance_variables: list[astroid.AssignAttr] = field(default_factory=list)


@dataclass
class NodeReference:
    name: astroid.Name | astroid.AssignName | str
    node_id: str
    scope: ScopeNode
    referenced_declarations: list[astroid.Name | astroid.AssignName] = field(default_factory=list)
    # TODO: it is possible to remove the name field since it is already stored in the ScopeNode


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

    current_node_stack: list[ScopeNode | ClassScopeNode] = field(default_factory=list)
    children: list[ScopeNode | ClassScopeNode] = field(default_factory=list)

    def get_node_by_name(self, name: str) -> ScopeNode | ClassScopeNode | None:
        """
        Get a ScopeNode by its name.

        Parameters
        ----------
            name    is the name of the node that should be found.

        Returns
        -------
            The ScopeNode with the given name, or None if no node with the given name was found.
        """
        for node in self.current_node_stack:
            if node.node.name == name:
                return node
        return None
        # TODO: this is inefficient, instead use a dict to store the nodes

    def _detect_scope(self, node: astroid.NodeNG) -> None:
        """
        Detect the scope of the given node.

        Detecting the scope of a node means finding the node in the scope tree that defines the scope of the given node.
        The scope of a node is defined by the parent node in the scope tree.
        """
        current_scope = node
        outer_scope_children: list[ScopeNode | ClassScopeNode] = []
        inner_scope_children: list[ScopeNode | ClassScopeNode] = []
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

    def _analyze_constructor(self, node: astroid.FunctionDef) -> None:
        """Analyze the constructor of a class.

        The constructor of a class is a special function that is called when an instance of the class is created.
        This function only is called when the name of the FunctionDef node is `__init__`.
        """
        # add instance variables to the instance_variables list of the class
        for child in node.body:
            class_node = self.get_node_by_name(node.parent.name)

            if isinstance(class_node, ClassScopeNode):
                if isinstance(child, astroid.Assign):
                    class_node.instance_variables.append(child.targets[0])
                elif isinstance(child, astroid.AnnAssign):
                    class_node.instance_variables.append(child.target)
                else:
                    raise TypeError(f"Unexpected node type {type(child)}")

    def enter_module(self, node: astroid.Module) -> None:
        """
        Enter a module node.

        The module node is the root node, so it has no parent (parent is None).
        The module node is also the first node that is visited, so the current_node_stack is empty before entering the module node.
        """
        self.current_node_stack.append(
            ScopeNode(node=node, id=_calc_node_id(node), children=[], parent=None),
        )

    def leave_module(self, node: astroid.Module) -> None:
        self._detect_scope(node)

    def enter_classdef(self, node: astroid.ClassDef) -> None:
        self.current_node_stack.append(
            ClassScopeNode(node=node, id=_calc_node_id(node), children=[],
                parent=self.current_node_stack[-1],
                instance_variables=[],
                class_variables=[],
            ),
        )
        # initialize the variable lists for the current class
        self.variables.append(Variables(class_variables=[], instance_variables=[]))

    def leave_classdef(self, node: astroid.ClassDef) -> None:
        self._detect_scope(node)

    def enter_functiondef(self, node: astroid.FunctionDef) -> None:
        self.current_node_stack.append(
            ScopeNode(node=node, id=_calc_node_id(node), children=[], parent=self.current_node_stack[-1]),
        )
        if node.name == "__init__":
            self._analyze_constructor(node)

    def leave_functiondef(self, node: astroid.FunctionDef) -> None:
        self._detect_scope(node)

    def enter_assignname(self, node: astroid.AssignName) -> None:
        if isinstance(node.parent, astroid.Arguments) and node.name == "self":
            pass  # TODO: Special treatment for self parameter

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
            scope_node = ScopeNode(node=node, id=_calc_node_id(node), children=[], parent=parent)
            self.children.append(scope_node)

        # add class variables to the class_variables list of the class
        if isinstance(node.parent.parent, astroid.ClassDef):
            class_node = self.get_node_by_name(node.parent.parent.name)
            if isinstance(class_node, ClassScopeNode):
                class_node.class_variables.append(node)

    def enter_assignattr(self, node: astroid.AssignAttr) -> None:
        parent = self.current_node_stack[-1]
        scope_node = ScopeNode(node=node, id=_calc_node_id(node), children=[], parent=parent)
        self.children.append(scope_node)

    def enter_import(self, node: astroid.Import) -> None:
        parent = self.current_node_stack[-1]
        scope_node = ScopeNode(node=node, id=_calc_node_id(node), children=[], parent=parent)
        self.children.append(scope_node)

    def enter_importfrom(self, node: astroid.ImportFrom) -> None:
        parent = self.current_node_stack[-1]
        scope_node = ScopeNode(node=node, id=_calc_node_id(node), children=[], parent=parent)
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
        member_access = _construct_member_access(node)
        self.names_list.append(member_access)

    def enter_assignattr(self, node: astroid.AssignAttr) -> None:
        member_access = _construct_member_access(node)
        self.names_list.append(member_access)

    # def enter_import(self, node: astroid.Import) -> None:
    #     for name in node.names:
    #         self.names_list.append(name[0])


def _construct_member_access(node: astroid.Attribute | astroid.AssignAttr) -> MemberAccess:
    if isinstance(node.expr, astroid.Attribute | astroid.AssignAttr):
        return MemberAccess(_construct_member_access(node.expr), Reference(node.attrname))
    else:
        return MemberAccess(node.expr, Reference(node.attrname))


def _get_name_nodes(code: str) -> list[astroid.Name | astroid.AssignName]:
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
def _calc_node_id(
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
        case astroid.Import():
            return NodeID(module, node.as_string(), node.lineno, node.col_offset, node.__class__.__name__)
        case astroid.ImportFrom():
            return NodeID(module, node.as_string(), node.lineno, node.col_offset, node.__class__.__name__)
        case _:
            raise ValueError(f"Node type {node.__class__.__name__} is not supported yet.")

    # TODO: add fitting default case


def _create_references(all_names_list: list[astroid.Name | astroid.AssignName]) -> tuple[list[NodeReference], list[NodeReference], list[NodeReference]]:
    """Create a list of references from a list of name nodes.

    Returns:
        tuple[list[NodeReference], list[NodeReference], list[NodeReference]]: A tuple of lists of references.
        * references_final: contains all references
        * references_value: contains all references that are used as values
        * references_target: contains all references that are used as targets
    """
    references_proto: list[NodeReference] = []
    references_value: list[NodeReference] = []
    references_target: list[NodeReference] = []
    references_final: list[NodeReference] = []
    for name in all_names_list:
        node_id = _calc_node_id(name)
        scope_node = ScopeNode(name, None, None)

        if isinstance(name, astroid.Name):
            references_proto.append(NodeReference(name, node_id.__str__(), scope_node, []))
        if isinstance(name, astroid.AssignName):
            references_proto.append(NodeReference(name, node_id.__str__(), scope_node, []))

    for reference in references_proto:
        if isinstance(reference.name, astroid.AssignName):
            value_ref = _add_potential_value_references(reference, references_proto)
            references_value.append(value_ref)
            references_final.append(value_ref)

        elif isinstance(reference.name, astroid.Name):
            target_ref = _add_potential_target_references(reference, references_proto)
            references_target.append(target_ref)
            references_final.append(target_ref)

    return references_final, references_value, references_target


def _add_potential_value_references(reference: NodeReference, reference_list: list[NodeReference]) -> NodeReference:
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


def _add_potential_target_references(reference: NodeReference, reference_list: list[NodeReference]) -> NodeReference:
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


# TODO: implement caching for nodes list, scope, vars to reduce runtime
# TODO: rework this function to respect the scope of the name
def _find_references(name_node: astroid.Name | astroid.AssignName, all_name_nodes_list: list[astroid.Name | astroid.AssignName], scope: list[ScopeNode], variable: list[Variables]) -> list[NodeReference]:
    """Find all references for a node.

    Parameters:
    * name_node: the node for which we want to find all references
    * all_name_nodes_list: a list of all name nodes in the module
    * scope: the scopes of the module
    * variable: list of class variables and instance variables for all classes inside the module

    """
    s = scope
    reference_list, value_list, target_list = _create_references(
        all_name_nodes_list)  # contains a list of all references for each node in the module

    # welcher scope sind wir gerade
    # entsprechend dem Scope die zugehörigen Symbole finden



    # TODO: Beispiele wiederfinden zu Flow analysis

    # TODO: since we have found all name Nodes, we need to find the scope of the current name node
    #  and then search for all name nodes in that scope where the name is used
    #  if the name is used as a value in an assignment, then we need to find the target of the assignment and then
    #  check all nodes further down the list where the name is used as a target

    return target_list


def _get_scope(code: str) -> list[ScopeNode | ClassScopeNode]:
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
    scope_handler.children = []  # reset the children
    scope_handler.current_node_stack = []  # reset the stack

    return scopes


def resolve_references(code: str) -> list[list[NodeReference]]:
    scope, variables = _get_scope(code)
    name_nodes_list = _get_name_nodes(code)
    references: list[list[NodeReference]] = []
    for name_node in name_nodes_list:
        references.append(_find_references(name_node, name_nodes_list, scope, variables))

    return references
