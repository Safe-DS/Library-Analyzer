from dataclasses import dataclass, field

import astroid

from library_analyzer.processing.api.model import (
    Scope,
    Symbol,
    MemberAccess,
)


@dataclass
class ReferenceNode:
    node: astroid.Name | astroid.AssignName | astroid.Call | MemberAccess | str  # TODO: remove str?
    scope: Scope
    referenced_symbols: list[Symbol] = field(default_factory=list)

    def __contains__(self, item) -> bool:
        return item in self.referenced_symbols

    def __hash__(self) -> int:
        return hash(str(self))

    def __str__(self) -> str:
        if isinstance(self.node, astroid.Call):
            return f"{self.node.func.name}.line{self.node.lineno}"
        if isinstance(self.node, MemberAccess):
            return f"{self.node.name}.line{self.node.lineno}"
        return f"{self.node.name}.line{self.node.lineno}"
