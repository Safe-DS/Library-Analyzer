from __future__ import annotations

from dataclasses import dataclass, field

import astroid

from library_analyzer.processing.api.purity_analysis.model import (
    ClassScope,
    ClassVariable,
    FunctionScope,
    GlobalVariable,
    Import,
    InstanceVariable,
    LocalVariable,
    MemberAccess,
    MemberAccessTarget,
    MemberAccessValue,
    ModuleData,
    NodeID,
    Parameter,
    Reference,
    Scope,
    Symbol,
)
from library_analyzer.utils import ASTWalker

_ComprehensionType = astroid.ListComp | astroid.DictComp | astroid.SetComp | astroid.GeneratorExp


@dataclass
class ModuleDataBuilder:
    """
    A ModuleDataBuilder instance is used to find all information relevant for the purity analysis of a module.

    It must be handed to an ASTWalker instance to collect all information.
    After the ASTWalker has walked the AST,
    the ModuleDataBuilder instance contains all information relevant to the purity analysis of the module.

    Attributes
    ----------
    current_node_stack : list[Scope | ClassScope | FunctionScope]
        Stack of nodes that are currently visited by the ASTWalker.
        The last node in the stack is the current node.
        It Is only used while walking the AST.
    current_function_def : list[FunctionScope]
        Stack of FunctionScopes that are currently visited by the ASTWalker.
        The top of the stack is the current function definition.
        It is only used while walking the AST.
    children : list[Scope | ClassScope | FunctionScope]
        All found children nodes are stored in children until their scope is determined.
        After the AST is completely walked, the resulting "Module"- Scope is stored in children.
        (children[0])
    targets : list[Symbol]
        All found targets are stored in targets until their scope is determined.
    values : list[Reference]
        All found names are stored in names until their scope is determined.
        It Is only used while walking the AST.
    calls : list[Reference]
        All calls found on function level are stored in calls until their scope is determined.
        It Is only used while walking the AST.
    classes : dict[str, ClassScope]
        Classnames in the module as key and their corresponding ClassScope instance as value.
    functions : dict[str, list[FunctionScope]]
        Function names in the module as key and a list of their corresponding FunctionScope instances as value.
    value_nodes : dict[astroid.Name | MemberAccessValue, Scope | ClassScope | FunctionScope]
        Nodes that are used as a value and their corresponding Scope or ClassScope instance.
        Value nodes are nodes that are used as a value in an expression.
    target_nodes : dict[astroid.AssignName | astroid.Name | MemberAccessTarget, Scope | ClassScope | FunctionScope]
        Nodes that are used as a target and their corresponding Scope or ClassScope instance.
        Target nodes are nodes that are used as a target in an expression.
    global_variables : dict[str, Scope | ClassScope | FunctionScope]
        All global variables and their corresponding Scope or ClassScope instance.
    parameters : dict[astroid.FunctionDef, tuple[Scope | ClassScope | FunctionScope, list[astroid.AssignName]]]
        All parameters and their corresponding Scope or ClassScope instance.
    function_calls : dict[astroid.Call, Scope | ClassScope | FunctionScope]
        All function calls and their corresponding Scope or ClassScope instance.
    """

    current_node_stack: list[Scope | ClassScope | FunctionScope] = field(default_factory=list)
    current_function_def: list[FunctionScope] = field(default_factory=list)
    children: list[Scope | ClassScope | FunctionScope] = field(default_factory=list)
    targets: list[Symbol] = field(default_factory=list)
    values: list[Reference] = field(default_factory=list)
    calls: list[Reference] = field(default_factory=list)
    classes: dict[str, ClassScope] = field(default_factory=dict)
    functions: dict[str, list[FunctionScope]] = field(default_factory=dict)
    value_nodes: dict[astroid.Name | MemberAccessValue, Scope | ClassScope | FunctionScope] = field(
        default_factory=dict,
    )
    target_nodes: dict[astroid.AssignName | astroid.Name | MemberAccessTarget,
                       Scope | ClassScope | FunctionScope] = field(default_factory=dict)
    global_variables: dict[str, Scope | ClassScope | FunctionScope] = field(default_factory=dict)
    parameters: dict[astroid.FunctionDef, tuple[Scope | ClassScope | FunctionScope, list[astroid.AssignName]]] = field(
        default_factory=dict,
    )  # TODO: [LATER] in a refactor:  remove parameters since they are stored inside the FunctionScope in functions now and use these instead
    function_calls: dict[astroid.Call, Scope | ClassScope | FunctionScope] = field(default_factory=dict)

    def _detect_scope(self, current_node: astroid.NodeNG) -> None:
        """
        Detect the scope of the given node.

        Detecting the scope of a node means finding the node in the scope tree that defines the scope of the given node.
        The scope of a node is defined by the parent node in the scope tree.
        This function is called when the ASTWalker leaves a node.
        It also adds classes and functions to their corresponding dicts
        while dealing with the construction of the corresponding Scope instance (FunctionsScope, ClassScope).

        Parameters
        ----------
        current_node : astroid.NodeNG
            The node whose scope is to be determined.
        """
        outer_scope_children: list[Scope | ClassScope] = []
        inner_scope_children: list[Scope | ClassScope] = []
        # This is only the case when the module is left: every child must be in the inner scope (=module scope).
        # This speeds up the process of finding the scope of the children.
        if isinstance(current_node, astroid.Module):
            inner_scope_children = self.children
        # Look at a nodes' parent node to determine if it is in the scope of the current node.
        else:
            for child in self.children:
                if (
                    child.parent is not None and child.parent.symbol.node != current_node
                ):  # Check if the child is in the scope of the current node.
                    outer_scope_children.append(child)  # Add the child to the outer scope.
                else:
                    inner_scope_children.append(child)  # Add the child to the inner scope.

        self.current_node_stack[-1].children = inner_scope_children  # Set the children of the current node.
        self.children = outer_scope_children  # Keep the children that are not in the scope of the current node.
        self.children.append(self.current_node_stack[-1])  # Add the current node to the children.

        # TODO: ideally this should not be part of detect_scope since it is just called when we leave the corresponding node
        # Analyze the current node regarding class exclusive property's.
        if isinstance(current_node, astroid.ClassDef):
            self._analyze_class(current_node)

        # Analyze the current node regarding function exclusive property's.
        if isinstance(current_node, astroid.FunctionDef):
            self._analyze_function(current_node)

        # Analyze the current node regarding lambda exclusive property's.
        if isinstance(current_node, astroid.Lambda):
            self._analyze_lambda(current_node)

        self.current_node_stack.pop()  # Remove the current node from the stack.

    def _analyze_class(self, current_node: astroid.ClassDef) -> None:
        """Analyze a ClassDef node.

        This is called while the scope of a node is detected.
        It must only be called when the current node is of type ClassDef.
        This adds the ClassScope to the classes dict and adds all class variables and instance variables to their dicts.

        Parameters
        ----------
        current_node : astroid.ClassDef
            The node to analyze.
        """
        if not isinstance(current_node, astroid.ClassDef):
            return
        # Add classdef to the classes dict.
        self.classes[current_node.name] = self.current_node_stack[
            -1
        ]  # type: ignore[assignment] # current_node_stack[-1] is always of type ClassScope

        # Add class variables to the class_variables dict.
        for child in self.current_node_stack[-1].children:
            if isinstance(child.symbol, ClassVariable) and isinstance(self.current_node_stack[-1], ClassScope):
                if child.symbol.name in self.current_node_stack[-1].class_variables:
                    self.current_node_stack[-1].class_variables[child.symbol.name].append(child.symbol)
                else:
                    self.current_node_stack[-1].class_variables[child.symbol.name] = [child.symbol]

    def _analyze_function(self, current_node: astroid.FunctionDef) -> None:
        """Analyze a FunctionDef node.

        This is called while the scope of a node is detected.
        It must only be called when the current node is of type FunctionDef.
        Add the FunctionScope to the functions' dict.
        Add all targets, values and calls that are collected inside the function to the FunctionScope instance.

        Parameters
        ----------
        current_node : astroid.FunctionDef
            The node to analyze.
        """
        if not isinstance(current_node, astroid.FunctionDef):
            return
        # Extend the dict of functions with the current node or create
        # a new dict entry with the list containing the current node
        # if the function name is already in the dict
        if current_node.name in self.functions:
            self.functions[current_node.name].append(self.current_function_def[-1])
        else:  # better for readability
            self.functions[current_node.name] = [self.current_function_def[-1]]

        # If the function is the constructor of a class, analyze it to find the instance variables of the class.
        if current_node.name == "__init__":
            self._analyze_constructor()

        # Add all calls that are used inside the function body to its calls' dict.
        if self.calls:
            for call in self.calls:
                if call.name not in self.functions[current_node.name][-1].call_references:
                    self.functions[current_node.name][-1].call_references[call.name] = [call]
                else:
                    self.functions[current_node.name][-1].call_references[call.name].append(call)

            self.calls = []

        # Add all targets that are used inside the function body to its targets' dict.
        if self.targets:
            parent_targets = []
            for target in self.targets:
                if self.find_first_parent_function(target.node) == self.current_function_def[-1].symbol.node:
                    if target.name not in self.current_function_def[-1].target_symbols:
                        self.current_function_def[-1].target_symbols[target.name] = [target]
                    else:
                        self.current_function_def[-1].target_symbols[target.name].append(target)
                    self.targets = []
                else:
                    parent_targets.append(target)
            if parent_targets:
                self.targets = parent_targets

        # Add all values that are used inside the function body to its values' dict.
        if self.values:
            for value in self.values:
                # Do not add calls to value references
                # if isinstance(value.node, MemberAccessValue) and value.node.member.attrname in self.current_function_def[-1].call_references:
                #     continue
                if self.find_first_parent_function(value.node) == self.current_function_def[-1].symbol.node:
                    if value.name not in self.current_function_def[-1].value_references:
                        self.current_function_def[-1].value_references[value.name] = [value]
                    else:
                        self.current_function_def[-1].value_references[value.name].append(value)
            self.values = []

    def _analyze_lambda(self, current_node: astroid.Lambda) -> None:
        """Analyze a Lambda node.

        This is called while the scope of a node is detected.
        It must only be called when the current node is of type Lambda.
        Add the Lambda FunctionScope to the functions' dict if the lambda function is assigned a name.
        Add all values and calls that are collected inside the lambda to the Lambda FunctionScope instance.
        Also add these values to the surrounding scope if it is of type FunctionScope.
        This is due to the fact that lambda functions define a scope themselves
        and otherwise the values would be lost.
        """
        if not isinstance(current_node, astroid.Lambda):
            return

        # Add lambda functions that are assigned to a name (and therefor are callable) to the functions' dict.
        if isinstance(current_node, astroid.Lambda) and isinstance(current_node.parent, astroid.Assign):
            # Make sure there is no AttributeError because of the inconsistent names in the astroid API.
            if isinstance(current_node.parent.targets[0], astroid.AssignAttr):
                node_name = current_node.parent.targets[0].attrname
            else:
                node_name = current_node.parent.targets[0].name
            # If the Lambda function is assigned to a name, it can be called just as a normal function.
            # Since Lambdas normally do not have names, they need to be assigned manually.
            self.current_function_def[-1].symbol.name = node_name
            self.current_function_def[-1].symbol.node.name = node_name
            self.current_function_def[-1].symbol.id.name = node_name

            # Extend the dict of functions with the current node or create a new list with the current node.
            if node_name in self.functions:
                self.functions[node_name].append(self.current_function_def[-1])
            else:  # better for readability
                self.functions[node_name] = [self.current_function_def[-1]]

            # Add all targets that are used inside the function body to its targets' dict.
            if self.targets:
                for target in self.targets:
                    if target.name not in self.current_function_def[-1].target_symbols:
                        self.current_function_def[-1].target_symbols[target.name] = [target]
                    else:
                        self.current_function_def[-1].target_symbols[target.name].append(target)
                self.targets = []

            # Add all values that are used inside the function body to its values' dict.
            if self.values:
                for value in self.values:
                    if value.name not in self.current_function_def[-1].value_references:
                        self.current_function_def[-1].value_references[value.name] = [value]
                    else:
                        self.current_function_def[-1].value_references[value.name].append(value)
                self.values = []

            # Add all calls that are used inside the function body to its calls' dict.
            if self.calls:
                for call in self.calls:
                    if call.name not in self.functions[current_node.name][-1].call_references:
                        self.functions[current_node.name][-1].call_references[call.name] = [call]
                    else:
                        self.functions[current_node.name][-1].call_references[call.name].append(call)
                self.calls = []

        # Lambda Functions that have no name are hard to deal with when building the call graph. Therefore,
        # add all of their targets/values/calls to the parent function to indirectly add the needed impurity info
        # to the parent function. From here, assume that lambda functions are only used inside a function body
        # (other cases would be irrelevant for function purity anyway).
        # Anyway, all names in the lambda function are of local scope.
        # Therefore, assign a FunctionScope instance with the name 'Lambda' to represent that.
        if (
            isinstance(current_node, astroid.Lambda)
            and not isinstance(current_node, astroid.FunctionDef)
            and isinstance(current_node.parent, astroid.Call | astroid.Expr)
            # Call deals  with: (lambda x: x+1)(2) and Expr deals with: lambda x: x+1
        ):
            # Add all targets that are used inside the function body to its targets' dict.
            if self.targets:
                for target in self.targets:
                    if target.name not in self.current_function_def[-1].target_symbols:
                        self.current_function_def[-1].target_symbols[target.name] = [target]
                    else:
                        self.current_function_def[-1].target_symbols[target.name].append(target)
                self.targets = []

            # Add all values that are used inside the lambda body to its parent function values' dict.
            if self.values and isinstance(self.current_node_stack[-2], FunctionScope):
                for value in self.values:
                    if (
                        value.name not in self.current_function_def[-1].parameters
                    ):  # type: ignore[union-attr] # ignore the linter error because the current scope node is always of type FunctionScope and therefor has a parameter attribute.
                        if value.name not in self.current_node_stack[-2].value_references:
                            self.current_node_stack[-2].value_references[value.name] = [value]
                        else:
                            self.current_node_stack[-2].value_references[value.name].append(value)

            # Add the values to the Lambda FunctionScope.
            if (
                self.values
                and isinstance(self.current_function_def[-1], FunctionScope)
                and isinstance(self.current_function_def[-1].symbol.node, astroid.Lambda)
            ):
                for value in self.values:
                    if value.name not in self.current_function_def[-1].value_references:
                        self.current_function_def[-1].value_references[value.name] = [value]
                    else:
                        self.current_function_def[-1].value_references[value.name].append(value)
            self.values = []

            # Add all calls that are used inside the lambda body to its parent function calls' dict.
            if self.calls and isinstance(self.current_node_stack[-2], FunctionScope):
                for call in self.calls:
                    if call.name not in self.current_node_stack[-2].call_references:
                        self.current_node_stack[-2].call_references[call.name] = [call]
                    else:
                        self.current_node_stack[-2].call_references[call.name].append(call)

            # Add the calls to the Lambda FunctionScope.
            if (
                self.calls
                and isinstance(self.current_function_def[-1], FunctionScope)
                and isinstance(self.current_function_def[-1].symbol.node, astroid.Lambda)
            ):
                for call in self.calls:
                    if call.name not in self.current_function_def[-1].call_references:
                        self.current_function_def[-1].call_references[call.name] = [call]
                    else:
                        self.current_function_def[-1].call_references[call.name].append(call)
            self.calls = []

            # Add all globals that are used inside the Lambda to the parent function globals list.
            if self.current_node_stack[-1].globals_used:  # type: ignore[union-attr]
                # Ignore the linter error because the current scope node is always of
                # type FunctionScope and therefor has a parameter attribute.
                for glob_name, glob_def_list in self.current_node_stack[
                    -1
                ].globals_used.items():  # type: ignore[union-attr] # see above
                    if glob_name not in self.current_function_def[-2].globals_used:
                        self.current_function_def[-2].globals_used[glob_name] = glob_def_list
                    else:
                        for glob_def in glob_def_list:
                            if glob_def not in self.current_function_def[-2].globals_used[glob_name]:
                                self.current_function_def[-2].globals_used[glob_name].append(glob_def)

    def _analyze_constructor(self) -> None:
        """Analyze the constructor of a class.

        The constructor of a class is a special function called when an instance of the class is created.
        This function must only be called when the name of the FunctionDef node is `__init__`.
        """
        # Add instance variables to the instance_variables list of the class.
        for child in self.current_function_def[-1].children:
            if isinstance(child.symbol, InstanceVariable) and isinstance(
                self.current_function_def[-1].parent,
                ClassScope,
            ):
                if child.symbol.name in self.current_function_def[-1].parent.instance_variables:
                    self.current_function_def[-1].parent.instance_variables[child.symbol.name].append(child.symbol)
                else:
                    self.current_function_def[-1].parent.instance_variables[child.symbol.name] = [child.symbol]
        # Add __init__ function to ClassScope.
        if isinstance(self.current_function_def[-1].parent, ClassScope):
            self.current_function_def[-1].parent.init_function = self.current_function_def[-1]

    def find_first_parent_function(self, node: astroid.NodeNG | MemberAccess) -> astroid.NodeNG:
        """Find the first parent of a call node that is a function.

        Parameters
        ----------
        node : astroid.NodeNG
            The node to start the search from.

        Returns
        -------
        astroid.NodeNG
            The first parent of the node that is a function.
            If the parent is a module, return the module.
        """
        if isinstance(node, MemberAccess):
            node = node.node  # This assures that the node to calculate the parent function exists.
        if isinstance(node.parent, astroid.FunctionDef | astroid.Lambda | astroid.Module | None):
            return node.parent
        return self.find_first_parent_function(node.parent)

    def enter_module(self, node: astroid.Module) -> None:
        """
        Enter a module node.

        The module node is the root node of the AST, so it has no parent (parent is None).
        The module node is also the first node that is visited, so the current_node_stack is empty before entering the module node.

        Parameters
        ----------
        node : astroid.Module
            The module node to enter.
        """
        self.current_node_stack.append(
            Scope(_symbol=self.get_symbol(node, None), _children=[], _parent=None),
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
            FunctionScope(
                _symbol=self.get_symbol(node, self.current_node_stack[-1].symbol.node),
                _children=[],
                _parent=self.current_node_stack[-1],
            ),
        )
        self.current_function_def.append(self.current_node_stack[-1])  # type: ignore[arg-type]
        # The current_node_stack[-1] is always of type FunctionScope here.

    def leave_functiondef(self, node: astroid.FunctionDef) -> None:
        self._detect_scope(node)
        # self.cleanup_globals(self.current_function_def[-1])
        self.current_function_def.pop()

    def enter_asyncfunctiondef(self, node: astroid.AsyncFunctionDef) -> None:
        self.current_node_stack.append(
            FunctionScope(
                _symbol=self.get_symbol(node, self.current_node_stack[-1].symbol.node),
                _children=[],
                _parent=self.current_node_stack[-1],
            ),
        )
        self.current_function_def.append(self.current_node_stack[-1])  # type: ignore[arg-type]
        # The current_node_stack[-1] is always of type FunctionScope here.

    def leave_asyncfunctiondef(self, node: astroid.AsyncFunctionDef) -> None:
        self._detect_scope(node)
        self.current_function_def.pop()

    def get_symbol(self, node: astroid.NodeNG, current_scope: astroid.NodeNG | None) -> Symbol:
        """Get the symbol of a node.

        It matches the current scope of the node and returns the corresponding symbol for the given node.

        Parameters
        ----------
        node : astroid.NodeNG
            The node whose symbol is to be determined.
        current_scope : astroid.NodeNG | None
            The current scope of the node (is None if the node is the module node).
        """
        match current_scope:
            case astroid.Module() | None:
                if isinstance(node, astroid.Import):
                    return Import(
                        node=node,
                        id=calc_node_id(node),
                        name=node.names[0][0],
                    )  # TODO: this needs fixing when multiple imports are handled

                if isinstance(node, astroid.ImportFrom):
                    return Import(
                        node=node,
                        id=calc_node_id(node),
                        name=node.names[0][1],
                    )  # TODO: this needs fixing when multiple imports are handled

                if isinstance(
                    node,
                    _ComprehensionType | astroid.Lambda | astroid.TryExcept | astroid.TryFinally,
                ) and not isinstance(node, astroid.FunctionDef):
                    return GlobalVariable(node=node, id=calc_node_id(node), name=node.__class__.__name__)
                return GlobalVariable(node=node, id=calc_node_id(node), name=node.name)

            case astroid.ClassDef():
                # Functions inside a class are defined as class variables if they are defined in the class scope.
                # if isinstance(node, astroid.FunctionDef):
                #     return LocalVariable(node=node, id=_calc_node_id(node), name=node.name)
                if isinstance(
                    node,
                    _ComprehensionType | astroid.Lambda | astroid.TryExcept | astroid.TryFinally,
                ) and not isinstance(node, astroid.FunctionDef):
                    return ClassVariable(
                        node=node,
                        id=calc_node_id(node),
                        name=node.__class__.__name__,
                        klass=current_scope,
                    )
                return ClassVariable(node=node, id=calc_node_id(node), name=node.name, klass=current_scope)

            case astroid.FunctionDef():
                # Find instance variables (in the constructor)
                if (
                    isinstance(current_scope, astroid.FunctionDef)
                    and isinstance(node, MemberAccessTarget)
                    and current_scope.name == "__init__"
                ):
                    return InstanceVariable(
                        node=node,
                        id=calc_node_id(node),
                        name=node.member,
                        klass=current_scope.parent,
                    )

                # Find parameters
                if (
                    isinstance(node, astroid.AssignName)
                    and self.parameters
                    and current_scope in self.parameters
                    and self.parameters[current_scope][1].__contains__(node)
                ):
                    return Parameter(node=node, id=calc_node_id(node), name=node.name)

                # Special cases for nodes inside functions that are defined as LocalVariables but which do not have a name
                if isinstance(node, _ComprehensionType | astroid.Lambda | astroid.TryExcept | astroid.TryFinally):
                    return LocalVariable(node=node, id=calc_node_id(node), name=node.__class__.__name__)

                if (
                    isinstance(node, astroid.Name | astroid.AssignName)
                    and node.name in node.root().globals
                    and node.name not in current_scope.locals
                ):
                    return GlobalVariable(node=node, id=calc_node_id(node), name=node.name)

                return LocalVariable(node=node, id=calc_node_id(node), name=node.name)

            case (
                astroid.Lambda() | astroid.ListComp() | astroid.DictComp() | astroid.SetComp() | astroid.GeneratorExp()
            ):
                # This deals with the case where a lambda function has parameters
                if isinstance(node, astroid.AssignName) and isinstance(node.parent, astroid.Arguments):
                    return Parameter(node=node, id=calc_node_id(node), name=node.name)
                # This deals with global variables that are used inside a lambda
                if isinstance(node, astroid.AssignName) and node.name in self.global_variables:
                    return GlobalVariable(node=node, id=calc_node_id(node), name=node.name)
                return LocalVariable(node=node, id=calc_node_id(node), name=node.name)

            case (
                astroid.TryExcept() | astroid.TryFinally()
            ):  # TODO: can we summarize Lambda and ListComp here? -> only if nodes in try except are not global
                return LocalVariable(node=node, id=calc_node_id(node), name=node.name)

        # This line is a fallback but should never be reached
        return Symbol(node=node, id=calc_node_id(node), name=node.name)  # pragma: no cover

    def enter_lambda(self, node: astroid.Lambda) -> None:
        self.current_node_stack.append(
            FunctionScope(
                _symbol=self.get_symbol(node, self.current_node_stack[-1].symbol.node),
                _children=[],
                _parent=self.current_node_stack[-1],
            ),
        )
        self.current_function_def.append(self.current_node_stack[-1])  # type: ignore[arg-type]
        # The current_node_stack[-1] is always of type FunctionScope here.

    def leave_lambda(self, node: astroid.Lambda) -> None:
        self._detect_scope(node)
        # self.cleanup_globals(self.current_node_stack[-1])
        self.current_function_def.pop()

    def enter_listcomp(self, node: astroid.ListComp) -> None:
        self.current_node_stack.append(
            Scope(
                _symbol=self.get_symbol(node, self.current_node_stack[-1].symbol.node),
                _children=[],
                _parent=self.current_node_stack[-1],
            ),
        )

    def leave_listcomp(self, node: astroid.ListComp) -> None:
        self._detect_scope(node)

    def enter_dictcomp(self, node: astroid.DictComp) -> None:
        self.current_node_stack.append(
            Scope(
                _symbol=self.get_symbol(node, self.current_node_stack[-1].symbol.node),
                _children=[],
                _parent=self.current_node_stack[-1],
            ),
        )

    def leave_dictcomp(self, node: astroid.DictComp) -> None:
        self._detect_scope(node)

    def enter_setcomp(self, node: astroid.SetComp) -> None:
        self.current_node_stack.append(
            Scope(
                _symbol=self.get_symbol(node, self.current_node_stack[-1].symbol.node),
                _children=[],
                _parent=self.current_node_stack[-1],
            ),
        )

    def leave_setcomp(self, node: astroid.SetComp) -> None:
        self._detect_scope(node)

    def enter_generatorexp(self, node: astroid.GeneratorExp) -> None:
        self.current_node_stack.append(
            Scope(
                _symbol=self.get_symbol(node, self.current_node_stack[-1].symbol.node),
                _children=[],
                _parent=self.current_node_stack[-1],
            ),
        )

    def leave_generatorexp(self, node: astroid.DictComp) -> None:
        self._detect_scope(node)

    # def enter_tryfinally(self, node: astroid.TryFinally) -> None:
    #     self.current_node_stack.append(
    #         Scope(_symbol=self.get_symbol(node, self.current_node_stack[-1].symbol.node),
    #               _children=[],
    #               _parent=self.current_node_stack[-1]),
    #     )
    #
    # def leave_tryfinally(self, node: astroid.TryFinally) -> None:
    #     self._detect_scope(node)

    def enter_tryexcept(self, node: astroid.TryExcept) -> None:
        self.current_node_stack.append(
            Scope(
                _symbol=self.get_symbol(node, self.current_node_stack[-1].symbol.node),
                _children=[],
                _parent=self.current_node_stack[-1],
            ),
        )

    def leave_tryexcept(self, node: astroid.TryExcept) -> None:
        self._detect_scope(node)

    def enter_arguments(self, node: astroid.Arguments) -> None:

        if node.args:
            self.parameters[self.current_node_stack[-1].symbol.node] = (self.current_node_stack[-1], node.args)
            for arg in node.args:
                self.add_arg_to_function_scope_parameters(arg)
        if node.kwonlyargs:
            self.parameters[self.current_node_stack[-1].symbol.node] = (
                self.current_node_stack[-1],
                node.kwonlyargs,
            )
            for arg in node.kwonlyargs:
                self.add_arg_to_function_scope_parameters(arg)
        if node.posonlyargs:
            self.parameters[self.current_node_stack[-1].symbol.node] = (
                self.current_node_stack[-1],
                node.posonlyargs,
            )
            for arg in node.kwonlyargs:
                self.add_arg_to_function_scope_parameters(arg)
        if node.vararg:
            constructed_node = astroid.AssignName(
                name=node.vararg,
                parent=node,
                lineno=node.parent.lineno,
                col_offset=node.parent.col_offset,
            )
            # TODO: col_offset is not correct: it should be the col_offset of the vararg/(kwarg) node which is not
            #  collected by astroid
            self.handle_arg(constructed_node)
        if node.kwarg:
            constructed_node = astroid.AssignName(
                name=node.kwarg,
                parent=node,
                lineno=node.parent.lineno,
                col_offset=node.parent.col_offset,
            )
            self.handle_arg(constructed_node)

    def add_arg_to_function_scope_parameters(self, argument: astroid.AssignName) -> None:
        """Add an argument to the parameters dict of the current function scope.

        Parameters
        ----------
        argument : astroid.AssignName
            The argument node to add to the parameter dict.
        """
        if isinstance(self.current_node_stack[-1], FunctionScope):
            self.current_node_stack[-1].parameters[argument.name] = Parameter(
                argument,
                calc_node_id(argument),
                argument.name,
            )

    def enter_name(self, node: astroid.Name) -> None:
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
            | astroid.Attribute,
        ):
            # The following if statement is necessary to avoid adding the same node to
            # both the target_nodes and the value_nodes dict. Since there is a case where a name node is used as a
            # target, a check is needed if the node is already in the target_nodes dict. This is only the case if the
            # name node is the receiver of a MemberAccessTarget node. It is made sure that in this case the node is
            # definitely in the target_nodes dict because the MemberAccessTarget node is added to the dict before the
            # name node.
            if node not in self.target_nodes:
                self.value_nodes[node] = self.current_node_stack[-1]

        elif isinstance(node.parent, astroid.AssignAttr):
            self.target_nodes[node] = self.current_node_stack[-1]
            self.targets.append(Symbol(node, calc_node_id(node), node.name))
        if (
            isinstance(node.parent, astroid.Call)
            and isinstance(node.parent.func, astroid.Name)
            and node.parent.func.name != node.name
        ):
            # Append a node only then when it is not the name node of the function
            self.value_nodes[node] = self.current_node_stack[-1]

        func_def = self.find_first_parent_function(node)

        if self.current_function_def and func_def == self.current_function_def[-1].symbol.node:
            # Exclude propagation to a function scope if the scope within that function defines a local scope itself.
            # e.g. ListComp, SetComp, DictComp, GeneratorExp
            # Except the name node is a global variable, than it must be propagated to the function scope.
            # TODO: dazu zählen ListComp, Lambda, TryExcept??, TryFinally??
            if (
                isinstance(self.current_node_stack[-1].symbol.node, _ComprehensionType)
                and node.name not in self.global_variables
            ):
                return

            # Deal with some special cases that need to be excluded
            if isinstance(node, astroid.Name):
                # Ignore self and cls because they are not relevant for purity by our means.
                # if node.name in ("self", "cls"):
                #     return

                # Do not add the "self" from the assignments of the instance variables since they are no real values.
                if isinstance(node.parent, astroid.AssignAttr):
                    return

                # Call removes the function name.
                if isinstance(node.parent, astroid.Call):
                    if isinstance(node.parent.func, astroid.Attribute):
                        if node.parent.func.attrname == node.name:
                            return
                    elif isinstance(node.parent.func, astroid.Name):
                        if node.parent.func.name == node.name:
                            return

                # Check if the Name belongs to a type hint.
                if self.is_annotated(node, found_annotation_node=False):
                    return

            reference = Reference(node, calc_node_id(node), node.name)
            if reference not in self.values:
                self.values.append(reference)

            # Add the name to the globals list of the surrounding function if it is a variable of global scope.
            global_node_defs = self.check_if_global(node.name, node)
            if global_node_defs is not None:
                # It is possible that a variable has more than one global assignment,
                # particularly in cases where the variable is depending on a condition.
                # Since this can only be determined at runtime, add all global assignments to the list.
                for global_node_def in global_node_defs:
                    # Propagate global variables in Comprehension type to
                    # the surrounding function if it is a global variable.
                    if isinstance(global_node_def, astroid.AssignName) and (
                        isinstance(self.current_node_stack[-1], FunctionScope)
                        or isinstance(self.current_node_stack[-1].symbol.node, _ComprehensionType | astroid.Lambda)
                    ):
                        # Create a new dict entry for a global variable (by name).
                        if node.name not in self.current_function_def[-1].globals_used:
                            symbol = self.get_symbol(global_node_def, self.current_function_def[-1].symbol.node)
                            if isinstance(symbol, GlobalVariable):
                                self.current_function_def[-1].globals_used[node.name] = [symbol]
                        # If the name of the global variable already exists,
                        # add the new declaration to the list (redeclaration).
                        else:
                            symbol = self.get_symbol(global_node_def, self.current_function_def[-1].symbol.node)
                            if symbol not in self.current_function_def[-1].globals_used[node.name] and isinstance(
                                symbol,
                                GlobalVariable,
                            ):
                                self.current_function_def[-1].globals_used[node.name].append(symbol)
                return

    def is_annotated(self, node: astroid.NodeNG | MemberAccess, found_annotation_node: bool) -> bool:
        """Check if the Name node is a type hint.

        Parameters
        ----------
        node : astroid.Name
            The node to check.
        found_annotation_node : bool
            A bool that indicates if an annotation node is found.

        Returns
        -------
        bool
            True if the node is a type hint, False otherwise.
        """
        # Condition that checks if an annotation node is found.
        # This can be extended by all nodes indicating a type hint.
        if isinstance(node, astroid.Arguments | astroid.AnnAssign):
            return True

        # This checks if the node is used as a return type
        if isinstance(node.parent, astroid.FunctionDef) and node.parent.returns and node == node.parent.returns:
            return True

        # Return the current bool if an assignment node is found.
        # This is the case when there are no more nested nodes that could contain a type hint property.
        if isinstance(node, astroid.Assign) or found_annotation_node:
            return found_annotation_node

        # Check the parent of the node for annotation types.
        elif node.parent is not None:
            return self.is_annotated(node.parent, found_annotation_node=found_annotation_node)

        return found_annotation_node

    def enter_assignname(self, node: astroid.AssignName) -> None:
        # Lambda assignments will not be added to the target_nodes dict because they are handled as functions.
        if isinstance(node.parent, astroid.Assign) and isinstance(node.parent.value, astroid.Lambda):
            return

        # The following nodes are added to the target_nodes dict,
        # because they are real assignments and therefore targets.
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
            | astroid.Comprehension
            | astroid.ExceptHandler
            | astroid.With,
        ):
            self.target_nodes[node] = self.current_node_stack[-1]
            if (
                isinstance(self.current_node_stack[-1], FunctionScope)
                # only add assignments if they are inside a function
                # and node.name not in ("self", "cls")  # exclude self and cls
                # and not isinstance(node.parent, astroid.For | astroid.While)  # exclude loop variables
            ):
                self.targets.append(self.get_symbol(node, self.current_node_stack[-1].symbol.node))

        # The following nodes are no real target nodes, but astroid generates an AssignName node for them.
        # They still need to be added to the children of the current scope.
        if isinstance(
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
            | astroid.Comprehension
            | astroid.ExceptHandler
            | astroid.With,
        ):
            parent = self.current_node_stack[-1]
            scope_node = Scope(
                _symbol=self.get_symbol(node, self.current_node_stack[-1].symbol.node),
                _children=[],
                _parent=parent,
            )
            self.children.append(scope_node)

            # Detect global assignments and add them to the global_variables dict.
            if isinstance(node.root(), astroid.Module) and node.name in node.root().globals:
                self.global_variables[node.name] = scope_node

    def enter_assignattr(self, node: astroid.AssignAttr) -> None:
        parent = self.current_node_stack[-1]
        member_access = _construct_member_access_target(node)
        scope_node = Scope(
            _symbol=self.get_symbol(member_access, self.current_node_stack[-1].symbol.node),
            _children=[],
            _parent=parent,
        )
        self.children.append(scope_node)

        if isinstance(member_access, MemberAccessTarget):
            self.target_nodes[member_access] = self.current_node_stack[-1]
            if isinstance(self.current_node_stack[-1], FunctionScope):
                self.targets.append(Symbol(member_access, calc_node_id(member_access), member_access.name))
        if isinstance(member_access, MemberAccessValue):
            self.value_nodes[member_access] = self.current_node_stack[-1]

    def enter_attribute(self, node: astroid.Attribute) -> None:
        # Do not handle names used in decorators since this would be to complex for now.
        if isinstance(node.parent, astroid.Decorators):
            return

        # Astroid generates an Attribute node for every attribute access.
        # Check if the attribute access is a target or a value.
        if isinstance(node.parent, astroid.AssignAttr) or self.has_assignattr_parent(node):
            member_access = _construct_member_access_target(node)
            if isinstance(node.expr, astroid.Name):
                self.target_nodes[node.expr] = self.current_node_stack[-1]
                if isinstance(self.current_node_stack[-1], FunctionScope):
                    self.targets.append(Symbol(member_access, calc_node_id(member_access), member_access.name))
        else:
            member_access = _construct_member_access_value(node)

        if isinstance(member_access, MemberAccessTarget):
            self.target_nodes[member_access] = self.current_node_stack[-1]
            if isinstance(self.current_node_stack[-1], FunctionScope):
                self.targets.append(Symbol(member_access, calc_node_id(member_access), member_access.name))
        elif isinstance(member_access, MemberAccessValue):
            # Ignore type annotations because they are not relevant for purity.
            top_receiver = member_access.get_top_level_receiver()
            if self.is_annotated(top_receiver, found_annotation_node=False):
                return

            self.value_nodes[member_access] = self.current_node_stack[-1]
            reference = Reference(member_access, calc_node_id(member_access), member_access.name)
            self.values.append(reference)

    @staticmethod
    def has_assignattr_parent(node: astroid.Attribute) -> bool:
        """Check if any parent of the given node is an AssignAttr node.

        Since astroid generates an Attribute node for every attribute access,
        and it is possible to have nested attribute accesses,
        it is possible that the direct parent is not an AssignAttr node.
        In this case, check if any parent of the given node is an AssignAttr node.

        Parameters
        ----------
        node : astroid.Attribute
            The node whose parents are to be checked.

        Returns
        -------
        bool
            True if any parent of the given node is an AssignAttr node, False otherwise.
            True means that the given node is a target node, False means that the given node is a value node.
        """
        # TODO: deal with attribute access to items of a target: self.cache[a] = 1
        #  this currently is detected as value because of the ast structure.
        current_node = node
        while current_node is not None:
            if isinstance(current_node, astroid.AssignAttr):
                return True
            current_node = current_node.parent
        return False

    def enter_global(self, node: astroid.Global) -> None:
        """Enter a global node.

        Global nodes are used to declare global variables inside a function.
        Collect all these global variable usages and add them to the globals_used dict of that FunctionScope.
        """
        for name in node.names:
            global_node_defs = self.check_if_global(name, node)
            if global_node_defs:
                # It is possible that a variable has more than one global assignment,
                # particularly in cases where the variable is depending on a condition.
                # Since this can only be determined at runtime, add all global assignments to the list.
                for global_node_def in global_node_defs:
                    if isinstance(global_node_def, astroid.AssignName) and isinstance(
                        self.current_node_stack[-1],
                        FunctionScope,
                    ):
                        symbol = self.get_symbol(global_node_def, self.current_node_stack[-1].symbol.node)
                        if isinstance(symbol, GlobalVariable):
                            if name not in self.current_node_stack[-1].globals_used:
                                self.current_node_stack[-1].globals_used[name] = [symbol]
                            else:
                                self.current_node_stack[-1].globals_used[name].append(symbol)

    def enter_call(self, node: astroid.Call) -> None:
        if isinstance(node.func, astroid.Name | astroid.Attribute):
            self.function_calls[node] = self.current_node_stack[-1]

            if isinstance(node.func, astroid.Attribute):
                call_name = node.func.attrname
            else:
                call_name = node.func.name

            call_reference = Reference(node, calc_node_id(node), call_name)
            # Add the call node to the calls of the parent scope if it is of type FunctionScope.
            if isinstance(self.current_node_stack[-1], FunctionScope):
                self.calls.append(call_reference)
            else:  # noqa: PLR5501
                # Add the call node to the calls of the last function definition to ensure it is considered in the call graph
                # since it would otherwise be lost in the (local) Scope of the Comprehension.
                if (
                    isinstance(self.current_node_stack[-1].symbol.node, _ComprehensionType)
                    and self.current_function_def
                ):
                    if call_name not in self.current_function_def[-1].call_references:
                        self.current_function_def[-1].call_references[call_name] = [call_reference]
                    else:
                        self.current_function_def[-1].call_references[call_name].append(call_reference)

    def enter_import(self, node: astroid.Import) -> None:  # TODO: handle multiple imports and aliases
        parent = self.current_node_stack[-1]
        scope_node = Scope(
            _symbol=self.get_symbol(node, self.current_node_stack[-1].symbol.node),
            _children=[],
            _parent=parent,
        )
        self.children.append(scope_node)

    def enter_importfrom(self, node: astroid.ImportFrom) -> None:  # TODO: handle multiple imports and aliases
        parent = self.current_node_stack[-1]
        scope_node = Scope(
            _symbol=self.get_symbol(node, self.current_node_stack[-1].symbol.node),
            _children=[],
            _parent=parent,
        )
        self.children.append(scope_node)

    # TODO: this lookup could be more efficient if we would add all global nodes to the dict when 'enter_module' is called
    #  we than can be sure that all globals are detected already and we do not need to traverse the tree
    def check_if_global(self, name: str, node: astroid.NodeNG) -> list[astroid.AssignName] | None:
        """
        Check if a name is a global variable.

        Checks if a name is a global variable inside the root of the given node
        and return its assignment node if it is a global variable.

        Parameters
        ----------
        name : str
            The variable name to check.
        node : astroid.NodeNG
            The node whose root is to be checked.

        Returns
        -------
        astroid.AssignName | None
            The symbol of the global variable if it exists, None otherwise.
        """
        if not isinstance(node, astroid.Module):
            return self.check_if_global(name, node.parent)
        elif isinstance(node, astroid.Module) and name in node.globals:
            # The globals() dict contains all assignments of the node with this name
            # (this includes assignments in other scopes).
            # Only add the assignments of the nodes which are assigned on module scope (true global variables).
            return [
                node for node in node.globals[name] if isinstance(self.find_first_parent_function(node), astroid.Module)
            ]
        return None

    def find_base_classes(self, node: astroid.ClassDef) -> list[ClassScope] | None:
        """Find a list of all base classes of the given class.

        If a class has no base classes, an empty list is returned.

        Parameters
        ----------
        node : astroid.ClassDef
            The class whose base classes are to be found.

        Returns
        -------
        list[ClassScope] | None
            A list of all base classes of the given class if it has any, None otherwise.
        """
        base_classes = []
        for base in node.bases:
            if isinstance(base, astroid.Name):
                base_class = self.get_class_by_name(base.name)
                if isinstance(base_class, ClassScope):
                    base_classes.append(base_class)
        if base_classes:
            return base_classes
        else:
            return None

    def get_class_by_name(self, name: str) -> ClassScope | None:
        """Get the class with the given name.

        Parameters
        ----------
        name : str
            The name of the class to get.

        Returns
        -------
        ClassScope | None
            The class with the given name if it exists, None otherwise.
            None will never be returned since this function is only called when it is certain that the class exists.
        """
        for klass in self.classes:
            if klass == name:
                return self.classes[klass]
        # This is not possible because the class is always added to the classes dict when it is defined.
        return None  # pragma: no cover

    def handle_arg(self, constructed_node: astroid.AssignName) -> None:
        """Handle an argument node.

        This function is called when a vararg or a kwarg parameter is found inside an Argument node.
        This is needed because astroid does not generate a symbol for these nodes.
        Therefore, create one manually and add it to the parameters' dict.

        Parameters
        ----------
        constructed_node : astroid.AssignName
            The node that is to be handled.
        """
        self.target_nodes[constructed_node] = self.current_node_stack[-1]
        scope_node = Scope(
            _symbol=Parameter(constructed_node, calc_node_id(constructed_node), constructed_node.name),
            _children=[],
            _parent=self.current_node_stack[-1],
        )
        self.children.append(scope_node)
        self.add_arg_to_function_scope_parameters(constructed_node)
        if self.current_node_stack[-1].symbol.node in self.parameters:
            self.parameters[self.current_node_stack[-1].symbol.node][1].append(constructed_node)
        else:
            self.parameters[self.current_node_stack[-1].symbol.node] = (self.current_node_stack[-1], [constructed_node])

    # def get_class_for_receiver_node(self, receiver: MemberAccessTarget) -> ClassScope | None:
    #     """Get the class for the given receiver node.
    #
    #     When dealing with MemberAccessTarget nodes,
    #     find the class of the receiver node since the MemberAccessTarget node does not have a symbol.
    #
    #     Parameters
    #     ----------
    #     receiver : MemberAccessTarget
    #         The receiver node whose class is to be found.
    #
    #     Returns
    #     -------
    #     ClassScope | None
    #         The class of the given receiver node if it exists, None otherwise.
    #     """
    #     if isinstance(receiver, astroid.Name) and receiver.name in self.classes:
    #         return self.classes[receiver.name]
    #     return None


