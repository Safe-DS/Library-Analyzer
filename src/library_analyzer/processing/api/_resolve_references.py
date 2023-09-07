from __future__ import annotations

import astroid
import builtins

from library_analyzer.processing.api._get_module_data import _get_module_data  # Todo: can we import from .api?
from library_analyzer.processing.api.model import (
    MemberAccessTarget,
    MemberAccessValue,
    NodeID,
    Symbol,
    Scope,
    ClassScope,
    Builtin,
    ReferenceNode,
)


# def get_scope_node_by_node_id(scope: Scope | list[Scope], targeted_node_id: NodeID,
#                               name_nodes: dict[astroid.Name, Scope | ClassScope] | None) -> Scope | ClassScope:
#     # TODO: implement a dfs search for the node (or an other quicker search algorithm)
#     if name_nodes is None:
#         for node in scope:
#             if node.symbol.id == targeted_node_id:
#                 return node
#             else:
#                 found_node = get_scope_node_by_node_id(node.children, targeted_node_id, None)
#                 if found_node is not None:
#                     return found_node
#
#     else:
#         for name in name_nodes.keys():
#             name_id = _calc_node_id(name)
#             if name_id == targeted_node_id:
#                 return name_nodes.get(name)


def _create_unspecified_references(target_nodes: dict[astroid.AssignName | astroid.Name | MemberAccessTarget, Scope | ClassScope],
                                   value_nodes: dict[astroid.Name | MemberAccessValue, Scope | ClassScope],
                                   scope: Scope,
                                   classes: dict[str, ClassScope],
                                   functions: dict[str, Scope | list[Scope]]) -> list[ReferenceNode]:
    """Create a list of references from a list of name nodes.

    Returns:
        * final_references: contains all references that are used as targets
    """
    final_references: list[ReferenceNode] = []

    # TODO: is it possible to do this in a more efficient way?
    target_references = [ReferenceNode(node, scope, []) for node, scope in target_nodes.items()]
    value_references = [ReferenceNode(node, scope, []) for node, scope in value_nodes.items()]

    # scope_node: Scope | None = field(default_factory=Callable[[], Scope])
    #
    # for name in all_names_list:
    #     node_id = _calc_node_id(name)
    #     if isinstance(name, astroid.AssignName):
    #         scope_node = get_scope_node_by_node_id(scope, node_id, None)
    #         target_references.append(ReferenceNode(name, scope_node, []))
    #     elif isinstance(name, astroid.Name):
    #         scope_node = get_scope_node_by_node_id(scope, node_id, name_nodes)
    #         value_references.append(ReferenceNode(name, scope_node, []))
    #     elif isinstance(name, MemberAccess):
    #         scope_node = get_scope_node_by_node_id(scope, node_id, name_nodes)
    #         value_references.append(ReferenceNode(name, scope_node, []))

    for value_ref in value_references:
        if isinstance(value_ref.node, astroid.Name | MemberAccessValue):
            target_ref = _find_references(value_ref, target_references, classes, functions)
            final_references.append(target_ref)

    return final_references


def _find_references(value_reference: ReferenceNode,
                     all_target_list: list[ReferenceNode],
                     classes: dict[str, ClassScope],
                     functions: dict[str, Scope | list[Scope]]) -> ReferenceNode:
    """ Find all references for a node.

    Finds all references for a node in a list of references and adds them to the list of referenced_symbols of the node.

    Parameters:
        * value_reference: the node for which we want to find all references
        * all_target_list: a list of target references in the module
        * classes: a list of all classes in the module
    """
    complete_reference = value_reference
    for ref in all_target_list:
        if ref.node.name == value_reference.node.name:
            complete_reference.referenced_symbols = list(set(complete_reference.referenced_symbols) | set(_get_symbols(ref)))
        if isinstance(value_reference.node, MemberAccessValue):
            if ref.node.name == value_reference.node.member.attrname:
                complete_reference.referenced_symbols = list(set(complete_reference.referenced_symbols) | set(_get_symbols(ref)))

            # Add InstanceVariables if the name of the MemberAccessValue is the same as the name of the InstanceVariable
            elif isinstance(ref.node, MemberAccessTarget) and isinstance(value_reference.node, MemberAccessValue):
                if ref.node.member.attrname == value_reference.node.member.attrname:
                    complete_reference.referenced_symbols = list(set(complete_reference.referenced_symbols) | set(_get_symbols(ref)))

    if classes:
        for klass in classes.values():
            if klass.symbol.node.name == value_reference.node.name:
                complete_reference.referenced_symbols.append(klass.symbol)
                break

    # Find functions that are passed as arguments to other functions (and therefor are not called directly)
    if functions:
        if value_reference.node.name in functions.keys():
            func = functions.get(value_reference.node.name)
            complete_reference.referenced_symbols.append(func.symbol)

    return complete_reference


