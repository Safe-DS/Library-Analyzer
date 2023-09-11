from __future__ import annotations

from dataclasses import dataclass, field

import astroid

from library_analyzer.utils import ASTWalker
from library_analyzer.processing.api.model import (
    ModuleData,
    Scope,
    ClassScope,
    MemberAccess,
    NodeID,
    MemberAccessTarget,
    MemberAccessValue,
    Symbol,
    GlobalVariable,
    LocalVariable,
    ClassVariable,
    Parameter,
    InstanceVariable,
    Import,
)


@dataclass
class ModuleDataBuilder:
    """
    A ScopeFinder instance is used to find the scope of a reference.

    The scope of a reference is the node in the scope tree that defines the reference.
    It is determined by walking the AST and checking if the reference is defined in the scope of the current node.

    Attributes
    ----------
        current_node_stack      stack of nodes that are currently visited by the ASTWalker.
        children:               All found children nodes are stored in children until their scope is determined.
        classes:                dict of all classes in the module and their corresponding ClassScope instance.
        functions:              dict of all functions in the module and their corresponding Scope or ClassScope instance.
        value_nodes:            dict of all nodes that are used as a value and their corresponding Scope or ClassScope instance.
        target_nodes:           dict of all nodes that are used as a target and their corresponding Scope or ClassScope instance.
        global_variables:       dict of all global variables and their corresponding Scope or ClassScope instance.
        parameters:             dict of all parameters and their corresponding Scope or ClassScope instance.
        function_calls:         dict of all function calls and their corresponding Scope or ClassScope instance.
    """

    current_node_stack: list[Scope | ClassScope] = field(default_factory=list)
    children: list[Scope | ClassScope] = field(default_factory=list)
    classes: dict[str, ClassScope] = field(default_factory=dict)
    functions: dict[str, Scope | list[Scope]] = field(default_factory=dict)
    value_nodes: dict[astroid.Name | MemberAccessValue, Scope | ClassScope] = field(default_factory=dict)
    target_nodes: dict[astroid.AssignName | astroid.Name | MemberAccessTarget, Scope | ClassScope] = field(default_factory=dict)
    global_variables: dict[str, Scope | ClassScope] = field(default_factory=dict)
    parameters: dict[astroid.FunctionDef, tuple[Scope | ClassScope, set[astroid.AssignName]]] = field(default_factory=dict)
    function_calls: dict[astroid.Call, Scope | ClassScope] = field(default_factory=dict)

    def get_node_by_name(self, name: str) -> Scope | ClassScope | None:
        """
        Get a ScopeNode by its name.

        Parameters
        ----------
            name    is the name of the node that should be found.

        Returns
        -------
            The Scope or ClassScope with the given name, or None if no node with the given name was found.
        """
        for node in self.current_node_stack:
            if node.symbol.node.name == name:
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
                child.parent is not None and child.parent.symbol.node != current_scope
            ):  # check if the child is in the scope of the current node
                outer_scope_children.append(child)  # add the child to the outer scope
            else:
                inner_scope_children.append(child)  # add the child to the inner scope

        self.current_node_stack[-1].children = inner_scope_children  # set the children of the current node
        self.children = outer_scope_children  # keep the children that are not in the scope of the current node
        self.children.append(self.current_node_stack[-1])  # add the current node to the children
        if isinstance(node, astroid.ClassDef):
            self.classes[node.name] = self.current_node_stack[-1]

        # add functions to the functions dict
        # if a function is defined multiple times (same name), the function is added to the functions dict as a list
        if isinstance(node, astroid.FunctionDef):
            if node.name in self.functions.keys():
                if not isinstance(self.functions[node.name], list):
                    self.functions[node.name] = [self.functions.get(node.name)]
                self.functions[node.name].append(self.current_node_stack[-1])
            else:
                self.functions[node.name] = self.current_node_stack[-1]

        # add lambda functions to the functions dict
        # if a function is defined multiple times (same name), the function is added to the functions dict as a list
        if isinstance(node, astroid.Lambda) and isinstance(node.parent, astroid.Assign):
            node_name = node.parent.targets[0].name
            if node_name in self.functions.keys():
                if not isinstance(self.functions[node_name], list):
                    self.functions[node_name] = [self.functions.get(node_name)]
                self.functions[node_name].append(self.current_node_stack[-1])
            else:
                self.functions[node_name] = self.current_node_stack[-1]

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
                    class_node.instance_variables[child.targets[0].attrname] = child.targets[0]
                elif isinstance(child, astroid.AnnAssign):
                    class_node.instance_variables[child.target.attrname] = child.target
                else:
                    raise TypeError(f"Unexpected node type {type(child)}")

    def enter_module(self, node: astroid.Module) -> None:
        """
        Enter a module node.

        The module node is the root node, so it has no parent (parent is None).
        The module node is also the first node that is visited, so the current_node_stack is empty before entering the module node.
        """
        self.current_node_stack.append(
            Scope(_symbol=self.get_symbol(node, None),
                  _children=[],
                  _parent=None),
        )

    def leave_module(self, node: astroid.Module) -> None:
        self._detect_scope(node)

    def enter_classdef(self, node: astroid.ClassDef) -> None:

        self.current_node_stack.append(
            ClassScope(
                _symbol=self.get_symbol(node, self.current_node_stack[-1].symbol.node),
                _children=[],
                _parent=self.current_node_stack[-1],
                instance_variables={},
                class_variables={},
                super_classes=self.find_base_classes(node),
            ),
        )

    def leave_classdef(self, node: astroid.ClassDef) -> None:
        self._detect_scope(node)

    def enter_functiondef(self, node: astroid.FunctionDef) -> None:
        self.current_node_stack.append(
            Scope(_symbol=self.get_symbol(node, self.current_node_stack[-1].symbol.node),
                  _children=[],
                  _parent=self.current_node_stack[-1]),
        )
        if node.name == "__init__":
            self._analyze_constructor(node)

    def leave_functiondef(self, node: astroid.FunctionDef) -> None:
        self._detect_scope(node)

    def get_symbol(self, node: astroid.NodeNG, current_scope: astroid.NodeNG | None) -> Symbol:
        match current_scope:
            case astroid.Module() | None:
                if isinstance(node, astroid.Import):
                    return Import(node=node, id=_calc_node_id(node), name=node.names[0][0])  # TODO: this needs fixing when multiple imports are handled
                if isinstance(node, astroid.ImportFrom):
                    return Import(node=node, id=_calc_node_id(node), name=node.names[0][1])  # TODO: this needs fixing when multiple imports are handled
                if isinstance(node, MemberAccessTarget):
                    klass = self.get_class_for_receiver_node(node.receiver)
                    if klass is not None:
                        if node.member.attrname in klass.class_variables:  # this means that we are dealing with a class variable
                            return ClassVariable(node=node, id=_calc_node_id(node), name=node.member.attrname, klass=klass.symbol.node)
                    # this means that we are dealing with an instance variable
                    elif self.classes is not None:
                        for klass in self.classes.values():
                            if node.member.attrname in klass.instance_variables.keys():
                                return InstanceVariable(node=node, id=_calc_node_id(node), name=node.member.attrname, klass=klass.symbol.node)
                return GlobalVariable(node=node, id=_calc_node_id(node), name=node.name)

            case astroid.ClassDef():
                # we defined that functions are class variables if they are defined in the class scope
                # if isinstance(node, astroid.FunctionDef):
                #     return LocalVariable(node=node, id=_calc_node_id(node), name=node.name)
                return ClassVariable(node=node, id=_calc_node_id(node), name=node.name, klass=current_scope)

            case astroid.FunctionDef():
                if isinstance(current_scope, astroid.FunctionDef):
                    if current_scope.name == "__init__":
                        if isinstance(node, MemberAccessTarget):
                            return InstanceVariable(node=node, id=_calc_node_id(node), name=node.member.attrname, klass=current_scope.parent)
                if isinstance(node, astroid.AssignName) and self.parameters:
                    if current_scope in self.parameters and self.parameters[current_scope][1].__contains__(node):
                        return Parameter(node=node, id=_calc_node_id(node), name=node.name)
                return LocalVariable(node=node, id=_calc_node_id(node), name=node.name)

            case astroid.Lambda():
                return LocalVariable(node=node, id=_calc_node_id(node), name=node.name)

        return Symbol(node=node, id=_calc_node_id(node), name=node.name)

    def enter_lambda(self, node: astroid.Lambda) -> None:
        self.current_node_stack.append(
            Scope(_symbol=self.get_symbol(node, self.current_node_stack[-1].symbol.node),
                  _children=[],
                  _parent=self.current_node_stack[-1]),
        )

    def leave_lambda(self, node: astroid.Lambda) -> None:
        self._detect_scope(node)

    def enter_arguments(self, node: astroid.Arguments) -> None:
        if node.args:
            self.parameters[self.current_node_stack[-1].symbol.node] = (self.current_node_stack[-1], set(node.args))
        if node.kwonlyargs:
            self.parameters[self.current_node_stack[-1].symbol.node] = (self.current_node_stack[-1], set(node.kwonlyargs))
        if node.posonlyargs:
            self.parameters[self.current_node_stack[-1].symbol.node] = (self.current_node_stack[-1], set(node.posonlyargs))
        if node.vararg:
            constructed_node = astroid.AssignName(name=node.vararg, parent=node, lineno=node.parent.lineno,
                                                  col_offset=node.parent.col_offset)
            # TODO: col_offset is not correct: it should be the col_offset of the vararg/(kwarg) node which is not
            #  collected by astroid
            self.handle_arg(constructed_node)
        if node.kwarg:
            constructed_node = astroid.AssignName(name=node.kwarg, parent=node, lineno=node.parent.lineno,
                                                  col_offset=node.parent.col_offset)
            self.handle_arg(constructed_node)

    def enter_name(self,
                   node: astroid.Name) -> None:
        if isinstance(node.parent, astroid.Decorators) or isinstance(node.parent.parent, astroid.Decorators):
            return

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
            | astroid.Comprehension
            | astroid.Attribute
        ):
            if node.name == "self":
                return
            # the following if statement is necessary to avoid adding the same node to
            # both the target_nodes and the value_nodes dict since there is a case where a name node is used as a
            # target we need to check if the node is already in the target_nodes dict this is only the case if the
            # name node is the receiver of a MemberAccessTarget node it is made sure that in this case the node is
            # definitely in the target_nodes dict because the MemberAccessTarget node is added to the dict before the
            # name node
            if node not in self.target_nodes:
                self.value_nodes[node] = self.current_node_stack[-1]

        elif isinstance(node.parent, astroid.AssignAttr):
            if node.name == "self":
                return
            self.target_nodes[node] = self.current_node_stack[-1]
        if (
            isinstance(node.parent, astroid.Call)
            and isinstance(node.parent.func, astroid.Name)
            and node.parent.func.name != node.name
        ):
            # append a node only then when it is not the name node of the function
            self.value_nodes[node] = self.current_node_stack[-1]

    def enter_assignname(self, node: astroid.AssignName) -> None:
        # we do not want lambda assignments to be added to the target_nodes dict because they are handled as functions
        if isinstance(node.parent, astroid.Assign) and isinstance(node.parent.value, astroid.Lambda):
            return
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
            | astroid.Starred
        ):
            self.target_nodes[node] = self.current_node_stack[-1]

        if isinstance(node.parent, astroid.Arguments) and node.name == "self":
            pass  # TODO: Special treatment for self parameter
            # here self stance for the first implicit parameter of a class methode.
            # we need to check all possible names here, because it is not bound to be "self"

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
            | astroid.Starred
        ):
            parent = self.current_node_stack[-1]
            scope_node = Scope(_symbol=self.get_symbol(node, self.current_node_stack[-1].symbol.node),
                               _children=[],
                               _parent=parent)
            self.children.append(scope_node)

        # add class variables to the class_variables list of the class
        if isinstance(node.parent.parent, astroid.ClassDef):
            class_node = self.get_node_by_name(node.parent.parent.name)
            if isinstance(class_node, ClassScope):
                class_node.class_variables[node.name] = node

    def enter_assignattr(self, node: astroid.AssignAttr) -> None:
        parent = self.current_node_stack[-1]
        member_access = _construct_member_access_target(node.expr, node)
        scope_node = Scope(_symbol=self.get_symbol(member_access, self.current_node_stack[-1].symbol.node),
                           _children=[],
                           _parent=parent)
        self.children.append(scope_node)

        if isinstance(member_access, MemberAccessTarget):
            self.target_nodes[member_access] = self.current_node_stack[-1]
        if isinstance(member_access, MemberAccessValue):
            self.value_nodes[member_access] = self.current_node_stack[-1]

        # self.names_list.append(member_access)

    def enter_attribute(self, node: astroid.Attribute) -> None:
        if isinstance(node.parent, astroid.Decorators):
            return

        member_access = _construct_member_access_value(node.expr, node)
        # Astroid generates an Attribute node for every attribute access.
        # We therefore need to check if the attribute access is a target or a value.
        if isinstance(node.parent, astroid.AssignAttr) or self.has_assignattr_parent(node):
            member_access = _construct_member_access_target(node.expr, node)
            if isinstance(node.expr, astroid.Name):
                if node.expr.name == "self":
                    return
                self.target_nodes[node.expr] = self.current_node_stack[-1]

        if isinstance(member_access, MemberAccessTarget):
            self.target_nodes[member_access] = self.current_node_stack[-1]
        elif isinstance(member_access, MemberAccessValue):
            self.value_nodes[member_access] = self.current_node_stack[-1]

    @staticmethod
    def has_assignattr_parent(node) -> bool:
        """Checks if any parent of the given node is an AssignAttr node."""
        current_node = node
        while current_node is not None:
            if isinstance(current_node, astroid.AssignAttr):
                return True
            current_node = current_node.parent
        return False

    def enter_global(self, node: astroid.Global) -> None:
        for name in node.names:
            if self.check_if_global(name, node):
                self.global_variables[name] = self.current_node_stack[-1]

    def enter_call(self, node: astroid.Call) -> None:
        if isinstance(node.func, astroid.Name):
            self.function_calls[node] = self.current_node_stack[-1]

    def enter_import(self, node: astroid.Import) -> None:  # TODO: handle multiple imports and aliases
        parent = self.current_node_stack[-1]
        scope_node = Scope(_symbol=self.get_symbol(node, self.current_node_stack[-1].symbol.node),
                           _children=[],
                           _parent=parent)
        self.children.append(scope_node)

    def enter_importfrom(self, node: astroid.ImportFrom) -> None:  # TODO: handle multiple imports and aliases
        parent = self.current_node_stack[-1]
        scope_node = Scope(_symbol=self.get_symbol(node, self.current_node_stack[-1].symbol.node),
                           _children=[],
                           _parent=parent)
        self.children.append(scope_node)

    def check_if_global(self, name: str, node: astroid.NodeNG) -> bool:
        """
        Check if a name is a global variable

        Checks if a name is a global variable inside the root of the given node
        Returns True if the name is listed in root.globals dict, False otherwise
        """
        if not isinstance(node, astroid.Module):
            return self.check_if_global(name, node.parent)
        else:
            if name in node.globals:
                return True
        return False

    def find_base_classes(self, node: astroid.ClassDef) -> list[ClassScope]:
        """
        Find a list of all base classes of the given class
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
        Get the class with the given name
        """
        for klass in self.classes:
            if klass == name:
                return self.classes[klass]
        return None

    def handle_arg(self, constructed_node: astroid.AssignName) -> None:
        self.target_nodes[constructed_node] = self.current_node_stack[-1]
        scope_node = Scope(_symbol=Parameter(constructed_node, _calc_node_id(constructed_node), constructed_node.name), _children=[], _parent=self.current_node_stack[-1])
        self.children.append(scope_node)
        self.parameters[self.current_node_stack[-1].symbol.node] = (self.current_node_stack[-1], {constructed_node})

    def get_class_for_receiver_node(self, receiver) -> ClassScope | None:
        if isinstance(receiver, astroid.Name):
            if receiver.name in self.classes:
                return self.classes[receiver.name]
        return None


