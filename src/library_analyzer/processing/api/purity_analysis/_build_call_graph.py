import builtins

import astroid

from library_analyzer.processing.api.purity_analysis.model import (
    Builtin,
    BuiltinOpen,
    CallGraphForest,
    CallGraphNode,
    ClassScope,
    FunctionScope,
    NodeID,
    Reasons,
    Reference,
    Symbol,
)

BUILTINS = dir(builtins)


def build_call_graph(
    functions: dict[str, list[FunctionScope]],
    classes: dict[str, ClassScope],
    raw_reasons: dict[NodeID, Reasons],
) -> CallGraphForest:
    """Build a call graph from a list of functions.

    This function builds a CallGraphForest from a list of functions.
    The root nodes of the trees are the functions that are called first.

    Parameters
    ----------
    functions : dict[str, list[FunctionScope]]
        All functions and a list of their FunctionScopes.
        The value is a list since there can be multiple functions with the same name.
    classes : dict[str, ClassScope]
        Classnames in the module as key and their corresponding ClassScope instance as value.
    raw_reasons : dict[str, Reasons]
        The reasons for impurity of the functions.

    Returns
    -------
    call_graph_forest : CallGraphForest
        The call graph forest for the given functions.
    """
    call_graph_forest = CallGraphForest()
    classes_and_functions: dict[str, list[FunctionScope] | ClassScope] = {**classes, **functions}

    for scopes in classes_and_functions.values():
        # Inner for loop is needed to handle multiple function defs with the same name.
        for scope in scopes:
            if not isinstance(scope, FunctionScope | ClassScope):
                raise TypeError(f"Scope {scope} is not of type FunctionScope or ClassScope") from None
            # Add reasons for impurity to the corresponding function.
            function_id = scope.symbol.id
            if isinstance(scope, ClassScope):
                current_call_graph_node = CallGraphNode(scope=scope, reasons=Reasons())
            elif raw_reasons[function_id]:
                current_call_graph_node = CallGraphNode(scope=scope, reasons=raw_reasons[function_id])
            else:
                raise ValueError(f"No reasons found for function {scope.symbol.name}")

            # Case where the function is not called before by any other function.
            if function_id not in call_graph_forest.graphs:
                call_graph_forest.add_graph(
                    function_id,
                    current_call_graph_node,
                )  # Save the tree in the forest by the name of the root function.

            # When dealing with a class, the init function needs to be added to the call graph manually (if it exists).
            if isinstance(scope, ClassScope):
                for fun in functions.get("__init__", []):
                    if fun.parent == scope:
                        init_function = fun
                        if init_function.symbol.id not in call_graph_forest.graphs:
                            call_graph_forest.add_graph(
                                init_function.symbol.id,
                                CallGraphNode(scope=init_function, reasons=Reasons(function_scope=init_function)),
                            )
                        current_call_graph_node.add_child(call_graph_forest.get_graph(init_function.symbol.id))
                        current_call_graph_node.reasons.calls.add(
                            Symbol(
                                node=raw_reasons[init_function.symbol.id].function_scope.symbol.node,  # type: ignore[union-attr]
                                # function_scope is always of type FunctionScope here since it is the init function.
                                id=init_function.symbol.id,
                                name=init_function.symbol.name,
                            ),
                        )
                        break
                continue

            # Default case where a function calls no other functions in its body - therefore, the tree has just one node
            if not isinstance(scope, FunctionScope) or not scope.call_references:
                continue

            # If the function calls other functions in its body, a tree is built for each call.
            else:
                for call_name, call_ref in scope.call_references.items():
                    # Take the first call to represent all calls of the same name.
                    # This does not vary the result and is faster.
                    call = call_ref[0]

                    # Handle self defined function calls
                    if call_name in classes_and_functions:
                        # Check if any function def has the same name as the called function
                        matching_function_defs = [
                            called_fun
                            for called_fun in classes_and_functions[call.name]
                            if called_fun.symbol.name == call.name
                        ]
                        current_tree_node = call_graph_forest.get_graph(function_id)
                        break_condition = False  # This is used to indicate that one or more functions defs was
                        # found inside the forest that matches the called function name.

                        # Check if the called function is already in the tree.
                        for f in matching_function_defs:
                            if call_graph_forest.has_graph(f.symbol.id):
                                current_tree_node.add_child(call_graph_forest.get_graph(f.symbol.id))
                                break_condition = True  # A function def inside the forest was found
                                # so the following else statement must not be executed.

                        if break_condition:
                            pass  # Skip the else statement because the function def is already in the forest.

                        # If the called function is not in the forest,
                        # compute it first and then connect it to the current tree
                        else:
                            for called_function_scope in classes_and_functions[call_name]:
                                # Check if any function def has the same name as the called function
                                for f in matching_function_defs:
                                    if raw_reasons[f.symbol.id]:
                                        call_graph_forest.add_graph(
                                            f.symbol.id,
                                            CallGraphNode(
                                                scope=called_function_scope,  # type: ignore[arg-type]
                                                # Mypy does not recognize that function_scope is of type FunctionScope
                                                # or ClassScope here even it is.
                                                reasons=raw_reasons[f.symbol.id],
                                            ),
                                        )
                                    else:
                                        call_graph_forest.add_graph(
                                            f.symbol.id,
                                            CallGraphNode(scope=called_function_scope, reasons=Reasons(function_scope=called_function_scope)),  # type: ignore[arg-type]
                                            # Mypy does not recognize that function_scope is of type FunctionScope or
                                            # ClassScope here even it is.
                                        )
                                    current_tree_node.add_child(call_graph_forest.get_graph(f.symbol.id))

                    # Handle builtins: builtins are not in the functions dict,
                    # and therefore need to be handled separately.
                    # Since builtins are not analyzed any further at this stage,
                    # they can simply be added as a child to the current tree node.
                    elif call.name in BUILTINS or call.name in (
                        "open",
                        "read",
                        "readline",
                        "readlines",
                        "write",
                        "writelines",
                        "close",
                    ):
                        current_tree_node = call_graph_forest.get_graph(function_id)
                        # Build an artificial FunctionScope node for calls of builtins, since the rest of the analysis
                        # relies on the function being a FunctionScope instance.
                        builtin_function = astroid.FunctionDef(
                            name=call.name,
                            lineno=call.node.lineno,
                            col_offset=call.node.col_offset,
                        )
                        builtin_symbol = Builtin(
                            node=builtin_function,
                            id=NodeID(None, call.name),
                            name=call.name,
                        )
                        if call.name in ("open", "read", "readline", "readlines", "write", "writelines", "close"):
                            builtin_symbol = BuiltinOpen(
                                node=builtin_function,
                                id=call.id,
                                name=call.name,
                                call=call.node,
                            )
                        builtin_scope = FunctionScope(builtin_symbol)

                        current_tree_node.add_child(
                            CallGraphNode(scope=builtin_scope, reasons=Reasons(function_scope=builtin_scope), is_builtin=True),
                        )

                    # Deal with unknown calls:
                    # - calls of imported functions
                    # - calls of native code
                    # - calls of function parameters
                    # These calls are not in the functions dict and therefore need to be handled separately later.
                    # This step is done in _infer_purity.py/transform_reasons_to_impurity_result()
                    else:
                        current_tree_node = call_graph_forest.get_graph(function_id)
                        if isinstance(current_tree_node.reasons, Reasons):
                            current_tree_node.reasons.unknown_calls.add(call.node)

    handle_cycles(call_graph_forest, raw_reasons, functions)

    return call_graph_forest


