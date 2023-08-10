from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from types import BuiltinFunctionType

import astroid
import builtins
from astroid import Name, FunctionDef, AssignName

from library_analyzer.processing.api.model import Expression, Reference
from library_analyzer.utils import ASTWalker

BUILTINS = dir(builtins)


@dataclass
class ModuleData:
    """
    Contains all data that is collected for a module.

    scope: The module's scope, this contains all child scopes.
    classes: All classes and their scope.
    functions: All functions and their scope.
    globals: All global variables and their scope.
    names: All names that are defined in the module and their scope.
    parameters: All parameters of functions and their scope.
    names_list: All names that are defined in the module.
    function_calls: All function calls and their scope.
    """
    scope: Scope | ClassScope
    classes: dict[str, ClassScope]
    functions: dict[str, Scope | ClassScope]  # classScope should not be possible here: check that
    globals: dict[str, Scope | ClassScope]
    names: dict[Name, Scope | ClassScope]
    parameters: dict[FunctionDef, tuple[Scope | ClassScope, list[AssignName]]]
    names_list: list[astroid.Name | astroid.AssignName | MemberAccess]  # TODO: dict[str, tuple [astroid.Name astroid.AssignName | MemberAccess, Scope]]
    function_calls: list[tuple[astroid.Call, Scope | ClassScope]]  # TODO: dict dict[str, tuple[astroid.Call, Scope | ClassScope]]


@dataclass
class MemberAccess(Expression):
    expression: astroid.NodeNG
    value: MemberAccess | Reference
    parent: astroid.NodeNG | None = field(default=None)
    name: str = field(init=False)

    # TODO: when detecting MemberAccess, we will only search for the nodes name in all class scopes ->
    #  add a list of all classes of a module to easily access their instance nodes (their names)

    # def __str__(self):
    #     return f"{self.expression.name}.{self.value.name}"

    def __hash__(self):
        return hash(str(self))

    def __post_init__(self):
        if isinstance(self.expression, astroid.Call):
            self.expression = self.expression.func
        self.name = f"{self.expression.name}.{self.value.name}"


@dataclass
class MemberAccessTarget(MemberAccess):
    def __hash__(self):
        return hash(str(self))


@dataclass
class MemberAccessValue(MemberAccess):
    def __hash__(self):
        return hash(str(self))


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
    node: Scope | ClassScope
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
class Builtin(Symbol):
    def __str__(self):
        return f"{self.__class__.__name__}.{self.name}"


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

    def root(self) -> Scope | ClassScope:
        if self.parent:
            return self.parent.root()
        return self

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
    super_classes: list[ClassScope] | None = field(default=None)


