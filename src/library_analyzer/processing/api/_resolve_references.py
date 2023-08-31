from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


import astroid
import builtins

from library_analyzer.processing.api._get_module_data import _calc_node_id, _get_module_data  # Todo: can we import from .api?
from library_analyzer.processing.api.model import (
    MemberAccess,
    MemberAccessTarget,
    MemberAccessValue,
    NodeID,
    Symbol,
    Scope,
    ClassScope,
    ClassVariable,
    InstanceVariable,
    GlobalVariable,
    Parameter,
    LocalVariable,
    Builtin,
    ModuleData
)


@dataclass
class ReferenceNode:
    name: astroid.Name | astroid.AssignName | astroid.Call | MemberAccess | str
    scope: Scope
    referenced_symbols: list[Symbol] = field(default_factory=list)

    def __contains__(self, item) -> bool:
        return item in self.referenced_symbols


def get_scope_node_by_node_id(scope: Scope | list[Scope], targeted_node_id: NodeID,
                              name_nodes: dict[astroid.Name, Scope | ClassScope] | None) -> Scope | ClassScope:
    # TODO: implement a dfs search for the node (or an other quicker search algorithm)
    if name_nodes is None:
        for node in scope:
            if node.id == targeted_node_id:
                return node
            else:
                found_node = get_scope_node_by_node_id(node.children, targeted_node_id, None)
                if found_node is not None:
                    return found_node

    else:
        for name in name_nodes.keys():
            name_id = _calc_node_id(name)
            if name_id == targeted_node_id:
                return name_nodes.get(name)


def _create_unspecified_references(all_names_list: list[astroid.Name | astroid.AssignName | MemberAccess],
                                   scope: Scope,
                                   name_nodes: dict[astroid.Name, Scope | ClassScope],
                                   classes: dict[str, ClassScope],
                                   functions: dict[str, Scope | ClassScope]) -> list[ReferenceNode]:
    """Create a list of references from a list of name nodes.

    Returns:
        * references_final: contains all references that are used as targets
    """
    references_proto: list[ReferenceNode] = []
    references_final: list[ReferenceNode] = []
    scope_node: Scope | None = field(default_factory=Callable[[], Scope])

    for name in all_names_list:
        node_id = _calc_node_id(name)
        if isinstance(name, astroid.AssignName):
            scope_node = get_scope_node_by_node_id(scope, node_id, None)
        elif isinstance(name, astroid.Name):
            scope_node = get_scope_node_by_node_id(scope, node_id, name_nodes)
        elif isinstance(name, MemberAccess):
            scope_node = get_scope_node_by_node_id(scope, node_id, name_nodes)

        references_proto.append(ReferenceNode(name, scope_node, []))

    for reference in references_proto:
        if isinstance(reference.name, astroid.Name | MemberAccessValue):
            target_ref = _add_target_references(reference, references_proto, classes, functions)
            references_final.append(target_ref)

    return references_final


def _add_target_references(reference: ReferenceNode,
                           reference_list: list[ReferenceNode],
                           classes: dict[str, ClassScope],
                           functions: dict[str, Scope | ClassScope]) -> ReferenceNode:
    """Add all target references to a reference.

    A target reference is a reference where the name is used as a target.
    Therefor we need to check all nodes further up the list where the name is used as a target.
    """
    complete_reference = reference
    if reference in reference_list:
        for ref in reference_list:
            # for ref in reference_list[:reference_list.index(reference)]:
            if isinstance(ref.name, MemberAccessValue):
                root = ref.scope.root()
                if isinstance(root.node, astroid.Module):
                    for class_scope in classes.values():
                        for variable in class_scope.class_variables:
                            if isinstance(reference.name, MemberAccessValue) and reference.name.value.name == variable.name:
                                cv = ClassVariable(node=class_scope, id=_calc_node_id(variable),
                                                   name=f"{class_scope.node.name}.{variable.name}")
                                if cv not in complete_reference.referenced_symbols:
                                    complete_reference.referenced_symbols.append(cv)
                                # complete_reference.referenced_symbols.append(
                                #     ClassVariable(node=class_scope, id=_calc_node_id(variable),
                                #                   name=f"{class_scope.node.name}.{variable.name}"))
                        for variable in class_scope.instance_variables:
                            if isinstance(reference.name, MemberAccessValue) and reference.name.value.name == variable.attrname:
                                iv = InstanceVariable(node=class_scope, id=_calc_node_id(variable),
                                                      name=f"{reference.name.expression.name}.{variable.attrname}")
                                if iv not in complete_reference.referenced_symbols:
                                    complete_reference.referenced_symbols.append(iv)

            elif isinstance(ref.name, MemberAccessTarget) and isinstance(reference.name, MemberAccessValue):
                if ref.name.name == reference.name.name:
                    complete_reference.referenced_symbols.append(
                        ClassVariable(node=ref.scope, id=_calc_node_id(ref.name), name=ref.name.name))

            elif isinstance(ref.name, astroid.AssignName) and ref.name.name == reference.name.name:
                complete_reference.referenced_symbols.append(
                    Symbol(node=ref.scope, id=_calc_node_id(ref.name), name=ref.name.name))

            # this detects functions that are passed as arguments to other functions (and therefor are not called)
            elif ref.name.name in functions.keys() and ref.name.name == reference.name.name:
                complete_reference.referenced_symbols.append(
                    GlobalVariable(node=functions[ref.name.name], id=_calc_node_id(functions[ref.name.name].node), name=ref.name.name))

            elif isinstance(ref.name, astroid.Name) and isinstance(reference.name, astroid.Name):
                if ref.name.name in classes.keys() and ref.name.name == reference.name.name:
                    gv = GlobalVariable(node=classes[ref.name.name], id=_calc_node_id(classes[ref.name.name].node), name=ref.name.name)
                    if gv not in complete_reference.referenced_symbols:
                        complete_reference.referenced_symbols.append(gv)

    return complete_reference