def _get_symbols(node: ReferenceNode) -> list[Symbol]:
    refined_symbol: list[Symbol] = []
    current_scope = node.scope

    for child in current_scope.children:
        if child.symbol.node.name == node.node.name:
            refined_symbol.append(child.symbol)

    return refined_symbol

# def _add_target_references(target_reference: ReferenceNode,
#                            reference_list: list[ReferenceNode],
#                            classes: dict[str, ClassScope],
#                            functions: dict[str, Scope | ClassScope]) -> ReferenceNode:
#     """Add all target references to a reference.
#
#     A target reference is a reference where the name is used as a target.
#     Therefor we need to check all nodes further up the list where the name is used as a target.
#     """
#     complete_reference = target_reference
#     if target_reference in reference_list:
#         for ref in reference_list:
#             # for ref in reference_list[:reference_list.index(reference)]:
#             if isinstance(ref.name, MemberAccessValue):
#                 root = ref.scope.root()
#                 if isinstance(root.symbol.node, astroid.Module):
#                     for class_scope in classes.values():
#                         for variable in class_scope.class_variables:
#                             if isinstance(target_reference.name, MemberAccessValue):
#                                 if isinstance(target_reference.name.member, astroid.Attribute | astroid.AssignAttr) and target_reference.name.member.attrname == variable.name:
#                                     if ref.scope.symbol not in complete_reference.referenced_symbols:
#                                         complete_reference.referenced_symbols.append(ref.scope.symbol)
#                                 elif not isinstance(target_reference.name.member, astroid.Attribute | astroid.AssignAttr) and target_reference.name.member.name == variable.name:
#                                     if ref.scope.symbol not in complete_reference.referenced_symbols:
#                                         complete_reference.referenced_symbols.append(ref.scope.symbol)
#
#                         for variable in class_scope.instance_variables:
#                             if isinstance(target_reference.name, MemberAccessValue):
#                                 if isinstance(target_reference.name.member, astroid.Attribute | astroid.AssignAttr) and target_reference.name.member.attrname == variable.attrname:
#                                     if ref.scope.symbol not in complete_reference.referenced_symbols:
#                                         complete_reference.referenced_symbols.append(ref.scope.symbol)
#                                 elif not isinstance(target_reference.name.member, astroid.Attribute | astroid.AssignAttr) and target_reference.name.member.name == variable.attrname:
#                                     if ref.scope.symbol not in complete_reference.referenced_symbols:
#                                         complete_reference.referenced_symbols.append(ref.scope.symbol)
#
#             elif isinstance(ref.name, MemberAccessTarget) and isinstance(target_reference.name, MemberAccessValue):
#                 if ref.name.name == target_reference.name.name:
#                     complete_reference.referenced_symbols.append(ref.scope.symbol)
#
#             elif isinstance(ref.name, astroid.AssignName) and ref.name.name == target_reference.name.name:
#                 complete_reference.referenced_symbols.append(ref.scope.symbol)
#
#             # this detects functions that are passed as arguments to other functions (and therefor are not called)
#             elif ref.name.name in functions.keys() and ref.name.name == target_reference.name.name:
#                 complete_reference.referenced_symbols.append(ref.scope.symbol)
#
#             elif isinstance(ref.name, astroid.Name) and isinstance(target_reference.name, astroid.Name):
#                 if ref.name.name in classes.keys() and ref.name.name == target_reference.name.name:
#                     if ref.scope.symbol not in complete_reference.referenced_symbols:
#                         complete_reference.referenced_symbols.append(ref.scope.symbol)
#
#     return complete_reference
#
#
# def _find_references(name_node: astroid.Name,
#                      references: list[ReferenceNode],
#                      module_data: ModuleData) -> list[ReferenceNode]:
#     """Find all references for a node.
#
#     Parameters:
#     * name_node: the node for which we want to find all references
#     * all_name_nodes_list: a list of all name nodes in the module
#     * module_data: the data of the module
#     """
#
#     for i, ref in enumerate(references):
#         if isinstance(ref.node or name_node, MemberAccess):
#             if ref.node.name == name_node.name:
#                 return [ref]
#         if ref.node == name_node:
#             return [ref]
#     return []
#
# #
# def _get_symbols(node: ReferenceNode,
#                  current_scope: Scope | ClassScope | None,
#                  function_parameters: dict[astroid.FunctionDef, tuple[Scope | ClassScope, list[astroid.AssignName]]],
#                  global_variables: dict[str, Scope | ClassScope]) -> ReferenceNode:
#     # wir können die Symbole bereits beim Erstellen des Scopes spezifizieren
#     try:
#         for i, symbol in enumerate(node.referenced_symbols):
#             if current_scope.children:
#                 for nod in current_scope.children:
#                     if isinstance(nod.node, MemberAccessTarget) and nod.node.name == symbol.name:
#                         parent_node = nod.parent
#                         specified_symbol = specify_symbols(parent_node, symbol, function_parameters)
#                         node.referenced_symbols[i] = specified_symbol
#
#                     elif isinstance(nod.node, astroid.AssignName) and nod.node.name == symbol.name:
#                         parent_node = nod.parent
#                         specified_symbol = specify_symbols(parent_node, symbol, function_parameters)
#                         node.referenced_symbols[i] = specified_symbol
#
#                 # if not isinstance(current_scope.parent, NoneType):
#                 #     return _get_symbols(node, current_scope.parent, function_parameters, global_variables)
#
#                 #  would fix: "for loop with local runtime variable local scope" but break other case
#             else:
#                 return _get_symbols(node, current_scope.parent, function_parameters, global_variables)
#             # TODO: ideally the functionality of the next block should be in the specify_symbols function
#             if symbol.name in global_variables.keys():
#                 current_symbol_parent = global_variables.get(symbol.name)
#                 if current_symbol_parent is not None:
#                     node.referenced_symbols[i] = GlobalVariable(symbol.node, symbol.id, symbol.name)
#         return node
#     except ChildProcessError:
#         raise ChildProcessError(f"Parent node {node.scope.node.name} of {node.name.name} does not have any (detected) children.")
#
#
# def specify_symbols(parent_node: Scope | ClassScope | None,
#                     symbol: Symbol,
#                     function_parameters: dict[
#                         astroid.FunctionDef, tuple[Scope | ClassScope, list[astroid.AssignName]]]) -> Symbol:
#     if isinstance(symbol, ClassVariable | InstanceVariable | Parameter | GlobalVariable):
#         return symbol
#     if isinstance(parent_node.node, astroid.Module):
#         return GlobalVariable(symbol.node, symbol.id, symbol.name)
#     elif isinstance(parent_node.node, astroid.ClassDef):
#         if parent_node.node:  # TODO: check if node is class attribute or instance attribute
#             return ClassVariable(symbol.node, symbol.id, symbol.name)
#         # if global_variables:
#         #     for key in global_variables.keys():
#         #         if key == symbol.name:
#         #             return GlobalVariable(symbol.node, symbol.id, symbol.name)
#     elif isinstance(parent_node.node, astroid.FunctionDef):
#         if parent_node.node in function_parameters.keys():
#             for param in function_parameters[parent_node.node][1]:
#                 if param.name == symbol.name:
#                     return Parameter(symbol.node, symbol.id, symbol.name)
#         if isinstance(symbol.node.parent.node, astroid.Module):
#             return GlobalVariable(symbol.node, symbol.id, symbol.name)
#
#         return LocalVariable(symbol.node, symbol.id, symbol.name)
#     elif isinstance(parent_node.node, astroid.Lambda):
#         return LocalVariable(symbol.node, symbol.id, symbol.name)
#     else:
#         return symbol