def _calc_node_id(
    node: astroid.NodeNG | astroid.Module | astroid.ClassDef | astroid.FunctionDef | astroid.AssignName | astroid.Name | astroid.AssignAttr | astroid.Import | astroid.ImportFrom | MemberAccess
) -> NodeID:
    if isinstance(node, MemberAccess):
        module = node.receiver.root().name
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
            expression = get_base_expression(node)
            return NodeID(module, node.name, expression.lineno, expression.col_offset)
        case astroid.Import():  # TODO: we need a special treatment for imports and import from
            return NodeID(module, node.names[0][0], node.lineno, node.col_offset)
        case astroid.ImportFrom():
            return NodeID(module, node.names[0][1], node.lineno, node.col_offset)
        case astroid.AssignAttr():
            return NodeID(module, node.attrname, node.lineno, node.col_offset)
        case astroid.Call():
            return NodeID(module, node.func.name, node.lineno, node.col_offset)
        case astroid.Lambda():
            return NodeID(module, "LAMBDA", node.lineno, node.col_offset)
        case astroid.NodeNG():
            return NodeID(module, node.as_string(), node.lineno, node.col_offset)
        case _:
            raise ValueError(f"Node type {node.__class__.__name__} is not supported yet.")

    # TODO: add fitting default case and merge same types of cases together


