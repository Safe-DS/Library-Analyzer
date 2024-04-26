from library_analyzer.processing.api.purity_analysis.model import (
    Builtin,
    CallGraphForest,
    CallGraphNode,
    ClassScope,
    CombinedCallGraphNode,
    CombinedSymbol,
    Import,
    ImportedCallGraphNode,
    NodeID,
    Parameter,
    Reasons,
    Symbol,
)


class CallGraphBuilder:
    """Class for building a call graph.

    This class is used to build a call graph forest for a module from a dict of Reasons.

    Attributes
    ----------
    classes : dict[str, ClassScope]
        Classnames in the module as key and their corresponding ClassScope instance as value.
    raw_reasons : dict[NodeID, Reasons]
        The raw reasons for impurity for all functions.
        Keys are the ids of the functions.
    call_graph_forest : CallGraphForest
        The call graph forest for the given functions.
    visited : set[NodeID]
        A set of all visited nodes.

    Parameters
    ----------
    classes : dict[str, ClassScope]
        Classnames in the module as key and their corresponding ClassScope instance as value.
    raw_reasons : dict[NodeID, Reasons]
        The raw reasons for impurity for all functions.
        Keys are the ids of the functions.
    """

    def __init__(
        self,
        classes: dict[str, ClassScope],
        raw_reasons: dict[NodeID, Reasons],
    ) -> None:
        self.classes = classes
        self.raw_reasons = raw_reasons
        self.call_graph_forest = CallGraphForest()
        self.visited: set[NodeID] = set()

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
            if (
                self.call_graph_forest.has_graph(reason.id)
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
            class_cgn = CallGraphNode(symbol=klass.symbol, reasons=Reasons(klass.symbol.id))
            # If the class has a __new__, __init__ or __post_init__ function, add it to the class node as a child.
            # Also add the init function to the forest if it is not already there.
            if klass.new_function:
                new_cgn = CallGraphNode(
                    symbol=klass.new_function.symbol,
                    reasons=self.raw_reasons[klass.new_function.symbol.id],
                )
                self.call_graph_forest.add_graph(klass.new_function.symbol.id, new_cgn)
                class_cgn.add_child(new_cgn)
            if klass.init_function:
                init_cgn = CallGraphNode(
                    symbol=klass.init_function.symbol,
                    reasons=self.raw_reasons[klass.init_function.symbol.id],
                )
                self.call_graph_forest.add_graph(klass.init_function.symbol.id, init_cgn)
                class_cgn.add_child(init_cgn)
            if klass.post_init_function:
                post_init_cgn = CallGraphNode(
                    symbol=klass.post_init_function.symbol,
                    reasons=self.raw_reasons[klass.post_init_function.symbol.id],
                )
                self.call_graph_forest.add_graph(klass.post_init_function.symbol.id, post_init_cgn)
                class_cgn.add_child(post_init_cgn)

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
        # If the node has already been visited, return
        if reason.id in self.visited:
            return

        # Mark the current node as visited
        self.visited.add(reason.id)

        # If the node is already inside the forest and does not have any calls left, it is considered to be finished.
        if self.call_graph_forest.has_graph(reason.id) and not reason.calls:
            return

        # Create a new node and add it to the forest.
        cgn = CallGraphNode(
            symbol=reason.function_scope.symbol,  # type: ignore[union-attr] # function_scope is never None here
            reasons=reason,
        )
        self.call_graph_forest.add_graph(reason.id, cgn)

        # The node has calls, which need to be added to the forest and to the children of the current node.
        # They are sorted to ensure a deterministic order of the children (especially but not only for testing).
        sorted_calls = sorted(cgn.reasons.calls, key=lambda x: x.id)
        for call in sorted_calls:
            if call in self.call_graph_forest.get_graph(reason.id).reasons.calls:
                self.call_graph_forest.get_graph(reason.id).reasons.calls.remove(call)
            if isinstance(call, Builtin):
                builtin_cgn = CallGraphNode(symbol=call, reasons=Reasons(call.id))
                self.call_graph_forest.get_graph(reason.id).add_child(builtin_cgn)

            # Check if the called child function is already in the forest and has no calls left to deal with.
            elif (
                self.call_graph_forest.has_graph(call.id)
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
            )
            self.call_graph_forest.add_graph(call.id, imported_cgn)
            self.call_graph_forest.get_graph(reason_id).add_child(self.call_graph_forest.get_graph(call.id))

            # If the call was used as a member of an MemberAccessValue, it needs to be removed from the unknown_calls.
            # This is due to the improved analysis that can determine the module through the receiver of that call.
            # Hence, the call is handled as a call of an imported function and not as an unknown_call
            # when inferring the purity later.
            for unknown_call in self.call_graph_forest.get_graph(reason_id).reasons.unknown_calls:
                if unknown_call.node == call.call:
                    (
                        self.call_graph_forest.get_graph(reason_id).reasons.remove_unknown_call(
                            NodeID.calc_node_id(call.call),
                        )
                    )

        # Deal with the case that the call calls a function parameter.
        elif isinstance(call, Parameter):
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
        for graph in self.call_graph_forest.graphs.copy().values():
            if graph.symbol.id in removed_nodes or all(
                child.symbol.id in removed_nodes for child in graph.children.values()
            ):
                continue

            cycle = self._test_cgn_for_cycles(graph)
            if cycle:
                self._contract_cycle(cycle)
                removed_nodes.update(cycle.keys())

    def _test_cgn_for_cycles(
        self,
        cgn: CallGraphNode,
        visited_nodes: set[CallGraphNode] | None = None,
        path: list[NodeID] | None = None,
    ) -> dict[NodeID, CallGraphNode]:
        """Test for cycles in the call graph.

        Recursively traverses the call graph and checks for cycles.
        It uses a DFS approach to traverse the graph.
        If a cycle is found, a dict of all nodes in the cycle is returned.

        Parameters
        ----------
        cgn : CallGraphNode
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
            cut_path = path[path.index(cgn.symbol.id) :]
            return {node_id: self.call_graph_forest.get_graph(node_id) for node_id in cut_path}

        # If a node has no children, it is a leaf node, and an empty list is returned.
        if not cgn.children:
            return {}

        # Mark the current node as visited.
        visited_nodes.add(cgn)
        path.append(cgn.symbol.id)

        cycle: dict[NodeID, CallGraphNode] = {}

        # Check for cycles in children.
        for child in cgn.children.values():
            cycle = self._test_cgn_for_cycles(child, visited_nodes, path)
            if cycle:
                return cycle
        # Remove the current node from the path when backtracking.
        path.pop()

        return cycle

    def _contract_cycle(self, cycle: dict[NodeID, CallGraphNode]) -> None:
        """Contract a cycle in the call graph.

        Contracts a cycle in the call graph into a single node.
        Therefore, creates a new CombinedCallGraphNode out of all nodes in the cycle and adds it to the forest.

        Parameters
        ----------
        cycle : dict[NodeID, CallGraphNode]
            A dict of all nodes in the cycle.
            Keys are the NodeIDs of the CallGraphNodes.
        """
        # Create the new combined node.
        combined_name = "+".join(sorted(c.__str__() for c in cycle))
        module = (
            next(iter(cycle.values())).symbol.node.root().name
            if (next(iter(cycle.values())).symbol.node and next(iter(cycle.values())).symbol.node.root().name != "")
            else None
        )
        combined_id = NodeID(module, combined_name)
        combined_reasons = Reasons(id=combined_id).join_reasons_list([node.reasons for node in cycle.values()])
        combined_cgn = CombinedCallGraphNode(
            symbol=CombinedSymbol(
                node=None,
                id=combined_id,
                name=combined_name,
            ),
            reasons=combined_reasons,
        )
        combines: dict[NodeID, CallGraphNode] = {}
        # Check if the combined node is already in the forest.
        if self.call_graph_forest.has_graph(combined_cgn.symbol.id):
            return

        # Find all other calls (calls that are not part of the cycle) and remove all nodes in the cycle from the forest.
        for node in cycle.values():
            for child in node.children.values():
                if child.symbol.id not in cycle and not combined_cgn.has_child(child.symbol.id):
                    combined_cgn.add_child(child)
            self.call_graph_forest.delete_graph(node.symbol.id)

            if isinstance(node, CombinedCallGraphNode):
                combines.update(node.combines)
            else:
                combines[node.symbol.id] = node
        combined_cgn.combines = combines

        # Add the combined node to the forest.
        self.call_graph_forest.add_graph(combined_id, combined_cgn)

        # Set all pointers from nodes calling the nodes in the cycle to the combined node.
        self._update_pointers(cycle, combined_cgn)

    def _update_pointers(self, cycle: dict[NodeID, CallGraphNode], combined_node: CombinedCallGraphNode) -> None:
        """Replace all pointers to nodes inside the cycle with pointers to the combined node.

        Traverses the tree and replaces all pointers to nodes in the cycle with pointers to the combined node.

        Parameters
        ----------
        cycle : dict[NodeID, CallGraphNode]
            A dict of all nodes in the cycle.
            Keys are the NodeIDs of the nodes.
        combined_node : CombinedCallGraphNode
            The combined node that replaces all nodes in the cycle.
        """
        for graph in self.call_graph_forest.graphs.values():
            for child in graph.children.copy().values():
                if child.symbol.id in cycle:
                    graph.delete_child(child.symbol.id)
                    graph.add_child(combined_node)


def build_call_graph(classes: dict[str, ClassScope], raw_reasons: dict[NodeID, Reasons]) -> CallGraphForest:
    """Build the call graph forest for the given classes and reasons.

    Parameters
    ----------
    classes : dict[str, ClassScope]
        Classnames in the module as key and their corresponding ClassScope instance as value.
    raw_reasons : dict[NodeID, Reasons]
        The raw reasons for impurity for all functions.
        Keys are the ids of the functions.

    Returns
    -------
    call_graph_forest : CallGraphForest
        The call graph forest for the given functions.
    """
    return CallGraphBuilder(classes, raw_reasons).call_graph_forest
