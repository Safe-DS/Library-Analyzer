import builtins

import astroid

from library_analyzer.processing.api.purity_analysis.model import (
    CallGraphForest,
    CallGraphNode,
    ClassScope,
    FunctionScope,
    NodeID,
    Reasons,
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

    for function_scopes in classes_and_functions.values():
        # Inner for loop is needed to handle multiple function defs with the same name
        for function_scope in function_scopes:
            # Add reasons for impurity to the corresponding function
            function_id = function_scope.symbol.id
            if not isinstance(function_scope, FunctionScope):
                function_node = CallGraphNode(function=function_scope, reasons=Reasons())
            elif raw_reasons[function_id]:
                function_node = CallGraphNode(function=function_scope, reasons=raw_reasons[function_id])
            else:
                raise ValueError(f"No reasons found for function {function_scope.symbol.name}")

            # Case where the function is not called before by any other function
            if function_id not in call_graph_forest.graphs:
                call_graph_forest.add_graph(
                    function_id,
                    function_node,
                )  # We save the tree in the forest by the name of the root function

            # When dealing with a class, we need to add the init function to the call graph manually (if it exists)
            if isinstance(function_scope, ClassScope):
                if "__init__" in functions:
                    for fun in functions["__init__"]:
                        if fun.parent == function_scope:
                            init_function = fun
                            if init_function.symbol.id not in call_graph_forest.graphs:
                                call_graph_forest.add_graph(
                                    init_function.symbol.id,
                                    CallGraphNode(function=init_function, reasons=Reasons()),
                                )
                            function_node.add_child(call_graph_forest.get_graph(init_function.symbol.id))
                            function_node.reasons.calls.add(Symbol(
                                node=raw_reasons[init_function.symbol.id].function.symbol.node,
                                # type: ignore[union-attr] # function is always of type FunctionScope here
                                id=init_function.symbol.id,
                                name=init_function.symbol.name))
                            break
                continue

            # Default case where a function calls no other functions in its body - therefore, the tree has just one node
            if not isinstance(function_scope, FunctionScope) or not function_scope.call_references:
                continue

            # If the function calls other functions in its body, we need to build a tree
            else:
                for call_name, call_ref in function_scope.call_references.items():
                    # We take the first call to represent all calls of the same name.
                    # This does not vary the result and is faster.
                    call = call_ref[0]

                    # Handle self defined function calls
                    if call_name in classes_and_functions:
                        # Check if any function def has the same name as the called function
                        matching_function_defs = [called_fun for called_fun in classes_and_functions[call.name]
                                                  if called_fun.symbol.name == call.name]
                        current_tree_node = call_graph_forest.get_graph(function_id)
                        break_condition = False  # This is used to indicate that one or more functions defs was
                        # found inside the forest that matches the called function name

                        # We need to check if the called function is already in the tree
                        for f in matching_function_defs:
                            if call_graph_forest.get_graph(f.symbol.id):
                                current_tree_node.add_child(call_graph_forest.get_graph(f.symbol.id))
                                break_condition = True  # A function def inside the forest was found
                                # so the following else statement must not be executed

                        if break_condition:
                            pass  # Skip the else statement because the function def is already in the forest

                        # If the called function is not in the forest,
                        # we need to compute it first and then connect it to the current tree
                        else:
                            for called_function_scope in classes_and_functions[call.name]:
                                # Check if any function def has the same name as the called function
                                for f in matching_function_defs:
                                    if raw_reasons[f.symbol.id]:
                                        call_graph_forest.add_graph(
                                            f.symbol.id,
                                            CallGraphNode(
                                                function=called_function_scope,
                                                reasons=raw_reasons[f.symbol.id],
                                            ),
                                        )
                                    else:
                                        call_graph_forest.add_graph(
                                            f.symbol.id,
                                            CallGraphNode(function=called_function_scope, reasons=Reasons()),
                                        )
                                    current_tree_node.add_child(call_graph_forest.get_graph(f.symbol.id))

                    # Handle builtins: builtins are not in the functions dict,
                    # and therefore we need to handle them separately.
                    # Since we do not analyze builtins any further at this stage,
                    # we can simply add them as a child to the current tree node.
                    # Because a builtin function has no real function def,
                    # we will use the call node as the function def - hence its id is always wrong
                    elif call.name in BUILTINS or call.name in ("read", "readline", "readlines", "write", "writelines"):
                        current_tree_node = call_graph_forest.get_graph(function_id)
                        # We need to build an artificial FunctionScope node for builtins, since the rest of the analysis
                        # relies on the function being a FunctionScope instance
                        builtin_function = astroid.FunctionDef(
                            name=call.name,
                            lineno=call.node.lineno,
                            col_offset=call.node.col_offset,
                        )
                        builtin_symbol = Symbol(
                            node=builtin_function,
                            id=call.id,
                            name=call.name,
                        )
                        builtin_scope = FunctionScope(builtin_symbol)

                        current_tree_node.add_child(CallGraphNode(function=builtin_scope, reasons=Reasons(), is_builtin=True))

                    # Deal with unknown calls:
                    # - calls of unknown code => call node not in functions dict
                    # - calls of external code => call node not in function_reference dict
                    # - calls of parameters # TODO: parameter calls are not handled yet
                    # These functions get an unknown flag
                    else:
                        current_tree_node = call_graph_forest.get_graph(function_id)
                        if isinstance(current_tree_node.reasons, Reasons):
                            if not isinstance(current_tree_node.reasons.unknown_calls, list):
                                current_tree_node.reasons.unknown_calls = []
                            current_tree_node.reasons.unknown_calls.append(call.node)

    handle_cycles(call_graph_forest, raw_reasons, functions)

    return call_graph_forest


def handle_cycles(call_graph_forest: CallGraphForest,
                  function_references: dict[NodeID, Reasons],
                  functions: dict[str, list[FunctionScope]]) -> CallGraphForest:
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
    # If a node has no children, it is a leaf node, and we can return an empty list
    if not graph.children:
        return []

    if graph in path:
        return path[path.index(graph):]  # A cycle is found, return the path containing the cycle

    # Mark the current node as visited
    visited_nodes.add(graph)
    path.append(graph)

    cycle = []

    # Check for cycles in children
    for child in graph.children:
        cycle = test_for_cycles(child, visited_nodes, path)
        if cycle:
            return cycle
    path.pop()  # Remove the current node from the path when backtracking

    return cycle


# TODO: add cycle detection for FunctionScope instances
def contract_cycle(
    forest: CallGraphForest,
    cycle: list[CallGraphNode],
    function_references: dict[NodeID, Reasons],
    functions: dict[str, list[FunctionScope]]
) -> None:
    """Contracts a cycle in the call graph.

    Given a cycle in the call graph, this function contracts the cycle into a single node.

    Parameters
    ----------
    forest : CallGraphForest
        The call graph forest of the functions.
    cycle : list[CallGraphNode]
        All nodes in the cycle.
    function_references : dict
        All nodes relevant for reference resolving inside functions.
    functions : dict[str, list[FunctionScope]]
        All functions and a list of their FunctionScopes.
        The value is a list since there can be multiple functions with the same name.
        It Is not needed in this function especially, but is needed for the contract_cycle function.
    """
    # Create the new combined node
    cycle_ids = [node.function.symbol.id.__str__() for node in cycle]
    cycle_names = [node.function.symbol.name for node in cycle]
    combined_node_name = "+".join(sorted(cycle_ids))
    combined_node_data = FunctionScope(
        Symbol(
            None,
            NodeID(None, combined_node_name, -1, -1),
            combined_node_name,
        ),
    )
    combined_reasons = Reasons.join_reasons_list([node.reasons for node in cycle])
    combined_node = CallGraphNode(function=combined_node_data, reasons=combined_reasons, combined_node_names=cycle_ids)

    # Add children to the combined node if they are not in the cycle (other calls)
    if any(isinstance(node.function, FunctionScope) and hasattr(node.function, "call_references") for node in cycle):
        other_calls = [
            call[0]
            for node in cycle
            for call_name, call in node.function.call_references.items()
            if call_name not in cycle_names and call_name not in BUILTINS or call[0].name in ("read", "readline", "readlines", "write", "writelines")
        ]
        # Find all function definitions that match the other call names for each call
        matching_function_defs = {}
        for call in other_calls:
            matching_function_defs[call.name] = [called_function for called_function in functions[call.name]
                                                 if called_function.symbol.name == call.name]

        # Find all builtin calls
        builtin_calls = []
        for node in cycle:
            for call in node.function.call_references.values():
                if call[0].name in BUILTINS or call[0].name in ("read", "readline", "readlines", "write", "writelines"):
                    call_node = call[0]
                    # We need to build an artificial FunctionScope node for builtins, since the rest of the analysis
                    # relies on the function being a FunctionScope instance
                    builtin_function = astroid.FunctionDef(
                        name=call_node.name,
                        lineno=call_node.node.lineno,
                        col_offset=call_node.node.col_offset,
                    )
                    builtin_symbol = Symbol(
                        node=builtin_function,
                        id=call_node.id,
                        name=call_node.name,
                    )
                    builtin_scope = FunctionScope(builtin_symbol)
                    builtin_calls.append(builtin_scope)

        # Add the calls as well as the children of the function defs to the combined node
        combined_node_data.call_references = other_calls + builtin_calls
        combined_node.children = {
            CallGraphNode(function=matching_function_defs[call.name][i],
                          reasons=function_references[matching_function_defs[call.name][i].symbol.id])
            for call in other_calls
            for i in range(len(matching_function_defs[call.name]))
        }  # Add the function def (list of function defs) as children to the combined node
        # if the function def name matches the call name
        combined_node.children.update({CallGraphNode(function=call, reasons=Reasons(), is_builtin=True)
                                       for call in builtin_calls})

    # Remove all nodes in the cycle from the forest and add the combined node instead
    for node in cycle:
        if node.function.symbol.name in BUILTINS:
            continue  # This should not happen since builtins never call self-defined functions
        if node.function.symbol.id in forest.graphs:
            forest.delete_graph(node.function.symbol.id)

    # Only add the combined node once - (it is possible that the same cycle is found multiple times)
    if combined_node_name not in forest.graphs:
        forest.add_graph(combined_node.function.symbol.id, combined_node)

    # Set all pointers to the nodes in the cycle to the combined node
    for graph in forest.graphs.values():
        update_pointers(graph, cycle_ids, combined_node)


def update_pointers(node: CallGraphNode, cycle_names: list[str], combined_node: CallGraphNode) -> None:
    """Replace all pointers to nodes in the cycle with the combined node.

    Recursively traverses the tree and replaces all pointers to nodes in the cycle with the combined node.

    Parameters
    ----------
    node : CallGraphNode
        The current node in the tree.
    cycle_names : list[str]
        A list of all names of nodes in the cycle.
    combined_node : CallGraphNode
        The combined node that replaces all nodes in the cycle.
    """
    for child in node.children:
        if child.is_builtin:
            continue
        if child.function.symbol.id.__str__() in cycle_names:
            node.children.remove(child)
            node.children.add(combined_node)
            # Update data
            if isinstance(node.function, FunctionScope):
                node.function.remove_call_node_by_name(child.function.symbol.name)
                node.function.call_references.update(
                    {combined_node.function.symbol.name: combined_node.function.call_references})
            # Remove the call from the reasons (reasons need to be updated later)
            if isinstance(node.reasons, Reasons):
                for call in node.reasons.calls.copy():
                    if (isinstance(call.node, astroid.Call) and isinstance(call.node.func, astroid.Name)
                        and call.node.func.name == child.function.symbol.name
                    ):
                        node.reasons.calls.remove(call)

        else:
            update_pointers(child, cycle_names, combined_node)