def _construct_member_access_target(receiver: astroid.Name | astroid.Attribute | astroid.Call, member: astroid.AssignAttr | astroid.Attribute) -> MemberAccessTarget:
    try:
        if isinstance(receiver, astroid.Name):
            return MemberAccessTarget(receiver=receiver, member=member)
        elif isinstance(receiver, astroid.Call):
            return MemberAccessTarget(receiver=receiver.func, member=member)
        else:
            return MemberAccessTarget(receiver=_construct_member_access_target(receiver.expr, receiver),
                                      member=member)
    except TypeError:
        raise TypeError(f"Unexpected node type {type(member)}")


def _construct_member_access_value(receiver: astroid.Name | astroid.Attribute | astroid.Call, member: astroid.Attribute) -> MemberAccessValue:
    try:
        if isinstance(receiver, astroid.Name):
            return MemberAccessValue(receiver=receiver, member=member)
        elif isinstance(receiver, astroid.Call):
            return MemberAccessValue(receiver=receiver.func, member=member)
        else:
            return MemberAccessValue(receiver=_construct_member_access_value(receiver.expr, receiver),
                                     member=member)
    except TypeError:
        raise TypeError(f"Unexpected node type {type(member)}")


def get_base_expression(node: MemberAccess) -> astroid.NodeNG:
    if isinstance(node.receiver, MemberAccess):
        return get_base_expression(node.receiver)
    else:
        return node.receiver


def _get_module_data(code: str) -> ModuleData:
    """Get the module data of the given code.

    In order to get the module data of the given code, the code is parsed into an AST and then walked by an ASTWalker.
    The ASTWalker detects the scope of each node and builds a scope tree by using an instance of ScopeFinder.
    The ScopeFinder also collects all name nodes, parameters, global variables, classes and functions of the module.
    """
    scope_handler = ModuleDataBuilder()
    walker = ASTWalker(scope_handler)
    module = astroid.parse(code)
    print(module.repr_tree())
    walker.walk(module)

    scope = scope_handler.children[0]  # get the children of the root node, which are the scopes of the module

    return ModuleData(scope=scope,
                      classes=scope_handler.classes,
                      functions=scope_handler.functions,
                      global_variables=scope_handler.global_variables,
                      value_nodes=scope_handler.value_nodes,
                      target_nodes=scope_handler.target_nodes,
                      parameters=scope_handler.parameters,
                      function_calls=scope_handler.function_calls)
