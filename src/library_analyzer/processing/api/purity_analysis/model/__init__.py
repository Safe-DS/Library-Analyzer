"""Data model for purity analysis."""

from library_analyzer.processing.api.purity_analysis.model._scope import (
    ModuleData,
    Scope,
    ClassScope,
    MemberAccess,
    MemberAccessTarget,
    MemberAccessValue,
    NodeID,
    Symbol,
    Parameter,
    LocalVariable,
    GlobalVariable,
    ClassVariable,
    InstanceVariable,
    Import,
    Builtin,
)

from library_analyzer.processing.api.purity_analysis.model._reference import ReferenceNode

from library_analyzer.processing.api.purity_analysis.model._purity import (  # TODO: rework this
    Expression,
    AttributeAccess,
    GlobalAccess,
    InstanceAccess,
    ParameterAccess,
    StringLiteral,
    Reference,
    ImpurityCertainty,
    ImpurityIndicator,
    ConcreteImpurityIndicator,
    VariableRead,
    VariableWrite,
    FileRead,
    FileWrite,
    SystemInteraction,
    UnknownCallTarget,
    Call,
    BuiltInFunction,
)

__all__ =[
    "ModuleData",
    "Scope",
    "ClassScope",
    "MemberAccess",
    "MemberAccessTarget",
    "MemberAccessValue",
    "NodeID",
    "Symbol",
    "Parameter",
    "LocalVariable",
    "GlobalVariable",
    "ClassVariable",
    "InstanceVariable",
    "Import",
    "Builtin",
    "ReferenceNode",
    "Expression",
    "AttributeAccess",
    "GlobalAccess",
    "InstanceAccess",
    "ParameterAccess",
    "StringLiteral",
    "Reference",
    "ImpurityCertainty",
    "ImpurityIndicator",
    "ConcreteImpurityIndicator",
    "VariableRead",
    "VariableWrite",
    "FileRead",
    "FileWrite",
    "SystemInteraction",
    "UnknownCallTarget",
    "Call",
    "BuiltInFunction",
]