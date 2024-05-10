from __future__ import annotations

from pathlib import Path

import astroid

from library_analyzer.processing.api._file_filters import _is_test_file
from library_analyzer.processing.api.purity_analysis import get_module_data
from library_analyzer.processing.api.purity_analysis._resolve_references import resolve_references
from library_analyzer.processing.api.purity_analysis.model import (
    BUILTIN_FUNCTIONS,
    BUILTIN_SPECIALS,
    OPEN_MODES,
    APIPurity,
    Builtin,
    BuiltinOpen,
    CallGraphForest,
    CallGraphNode,
    CallOfParameter,
    CombinedCallGraphNode,
    FileRead,
    FileWrite,
    Import,
    ImportedCallGraphNode,
    Impure,
    ImpurityReason,
    NativeCall,
    NodeID,
    OpenMode,
    PackageData,
    Parameter,
    ParameterAccess,
    Pure,
    PurityResult,
    Reasons,
    Reference,
    StringLiteral,
    UnknownCall,
    UnknownClassInit,
    UnknownFunctionCall,
)


class PurityAnalyzer:
    """
    The PurityAnalyzer class.

    This class is used to analyze the purity of a given module.
    It uses the infer_purity function to determine the purity of the functions in a module.

    Attributes
    ----------
    module_id : NodeID
        The ID of the module to analyze.
    visited_nodes : set[NodeID]
        A set of all nodes that have been visited during the analysis.
    call_graph_forest : CallGraphForest
        The call graph forest of the module.
    current_purity_results : dict[NodeID, dict[NodeID, PurityResult]]
        The purity results of the functions in the module.
    separated_nodes : dict[NodeID, CallGraphNode]
        If the module has cycles, they will be found by the CallGraphBuilder and combined to a single node.
        Since these combined nodes are not part of the module but needed for the analysis,
        their purity results will be propagated to the original nodes during the analysis.
        This attribute stores the original nodes inside after the combined node was analyzed.
    cached_module_results : dict[NodeID, dict[NodeID, PurityResult]]
        The results of all previously analyzed modules.
        The key is the NodeID of the module,
        the value is a dictionary of the purity results of the functions in the module.
        After the analysis of the module, the results are saved in this dictionary.
        All imported modules are saved in this dictionary too for further runtime reduction.

    Parameters
    ----------
    code : str | None
        The source code of the module.
        If None is provided, the package data must be provided (or else an exception is raised).
    module_name : str
        The name of the module.
    path : str | None
        The path of the module.
    results : dict[NodeID, dict[NodeID, PurityResult]] | None
        The results of all previously analyzed modules.
        The key is the NodeID of the module,
        the value is a dictionary of the purity results of the functions in the module.
    package_data : PackageData | None
        The module data of all modules the package.
        If provided, the references are resolved with the package data, else the module data is collected first.
        It is used for the inference of the purity between modules in the package.
    """

    def __init__(
        self,
        code: str | None,
        module_name: str = "",
        path: str | None = None,
        results: dict[NodeID, dict[NodeID, PurityResult]] | None = None,
        package_data: PackageData | None = None,
    ) -> None:
        if code is None and not package_data:
            raise ValueError("The code and package data are None.")
        elif package_data:
            references = resolve_references(code, module_name, path, package_data)  # type: ignore[arg-type]  # code is not None, so the type is correct.
        else:
            references = resolve_references(code, module_name, path)  # type: ignore[arg-type]  # code is not None, so the type is correct.
        if references.call_graph_forest is None:
            raise ValueError("The call graph forest is empty.")

        self.module_id = references.module_id
        if self.module_id is None:
            raise ValueError("The module ID is None.")
        self.visited_nodes: set[NodeID] = set()
        self.call_graph_forest: CallGraphForest = references.call_graph_forest
        self.current_purity_results: dict[NodeID, dict[NodeID, PurityResult]] = {self.module_id: {}}
        self.separated_nodes: dict[NodeID, CallGraphNode] = {}
        self.cached_module_results: dict[NodeID, dict[NodeID, PurityResult]] = results if results else {}

        self._analyze_purity()

    @staticmethod
    def _handle_open_like_functions(call: astroid.Call) -> PurityResult:
        """Check open-like function for impurity.

        This includes functions like open, read, readline, readlines, write, writelines.

        Parameters
        ----------
        call: astrid.Call
            The call to check.

        Returns
        -------
        PurityResult
            The purity result of the function.

        """
        if not isinstance(call, astroid.Call):
            raise TypeError(f"Expected astroid.Call, got {call.__class__.__name__}") from None

        func_ref_node_func_name = call.func.attrname if isinstance(call.func, astroid.Attribute) else call.func.name

        # Check if the function is open
        if func_ref_node_func_name == "open":
            open_mode_str = "r"
            open_mode = None

            if not call.args:
                return Impure({FileRead(StringLiteral("UNKNOWN")), FileWrite(StringLiteral("UNKNOWN"))})

            # Check if a mode is set and if the value is a string literal
            if len(call.args) >= 2 and isinstance(call.args[1], astroid.Const):
                if call.args[1].value in OPEN_MODES:
                    open_mode_str = call.args[1].value
            # Exclude the case where the mode is a variable since it cannot be determined in this case,
            # therefore, set it to be the worst case (read and write).
            elif len(call.args) == 2 and not isinstance(call.args[1], astroid.Const):
                open_mode = OpenMode.READ_WRITE

            # Check if the file name is a variable or a string literal
            file_var = call.args[0].name if isinstance(call.args[0], astroid.Name) else None
            file_str = call.args[0].value if not file_var and hasattr(call.args[0], "value") else None

            # The file name is a variable
            if file_var:
                open_mode = open_mode or OPEN_MODES[open_mode_str]
                return Impure(
                    (
                        {FileRead(source=ParameterAccess(file_var))}
                        if open_mode is OpenMode.READ
                        else (
                            {FileWrite(source=ParameterAccess(file_var))}
                            if open_mode is OpenMode.WRITE
                            else {
                                FileRead(source=ParameterAccess(file_var)),
                                FileWrite(source=ParameterAccess(file_var)),
                            }
                        )
                    ),
                )

            # The file name is a string literal
            elif file_str:
                open_mode = OPEN_MODES[open_mode_str]
                return Impure(
                    (
                        {FileRead(StringLiteral(file_str))}
                        if open_mode is OpenMode.READ
                        else (
                            {FileWrite(StringLiteral(file_str))}
                            if open_mode is OpenMode.WRITE
                            else {FileRead(StringLiteral(file_str)), FileWrite(StringLiteral(file_str))}
                        )
                    ),
                )
            else:
                return Impure({FileRead(StringLiteral("UNKNOWN")), FileWrite(StringLiteral("UNKNOWN"))})
        else:
            return Pure()

    @staticmethod
    def _get_impurity_result(reasons: Reasons) -> PurityResult:
        """
        Get the reasons for impurity from the reasons.

        Given a Reasons object, this function transforms the collected reasons
        from a Reasons object to a set of ImpurityReason and returns a PurityResult.
        If any ImpurityReason is found in the reasons, the function returns an Impure result.
        If no ImpurityReason is found, the function returns a Pure result.
        If any unknown calls are found, the function returns an Unknown result.

        Parameters
        ----------
        reasons : Reasons
            The node to process containing the raw reasons for impurity collected.

        Returns
        -------
        PurityResult
            The impurity result of the function (Pure, Impure or Unknown).
        """
        impurity_reasons: set[ImpurityReason] = set()

        # If no reasons are found, the function is pure.
        if not reasons.reads_from and not reasons.writes_to and not reasons.unknown_calls:
            return Pure()

        # Check if the function has any non-local variable writes.
        if reasons.writes_to:
            for write in reasons.writes_to.values():
                impurity_reasons.add(write)

        # Check if the function has any non-local variable reads.
        if reasons.reads_from:
            for read in reasons.reads_from.values():
                # Check if the read reads from an imported module.
                if isinstance(read.symbol, Import):
                    if read.symbol.inferred_node:
                        # If the inferred node is a function, it must be analyzed to determine its purity.
                        if isinstance(read.symbol.inferred_node, astroid.FunctionDef):
                            impurity_reasons.add(
                                UnknownCall(
                                    UnknownFunctionCall(call=read.symbol.call, inferred_def=read.symbol.inferred_node),
                                ),
                            )
                        elif isinstance(read.symbol.inferred_node, astroid.ClassDef):
                            impurity_reasons.add(
                                UnknownCall(
                                    UnknownClassInit(call=read.symbol.call, inferred_def=read.symbol.inferred_node),
                                ),
                            )
                        # If the inferred node is a module, it will not count towards the impurity of the function.
                        # If this was added, nearly anything would be impure.
                        # Also, since the imported symbols are analyzed in much more detail, this can be omitted.
                        elif isinstance(read.symbol.inferred_node, astroid.Module):
                            pass
                        # Default case for symbols that could not be inferred.
                        else:  # TODO: what type of nodes are allowed here?
                            impurity_reasons.add(read)

                    else:
                        raise ValueError(f"Imported node {read.symbol.name} has no inferred node.") from None

                else:
                    impurity_reasons.add(read)

        # Check if the function has any unknown calls.
        if reasons.unknown_calls:
            for unknown_call in reasons.unknown_calls.values():
                # Handle calls of code where no definition was found.
                if isinstance(unknown_call.symbol, Reference):
                    # This checks special cases of unknown calls.
                    # These are cases where a function is not a true builtin, but also not a user-defined function.
                    # Cases like dict.pop(), list.remove(), set.union(), etc.
                    if unknown_call.symbol.name in BUILTIN_SPECIALS:
                        pass
                    else:
                        impurity_reasons.add(
                            UnknownCall(
                                expression=UnknownFunctionCall(call=unknown_call.symbol.node),
                                origin=unknown_call.origin,
                            ),
                        )
                # Handle parameter calls
                elif isinstance(unknown_call.symbol, Parameter):
                    impurity_reasons.add(
                        CallOfParameter(
                            expression=ParameterAccess(unknown_call.symbol),
                            origin=unknown_call.origin,
                        ),
                    )
                # Do not handle imported calls here since they are handled separately.
                elif isinstance(unknown_call, Import):
                    pass

        if impurity_reasons:
            return Impure(impurity_reasons)
        return Pure()

    def _process_imported_node(self, imported_node: ImportedCallGraphNode) -> PurityResult:
        """Process an imported node.

        Since imported nodes are not part of the module, they need to be analyzed separately.
        Therefore, the inferred node of the imported node is analyzed to determine its purity.
        If the module can be determined, a purity analysis is run on the imported module.
        If the module cannot be determined,
        or the function def is not found inside the module, the function is impure.
        Since it is possible that a module is used more than once,
        the results are cached after the first time analyzing the module.

        Parameters
        ----------
        imported_node : ImportedCallGraphNode
            The imported node to process.

        Returns
        -------
        PurityResult
            The purity result of the imported node.
        """
        # Check if the reference was resolved and the symbol has an inferred node.
        if imported_node.symbol.inferred_node is None:
            return Impure(
                {
                    UnknownCall(
                        expression=UnknownFunctionCall(call=imported_node.symbol.call),
                        origin=imported_node.symbol,
                    ),
                },
            )

        imported_module = imported_node.symbol.inferred_node.root()
        # Some imported modules are not written in python. Their purity cannot be analyzed.
        if not imported_module.path:
            return Impure(
                {
                    NativeCall(
                        expression=UnknownFunctionCall(
                            call=imported_node.symbol.call,
                            inferred_def=(
                                imported_node.symbol.inferred_node
                                if isinstance(imported_node.symbol.inferred_node, astroid.FunctionDef)
                                else None
                            ),
                        ),
                        origin=imported_node.symbol,
                    ),
                },
            )
        # Check if the imported module is actually a module.
        if not isinstance(imported_module, astroid.Module):
            return Impure(
                {
                    UnknownCall(
                        expression=UnknownFunctionCall(call=imported_node.symbol.call),
                        origin=imported_node.symbol,
                    ),
                },
            )

        # Calculate the ID of the imported module.
        imported_module_id = NodeID.calc_node_id(imported_module)
        inferred_node_id = NodeID.calc_node_id(imported_node.symbol.inferred_node)

        # Check if the imported module has already been analyzed.
        # Check if the purity result for the inferred node is available in the cache.
        if (
            imported_module_id in self.cached_module_results
            and inferred_node_id in self.cached_module_results[imported_module_id]
        ):
            return self.cached_module_results[imported_module_id].get(inferred_node_id)  # type: ignore[return-value]

        # Check if the imported module is currently being analyzed to prevent recursion.
        elif (
            imported_module_id in self.cached_module_results
            and inferred_node_id not in self.cached_module_results[imported_module_id]
        ):
            # The module is being analyzed, return an impure result to break the recursion.
            return Impure(
                {
                    UnknownCall(
                        expression=UnknownFunctionCall(call=imported_node.symbol.call),
                        origin=imported_node.symbol,
                    ),
                },
            )

        # Mark the imported module as being analyzed.
        elif imported_module_id not in self.cached_module_results:
            self.cached_module_results.update({imported_module_id: {}})

        # Get the source code of the imported module.
        with imported_module.stream() as s:
            source_code = s.read()
            s.close()
        try:
            source_code = source_code.decode("utf-8")
        except UnicodeDecodeError:
            return Impure(
                {
                    UnknownCall(
                        expression=UnknownFunctionCall(call=imported_node.symbol.call),
                        origin=imported_node.symbol,
                    ),
                },
            )

        # Analyze the purity of the imported module.
        purity_result_imported_module = infer_purity(
            code=source_code,
            module_name=imported_module.name,
            path=imported_module.path[0],
            results=self.cached_module_results,
        )

        # Update the cache with the purity results of the imported module.
        self.cached_module_results.update(purity_result_imported_module)

        # Check if the purity result for the inferred node is available in the cache.
        if inferred_node_id in self.cached_module_results[imported_module_id]:
            return self.cached_module_results[imported_module_id].get(inferred_node_id)  # type: ignore[return-value]
        # If the inferred_node cannot be found in the result, return an unknown call.
        else:
            if isinstance(imported_node.symbol.inferred_node, astroid.ClassDef):
                return Impure(
                    {
                        UnknownCall(
                            expression=UnknownClassInit(
                                call=imported_node.symbol.call,
                                inferred_def=imported_node.symbol.inferred_node,
                            ),
                            origin=imported_node.symbol,
                        ),
                    },
                )
            return Impure(
                {
                    UnknownCall(
                        expression=UnknownFunctionCall(
                            call=imported_node.symbol.call,
                            inferred_def=(
                                imported_node.symbol.inferred_node if imported_node.symbol.inferred_node else None
                            ),
                        ),
                        origin=imported_node.symbol,
                    ),
                },
            )

    def _process_node(self, node: CallGraphNode) -> PurityResult:
        """Process a node in the call graph.

        Process a node in the call graph to determine the purity of the function.
        Therefore, recursively process the children of the node (if any) and propagate the results afterward.
        First check if the purity of the function is already determined.
        Works with builtin functions and combined function nodes.

        Parameters
        ----------
        node : CallGraphNode
            The node to process.

        Returns
        -------
        PurityResult
            The purity result of the function node (combined with the results of its children).
        """
        # Check the forest if the purity of the function is already determined
        if node.is_inferred():
            # The purity of the function is determined already.
            return node.reasons.result  # type: ignore[return-value] # It is checked before that the result is not None.
        elif (
            self.module_id in self.cached_module_results
            and node.symbol.id in self.cached_module_results[self.module_id]
        ):
            return self.cached_module_results[self.module_id].get(node.symbol.id)  # type: ignore[return-value]
        elif node.symbol.id in self.visited_nodes and not isinstance(node.symbol, Builtin | BuiltinOpen):
            return Impure(
                {UnknownCall(expression=UnknownFunctionCall(), origin=node.symbol)},
            )  # TODO: find better return value

        self.visited_nodes.add(node.symbol.id)

        # Check if the node is a builtin function.
        if isinstance(node.symbol, Builtin | BuiltinOpen):
            if isinstance(node.symbol, BuiltinOpen):
                result = self._handle_open_like_functions(node.symbol.call)
            elif node.symbol.name in BUILTIN_FUNCTIONS:
                result = BUILTIN_FUNCTIONS[node.symbol.name]
            else:
                result = Impure({UnknownCall(UnknownFunctionCall(call=node.symbol.call))})
            # Add the origin to the reasons if it is not set yet.
            # Also add the caller of a builtin function to the origin (for better traceability).
            if isinstance(result, Impure):
                for reason in result.reasons:
                    if hasattr(reason, "origin") and reason.origin is None:
                        caller = None
                        parent = node.symbol.call.parent
                        while not caller:
                            if parent is None:
                                break
                            if isinstance(parent, astroid.FunctionDef):
                                caller = parent
                            else:
                                parent = parent.parent

                        reason.origin = node.symbol
                        if caller:
                            reason.origin.id.name = reason.origin.id.name + " @ " + str(NodeID.calc_node_id(caller))
            return result

        # The purity of the node is not determined yet, but the node has children.
        # Check their purity first and propagate the results afterward.
        if not node.is_leaf():
            purity_result_children: PurityResult = Pure()
            for child in node.children.values():
                # Check imported nodes separately.
                if isinstance(child, ImportedCallGraphNode):
                    purity_result_child = self._process_imported_node(child)
                # Check combined nodes separately.
                elif isinstance(child, CombinedCallGraphNode):
                    purity_result_child = self._process_node(child)
                    self.separated_nodes.update(child.separate())
                else:
                    purity_result_child = self._process_node(child)
                # Combine the reasons of all children.
                purity_result_children = purity_result_children.update(purity_result_child)

            node.reasons.result = self._get_impurity_result(node.reasons)
            node.reasons.result = node.reasons.result.update(purity_result_children)

        # The purity of the node is not determined yet, and it has no children.
        # Therefore, it is possible to check its (reasons for) impurity directly.
        # TODO: what about combined nodes here? Add testcase for that!
        else:
            node.reasons.result = self._get_impurity_result(node.reasons)

        return node.reasons.result

    def _analyze_purity(self) -> None:
        """
        Analyze the purity of the module.

        While traversing the forest, it saves the purity results in the purity_results attribute.
        """
        # Check if the module was already analyzed and the results are cached.
        # if self.module_id in self.cached_module_results:
        #     self.current_purity_results[self.module_id] = self.cached_module_results[self.module_id]
        #     return

        # The purity of the module is not determined yet, so all graphs in the forest need to be analyzed.
        for graph in self.call_graph_forest.graphs.values():
            if isinstance(graph, CombinedCallGraphNode):
                self._process_node(graph)
                self.separated_nodes.update(graph.separate())
            elif isinstance(graph, ImportedCallGraphNode):
                pass
            elif isinstance(graph, CallGraphNode):
                purity_result = self._process_node(graph)
                if isinstance(graph.symbol.node, astroid.ClassDef):
                    purity_result.is_class = True

                self.current_purity_results[self.module_id].update({graph.symbol.id: purity_result})  # type: ignore[index] # self.module_id is never None here, since an exception is raised before.

        if self.separated_nodes:
            for func_id, graph in self.separated_nodes.items():
                if graph.reasons.result is None:
                    raise ValueError(f"The purity of the combined node {func_id} is not inferred.")
                self.current_purity_results[self.module_id].update({func_id: graph.reasons.result})  # type: ignore[index] # self.module_id is never None here, since an exception is raised before.