@dataclass
class ReferenceNode:
    name: astroid.Name | astroid.AssignName | astroid.Call | MemberAccess | str
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
    classes: dict[str, ClassScope] = field(default_factory=dict)
    functions: dict[str, Scope | ClassScope] = field(default_factory=dict)
    name_nodes: dict[astroid.Name | MemberAccess, Scope | ClassScope] = field(default_factory=dict)
    global_variables: dict[str, Scope | ClassScope] = field(default_factory=dict)
    function_parameters: dict[astroid.FunctionDef, tuple[Scope | ClassScope, list[astroid.AssignName]]] = field(
        default_factory=dict)
    names_list: list[astroid.Name | astroid.AssignName | MemberAccess] = field(default_factory=list)
    function_calls: list[tuple[astroid.Call, Scope | ClassScope]] = field(default_factory=list)


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
        if isinstance(node, astroid.ClassDef):
            self.classes[node.name] = self.current_node_stack[-1]
        if isinstance(node, astroid.FunctionDef):
            self.functions[node.name] = self.current_node_stack[-1]
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
                super_classes=self.find_base_classes(node),
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

    def enter_name(self,
                   node: astroid.Name) -> None:
        self.name_nodes[node] = self.current_node_stack[-1]  # TODO: this could be more efficient if unnecessary nodes are not added to the dict

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
            | astroid.Subscript
            | astroid.FormattedValue
            | astroid.Keyword
            | astroid.Expr
        ):
            self.names_list.append(node)
        if (
            isinstance(node.parent, astroid.Call)
            and isinstance(node.parent.func, astroid.Name)
            and node.parent.func.name != node.name
        ):
            # append a node only then when it is not the name node of the function
            self.names_list.append(node)

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
            | astroid.For
            | astroid.Tuple
            | astroid.NamedExpr
        ):
            self.names_list.append(node)

        if isinstance(node.parent, astroid.Arguments) and node.name == "self":
            pass  # TODO: Special treatment for self parameter

        elif isinstance(
            node.parent,
            astroid.Assign
            | astroid.Arguments
            | astroid.AssignAttr
            | astroid.Attribute
            | astroid.AugAssign
            | astroid.AnnAssign
            | astroid.Tuple
            | astroid.For
            | astroid.NamedExpr
        ):
            parent = self.current_node_stack[-1]
            scope_node = Scope(_node=node, _id=_calc_node_id(node), _children=[], _parent=parent)
            self.children.append(scope_node)

        # add class variables to the class_variables list of the class
        if isinstance(node.parent.parent, astroid.ClassDef):
            class_node = self.get_node_by_name(node.parent.parent.name)
            if isinstance(class_node, ClassScope):
                class_node.class_variables.append(node)

    def enter_assignattr(self, node: astroid.AssignAttr) -> None:
        parent = self.current_node_stack[-1]
        member_access = _construct_member_access(node)
        scope_node = Scope(_node=member_access, _id=_calc_node_id(node), _children=[], _parent=parent)
        self.children.append(scope_node)
        self.name_nodes[member_access] = self.current_node_stack[-1]

        self.names_list.append(member_access)

    def enter_attribute(self, node: astroid.Attribute) -> None:
        member_access = _construct_member_access(node)
        self.name_nodes[member_access] = self.current_node_stack[-1]

        self.names_list.append(member_access)

    def enter_global(self, node: astroid.Global) -> None:
        for name in node.names:
            if self.check_if_global(name, node):
                self.global_variables[name] = self.current_node_stack[-1]

    def enter_call(self, node: astroid.Call) -> None:
        if isinstance(node.func, astroid.Name):
            self.function_calls.append((node, self.current_node_stack[-1]))
        # print(node.func.name)

    def enter_import(self, node: astroid.Import) -> None:  # TODO: handle multiple imports and aliases
        parent = self.current_node_stack[-1]
        scope_node = Scope(_node=node, _id=_calc_node_id(node), _children=[], _parent=parent)
        self.children.append(scope_node)

    def enter_importfrom(self, node: astroid.ImportFrom) -> None:  # TODO: handle multiple imports and aliases
        parent = self.current_node_stack[-1]
        scope_node = Scope(_node=node, _id=_calc_node_id(node), _children=[], _parent=parent)
        self.children.append(scope_node)

    def check_if_global(self, name: str, node: astroid.NodeNG) -> bool:
        """
        Checks if a name is a global variable inside the root of the given node
        Returns True if the name is listed in root.globals dict, False otherwise
        """
        if not isinstance(node, astroid.Module):
            return self.check_if_global(name, node.parent)
        else:
            if name in node.globals:
                return True

    def find_base_classes(self, node: astroid.ClassDef) -> list[ClassScope]:
        """
        Returns a list of all base classes of the given class
        """
        base_classes = []
        for base in node.bases:
            if isinstance(base, astroid.Name):
                base_class = self.get_class_by_name(base.name)
                if isinstance(base_class, ClassScope):
                    base_classes.append(base_class)
        return base_classes

    def get_class_by_name(self, name: str) -> ClassScope | None:
        """
        Returns the class with the given name
        """
        for klass in self.classes:
            if klass == name:
                return self.classes[klass]
        return None


