import pytest
import os
import json

from library_analyzer.processing.annotations._extract_valid_values import extract_valid_literals
@pytest.mark.parametrize(
    "subfolder",
    [
        "enumAnnotations"
    ]
)
def test_extract_values(subfolder: str):
    parameter_json_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "data", subfolder, "parameter_data_with_description.json"
    )

    with open(parameter_json_path, "r") as param_data:
        params = json.load(param_data)["parameters"]

    for param in params:
        description = param["docstring"]["description"]
        typestring = param["docstring"]["type"]
        expected_literals = param["expected_literals"]

        assert extract_valid_literals(description, typestring) == set(expected_literals)
