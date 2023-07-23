from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field

import astroid
from astroid import Name, FunctionDef, AssignName

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

    def __str__(self) -> str:
        return f"{self.module}.{self.name}.{self.line}.{self.col}"


@dataclass
class Variables:
    class_variables: list[astroid.AssignName] | None
    instance_variables: list[astroid.NodeNG] | None


@dataclass
class Symbol(ABC):
    node: astroid.NodeNG
    id: NodeID
    name: str

    def __str__(self):
        return f"{self.__class__.__name__}.{self.name}.line{self.id.line}"


@dataclass
class Parameter(Symbol):  # TODO: find correct node type and add fields with further infos for each subclass
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
        _node        is the node in the AST that defines the scope of the node.
        _id          is the id of the node.
        _children    is a list of Scope or ClassScope instances that are defined in the scope of the node, is None if the node is a leaf node.
        _parent      is the parent node in the scope tree, is None if the node is the root node.
    """

    _node: astroid.Module | astroid.FunctionDef | astroid.ClassDef | astroid.Name | astroid.AssignName | astroid.AssignAttr | astroid.Attribute | astroid.Import | astroid.ImportFrom | MemberAccess
    _id: NodeID
    _children: list[Scope | ClassScope] = field(default_factory=list)
    _parent: Scope | ClassScope | None = None

    def __iter__(self):
        yield self

    @property
    def node(self):
        return self._node

    @node.setter
    def node(self, new_node):
        if not isinstance(new_node, (astroid.Module, astroid.FunctionDef, astroid.ClassDef, astroid.Name,
                                     astroid.AssignName, astroid.AssignAttr, astroid.Attribute,
                                     astroid.Import, astroid.ImportFrom, MemberAccess)):
            raise ValueError("Invalid node type.")
        self._node = new_node

    @property
    def id(self):
        return self._id

    @property
    def children(self):
        return self._children

    @children.setter
    def children(self, new_children):
        if not isinstance(new_children, list):
            raise ValueError("Children must be a list.")
        self._children = new_children

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, new_parent):
        if not isinstance(new_parent, (Scope, ClassScope, type(None))):
            raise ValueError("Invalid parent type.")
        self._parent = new_parent


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
class ReferenceNode:
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
    name_nodes: dict[astroid.Name, Scope | ClassScope] = field(default_factory=dict)
    function_parameters: dict[astroid.FunctionDef, tuple[Scope | ClassScope, list[astroid.AssignName]]] = field(default_factory=dict)
    global_variables: dict[str, Scope | ClassScope] = field(default_factory=dict)
    # TODO: do we need to store ClassDefs and FunctionDefs as global variables?

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
            Scope(_node=node, _id=_calc_node_id(node), _children=[], _parent=None),
        )
        # self.global_variables[node] = node.globals

    def leave_module(self, node: astroid.Module) -> None:
        self._detect_scope(node)

    def enter_classdef(self, node: astroid.ClassDef) -> None:
        self.current_node_stack.append(
            ClassScope(
                _node=node,
                _id=_calc_node_id(node),
                _children=[],
                _parent=self.current_node_stack[-1],
                instance_variables=[],
                class_variables=[],
            ),
        )

    def leave_classdef(self, node: astroid.ClassDef) -> None:
        self._detect_scope(node)

    def enter_functiondef(self, node: astroid.FunctionDef) -> None:
        self.current_node_stack.append(
            Scope(_node=node, _id=_calc_node_id(node), _children=[], _parent=self.current_node_stack[-1]),
        )
        if node.name == "__init__":
            self._analyze_constructor(node)

    def leave_functiondef(self, node: astroid.FunctionDef) -> None:
        self._detect_scope(node)

    def enter_arguments(self, node: astroid.Arguments) -> None:
        if node.args:
            self.function_parameters[self.current_node_stack[-1].node] = (self.current_node_stack[-1], node.args)
        if node.kwonlyargs:
            self.function_parameters[self.current_node_stack[-1].node] = (self.current_node_stack[-1], node.kwonlyargs)
        if node.posonlyargs:
            self.function_parameters[self.current_node_stack[-1].node] = (self.current_node_stack[-1], node.posonlyargs)

    def enter_name(self, node: astroid.Name) -> None:  # TODO: this could be more efficient if unnecessary nodes are not added to the dict
        # if isinstance(
        #     node.parent,
        #     astroid.Assign
        #     | astroid.AugAssign
        #     | astroid.Return
        #     | astroid.Compare
        #     | astroid.For
        #     | astroid.BinOp
        #     | astroid.BoolOp
        #     | astroid.UnaryOp
        # ):
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
            scope_node = Scope(_node=node, _id=_calc_node_id(node), _children=[], _parent=parent)
            self.children.append(scope_node)

        # add class variables to the class_variables list of the class
        if isinstance(node.parent.parent, astroid.ClassDef):
            class_node = self.get_node_by_name(node.parent.parent.name)
            if isinstance(class_node, ClassScope):
                class_node.class_variables.append(node)
        # if isinstance(node.parent.parent, astroid.Module):
        #     self.global_variables[node] = self.current_node_stack[-1]

    def enter_assignattr(self, node: astroid.AssignAttr) -> None:
        parent = self.current_node_stack[-1]
        scope_node = Scope(_node=node, _id=_calc_node_id(node), _children=[], _parent=parent)
        self.children.append(scope_node)

    def enter_global(self, node: astroid.Global) -> None:
        for name in node.names:
            self.global_variables[name] = self.current_node_stack[-1]

    def enter_import(self, node: astroid.Import) -> None:  # TODO: handle multiple imports and aliases
        parent = self.current_node_stack[-1]
        scope_node = Scope(_node=node, _id=_calc_node_id(node), _children=[], _parent=parent)
        self.children.append(scope_node)

    def enter_importfrom(self, node: astroid.ImportFrom) -> None:  # TODO: handle multiple imports and aliases
        parent = self.current_node_stack[-1]
        scope_node = Scope(_node=node, _id=_calc_node_id(node), _children=[], _parent=parent)
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
            | astroid.BoolOp
            | astroid.UnaryOp
            | astroid.Match
            | astroid.Tuple
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
            walker.walk(node)
            name_nodes.extend(name_node_handler.names_list)
            name_node_handler.names_list = []

    return name_nodes


def _calc_node_id(
    node: astroid.NodeNG | astroid.Module | astroid.ClassDef | astroid.FunctionDef | astroid.AssignName | astroid.Name | astroid.AssignAttr | astroid.Import | astroid.ImportFrom | MemberAccess
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
        case astroid.NodeNG():
            return NodeID(module, node.as_string(), node.lineno, node.col_offset)
        case _:
            raise ValueError(f"Node type {node.__class__.__name__} is not supported yet.")

    # TODO: add fitting default case and merge same types of cases together


def get_scope_node_by_node_id(scope: Scope | list[Scope], targeted_node_id: NodeID, name_nodes: dict[astroid.Name] | None) -> Scope:
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


def _create_references(all_names_list: list[astroid.Name | astroid.AssignName],
                       scope: Scope,
                       name_nodes: dict[astroid.Name]) -> list[ReferenceNode]:
    """Create a list of references from a list of name nodes.

    Returns:
        * references_final: contains all references that are used as targets
    """
    references_proto: list[ReferenceNode] = []
    references_final: list[ReferenceNode] = []
    scope_node: Scope | None = field(default_factory=Scope)

    for name in all_names_list:
        node_id = _calc_node_id(name)  # TODO: is there a better way to connect the name to the scope node?
        if isinstance(name, astroid.AssignName):
            scope_node = get_scope_node_by_node_id(scope, node_id, None)
        elif isinstance(name, astroid.Name):
            scope_node = get_scope_node_by_node_id(scope, node_id, name_nodes)

        references_proto.append(ReferenceNode(name, scope_node, []))

    for reference in references_proto:
        if isinstance(reference.name, astroid.Name):
            target_ref = _add_target_references(reference, references_proto)
            references_final.append(target_ref)

    return references_final
    # TODO: sonderfälle mit AssignName müssen separat betrachtet werden (global) ?? was bedeutet das?


def _add_target_references(reference: ReferenceNode, reference_list: list[ReferenceNode]) -> ReferenceNode:
    """Add all target references to a reference.

    A target reference is a reference where the name is used as a target.
    Therefor we need to check all nodes further up the list where the name is used as a target.
    """
    complete_reference = reference
    if reference in reference_list:
        for ref in reference_list[:reference_list.index(reference)]:
            if isinstance(ref.name, MemberAccess):
                if ref.name.expression.as_string() == reference.name.name:
                    complete_reference.referenced_symbols.append(Symbol(ref.name, _calc_node_id(ref.name), ref.name.expression.as_string()))
            elif ref.name.name == reference.name.name and isinstance(ref.name, astroid.AssignName):
                complete_reference.referenced_symbols.append(Symbol(ref.name, _calc_node_id(ref.name), ref.name.name))

    return complete_reference


def _find_references(name_node: astroid.Name,
                     all_name_nodes_list: list[astroid.Name | astroid.AssignName],
                     scope: Scope,
                     name_nodes: dict[astroid.Name],
                     function_parameters: dict[astroid.FunctionDef, tuple[Scope | ClassScope, list[astroid.AssignName]]],
                     global_variables: dict[str, Scope | ClassScope]) -> list[ReferenceNode]:
    """Find all references for a node.

    Parameters:
    * name_node: the node for which we want to find all references
    * all_name_nodes_list: a list of all name nodes in the module
    * scope: the scopes of the module
    * name_nodes: a dict of all name nodes in the module
    * function_parameters: a dict of all function parameters for each function in the module
    * global_variables: a dict of all global variables in the module

    """
    references = _create_references(all_name_nodes_list, scope, name_nodes)  # contains a list of all referenced symbols for each node in the module

    for ref in references:
        _get_symbols(ref, function_parameters, global_variables)
        if ref.name == name_node:  # TODO: it would be more efficient to remove the node from the list before creating the references
            return [ref]

    # welcher scope sind wir gerade
    # entsprechend dem Scope die zugehörigen Symbole finden


def _get_symbols(node: ReferenceNode,
                 function_parameters: dict[astroid.FunctionDef, tuple[Scope | ClassScope, list[astroid.AssignName]]],
                 global_variables: dict[str, Scope | ClassScope]) -> None:

    for i, symbol in enumerate(node.referenced_symbols):
        for nod in node.scope.children:
            if nod.id.name == symbol.name:
                parent_node = nod.parent
                specified_symbol = specify_symbols(parent_node, symbol, function_parameters)
                node.referenced_symbols[i] = specified_symbol
        # TODO: ideally the functionality of the next block should be in the specify_symbols function
        if symbol.name in global_variables.keys():
            current_symbol_parent = global_variables.get(symbol.name)
            if current_symbol_parent is not None:
                if check_if_global_is_in_parent_scope(current_symbol_parent, symbol.node):
                    node.referenced_symbols[i] = GlobalVariable(symbol.node, symbol.id, symbol.name)
                else:
                    raise ValueError(f"Symbol {symbol.name} is not defined in the module scope")

            # sonst, suche im höheren scope weiter
            # sonst, gebe einen Fehler aus


def specify_symbols(parent_node: Scope | ClassScope, symbol: Symbol,
                    function_parameters: dict[astroid.FunctionDef, tuple[Scope | ClassScope, list[astroid.AssignName]]]) -> Symbol:
    if isinstance(parent_node.node, astroid.Module):
        return GlobalVariable(symbol.node, symbol.id, symbol.name)
    elif isinstance(parent_node.node, astroid.ClassDef):
        if parent_node.node:  # TODO: check if node is class attribute or instance attribute
            return ClassVariable(symbol.node, symbol.id, symbol.name)
        # if global_variables:
        #     for key in global_variables.keys():
        #         if key == symbol.name:
        #             return GlobalVariable(symbol.node, symbol.id, symbol.name)
    elif isinstance(parent_node.node, astroid.FunctionDef):
        if parent_node.node in function_parameters.keys():
            for param in function_parameters[parent_node.node][1]:
                if param.name == symbol.name:
                    return Parameter(symbol.node, symbol.id, symbol.name)

        return LocalVariable(symbol.node, symbol.id, symbol.name)
    else:
        return symbol


def check_if_global_is_in_parent_scope(scope: Scope | ClassScope, node: astroid.NodeNG) -> bool:
    if isinstance(scope.node, astroid.Module):
        for child in scope.children:
            if child.id == _calc_node_id(node):
                return True
        return False
    else:
        return check_if_global_is_in_parent_scope(scope.parent, node)


def _get_scope(code: str) -> tuple[Scope | ClassScope, dict[Name, Scope | ClassScope], dict[
        FunctionDef, tuple[Scope | ClassScope, list[AssignName]]], dict[str, Scope | ClassScope]]:
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

    scopes = scope_handler.children[0]  # get the children of the root node, which are the scopes of the module
    names = scope_handler.name_nodes  # get the name nodes of the module
    parameters = scope_handler.function_parameters  # get the parameters for each function of the module
    globs = scope_handler.global_variables  # get the global nodes of the module

    return scopes, names, parameters, globs


def resolve_references(code: str) -> list[ReferenceNode]:
    scope = _get_scope(code)
    name_nodes_list = _get_name_nodes(code)
    references: list[ReferenceNode] = []

    for name_node in name_nodes_list:
        if isinstance(name_node, astroid.Name):
            references_for_name_node = _find_references(name_node, name_nodes_list, scope[0], scope[1], scope[2], scope[3])
            references.extend(references_for_name_node)

    return references