def _construct_member_access(node: astroid.Attribute | astroid.AssignAttr) -> MemberAccess:
    if isinstance(node, astroid.Attribute):
        if isinstance(node.expr, astroid.Attribute | astroid.AssignAttr):
            return MemberAccessValue(_construct_member_access(node.expr), Reference(node.attrname))
        else:
            return MemberAccessValue(node.expr, Reference(node.attrname))
    elif isinstance(node, astroid.AssignAttr):
        if isinstance(node.expr, astroid.Attribute | astroid.AssignAttr):
            return MemberAccessTarget(_construct_member_access(node.expr), Reference(node.attrname))
        else:
            return MemberAccessTarget(node.expr, Reference(node.attrname))


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
            # TODO: check if the MemberAccess is nested
            return NodeID(module, f"{node.expression.name}.{node.value.name}", node.expression.lineno,
                          node.expression.col_offset)
        case astroid.Import():  # TODO: we need a special treatment for imports and import from
            return NodeID(module, node.names[0][0], node.lineno, node.col_offset)
        case astroid.ImportFrom():
            return NodeID(module, node.names[0][1], node.lineno, node.col_offset)
        case astroid.AssignAttr():
            return NodeID(module, node.attrname, node.lineno, node.col_offset)
        case astroid.Call():
            return NodeID(module, node.func.name, node.lineno, node.col_offset)
        case astroid.NodeNG():
            return NodeID(module, node.as_string(), node.lineno, node.col_offset)
        case _:
            raise ValueError(f"Node type {node.__class__.__name__} is not supported yet.")

    # TODO: add fitting default case and merge same types of cases together


def get_scope_node_by_node_id(scope: Scope | list[Scope], targeted_node_id: NodeID,
                              name_nodes: dict[astroid.Name] | None) -> Scope:
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


def _create_unspecified_references(all_names_list: list[astroid.Name | astroid.AssignName | MemberAccess],
                                   scope: Scope,
                                   name_nodes: dict[astroid.Name],
                                   classes: dict[str, ClassScope]) -> list[ReferenceNode]:
    """Create a list of references from a list of name nodes.

    Returns:
        * references_final: contains all references that are used as targets
    """
    references_proto: list[ReferenceNode] = []
    references_final: list[ReferenceNode] = []
    scope_node: Scope | None = field(default_factory=Scope)

    for name in all_names_list:
        node_id = _calc_node_id(name)
        if isinstance(name, astroid.AssignName):
            scope_node = get_scope_node_by_node_id(scope, node_id, None)
        elif isinstance(name, astroid.Name):
            scope_node = get_scope_node_by_node_id(scope, node_id, name_nodes)
        elif isinstance(name, MemberAccess):
            scope_node = get_scope_node_by_node_id(scope, node_id, name_nodes)

        references_proto.append(ReferenceNode(name, scope_node, []))

    for reference in references_proto:
        if isinstance(reference.name, astroid.Name | MemberAccessValue):
            target_ref = _add_target_references(reference, references_proto, classes)
            references_final.append(target_ref)

    return references_final


def _add_target_references(reference: ReferenceNode, reference_list: list[ReferenceNode], classes: dict[str, ClassScope]) -> ReferenceNode:
    """Add all target references to a reference.

    A target reference is a reference where the name is used as a target.
    Therefor we need to check all nodes further up the list where the name is used as a target.
    """
    complete_reference = reference
    if reference in reference_list:
        for ref in reference_list:
            if isinstance(ref.name, MemberAccessValue):
                root = ref.scope.root()
                if isinstance(root.node, astroid.Module):
                    for class_scope in classes.values():
                        # print(class_scope)
                        for variable in class_scope.class_variables:
                            if reference.name.value.name == variable.name:
                                # print(variable.name)
                                complete_reference.referenced_symbols.append(
                                    ClassVariable(node=class_scope, id=_calc_node_id(variable),
                                                  name=f"{class_scope.node.name}.{variable.name}"))

            if isinstance(ref.name, MemberAccessTarget) and isinstance(reference.name, MemberAccessValue):
                if ref.name.name == reference.name.name:
                    complete_reference.referenced_symbols.append(
                        ClassVariable(node=ref.scope, id=_calc_node_id(ref.name), name=ref.name.name))

            elif isinstance(ref.name, astroid.AssignName) and ref.name.name == reference.name.name:
                complete_reference.referenced_symbols.append(
                    Symbol(node=ref.scope, id=_calc_node_id(ref.name), name=ref.name.name))

    return complete_reference


