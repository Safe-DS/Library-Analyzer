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
    module: astroid.Module | str
    name: str
    line: int
    col: int
    # node_type: str | None  # TODO: this can be removed after Symbol is implemented since it will be redundant

    def __str__(self) -> str:
        return f"{self.module}.{self.name}.{self.line}.{self.col}"


@dataclass
class Variables:
    class_variables: list[astroid.AssignName] | None
    instance_variables: list[astroid.NodeNG] | None


@dataclass
class Symbol(ABC):
    node: astroid.NodeNG
    name: str  # class A = name = "A"

    def __str__(self):
        return f"{self.__class__.__name__}.{self.name}"


@dataclass
class Parameter(Symbol):
    node: astroid.AssignName  # TODO: find correct node type and add fields for each subclass
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
class Import(Symbol):
    pass


@dataclass
class Scope:
    """Represents a node in the scope tree.

    The scope tree is a tree that represents the scope of a module. It is used to determine the scope of a reference.
    On the top level, there is a ScopeNode for the module. Each Scope has a list of children, which are the nodes
    that are defined in the scope of the node. Each Scope also has a reference to its parent node.

    Attributes
    ----------
        node        is the node in the AST that defines the scope of the node.
        node_id     is the id of the node.
        children    is a list of ScopeNodes that are defined in the scope of the node, is None if the node is a leaf node.
        parent      is the parent node in the scope tree, is None if the node is the root node.
    """

    node: astroid.Module | astroid.FunctionDef | astroid.ClassDef | astroid.Name | astroid.AssignName | astroid.AssignAttr | astroid.Attribute | astroid.Import | astroid.ImportFrom | MemberAccess
    id: NodeID
    children: list[Scope | ClassScope] = field(default_factory=list)
    parent: Scope | ClassScope | None = None
    # _symbol: dict[Symbol] = field(default_factory=dict)
    # TODO: make fields private (_name)