def infer_purity(
    code: str | None,
    module_name: str = "",
    path: str | None = None,
    results: dict[NodeID, dict[NodeID, PurityResult]] | None = None,
    package_data: PackageData | None = None,
) -> dict[NodeID, dict[NodeID, PurityResult]]:
    """
    Infer the purity of functions.

    Given the code of a module, this function infers the purity of the functions inside a module.
    It uses the PurityAnalyzer to determine the purity of the functions in a module.

    Parameters
    ----------
    code : str | None
        The source code of the module.
        If None is provided, the package data must be provided (or else an exception is raised).
    module_name : str, optional
        The name of the module, by default "".
    path : str, optional
        The path of the module, by default None.
    results : dict[NodeID, dict[NodeID, PurityResult]] | None
        The results of all previously analyzed modules.
        The key is the NodeID of the module, the value is a dictionary of the purity results of the functions in the module.
        After the analysis of the module, the results are saved in this dictionary.
        All imported modules are saved in this dictionary too for further runtime reduction.
        Is None if no results are available.
    package_data : PackageData | None
        The module data of all modules the package.
        If provided, the references are resolved with the package data, else the module data is collected first.
        It is used for the inference of the purity between modules in the package.

    Returns
    -------
    purity_results : dict[NodeID, dict[NodeID, PurityResult]]
        The purity results of the functions in the module.
        The key is the NodeID of the module, the value is a dictionary of the purity results of the functions in the module.
    """
    purity_analyzer = PurityAnalyzer(code, module_name, path, results, package_data)
    return purity_analyzer.current_purity_results


