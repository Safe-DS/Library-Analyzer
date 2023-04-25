from pathlib import Path

from library_analyzer.processing.annotations import generate_annotations

from ._read_and_write_file import (
    _read_api_file,
    _read_usages_file,
    _write_annotations_file,
)


def _run_annotations(api_file_path: Path, usages_file_path: Path, annotations_file_path: Path) -> None:
    """
    Generate an annotation file from the given API and UsageStore files, and write it to the given output file.

    Annotations that are generated are: remove, constant, required, optional, enum and boundary.

    Parameters
    ----------
    api_file_path : Path
        API file Path
    usages_file_path : Path
        UsageStore file Path
    annotations_file_path : Path
        Output file Path.
    """
    api = _read_api_file(api_file_path)
    usages = _read_usages_file(usages_file_path)
    annotations = generate_annotations(api, usages)
    _write_annotations_file(annotations, annotations_file_path)