@dataclass
class ClassScope(Scope):
    """Represents a Scope that defines the scope of a class.

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
    scope: Scope
    referenced_symbols: list[Symbol] = field(default_factory=list)

    def __contains__(self, item):
        return item in self.referenced_symbols


# TODO: how to deal with astroid.Lambda and astroid.GeneratorExp in scope?


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

    current_node_stack: list[Scope | ClassScope] = field(default_factory=list)
    children: list[Scope | ClassScope] = field(default_factory=list)
    name_nodes: dict[astroid.Name, Scope] = field(default_factory=dict)

    def get_node_by_name(self, name: str) -> Scope | ClassScope | None:
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
        outer_scope_children: list[Scope | ClassScope] = []
        inner_scope_children: list[Scope | ClassScope] = []
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

            if isinstance(class_node, ClassScope):
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
            Scope(node=node, id=_calc_node_id(node), children=[], parent=None),
        )

    def leave_module(self, node: astroid.Module) -> None:
        self._detect_scope(node)

    def enter_classdef(self, node: astroid.ClassDef) -> None:
        self.current_node_stack.append(
            ClassScope(
                node=node,
                id=_calc_node_id(node),
                children=[],
                parent=self.current_node_stack[-1],
                instance_variables=[],
                class_variables=[],
            ),
        )

    def leave_classdef(self, node: astroid.ClassDef) -> None:
        self._detect_scope(node)

    def enter_functiondef(self, node: astroid.FunctionDef) -> None:
        self.current_node_stack.append(
            Scope(node=node, id=_calc_node_id(node), children=[], parent=self.current_node_stack[-1]),
        )
        if node.name == "__init__":
            self._analyze_constructor(node)

    def leave_functiondef(self, node: astroid.FunctionDef) -> None:
        self._detect_scope(node)

    def enter_name(self, node: astroid.Name) -> None:
        self.name_nodes[node] = self.current_node_stack[-1]

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
            scope_node = Scope(node=node, id=_calc_node_id(node), children=[], parent=parent)
            self.children.append(scope_node)

        # add class variables to the class_variables list of the class
        if isinstance(node.parent.parent, astroid.ClassDef):
            class_node = self.get_node_by_name(node.parent.parent.name)
            if isinstance(class_node, ClassScope):
                class_node.class_variables.append(node)

    def enter_assignattr(self, node: astroid.AssignAttr) -> None:
        parent = self.current_node_stack[-1]
        scope_node = Scope(node=node, id=_calc_node_id(node), children=[], parent=parent)
        self.children.append(scope_node)

    def enter_import(self, node: astroid.Import) -> None:  # TODO: handle multiple imports and aliases
        parent = self.current_node_stack[-1]
        scope_node = Scope(node=node, id=_calc_node_id(node), children=[], parent=parent)
        self.children.append(scope_node)

    def enter_importfrom(self, node: astroid.ImportFrom) -> None:  # TODO: handle multiple imports and aliases
        parent = self.current_node_stack[-1]
        scope_node = Scope(node=node, id=_calc_node_id(node), children=[], parent=parent)
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


def _calc_node_id(
    node: astroid.Module | astroid.ClassDef | astroid.FunctionDef | astroid.AssignName | astroid.Name | astroid.AssignAttr | astroid.Import | astroid.ImportFrom | MemberAccess
) -> NodeID | None:
    if isinstance(node, MemberAccess):
        module = node.expression.root().name
    else:
        module = node.root().name
        # TODO: check if this is correct when working with a real module

    match node:
        case astroid.Module():
            return NodeID(module, node.name, 0, 0)
        case astroid.ClassDef():
            return NodeID(module, node.name, node.lineno, node.col_offset)
        case astroid.FunctionDef():
            return NodeID(module, node.name, node.lineno, node.col_offset)
        case astroid.AssignName():
            return NodeID(module, node.name, node.lineno, node.col_offset)
        case astroid.Name():
            return NodeID(module, node.name, node.lineno, node.col_offset)
        case MemberAccess():
            return NodeID(module, node.expression.as_string(), node.expression.lineno, node.expression.col_offset)
        case astroid.Import():
            return NodeID(module, node.as_string(), node.lineno, node.col_offset)
        case astroid.ImportFrom():
            return NodeID(module, node.as_string(), node.lineno, node.col_offset)
        case astroid.AssignAttr():
            return NodeID(module, node.attrname, node.lineno, node.col_offset)
        case _:
            raise ValueError(f"Node type {node.__class__.__name__} is not supported yet.")

    # TODO: add fitting default case and merge same types of cases together


def get_scope_node_by_node_id(scope: list[Scope], targeted_node_id: NodeID, name_nodes: dict[astroid.Name] | None) -> Scope:
    if name_nodes is None:
        for node in scope:
            if node.id == targeted_node_id:
                return node
            else:
                found_node = get_scope_node_by_node_id(node.children, targeted_node_id, None)
                if found_node is not None:
                    return found_node

    else:
        for name in name_nodes.keys():
            name_id = _calc_node_id(name)
            if name_id == targeted_node_id:
                return name_nodes.get(name)
            # else:
            #     found_node = get_scope_node_by_node_id(scope, targeted_node_id, name_nodes)
            #     if found_node is not None:
            #         return found_node


def _create_references(all_names_list: list[astroid.Name | astroid.AssignName], scope: list[Scope], name_nodes: dict[astroid.Name]) -> list[NodeReference]:
    """Create a list of references from a list of name nodes.

    Returns:
        * references_final: contains all references that are used as targets
    """
    references_proto: list[NodeReference] = []
    references_final: list[NodeReference] = []
    scope_node: Scope | None = field(default_factory=Scope)

    for name in all_names_list:
        node_id = _calc_node_id(name)  # TODO: is there a better way to connect the name to the scope node?
        if isinstance(name, astroid.AssignName):
            scope_node = get_scope_node_by_node_id(scope, node_id, None)
        elif isinstance(name, astroid.Name):
            scope_node = get_scope_node_by_node_id(scope, node_id, name_nodes)

        references_proto.append(NodeReference(name, scope_node, []))

    for reference in references_proto:
        if isinstance(reference.name, astroid.Name):
            target_ref = _add_target_references(reference, references_proto)
            references_final.append(target_ref)

    return references_final
    # TODO: sonderfälle mit AssignName müssen separat betrachtet werden (global)


def _add_target_references(reference: NodeReference, reference_list: list[NodeReference]) -> NodeReference:
    """Add all target references to a reference.

    A target reference is a reference where the name is used as a target.
    Therefor we need to check all nodes further up the list where the name is used as a target.
    """
    complete_reference = reference
    if reference in reference_list:
        for ref in reference_list[:reference_list.index(reference)]:
            if isinstance(ref.name, MemberAccess):
                if ref.name.expression.as_string() == reference.name.name:
                    complete_reference.referenced_symbols.append(Symbol(ref.name, ref.name.expression.as_string()))
            elif ref.name.name == reference.name.name and isinstance(ref.name, astroid.AssignName):
                complete_reference.referenced_symbols.append(Symbol(ref.name, ref.name.name))

    return complete_reference


def _find_references(name_node: astroid.Name | astroid.AssignName,
                     all_name_nodes_list: list[astroid.Name | astroid.AssignName],
                     scope: list[Scope],
                     name_nodes: dict[astroid.Name]) -> list[NodeReference]:
    """Find all references for a node.

    Parameters:
    * name_node: the node for which we want to find all references
    * all_name_nodes_list: a list of all name nodes in the module
    * scope: the scopes of the module

    """
    reference_list = _create_references(all_name_nodes_list, scope, name_nodes)  # contains a list of all referenced symbols for each node in the module

    # print(reference_list)

    for ref in reference_list:
        _get_symbols(ref)

    # print(reference_list)

    # welcher scope sind wir gerade
    # entsprechend dem Scope die zugehörigen Symbole finden

    return reference_list


def _get_symbols(node: NodeReference) -> None:
    for i, symbol in enumerate(node.referenced_symbols):
        for nod in node.scope.children:
            if nod.id.name == symbol.name:
                parent_node = nod.parent
                specific_symbol = add_specific_symbols(parent_node, symbol)
                node.referenced_symbols[i] = specific_symbol

            # sonst, suche im höheren scope weiter
            # sonst, gebe einen Fehler aus


def add_specific_symbols(parent_node: Scope | ClassScope, symbol: Symbol) -> Symbol:
    if isinstance(parent_node.node, astroid.Module):
        return GlobalVariable(symbol.node, symbol.name)
    elif isinstance(parent_node.node, astroid.ClassDef):
        if parent_node.node:
            return ClassVariable(symbol.node, symbol.name)
    elif isinstance(parent_node.node, astroid.FunctionDef):
        return LocalVariable(symbol.node, symbol.name)
        # if function def body contains global node -> check if name node is in global node
        # if the name node is in the global node -> global variable
        # TODO: check if name node is in global node
    elif isinstance(parent_node.node, astroid.Arguments):
        return Parameter(symbol.node, symbol.name)  # TODO: how can we check if the name node is a parameter?  maybe we can add an identifier as we built the ast
    else:
        return symbol
    # TODO: find globals defined in lower scopes ("global" keyword)


def _get_scope(code: str) -> tuple[list[Scope | ClassScope], dict[astroid.Name, Scope]]:  # TODO: this could return ScopeNode | ClassScopeNode since a module can only contain one node?
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
    print(module.repr_tree())
    walker.walk(module)

    names = scope_handler.name_nodes

    scopes = scope_handler.children  # get the children of the root node, which are the scopes of the module
    scope_handler.children = []  # reset the children
    scope_handler.current_node_stack = []  # reset the stack

    return scopes, names


def resolve_references(code: str) -> list[list[NodeReference]]:
    scope = _get_scope(code)
    name_nodes_list = _get_name_nodes(code)
    references: list[list[NodeReference]] = []
    for name_node in name_nodes_list:
        references.append(_find_references(name_node, name_nodes_list, scope[0], scope[1]))

    return references
