import builtins

from library_analyzer.processing.api.purity_analysis.model import FunctionScope, CallGraphNode, CallGraphForest, Symbol

BUILTINS = dir(builtins)


def build_call_graph(functions: dict[str, list[FunctionScope]]) -> CallGraphForest:
    global BUILTINS

    current_tree_node = CallGraphNode()
    call_graph_forest = CallGraphForest()

    for function_name, function_scope in functions.items():
        # TODO: how do we deal with functions with the same name?
        #  - use a loop to add all of them to the tree but add a warning to indicate this inaccuracy
        # right now we use the first one we find
        function_scope = function_scope[0]
        function_node = CallGraphNode(data=function_scope)

        # case where the function is not called before by any other function
        if function_name not in call_graph_forest.graphs.keys():
            call_graph_forest.add_graph(function_name, function_node)  # we save the tree in the forest by the name of the root function call

        # default case where a function calls no other functions in its body - therefore the tree has just one node
        if not function_scope.calls:
            continue

        # if the function calls other functions in its body we need to build a tree
        else:
            for call in function_scope.calls:
                if call.symbol.name in functions.keys():
                    current_tree_node = call_graph_forest.get_graph(function_name)

                    # we need to check if the called function is already in the tree
                    if call_graph_forest.get_graph(call.symbol.name):
                        current_tree_node.add_child(call_graph_forest.get_graph(call.symbol.name))
                    # if the called function is not in the tree we need to compute it first and then connect it to the current tree
                    else:
                        call_graph_forest.add_graph(call.symbol.name, CallGraphNode(functions[call.symbol.name][0]))
                        current_tree_node.add_child(call_graph_forest.get_graph(call.symbol.name))

                # handle builtins: builtins are not in the functions dict and therefore we need to handle them separately
                # since we do not analyse builtins any further at this stage, we can simply add them as a child to the current tree node
                elif call.symbol.name in BUILTINS:
                    current_tree_node = call_graph_forest.get_graph(function_name)
                    current_tree_node.add_child(CallGraphNode(call))

                else:  # TODO: what if the function is not in the functions dict?
                       #  -> this scenario happens when the function is external code or parameter call
                    current_tree_node.add_child(CallGraphNode())

    handle_cycles(call_graph_forest)

    return call_graph_forest


def handle_cycles(call_graph_forest: CallGraphForest) -> CallGraphForest:
    for name, graph in call_graph_forest.graphs.copy().items():
        visited_nodes = set()
        path = []
        cycle = test_for_cycles(graph, visited_nodes, path)
        if cycle:
            print("cycle found", cycle)
            contract_cycle(call_graph_forest, cycle)
            # TODO: check if other cycles exists
        else:
            print("no cycles found")

    return call_graph_forest


def test_for_cycles(graph: CallGraphNode, visited_nodes: set, path: list) -> list[CallGraphNode]:
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


def contract_cycle(forest: CallGraphForest, cycle: list[CallGraphNode]):
    # Create the new combined node
    cycle_names = [node.data.symbol.name for node in cycle]
    combined_node_name = ".".join(sorted(cycle_names))
    combined_node_data = FunctionScope(Symbol("", "", combined_node_name))  # TODO: what do we use for the other parameters?
    combined_node = CallGraphNode(combined_node_data)

    # Add children to combined node if they are not in the cycle (other calls)
    if any([isinstance(node.data, FunctionScope) and hasattr(node.data, 'calls') for node in cycle]):
        other_calls = [call for node in cycle for call in node.data.calls if call.symbol.name not in cycle_names]
        combined_node_data.calls = other_calls
        combined_node.children = [CallGraphNode(call) for call in other_calls]

    # Remove all nodes in the cycle from the forest and add the combined node instead
    for node in cycle:
        if node.data.symbol.name in BUILTINS:
            continue
        if node.data.symbol.name in forest.graphs.keys():
            forest.delete_graph(node.data.symbol.name)
    if combined_node_name not in forest.graphs.keys():
        forest.add_graph(combined_node_name, combined_node)

    # Set all pointers to the nodes in the cycle to the combined node
    for node_name, graph in forest.graphs.items():
        update_pointers(graph, cycle_names, combined_node)


def update_pointers(node: CallGraphNode, cycle: list[str], combined_node: CallGraphNode):
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

        else:
            update_pointers(child, cycle, combined_node)
