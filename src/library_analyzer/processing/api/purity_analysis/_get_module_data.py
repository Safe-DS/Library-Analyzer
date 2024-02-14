from __future__ import annotations

import builtins
from dataclasses import dataclass, field

import astroid

from library_analyzer.processing.api.purity_analysis.model import (
    Builtin,
    ClassScope,
    ClassVariable,
    FunctionReference,
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
    Reasons,
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
    children : list[Scope | ClassScope | FunctionScope]
        All found children nodes are stored in children until their scope is determined.
        After the AST is completely walked, the resulting "Module"- Scope is stored in children.
        (children[0])
    names : list[Scope | ClassScope | FunctionScope]
        All found names are stored in names until their scope is determined.
        It Is only used while walking the AST.
    calls : list[Scope | ClassScope | FunctionScope]
        All found calls on function level are stored in calls until their scope is determined.
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
    function_references : dict[NodeID, Reasons]
        All function references and their corresponding Reasons instance.
    """

    current_node_stack: list[Scope | ClassScope | FunctionScope] = field(default_factory=list)
    children: list[Scope | ClassScope | FunctionScope] = field(default_factory=list)
    names: list[Scope | ClassScope | FunctionScope] = field(default_factory=list)
    calls: list[Scope | ClassScope | FunctionScope] = field(default_factory=list)
    classes: dict[str, ClassScope] = field(default_factory=dict)
    functions: dict[str, list[FunctionScope]] = field(default_factory=dict)
    value_nodes: dict[astroid.Name | MemberAccessValue, Scope | ClassScope | FunctionScope] = field(
        default_factory=dict,
    )
    target_nodes: dict[astroid.AssignName | astroid.Name | MemberAccessTarget, Scope | ClassScope | FunctionScope] = field(default_factory=dict)
    global_variables: dict[str, Scope | ClassScope | FunctionScope] = field(default_factory=dict)
    parameters: dict[astroid.FunctionDef, tuple[Scope | ClassScope | FunctionScope, list[astroid.AssignName]]] = field(
        default_factory=dict,
    )  # TODO: [LATER] in a refactor:  remove parameters since they are stored inside the FunctionScope in functions now and use these instead
    function_calls: dict[astroid.Call, Scope | ClassScope | FunctionScope] = field(default_factory=dict)
    function_references: dict[NodeID, Reasons] = field(default_factory=dict)  # TODO: rename to raw_reasons?
    last_function_def: list[FunctionScope] = field(default_factory=list)

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
        # This is only the case when we leave the module: every child must be in the inner scope(=module scope)
        # This speeds up the process of finding the scope of the children and guarantees that no child is lost
        if isinstance(current_node, astroid.Module):
            inner_scope_children = self.children

            # add all symbols of a function to the function_references dict
            self.function_references = self.collect_function_references()

        # We need to look at a nodes' parent node to determine if it is in the scope of the current node.
        else:
            for child in self.children:
                if (
                    child.parent is not None and child.parent.symbol.node != current_node
                ):  # Check if the child is in the scope of the current node
                    outer_scope_children.append(child)  # Add the child to the outer scope
                else:
                    inner_scope_children.append(child)  # Add the child to the inner scope

        self.current_node_stack[-1].children = inner_scope_children  # Set the children of the current node
        self.children = outer_scope_children  # Keep the children that are not in the scope of the current node
        self.children.append(self.current_node_stack[-1])  # Add the current node to the children
        # TODO: refactor this to a separate function
        if isinstance(current_node, astroid.ClassDef):
            # Add classdef to the classes dict
            self.classes[current_node.name] = self.current_node_stack[-1]  # type: ignore[assignment] # we can ignore the linter error because of the if statement above

            # Add class variables to the class_variables dict
            for child in self.current_node_stack[-1].children:
                if isinstance(child.symbol, ClassVariable) and isinstance(self.current_node_stack[-1], ClassScope):
                    if child.symbol.name in self.current_node_stack[-1].class_variables:
                        self.current_node_stack[-1].class_variables[child.symbol.name].append(child.symbol)
                    else:
                        self.current_node_stack[-1].class_variables[child.symbol.name] = [child.symbol]
        # TODO: refactor this to a separate function
        # Add functions to the functions dict
        if isinstance(current_node, astroid.FunctionDef):
            # Extend the dict of functions with the current node or create a new list with the current node
            if current_node.name in self.functions:
                if isinstance(
                    self.current_node_stack[-1],
                    FunctionScope,
                ):  # only add the current node if it is a function
                    self.functions[current_node.name].append(self.current_node_stack[-1])
            else:  # noqa: PLR5501 # better for readability
                if isinstance(self.current_node_stack[-1], FunctionScope):  # better for readability
                    self.functions[current_node.name] = [self.current_node_stack[-1]]

            # If we deal with a constructor, we need to analyze it to find the instance variables of the class
            if current_node.name == "__init__":
                self._analyze_constructor()

            # Add all values that are used inside the function body to its values' dict
            if self.names:
                for name in self.names:
                    if name.parent is not None and name.parent.symbol.node == current_node:
                        if name.symbol.name not in self.current_node_stack[-1].values:
                            self.current_node_stack[-1].values[name.symbol.name] = [name.symbol]
                        else:
                            self.current_node_stack[-1].values[name.symbol.name].append(name.symbol)
                self.names = []

            # Add all calls that are used inside the function body to its calls' dict
            if self.calls:
                self.functions[current_node.name][-1].calls = {call.symbol.name: call for call in self.calls}
                self.calls = []

        # Add lambda functions that are assigned to a name (and therefor are callable) to the functions dict
        if isinstance(current_node, astroid.Lambda) and isinstance(current_node.parent, astroid.Assign):
            # make sure we do not get an AttributeError because of the inconsistent names in the astroid API
            if isinstance(current_node.parent.targets[0], astroid.AssignAttr):
                node_name = current_node.parent.targets[0].attrname
            else:
                node_name = current_node.parent.targets[0].name
            # If the Lambda function is assigned to a name, it can be called just as a normal function
            # Since Lambdas normally do not have names, we need to add its assigned name manually
            self.current_node_stack[-1].symbol.name = node_name
            self.current_node_stack[-1].symbol.node.name = node_name
            self.current_node_stack[-1].symbol.id.name = node_name

            # Extend the dict of functions with the current node or create a new list with the current node
            if node_name in self.functions:
                if isinstance(self.current_node_stack[-1], FunctionScope):
                    self.functions[node_name].append(self.current_node_stack[-1])
            else:  # noqa: PLR5501 # better for readability
                if isinstance(self.current_node_stack[-1], FunctionScope):  # better for readability
                    self.functions[node_name] = [self.current_node_stack[-1]]

            # Add all values that are used inside the function body to its values' dict
            if self.names:
                for name in self.names:
                    if name.parent is not None and name.parent.symbol.node == current_node:
                        if name.symbol.name not in self.current_node_stack[-1].values:
                            self.current_node_stack[-1].values[name.symbol.name] = [name.symbol]
                        else:
                            self.current_node_stack[-1].values[name.symbol.name].append(name.symbol)
                self.names = []

            # Add all calls that are used inside the function body to its calls' dict
            if self.calls:
                self.functions[node_name][-1].calls = {call.symbol.name: call for call in self.calls}
                self.calls = []

        # Lambda Functions that have no name are hard to deal with when building the call graph. Therefore,
        # we simply add all of their names/calls to the parent function to indirectly add the needed impurity info
        # to the parent function. We assume that lambda functions are only used inside a function body (other cases
        # would be irrelevant for function purity anyway). Anyway, all names in the lambda function are of local
        # scope. Therefore, we assign a FunctionScope instance with the name 'Lambda' to represent that.
        if (
            isinstance(current_node, astroid.Lambda)
            and not isinstance(current_node, astroid.FunctionDef)
            and isinstance(current_node.parent, astroid.Call | astroid.Expr)  # Call deals  with: (lambda x: x+1)(2) and Expr deals with: lambda x: x+1
        ):
            # Add all values that are used inside the lambda body to its parent function values' dict
            if self.names and isinstance(self.current_node_stack[-2], FunctionScope):
                for name in self.names:
                    if name.parent is not None and name.parent.symbol.node == current_node and name.symbol.name not in self.current_node_stack[-1].parameters:  # type: ignore[union-attr] # we can ignore the linter error because the current scope node is always of type FunctionScope and therefor has a parameter attribute.
                        if name.symbol.name not in self.current_node_stack[-2].values:
                            self.current_node_stack[-2].values[name.symbol.name] = [name.symbol]
                        else:
                            self.current_node_stack[-2].values[name.symbol.name].append(name.symbol)

            # Add the values to the Lambda FunctionScope
            if self.names and isinstance(self.current_node_stack[-1], FunctionScope) and isinstance(self.current_node_stack[-1].symbol.node, astroid.Lambda):
                for name in self.names:
                    if name.parent is not None and name.parent.symbol.node == current_node:
                        if name.symbol.name not in self.current_node_stack[-1].values:
                            self.current_node_stack[-1].values[name.symbol.name] = [name.symbol]
                        else:
                            self.current_node_stack[-1].values[name.symbol.name].append(name.symbol)
            self.names = []

            # Add all calls that are used inside the lambda body to its parent function calls' dict
            if self.calls and isinstance(self.current_node_stack[-2], FunctionScope):
                self.current_node_stack[-2].calls = {call.symbol.name: call for call in self.calls}

            # Add the calls to the Lambda FunctionScope
            if self.calls and isinstance(self.current_node_stack[-1], FunctionScope) and isinstance(self.current_node_stack[-1].symbol.node, astroid.Lambda):
                self.current_node_stack[-1].calls = {call.symbol.name: call for call in self.calls}
            self.calls = []

            # Add all globals that are used inside the Lambda to the parent function globals' list
            if self.current_node_stack[-1].globals:  # type: ignore[union-attr] # we can ignore the linter error because the current scope node is always of type FunctionScope and therefor has a parameter attribute.
                for glob_name, glob_def_list in self.current_node_stack[-1].globals.items():  # type: ignore[union-attr] # see above
                    if glob_name not in self.last_function_def[-2].globals:
                        self.last_function_def[-2].globals[glob_name] = glob_def_list
                    else:
                        for glob_def in glob_def_list:
                            if glob_def not in self.last_function_def[-2].globals[glob_name]:
                                self.last_function_def[-2].globals[glob_name].append(glob_def)

        self.current_node_stack.pop()  # Remove the current node from the stack

    def _analyze_constructor(self) -> None:
        """Analyze the constructor of a class.

        The constructor of a class is a special function called when an instance of the class is created.
        This function must only be called when the name of the FunctionDef node is `__init__`.
        """
        # add instance variables to the instance_variables list of the class
        for child in self.current_node_stack[-1].children:
            if isinstance(child.symbol, InstanceVariable) and isinstance(
                self.current_node_stack[-1].parent,
                ClassScope,
            ):
                if child.symbol.name in self.current_node_stack[-1].parent.instance_variables:
                    self.current_node_stack[-1].parent.instance_variables[child.symbol.name].append(child.symbol)
                else:
                    self.current_node_stack[-1].parent.instance_variables[child.symbol.name] = [child.symbol]

    def find_first_parent_function(self, node: astroid.NodeNG) -> astroid.NodeNG:
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
        # TODO: does this work with Lambdas as well?
        if isinstance(node.parent, astroid.FunctionDef | astroid.Lambda | astroid.Module | None):
            return node.parent
        return self.find_first_parent_function(node.parent)

    def collect_function_references(self) -> dict[NodeID, Reasons]:
        """Collect all function references in the module.

        This function must only be called after the scope of all nodes has been determined,
        and the module scope is the current node.
        Iterate over all functions and find all function references in the module.
        Therefore, we loop over all target nodes and check if they are used in the function body of each function.
        The same is done for all value nodes and all calls/class initializations.

        Returns
        -------
        dict[NodeID, Reasons]
            A dict containing all function references in the module.
            The dict is structured as follows:
            {
                "NodeID_of_function": Reasons(
                    function_def_node,
                    {FunctionReference}, # writes
                    {FunctionReference}, # reads
                    {FunctionReference}, # calls
                )
                ...
            }
        """
        python_builtins = dir(builtins)
        function_references: dict[NodeID, Reasons] = {}

        for function_scopes in self.functions.values():
            for function_node in function_scopes:  # iterate over all functions with the same name
                function_id = calc_node_id(function_node.symbol.node)
                function_def_node = function_node.symbol.node

                # Look at all target nodes and check if they are used in the function body
                for target in self.target_nodes:
                    # Only look at global variables (for global reads)
                    if target.name in self.global_variables or isinstance(target, MemberAccessTarget):  # Filter out all non-global variables
                        for child in function_node.children:
                            if target.name == child.symbol.name and child in function_node.children:
                                ref = child.symbol

                                if function_id in function_references:  # check if the function is already in the dict
                                    if ref not in function_references[function_id]:
                                        function_references[function_id].writes.add(ref)
                                else:  # create a new entry in the dict
                                    function_references[function_id] = Reasons(
                                        function_def_node,
                                        {ref},
                                        set(),
                                        set(),
                                    )  # Add writes

                # Look at all value nodes and check if they are used in the function body
                for value in self.value_nodes:
                    if isinstance(self.functions[function_id.name][0], FunctionScope):
                        # Since we do not differentiate between functions with the same name, we can choose the first one
                        # TODO: this is not correct. also cache this since it is called multiple times
                        function_values = self.functions[function_id.name][0].values
                        if value.name in function_values:
                            if value.name in self.global_variables or isinstance(value, MemberAccessValue):
                                # Get the correct symbol
                                sym = None
                                if isinstance(self.value_nodes[value], FunctionScope):
                                    for val_list in self.value_nodes[value].values.values():  # type: ignore[union-attr] # we can ignore the linter error because of the if statement above
                                        for val in val_list:
                                            if val.node == value:
                                                sym = val
                                                break
                                else:
                                    # raise TypeError(f"{self.value_nodes[value]} is not of type FunctionScope")
                                    continue

                                ref = sym

                                if function_id in function_references:  # check if the function is already in the dict
                                    function_references[function_id].reads.add(ref)
                                else:  # create a new entry in the dict
                                    function_references[function_id] = Reasons(
                                        function_def_node,
                                        set(),
                                        {ref},
                                        set(),
                                    )  # Add reads

                # Look at all calls and check if they are used in the function body
                unknown = []
                for call in self.function_calls:
                    # make sure we do not get an AttributeError because of the inconsistent names in the astroid API
                    if isinstance(call.func, astroid.Attribute):
                        call_func_name = call.func.attrname
                    else:
                        call_func_name = call.func.name

                    parent_function = self.find_first_parent_function(call)
                    function_scopes_calls_names = [c.symbol.name for c in function_node.calls.values()]
                    if call_func_name in function_scopes_calls_names and parent_function.name == function_id.name:
                        # get the correct symbol
                        sym = None
                        ref = None
                        # check all self defined functions
                        if call_func_name in self.functions:
                            sym = self.functions[call_func_name][0].symbol
                        # check all self defined classes
                        elif call_func_name in self.classes:
                            sym = self.classes[call_func_name].symbol
                        # check all builtins
                        elif call_func_name in python_builtins:
                            sym = Builtin(call, NodeID("builtins", call_func_name, 0, 0), call_func_name)
                        # check if a parameter of the function is called
                        # elif isinstance(parent_function, astroid.FunctionDef) and parent_function in self.parameters:
                        #     for i, p in enumerate(self.parameters[parent_function][1]):
                        #         if p.name == call_func_name:
                        #             sym = self.parameters[parent_function][1][i]
                        #             break
                        elif isinstance(parent_function, astroid.FunctionDef):
                            fun_list = self.functions[parent_function.name]
                            fun = None
                            for f in fun_list:
                                if f.symbol.node == parent_function:
                                    fun = f
                                    break
                            if fun is not None:
                                for par_name, par in fun.parameters.items():
                                    if par_name == call_func_name:
                                        sym = par
                                        break

                        if sym is None:
                            unknown.append(call)
                        else:
                            ref = Symbol(call, calc_node_id(call), call_func_name)

                        if function_id in function_references:  # check if the function is already in the dict
                            function_references[function_id].calls.add(ref)
                        else:  # create a new entry in the dict
                            function_references[function_id] = Reasons(
                                function_def_node,
                            )  # Add calls
                            if ref:
                                function_references[function_id].calls.add(ref)
                            if unknown:
                                function_references[function_id].unknown_calls = unknown

                # Add function to function_references dict if no reason (write, read nor call) was found
                if function_id not in function_references:
                    function_references[function_id] = Reasons(function_def_node, set(), set(), set())

        # remove duplicate calls from reads
        if self.function_calls:
            for ref in function_references.values():
                if not isinstance(ref, Reasons):
                    raise TypeError("ref is not of type Reasons")
                if ref.calls and ref.reads:
                    ref.remove_class_method_calls_from_reads()
        return function_references

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
        self.last_function_def.append(self.current_node_stack[-1])  # type: ignore[arg-type] # we can be sure that the top of the current node stack is of type FunctionScope

    def leave_functiondef(self, node: astroid.FunctionDef) -> None:
        self._detect_scope(node)
        # self.cleanup_globals(self.last_function_def[-1])
        self.last_function_def.pop()

    @staticmethod
    def cleanup_globals(function_scope: FunctionScope) -> None:
        """Remove all global variables that are shadowed by local variables.

        This function is called after the ASTWalker has walked all children of a function def and all their scopes are determined.
        It removes all global variables from the globals dict that are shadowed by local variables.
        """
        if not isinstance(function_scope, FunctionScope) or not function_scope.globals:
            return
        for glob_name in function_scope.globals.copy():
            if glob_name in [child.symbol.name for child in function_scope.children if isinstance(child.symbol, LocalVariable)]:
                del function_scope.globals[glob_name]

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

                if isinstance(node, MemberAccessTarget):
                    klass = self.get_class_for_receiver_node(node.receiver)
                    if klass is not None:
                        if (
                            node.member.attrname in klass.class_variables
                        ):  # This means that we are dealing with a class variable
                            return ClassVariable(
                                node=node,
                                id=calc_node_id(node),
                                name=node.member.attrname,
                                klass=klass.symbol.node,
                            )
                    # This means that we are dealing with an instance variable
                    elif self.classes is not None:
                        for klass in self.classes.values():
                            if node.member.attrname in klass.instance_variables:
                                return InstanceVariable(
                                    node=node,
                                    id=calc_node_id(node),
                                    name=node.member.attrname,
                                    klass=klass.symbol.node,
                                )
                if isinstance(
                    node,
                    _ComprehensionType | astroid.Lambda | astroid.TryExcept | astroid.TryFinally,
                ) and not isinstance(node, astroid.FunctionDef):
                    return GlobalVariable(node=node, id=calc_node_id(node), name=node.__class__.__name__)
                return GlobalVariable(node=node, id=calc_node_id(node), name=node.name)

            case astroid.ClassDef():
                # We defined that functions are class variables if they are defined in the class scope
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
                        name=node.member.attrname,
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

                # Special cases for nodes inside functions that we defined as LocalVariables but which do not have a name
                if isinstance(node, _ComprehensionType | astroid.Lambda | astroid.TryExcept | astroid.TryFinally):
                    return LocalVariable(node=node, id=calc_node_id(node), name=node.__class__.__name__)

                if isinstance(node, astroid.Name | astroid.AssignName) and node.name in self.global_variables:
                    # TODO: detect the case where a global variable is shadowed in the function scope as LocalVariable
                    return GlobalVariable(node=node, id=calc_node_id(node), name=node.name)

                if isinstance(node, astroid.Call):
                    # make sure we do not get an AttributeError because of the inconsistent names in the astroid API
                    if isinstance(node.func, astroid.Attribute):
                        return LocalVariable(node=node, id=calc_node_id(node), name=node.func.attrname)
                    return LocalVariable(node=node, id=calc_node_id(node), name=node.func.name)

                return LocalVariable(node=node, id=calc_node_id(node), name=node.name)

            case astroid.Lambda() | astroid.ListComp() | astroid.DictComp() | astroid.SetComp() | astroid.GeneratorExp():
                if isinstance(node, astroid.Call):
                    # make sure we do not get an AttributeError because of the inconsistent names in the astroid API
                    if isinstance(node.func, astroid.Attribute):
                        return LocalVariable(node=node, id=calc_node_id(node), name=node.func.attrname)
                    return LocalVariable(node=node, id=calc_node_id(node), name=node.func.name)
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
        self.last_function_def.append(self.current_node_stack[-1])  # type: ignore[arg-type] # we can be sure that the top of the current node stack is of type FunctionScope

    def leave_lambda(self, node: astroid.Lambda) -> None:
        self._detect_scope(node)
        self.last_function_def.pop()

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

    # TODO: [Refactor] when refactoring the FunctionScope class to use properties, move this to the FunctionScope class
    def add_arg_to_function_scope_parameters(self, argument: astroid.AssignName) -> None:
        """Add an argument to the parameters dict of the current function scope.

        Parameters
        ----------
        argument : astroid.AssignName
            The argument node to add to the parameter dict.
        """
        if isinstance(self.current_node_stack[-1], FunctionScope) and argument.name != "self" and argument.name != "cls":
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
            # both the target_nodes and the value_nodes dict since there is a case where a name node is used as a
            # target we need to check if the node is already in the target_nodes dict this is only the case if the
            # name node is the receiver of a MemberAccessTarget node it is made sure that in this case the node is
            # definitely in the target_nodes dict because the MemberAccessTarget node is added to the dict before the
            # name node
            if node not in self.target_nodes:
                self.value_nodes[node] = self.current_node_stack[-1]

        elif isinstance(node.parent, astroid.AssignAttr):
            self.target_nodes[node] = self.current_node_stack[-1]
        if (
            isinstance(node.parent, astroid.Call)
            and isinstance(node.parent.func, astroid.Name)
            and node.parent.func.name != node.name
        ):
            # Append a node only then when it is not the name node of the function
            self.value_nodes[node] = self.current_node_stack[-1]

        # idee: hole die letzte function def vom stack und füge alle namen hinzu
        # mache eine ausnahme für den fall, dass der current_node_stack[-1] ein Scope ist, dass einen lokalen Scope definiert:
        # TODO: dazu zählen ListComp, Lambda, TryExcept??, TryFinally??

        func_def = self.find_first_parent_function(node)

        if self.last_function_def and func_def == self.last_function_def[-1].symbol.node:
            # Exclude propagation to a function scope if we deal with a scope within that function that defined a local scope itself
            # e.g. ListComp, SetComp, DictComp, GeneratorExp
            # Except the name node is a global variable
            if isinstance(self.current_node_stack[-1].symbol.node, _ComprehensionType) and node.name not in self.global_variables:
                return

            # Deal with some special cases that need to be excluded
            if isinstance(node, astroid.Name):
                # We ignore self and cls because they are not relevant for purity by our means
                if node.name in ("self", "cls"):
                    return

                # Call removes the function name
                if isinstance(node.parent, astroid.Call):
                    if isinstance(node.parent.func, astroid.Attribute):
                        if node.parent.func.attrname == node.name:
                            return
                    elif isinstance(node.parent.func, astroid.Name):
                        if node.parent.func.name == node.name:
                            return

                # Check if the Name belongs to a type hint
                if self.is_annotated(node, False):
                    return

            parent = self.current_node_stack[-1]
            name_node = Scope(
                _symbol=self.get_symbol(node, self.current_node_stack[-1].symbol.node),
                _children=[],
                _parent=parent,
            )
            if name_node not in self.names:
                self.names.append(name_node)

            # Add the name to the globals list of the surrounding function if it is a variable of global scope
            global_node_defs = self.check_if_global(node.name, node)
            if global_node_defs:
                # It is possible that a variable has more than one global assignment
                # (particularly in cases where the variable is depending on a condition.
                # Since we do not check if those are met, we add them all)
                for global_node_def in global_node_defs:
                    # Propagate global variables in Comprehension type to the surrounding function if it is a global variable
                    if isinstance(global_node_def, astroid.AssignName) and (isinstance(self.current_node_stack[-1], FunctionScope) or isinstance(self.current_node_stack[-1].symbol.node, _ComprehensionType | astroid.Lambda)):
                        # Create a new dict entry for a global variable (by name)
                        if node.name not in self.last_function_def[-1].globals:
                            symbol = self.get_symbol(global_node_def, self.last_function_def[-1].symbol.node)
                            if isinstance(symbol, GlobalVariable):
                                self.last_function_def[-1].globals[node.name] = [symbol]
                        # If the name of the global variable already exists, add the new declaration to the list (redeclaration)
                        else:
                            symbol = self.get_symbol(global_node_def, self.last_function_def[-1].symbol.node)
                            if symbol not in self.last_function_def[-1].globals[node.name] and isinstance(symbol, GlobalVariable):
                                self.last_function_def[-1].globals[node.name].append(symbol)
                # TODO: check if the global is used as type annotation, if it is, dont add it
                return

    def is_annotated(self, node: astroid.NodeNG, found_annotation_node: bool) -> bool:
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
            found_annotation_node = True

        # Return the current bool if an assignment node is found.
        # This is the case when there are no more nested nodes that could contain a type hint property.
        if isinstance(node, astroid.Assign) or found_annotation_node:
            return found_annotation_node

        elif node.parent is not None:
            found_annotation_node = self.is_annotated(node.parent, found_annotation_node)
            if isinstance(node, astroid.Assign) or found_annotation_node:
                return found_annotation_node

    def enter_assignname(self, node: astroid.AssignName) -> None:
        # We do not want lambda assignments to be added to the target_nodes dict because they are handled as functions
        if isinstance(node.parent, astroid.Assign) and isinstance(node.parent.value, astroid.Lambda):
            return

        # The following nodes are added to the target_nodes dict because they are real assignments and therefore targets
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

        # The following nodes are no real target nodes, but astroid generates an AssignName node for them.
        # They still need to be added to the children of the current scope
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

            # Detect global assignments and add them to the global_variables dict
            if isinstance(node.root(), astroid.Module) and node.name in node.root().globals:
                self.global_variables[node.name] = scope_node

    def enter_assignattr(self, node: astroid.AssignAttr) -> None:
        parent = self.current_node_stack[-1]
        member_access = _construct_member_access_target(node.expr, node)
        scope_node = Scope(
            _symbol=self.get_symbol(member_access, self.current_node_stack[-1].symbol.node),
            _children=[],
            _parent=parent,
        )
        self.children.append(scope_node)

        if isinstance(member_access, MemberAccessTarget):
            self.target_nodes[member_access] = self.current_node_stack[-1]
        if isinstance(member_access, MemberAccessValue):
            self.value_nodes[member_access] = self.current_node_stack[-1]

    def enter_attribute(self, node: astroid.Attribute) -> None:
        # We do not want to handle names used in decorators
        if isinstance(node.parent, astroid.Decorators):
            return

        member_access = _construct_member_access_value(node.expr, node)
        # Astroid generates an Attribute node for every attribute access.
        # We therefore need to check if the attribute access is a target or a value.
        if isinstance(node.parent, astroid.AssignAttr) or self.has_assignattr_parent(node):
            member_access = _construct_member_access_target(node.expr, node)
            if isinstance(node.expr, astroid.Name):
                self.target_nodes[node.expr] = self.current_node_stack[-1]

        if isinstance(member_access, MemberAccessTarget):
            self.target_nodes[member_access] = self.current_node_stack[-1]
        elif isinstance(member_access, MemberAccessValue):

            # We ignore self and cls because they are not relevant for purity by our means.
            top_receiver = member_access.get_top_level_receiver()

            if self.is_annotated(top_receiver, False):
                return

            print("ALARM MEMBER", node)

            self.value_nodes[member_access] = self.current_node_stack[-1]
            parent = self.current_node_stack[-1]
            name_node = Scope(
                _symbol=self.get_symbol(member_access, self.current_node_stack[-1].symbol.node),  # TODO: for now we use the complete name of the attribute access as the name of the node and do not check the components for their real scoping
                _children=[],
                _parent=parent,
            )
            self.names.append(name_node)

    @staticmethod
    def has_assignattr_parent(node: astroid.Attribute) -> bool:
        """Check if any parent of the given node is an AssignAttr node.

        Since astroid generates an Attribute node for every attribute access,
        and it is possible to have nested attribute accesses,
        it is possible that the direct parent is not an AssignAttr node.
        In this case, we need to check if any parent of the given node is an AssignAttr node.

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
        current_node = node
        while current_node is not None:
            if isinstance(current_node, astroid.AssignAttr):
                return True
            current_node = current_node.parent
        return False

    def enter_global(self, node: astroid.Global) -> None:
        """Enter a global node.

        Global nodes are used to declare global variables inside a function.
        We will collect all these global variable usages and add them to the globals dict of that FunctionScope
        """
        for name in node.names:
            global_node_defs = self.check_if_global(name, node)
            if global_node_defs:
                # It is possible that a variable has more than one global assignment
                # (particularly in cases where the variable is depending on a condition.
                # Since we do not check if those are met, we add them all)
                for global_node_def in global_node_defs:
                    if (isinstance(global_node_def, astroid.AssignName) and
                       isinstance(self.current_node_stack[-1], FunctionScope)):
                        symbol = self.get_symbol(global_node_def, self.current_node_stack[-1].symbol.node)
                        if isinstance(symbol, GlobalVariable):
                            if name not in self.current_node_stack[-1].globals:
                                self.current_node_stack[-1].globals[name] = [symbol]
                            else:
                                self.current_node_stack[-1].globals[name].append(symbol)

    def enter_call(self, node: astroid.Call) -> None:
        if isinstance(node.func, astroid.Name | astroid.Attribute):
            self.function_calls[node] = self.current_node_stack[-1]

            # Add the call node to the calls
            if isinstance(self.current_node_stack[-1], FunctionScope):
                call_node = Scope(
                    _symbol=self.get_symbol(node, self.current_node_stack[-1].symbol.node),
                    _children=[],
                    _parent=self.current_node_stack[-1],
                )
                self.calls.append(call_node)
            else:
                # Add the call node to the calls of the last function definition to ensure it is considered in the call graph
                # since it would otherwise be lost in the (local) Scope of the Comprehension
                if isinstance(self.current_node_stack[-1].symbol.node, _ComprehensionType) and self.last_function_def:
                    call_node = Scope(
                        _symbol=self.get_symbol(node, self.current_node_stack[-1].symbol.node),
                        _children=[],
                        _parent=self.current_node_stack[-1],
                    )
                    self.last_function_def[-1].calls.update({call_node.symbol.name: call_node})

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
            return node.globals[name]
        return None

    def find_base_classes(self, node: astroid.ClassDef) -> list[ClassScope]:
        """Find a list of all base classes of the given class.

        If a class has no base classes, an empty list is returned.

        Parameters
        ----------
        node : astroid.ClassDef
            The class whose base classes are to be found.

        Returns
        -------
        list[ClassScope]
            A list of all base classes of the given class.
        """
        base_classes = []
        for base in node.bases:
            if isinstance(base, astroid.Name):
                base_class = self.get_class_by_name(base.name)
                if isinstance(base_class, ClassScope):
                    base_classes.append(base_class)
        return base_classes

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
            None will never be returned since we only call this function when we know that the class exists.
        """
        for klass in self.classes:
            if klass == name:
                return self.classes[klass]
        # This is not possible because we only call this function when we know that the class exists
        return None  # pragma: no cover

    def handle_arg(self, constructed_node: astroid.AssignName) -> None:
        """Handle an argument node.

        This function is called when an vararg or a kwarg parameter is found inside of an Argument node.
        This is needed because astroid does not generate a symbol for these nodes.
        Therefore, we need to create one manually and add it to the parameters dict.

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

    # TODO: move this to MemberAccessTarget
    def get_class_for_receiver_node(self, receiver: MemberAccessTarget) -> ClassScope | None:
        """Get the class for the given receiver node.

        When dealing with MemberAccessTarget nodes,
        we need to find the class of the receiver node since the MemberAccessTarget node does not have a symbol.

        Parameters
        ----------
        receiver : MemberAccessTarget
            The receiver node whose class is to be found.

        Returns
        -------
        ClassScope | None
            The class of the given receiver node if it exists, None otherwise.
        """
        if isinstance(receiver, astroid.Name) and receiver.name in self.classes:
            return self.classes[receiver.name]
        return None


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
            return NodeID(module, node.name, node.fromlineno, node.col_offset)
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
            # make sure we do not get an AttributeError because of the inconsistent names in the astroid API
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

    # TODO: add fitting default case and merge same types of cases together


def _construct_member_access_target(
    receiver: astroid.Name | astroid.Attribute | astroid.Call,
    member: astroid.AssignAttr | astroid.Attribute,
) -> MemberAccessTarget:
    """Construct a MemberAccessTarget node.

    Constructing a MemberAccessTarget node means constructing a MemberAccessTarget node with the given receiver and member.
    The receiver is the node that is accessed, and the member is the node that accesses the receiver. The receiver can be nested.

    Parameters
    ----------
    receiver : astroid.Name | astroid.Attribute | astroid.Call
        The receiver node.
    member : astroid.AssignAttr | astroid.Attribute
        The member node.

    Returns
    -------
    MemberAccessTarget
        The constructed MemberAccessTarget node.
    """
    try:
        if isinstance(receiver, astroid.Name):
            return MemberAccessTarget(receiver=receiver, member=member)
        elif isinstance(receiver, astroid.Call):
            return MemberAccessTarget(receiver=receiver.func, member=member)
        else:
            return MemberAccessTarget(receiver=_construct_member_access_target(receiver.expr, receiver), member=member)
    # Since it is tedious to add testcases for this function, we ignore the coverage for now
    except TypeError as err:  # pragma: no cover
        raise TypeError(f"Unexpected node type {type(member)}") from err  # pragma: no cover


def _construct_member_access_value(
    receiver: astroid.Name | astroid.Attribute | astroid.Call,
    member: astroid.Attribute,
) -> MemberAccessValue:
    """Construct a MemberAccessValue node.

    Constructing a MemberAccessValue node means constructing a MemberAccessValue node with the given receiver and member.
    The receiver is the node that is accessed, and the member is the node that accesses the receiver. The receiver can be nested.

    Parameters
    ----------
    receiver : astroid.Name | astroid.Attribute | astroid.Call
        The receiver node.
    member : astroid.Attribute
        The member node.

    Returns
    -------
    MemberAccessValue
        The constructed MemberAccessValue node.
    """
    try:
        if isinstance(receiver, astroid.Name):
            return MemberAccessValue(receiver=receiver, member=member)
        elif isinstance(receiver, astroid.Call):
            return MemberAccessValue(receiver=receiver.func, member=member)
        else:
            return MemberAccessValue(receiver=_construct_member_access_value(receiver.expr, receiver), member=member)
    # Since it is tedious to add testcases for this function, we ignore the coverage for now
    except TypeError as err:  # pragma: no cover
        raise TypeError(f"Unexpected node type {type(member)}") from err  # pragma: no cover


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
        function_references=module_data_handler.function_references,
    )
