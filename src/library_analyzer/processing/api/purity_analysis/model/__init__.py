"""Data model for purity analysis."""

from library_analyzer.processing.api.purity_analysis.model._call_graph import (
    CallGraphForest,
    CallGraphNode,
    CombinedCallGraphNode,
    ImportedCallGraphNode,
)
from library_analyzer.processing.api.purity_analysis.model._module_data import (
    Builtin,
    BuiltinOpen,
    ClassScope,
    ClassVariable,
    CombinedSymbol,
    FunctionScope,
    GlobalVariable,
    Import,
    InstanceVariable,
    LocalVariable,
    MemberAccess,
    MemberAccessTarget,
    MemberAccessValue,
    ModuleData,
    NodeID,
    Parameter,
    Reference,
    Scope,
    Symbol,
    UnknownSymbol,
)
from library_analyzer.processing.api.purity_analysis.model._purity import (
    APIPurity,
    CallOfParameter,
    Expression,
    FileRead,
    FileWrite,
    Impure,
    ImpurityReason,
    NativeCall,
    NonLocalVariableRead,
    NonLocalVariableWrite,
    OpenMode,
    ParameterAccess,
    Pure,
    PurityResult,
    StringLiteral,
    UnknownCall,
    UnknownClassInit,
    UnknownFunctionCall,
)
from library_analyzer.processing.api.purity_analysis.model._purity_builtins import (
    BUILTIN_CLASSSCOPES,
    BUILTIN_FUNCTIONS,
    OPEN_MODES,
    BUILTIN_SPECIALS,
)
from library_analyzer.processing.api.purity_analysis.model._reference import (
    ModuleAnalysisResult,
    Reasons,
    ReferenceNode,
    TargetReference,
    ValueReference,
)

__all__ = [
    "ModuleAnalysisResult",
    "ModuleData",
    "Scope",
    "ClassScope",
    "FunctionScope",
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
    "ParameterAccess",
    "StringLiteral",
    "ImpurityReason",
    "NonLocalVariableRead",
    "NonLocalVariableWrite",
    "FileRead",
    "FileWrite",
    "PurityResult",
    "Pure",
    "Impure",
    "Reasons",
    "CallGraphForest",
    "OpenMode",
    "NativeCall",
    "UnknownCall",
    "CallOfParameter",
    "Reference",
    "TargetReference",
    "ValueReference",
    "APIPurity",
    "BuiltinOpen",
    "CallGraphNode",
    "CombinedCallGraphNode",
    "CombinedSymbol",
    "UnknownFunctionCall",
    "UnknownClassInit",
    "ImportedCallGraphNode",
    "BUILTIN_CLASSSCOPES",
    "BUILTIN_FUNCTIONS",
    "OPEN_MODES",
    "UnknownSymbol",
    "BUILTIN_SPECIALS",
]
