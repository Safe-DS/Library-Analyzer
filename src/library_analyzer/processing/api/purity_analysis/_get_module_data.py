from __future__ import annotations

from dataclasses import dataclass, field

import astroid

from library_analyzer.processing.api.purity_analysis.model import (
    BUILTIN_CLASSSCOPES,
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
    ParameterKind,
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
    current_node_stack : list[Scope]
        Stack of nodes that are currently visited by the ASTWalker.
        The last node in the stack is the current node.
        It Is only used while walking the AST.
    current_function_def : list[FunctionScope]
        Stack of FunctionScopes that are currently visited by the ASTWalker.
        The top of the stack is the current function definition.
        It is only used while walking the AST.
    children : list[Scope]
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
    global_variables : dict[str, Scope]
        All global variables and their corresponding Scope instance.
    imports : dict[str, Import]
        All imports and their corresponding Import instance.
    """

    current_node_stack: list[Scope] = field(default_factory=list)
    current_function_def: list[FunctionScope] = field(default_factory=list)
    children: list[Scope] = field(default_factory=list)
    targets: list[Symbol] = field(default_factory=list)
    values: list[Reference] = field(default_factory=list)
    calls: list[Reference] = field(default_factory=list)
    classes: dict[str, ClassScope] = field(default_factory=dict)
    functions: dict[str, list[FunctionScope]] = field(default_factory=dict)
    global_variables: dict[str, Scope] = field(default_factory=dict)
    imports: dict[str, Import] = field(default_factory=dict)

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
        current_node = node
        while current_node is not None:
            if isinstance(current_node, astroid.AssignAttr):
                return True
            current_node = current_node.parent
        return False

    def get_symbol(self, node: astroid.NodeNG, current_scope: astroid.NodeNG | None) -> Symbol:
        """Get the symbol of a node.

        It matches the current scope of the node and returns the corresponding symbol for the given node.
        This function can not handle Import and ImportFrom nodes since they need special treatment.

        Parameters
        ----------
        node : astroid.NodeNG
            The node whose symbol is to be determined.
        current_scope : astroid.NodeNG | None
            The current scope of the node (is None if the node is the module node).
        """
        match current_scope:
            case astroid.Module() | None:
                if isinstance(
                    node,
                    _ComprehensionType | astroid.Lambda | astroid.TryExcept | astroid.TryFinally,
                ) and not isinstance(node, astroid.FunctionDef):
                    return GlobalVariable(node=node, id=NodeID.calc_node_id(node), name=node.__class__.__name__)
                return GlobalVariable(node=node, id=NodeID.calc_node_id(node), name=node.name)

            case astroid.ClassDef():
                # Functions inside a class are defined as class variables if they are defined in the class scope.
                # if isinstance(node, astroid.FunctionDef):
                #     return LocalVariable(node=node, id=_NodeID.calc_node_id(node), name=node.name)
                if isinstance(
                    node,
                    _ComprehensionType | astroid.Lambda | astroid.TryExcept | astroid.TryFinally,
                ) and not isinstance(node, astroid.FunctionDef):
                    return ClassVariable(
                        node=node,
                        id=NodeID.calc_node_id(node),
                        name=node.__class__.__name__,
                        klass=current_scope,
                    )
                return ClassVariable(node=node, id=NodeID.calc_node_id(node), name=node.name, klass=current_scope)

            case astroid.FunctionDef():
                # Find instance variables (in the constructor)
                if (
                    isinstance(current_scope, astroid.FunctionDef)
                    and isinstance(node, MemberAccessTarget)
                    and current_scope.name == "__init__"
                ):
                    return InstanceVariable(
                        node=node,
                        id=NodeID.calc_node_id(node),
                        name=node.member,
                        klass=current_scope.parent,
                    )

                # Find parameters
                if (
                    isinstance(node, astroid.AssignName)
                    and isinstance(self.current_node_stack[-1], FunctionScope)
                    and node.name in self.current_node_stack[-1].parameters
                ):
                    return Parameter(node=node, id=NodeID.calc_node_id(node), name=node.name)

                # Special cases for nodes inside functions that are defined as LocalVariables but which do not have a name
                if isinstance(node, _ComprehensionType | astroid.Lambda | astroid.TryExcept | astroid.TryFinally):
                    return LocalVariable(node=node, id=NodeID.calc_node_id(node), name=node.__class__.__name__)

                if (
                    isinstance(node, astroid.Name | astroid.AssignName)
                    and node.name in node.root().globals
                    and node.name not in current_scope.locals
                ):
                    return GlobalVariable(node=node, id=NodeID.calc_node_id(node), name=node.name)

                return LocalVariable(node=node, id=NodeID.calc_node_id(node), name=node.name)

            case (
                astroid.Lambda() | astroid.ListComp() | astroid.DictComp() | astroid.SetComp() | astroid.GeneratorExp()
            ):
                # This deals with the case where a lambda function has parameters
                if isinstance(node, astroid.AssignName) and isinstance(node.parent, astroid.Arguments):
                    return Parameter(node=node, id=NodeID.calc_node_id(node), name=node.name)
                # This deals with global variables that are used inside a lambda
                if isinstance(node, astroid.AssignName) and node.name in self.global_variables:
                    return GlobalVariable(node=node, id=NodeID.calc_node_id(node), name=node.name)
                return LocalVariable(
                    node=node,
                    id=NodeID.calc_node_id(node),
                    name=node.name if hasattr(node, "name") else "None",
                )

            case (
                astroid.TryExcept() | astroid.TryFinally()
            ):  # TODO: can we summarize Lambda and ListComp here? -> only if nodes in try except are not global
                return LocalVariable(
                    node=node,
                    id=NodeID.calc_node_id(node),
                    name=node.name if hasattr(node, "name") else "None",
                )

        # This line is a fallback but should never be reached
        return Symbol(node=node, id=NodeID.calc_node_id(node), name=node.name)  # pragma: no cover

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
        outer_scope_children: list[Scope] = []
        inner_scope_children: list[Scope] = []
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

                # Special case for try-except and try-finally nodes.
                # There is no need to add another nested scope for try-except and try-finally nodes.
                # If a try-finally node is the parent of a try-except node,
                # add all children of the try-finally node and remove the try-except node.
                if isinstance(current_node, astroid.TryFinally) and isinstance(child.symbol.node, astroid.TryExcept):
                    inner_scope_children.extend(child.children)
                    if child in inner_scope_children:
                        inner_scope_children.remove(child)

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
        if isinstance(self.current_node_stack[-1], ClassScope):
            self.classes[current_node.name] = self.current_node_stack[-1]

        # Add class variables to the class_variables dict.
        for child in self.current_node_stack[-1].children:
            if (
                isinstance(child.symbol, ClassVariable)
                and isinstance(self.current_node_stack[-1], ClassScope)
                and hasattr(self.current_node_stack[-1], "class_variables")
            ):
                self.current_node_stack[-1].class_variables.setdefault(child.symbol.name, []).append(child.symbol)

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
        if current_node.name in ("__init__", "__new__", "__post_init__"):
            self._analyze_constructor(current_node.name)

        # Add all calls that are used inside the function body to its calls' dict.
        if self.calls:
            for call in self.calls:
                self.functions[current_node.name][-1].call_references.setdefault(call.name, []).append(call)
            self.calls = []

        # Add all targets that are used inside the function body to its targets' dict.
        if self.targets:
            parent_targets = []
            for target in self.targets:
                if self.find_first_parent_function(target.node) == self.current_function_def[-1].symbol.node:
                    self.current_function_def[-1].target_symbols.setdefault(target.name, []).append(target)
                    self.targets = []
                else:
                    parent_targets.append(target)
            if parent_targets:
                self.targets = parent_targets

        # Add all values that are used inside the function body to its values' dict.
        if self.values:
            for value in self.values:
                if self.find_first_parent_function(value.node) == self.current_function_def[-1].symbol.node:
                    self.current_function_def[-1].value_references.setdefault(value.name, []).append(value)
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
            elif isinstance(current_node.parent.targets[0], astroid.AssignName):
                node_name = current_node.parent.targets[0].name
            else:
                node_name = "Lambda"
            # If the Lambda function is assigned to a name, it can be called just as a normal function.
            # Since Lambdas normally do not have names, they need to be assigned manually.
            self.current_function_def[-1].symbol.name = node_name
            self.current_function_def[-1].symbol.node.name = node_name
            self.current_function_def[-1].symbol.id.name = node_name

            # Extend the dict of functions with the current node or create a new list with the current node.
            self.functions.setdefault(node_name, []).append(self.current_function_def[-1])

            # Add all targets that are used inside the function body to its targets' dict.
            if self.targets:
                for target in self.targets:
                    self.current_function_def[-1].target_symbols.setdefault(target.name, []).append(target)
                self.targets = []

            # Add all values that are used inside the function body to its values' dict.
            if self.values:
                for value in self.values:
                    self.current_function_def[-1].value_references.setdefault(value.name, []).append(value)
                self.values = []

            # Add all calls that are used inside the function body to its calls' dict.
            if self.calls:
                for call in self.calls:
                    self.functions[current_node.name][-1].call_references.setdefault(call.name, []).append(call)
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
                    self.current_function_def[-1].target_symbols.setdefault(target.name, []).append(target)
                self.targets = []

            # Add all values that are used inside the lambda body to its parent function values' dict.
            if (
                self.values
                and len(self.current_function_def) >= 2
                and isinstance(self.current_node_stack[-2], FunctionScope)
            ):
                for value in self.values:
                    if value.name not in self.current_function_def[-1].parameters:
                        self.current_function_def[-2].value_references.setdefault(value.name, []).append(value)

            # Add the values to the Lambda FunctionScope.
            if (
                self.values
                and isinstance(self.current_function_def[-1], FunctionScope)
                and isinstance(self.current_function_def[-1].symbol.node, astroid.Lambda)
            ):
                for value in self.values:
                    self.current_function_def[-1].value_references.setdefault(value.name, []).append(value)
            self.values = []

            # Add all calls that are used inside the lambda body to its parent function calls' dict.
            if (
                self.calls
                and len(self.current_function_def) >= 2
                and isinstance(self.current_function_def[-2], FunctionScope)
            ):
                for call in self.calls:
                    if call.name not in self.current_function_def[-2].call_references:
                        self.current_function_def[-2].call_references[call.name] = [call]
                    else:
                        self.current_function_def[-2].call_references[call.name].append(call)

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
            if self.current_function_def[-1].globals_used:
                for glob_name, glob_def_list in self.current_function_def[-1].globals_used.items():
                    if (
                        len(self.current_function_def) >= 2
                        and glob_name not in self.current_function_def[-2].globals_used
                    ):
                        self.current_function_def[-2].globals_used[glob_name] = glob_def_list
                    else:
                        for glob_def in glob_def_list:
                            if (
                                len(self.current_function_def) >= 2
                                and glob_def not in self.current_function_def[-2].globals_used[glob_name]
                            ):
                                self.current_function_def[-2].globals_used[glob_name].append(glob_def)

    def _analyze_constructor(self, function_name: str) -> None:
        """Analyze the constructor of a class.

        The constructor of a class is a special function called when an instance of the class is created.
        This function must only be called when the name of the FunctionDef node is `__init__`.
        """
        if function_name == "__init__":
            # Add instance variables to the instance_variables list of the class.
            for child in self.current_function_def[-1].children:
                if (
                    isinstance(child.symbol, InstanceVariable)
                    and isinstance(self.current_function_def[-1].parent, ClassScope)
                    and hasattr(self.current_function_def[-1].parent, "instance_variables")
                ):
                    self.current_function_def[-1].parent.instance_variables.setdefault(child.symbol.name, []).append(
                        child.symbol,
                    )

            # Add __init__ function to ClassScope.
            if isinstance(self.current_function_def[-1].parent, ClassScope) and hasattr(
                self.current_function_def[-1].parent,
                "init_function",
            ):
                self.current_function_def[-1].parent.init_function = self.current_function_def[-1]
        elif function_name == "__new__":
            # Add __new__ function to ClassScope.
            if isinstance(self.current_function_def[-1].parent, ClassScope) and hasattr(
                self.current_function_def[-1].parent,
                "new_function",
            ):
                self.current_function_def[-1].parent.new_function = self.current_function_def[-1]
        elif function_name == "__post_init__":
            # Add __post_init__ function to ClassScope.
            if isinstance(self.current_function_def[-1].parent, ClassScope) and hasattr(
                self.current_function_def[-1].parent,
                "post_init_function",
            ):
                self.current_function_def[-1].parent.post_init_function = self.current_function_def[-1]

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

    def handle_arg(self, node: astroid.AssignName, kind: ParameterKind) -> None:
        """Handle an argument node.

        This function is called when a vararg or a kwarg parameter is found inside an Argument node.
        This is needed because astroid does not generate a symbol for these nodes.
        Therefore, create one manually and add it to the parameters' dict.

        Parameters
        ----------
        node : astroid.AssignName
            The node that is to be handled.
        kind : ParameterKind
            The kind of the parameter.
        """
        scope_node = Scope(
            _symbol=Parameter(node, NodeID.calc_node_id(node), node.name, kind=kind),
            _children=[],
            _parent=self.current_node_stack[-1],
        )
        self.targets.append(scope_node.symbol)
        self.children.append(scope_node)
        self.add_arg_to_function_scope_parameters(node, kind)

    def add_arg_to_function_scope_parameters(self, argument: astroid.AssignName, kind: ParameterKind) -> None:
        """Add an argument to the parameters dict of the current function scope.

        Parameters
        ----------
        argument : astroid.AssignName
            The argument node to add to the parameter dict.
        kind : ParameterKind
            The kind of the parameter.
        """
        if isinstance(self.current_node_stack[-1], FunctionScope):
            self.current_node_stack[-1].parameters[argument.name] = Parameter(
                argument,
                NodeID.calc_node_id(argument),
                argument.name,
                kind=kind,
            )

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
        list[astroid.AssignName] | None
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
            A list of all base classes of the given class if it has any, else an empty list.
        """
        base_classes: list[ClassScope] = []
        for base in node.bases:
            if isinstance(base, astroid.Name):
                if base.name in self.classes:
                    base_classes.append(self.classes[base.name])
                elif base.name in BUILTIN_CLASSSCOPES:
                    base_classes.append(BUILTIN_CLASSSCOPES[base.name])

        return base_classes

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
        if node.decorators:
            for decorator in node.decorators.nodes:
                if isinstance(decorator, astroid.Name) and decorator.name == "overload":
                    return
                elif isinstance(decorator, astroid.Name) and decorator.name == "property":
                    if isinstance(self.current_node_stack[-1], ClassScope) and hasattr(self.current_node_stack[-1], "instance_variables"):
                        self.current_node_stack[-1].instance_variables.setdefault(node.name, []).append(
                            InstanceVariable(
                                node=node,
                                id=NodeID.calc_node_id(node),
                                name=node.name,
                                klass=self.current_node_stack[-1].symbol.node,
                            ),
                        )

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
        if node.decorators:
            for decorator in node.decorators.nodes:
                if isinstance(decorator, astroid.Name) and decorator.name == "overload":
                    return

        self._detect_scope(node)
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

    def enter_tryfinally(self, node: astroid.TryFinally) -> None:
        self.current_node_stack.append(
            Scope(
                _symbol=self.get_symbol(node, self.current_node_stack[-1].symbol.node),
                _children=[],
                _parent=self.current_node_stack[-1],
            ),
        )

    def leave_tryfinally(self, node: astroid.TryFinally) -> None:
        self._detect_scope(node)

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
            for arg in node.args:
                kind = ParameterKind.POSITIONAL_OR_KEYWORD
                self.add_arg_to_function_scope_parameters(arg, kind)
        if node.kwonlyargs:
            for arg in node.kwonlyargs:
                kind = ParameterKind.KEYWORD_ONLY
                self.add_arg_to_function_scope_parameters(arg, kind)
        if node.posonlyargs:
            for arg in node.posonlyargs:
                kind = ParameterKind.POSITIONAL_ONLY
                self.add_arg_to_function_scope_parameters(arg, kind)
        if node.vararg:
            kind = ParameterKind.VAR_POSITIONAL
            constructed_node = astroid.AssignName(
                name=node.vararg,
                parent=node,
                lineno=(
                    node.parent.lineno
                    if isinstance(node.parent, astroid.FunctionDef) and not node.parent.decorators
                    else (
                        node.parent.lineno + len(node.parent.decorators.nodes)
                        if isinstance(node.parent, astroid.FunctionDef)
                        else node.parent.lineno
                    )
                ),
                col_offset=node.parent.col_offset,
            )
            self.handle_arg(constructed_node, kind)
            # TODO: col_offset is not correct: it should be the col_offset of the vararg/(kwarg) node which is not
            #  collected by astroid
        if node.kwarg:
            kind = ParameterKind.VAR_KEYWORD
            constructed_node = astroid.AssignName(
                name=node.kwarg,
                parent=node,
                lineno=(
                    node.parent.lineno
                    if isinstance(node.parent, astroid.FunctionDef) and not node.parent.decorators
                    else (
                        node.parent.lineno + len(node.parent.decorators.nodes)
                        if isinstance(node.parent, astroid.FunctionDef)
                        else node.parent.lineno
                    )
                ),
                col_offset=node.parent.col_offset,
            )
            self.handle_arg(constructed_node, kind)

    def enter_name(self, node: astroid.Name) -> None:
        # Do not add names of decorators as values, since are not needed.
        if isinstance(node.parent, astroid.Decorators) or isinstance(node.parent.parent, astroid.Decorators):
            return
        # Since astroid also uses Name nodes inside AssignAttr nodes, the following condition checks for that.
        # These names are not added to the values' list because they are not used as values.
        # Add the name to the targets dict to determine the scope of the name later.
        elif isinstance(node.parent, astroid.AssignAttr):
            self.targets.append(Symbol(node, NodeID.calc_node_id(node), node.name))

        # Add the name to the values' list to determine the scope of the name later.
        # Some cases need to be filtert out because they are not defined as values.
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

            # Deal with other cases that need to be excluded.
            if isinstance(node, astroid.Name):
                # Do not add the names, that astroid used inside AssignAttr.
                if isinstance(node.parent, astroid.AssignAttr):
                    return

                # Do not add the name of a function as a value.
                if isinstance(node.parent, astroid.Call):
                    if isinstance(node.parent.func, astroid.Attribute):
                        if node.parent.func.attrname == node.name:
                            return
                    elif isinstance(node.parent.func, astroid.Name):
                        if node.parent.func.name == node.name:
                            return

                # Check if the Name belongs to a type hint, if so do not add it.
                if self.is_annotated(node, found_annotation_node=False):
                    return

            # If none of the conditions above is true, the name node is added to the values' list.
            reference = Reference(node, NodeID.calc_node_id(node), node.name)
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
            | astroid.With,
        ):
            # Only add assignments if they are inside a function, or if they are inside a try-except block.
            # Nodes inside try-except will be propagated to the next function scope.
            if (
                isinstance(self.current_node_stack[-1], FunctionScope)
                or isinstance(self.current_node_stack[-1].symbol.node, astroid.TryExcept | astroid.TryFinally)
                and self.current_function_def
                and self.find_first_parent_function(node) == self.current_function_def[-1].symbol.node
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
        member_access = MemberAccessTarget.construct_member_access_target(node)
        scope_node = Scope(
            _symbol=self.get_symbol(member_access, self.current_node_stack[-1].symbol.node),
            _children=[],
            _parent=parent,
        )
        self.children.append(scope_node)

        if isinstance(self.current_node_stack[-1], FunctionScope):
            self.targets.append(Symbol(member_access, NodeID.calc_node_id(member_access), member_access.name))

    def enter_attribute(self, node: astroid.Attribute) -> None:
        # Do not handle names used in decorators since this would be to complex for now.
        if isinstance(node.parent, astroid.Decorators):
            return

        # Astroid generates an Attribute node for every attribute access.
        # Check if the attribute access is a target or a value.
        # Subscript deals with assignments to a dictionary.
        if (
            isinstance(node.parent, astroid.AssignAttr)
            or isinstance(node.parent, astroid.Subscript)
            and not isinstance(node.parent.parent, astroid.Arguments)
            or self.has_assignattr_parent(node)
        ):
            member_access = MemberAccessTarget.construct_member_access_target(node)
            if isinstance(node.expr, astroid.Name) and isinstance(self.current_node_stack[-1], FunctionScope):
                self.targets.append(Symbol(member_access, NodeID.calc_node_id(member_access), member_access.name))
        else:
            member_access = MemberAccessValue.construct_member_access_value(node)

        if isinstance(member_access, MemberAccessTarget):
            if isinstance(self.current_node_stack[-1], FunctionScope):
                self.targets.append(Symbol(member_access, NodeID.calc_node_id(member_access), member_access.name))
        elif isinstance(member_access, MemberAccessValue):
            # Ignore type annotations because they are not relevant for purity.
            if self.is_annotated(member_access.node, found_annotation_node=False):
                return

            reference = Reference(member_access, NodeID.calc_node_id(member_access), member_access.name)
            self.values.append(reference)

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
                        if isinstance(symbol, GlobalVariable) and hasattr(self.current_node_stack[-1], "globals_used"):
                            self.current_node_stack[-1].globals_used.setdefault(name, []).append(symbol)

    def enter_call(self, node: astroid.Call) -> None:
        if isinstance(node.func, astroid.Name | astroid.Attribute):
            if isinstance(node.func, astroid.Attribute):
                call_name = node.func.attrname
            else:
                call_name = node.func.name

            call_reference = Reference(node, NodeID.calc_node_id(node), call_name)
            # Add the call node to the calls of the parent scope if it is of type FunctionScope.
            if isinstance(self.current_node_stack[-1], FunctionScope):
                self.calls.append(call_reference)
            else:  # noqa: PLR5501
                # Add the call node to the calls of the last function definition to ensure it is considered
                # in the call graph since it would otherwise be lost in the (local) Scope of the Comprehension.
                if (
                    isinstance(
                        self.current_node_stack[-1].symbol.node,
                        _ComprehensionType | astroid.TryExcept | astroid.TryFinally,
                    )
                    and self.current_function_def
                ):
                    self.current_function_def[-1].call_references.setdefault(call_name, []).append(call_reference)

        # This deals with cases where a nested call calls the result of another call.
        # Like: fun(1)(2)(3), where fun1 returns a function.
        elif isinstance(node.func, astroid.Call):
            call_reference = Reference(node, NodeID.calc_node_id(node), "UNKNOWN")
            # Add the call node to the calls of the parent scope if it is of type FunctionScope.
            if isinstance(self.current_node_stack[-1], FunctionScope):
                self.calls.append(call_reference)
            else:  # noqa: PLR5501
                # Add the call node to the calls of the last function definition to ensure it is considered
                # in the call graph since it would otherwise be lost in the (local) Scope of the Comprehension.
                if (
                    isinstance(self.current_node_stack[-1].symbol.node, _ComprehensionType)
                    and self.current_function_def
                ):
                    self.current_function_def[-1].call_references.setdefault("UNKNOWN", []).append(call_reference)

    def enter_import(self, node: astroid.Import) -> None:
        parent = self.current_node_stack[-1]
        symbols: dict[str, Import] = {}
        for name_tuple in node.names:
            module = name_tuple[0]
            alias = name_tuple[1]
            if alias and isinstance(alias, str):
                import_symbol = Import(
                    node=node,
                    id=NodeID(node.root().name, module, node.lineno, node.col_offset),
                    # Do not use NodeID.calc_node_id here because it would use the wrong name as node name.
                    name=module,
                    module=module,
                    alias=alias,
                )
                symbols[import_symbol.alias] = import_symbol  # type: ignore[index] # It is checked, that alias is str.
            else:
                import_symbol = Import(
                    node=node,
                    id=NodeID(node.root().name, module, node.lineno, node.col_offset),
                    # Do not use NodeID.calc_node_id here because it would use the wrong name as node name.
                    name=module,
                    module=module,
                )
                symbols[import_symbol.name] = import_symbol
            scope_node = Scope(
                _symbol=import_symbol,
                _children=[],
                _parent=parent,
            )
            self.children.append(scope_node)

        self.imports.update(symbols)

    def enter_importfrom(self, node: astroid.ImportFrom) -> None:
        parent = self.current_node_stack[-1]
        symbols: dict[str, Import] = {}
        for name_tuple in node.names:
            module = node.modname
            name = name_tuple[0]
            alias = name_tuple[1]
            if alias and isinstance(alias, str):
                import_symbol = Import(
                    node=node,
                    id=NodeID(node.root().name, name, node.lineno, node.col_offset),
                    # Do not use NodeID.calc_node_id here because it would use the wrong name as node name.
                    name=name,
                    module=module,
                    alias=alias,
                )
                symbols[import_symbol.alias] = import_symbol  # type: ignore[index] # It is checked, that alias is str.
            else:
                import_symbol = Import(
                    node=node,
                    id=NodeID(node.root().name, name, node.lineno, node.col_offset),
                    # Do not use NodeID.calc_node_id here because it would use the wrong name as node name.
                    name=name,
                    module=module,
                )
                symbols[import_symbol.name] = import_symbol
            scope_node = Scope(
                _symbol=import_symbol,
                _children=[],
                _parent=parent,
            )
            self.children.append(scope_node)

        self.imports.update(symbols)


def get_module_data(code: str, module_name: str = "", path: str | None = None) -> ModuleData:
    """Get the module data of the given code.

    To get the module data of the given code, the code is parsed into an AST and then walked by an ASTWalker.
    The ModuleDataBuilder detects the scope of each node and builds a scope tree.
    The ModuleDataBuilder also collects all classes, functions, global variables, value nodes, target nodes, parameters,
    function calls, and function references.

    Parameters
    ----------
    code : str
        The source code of the module whose module data is to be found.
    module_name : str, optional
        The name of the module, by default "".
    path : str, optional
        The path of the module, by default None.

    Returns
    -------
    ModuleData
        The module data of the given module.

    Raises
    ------
    ValueError
        If the code has invalid syntax.
    """
    module_data_handler = ModuleDataBuilder()
    walker = ASTWalker(module_data_handler)
    try:
        module = astroid.parse(code, module_name, path)
    except astroid.AstroidSyntaxError as e:
        raise ValueError(f"Invalid syntax in code: {e}") from e
    walker.walk(module)

    scope = module_data_handler.children[0]  # Get the children of the root node, which are the scopes of the module

    return ModuleData(
        scope=scope,
        classes=module_data_handler.classes,
        functions=module_data_handler.functions,
        imports=module_data_handler.imports,
    )