def handle_cycles(
    call_graph_forest: CallGraphForest,
    function_references: dict[NodeID, Reasons],
    functions: dict[str, list[FunctionScope]],
) -> CallGraphForest:
    """Handle cycles in the call graph.

    This function checks for cycles in the call graph forest and contracts them into a single node.

    Parameters
    ----------
    call_graph_forest : CallGraphForest
        The call graph forest of the functions.
    function_references : dict[str, Reasons]
        All nodes relevant for reference resolving inside functions.
    functions : dict[str, list[FunctionScope]]
        All functions and a list of their FunctionScopes.
        The value is a list since there can be multiple functions with the same name.
        It Is not needed in this function especially, but is needed for the contract_cycle function.

    Returns
    -------
    call_graph_forest : CallGraphForest
        The call graph forest with contracted cycles.
    """
    for graph in call_graph_forest.graphs.copy().values():
        visited_nodes: set[CallGraphNode] = set()
        path: list[CallGraphNode] = []
        cycle = test_for_cycles(graph, visited_nodes, path)
        if cycle:
            # print("cycle found", cycle)
            contract_cycle(call_graph_forest, cycle, function_references, functions)
            # TODO: check if other cycles exists
        else:
            # print("no cycles found")
            pass
    return call_graph_forest


def test_for_cycles(
    graph: CallGraphNode,
    visited_nodes: set[CallGraphNode],
    path: list[CallGraphNode],
) -> list[CallGraphNode]:
    """Tests for cycles in the call graph.

    This function recursively traverses the call graph and checks for cycles.
    It uses a DFS approach to traverse the graph.
    If a cycle is found, the cycle is returned.
    It is possible that multiple cycles exist, but only one is returned.

    Parameters
    ----------
    graph : CallGraphNode
        The current node in the graph that is visited.
    visited_nodes : set[CallGraphNode]
        A set of all visited nodes.
    path : list[CallGraphNode]
        A list of all nodes in the current path.

    Returns
    -------
    cycle : list[CallGraphNode]
        A list of all nodes in the cycle.
        If no cycle is found, an empty list is returned.
    """
    # If a node has no children, it is a leaf node, and an empty list is returned.
    if not graph.children:
        return []

    if graph in path:
        return path[path.index(graph) :]  # A cycle is found, return the path containing the cycle.

    # Mark the current node as visited.
    visited_nodes.add(graph)
    path.append(graph)

    cycle = []

    # Check for cycles in children.
    for child in graph.children:
        cycle = test_for_cycles(child, visited_nodes, path)
        if cycle:
            return cycle
    path.pop()  # Remove the current node from the path when backtracking.

    return cycle


