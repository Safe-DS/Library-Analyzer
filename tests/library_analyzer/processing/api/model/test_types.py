from copy import deepcopy
from typing import Any

import pytest
from library_analyzer.processing.api.model import (
    Attribute,
    BoundaryType,
    EnumType,
    NamedType,
    Parameter,
    ParameterAssignment,
    ParameterDocstring,
    create_type,
)


@pytest.mark.parametrize(
    ("docstring_type", "expected"),
    [
        ("", {}),
        (
            "int, or None, 'manual', {'auto', 'sqrt', 'log2'}, default='auto'",
            {
                "kind": "UnionType",
                "types": [
                    {"kind": "EnumType", "values": {"auto", "log2", "sqrt"}},
                    {"kind": "NamedType", "name": "int"},
                    {"kind": "NamedType", "name": "None"},
                    {"kind": "NamedType", "name": "'manual'"},
                ],
            },
        ),
        (
            "tuple of slice, AUTO or array of shape (12,2), default=(slice(70, 195), slice(78, 172))",
            {
                "kind": "UnionType",
                "types": [
                    {"kind": "NamedType", "name": "tuple of slice"},
                    {"kind": "NamedType", "name": "AUTO"},
                    {"kind": "NamedType", "name": "array of shape (12,2)"},
                ],
            },
        ),
        ("object", {"kind": "NamedType", "name": "object"}),
        (
            "ndarray, shape (n_samples,), default=None",
            {
                "kind": "UnionType",
                "types": [
                    {"kind": "NamedType", "name": "ndarray"},
                    {"kind": "NamedType", "name": "shape (n_samples,)"},
                ],
            },
        ),
        (
            "estor adventus or None",
            {
                "kind": "UnionType",
                "types": [
                    {"kind": "NamedType", "name": "estor adventus"},
                    {"kind": "NamedType", "name": "None"},
                ],
            },
        ),
        (
            "int or array-like, shape (n_samples, n_classes) or (n_samples, 1)                     when binary.",
            {
                "kind": "UnionType",
                "types": [
                    {"kind": "NamedType", "name": "int"},
                    {"kind": "NamedType", "name": "array-like"},
                    {
                        "kind": "NamedType",
                        "name": "shape (n_samples, n_classes) or (n_samples, 1) when binary.",
                    },
                ],
            },
        ),
    ],
)
def test_union_from_string(docstring_type: str, expected: dict[str, Any]) -> None:
    result = create_type(ParameterDocstring(docstring_type, "", ""))
    if result is None:
        assert expected == {}
    else:
        assert result.to_dict() == expected


@pytest.mark.parametrize(
    ("description", "expected"),
    [
        (
            "Scale factor between inner and outer circle in the range `[0, 1)`",
            {
                "base_type": "float",
                "kind": "BoundaryType",
                "max": 1.0,
                "max_inclusive": False,
                "min": 0.0,
                "min_inclusive": True,
            },
        ),
        (
            (
                "Tolerance for singular values computed by svd_solver == 'arpack'.\nMust be of range [1,"
                " infinity].\n\n.. versionadded:: 0.18.0"
            ),
            {
                "base_type": "float",
                "kind": "BoundaryType",
                "max": "Infinity",
                "max_inclusive": True,
                "min": 1.0,
                "min_inclusive": True,
            },
        ),
        ("", {}),
    ],
)
def test_boundary_from_string(description: str, expected: dict[str, Any]) -> None:
    result = create_type(ParameterDocstring("", "", description))
    if result is None:
        assert expected == {}
    else:
        assert result.to_dict() == expected


@pytest.mark.parametrize(
    ("docstring_type", "docstring_description", "expected"),
    [
        (
            "int or 'Auto', or {'today', 'yesterday'}",
            "int in the range `[0, 10]`",
            {
                "kind": "UnionType",
                "types": [
                    {
                        "base_type": "int",
                        "kind": "BoundaryType",
                        "max": 10.0,
                        "max_inclusive": True,
                        "min": 0.0,
                        "min_inclusive": True,
                    },
                    {"kind": "EnumType", "values": {"yesterday", "today"}},
                    {"kind": "NamedType", "name": "int"},
                    {"kind": "NamedType", "name": "'Auto'"},
                ],
            },
        ),
    ],
)
def test_boundary_and_union_from_string(
    docstring_type: str,
    docstring_description: str,
    expected: dict[str, Any],
) -> None:
    result = create_type(
        ParameterDocstring(type=docstring_type, default_value="", description=docstring_description),
    )

    if result is None:
        assert expected == {}
    else:
        assert result.to_dict() == expected


def test_correct_hash() -> None:
    parameter = Parameter(
        id_="test/test.Test/test/test_parameter_for_hashing",
        name="test_parameter_for_hashing",
        qname="test.Test.test.test_parameter_for_hashing",
        default_value="'test_str'",
        assigned_by=ParameterAssignment.POSITION_OR_NAME,
        is_public=True,
        docstring=ParameterDocstring("'hashvalue'", "r", "r"),
    )
    assert hash(parameter) == hash(deepcopy(parameter))
    enum_values = frozenset({"a", "b", "c"})
    enum_type = EnumType(enum_values, "full_match")
    assert enum_type == deepcopy(enum_type)
    assert hash(enum_type) == hash(deepcopy(enum_type))
    assert enum_type == EnumType(deepcopy(enum_values), "full_match")
    assert hash(enum_type) == hash(EnumType(deepcopy(enum_values), "full_match"))
    assert enum_type != EnumType(frozenset({"a", "b"}), "full_match")
    assert hash(enum_type) != hash(EnumType(frozenset({"a", "b"}), "full_match"))
    assert NamedType("a") == NamedType("a")
    assert hash(NamedType("a")) == hash(NamedType("a"))
    assert NamedType("a") != NamedType("b")
    assert hash(NamedType("a")) != hash(NamedType("b"))
    attribute = Attribute(
        "boundary",
        BoundaryType(
            base_type="int",
            min=0,
            max=1,
            min_inclusive=True,
            max_inclusive=True,
        ),
    )
    assert attribute == deepcopy(attribute)
    assert hash(attribute) == hash(deepcopy(attribute))


