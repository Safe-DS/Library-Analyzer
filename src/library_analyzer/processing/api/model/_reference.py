from dataclasses import dataclass, field

import astroid

from library_analyzer.processing.api.model import (
    Scope,
    Symbol,
    MemberAccess,
)


@dataclass
class ReferenceNode:
    name: astroid.Name | astroid.AssignName | astroid.Call | MemberAccess | str
    scope: Scope
    referenced_symbols: list[Symbol] = field(default_factory=list)

    def __contains__(self, item) -> bool:
        return item in self.referenced_symbols