def _find_references(name_node: astroid.Name,
                     references: list[ReferenceNode],
                     module_data: ModuleData) -> list[ReferenceNode]:
    """Find all references for a node.

    Parameters:
    * name_node: the node for which we want to find all references
    * all_name_nodes_list: a list of all name nodes in the module
    * module_data: the data of the module
    """

    for i, ref in enumerate(references):
        if isinstance(ref.name or name_node, MemberAccess):
            if ref.name.name == name_node.name:
                return [_get_symbols(ref, ref.scope, module_data.parameters, module_data.globals)]
        if ref.name == name_node:
            return [_get_symbols(ref, ref.scope, module_data.parameters, module_data.globals)]


def _get_symbols(node: ReferenceNode,
                 current_scope: Scope | ClassScope,
                 function_parameters: dict[astroid.FunctionDef, tuple[Scope | ClassScope, list[astroid.AssignName]]],
                 global_variables: dict[str, Scope | ClassScope]) -> ReferenceNode:
    try:
        for i, symbol in enumerate(node.referenced_symbols):
            if current_scope.children:
                for nod in current_scope.children:
                    if isinstance(nod.node, MemberAccessTarget) and nod.node.name == symbol.name:
                        parent_node = nod.parent
                        specified_symbol = specify_symbols(parent_node, symbol, function_parameters)
                        node.referenced_symbols[i] = specified_symbol

                    elif isinstance(nod.node, astroid.AssignName) and nod.node.name == symbol.name:
                        parent_node = nod.parent
                        specified_symbol = specify_symbols(parent_node, symbol, function_parameters)
                        node.referenced_symbols[i] = specified_symbol

                # if not isinstance(current_scope.parent, NoneType):
                #     return _get_symbols(node, current_scope.parent, function_parameters, global_variables)

                #  would fix: "for loop with local runtime variable local scope" but break other case
            else:
                return _get_symbols(node, current_scope.parent, function_parameters, global_variables)
            # TODO: ideally the functionality of the next block should be in the specify_symbols function
            if symbol.name in global_variables.keys():
                current_symbol_parent = global_variables.get(symbol.name)
                if current_symbol_parent is not None:
                    node.referenced_symbols[i] = GlobalVariable(symbol.node, symbol.id, symbol.name)
        return node
    except ChildProcessError:
        raise ChildProcessError(f"Parent node {node.scope.node.name} of {node.name.name} does not have any (detected) children.")


def specify_symbols(parent_node: Scope | ClassScope,
                    symbol: Symbol,
                    function_parameters: dict[
                        astroid.FunctionDef, tuple[Scope | ClassScope, list[astroid.AssignName]]]) -> Symbol:
    if isinstance(symbol, ClassVariable | InstanceVariable | Parameter | GlobalVariable):
        return symbol
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
        if isinstance(symbol.node.parent.node, astroid.Module):
            return GlobalVariable(symbol.node, symbol.id, symbol.name)

        return LocalVariable(symbol.node, symbol.id, symbol.name)
    else:
        return symbol