@pytest.mark.parametrize(
    ("string", "expected"),
    [
        (
            (
                "float, default=0.0 Tolerance for singular values computed by svd_solver == 'arpack'.\nMust be of range"
                " [0.0, infinity).\n\n.. versionadded:: 0.18.0"
            ),
            BoundaryType(
                base_type="float",
                min=0,
                max="Infinity",
                min_inclusive=True,
                max_inclusive=True,
            ),
        ),
        (
            """If bootstrap is True, the number of samples to draw from X\nto train each base estimator.\n\n
            - If None (default), then draw `X.shape[0]` samples.\n- If int, then draw `max_samples` samples.\n
            - If float, then draw `max_samples * X.shape[0]` samples. Thus,\n  `max_samples` should be in the interval `(0.0, 1.0]`.\n\n..
            versionadded:: 0.22""",
            BoundaryType(
                base_type="float",
                min=0,
                max=1,
                min_inclusive=False,
                max_inclusive=True,
            ),
        ),
        (
            """When building the vocabulary ignore terms that have a document\nfrequency strictly lower than the given threshold. This value is also\n
            called cut-off in the literature.\nIf float in range of [0.0, 1.0], the parameter represents a proportion\nof documents, integer absolute counts.\n
            This parameter is ignored if vocabulary is not None.""",
            BoundaryType(
                base_type="float",
                min=0,
                max=1,
                min_inclusive=True,
                max_inclusive=True,
            ),
        ),
        (
            """float in range [0.0, 1.0] or int, default=1.0 When building the vocabulary ignore terms that have a document\n
            frequency strictly higher than the given threshold (corpus-specific\nstop words).\nIf float, the parameter represents a proportion of documents, integer\n
            absolute counts.\nThis parameter is ignored if vocabulary is not None.""",
            BoundaryType(
                base_type="float",
                min=0,
                max=1,
                min_inclusive=True,
                max_inclusive=True,
            ),
        ),
        (
            (
                "Tolerance for singular values computed by svd_solver == 'arpack'.\nMust be of range [-2, -1].\n\n.."
                " versionadded:: 0.18.0"
            ),
            BoundaryType(
                base_type="float",
                min=-2,
                max=-1,
                min_inclusive=True,
                max_inclusive=True,
            ),
        ),
        (
            "Damping factor in the range (-1, -0.5)",
            BoundaryType(
                base_type="float",
                min=-1,
                max=-0.5,
                min_inclusive=False,
                max_inclusive=False,
            ),
        ),
        (
            "'max_samples' should be in the interval (-1.0, -0.5]",
            BoundaryType(
                base_type="float",
                min=-1.0,
                max=-0.5,
                min_inclusive=False,
                max_inclusive=True,
            ),
        ),
    ],
)
def test_boundaries_from_string(string: str, expected: BoundaryType) -> None:
    ref_type = BoundaryType.from_string(string)
    assert ref_type == expected


@pytest.mark.parametrize(
    ("docstring_type", "expected"),
    [
        ('{"frobenius", "spectral"}, default="frobenius"', {"frobenius", "spectral"}),
        (
            "{'strict', 'ignore', 'replace'}, default='strict'",
            {"strict", "ignore", "replace"},
        ),
        (
            "{'linear', 'poly',             'rbf', 'sigmoid', 'cosine', 'precomputed'}, default='linear'",
            {"linear", "poly", "rbf", "sigmoid", "cosine", "precomputed"},
        ),
        # https://github.com/lars-reimann/sem21/pull/30#discussion_r771288528
        (r"{\"frobenius\", \'spectral\'}", set()),
        (r"""{"frobenius'}""", set()),
        (r"""{'spectral"}""", set()),
        (r"""{'text\", \"that'}""", {'text", "that'}),
        (r"""{'text", "that'}""", {'text", "that'}),
        (r"{'text\', \'that'}", {"text', 'that"}),
        (r"{'text', 'that'}", {"text", "that"}),
        (r"""{"text\', \'that"}""", {"text', 'that"}),
        (r"""{"text', 'that"}""", {"text', 'that"}),
        (r"""{"text\", \"that"}""", {'text", "that'}),
        (r'{"text", "that"}', {"text", "that"}),
        (r"""{\"not', 'be', 'matched'}""", {", "}),
        ("""{"gini\\", \\"entropy"}""", {'gini", "entropy'}),
        ("""{'best\\', \\'random'}""", {"best', 'random"}),
    ],
)
def test_enum_from_string(docstring_type: str, expected: set[str] | None) -> None:
    result = EnumType.from_string(docstring_type)
    if result is not None:
        assert result.values == expected
