from dataclasses import dataclass, field

import astroid

from library_analyzer.processing.api.purity_analysis.model import (
    MemberAccessTarget,
    MemberAccessValue,
    Scope,
    Symbol,
)


@dataclass
class ReferenceNode:
    node: astroid.Name | astroid.AssignName | astroid.Call | MemberAccessTarget | MemberAccessValue
    scope: Scope
    referenced_symbols: list[Symbol] = field(default_factory=list)

    def __repr__(self) -> str:
        if isinstance(self.node, astroid.Call):
            return f"{self.node.func.name}.line{self.node.lineno}"
        if isinstance(self.node, MemberAccessTarget | MemberAccessValue):
            return f"{self.node.name}.line{self.node.member.lineno}"
        return f"{self.node.name}.line{self.node.lineno}"
