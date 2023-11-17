import builtins

from library_analyzer.processing.api.purity_analysis.model import FunctionScope, CallGraphNode, CallGraphForest, Symbol, \
    Reasons

BUILTINS = dir(builtins)


def build_call_graph(functions: dict[str, list[FunctionScope]], function_references: dict[str, Reasons]) -> CallGraphForest:
    """Builds a call graph from a list of functions.

    Parameters
    ----------
        * functions: a dict of functions
        * function_references: a dict of function references - contains the reasons for impurity

    Returns
    -------
        * call_graph_forest: the call graph forest with cycles contracted
    """

    global BUILTINS

    current_tree_node = CallGraphNode()
    call_graph_forest = CallGraphForest()

    for function_name, function_scopes in functions.items():
        for function_scope in function_scopes:
            # Add reasons for impurity to the corresponding function
            if function_references[function_name]:
                function_node = CallGraphNode(data=function_scope, reasons=function_references[function_name])
            else:
                function_node = CallGraphNode(data=function_scope)

            # Case where the function is not called before by any other function
            if function_name not in call_graph_forest.graphs.keys():
                call_graph_forest.add_graph(function_name, function_node)  # We save the tree in the forest by the name of the root function

            # Default case where a function calls no other functions in its body - therefore the tree has just one node
            if not function_scope.calls:
                continue

            # If the function calls other functions in its body we need to build a tree
            else:
                for call in function_scope.calls:
                    if call.symbol.name in functions.keys():
                        current_tree_node = call_graph_forest.get_graph(function_name)

                        # We need to check if the called function is already in the tree
                        if call_graph_forest.get_graph(call.symbol.name):
                            current_tree_node.add_child(call_graph_forest.get_graph(call.symbol.name))
                        # If the called function is not in the forest, we need to compute it first and then connect it to the current tree
                        else:
                            for called_function_scope in functions[call.symbol.name]:
                                if function_references[call.symbol.name]:
                                    call_graph_forest.add_graph(call.symbol.name, CallGraphNode(data=called_function_scope, reasons=function_references[call.symbol.name]))
                                else:
                                    call_graph_forest.add_graph(call.symbol.name, CallGraphNode(data=called_function_scope))
                                current_tree_node.add_child(call_graph_forest.get_graph(call.symbol.name))

                    # Handle builtins: builtins are not in the functions dict, and therefore we need to handle them separately
                    # since we do not analyze builtins any further at this stage, we can simply add them as a child to the current tree node
                    elif call.symbol.name in BUILTINS:
                        current_tree_node = call_graph_forest.get_graph(function_name)
                        current_tree_node.add_child(CallGraphNode(call))

                    else:  # TODO: what if the function is not in the functions dict?
                           #  -> this scenario happens when the function is external code or parameter call
                           #  These functions will get an unknown flag
                        current_tree_node.add_child(CallGraphNode())

    handle_cycles(call_graph_forest, function_references)

    return call_graph_forest


def handle_cycles(call_graph_forest: CallGraphForest, function_references: dict[str, Reasons]) -> CallGraphForest:
    """Handles cycles in the call graph.

    This function checks for cycles in the call graph forest and contracts them into a single node.

    Parameters
    ----------
        * call_graph_forest: the call graph forest
        * function_references: a dict of function references - contains the reasons for impurity

    Returns
    -------
        * call_graph_forest: the call graph forest with contracted cycles
    """

    for name, graph in call_graph_forest.graphs.copy().items():
        visited_nodes = set()
        path = []
        cycle = test_for_cycles(graph, visited_nodes, path)
        if cycle:
            print("cycle found", cycle)
            contract_cycle(call_graph_forest, cycle, function_references)
            # TODO: check if other cycles exists
        else:
            print("no cycles found")

    return call_graph_forest