def _find_references(name_node: astroid.Name,
                     references: list[ReferenceNode],
                     module_data: ModuleData) -> list[ReferenceNode]:
    """Find all references for a node.

    Parameters:
    * name_node: the node for which we want to find all references
    * all_name_nodes_list: a list of all name nodes in the module
    * module_data: the data of the module
    """

    for i, ref in enumerate(references):
        if isinstance(ref.name or name_node, MemberAccess):
            if ref.name.name == name_node.name:
                return [_get_symbols(ref, ref.scope, module_data.parameters, module_data.globals)]
        if ref.name == name_node:
            return [_get_symbols(ref, ref.scope, module_data.parameters, module_data.globals)]
    return []


def _get_symbols(node: ReferenceNode,
                 current_scope: Scope | ClassScope | None,
                 function_parameters: dict[astroid.FunctionDef, tuple[Scope | ClassScope, list[astroid.AssignName]]],
                 global_variables: dict[str, Scope | ClassScope]) -> ReferenceNode:
    # wir können die Symbole bereits beim Erstellen des Scopes spezifizieren
    try:
        for i, symbol in enumerate(node.referenced_symbols):
            if current_scope.children:
                for nod in current_scope.children:
                    if isinstance(nod.node, MemberAccessTarget) and nod.node.name == symbol.name:
                        parent_node = nod.parent
                        specified_symbol = specify_symbols(parent_node, symbol, function_parameters)
                        node.referenced_symbols[i] = specified_symbol

                    elif isinstance(nod.node, astroid.AssignName) and nod.node.name == symbol.name:
                        parent_node = nod.parent
                        specified_symbol = specify_symbols(parent_node, symbol, function_parameters)
                        node.referenced_symbols[i] = specified_symbol

                # if not isinstance(current_scope.parent, NoneType):
                #     return _get_symbols(node, current_scope.parent, function_parameters, global_variables)

                #  would fix: "for loop with local runtime variable local scope" but break other case
            else:
                return _get_symbols(node, current_scope.parent, function_parameters, global_variables)
            # TODO: ideally the functionality of the next block should be in the specify_symbols function
            if symbol.name in global_variables.keys():
                current_symbol_parent = global_variables.get(symbol.name)
                if current_symbol_parent is not None:
                    node.referenced_symbols[i] = GlobalVariable(symbol.node, symbol.id, symbol.name)
        return node
    except ChildProcessError:
        raise ChildProcessError(f"Parent node {node.scope.node.name} of {node.name.name} does not have any (detected) children.")


def specify_symbols(parent_node: Scope | ClassScope | None,
                    symbol: Symbol,
                    function_parameters: dict[
                        astroid.FunctionDef, tuple[Scope | ClassScope, list[astroid.AssignName]]]) -> Symbol:
    if isinstance(symbol, ClassVariable | InstanceVariable | Parameter | GlobalVariable):
        return symbol
    if isinstance(parent_node.node, astroid.Module):
        return GlobalVariable(symbol.node, symbol.id, symbol.name)
    elif isinstance(parent_node.node, astroid.ClassDef):
        if parent_node.node:  # TODO: check if node is class attribute or instance attribute
            return ClassVariable(symbol.node, symbol.id, symbol.name)
        # if global_variables:
        #     for key in global_variables.keys():
        #         if key == symbol.name:
        #             return GlobalVariable(symbol.node, symbol.id, symbol.name)
    elif isinstance(parent_node.node, astroid.FunctionDef):
        if parent_node.node in function_parameters.keys():
            for param in function_parameters[parent_node.node][1]:
                if param.name == symbol.name:
                    return Parameter(symbol.node, symbol.id, symbol.name)
        if isinstance(symbol.node.parent.node, astroid.Module):
            return GlobalVariable(symbol.node, symbol.id, symbol.name)

        return LocalVariable(symbol.node, symbol.id, symbol.name)
    elif isinstance(parent_node.node, astroid.Lambda):
        return LocalVariable(symbol.node, symbol.id, symbol.name)
    else:
        return symbol




