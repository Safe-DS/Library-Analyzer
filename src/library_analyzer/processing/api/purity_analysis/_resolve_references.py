from __future__ import annotations

import builtins
import contextlib
import dataclasses

import astroid
from astroid.helpers import safe_infer

from library_analyzer.processing.api.purity_analysis import build_call_graph, get_module_data
from library_analyzer.processing.api.purity_analysis.model import (
    Builtin,
    BuiltinOpen,
    ClassScope,
    ClassVariable,
    FunctionScope,
    GlobalVariable,
    Import,
    InstanceVariable,
    MemberAccessTarget,
    MemberAccessValue,
    ModuleAnalysisResult,
    NodeID,
    PackageData,
    Reasons,
    Reference,
    ReferenceNode,
    Symbol,
    TargetReference,
    ValueReference,
)

_BUILTINS = dir(builtins)


class ReferenceResolver:
    """Class to resolve all references in a module.

    Attributes
    ----------
    functions : dict[str, list[FunctionScope]]
        The functions of the module.
    classes : dict[str, ClassScope]
        The classes of the module.
    imports : dict[str, Import]
        The imports of the module.
    module_analysis_result : ModuleAnalysisResult
        The result of the reference resolving.

    Parameters
    ----------
    code : str
        The code of the module.
    module_name : str
        The name of the module if any.
    path : str | None
        The path of the module if any.
    package_data : PackageData | None
        The module data of all modules the package.
        If provided, the references are resolved with the package data, else the module data is collected first.
        It is used for the inference of the purity between modules in the package.
    """

    functions: dict[str, list[FunctionScope]]
    classes: dict[str, ClassScope]
    imports: dict[str, Import]
    module_analysis_result: ModuleAnalysisResult = ModuleAnalysisResult()

    def __init__(self, code: str,
                 module_name: str = "",
                 path: str | None = None,
                 package_data: PackageData | None = None,
                 ):
        # Check if the module is part of a package and if the package data is given.
        if package_data and package_data.combined_module:
            module_data = package_data.combined_module
            self.module_analysis_result.module_id = module_data.scope.symbol.id
        else:
            # Initialize the Class by getting the module data for the given (module) code.
            try:
                module_data = get_module_data(code, module_name, path)
                self.module_analysis_result.module_id = module_data.scope.symbol.id
            except ValueError:
                return  # TODO: add error message to result?
        self.functions = module_data.functions
        self.classes = module_data.classes
        self.imports = module_data.imports

        # Resolve the references for the module.
        self.module_analysis_result.classes = self.classes
        resolved_references, raw_reasons = self._resolve_references()
        self.module_analysis_result.resolved_references = resolved_references
        self.module_analysis_result.raw_reasons = raw_reasons
        self.module_analysis_result.call_graph_forest = build_call_graph(self.classes,
                                                                         self.module_analysis_result.raw_reasons)

    @staticmethod
    def is_function_of_class(function: astroid.FunctionDef, klass: ClassScope) -> bool:
        """Check if a function is a method of a class.

        Parameters
        ----------
        function : astroid.FunctionDef
            The function to check.
        klass : ClassScope
            The class to check.

        Returns
        -------
        bool
            True if the function is a method of the class, False otherwise.
        """
        parent = function
        while not isinstance(parent, astroid.Module | None):
            if isinstance(parent, astroid.ClassDef) and parent == klass.symbol.node:
                return True
            elif isinstance(parent, astroid.ClassDef):
                return False
            parent = parent.parent
        return False

    @staticmethod
    def merge_dicts(
        d1: dict[str, list[ReferenceNode]],
        d2: dict[str, list[ReferenceNode]],
    ) -> dict[str, list[ReferenceNode]]:
        """Merge two dicts of lists of ReferenceNodes.

        Parameters
        ----------
        d1 : dict[str, list[ReferenceNode]]
            The first dict.
        d2 : dict[str, list[ReferenceNode]]
            The second dict.

        Returns
        -------
        d3 : dict[str, list[ReferenceNode]]
            The merged dict.
        """
        d3 = d1.copy()
        for key, value in d2.items():
            if key in d3:
                d3[key].extend(value)
            else:
                d3[key] = value
        return d3

    def _find_call_references(self,
                              call_reference: Reference,
                              function: FunctionScope,
                              ) -> ValueReference:
        """Find all references for a function call.

        This function finds all referenced Symbols for a call reference.
        A reference for a call node can be either a FunctionDef or a ClassDef node.
        Also analyze builtins calls and calls of function parameters.

        Parameters
        ----------
        call_reference : Reference
            The call reference which should be analyzed.
        function : FunctionScope
            The function in which the call is made.

        Returns
        -------
        ValueReference
            A ValueReference for the given call reference.
            This contains all referenced symbols for the call reference.
        """
        if not isinstance(call_reference, Reference):
            raise TypeError(f"call is not of type Reference, but of type {type(call_reference)}")

        result_value_reference = ValueReference(call_reference, function, [])

        # Find functions that are called.
        if call_reference.name in self.functions:
            function_def = self.functions.get(call_reference.name)
            function_symbols = [func.symbol for func in function_def if function_def]  # type: ignore[union-attr]
            # "None" is not iterable, but it is checked before
            class_iterator = function.symbol.node
            klass = None
            while class_iterator:
                if isinstance(class_iterator, astroid.ClassDef):
                    klass = self.classes.get(class_iterator.name)
                    break
                class_iterator = class_iterator.parent

            if klass and klass.super_classes:
                res = []
                for sup in klass.super_classes:
                    for func in sup.class_variables.values():
                        for f in func:
                            if f.name == call_reference.name:
                                res.append(f)

                result_value_reference.referenced_symbols.extend(res)
            else:
                result_value_reference.referenced_symbols.extend(function_symbols)

        # Find classes that are called (initialized).
        elif call_reference.name in self.classes:
            class_def = self.classes.get(call_reference.name)
            if class_def:
                result_value_reference.referenced_symbols.append(class_def.symbol)

        # Find builtins that are called, this includes open-like functions.
        # Because the parameters of the call node are relevant for the analysis, they are added to the (Builtin) Symbol.
        if call_reference.name in _BUILTINS or call_reference.name in (
            "open",
            "read",
            "readline",
            "readlines",
            "write",
            "writelines",
            "close",
        ):
            # Construct an artificial FunctionDef node for the builtin function.
            builtin_function = astroid.FunctionDef(
                name=(
                    (
                        call_reference.node.func.attrname
                        if isinstance(call_reference.node.func, astroid.Attribute)
                        else call_reference.node.func.name
                    )
                    if isinstance(call_reference.node.func, astroid.Attribute | astroid.Name)
                    else None
                ),
                lineno=call_reference.node.lineno,
                col_offset=call_reference.node.col_offset,
            )
            builtin_call = Builtin(
                node=builtin_function,
                id=NodeID("BUILTIN", call_reference.name),
                name=call_reference.name,
                call=call_reference.node,
            )
            if call_reference.name in ("open", "read", "readline", "readlines", "write", "writelines", "close"):
                builtin_call = BuiltinOpen(
                    node=builtin_function,
                    id=NodeID("BUILTIN", call_reference.name),
                    name=call_reference.name,
                    call=call_reference.node,
                )
            result_value_reference.referenced_symbols.append(builtin_call)

        # Find function parameters that are called (passed as arguments), like:
        # def f(a):
        #     a()
        # It is not possible to analyze this any further before runtime, so they will later be marked as unknown.
        if call_reference.name in function.parameters:
            param = function.parameters[call_reference.name]
            result_value_reference.referenced_symbols.append(param)

        # Find imported functions or classes that are called for ImportFrom nodes.
        if call_reference.name in self.imports:
            import_def = self.imports.get(call_reference.name)
            inferred_node_def = safe_infer(call_reference.node.func)
            if not inferred_node_def:
                with contextlib.suppress(astroid.InferenceError):
                    inferred_node_def = next(call_reference.node.func.infer())
            if not isinstance(inferred_node_def, astroid.FunctionDef | astroid.ClassDef):
                # These cases will be added to the unknown calls since they do not have any referenced_symbols.
                pass
            else:
                specified_import_def = dataclasses.replace(
                    import_def,  # type: ignore[type-var] # import def is not None.
                    inferred_node=inferred_node_def,
                    call=call_reference.node,
                )
                if specified_import_def:
                    result_value_reference.referenced_symbols.append(specified_import_def)

        return result_value_reference

    def _find_value_references(self,
                               value_reference: Reference,
                               function: FunctionScope,
                               ) -> ValueReference:
        """Find all references for a value node.

        This functions finds all referenced Symbols for a value reference.
        A reference for a value node can be a GlobalVariable, a LocalVariable,
        a Parameter, a ClassVariable or an InstanceVariable.
        It Also deals with the case where a class or a function is used as a value.

        Parameters
        ----------
        value_reference : Reference
            The value reference which should be analyzed.
        function : FunctionScope
            The function in which the value is used.

        Returns
        -------
        ValueReference
            A ValueReference for the given value reference.
            This contains all referenced symbols for the value reference.
        """
        if not isinstance(value_reference, Reference):
            raise TypeError(f"call is not of type Reference, but of type {type(value_reference)}")

        result_value_reference = ValueReference(value_reference, function, [])

        # Find local variables that are referenced.
        if value_reference.name in function.target_symbols and value_reference.name not in function.parameters:
            symbols = function.target_symbols[value_reference.name]
            # Check if all symbols are refined (refined means that they are of any subtyp of Symbol)
            if any(isinstance(symbol, Symbol) for symbol in symbols):
                # This currently is mostly the case for ClassVariables and InstanceVariables that are used as targets
                missing_refined = [symbol for symbol in symbols if type(symbol) is Symbol]

                # Because the missing refined symbols are added separately below,
                # remove the unrefined symbols from the list to avoid duplicates.
                symbols = list(set(symbols) - set(missing_refined))

                for symbol in missing_refined:
                    if isinstance(symbol.node, MemberAccessTarget):
                        for klass in self.classes.values():
                            if klass.class_variables:
                                if value_reference.node.member in klass.class_variables:
                                    symbols.append(
                                        ClassVariable(symbol.node, symbol.id, symbol.node.member, klass.symbol.node),
                                    )
                            if klass.instance_variables:
                                if value_reference.node.member in klass.instance_variables:
                                    symbols.append(
                                        InstanceVariable(symbol.node, symbol.id, symbol.node.member, klass.symbol.node),
                                    )

            # Only add symbols that are defined before the value is used.
            for symbol in symbols:
                if symbol.id.line is None or value_reference.id.line is None or symbol.id.line <= value_reference.id.line:
                    result_value_reference.referenced_symbols.append(symbol)

        # Find parameters that are referenced.
        if value_reference.name in function.parameters:
            local_symbols = [function.parameters[value_reference.name]]
            result_value_reference.referenced_symbols.extend(local_symbols)

        # Find global variables that are referenced.
        if value_reference.name in function.globals_used:
            global_symbols = function.globals_used[value_reference.name]  # type: ignore[assignment]
            # globals_used contains GlobalVariable instances, which are a subtype of Symbol.
            result_value_reference.referenced_symbols.extend(global_symbols)

        # Find functions that are referenced (as value).
        if value_reference.name in self.functions:
            function_def = self.functions.get(value_reference.name)
            if function_def:
                function_symbols = [func.symbol for func in function_def if function_def]
                result_value_reference.referenced_symbols.extend(function_symbols)

        # Find classes that are referenced (as value).
        if value_reference.name in self.classes:
            class_def = self.classes.get(value_reference.name)
            if class_def:
                result_value_reference.referenced_symbols.append(class_def.symbol)

        # Find imported modules that are referenced (as value) for Import.
        # Find symbols that are referenced for ImportFrom.
        if not isinstance(value_reference.node, MemberAccessValue) and value_reference.name in self.imports:
            import_def = self.imports.get(value_reference.name)
            inferred_node_def = safe_infer(value_reference.node)
            if not inferred_node_def:
                with contextlib.suppress(astroid.InferenceError):
                    inferred_node_def = next(value_reference.node.infer())
            if not inferred_node_def:
                pass
            else:
                specified_import_def = dataclasses.replace(
                    import_def,
                    inferred_node=inferred_node_def,  # type: ignore[type-var] # import def is not None.
                )
                if specified_import_def:
                    result_value_reference.referenced_symbols.append(specified_import_def)

        # Find class and instance variables that are referenced.
        if isinstance(value_reference.node, MemberAccessValue):
            for klass in self.classes.values():
                if klass.class_variables:
                    if (
                        value_reference.node.member in klass.class_variables
                        and value_reference.node.member not in function.call_references
                    ):
                        result_value_reference.referenced_symbols.extend(
                            klass.class_variables[value_reference.node.member])
                if klass.instance_variables:
                    if (
                        value_reference.node.member in klass.instance_variables
                        and value_reference.node.member not in function.call_references
                    ):
                        result_value_reference.referenced_symbols.extend(
                            klass.instance_variables[value_reference.node.member],
                        )

            # Find imported symbols that are referenced (as member of a MemberAccessValue).

            # Also deal with the case that the member is a call here, which at first is not intuitive
            # (not imported function calls, where the member is a call, are treated as calls).
            # On the other hand, dealing with imported calls as members when the references for function calls
            # are resolved is much more effort and would require to change the data structure.
            # Therefore, all calls of imported functions are handled as MemberAccessValue.
            # Because of this, a check at the point where the referenced_symbols are added to the raw_reasons is needed.
            if value_reference.node.receiver is None:
                receiver_name = "UNKNOWN"
            elif isinstance(value_reference.node.receiver, astroid.Attribute):
                receiver_name = value_reference.node.receiver.attrname
            elif (isinstance(value_reference.node.receiver, astroid.Call)
                  and isinstance(value_reference.node.receiver.func, astroid.Name)):
                receiver_name = value_reference.node.receiver.func.name
            else:
                receiver_name = value_reference.node.receiver.name

            if receiver_name in self.imports:
                # In references imported via "import" statements, the symbols of the imported module are not known yet.
                # The symbol is accessed via its name, which is of type MemberAccessValue.
                # At this point, only the receiver(=module name) is saved in the imports' dict.
                # This means that the symbol for the member needs to be inferred from the module and added to the list
                # of referenced symbols.
                import_def = self.imports.get(receiver_name)
                # TODO: we need a better way to make sure not all symbols are copied
                if import_def and value_reference.node.node is not None:
                    # Use astroid to infer the symbol of the member from the module.
                    inferred_node_def = safe_infer(
                        value_reference.node.node)  # TODO: what if node is a MemberAccessValue?
                    if not inferred_node_def:
                        with contextlib.suppress(astroid.InferenceError):
                            inferred_node_def = next(value_reference.node.node.infer())
                    if not inferred_node_def:
                        pass

                    else:
                        # Overcome the problem, that the import symbol object is the same for all possible functions and
                        # classes that are imported from one module.
                        # Therefore, copy the original import node and define a new one for one specific function or class.
                        # This means that every function or class imported from a module has its own import node.
                        specified_import_def = dataclasses.replace(
                            import_def,
                            name=value_reference.node.member,
                            inferred_node=inferred_node_def,
                        )

                        # If the member is a call, add the call node to the specified_import_def as fallback for the case
                        # that the purity of the called function cannot be inferred.
                        if isinstance(value_reference.node.node.parent, astroid.Call):
                            specified_import_def.call = value_reference.node.node.parent

                        result_value_reference.referenced_symbols.append(specified_import_def)

        return result_value_reference

    def _find_target_references(self,
                                target_reference: Symbol,
                                function: FunctionScope,
                                ) -> TargetReference:
        """Find all references for a target node.

        This functions finds all referenced Symbols for a target reference.
        TargetReferences occur whenever a Symbol is reassigned.
        A reference for a target node can be a GlobalVariable, a LocalVariable, a ClassVariable or an InstanceVariable.
        It Also deals with the case where a class is used as a target.

        Parameters
        ----------
        target_reference : Symbol
            The target reference which should be analyzed.
        function : FunctionScope
            The function in which the value is used.

        Returns
        -------
        TargetReference
            A TargetReference for the given target reference.
            This contains all referenced symbols for the value reference.
        """
        if not isinstance(target_reference, Symbol):
            raise TypeError(f"call is not of type Reference, but of type {type(target_reference)}")

        result_target_reference = TargetReference(target_reference, function, [])

        # Find local variables that are referenced.
        if target_reference.name in function.target_symbols:
            # Only check for symbols that are defined before the current target_reference.
            local_symbols = function.target_symbols[target_reference.name][
                            : function.target_symbols[target_reference.name].index(target_reference)
                            ]
            result_target_reference.referenced_symbols.extend(local_symbols)

        # Find global variables that are referenced.
        if target_reference.name in function.globals_used:
            global_symbols = function.globals_used[target_reference.name]
            result_target_reference.referenced_symbols.extend(global_symbols)

        # Find classes that are referenced (as value).
        if target_reference.name in self.classes:
            class_def = self.classes.get(target_reference.name)
            if class_def:
                result_target_reference.referenced_symbols.append(class_def.symbol)

        # Find class and instance variables that are referenced.
        if isinstance(target_reference.node, MemberAccessTarget):
            for klass in self.classes.values():
                if klass.class_variables:
                    if target_reference.node.member in klass.class_variables:
                        # Do not add class variables from other classes
                        if target_reference.node.receiver is not None:
                            if (
                                function.symbol.name == "__init__"
                                and function.parent != klass
                                or isinstance(target_reference.node.receiver, astroid.Name)
                                and target_reference.node.receiver.name == "self"
                                and function.parent != klass
                                or isinstance(target_reference.node.receiver, astroid.Attribute)
                                and target_reference.node.receiver.attrname == "self"
                                and function.parent != klass
                            ):
                                continue
                        # Do not add functions that are not of the current class (or superclass).
                        if function.symbol.name not in klass.class_variables or not self.is_function_of_class(
                            function.symbol.node, klass,
                        ):
                            # Collect all functions of superclasses for the current klass instance.
                            super_functions = []
                            for sup in klass.super_classes:
                                for class_var_list in sup.class_variables.values():
                                    for var in class_var_list:
                                        if isinstance(var.node, astroid.FunctionDef):
                                            super_functions.append(var.node.name)

                            # Make an exception for global functions and functions of superclasses.
                            # Also check if the function was overwritten in the current class.
                            if (isinstance(function.symbol, GlobalVariable)
                                or function.symbol.name in super_functions
                                and function.symbol.name not in klass.class_variables
                            ):
                                pass
                            else:
                                continue

                        result_target_reference.referenced_symbols.extend(
                            klass.class_variables[target_reference.node.member],
                        )
                if klass.instance_variables:
                    if (
                        target_reference.node.member in klass.instance_variables
                        and target_reference.node != klass.instance_variables[target_reference.node.member][0].node
                    ):  # This excludes the case where the instance variable is assigned
                        result_target_reference.referenced_symbols.extend(
                            klass.instance_variables[target_reference.node.member],
                        )

            # Find imported symbols that are referenced (as member of a MemberAccessTarget).
            # Astroids safe_infer methode will get the value of the assignment in the MemberAccessTarget node.
            # However, it is possible to detect write to an imported symbol which should be enough to ensure impurity.
            receiver_name: str | None = None
            if isinstance(target_reference.node.receiver, astroid.Attribute):
                receiver_name = target_reference.node.receiver.attrname
            elif isinstance(target_reference.node.receiver, astroid.Name):
                receiver_name = target_reference.node.receiver.name

            if receiver_name is not None and receiver_name in self.imports:
                import_def = self.imports.get(receiver_name)
                if import_def:
                    specified_import_def = dataclasses.replace(import_def, name=target_reference.node.member)
                    result_target_reference.referenced_symbols.append(specified_import_def)

        return result_target_reference

    def _resolve_references(self) -> tuple[dict[str, list[ReferenceNode]], dict[NodeID, Reasons]]:
        """
        Resolve all references in a module.

        This function is the entry point for the reference resolving.
        It calls all other functions that are needed to resolve the references.
        First, get the module data for the given (module) code.
        Then call the functions to find all call, target and value references in the module.

        Returns
        -------
        tuple[dict[NodeID, list[ReferenceNode]], dict[NodeID, Reasons]]
            The resolved references and the raw reasons for the functions.
        """
        raw_reasons: dict[NodeID, Reasons] = {}
        call_references: dict[str, list[ReferenceNode]] = {}
        value_references: dict[str, list[ReferenceNode]] = {}
        target_references: dict[str, list[ReferenceNode]] = {}
        # The call_references value is a list because the analysis analyzes the functions by name,
        # therefor a call can reference more than one function.
        # In the future, it is possible to differentiate between calls with the same name.
        # This could be done by further specifying the call_references for a function (by analyzing the signature, etc.)
        # If it is analyzed with 100% certainty, it is possible to remove the list and use a single ValueReference.

        for function_list in self.functions.values():
            # iterate over all functions with the same name
            for function in function_list:
                # Collect the reasons while iterating over the functions, so there is no need to iterate over them again.
                raw_reasons[function.symbol.id] = Reasons(function.symbol.id, function)

                # Check if the function has call_references (References from a call to the function definition itself).
                if function.call_references:
                    for call_list in function.call_references.values():
                        for call_reference in call_list:
                            call_references_result: ReferenceNode
                            call_references_result = self._find_call_references(
                                call_reference,
                                function,
                            )

                            # If referenced symbols are found,
                            # add them to the list of symbols in the dict by the name of the node.
                            # If the name does not yet exist, create a new list with the reference.
                            if call_references_result.referenced_symbols:
                                call_references.setdefault(call_references_result.node.name, []).append(
                                    call_references_result,
                                )

                                # Add the referenced symbols to the calls of the raw_reasons dict for this function
                                for referenced_symbol in call_references_result.referenced_symbols:
                                    # if isinstance(
                                    #     referenced_symbol,
                                    #     GlobalVariable | ClassVariable | Builtin | BuiltinOpen | Import
                                    # ):
                                    if referenced_symbol not in raw_reasons[function.symbol.id].calls:
                                        raw_reasons[function.symbol.id].calls.add(referenced_symbol)
                            # If no referenced symbols are found, add the call to the list of unknown_calls
                            # of the raw_reasons dict for this function
                            elif call_references_result.node not in raw_reasons[function.symbol.id].unknown_calls:
                                raw_reasons[function.symbol.id].unknown_calls.add(call_references_result.node)

                # Check if the function has value_references (References from a value node to a target node).
                if function.value_references:
                    for value_list in function.value_references.values():
                        for value_reference in value_list:
                            value_reference_result: ReferenceNode
                            value_reference_result = self._find_value_references(
                                value_reference,
                                function,
                            )

                            # If referenced symbols are found,
                            # add them to the list of symbols in the dict by the name of the node.
                            # If the name does not yet exist, create a new list with the reference.
                            if value_reference_result.referenced_symbols:
                                value_references.setdefault(value_reference_result.node.name, []).append(
                                    value_reference_result,
                                )

                                # Add the referenced symbols to the reads_from of the raw_reasons dict for this function
                                for referenced_symbol in value_reference_result.referenced_symbols:
                                    if isinstance(referenced_symbol, GlobalVariable | ClassVariable | InstanceVariable):
                                        # Since classes and functions are defined as immutable
                                        # reading from them is not a reason for impurity.
                                        if isinstance(referenced_symbol.node, astroid.ClassDef | astroid.FunctionDef):
                                            continue
                                        # Add the referenced symbol to the list of symbols whom are read from.
                                        if referenced_symbol not in raw_reasons[function.symbol.id].reads_from:
                                            raw_reasons[function.symbol.id].reads_from.add(referenced_symbol)
                                    elif isinstance(referenced_symbol, Import):
                                        # Since calls of imported functions are treated within _find_value_references
                                        # as MemberAccessValue, they need to be added to the calls of the raw_reasons dict
                                        # instead of the reads_from.
                                        if isinstance(
                                            referenced_symbol.inferred_node,
                                            astroid.FunctionDef | astroid.ClassDef,
                                        ):
                                            if referenced_symbol not in raw_reasons[function.symbol.id].calls:
                                                raw_reasons[function.symbol.id].calls.add(referenced_symbol)
                                        else:  # noqa: PLR5501
                                            if referenced_symbol not in raw_reasons[function.symbol.id].reads_from:
                                                raw_reasons[function.symbol.id].reads_from.add(referenced_symbol)
                            # If no referenced symbols are found, add the call to the list of unknown_calls
                            # of the raw_reasons dict for this function
                            elif (value_reference_result.node not in raw_reasons[function.symbol.id].unknown_calls
                                  and isinstance(value_reference_result.node.node, astroid.Call)
                            ):
                                raw_reasons[function.symbol.id].unknown_calls.add(value_reference_result.node)

                # Check if the function has target_references (References from a target node to another target node).
                if function.target_symbols:
                    for target_list in function.target_symbols.values():
                        for target_reference in target_list:
                            target_reference_result: ReferenceNode
                            target_reference_result = self._find_target_references(
                                target_reference,
                                function,
                            )

                            # If referenced symbols are found,
                            # add them to the list of symbols in the dict by the name of the node.
                            # If the name does not yet exist, create a new list with the reference.
                            if target_reference_result.referenced_symbols:
                                target_references.setdefault(target_reference_result.node.name, []).append(
                                    target_reference_result,
                                )

                                # Add the referenced symbols to the writes_to of the raw_reasons dict for this function
                                for referenced_symbol in target_reference_result.referenced_symbols:
                                    if isinstance(
                                        referenced_symbol,
                                        GlobalVariable | ClassVariable | InstanceVariable | Import,
                                    ):
                                        # Since classes and functions are defined as immutable,
                                        # writing to them is not a reason for impurity.
                                        # Also, it is not common to do so anyway.
                                        if isinstance(referenced_symbol.node, astroid.ClassDef | astroid.FunctionDef):
                                            continue
                                        # Add the referenced symbol to the list of symbols whom are written to.
                                        if referenced_symbol not in raw_reasons[function.symbol.id].writes_to:
                                            raw_reasons[function.symbol.id].writes_to.add(referenced_symbol)

        name_references: dict[str, list[ReferenceNode]] = self.merge_dicts(value_references, target_references)
        resolved_references: dict[str, list[ReferenceNode]] = self.merge_dicts(call_references, name_references)

        return resolved_references, raw_reasons


def resolve_references(code: str,
                       module_name: str = "",
                       path: str | None = None,
                       package_data: PackageData | None = None,
                       ) -> ModuleAnalysisResult:
    """Resolve all references in a module.

    Parameters
    ----------
    code : str
        The code of the module.
    module_name : str
        The name of the module if any.
    path : str | None
        The path of the module if any.
    package_data : PackageData | None
        The module data of all modules the package.
        If provided, the references are resolved with the package data, else the module data is collected first.
        It is used for the inference of the purity between modules in the package.

    Returns
    -------
    ModuleAnalysisResult
        The result of the reference resolving.
    """
    return ReferenceResolver(code, module_name, path, package_data).module_analysis_result