def _find_call_reference_new(function_calls: dict[astroid.Call, Scope | ClassScope],
                             classes: dict[str, ClassScope],
                             functions: dict[str, Scope | ClassScope],
                             parameters: dict[astroid.FunctionDef, tuple[Scope | ClassScope, list[astroid.AssignName]]]) -> list[ReferenceNode]:
    final_call_references: list[ReferenceNode] = []
    python_builtins = dir(builtins)

    call_references = [ReferenceNode(call, scope, []) for call, scope in function_calls.items()]

    for i, reference in enumerate(call_references):
        if isinstance(reference.node.func, astroid.Name):
            # Find functions that are called
            if reference.node.func.name in functions.keys():
                symbol = functions.get(reference.node.func.name)

                # If the Lambda function is assigned to a name, it can be called just as a normal function
                # therefore we need to add its assigned name manually
                if isinstance(functions.get(reference.node.func.name).symbol.node, astroid.Lambda):
                    symbol.symbol.name = reference.node.func.name

                call_references[i].referenced_symbols.append(symbol.symbol)
                final_call_references.append(call_references[i])

            # Find classes that are called (initialized)
            elif reference.node.func.name in classes.keys():
                symbol = classes.get(reference.node.func.name)
                call_references[i].referenced_symbols.append(symbol.symbol)
                final_call_references.append(call_references[i])

            # Find builtins that are called
            if reference.node.func.name in python_builtins:
                builtin_call = Builtin(reference.scope, NodeID("builtins", reference.node.func.name, 0, 0),
                                        reference.node.func.name)
                call_references[i].referenced_symbols.append(builtin_call)
                final_call_references.append(call_references[i])

            # Find function parameters that are called (passed as arguments), like:
            # def f(a):
            #     a()
            # For now: it is not possible to analyse this any further before runtime
            if parameters:
                for func_def, (scope, parameter_set) in parameters.items():
                    for param in parameter_set:
                        if reference.node.func.name == param.name and reference.scope.symbol.node == func_def:
                            for child in parameters.get(func_def)[0].children:
                                if child.symbol.node.name == param.name:
                                    call_references[i].referenced_symbols.append(child.symbol)
                                    final_call_references.append(call_references[i])
                                    break

    return final_call_references