# TODO: add cycle detection for FunctionScope instances
def contract_cycle(
    forest: CallGraphForest,
    cycle: list[CallGraphNode],
    raw_reasons: dict[NodeID, Reasons],
    functions: dict[str, list[FunctionScope]],
) -> None:
    """Contracts a cycle in the call graph.

    Given a cycle in the call graph, this function contracts the cycle into a single node.

    Parameters
    ----------
    forest : CallGraphForest
        The call graph forest of the functions.
    cycle : list[CallGraphNode]
        All nodes in the cycle.
    raw_reasons : dict
        All nodes relevant for reference resolving inside functions.
    functions : dict[str, list[FunctionScope]]
        All functions and a list of their FunctionScopes.
        The value is a list since there can be multiple functions with the same name.
        It Is not needed in this function especially, but is needed for the contract_cycle function.
    """
    # Create the new combined node
    cycle_ids = [node.scope.symbol.id for node in cycle]
    cycle_id_strs = [node.scope.symbol.id.__str__() for node in cycle]
    cycle_names = [node.scope.symbol.name for node in cycle]
    combined_node_name = "+".join(sorted(cycle_id_strs))
    # TODO: we probably need to differentiate between real cyclic calls and recursive calls
    combined_node_data = FunctionScope(
        Symbol(
            None,
            NodeID(None, combined_node_name),
            combined_node_name,
        ),
    )
    combined_reasons = Reasons(function_scope=combined_node_data).join_reasons_list([node.reasons for node in cycle])
    combined_node = CallGraphNode(
        scope=combined_node_data,
        reasons=combined_reasons,
        combined_node_ids=cycle_ids,
    )

    # Add children to the combined node if they are not in the cycle (other calls).
    if any(
        isinstance(node.scope, FunctionScope) and hasattr(node.scope, "call_references")
        for node in cycle
    ):
        other_calls: dict[str, list[Reference]] = {
            call[0].name: [call[0]]
            for node in cycle
            for call_name, call in node.scope.call_references.items()  # type: ignore[union-attr] # Mypy does not recognize that function_scope is of type FunctionScope here even it is.
            if isinstance(node.scope, FunctionScope)
            and call_name not in cycle_names
            and call_name not in BUILTINS
            or call[0].name in ("read", "readline", "readlines", "write", "writelines")
        }
        # Find all function definitions that match the other call names for each call.
        matching_function_defs = {}
        for call_name in other_calls:
            if call_name not in functions:
                matching_function_defs[call_name] = []
            else:
                matching_function_defs[call_name] = [
                    called_function for called_function in functions[call_name] if called_function.symbol.name == call_name
                ]

        # Find all builtin calls.
        builtin_calls: dict[str, list[Reference]] = {
            call[0].name: [call[0]]
            for node in cycle
            for call in node.scope.call_references.values()  # type: ignore[union-attr]
            if isinstance(node.scope, FunctionScope)
            and call[0].name in BUILTINS
            or call[0].name in ("read", "readline", "readlines", "write", "writelines")
        }

        builtin_call_functions: list[FunctionScope] = []
        for call_node in builtin_calls.values():
            # Build an artificial FunctionScope node for calls of builtins, since the rest of the analysis
            # relies on the function being a FunctionScope instance.
            builtin_function = astroid.FunctionDef(
                name=call_node[0].name,
                lineno=call_node[0].node.lineno,
                col_offset=call_node[0].node.col_offset,
            )

            builtin_symbol = Builtin(
                node=builtin_function,
                id=call_node[0].id,
                name=call_node[0].name,
            )
            if call_node[0].name in ("read", "readline", "readlines", "write", "writelines"):
                builtin_symbol = BuiltinOpen(
                    node=builtin_function,
                    id=call_node[0].id,
                    name=call_node[0].name,
                    call=call_node[0].node,
                )
            builtin_scope = FunctionScope(builtin_symbol)
            builtin_call_functions.append(builtin_scope)

        # Add the calls as well as the children of the function defs to the combined node.
        combined_node_data.call_references.update(other_calls)
        combined_node_data.call_references.update(builtin_calls)
        combined_node.children = {
            CallGraphNode(
                scope=matching_function_defs[call[0].name][i],
                reasons=raw_reasons[matching_function_defs[call[0].name][i].symbol.id],
            )
            for call in other_calls.values()
            for i in range(len(matching_function_defs[call[0].name]))
        }  # Add the function def (list of function defs) as children to the combined node
        # if the function def name matches the call name.
        combined_node.children.update({
            CallGraphNode(scope=builtin_call_function, reasons=Reasons(function_scope=builtin_call_function), is_builtin=True)
            for builtin_call_function in builtin_call_functions
        })

    # Remove all nodes in the cycle from the forest and add the combined node instead.
    for node in cycle:
        if node.scope.symbol.name in BUILTINS:
            continue  # This should not happen since builtins never call self-defined functions.
        if node.scope.symbol.id in forest.graphs:
            forest.delete_graph(node.scope.symbol.id)

    # Only add the combined node once - (it is possible that the same cycle is found multiple times).
    if combined_node_name not in forest.graphs:
        forest.add_graph(combined_node.scope.symbol.id, combined_node)

    # Set all pointers pointing to the nodes in the cycle to the combined node.
    for graph in forest.graphs.values():
        update_pointers(graph, cycle_ids, cycle_id_strs, combined_node)


