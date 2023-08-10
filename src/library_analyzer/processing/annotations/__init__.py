"""Generation of annotations."""

from ._generate_annotations import generate_annotations
from ._generate_dependency_annotations import _generate_dependency_annotations


__all__ = [
    "generate_annotations",
   "_generate_dependency_annotations"
]
