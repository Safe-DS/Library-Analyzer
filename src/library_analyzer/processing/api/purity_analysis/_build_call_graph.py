import builtins

import astroid

from library_analyzer.processing.api.purity_analysis.model import (
    CallGraphForest,
    CallGraphNode,
    ClassScope,
    FunctionReference,
    FunctionScope,
    NodeID,
    Reasons,
    Symbol,
)

BUILTINS = dir(builtins)


def build_call_graph(
    functions: dict[str, list[FunctionScope]],
    classes: dict[str, ClassScope],
    function_references: dict[NodeID, Reasons],
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
    function_references : dict[str, Reasons]
        All nodes relevant for reference resolving inside functions.

    Returns
    -------
    call_graph_forest : CallGraphForest
        The call graph forest for the given functions.
    """
    call_graph_forest = CallGraphForest()
    classes_and_functions = {**classes, **functions}

    for function_scopes in classes_and_functions.values():
        # Inner for loop is needed to handle multiple function defs with the same name
        for function_scope in function_scopes:
            # Add reasons for impurity to the corresponding function
            function_id = function_scope.symbol.id
            if isinstance(function_scope, ClassScope):
                function_node = CallGraphNode(data=function_scope, reasons=Reasons())
            elif function_references[function_id]:
                function_node = CallGraphNode(data=function_scope, reasons=function_references[function_id])
            else:
                function_node = CallGraphNode(data=function_scope, reasons=Reasons())

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
                                    CallGraphNode(data=init_function, reasons=Reasons()),
                                )
                            function_node.add_child(call_graph_forest.get_graph(init_function.symbol.id))
                            function_node.reasons.calls.add(FunctionReference(function_references[init_function.symbol.id].function, "Call"))
                            break
                continue

            # Default case where a function calls no other functions in its body - therefore, the tree has just one node
            if not function_scope.calls:
                continue

            # If the function calls other functions in its body, we need to build a tree
            else:
                for call in function_scope.calls.values():
                    # Handle self defined function calls
                    if call.symbol.name in classes_and_functions:
                        # Check if any function def has the same name as the called function
                        matching_function_defs = [called_function for called_function in classes_and_functions[call.symbol.name] if called_function.symbol.name == call.symbol.name]
                        current_tree_node = call_graph_forest.get_graph(function_id)
                        break_condition = False  # This is used to indicate that one or more functions defs was found inside the forest which match the called function name

                        # We need to check if the called function is already in the tree
                        for f in matching_function_defs:
                            if call_graph_forest.get_graph(f.symbol.id):
                                current_tree_node.add_child(call_graph_forest.get_graph(f.symbol.id))
                                break_condition = True  # We found a function def inside the forest so the following else statement must not be executed

                        if break_condition:
                            pass  # Skip the else statement because the function def is already in the forest

                        # If the called function is not in the forest, we need to compute it first and then connect it to the current tree
                        else:
                            for called_function_scope in classes_and_functions[call.symbol.name]:
                                # Check if any function def has the same name as the called function
                                matching_function_defs = [called_function for called_function in classes_and_functions[call.symbol.name] if called_function.symbol.name == call.symbol.name]
                                # TODO: check if this is correct
                                for f in matching_function_defs:
                                    if function_references[f.symbol.id]:
                                        call_graph_forest.add_graph(
                                            f.symbol.id,
                                            CallGraphNode(
                                                data=called_function_scope,
                                                reasons=function_references[f.symbol.id],
                                            ),
                                        )
                                    else:
                                        call_graph_forest.add_graph(
                                            f.symbol.id,
                                            CallGraphNode(data=called_function_scope, reasons=Reasons()),
                                        )
                                    current_tree_node.add_child(call_graph_forest.get_graph(f.symbol.id))

                    # Handle builtins: builtins are not in the functions dict, and therefore we need to handle them separately
                    # Since we do not analyze builtins any further at this stage, we can simply add them as a child to the current tree node
                    # Because a builtin function has no real function def, we will use the call node as the function def - hence its id is always wrong
                    elif call.symbol.name in BUILTINS or call.symbol.name in ("read", "readline", "readlines", "write", "writelines"):
                        current_tree_node = call_graph_forest.get_graph(function_id)
                        current_tree_node.add_child(CallGraphNode(data=call, reasons=Reasons()))

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
                            current_tree_node.reasons.unknown_calls.append(call.symbol.node)

    handle_cycles(call_graph_forest, function_references, functions)

    return call_graph_forest


def handle_cycles(call_graph_forest: CallGraphForest, function_references: dict[NodeID, Reasons], functions: dict[str, list[FunctionScope]]) -> CallGraphForest:
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
        return path[path.index(graph) :]  # A cycle is found, return the path containing the cycle

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
    cycle_ids = [node.data.symbol.id.__str__() for node in cycle]
    cycle_names = [node.data.symbol.name for node in cycle]
    combined_node_name = "+".join(sorted(cycle_ids))
    combined_node_data = FunctionScope(
        Symbol(
            None,
            NodeID(None, combined_node_name),
            combined_node_name,
        ),
    )
    combined_reasons = Reasons.join_reasons_list([node.reasons for node in cycle], combined_node_name)
    combined_node = CallGraphNode(data=combined_node_data, reasons=combined_reasons, combined_node_names=cycle_ids)

    # Add children to the combined node if they are not in the cycle (other calls)
    if any([isinstance(node.data, FunctionScope) and hasattr(node.data, "calls") for node in cycle]):  # noqa: C419
        other_calls = [
            call
            for node in cycle
            for call in node.data.calls.values()
            if call.symbol.name not in cycle_names and call.symbol.name not in BUILTINS
        ]
        # Find all function definitions that match the other call names for each call
        matching_function_defs = {}
        for call in other_calls:
            matching_function_defs[call.symbol.name] = [called_function for called_function in functions[call.symbol.name] if called_function.symbol.name == call.symbol.name]

        # Find all builtin calls
        builtin_calls = [call for node in cycle for call in node.data.calls.values() if call.symbol.name in BUILTINS]

        # Add the calls as well as the children of the function defs to the combined node
        combined_node_data.calls = other_calls + builtin_calls
        combined_node.children = {
            CallGraphNode(data=matching_function_defs[call.symbol.name][i], reasons=function_references[matching_function_defs[call.symbol.name][i].symbol.id])
            for call in other_calls
            for i in range(len(matching_function_defs[call.symbol.name]))
        }  # Add the function def (list of function defs) as children to the combined node if the a function def name matches the call name
        combined_node.children.update({CallGraphNode(data=call, reasons=Reasons()) for call in builtin_calls})

    # Remove all nodes in the cycle from the forest and add the combined node instead
    for node in cycle:
        if node.data.symbol.name in BUILTINS:
            continue  # This should not happen since builtins never call self-defined functions
        if node.data.symbol.id in forest.graphs:
            forest.delete_graph(node.data.symbol.id)

    # Only add the combined node once - (it is possible that the same cycle is found multiple times)
    if combined_node_name not in forest.graphs:
        forest.add_graph(combined_node.data.symbol.id, combined_node)

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
        if child.data.symbol.name in BUILTINS:
            continue
        if child.data.symbol.id.__str__() in cycle_names:
            node.children.remove(child)
            node.children.add(combined_node)
            # Update data
            if isinstance(node.data, FunctionScope):
                node.data.remove_call_node_by_name(child.data.symbol.name)
                node.data.calls.update({combined_node.data.symbol.name: combined_node.data})
            # Remove the call from the reasons (reasons need to be updated later)
            if isinstance(node.reasons, Reasons):
                for call in node.reasons.calls.copy():
                    if isinstance(call.node, astroid.Call) and call.node.func.name == child.data.symbol.name:
                        node.reasons.calls.remove(call)

        else:
            update_pointers(child, cycle_names, combined_node)
