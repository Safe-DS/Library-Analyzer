import json
from pathlib import Path

from library_analyzer.cli._json_encoder import CustomEncoder
from library_analyzer.processing.annotations.model import AnnotationStore
from library_analyzer.processing.api.model import API
from library_analyzer.processing.dependencies._parameter_dependencies import APIDependencies
from library_analyzer.processing.usages.model import UsageCountStore
from library_analyzer.utils import ensure_file_exists


def _read_annotations_file(annotations_file_path: Path) -> AnnotationStore:
    with annotations_file_path.open(encoding="utf-8") as annotations_file:
        annotations_json = json.load(annotations_file)

    return AnnotationStore.from_json(annotations_json)


def _write_annotations_file(annotations: AnnotationStore, annotations_file_path: Path) -> None:
    ensure_file_exists(annotations_file_path)
    with annotations_file_path.open("w", encoding="utf-8") as f:
        json.dump(annotations.to_json(), f, indent=2)


def _read_api_file(api_file_path: Path) -> API:
    with api_file_path.open(encoding="utf-8") as api_file:
        api_json = json.load(api_file)

    return API.from_json(api_json)


def _read_usages_file(usages_file_path: Path) -> UsageCountStore:
    with usages_file_path.open(encoding="utf-8") as usages_file:
        usages_json = json.load(usages_file)

    return UsageCountStore.from_json(usages_json)


def _write_api_file(api: API, out_dir_path: Path) -> Path:
    out_file_api = out_dir_path.joinpath(f"{api.package}__api.json")
    ensure_file_exists(out_file_api)
    with out_file_api.open("w", encoding="utf-8") as f:
        json.dump(api.to_json(), f, indent=2, cls=CustomEncoder)
    return out_file_api


def _write_api_dependency_file(api: API, api_dependencies: APIDependencies, out: Path) -> None:
    out_file_api_dependencies = out.joinpath(f"{api.package}__api_dependencies.json")
    ensure_file_exists(out_file_api_dependencies)
    with out_file_api_dependencies.open("w") as f:
        json.dump(api_dependencies.to_json(), f, indent=2, cls=CustomEncoder)
