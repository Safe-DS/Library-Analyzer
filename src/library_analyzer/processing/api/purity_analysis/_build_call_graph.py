from library_analyzer.processing.api.purity_analysis import calc_node_id
from library_analyzer.processing.api.purity_analysis.model import (
    Builtin,
    CallGraphForest,
    ClassScope,
    CombinedCallGraphNode,
    CombinedSymbol,
    Import,
    ImportedCallGraphNode,
    NewCallGraphNode,
    NodeID,
    Parameter,
    Reasons,
    Symbol,
)

# BUILTINS = dir(builtins)
#
#
# def build_call_graph(
#     functions: dict[str, list[FunctionScope]],
#     classes: dict[str, ClassScope],
#     raw_reasons: dict[NodeID, Reasons],
# ) -> CallGraphForest:
#     """Build a call graph from a list of functions.
#
#     This function builds a CallGraphForest from a list of functions.
#     The root nodes of the trees are the functions that are called first.
#
#     Parameters
#     ----------
#     functions : dict[str, list[FunctionScope]]
#         All functions and a list of their FunctionScopes.
#         The value is a list since there can be multiple functions with the same name.
#     classes : dict[str, ClassScope]
#         Classnames in the module as key and their corresponding ClassScope instance as value.
#     raw_reasons : dict[str, Reasons]
#         The reasons for impurity of the functions.
#
#     Returns
#     -------
#     call_graph_forest : CallGraphForest
#         The call graph forest for the given functions.
#     """
#     call_graph_forest = CallGraphForest()
#     classes_and_functions: dict[str, list[FunctionScope] | ClassScope] = {**classes, **functions}
#
#     for function_scopes in classes_and_functions.values():
#         # Inner for loop is needed to handle multiple function defs with the same name.
#         for scope in function_scopes:
#             if not isinstance(scope, FunctionScope | ClassScope):
#                 raise TypeError(f"Scope {scope} is not of type FunctionScope or ClassScope") from None
#             # Add reasons for impurity to the corresponding function.
#             function_id = scope.symbol.id
#             if isinstance(scope, ClassScope):
#                 current_call_graph_node = CallGraphNode(scope=scope, reasons=Reasons(scope.symbol.id))
#             elif raw_reasons[function_id]:
#                 current_call_graph_node = CallGraphNode(scope=scope, reasons=raw_reasons[function_id])
#             else:
#                 raise ValueError(f"No reasons found for function {scope.symbol.name}")
#
#             # Case where the function is not called before by any other function.
#             if function_id not in call_graph_forest.forest:
#                 call_graph_forest.add_graph(
#                     function_id,
#                     current_call_graph_node,
#                 )  # Save the tree in the forest by the name of the root function.
#
#             # When dealing with a class, the init function needs to be added to the call graph manually (if it exists).
#             if isinstance(scope, ClassScope):
#                 for fun in functions.get("__init__", []):
#                     if fun.parent == scope:
#                         init_function = fun
#                         if init_function.symbol.id not in call_graph_forest.forest:
#                             call_graph_forest.add_graph(
#                                 init_function.symbol.id,
#                                 CallGraphNode(scope=init_function, reasons=Reasons(init_function.symbol.id)),
#                             )
#                         current_call_graph_node.add_child(call_graph_forest.get_graph(init_function.symbol.id))
#                         current_call_graph_node.reasons.calls.add(
#                             Symbol(
#                                 node=raw_reasons[init_function.symbol.id].function_scope.symbol.node,
#                                 # type: ignore[union-attr]
#                                 # function_scope is always of type FunctionScope here since it is the init function.
#                                 id=init_function.symbol.id,
#                                 name=init_function.symbol.name,
#                             ),
#                         )
#                         break
#                 continue
#
#             # Default case where a function calls no other functions in its body - therefore, the tree has just one node
#             if not isinstance(scope, FunctionScope) or not scope.call_references:
#                 continue
#
#             # If the function calls other functions in its body, a tree is built for each call.
#             else:
#                 for call_name, call_ref in scope.call_references.items():
#                     # Take the first call to represent all calls of the same name.
#                     # This does not vary the result and is faster.
#                     call = call_ref[0]
#
#                     # Handle self defined function calls
#                     if call_name in classes_and_functions:
#                         # Check if any function def has the same name as the called function
#                         matching_function_defs = [
#                             called_fun
#                             for called_fun in classes_and_functions[call.name]
#                             if called_fun.symbol.name == call.name
#                         ]
#                         current_tree_node = call_graph_forest.get_graph(function_id)
#                         break_condition = False  # This is used to indicate that one or more functions defs was
#                         # found inside the forest that matches the called function name.
#
#                         # Check if the called function is already in the tree.
#                         for f in matching_function_defs:
#                             if call_graph_forest.has_graph(f.symbol.id):
#                                 current_tree_node.add_child(call_graph_forest.get_graph(f.symbol.id))
#                                 break_condition = True  # A function def inside the forest was found
#                                 # so the following else statement must not be executed.
#
#                         if break_condition:
#                             pass  # Skip the else statement because the function def is already in the forest.
#
#                         # If the called function is not in the forest,
#                         # compute it first and then connect it to the current tree
#                         else:
#                             for called_function_scope in classes_and_functions[call_name]:
#                                 # Check if any function def has the same name as the called function
#                                 for f in matching_function_defs:
#                                     if raw_reasons[f.symbol.id]:
#                                         call_graph_forest.add_graph(
#                                             f.symbol.id,
#                                             CallGraphNode(
#                                                 scope=called_function_scope,  # type: ignore[arg-type]
#                                                 # Mypy does not recognize that function_scope is of type FunctionScope
#                                                 # or ClassScope here even it is.
#                                                 reasons=raw_reasons[f.symbol.id],
#                                             ),
#                                         )
#                                     else:
#                                         call_graph_forest.add_graph(
#                                             f.symbol.id,
#                                             CallGraphNode(scope=called_function_scope, reasons=Reasons()),
#                                             # type: ignore[arg-type]
#                                             # Mypy does not recognize that function_scope is of type FunctionScope or
#                                             # ClassScope here even it is.
#                                         )
#                                     current_tree_node.add_child(call_graph_forest.get_graph(f.symbol.id))
#
#                     # Handle builtins: builtins are not in the functions dict,
#                     # and therefore need to be handled separately.
#                     # Since builtins are not analyzed any further at this stage,
#                     # they can simply be added as a child to the current tree node.
#                     elif call.name in BUILTINS or call.name in (
#                         "open",
#                         "read",
#                         "readline",
#                         "readlines",
#                         "write",
#                         "writelines",
#                         "close",
#                     ):
#                         current_tree_node = call_graph_forest.get_graph(function_id)
#                         # Build an artificial FunctionScope node for calls of builtins, since the rest of the analysis
#                         # relies on the function being a FunctionScope instance.
#                         builtin_function = astroid.FunctionDef(
#                             name=call.name,
#                             lineno=call.node.lineno,
#                             col_offset=call.node.col_offset,
#                         )
#                         builtin_symbol = Builtin(
#                             node=builtin_function,
#                             id=NodeID(None, call.name),
#                             name=call.name,
#                         )
#                         if call.name in ("open", "read", "readline", "readlines", "write", "writelines", "close"):
#                             builtin_symbol = BuiltinOpen(
#                                 node=builtin_function,
#                                 id=call.id,
#                                 name=call.name,
#                                 call=call.node,
#                             )
#                         builtin_scope = FunctionScope(builtin_symbol)
#
#                         current_tree_node.add_child(
#                             CallGraphNode(scope=builtin_scope, reasons=Reasons(builtin_scope.symbol.id),
#                                           is_builtin=True),
#                         )
#
#                     # Deal with unknown calls:
#                     # - calls of unknown code => call node not in functions dict
#                     # - calls of external code => call node not in function_reference dict
#                     # - calls of parameters # TODO: parameter calls are not handled yet
#                     # These functions get an unknown flag
#                     else:
#                         current_tree_node = call_graph_forest.get_graph(function_id)
#                         if isinstance(current_tree_node.reasons, Reasons):
#                             current_tree_node.reasons.unknown_calls.add(call.node)
#
#     handle_cycles(call_graph_forest, raw_reasons, functions)
#
#     return call_graph_forest
#
#
# def handle_cycles(
#     call_graph_forest: CallGraphForest,
#     function_references: dict[NodeID, Reasons],
#     functions: dict[str, list[FunctionScope]],
# ) -> CallGraphForest:
#     """Handle cycles in the call graph.
#
#     This function checks for cycles in the call graph forest and contracts them into a single node.
#
#     Parameters
#     ----------
#     call_graph_forest : CallGraphForest
#         The call graph forest of the functions.
#     function_references : dict[str, Reasons]
#         All nodes relevant for reference resolving inside functions.
#     functions : dict[str, list[FunctionScope]]
#         All functions and a list of their FunctionScopes.
#         The value is a list since there can be multiple functions with the same name.
#         It Is not needed in this function especially, but is needed for the contract_cycle function.
#
#     Returns
#     -------
#     call_graph_forest : CallGraphForest
#         The call graph forest with contracted cycles.
#     """
#     for graph in call_graph_forest.forest.copy().values():
#         visited_nodes: set[CallGraphNode] = set()
#         path: list[CallGraphNode] = []
#         cycle = test_for_cycles(graph, visited_nodes, path)
#         if cycle:
#             # print("cycle found", cycle)
#             contract_cycle(call_graph_forest, cycle, function_references, functions)
#             # TODO: check if other cycles exists
#         else:
#             # print("no cycles found")
#             pass
#     return call_graph_forest
#
#
# def test_for_cycles(
#     graph: CallGraphNode,
#     visited_nodes: set[CallGraphNode],
#     path: list[CallGraphNode],
# ) -> list[CallGraphNode]:
#     """Tests for cycles in the call graph.
#
#     This function recursively traverses the call graph and checks for cycles.
#     It uses a DFS approach to traverse the graph.
#     If a cycle is found, the cycle is returned.
#     It is possible that multiple cycles exist, but only one is returned.
#
#     Parameters
#     ----------
#     graph : CallGraphNode
#         The current node in the graph that is visited.
#     visited_nodes : set[CallGraphNode]
#         A set of all visited nodes.
#     path : list[CallGraphNode]
#         A list of all nodes in the current path.
#
#     Returns
#     -------
#     cycle : list[CallGraphNode]
#         A list of all nodes in the cycle.
#         If no cycle is found, an empty list is returned.
#     """
#     # If a node has no children, it is a leaf node, and an empty list is returned.
#     if not graph.children:
#         return []
#
#     if graph in path:
#         return path[path.index(graph):]  # A cycle is found, return the path containing the cycle.
#
#     # Mark the current node as visited.
#     visited_nodes.add(graph)
#     path.append(graph)
#
#     cycle = []
#
#     # Check for cycles in children.
#     for child in graph.children:
#         cycle = test_for_cycles(child, visited_nodes, path)
#         if cycle:
#             return cycle
#     path.pop()  # Remove the current node from the path when backtracking.
#
#     return cycle
#
#
# # TODO: add cycle detection for FunctionScope instances
# def contract_cycle(
#     forest: CallGraphForest,
#     cycle: list[CallGraphNode],
#     raw_reasons: dict[NodeID, Reasons],
#     functions: dict[str, list[FunctionScope]],
# ) -> None:
#     """Contracts a cycle in the call graph.
#
#     Given a cycle in the call graph, this function contracts the cycle into a single node.
#
#     Parameters
#     ----------
#     forest : CallGraphForest
#         The call graph forest of the functions.
#     cycle : list[CallGraphNode]
#         All nodes in the cycle.
#     raw_reasons : dict
#         All nodes relevant for reference resolving inside functions.
#     functions : dict[str, list[FunctionScope]]
#         All functions and a list of their FunctionScopes.
#         The value is a list since there can be multiple functions with the same name.
#         It Is not needed in this function especially, but is needed for the contract_cycle function.
#     """
#     # Create the new combined node
#     cycle_ids = [node.scope.symbol.id for node in cycle]
#     cycle_id_strs = [node.scope.symbol.id.__str__() for node in cycle]
#     cycle_names = [node.scope.symbol.name for node in cycle]
#     combined_node_name = "+".join(sorted(cycle_id_strs))
#     combined_node_data = FunctionScope(
#         Symbol(
#             None,
#             NodeID(None, combined_node_name),
#             combined_node_name,
#         ),
#     )
#     combined_reasons = Reasons(id=NodeID(None, combined_node_name),
#                                function_scope=combined_node_data).join_reasons_list([node.reasons for node in cycle])
#     combined_node = CallGraphNode(
#         scope=combined_node_data,
#         reasons=combined_reasons,
#         combined_node_ids=cycle_ids,
#     )
#
#     # Add children to the combined node if they are not in the cycle (other calls).
#     if any(isinstance(node.scope, FunctionScope) and hasattr(node.scope, "call_references") for node in cycle):
#         other_calls: dict[str, list[Reference]] = {
#             call[0].name: [call[0]]
#             for node in cycle
#             for call_name, call in node.scope.call_references.items()
#             # type: ignore[union-attr] # Mypy does not recognize that function_scope is of type FunctionScope here even it is.
#             if isinstance(node.scope, FunctionScope)
#                and call_name not in cycle_names
#                and call_name not in BUILTINS
#                or call[0].name in ("read", "readline", "readlines", "write", "writelines")
#         }
#         # Find all function definitions that match the other call names for each call.
#         matching_function_defs = {}
#         for call_name in other_calls:
#             matching_function_defs[call_name] = [
#                 called_function for called_function in functions[call_name] if called_function.symbol.name == call_name
#             ]
#
#         # Find all builtin calls.
#         builtin_calls: dict[str, list[Reference]] = {
#             call[0].name: [call[0]]
#             for node in cycle
#             for call in node.scope.call_references.values()  # type: ignore[union-attr]
#             if isinstance(node.scope, FunctionScope)
#                and call[0].name in BUILTINS
#                or call[0].name in ("read", "readline", "readlines", "write", "writelines")
#         }
#
#         builtin_call_functions: list[FunctionScope] = []
#         for call_node in builtin_calls.values():
#             # Build an artificial FunctionScope node for calls of builtins, since the rest of the analysis
#             # relies on the function being a FunctionScope instance.
#             builtin_function = astroid.FunctionDef(
#                 name=call_node[0].name,
#                 lineno=call_node[0].node.lineno,
#                 col_offset=call_node[0].node.col_offset,
#             )
#
#             builtin_symbol = Builtin(
#                 node=builtin_function,
#                 id=call_node[0].id,
#                 name=call_node[0].name,
#             )
#             if call_node[0].name in ("read", "readline", "readlines", "write", "writelines"):
#                 builtin_symbol = BuiltinOpen(
#                     node=builtin_function,
#                     id=call_node[0].id,
#                     name=call_node[0].name,
#                     call=call_node[0].node,
#                 )
#             builtin_scope = FunctionScope(builtin_symbol)
#             builtin_call_functions.append(builtin_scope)
#
#         # Add the calls as well as the children of the function defs to the combined node.
#         combined_node_data.call_references.update(other_calls)
#         combined_node_data.call_references.update(builtin_calls)
#         combined_node.children = {
#             CallGraphNode(
#                 scope=matching_function_defs[call[0].name][i],
#                 reasons=raw_reasons[matching_function_defs[call[0].name][i].symbol.id],
#             )
#             for call in other_calls.values()
#             for i in range(len(matching_function_defs[call[0].name]))
#         }  # Add the function def (list of function defs) as children to the combined node
#         # if the function def name matches the call name.
#         combined_node.children.update({
#             CallGraphNode(scope=builtin_call_function, reasons=Reasons(builtin_call_function.symbol.id),
#                           is_builtin=True)
#             for builtin_call_function in builtin_call_functions
#         })
#
#     # Remove all nodes in the cycle from the forest and add the combined node instead.
#     for node in cycle:
#         if node.scope.symbol.name in BUILTINS:
#             continue  # This should not happen since builtins never call self-defined functions.
#         if node.scope.symbol.id in forest.forest:
#             forest.delete_graph(node.scope.symbol.id)
#
#     # Only add the combined node once - (it is possible that the same cycle is found multiple times).
#     if combined_node_name not in forest.forest:
#         forest.add_graph(combined_node.scope.symbol.id, combined_node)
#
#     # Set all pointers pointing to the nodes in the cycle to the combined node.
#     for graph in forest.forest.values():
#         update_pointers(graph, cycle_ids, cycle_id_strs, combined_node)
#
#
# def update_pointers(
#     node: CallGraphNode,
#     cycle_ids: list[NodeID],
#     cycle_id_strs: list[str],
#     combined_node: CallGraphNode,
# ) -> None:
#     """Replace all pointers to nodes in the cycle with the combined node.
#
#     Recursively traverses the tree and replaces all pointers to nodes in the cycle with the combined node.
#
#     Parameters
#     ----------
#     node : CallGraphNode
#         The current node in the tree.
#     cycle_id_strs : list[NodeID]
#         A list of all NodeIDs of nodes in the cycle.
#     combined_node : CallGraphNode
#         The combined node that replaces all nodes in the cycle.
#     """
#     for child in node.children:
#         if child.is_builtin:
#             continue
#         if child.scope.symbol.id.__str__() in cycle_id_strs:
#             node.children.remove(child)
#             node.children.add(combined_node)
#             # Update data
#             if isinstance(node.scope, FunctionScope) and isinstance(
#                 combined_node.scope,
#                 FunctionScope,
#             ):
#                 # node.scope.remove_call_reference_by_id(child.scope.symbol.name)
#                 # TODO: This does not work since we compare a function id with a call id.
#                 #  for this to work we would need to save the call id in the call reference.
#                 #  This would than lead to the analysis analyzing all calls of a function with the same name separately
#                 #  since they no longer share the same name (since this would be the ID of the call).
#                 if child.scope.symbol.id in cycle_ids:
#                     references_to_remove = child.scope.symbol.id
#                     call_ref_list = node.scope.call_references[child.scope.symbol.name]
#                     for ref in call_ref_list:
#                         if ref.id == references_to_remove:
#                             call_ref_list.remove(ref)
#                     node.scope.call_references[child.scope.symbol.name] = call_ref_list  # type: ignore[union-attr]
#
#                 call_refs: list[Reference] = []
#                 if isinstance(child.scope, FunctionScope):
#                     for c_ref in child.scope.call_references.values():
#                         call_refs.extend(c_ref)
#                     calls: dict[str, list[Reference]] = {combined_node.scope.symbol.name: call_refs}
#                     node.scope.call_references.update(calls)
#             # Remove the call from the reasons (reasons need to be updated later)
#             if isinstance(node.reasons, Reasons):
#                 for call in node.reasons.calls.copy():
#                     if (
#                         isinstance(call.node, astroid.Call)
#                         and isinstance(call.node.func, astroid.Name)
#                         and call.node.func.name == child.scope.symbol.name
#                     ):
#                         node.reasons.calls.remove(call)
#
#         else:
#             update_pointers(child, cycle_ids, cycle_id_strs, combined_node)