def calc_node_id(
    node: (
        astroid.NodeNG
        | astroid.Module
        | astroid.ClassDef
        | astroid.FunctionDef
        | astroid.AssignName
        | astroid.Name
        | astroid.AssignAttr
        | astroid.Import
        | astroid.ImportFrom
        | astroid.Call
        | astroid.Lambda
        | astroid.ListComp
        | MemberAccess
    ),
) -> NodeID:
    """Calculate the NodeID of the given node.

    The NodeID is calculated by using the name of the module, the name of the node, the line number and the column offset.
    The NodeID is used to identify nodes in the module.

    Parameters
    ----------
    node : astroid.NodeNG | astroid.Module | astroid.ClassDef | astroid.FunctionDef | astroid.AssignName | astroid.Name | astroid.AssignAttr | astroid.Import | astroid.ImportFrom | astroid.Call | astroid.Lambda | astroid.ListComp | MemberAccess

    Returns
    -------
    NodeID
        The NodeID of the given node.
    """
    if isinstance(node, MemberAccess):
        module = node.node.root().name
    else:
        module = node.root().name
        # TODO: check if this is correct when working with a real module

    match node:
        case astroid.Module():
            return NodeID(module, node.name, 0, 0)
        case astroid.ClassDef():
            return NodeID(module, node.name, node.lineno, node.col_offset)
        case astroid.FunctionDef():
            return NodeID(module, node.name, node.fromlineno, node.col_offset)
        case astroid.AssignName():
            return NodeID(module, node.name, node.lineno, node.col_offset)
        case astroid.Name():
            return NodeID(module, node.name, node.lineno, node.col_offset)
        case MemberAccess():
            return NodeID(module, node.name, node.node.lineno, node.node.col_offset)
        case astroid.Import():  # TODO: we need a special treatment for imports and import from
            return NodeID(module, node.names[0][0], node.lineno, node.col_offset)
        case astroid.ImportFrom():
            return NodeID(module, node.names[0][1], node.lineno, node.col_offset)
        case astroid.AssignAttr():
            return NodeID(module, node.attrname, node.lineno, node.col_offset)
        case astroid.Call():
            # Make sure there is no AttributeError because of the inconsistent names in the astroid API.
            if isinstance(node.func, astroid.Attribute):
                return NodeID(module, node.func.attrname, node.lineno, node.col_offset)
            return NodeID(module, node.func.name, node.lineno, node.col_offset)
        case astroid.Lambda():
            if isinstance(node.parent, astroid.Assign) and node.name != "LAMBDA":
                return NodeID(module, node.name, node.lineno, node.col_offset)
            return NodeID(module, "LAMBDA", node.lineno, node.col_offset)
        case astroid.ListComp():
            return NodeID(module, "LIST_COMP", node.lineno, node.col_offset)
        case astroid.NodeNG():
            return NodeID(module, node.as_string(), node.lineno, node.col_offset)
        case _:
            raise ValueError(f"Node type {node.__class__.__name__} is not supported yet.")


