"""Model classes to store migration information."""

from ._api_mapping import APIMapping
from ._differ import AbstractDiffer, SimpleDiffer
from ._inheritance_differ import InheritanceDiffer
from ._mapping import (
    ManyToManyMapping,
    ManyToOneMapping,
    Mapping,
    OneToManyMapping,
    OneToOneMapping,
    merge_mappings,
)
from ._strict_differ import StrictDiffer
from ._unchanged_differ import UnchangedDiffer

__all__ = [
    "APIMapping",
    "AbstractDiffer",
    "InheritanceDiffer",
    "ManyToManyMapping",
    "ManyToOneMapping",
    "Mapping",
    "OneToManyMapping",
    "OneToOneMapping",
    "SimpleDiffer",
    "StrictDiffer",
    "UnchangedDiffer",
    "merge_mappings",
]