def test_for_cycles(graph: CallGraphNode, visited_nodes: set, path: list) -> list[CallGraphNode]:
    """Tests for cycles in the call graph.

    This function recursively traverses the call graph and checks for cycles.
    It uses a DFS approach to traverse the graph.
    If a cycle is found, the cycle is returned.
    It is possible that multiple cycles exist, but only one is returned.

    Parameters
    ----------
        * graph: the current node in the call graph
        * visited_nodes: a set of all visited nodes
        * path: a list of all nodes in the current path
    """

    # If a node has no children, it is a leaf node, and we can return an empty list
    if not graph.children:
        return []

    if graph in path:
        return path[path.index(graph):]  # A cycle is found, return the path

    # Mark the current node as visited
    visited_nodes.add(graph)
    path.append(graph)

    cycle = []

    # Check for cycles in children
    for child in graph.children:
        cycle = test_for_cycles(child, visited_nodes, path)
        if cycle:
            return cycle
    path.pop()  # Remove the current node from path when backtracking

    return cycle


def contract_cycle(forest: CallGraphForest, cycle: list[CallGraphNode], function_references: dict[str, Reasons]) -> None:
    """Contracts a cycle in the call graph.

    Given a cycle in the call graph, this function contracts the cycle into a single node.

    Parameters
    ----------
        * forest: the call graph forest
        * cycle: a list of nodes in the cycle
        * function_references: a dict of function references - contains the reasons for impurity
    """
    # Create the new combined node
    cycle_names = [node.data.symbol.name for node in cycle]
    combined_node_name = ".".join(sorted(cycle_names))  # TODO: +
    combined_node_data = FunctionScope(Symbol("", "", combined_node_name))  # TODO: what do we use for the other parameters? - make them none
    combined_reasons = Reasons.join_reasons_list([node.reasons for node in cycle])
    combined_node = CallGraphNode(data=combined_node_data, reasons=combined_reasons)

    # Add children to combined node if they are not in the cycle (other calls)
    if any([isinstance(node.data, FunctionScope) and hasattr(node.data, 'calls') for node in cycle]):
        other_calls = [call for node in cycle for call in node.data.calls if call.symbol.name not in cycle_names]
        combined_node_data.calls = other_calls
        combined_node.children = [CallGraphNode(data=call, reasons=function_references[call.symbol.name]) for call in other_calls]

    # Remove all nodes in the cycle from the forest and add the combined node instead
    for node in cycle:
        if node.data.symbol.name in BUILTINS:
            continue  # This should not happen since builtins never call self defined functions
        if node.data.symbol.name in forest.graphs.keys():
            forest.delete_graph(node.data.symbol.name)

    # Only add the combined node once - (it is possible that the same cycle is found multiple times)
    if combined_node_name not in forest.graphs.keys():
        forest.add_graph(combined_node_name, combined_node)

    # Set all pointers to the nodes in the cycle to the combined node
    for node_name, graph in forest.graphs.items():
        update_pointers(graph, cycle_names, combined_node)


def update_pointers(node: CallGraphNode, cycle: list[str], combined_node: CallGraphNode) -> None:
    """Replaces all pointers to nodes in the cycle with the combined node.

    Recursively traverses the tree and replaces all pointers to nodes in the cycle with the combined node.

    Parameters
    ----------
        * node: the current node in the tree
        * cycle: a list of all names of nodes in the cycle
        * combined_node: the combined node that replaces all nodes in the cycle
    """
    for child in node.children:
        if child.data.symbol.name in BUILTINS:
            continue
        if child.data.symbol.name in cycle:
            node.children.remove(child)
            node.children.add(combined_node)
            # Update data
            if isinstance(node.data, FunctionScope):
                node.data.remove_call_node_by_name(child.data.symbol.name)
                node.data.calls.append(combined_node.data)
            # Remove the call from the reasons (reasons need to be updated later)
            for call in node.reasons.calls.copy():
                if call.node.func.name == child.data.symbol.name:
                    node.reasons.calls.remove(call)

        else:
            update_pointers(child, cycle, combined_node)
