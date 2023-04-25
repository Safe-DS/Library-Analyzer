import os
from pathlib import Path
from typing import Any, Optional

from library_analyzer.processing.migration import APIMapping, Migration
from library_analyzer.processing.migration.model import (
    AbstractDiffer,
    InheritanceDiffer,
    Mapping,
    SimpleDiffer,
    StrictDiffer,
    UnchangedDiffer,
)

from ._read_and_write_file import (
    _read_annotations_file,
    _read_api_file,
    _write_annotations_file,
)
from ..processing.api.model import API


def _run_migrate_command(
    apiv1_file_path: Path,
    annotations_file_path: Path,
    apiv2_file_path: Path,
    out_dir_path: Path,
) -> None:
    apiv1 = _read_api_file(apiv1_file_path)
    apiv2 = _read_api_file(apiv2_file_path)
    annotationsv1 = _read_annotations_file(annotations_file_path)

    apiv1_ = API(apiv1.distribution, apiv1.package, apiv1.version)
    apiv2_ = API(apiv2.distribution, apiv2.package, apiv2.version)

    # id_filter = ""
    # for class_v1 in apiv1.classes.values():
    #     if class_v1.id.startswith(id_filter) and class_v1.is_public:
    #         apiv1_.add_class(class_v1)
    # for func_v1 in apiv1.functions.values():
    #     if func_v1.id.startswith(id_filter) and func_v1.is_public:
    #         apiv1_.add_function(func_v1)
    # for class_v2 in apiv2.classes.values():
    #     if class_v2.id.startswith(id_filter) and class_v2.is_public:
    #         apiv2_.add_class(class_v2)
    # for func_v2 in apiv2.functions.values():
    #     if func_v2.id.startswith(id_filter) and func_v2.is_public:
    #         apiv2_.add_function(func_v2)
    #
    # apiv1 = apiv1_
    # apiv2 = apiv2_

    threshold_of_similarity_for_creation_of_mappings = 0.61
    threshold_of_similarity_between_mappings = 0.23

    print("-----------------------------")
    print("i: " + str(threshold_of_similarity_for_creation_of_mappings) + " j:" + str(threshold_of_similarity_between_mappings))
    print("-----------------------------")

    unchanged_differ = UnchangedDiffer(None, [], apiv1, apiv2)
    api_mapping = APIMapping(apiv1, apiv2, unchanged_differ, threshold_of_similarity_for_creation_of_mappings, threshold_of_similarity_between_mappings)
    unchanged_mappings: list[Mapping] = api_mapping.map_api()
    previous_mappings = unchanged_mappings
    previous_base_differ: Optional[AbstractDiffer] = unchanged_differ

    differ_init_list: list[tuple[type[AbstractDiffer], dict[str, Any]]] = [
        (SimpleDiffer, {}),
        (StrictDiffer, {"unchanged_mappings": unchanged_mappings}),
        (InheritanceDiffer, {}),
    ]

    for differ_init in differ_init_list:
        differ_class, additional_parameters = differ_init
        differ = differ_class(
            previous_base_differ,
            previous_mappings,
            apiv1,
            apiv2,
            **additional_parameters
        )
        api_mapping = APIMapping(apiv1, apiv2, differ, threshold_of_similarity_for_creation_of_mappings, threshold_of_similarity_between_mappings)
        mappings = api_mapping.map_api()

        previous_mappings = mappings
        previous_base_differ = (
            differ if differ.is_base_differ() else differ.previous_base_differ
        )

    if previous_mappings is not None:
        migration = Migration(annotationsv1, previous_mappings)
        migration.migrate_annotations()
        migration.print(apiv1, apiv2)
        migrated_annotations_file = Path(
            os.path.join(
                out_dir_path, "migrated_annotationsv" + apiv2.version + ".json"
            )
        )
        unsure_migrated_annotations_file = Path(
            os.path.join(
                out_dir_path, "unsure_migrated_annotationsv" + apiv2.version + ".json"
            )
        )
        _write_annotations_file(
            migration.migrated_annotation_store, migrated_annotations_file
        )
        _write_annotations_file(
            migration.unsure_migrated_annotation_store, unsure_migrated_annotations_file
        )