def _get_module_data(code: str) -> ModuleData:
    """Get the module data of the given code.

    In order to get the module data of the given code, the code is parsed into an AST and then walked by an ASTWalker.
    The ASTWalker detects the scope of each node and builds a scope tree by using an instance of ScopeFinder.
    The ScopeFinder also collects all name nodes, parameters, global variables, classes and functions of the module.
    """
    scope_handler = ScopeFinder()
    walker = ASTWalker(scope_handler)
    module = astroid.parse(code)
    print(module.repr_tree())
    walker.walk(module)

    scope = scope_handler.children[0]  # get the children of the root node, which are the scopes of the module

    return ModuleData(scope=scope,
                      classes=scope_handler.classes,
                      functions=scope_handler.functions,
                      globals=scope_handler.global_variables,
                      names=scope_handler.name_nodes,
                      parameters=scope_handler.function_parameters,
                      names_list=scope_handler.names_list,
                      function_calls=scope_handler.function_calls)


def _find_call_reference(function_calls: list[tuple[astroid.Call, Scope | ClassScope]],
                         classes: dict[str, ClassScope],
                         scope: Scope,
                         functions: dict[str, Scope | ClassScope]) -> list[ReferenceNode]:

    references_proto: list[ReferenceNode] = []
    references_final: list[ReferenceNode] = []
    scope_node: Scope | None = field(default_factory=Scope)
    global BUILTINS

    for call in function_calls:
        if isinstance(call[0].func, astroid.Name):
            if call[0].func.name in functions.keys() or call[0].func.name in BUILTINS or call[0].func.name in classes.keys():
                node_id = _calc_node_id(call[1].node)
                scope_node = get_scope_node_by_node_id_call(node_id, scope)

            references_proto.append(ReferenceNode(call[0], scope_node, []))

    for i, reference in enumerate(references_proto):
        func_name = reference.name.func.name
        if func_name in BUILTINS and func_name not in functions.keys() and func_name not in classes.keys():
            references_final.append(ReferenceNode(reference.name, reference.scope, [
                Builtin(reference.scope, NodeID("builtins", func_name, 0, 0),
                        func_name)]))
        elif isinstance(reference.name, astroid.Call):
            func_def = _get_function_def(reference, functions, classes)
            references_final.append(func_def)
            if func_name in BUILTINS:
                references_final[i].referenced_symbols.append(Builtin(reference.scope, NodeID("builtins", func_name, 0, 0), func_name))

    return references_final


def _get_function_def(reference: ReferenceNode, functions: dict[str, Scope | ClassScope], classes: dict[str, ClassScope]) -> ReferenceNode:
    if functions:
        for func in functions.values():
            if func.node.name == reference.name.func.name:
                return ReferenceNode(reference.name, reference.scope, [GlobalVariable(func, func.id, func.node.name)])
    if classes:
        for klass in classes.values():
            if klass.node.name == reference.name.func.name:
                return ReferenceNode(reference.name, reference.scope, [GlobalVariable(klass, klass.id, klass.node.name)])
    raise ChildProcessError(f"Function {reference.name.func.name} not found in functions.")


def get_scope_node_by_node_id_call(targeted_node_id: NodeID,
                                   scope: Scope) -> Scope:
    if scope.id == targeted_node_id:
        return scope
    else:
        for child in scope.children:
            if child.id == targeted_node_id:
                return child
            else:
                return get_scope_node_by_node_id_call(targeted_node_id, child)


def resolve_references(code: str) -> list[ReferenceNode]:
    module_data = _get_module_data(code)
    references_specified: list[ReferenceNode] = []

    references_unspecified = _create_unspecified_references(module_data.names_list, module_data.scope,
                                                            module_data.names, module_data.classes)

    references_call = _find_call_reference(module_data.function_calls, module_data.classes, module_data.scope, module_data.functions)
    references_specified.extend(references_call)

    for name_node in module_data.names_list:
        if isinstance(name_node, astroid.Name | MemberAccessValue):
            references_for_name_node = _find_references(name_node, references_unspecified, module_data)
            references_specified.extend(references_for_name_node)

    return references_specified