# def _find_call_reference(function_calls: list[tuple[astroid.Call, Scope | ClassScope]],
#                          classes: dict[str, ClassScope],
#                          scope: Scope,
#                          functions: dict[str, Scope | ClassScope],
#                          parameters: dict[astroid.FunctionDef, tuple[Scope | ClassScope, list[astroid.AssignName]]]) -> list[ReferenceNode]:
#
#     references_proto: list[ReferenceNode] = []
#     references_final: list[ReferenceNode] = []
#     scope_node: Scope | None = field(default_factory=Callable[[], Scope])
#     python_builtins = dir(builtins)
#
#     for call in function_calls:
#         if isinstance(call[0].func, astroid.Name):
#             if call[0].func.name in functions.keys() or call[0].func.name in python_builtins or call[0].func.name in classes.keys():
#                 node_id = _calc_node_id(call[1].symbol.node)
#                 scope_node = get_scope_node_by_node_id_call(node_id, scope)
#             else:  # the call is a variable that is passed to a function as an argument
#                 for param in parameters.values():
#                     for name in param[1]:
#                         if call[0].func.name in name.name:
#                             scope_node = param[0]
#
#             references_proto.append(ReferenceNode(call[0], scope_node, []))
#
#     for i, reference in enumerate(references_proto):
#         func_name = reference.name.func.name
#         if func_name in python_builtins and func_name not in functions.keys() and func_name not in classes.keys():
#             references_final.append(ReferenceNode(reference.name, reference.scope, [
#                 Builtin(reference.scope, NodeID("builtins", func_name, 0, 0),
#                         func_name)]))
#         elif isinstance(reference.name, astroid.Call):
#             func_def = _get_function_def(reference, functions, classes, parameters)
#             references_final.append(func_def)
#             if func_name in python_builtins:
#                 references_final[i].referenced_symbols.append(Builtin(reference.scope, NodeID("builtins", func_name, 0, 0), func_name))
#
#     return references_final
#
#
# def _get_function_def(reference: ReferenceNode,
#                       functions: dict[str, Scope | ClassScope],
#                       classes: dict[str, ClassScope],
#                       parameters: dict[astroid.FunctionDef, tuple[Scope | ClassScope, list[astroid.AssignName]]]) -> ReferenceNode:
#     if functions:
#         for func in functions.values():
#             if func.symbol.node.name == reference.node.func.name:
#                 return ReferenceNode(reference.node, reference.scope, [func.symbol])
#             # elif isinstance(func.symbol.node, astroid.Lambda) and not isinstance(func.symbol.node, astroid.FunctionDef) and reference.name.func.name in functions.keys():
#             #     for funtion_name in functions.keys():
#             #         if funtion_name == reference.name.func.name:
#             #             return ReferenceNode(reference.name, reference.scope, [func.symbol])
#     if classes:
#         for klass in classes.values():
#             if klass.symbol.node.name == reference.node.func.name:
#                 return ReferenceNode(reference.node, reference.scope, [klass.symbol])
#     if parameters:
#         for funtion_def in parameters.keys():
#             for param in parameters[funtion_def][1]:
#                 if param.name == reference.node.func.name:
#                     return ReferenceNode(reference.node, reference.scope, [Parameter(parameters[funtion_def][0], _calc_node_id(param), param.name)])
#
#     raise ChildProcessError(f"Function {reference.node.func.name} not found in functions.")
#
#
# def get_scope_node_by_node_id_call(targeted_node_id: NodeID,
#                                    scope: Scope) -> Scope:
#     # TODO: implement a dfs search for the node (or an other quicker search algorithm)
#     if scope.symbol.id == targeted_node_id:
#         return scope
#     else:
#         if scope.children:
#             for child in scope.children:
#                 print(child.symbol.id)
#                 if child.symbol.id == targeted_node_id:
#                     return child
#         # else:
#         #     return get_scope_node_by_node_id_call(targeted_node_id, child)
#     raise ChildProcessError(f"Node with id {targeted_node_id} not found in scope.")

def resolve_references(code: str) -> list[ReferenceNode]:
    """
    Resolve all references in a module.

    This function is the entry point for the reference resolving.
    It calls all other functions that are needed to resolve the references.
    First we get the module data for the given (module) code.

    Parameters:
        * code: the code of the module for which we want to resolve the references

    Returns:
        * resolved_references: a list of all resolved references in the module
    """

    module_data = _get_module_data(code)
    resolved_references = _create_unspecified_references(module_data.target_nodes, module_data.value_nodes, module_data.scope,
                                                            module_data.classes, module_data.functions)

    if module_data.function_calls:
        # references_call = _find_call_reference(module_data.function_calls, module_data.classes, module_data.scope, module_data.functions, module_data.parameters)
        references_call = _find_call_reference_new(module_data.function_calls, module_data.classes, module_data.functions, module_data.parameters)
        resolved_references.extend(references_call)

    # for name_node in module_data.value_nodes:
    #     if isinstance(name_node, astroid.Name | MemberAccessValue):
    #         references_for_name_node = _find_references(name_node, references_unspecified, module_data)
    #         resolved_references.extend(references_for_name_node)

    return resolved_references
