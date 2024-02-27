from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import astroid

from library_analyzer.processing.api.purity_analysis.model._module_data import (
    ClassScope,
    ClassVariable,
    FunctionScope,
    GlobalVariable,
    InstanceVariable,
    MemberAccessTarget,
    MemberAccessValue,
    NodeID,
    Reference,
    Scope,
    Symbol,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from library_analyzer.processing.api.purity_analysis.model import CallGraphForest, PurityResult


@dataclass
class ReferenceNode(ABC):
    """Class for reference nodes.

    A reference node represents a reference to a list of its referenced symbols.


    Attributes
    ----------
    node : astroid.Name | astroid.AssignName | astroid.Call | MemberAccessTarget | MemberAccessValue
        The node that references the symbols.
    scope : Scope
        The scope of the node.
    referenced_symbols : list[Symbol]
        The list of referenced symbols.
        These are the symbols of the nodes that node references.
    """

    node: Symbol | Reference
    scope: Scope
    referenced_symbols: list[Symbol] = field(default_factory=list)

    def __repr__(self) -> str:
        if isinstance(self.node, astroid.Call) and isinstance(self.node.func, astroid.Name):
            return f"{self.node.func.name}.line{self.node.lineno}"
        if isinstance(self.node, MemberAccessTarget | MemberAccessValue):
            return f"{self.node.name}.line{self.node.node.lineno}"
        return f"{self.node.name}.line{self.node.node.lineno}"


@dataclass
class TargetReference(ReferenceNode):
    """Class for target reference nodes.

    A TargetReference represents a reference from a target (=Symbol) to a list of Symbols.
    This is used to represent a Reference from a reassignment to the original assignment
    (or another previous assignment) of the same variable.
    """

    node: Symbol

    def __hash__(self) -> int:
        return hash(str(self))


@dataclass
class ValueReference(ReferenceNode):
    """Class for value reference nodes.

    A ValueReference represents a reference from a value to a list of Symbols.
    This is used to represent a Reference from a function call to the function definition.
    """

    node: Reference

    def __hash__(self) -> int:
        return hash(str(self))


@dataclass
class ModuleAnalysisResult:
    """Class for module analysis results.

    After the references of aaa module have been resolved, all necessary information for the purity analysis is available in this class.

    Attributes
    ----------
    resolved_references : dict[str, list[ValueReference | TargetReference]]
        The dictionary of references.
        The key is the name of the reference node, the value is the list of ReferenceNodes.
    raw_reasons : dict[NodeID, Reasons]
        The dictionary of function references.
        The key is the NodeID of the function, the value is the Reasons for the function.
    classes : dict[str, ClassScope]
        All classes and their ClassScope.
    call_graph : CallGraphForest
        The call graph forest of the module.
    """

    resolved_references: dict[str, list[ReferenceNode]]
    raw_reasons: dict[NodeID, Reasons]
    classes: dict[str, ClassScope]
    call_graph: CallGraphForest


@dataclass
class Reasons:
    """
    Represents a function and the raw reasons for impurity.

    Raw reasons means that the reasons are just collected and not yet processed.

    Attributes
    ----------
    function_scope : FunctionScope | None
        The scope of the function which the reasons belong to.
        Is None if the reasons are not for a function.
        This is the case when a combined node is created, or a ClassScope is used to propagate reasons.
    writes_to : set[Symbol]
        A set of all nodes that are written to.
    reads_from : set[Symbol]
        A set of all nodes that are read from.
    calls : set[Symbol]
        A set of all nodes that are called.
    result : PurityResult | None
        The result of the purity analysis
        This also works as a flag to determine if the purity analysis has already been performed:
        If it is None, the purity analysis has not been performed
    unknown_calls : list[astroid.Call | astroid.NodeNG] | None
        A list of all unknown calls.
        Unknown calls are calls to functions that are not defined in the module or are simply not existing.
    """

    function_scope: FunctionScope | None = field(default=None)
    writes_to: set[GlobalVariable | ClassVariable | InstanceVariable] = field(default_factory=set)
    reads_from: set[GlobalVariable | ClassVariable | InstanceVariable] = field(default_factory=set)
    calls: set[Symbol] = field(default_factory=set)
    result: PurityResult | None = field(default=None)
    unknown_calls: list[astroid.Call | astroid.NodeNG] | None = field(default=None)

    def __iter__(self) -> Iterator[Symbol]:
        return iter(self.writes_to.union(self.reads_from).union(self.calls))

    # def get_call_by_name(self, name: str) -> Symbol:
    #     """Get a call by name.
    #
    #     Parameters
    #     ----------
    #     name  : str
    #         The name of the call to get.
    #
    #     Returns
    #     -------
    #     Symbol
    #         The Symbol of the call.
    #
    #     Raises
    #     ------
    #     ValueError
    #         If no call to the function with the given name is found.
    #     """
    #     for call in self.calls:
    #         if isinstance(call.node, astroid.Call):
    #             # make sure we do not get an AttributeError because of the inconsistent names in the astroid API
    #             if isinstance(call.node.func, astroid.Attribute) and call.node.func.attrname == name:
    #                 return call
    #             return call
    #         else:  # noqa: PLR5501
    #             # make sure we do not get an AttributeError because of the inconsistent names in the astroid API
    #             if isinstance(call.node.func, astroid.Attribute) and call.node.attrname == name:  # noqa: SIM114
    #                 return call
    #             elif call.node.name == name:
    #                 return call
    #
    #     raise ValueError("No call to the function found.")

    def join_reasons(self, other: Reasons) -> Reasons:
        """Join two Reasons objects.

        When a function has multiple reasons for impurity, the Reasons objects are joined.
        This means that the writes, reads, calls and unknown_calls are merged.

        Parameters
        ----------
        other : Reasons
            The other Reasons object.

        Returns
        -------
        Reasons
            The updated Reasons object.
        """
        self.writes_to.update(other.writes_to)
        self.reads_from.update(other.reads_from)
        self.calls.update(other.calls)
        # join unknown calls - since they can be None we need to deal with that
        if self.unknown_calls is not None and other.unknown_calls is not None:
            self.unknown_calls.extend(other.unknown_calls)
        elif self.unknown_calls is None and other.unknown_calls is not None:
            self.unknown_calls = other.unknown_calls
        elif other.unknown_calls is None:
            pass

        return self

    @staticmethod
    def join_reasons_list(reasons_list: list[Reasons]) -> Reasons:
        # combined_node_name: str | None = None) -> Reasons:
        # combined_node_name : str
        #    Indicates if the Reasons object is a combined node.
        #    If it is a combined node, the function is set to None since it does not exist.
        """Join a list of Reasons objects.

        Combines a list of Reasons objects into one Reasons object.

        Parameters
        ----------
        reasons_list : list[Reasons]
            The list of Reasons objects.


        Returns
        -------
        Reasons
            The combined Reasons object.

        Raises
        ------
        ValueError
            If the list of Reasons objects is empty.
        """
        if not reasons_list:
            raise ValueError("List of Reasons is empty.")

        result = Reasons()
        for reason in reasons_list:
            result.join_reasons(reason)
        # if combined_node_name is not None:
        #     result.function = combined_node_name
        return result