def _construct_member_access_target(node: astroid.Attribute | astroid.AssignAttr) -> MemberAccessTarget:
    """Construct a MemberAccessTarget node.

    Construct a MemberAccessTarget node from an Attribute or AssignAttr node.
    The receiver is the node that is accessed, and the member is the node that accesses the receiver.
    The receiver can be nested.

    Parameters
    ----------
    node : astroid.Attribute | astroid.AssignAttr
        The node to construct the MemberAccessTarget node from.

    Returns
    -------
    MemberAccessTarget
        The constructed MemberAccessTarget node.
    """
    receiver = node.expr
    member = node.attrname

    try:
        if isinstance(receiver, astroid.Name):
            return MemberAccessTarget(node=node, receiver=receiver, member=member)
        elif isinstance(receiver, astroid.Call):
            return MemberAccessTarget(node=node, receiver=receiver.func, member=member)
        elif isinstance(receiver, astroid.Attribute):
            return MemberAccessTarget(node=node, receiver=_construct_member_access_target(receiver), member=member)
        else:
            return MemberAccessTarget(node=node, receiver=None, member=member)
    # Since it is tedious to add testcases for this function, ignore the coverage for now
    except TypeError as err:  # pragma: no cover
        raise TypeError(f"Unexpected node type {type(node)}") from err  # pragma: no cover


