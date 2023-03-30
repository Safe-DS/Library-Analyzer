import pytest

from library_analyzer.processing.annotations._extract_valid_values import extract_valid_literals


@pytest.mark.parametrize(
    ("type_", "description", "expected_literals"),
    [
        (
            "str",
            "If \"mean\", then replace missing values using the mean along each column\nIf \"median\", then replace missing values using the median along each column\nIf \"most_frequent\", then replace missing using the most frequent value along each column\nIf \"constant\", then replace missing values with fill_value\n",
            ["\"mean\"", "\"median\"", "\"most_frequent\"", "\"constant\""]
        )
        # TODO: add other test cases from file
    ]
)
def test_extract_values(type_: str, description: str, expected_literals: list):
    assert extract_valid_literals(description, type_) == set(expected_literals)
