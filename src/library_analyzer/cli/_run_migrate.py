from pathlib import Path
from typing import Any

from library_analyzer.processing.migration import Migration
from library_analyzer.processing.migration.model import (
    AbstractDiffer,
    APIMapping,
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


def _run_migrate_command(
    apiv1_file_path: Path,
    annotations_file_path: Path,
    apiv2_file_path: Path,
    out_dir_path: Path,
) -> None:
    apiv1 = _read_api_file(apiv1_file_path)
    apiv2 = _read_api_file(apiv2_file_path)
    annotationsv1 = _read_annotations_file(annotations_file_path)

    unchanged_differ = UnchangedDiffer(None, [], apiv1, apiv2)
    api_mapping = APIMapping(apiv1, apiv2, unchanged_differ)
    unchanged_mappings: list[Mapping] = api_mapping.map_api()
    previous_mappings = unchanged_mappings
    previous_base_differ: AbstractDiffer | None = unchanged_differ

    differ_init_list: list[tuple[type[AbstractDiffer], dict[str, Any]]] = [
        (SimpleDiffer, {}),
        (StrictDiffer, {"unchanged_mappings": unchanged_mappings}),
        (InheritanceDiffer, {}),
    ]

    for differ_init in differ_init_list:
        differ_class, additional_parameters = differ_init
        differ = differ_class(previous_base_differ, previous_mappings, apiv1, apiv2, **additional_parameters)
        api_mapping = APIMapping(apiv1, apiv2, differ)
        mappings = api_mapping.map_api()

        previous_mappings = mappings
        previous_base_differ = differ if differ.is_base_differ() else differ.previous_base_differ

    if previous_mappings is not None:
        migration = Migration(annotationsv1, previous_mappings)
        migration.migrate_annotations()
        migration.print(apiv1, apiv2)
        migrated_annotations_file = out_dir_path / f"migrated_annotationsv{apiv2.version}.json"
        unsure_migrated_annotations_file = out_dir_path / f"unsure_migrated_annotationsv{apiv2.version}.json"
        _write_annotations_file(migration.migrated_annotation_store, migrated_annotations_file)
        _write_annotations_file(migration.unsure_migrated_annotation_store, unsure_migrated_annotations_file)