def _find_call_reference(function_calls: list[tuple[astroid.Call, Scope | ClassScope]],
                         classes: dict[str, ClassScope],
                         scope: Scope,
                         functions: dict[str, Scope | ClassScope],
                         parameters: dict[astroid.FunctionDef, tuple[Scope | ClassScope, list[astroid.AssignName]]]) -> list[ReferenceNode]:

    references_proto: list[ReferenceNode] = []
    references_final: list[ReferenceNode] = []
    scope_node: Scope | None = field(default_factory=Callable[[], Scope])
    python_builtins = dir(builtins)

    for call in function_calls:
        if isinstance(call[0].func, astroid.Name):
            if call[0].func.name in functions.keys() or call[0].func.name in python_builtins or call[0].func.name in classes.keys():
                node_id = _calc_node_id(call[1].node)
                scope_node = get_scope_node_by_node_id_call(node_id, scope)
            else:  # the call is a variable that is passed to a function as an argument
                for param in parameters.values():
                    for name in param[1]:
                        if call[0].func.name in name.name:
                            scope_node = param[0]

            references_proto.append(ReferenceNode(call[0], scope_node, []))

    for i, reference in enumerate(references_proto):
        func_name = reference.name.func.name
        if func_name in python_builtins and func_name not in functions.keys() and func_name not in classes.keys():
            references_final.append(ReferenceNode(reference.name, reference.scope, [
                Builtin(reference.scope, NodeID("builtins", func_name, 0, 0),
                        func_name)]))
        elif isinstance(reference.name, astroid.Call):
            func_def = _get_function_def(reference, functions, classes, parameters)
            references_final.append(func_def)
            if func_name in python_builtins:
                references_final[i].referenced_symbols.append(Builtin(reference.scope, NodeID("builtins", func_name, 0, 0), func_name))

    return references_final


def _get_function_def(reference: ReferenceNode,
                      functions: dict[str, Scope | ClassScope],
                      classes: dict[str, ClassScope],
                      parameters: dict[astroid.FunctionDef, tuple[Scope | ClassScope, list[astroid.AssignName]]]) -> ReferenceNode:
    if functions:
        for func in functions.values():
            if func.node.name == reference.name.func.name:
                return ReferenceNode(reference.name, reference.scope, [GlobalVariable(func, func.id, func.node.name)])
            elif isinstance(func.node, astroid.Lambda) and not isinstance(func.node, astroid.FunctionDef) and reference.name.func.name in functions.keys():
                for funtion_name in functions.keys():
                    if funtion_name == reference.name.func.name:
                        return ReferenceNode(reference.name, reference.scope, [GlobalVariable(func, func.id, reference.name.func.name)])
    if classes:
        for klass in classes.values():
            if klass.node.name == reference.name.func.name:
                return ReferenceNode(reference.name, reference.scope, [GlobalVariable(klass, klass.id, klass.node.name)])
    if parameters:
        for funtion_def in parameters.keys():
            for param in parameters[funtion_def][1]:
                if param.name == reference.name.func.name:
                    return ReferenceNode(reference.name, reference.scope, [Parameter(parameters[funtion_def][0], _calc_node_id(param), param.name)])

    raise ChildProcessError(f"Function {reference.name.func.name} not found in functions.")


def get_scope_node_by_node_id_call(targeted_node_id: NodeID,
                                   scope: Scope) -> Scope:
    # TODO: implement a dfs search for the node (or an other quicker search algorithm)
    if scope.id == targeted_node_id:
        return scope
    else:
        if scope.children:
            for child in scope.children:
                print(child.id)
                if child.id == targeted_node_id:
                    return child
        # else:
        #     return get_scope_node_by_node_id_call(targeted_node_id, child)
    raise ChildProcessError(f"Node with id {targeted_node_id} not found in scope.")


def resolve_references(code: str) -> list[ReferenceNode]:
    module_data = _get_module_data(code)
    references_specified: list[ReferenceNode] = []

    references_unspecified = _create_unspecified_references(module_data.names_list, module_data.scope,
                                                            module_data.names, module_data.classes, module_data.functions)

    if module_data.function_calls:
        references_call = _find_call_reference(module_data.function_calls, module_data.classes, module_data.scope, module_data.functions, module_data.parameters)
        references_specified.extend(references_call)

    for name_node in module_data.names_list:
        if isinstance(name_node, astroid.Name | MemberAccessValue):
            references_for_name_node = _find_references(name_node, references_unspecified, module_data)
            references_specified.extend(references_for_name_node)

    return references_specified
