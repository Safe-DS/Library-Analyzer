from library_analyzer.processing.api.purity_analysis.model import FunctionScope, CallGraphNode, CallGraphForest

# lookup table for nodes that are not yet in the tree: key = function name, value = node which we need to update later
NODE_LOOKUP: dict[str, CallGraphNode] = {}


def build_call_graph(functions: dict[str, list[FunctionScope]]) -> CallGraphForest:
    global NODE_LOOKUP

    current_tree_node = CallGraphNode()
    call_graph_forest = CallGraphForest()

    for function_name, function_scope in functions.items():
        # TODO: how do we deal with functions with the same name?
        # right now we use the first one we find
        function_scope = function_scope[0]
        function_node = CallGraphNode(data=function_scope)

        if function_name not in call_graph_forest.trees.keys():
            call_graph_forest.add_tree(function_name, function_node) # we save the tree in the forest by the name of the root function call

        # default case where a function calls no other functions in its body - therefore the tree has just one node
        if not function_scope.calls:
            continue

        # if the function calls other functions in its body we need to build a tree
        else:
            for call in function_scope.calls:
                if call.symbol.name in functions.keys():
                    current_tree_node = call_graph_forest.get_tree(function_name)

                    # we need to check if the called function is already in the tree
                    if call_graph_forest.get_tree(call.symbol.name):
                        current_tree_node.add_child(call_graph_forest.get_tree(call.symbol.name))
                    # if the called function is not in the tree we need to compute it first and then connect it to the current tree
                    else:

                        # since we don't have the children for this node yet, we need to save it in a lookup table
                        # current_tree_node.missing_children = True
                        # NODE_LOOKUP[call.symbol.name] = current_tree_node
                        # current_tree_node.add_child(CallGraphNode(data=functions[call.symbol.name][0]))

                        call_graph_forest.add_tree(call.symbol.name, CallGraphNode(functions[call.symbol.name][0]))
                        current_tree_node.add_child(call_graph_forest.get_tree(call.symbol.name))


                else:  # TODO: what if the function is not in the functions dict?
                       #  -> this scenario happens when the function is a builtin function or external code or parameter call
                    current_tree_node.add_child(CallGraphNode())

        # if the function is in the lookup table we can now update the tree with the children
        # if function_name in NODE_LOOKUP.keys():
        #
        #     try:
        #         del NODE_LOOKUP[function_name]
        #     except KeyError:  # this should never happen
        #         pass

    return call_graph_forest