def update_pointers(
    node: CallGraphNode,
    cycle_ids: list[NodeID],
    cycle_id_strs: list[str],
    combined_node: CallGraphNode,
) -> None:
    """Replace all pointers to nodes in the cycle with the combined node.

    Recursively traverses the tree and replaces all pointers to nodes in the cycle with the combined node.

    Parameters
    ----------
    node : CallGraphNode
        The current node in the tree.
    cycle_id_strs : list[NodeID]
        A list of all NodeIDs of nodes in the cycle.
    combined_node : CallGraphNode
        The combined node that replaces all nodes in the cycle.
    """
    for child in node.children:
        if child.is_builtin:
            continue
        if child.scope.symbol.id.__str__() in cycle_id_strs:
            node.children.remove(child)
            node.children.add(combined_node)
            # Update data
            if isinstance(node.scope, FunctionScope) and isinstance(
                combined_node.scope,
                FunctionScope,
            ):
                # node.scope.remove_call_reference_by_id(child.scope.symbol.name)
                # TODO: This does not work since we compare a function id with a call id.
                #  for this to work we would need to save the call id in the call reference.
                #  This would than lead to the analysis analyzing all calls of a function with the same name separately
                #  since they no longer share the same name (since this would be the ID of the call).
                if child.scope.symbol.id in cycle_ids:
                    references_to_remove = child.scope.symbol.id
                    call_ref_list = node.scope.call_references[child.scope.symbol.name]
                    for ref in call_ref_list:
                        if ref.id == references_to_remove:
                            call_ref_list.remove(ref)
                    node.scope.call_references[child.scope.symbol.name] = call_ref_list  # type: ignore[union-attr]

                call_refs: list[Reference] = []
                if isinstance(child.scope, FunctionScope):
                    for c_ref in child.scope.call_references.values():
                        call_refs.extend(c_ref)
                    calls: dict[str, list[Reference]] = {combined_node.scope.symbol.name: call_refs}
                    node.scope.call_references.update(calls)
            # Remove the call from the reasons (reasons need to be updated later)
            if isinstance(node.reasons, Reasons):
                for call in node.reasons.calls.copy():
                    if (
                        isinstance(call.node, astroid.Call)
                        and isinstance(call.node.func, astroid.Name)
                        and call.node.func.name == child.scope.symbol.name
                    ):
                        node.reasons.calls.remove(call)

        else:
            update_pointers(child, cycle_ids, cycle_id_strs, combined_node)
