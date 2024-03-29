from library_analyzer.processing.annotations._generate_boundary_annotations import (
    _generate_boundary_annotations,
)
from library_analyzer.processing.annotations._generate_dependency_annotations import _generate_dependency_annotations
from library_analyzer.processing.annotations._generate_enum_annotations import (
    _generate_enum_annotations,
)
from library_analyzer.processing.annotations._generate_remove_annotations import (
    _generate_remove_annotations,
)
from library_analyzer.processing.annotations._generate_value_annotations import (
    _generate_value_annotations,
)
from library_analyzer.processing.annotations._usages_preprocessor import (
    _preprocess_usages,
)
from library_analyzer.processing.annotations.model import AnnotationStore
from library_analyzer.processing.api.model import API
from library_analyzer.processing.usages.model import UsageCountStore


def generate_annotations(api: API, usages: UsageCountStore) -> AnnotationStore:
    _preprocess_usages(usages, api)

    annotations = AnnotationStore()
    _generate_remove_annotations(api, usages, annotations)
    _generate_value_annotations(api, usages, annotations)
    _generate_enum_annotations(api, annotations)
    _generate_boundary_annotations(api, annotations)
    _generate_dependency_annotations(api, annotations)
    return annotations
