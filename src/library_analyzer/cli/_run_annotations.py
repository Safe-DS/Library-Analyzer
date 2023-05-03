from pathlib import Path

from library_analyzer.processing.annotations import generate_annotations
from library_analyzer.processing.api.model import API
from library_analyzer.processing.usages.model import UsageCountStore


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
    api = API.from_json_file(api_file_path)
    usages = UsageCountStore.from_json_file(usages_file_path)
    annotations = generate_annotations(api, usages)
    annotations.to_json_file(annotations_file_path)
