import json
import os
from pathlib import Path

import pytest
from library_analyzer.processing.annotations import generate_annotations
from library_analyzer.processing.api.model import API
from library_analyzer.processing.usages.model import UsageCountStore


@pytest.mark.parametrize(
    "subfolder",
    [
        "boundaryAnnotations",
        "enumAnnotations",
        "removeAnnotations",
        "valueAnnotations",
    ],
)
def test_generate_annotations(
    subfolder: str,
) -> None:
    usages, api, expected_annotations = read_test_data(subfolder)
    annotations = generate_annotations(api, usages)

    assert annotations.to_json()[subfolder] == expected_annotations


def read_test_data(subfolder: str) -> tuple[UsageCountStore, API, dict]:
    data_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", subfolder)

    api_json_path = os.path.join(data_path, "api_data.json")
    usages_json_path = os.path.join(data_path, "usage_data.json")
    annotations_json_path = os.path.join(data_path, "annotation_data.json")

    with Path(api_json_path).open(encoding="utf-8") as api_file:
        api_json = json.load(api_file)
        api = API.from_json(api_json)

    with Path(usages_json_path).open(encoding="utf-8") as usages_file:
        usages_json = json.load(usages_file)
        usages = UsageCountStore.from_json(usages_json)

    with Path(annotations_json_path).open(encoding="utf-8") as annotations_file:
        annotations_json = json.load(annotations_file)

    return usages, api, annotations_json