def _construct_member_access_value(node: astroid.Attribute) -> MemberAccessValue:
    """Construct a MemberAccessValue node.

    Construct a MemberAccessValue node from an Attribute node.
    The receiver is the node that is accessed, and the member is the node that accesses the receiver.
    The receiver can be nested.

    Parameters
    ----------
    node : astrid.Attribute
        The node to construct the MemberAccessValue node from.

    Returns
    -------
    MemberAccessValue
        The constructed MemberAccessValue node.
    """
    receiver = node.expr
    member = node.attrname

    try:
        if isinstance(receiver, astroid.Name):
            return MemberAccessValue(node=node, receiver=receiver, member=member)
        elif isinstance(receiver, astroid.Call):
            return MemberAccessValue(node=node, receiver=receiver.func, member=member)
        elif isinstance(receiver, astroid.Attribute):
            return MemberAccessValue(node=node, receiver=_construct_member_access_value(receiver), member=member)
        else:
            return MemberAccessValue(node=node, receiver=None, member=member)
    # Since it is tedious to add testcases for this function, ignore the coverage for now
    except TypeError as err:  # pragma: no cover
        raise TypeError(f"Unexpected node type {type(node)}") from err  # pragma: no cover


def get_base_expression(node: MemberAccess) -> astroid.NodeNG:
    """Get the base expression of a MemberAccess node.

    Get the base expression of a MemberAccess node by recursively calling this function on the receiver of the MemberAccess node.

    Parameters
    ----------
    node : MemberAccess
        The MemberAccess node whose base expression is to be found.

    Returns
    -------
    astroid.NodeNG
        The base expression of the given MemberAccess node.
    """
    if isinstance(node.receiver, MemberAccess):
        return get_base_expression(node.receiver)
    else:
        return node.receiver


def get_module_data(code: str) -> ModuleData:
    """Get the module data of the given code.

    To get the module data of the given code, the code is parsed into an AST and then walked by an ASTWalker.
    The ModuleDataBuilder detects the scope of each node and builds a scope tree.
    The ModuleDataBuilder also collects all classes, functions, global variables, value nodes, target nodes, parameters,
    function calls, and function references.

    Parameters
    ----------
    code : str
        The source code of the module whose module data is to be found.

    Returns
    -------
    ModuleData
        The module data of the given module.
    """
    module_data_handler = ModuleDataBuilder()
    walker = ASTWalker(module_data_handler)
    module = astroid.parse(code)
    print(module.repr_tree())
    walker.walk(module)

    scope = module_data_handler.children[0]  # Get the children of the root node, which are the scopes of the module

    return ModuleData(
        scope=scope,
        classes=module_data_handler.classes,
        functions=module_data_handler.functions,
        global_variables=module_data_handler.global_variables,
        value_nodes=module_data_handler.value_nodes,
        target_nodes=module_data_handler.target_nodes,
        parameters=module_data_handler.parameters,
        function_calls=module_data_handler.function_calls,
    )