class CallGraphBuilder:
    """Class for building a call graph.

    This class is used to build a call graph forest for a module from a dict of Reasons.

    Attributes
    ----------
    classes : dict[str, ClassScope]
        Classnames in the module as key and their corresponding ClassScope instance as value.
    raw_reasons : dict[NodeID, Reasons]
        The raw reasons for impurity for all functions.
    call_graph_forest : CallGraphForest
        The call graph forest of the module.
    """

    # TODO: is this the right way to document instance attributes? LARS
    def __init__(
        self,
        classes: dict[str, ClassScope],
        raw_reasons: dict[NodeID, Reasons],
    ) -> None:
        """Initialize the CallGraphBuilder.

        Parameters
        ----------
        classes : dict[str, ClassScope]
            Classnames in the module as key and their corresponding ClassScope instance as value.
        raw_reasons : dict[str, Reasons]
            The raw reasons for impurity for all functions.
            Keys are the ids of the functions.
        """
        self.classes = classes
        self.raw_reasons = raw_reasons
        self.call_graph_forest = CallGraphForest()
        # TODO: does this belong into postinit? LARS
        self._build_call_graph_forest()

    def _build_call_graph_forest(self) -> CallGraphForest:
        """Build the call graph forest.

        Build the call graph forest for the functions of a given module.

        Returns
        -------
        call_graph_forest : CallGraphForest
            The call graph forest for the given functions.
        """
        # Prepare the classes for the call graph.
        self._prepare_classes()

        # Create a new CallGraphNode for each function and add it to the forest.
        for reason in self.raw_reasons.values():
            # Check if the CallGraphNode is already in the forest and has no calls left to deal with.
            if (self.call_graph_forest.has_graph(reason.id)
                and not self.call_graph_forest.get_graph(reason.id).reasons.calls
            ):
                continue

            # Build the call graph for the function and add it to the forest.
            self._built_call_graph(reason)

        # Handle cycles in the call graph.
        self._handle_cycles()

        return self.call_graph_forest

    def _prepare_classes(self) -> None:
        """Prepare the classes of the module.

        Adds the classes of the module to the call graph.
        Since classes can be called (initialized) like functions,
        they need to be added to the call graph forest to propagate the information from the init function
        (which is indirectly invoked by the class call).
        This is done by creating a new CallGraphNode for each class
        and adding it to the forest before the call graph is built.
        """
        for klass in self.classes.values():
            # Create a new CallGraphNode for each class and add it to the forest.
            class_cgn = NewCallGraphNode(
                symbol=klass.symbol,
                reasons=Reasons(klass.symbol.id)
            )
            # If the class has an init function, add it to the class node as a child.
            # Also add the init function to the forest if it is not already there.
            if klass.init_function:
                init_cgn = NewCallGraphNode(
                    symbol=klass.init_function.symbol,
                    reasons=self.raw_reasons[klass.init_function.symbol.id]
                )
                self.call_graph_forest.add_graph(klass.init_function.symbol.id, init_cgn)
                class_cgn.add_child(init_cgn)

            # Add the class to the forest.
            self.call_graph_forest.add_graph(klass.symbol.id, class_cgn)

    def _built_call_graph(self, reason: Reasons) -> None:
        """Build the call graph for a function.

        Recursively builds the call graph for a function and adds it to the forest.
        The order in which the functions are handled does not matter,
         since the functions will set the pointers to the children if needed.

        Parameters
        ----------
        reason : Reasons
            The raw reasons of the function.
        """
        # If the node is already inside the forest and does not have any calls left, it is considered to be finished.
        if self.call_graph_forest.has_graph(reason.id) and not reason.calls:
            return

        # Create a new node and add it to the forest.
        cgn = NewCallGraphNode(
            symbol=reason.function_scope.symbol,
            reasons=reason
        )
        self.call_graph_forest.add_graph(reason.id, cgn)

        # The node has calls, which need to be added to the forest and to the children of the current node.
        for call in cgn.reasons.calls.copy():
            if call in self.call_graph_forest.get_graph(reason.id).reasons.calls:
                self.call_graph_forest.get_graph(reason.id).reasons.calls.remove(call)
            if isinstance(call, Builtin):
                builtin_cgn = NewCallGraphNode(
                    symbol=call,
                    reasons=Reasons(call.id)
                )
                self.call_graph_forest.get_graph(reason.id).add_child(builtin_cgn)

            # Check if the called child function is already in the forest and has no calls left to deal with.
            elif (self.call_graph_forest.has_graph(call.id)
                  and not self.call_graph_forest.get_graph(call.id).reasons.calls
            ):
                # Add the child to the children of the current node since it doesn't need further handling.
                self.call_graph_forest.get_graph(reason.id).add_child(self.call_graph_forest.get_graph(call.id))

            # Check if the node was declared inside the current module.
            elif call.id not in self.raw_reasons:
                self._handle_unknown_call(call, reason.id)

            # Build the call graph for the child function and add it to the children of the current node.
            else:
                self._built_call_graph(self.raw_reasons[call.id])
                self.call_graph_forest.get_graph(reason.id).add_child(self.call_graph_forest.get_graph(call.id))

    def _handle_unknown_call(self, call: Symbol, reason_id: NodeID) -> None:
        """Handle unknown calls.

        Deal with unknown calls and add them to the forest.
        Unknown calls are calls of unknown code, calls of imported code, or calls of parameters.
        If the call references an imported function, it is represented as ImportedCallGraphNode in the forest.

        Parameters
        ----------
        call : Symbol
            The call that is unknown.
        reason_id : NodeID
            The id of the function that the call is in.
        """
        # Deal with the case that the call calls an imported function.
        if isinstance(call, Import):
            imported_cgn = ImportedCallGraphNode(
                symbol=call,
                reasons=Reasons(id=call.id),
                # is_imported=bool(isinstance(call.node, astroid.Import | astroid.ImportFrom))
            )
            self.call_graph_forest.add_graph(call.id, imported_cgn)
            self.call_graph_forest.get_graph(reason_id).add_child(self.call_graph_forest.get_graph(call.id))

            # If the call was used as a member of an MemberAccessValue, it needs to be removed from the unknown_calls.
            # This is due to the improved analysis that can determine the module through the receiver of that call.
            # Hence, the call is handled as a call of an imported function and not as an unknown_call
            # when inferring the purity later.
            for unknown_call in self.call_graph_forest.get_graph(reason_id).reasons.unknown_calls:
                if unknown_call.node == call.call:
                    self.call_graph_forest.get_graph(reason_id).reasons.remove_unknown_call(calc_node_id(call.call))

        # Deal with the case that the call calls a function parameter.
        if isinstance(call, Parameter):
            self.call_graph_forest.get_graph(reason_id).reasons.unknown_calls.add(call)

        else:
            self.call_graph_forest.get_graph(reason_id).reasons.unknown_calls.add(call)

    def _handle_cycles(self, removed_nodes: set[NodeID] | None = None) -> None:
        """Handle cycles in the call graph.

        Handles cycles within the call graph.
        Iterates over the forest and checks for cycles in each tree.
        If a cycle is found, it is contracted into a single node and all pointers are updated respectively.
        Stores all nodes that have been removed (=nodes inside combined nodes) in the removed_nodes set.

        Parameters
        ----------
        removed_nodes : set[NodeID] | None
            A set of all removed nodes.
            If not given, a new set is created.
        """
        if removed_nodes is None:
            removed_nodes = set()
        for graph in self.call_graph_forest.forest.copy().values():
            if graph.symbol.id in removed_nodes or all(child.symbol.id in removed_nodes for child in graph.children.values()):
                continue

            cycle = self._test_cgn_for_cycles(graph)
            if cycle:
                self._contract_cycle(cycle)
                removed_nodes.update(cycle.keys())

    def _test_cgn_for_cycles(
        self,
        cgn: NewCallGraphNode,
        visited_nodes: set[NewCallGraphNode] | None = None,
        path: list[NodeID] | None = None,
    ) -> dict[NodeID, NewCallGraphNode]:
        """Test for cycles in the call graph.

        Recursively traverses the call graph and checks for cycles.
        It uses a DFS approach to traverse the graph.
        If a cycle is found, a dict of all nodes in the cycle is returned.

        Parameters
        ----------
        cgn : NewCallGraphNode
            The current node in the graph that is visited.
        visited_nodes : set[NewCallGraphNode] | None
            A set of all visited nodes.
        path : list[NodeID] | None
            A list of all nodes in the current path.

        Returns
        -------
        cycle : dict[NodeID, NewCallGraphNode]
           Dict of all nodes in the cycle.
           Keys are the NodeIDs of the nodes.
           Returns an empty dict if no cycle is found.
        """
        # If the visited_nodes set is not given, create a new one.
        if visited_nodes is None:
            visited_nodes = set()
        # If the path list is not given, create a new one.
        if path is None:
            path = []

        # If the current node is already in the path, a cycle is found.
        if cgn.symbol.id in path:
            # TODO: how to handle nested cycles? LARS
            cut_path = path[path.index(cgn.symbol.id):]
            return {node_id: self.call_graph_forest.get_graph(node_id) for node_id in cut_path}

        # If a node has no children, it is a leaf node, and an empty list is returned.
        if not cgn.children:
            return {}

        # Mark the current node as visited.
        visited_nodes.add(cgn)
        path.append(cgn.symbol.id)

        cycle: dict[NodeID, NewCallGraphNode] = {}

        # Check for cycles in children.
        for child in cgn.children.values():
            cycle = self._test_cgn_for_cycles(child, visited_nodes, path)
            if cycle:
                return cycle
        # Remove the current node from the path when backtracking.
        path.pop()

        return cycle

    def _contract_cycle(self, cycle: dict[NodeID, NewCallGraphNode]) -> None:
        # Create the new combined node.
        combined_name = "+".join(sorted(c.__str__() for c in cycle))
        # module = cycle[next(iter(cycle))].symbol.node.root()
        combined_id = NodeID(None, combined_name)
        combined_reasons = Reasons(id=combined_id).join_reasons_list([node.reasons for node in cycle.values()])
        combined_cgn = CombinedCallGraphNode(
            symbol=CombinedSymbol(
                node=None,
                id=combined_id,
                name=combined_name,
            ),
            reasons=combined_reasons,
            combines=cycle
        )
        # Check if the combined node is already in the forest.
        if self.call_graph_forest.has_graph(combined_cgn.symbol.id):
            return

        # Find all other calls (calls that are not part of the cycle) and remove all nodes in the cycle from the forest.
        for node in cycle.values():
            for child in node.children.values():
                if child.symbol.id not in cycle and not combined_cgn.has_child(child.symbol.id):
                    combined_cgn.add_child(child)
            self.call_graph_forest.delete_graph(node.symbol.id)

        # Add the combined node to the forest.
        self.call_graph_forest.add_graph(combined_id, combined_cgn)

        # Set all pointers from nodes calling the nodes in the cycle to the combined node.
        self._update_pointers(cycle, combined_cgn)

    def _update_pointers(self, cycle: dict[NodeID, NewCallGraphNode], combined_node: CombinedCallGraphNode) -> None:
        """Replace all pointers to nodes inside the cycle with pointers to the combined node.

        Traverses the tree and replaces all pointers to nodes in the cycle with pointers to the combined node.

        Parameters
        ----------
        cycle : dict[NodeID, NewCallGraphNode]
            A dict of all nodes in the cycle.
            Keys are the NodeIDs of the nodes.
        combined_node : CombinedCallGraphNode
            The combined node that replaces all nodes in the cycle.
        """
        for graph in self.call_graph_forest.forest.values():
            for child in graph.children.copy().values():
                if child.symbol.id in cycle:
                    graph.delete_child(child.symbol.id)
                    graph.add_child(combined_node)