def get_purity_results(
    src_dir_path: Path,
) -> APIPurity:
    """Get the purity results of a package.

    This function is the entry to the purity analysis of a package.
    It iterates over all modules in the package and infers the purity of the functions in the modules.

    Parameters
    ----------
    src_dir_path : Path
        The path of the source directory of the package.

    Returns
    -------
    APIPurity
        The purity results of the package.
    """
    modules = list(src_dir_path.glob("**/*.py"))
    module_names: list[str] = []
    package_purity = APIPurity()
    package_data = PackageData(src_dir_path.stem)

    for module in modules:
        posix_path = Path(module).as_posix()

        if _is_test_file(posix_path):
            continue

        module_name = __module_name(src_dir_path, Path(module))
        module_names.append(module_name)
        # Prepare the module data for all modules of the package.
        with module.open("r", encoding="utf-8") as file:
            code = file.read()
            package_data.modules.update({module_name: (posix_path, get_module_data(code, module_name, posix_path))})

    # Analyze the complete package.
    package_data.combine_modules()
    package_purity_results = infer_purity(code=None, results=package_purity.purity_results, package_data=package_data)

    # Group the results by file name.
    sorted_module_purity_results: dict[NodeID, dict[NodeID, PurityResult]] = {}
    for values in package_purity_results.values():
        for k, v in values.items():
            sorted_module_purity_results.setdefault(
                NodeID(None, "UNKNOWN" if k.module is None else k.module),
                {},
            ).update({k: v})

    # Add back empty files.
    for mod in module_names:
        if NodeID(None, mod) not in sorted_module_purity_results:
            sorted_module_purity_results[NodeID(None, mod)] = {}

    # Sort the functions by line number to make the results more readable.
    sorted_module_purity_results = {
        key: dict(
            sorted(
                value.items(),
                key=lambda item: item[0].line if item[0] is not None and item[0].line is not None else float("inf"),
            ),
        )
        for key, value in sorted_module_purity_results.items()
    }

    package_purity.purity_results.update(sorted_module_purity_results)

    # Clean the purity results by removing all modules that are not part of the package.
    for module_id in package_purity.purity_results.copy():
        if module_id.name not in module_names:
            package_purity.purity_results.pop(module_id)

    return package_purity


def __module_name(root: Path, file: Path) -> str:
    relative_path = file.relative_to(root.parent).as_posix()
    return str(relative_path).replace(".py", "").replace("/", ".")
