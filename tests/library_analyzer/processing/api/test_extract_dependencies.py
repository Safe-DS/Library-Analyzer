from typing import Any, TypeAlias

import pytest
from library_analyzer.processing.api import (
    Action,
    Condition,
    ParameterDoesNotHaveType,
    ParameterHasType,
    ParameterHasValue,
    ParameterIsIgnored,
    ParameterIsIllegal,
    ParameterIsNone,
    ParameterIsRestricted,
    ParametersInRelation,
    ParameterWillBeSetTo,
    extract_param_dependencies,
)
from library_analyzer.processing.api._extract_dependencies import ParameterHasNotValue

_CONDTION_TYPE: TypeAlias = ParametersInRelation | ParameterHasValue | ParameterHasNotValue | ParameterIsNone | ParameterHasType | ParameterDoesNotHaveType | Condition
_ACTION_TYPE: TypeAlias = ParameterIsIgnored | ParameterIsIllegal | ParameterWillBeSetTo | ParameterIsRestricted | Action


def _assert_condition(extracted: _CONDTION_TYPE, expected: _CONDTION_TYPE) -> None:
    assert type(extracted) is type(expected)
    assert extracted == expected

    match extracted:
        case ParametersInRelation():
            assert extracted.left_dependee == expected.left_dependee
            assert extracted.right_dependee == expected.right_dependee
            assert extracted.rel_op == expected.rel_op
        case ParameterHasValue():
            print(f"EXTRACTED: {extracted.check_dependee}, EXPECTED: {expected.check_dependee}")
            assert extracted.check_dependee == expected.check_dependee
            assert extracted.value == expected.value
            assert extracted.also == expected.also
        case ParameterIsNone():
            assert extracted.also == expected.also
        case ParameterHasType() | ParameterDoesNotHaveType():
            assert extracted.type_ == expected.type_

    if extracted.combined_with:
        assert len(extracted.combined_with) == len(expected.combined_with)

        for idx, extracted_cond in enumerate(extracted.combined_with):
            _assert_condition(extracted_cond, expected.combined_with[idx])


def _assert_action(extracted: _ACTION_TYPE, expected: _ACTION_TYPE) -> None:
    assert type(extracted) is type(expected)
    assert extracted == expected

    match extracted:
        case ParameterIsIgnored():
            assert extracted.dependee == expected.dependee
        case ParameterWillBeSetTo():
            assert extracted.depender == expected.depender
            assert extracted.value_ == expected.value_


@pytest.mark.parametrize(
    ("param_name", "description", "expected_dependencies"),
    [
        # https://github.com/scikit-learn/scikit-learn/blob/5d145bf760539d40f4e2c50c0f4c46200945c978/sklearn/ensemble/_bagging.py#L606
        (
            "solver",
            "Only available if bootstrap=True.",
            [
                (
                    "solver",
                    ParameterHasValue("Only available if bootstrap equals True", "bootstrap", "True"),
                    ParameterIsIgnored("not ignored"),
                ),
            ],
        ),
        # https://github.com/scikit-learn/scikit-learn/blob/5d145bf760539d40f4e2c50c0f4c46200945c978/sklearn/feature_extraction/text.py#L652
        (
            "tokenizer",
            "Only applies if analyzer == 'word'.",
            [
                (
                    "tokenizer",
                    ParameterHasValue("Only applies if analyzer equals word", "analyzer", "word"),
                    ParameterIsIgnored("not ignored"),
                ),
            ],
        ),
        # Test was derived from previous test.
        (
            "penalty",
            "Only used when solver is set to 'lbfgs'.",
            [
                (
                    "penalty",
                    ParameterHasValue("Only used when solver equals lbfgs", "solver", "lbfgs"),
                    ParameterIsIgnored("not ignored"),
                ),
            ],
        ),
        # Test was derived from previous test.
        (
            "solver",
            "Only used when penalty is None.",
            [
                (
                    "solver",
                    ParameterIsNone("Only used when penalty is None", "penalty"),
                    ParameterIsIgnored("not ignored"),
                ),
            ],
        ),
        # https://github.com/scikit-learn/scikit-learn/blob/5d145bf760539d40f4e2c50c0f4c46200945c978/sklearn/feature_extraction/text.py#L647
        (
            "preprocessor",
            "Only applies if analyzer is not callable.",
            [
                (
                    "preprocessor",
                    ParameterDoesNotHaveType("Only applies if analyzer is not callable", "analyzer", "not callable"),
                    ParameterIsIgnored("not ignored"),
                ),
            ],
        ),
        # https://github.com/scikit-learn/scikit-learn/blob/5d145bf760539d40f4e2c50c0f4c46200945c978/sklearn/ensemble/_gb.py#L996
        (
            "validation_fraction",
            "Only used if n_iter_no_change is set to an integer.",
            [
                (
                    "validation_fraction",
                    ParameterHasType("Only used if n_iter_no_change equals an integer", "n_iter_no_change", "integer"),
                    ParameterIsIgnored("not ignored"),
                ),
            ],
        ),
        # https://github.com/scikit-learn/scikit-learn/blob/5d145bf760539d40f4e2c50c0f4c46200945c978/sklearn/linear_model/_logistic.py#L194-L195
        (
            "intercept_scaling",
            "Useful only when the solver 'liblinear' is used and self.fit_intercept is set to True.",
            [
                (
                    "intercept_scaling",
                    ParameterHasValue(
                        "only when self.fit_intercept equals True",
                        "self.fit_intercept",
                        "True",
                        [
                            ParameterHasValue(
                                "only when the solver liblinear is used",
                                "solver",
                                "liblinear",
                                check_dependee=True,
                            ),
                        ],
                    ),
                    ParameterIsIgnored("not ignored"),
                ),
            ],
        ),
        # Test was derived from previous test.
        (
            "penalty",
            "Only available if solver='lbfgs' or solver='linear'.",
            [
                (
                    "penalty",
                    ParameterHasValue("Only available if solver equals lbfgs", "solver", "lbfgs"),
                    ParameterIsIgnored("not ignored"),
                ),
                (
                    "penalty",
                    ParameterHasValue("Only available if solver equals linear", "solver", "linear"),
                    ParameterIsIgnored("not ignored"),
                ),
            ],
        ),
        # Test was derived from previous test.
        (
            "n_jobs",
            "Only when self.fit_intercept is True.",
            [
                (
                    "n_jobs",
                    ParameterHasValue("Only when self.fit_intercept is True", "self.fit_intercept", "True"),
                    ParameterIsIgnored("not ignored"),
                ),
            ],
        ),
        # https://github.com/scikit-learn/scikit-learn/blob/5d145bf760539d40f4e2c50c0f4c46200945c978/sklearn/linear_model/_logistic.py#L966-L968
        (
            "n_jobs",
            (
                "This parameter is ignored when the solver is set to 'liblinear' regardless of whether 'multi_class' is"
                " specified or not."
            ),
            [
                (
                    "n_jobs",
                    ParameterHasValue("ignored when the solver equals liblinear", "solver", "liblinear"),
                    ParameterIsIgnored("ignored"),
                ),
            ],
        ),
        # https://github.com/scikit-learn/scikit-learn/blob/5d145bf760539d40f4e2c50c0f4c46200945c978/sklearn/metrics/_classification.py#L2455-L2456
        (
            "digits",
            "When output_dict is True, this will be ignored and the returned values will not be rounded.",
            [
                (
                    "digits",
                    ParameterHasValue("When output_dict is True, this will be ignored", "output_dict", "True"),
                    ParameterIsIgnored("ignored"),
                ),
            ],
        ),
        # https://github.com/scikit-learn/scikit-learn/blob/5d145bf760539d40f4e2c50c0f4c46200945c978/sklearn/linear_model/_stochastic_gradient.py#L1030
        (
            "random_state",
            "Used for shuffling the data, when shuffle is set to True.",
            [
                (
                    "random_state",
                    ParameterHasValue("Used for shuffling the data, when shuffle equals True", "shuffle", "True"),
                    ParameterIsIgnored("not ignored"),
                ),
            ],
        ),
        # Test was derived from previous test.
        (
            "random_state",
            "Used for shuffling the data, when shuffle=True.",
            [
                (
                    "random_state",
                    ParameterHasValue("Used for shuffling the data, when shuffle equals True", "shuffle", "True"),
                    ParameterIsIgnored("not ignored"),
                ),
            ],
        ),
        # https://github.com/scikit-learn/scikit-learn/blob/5d145bf760539d40f4e2c50c0f4c46200945c978/sklearn/linear_model/_ridge.py#L503
        (
            "random_state",
            "Used when solver == 'sag' or 'saga' to shuffle the data.",
            [
                (
                    "random_state",
                    ParameterHasValue("Used when solver equals sag", "solver", "sag"),
                    ParameterIsIgnored("not ignored"),
                ),
                (
                    "random_state",
                    ParameterHasValue("Used when solver equals saga", "solver", "saga"),
                    ParameterIsIgnored("not ignored"),
                ),
            ],
        ),
        # test was derived from the previous test case
        (
            "random_state",
            "Used when solver == 'sag', 'adam', or 'saga' to shuffle the data.",
            [
                (
                    "random_state",
                    ParameterHasValue("Used when solver equals sag", "solver", "sag"),
                    ParameterIsIgnored("not ignored"),
                ),
                (
                    "random_state",
                    ParameterHasValue("Used when solver equals adam", "solver", "adam"),
                    ParameterIsIgnored("not ignored"),
                ),
                (
                    "random_state",
                    ParameterHasValue("Used when solver equals saga", "solver", "saga"),
                    ParameterIsIgnored("not ignored"),
                ),
            ],
        ),
        # Test was derived from previous test.
        (
            "random_state",
            "Used when solver is 'sag'.",
            [
                (
                    "random_state",
                    ParameterHasValue("Used when solver is sag", "solver", "sag"),
                    ParameterIsIgnored("not ignored"),
                ),
            ],
        ),
        # https://github.com/scikit-learn/scikit-learn/blob/5d145bf760539d40f4e2c50c0f4c46200945c978/sklearn/decomposition/_pca.py#L224
        (
            "random_state",
            "Used when the 'randomized' or 'arpack' solvers are used.",
            [
                (
                    "random_state",
                    ParameterHasValue(
                        "Used when the randomized or arpack solvers are used.",
                        "arpack",
                        "solvers",
                        check_dependee=True,
                    ),
                    ParameterIsIgnored("not ignored"),
                ),
                (
                    "random_state",
                    ParameterHasValue(
                        "Used when the randomized solvers are used.",
                        "randomized",
                        "solvers",
                        check_dependee=True,
                    ),
                    ParameterIsIgnored("not ignored"),
                ),
            ],
        ),
        # https://github.com/scikit-learn/scikit-learn/blob/5d145bf760539d40f4e2c50c0f4c46200945c978/sklearn/decomposition/_kernel_pca.py#L72-L73
        (
            "alpha",
            (
                "Hyperparameter of the ridge regression that learns the inverse transform (when "
                "fit_inverse_transform=True)."
            ),
            [
                (
                    "alpha",
                    ParameterHasValue("(when fit_inverse_transform equals True).", "fit_inverse_transform", "True"),
                    ParameterIsIgnored("not ignored"),
                ),
            ],
        ),
        # https://github.com/scikit-learn/scikit-learn/blob/5d145bf760539d40f4e2c50c0f4c46200945c978/sklearn/model_selection/_split.py#L2560-L2561
        (
            "shuffle",
            "If shuffle=False then stratify must be None.",
            [
                (
                    "shuffle",
                    ParameterHasValue("If shuffle equals False", "shuffle", "False"),
                    ParameterWillBeSetTo("must be None", "stratify", "None"),
                ),
            ],
        ),
        # Test was derived from previous test.
        (
            "shuffle",
            "If shuffle=False then algorithm must be None.",
            [
                (
                    "shuffle",
                    ParameterHasValue("If shuffle equals False", "shuffle", "False"),
                    ParameterWillBeSetTo("must be None", "algorithm", "None"),
                ),
            ],
        ),
        # https://github.com/scikit-learn/scikit-learn/blob/6b367d54ef2a055e9a7d54eaf6f035974e66305b/sklearn/decomposition/_truncated_svd.py#L54
        (
            "n_components",
            "If algorithm equals arpack, must be strictly less than the number of features.",
            [
                (
                    "n_components",
                    ParameterHasValue("If algorithm equals arpack", "algorithm", "arpack"),
                    ParameterIsRestricted(", must be strictly less than the number of features"),
                ),
            ],
        ),
        # https://github.com/scikit-learn/scikit-learn/blob/6b367d54ef2a055e9a7d54eaf6f035974e66305b/sklearn/linear_model/_logistic.py#L185-L186
        (
            "dual",
            "Prefer dual=False when n_samples > n_features.",
            [
                (
                    "dual",
                    ParametersInRelation("when n_samples > n_features", "n_samples", "n_features", ">"),
                    ParameterWillBeSetTo("Prefer dual equals False", "dual", "False"),
                ),
            ],
        ),
        # Test was derived from previous test.
        (
            "dual",
            "Prefer dual=False when n_samples < n_features.",
            [
                (
                    "dual",
                    ParametersInRelation("when n_samples < n_features", "n_samples", "n_features", "<"),
                    ParameterWillBeSetTo("Prefer dual equals False", "dual", "False"),
                ),
            ],
        ),
        # Test was derived from previous test.
        (
            "dual",
            "Prefer dual=False when n_samples <= n_features.",
            [
                (
                    "dual",
                    ParametersInRelation("when n_samples <= n_features", "n_samples", "n_features", "<="),
                    ParameterWillBeSetTo("Prefer dual equals False", "dual", "False"),
                ),
            ],
        ),
        # Test was derived from previous test.
        (
            "dual",
            "Prefer dual=False when n_samples >= n_features.",
            [
                (
                    "dual",
                    ParametersInRelation("when n_samples >= n_features", "n_samples", "n_features", ">="),
                    ParameterWillBeSetTo("Prefer dual equals False", "dual", "False"),
                ),
            ],
        ),
        # https://github.com/scikit-learn/scikit-learn/blob/5d145bf760539d40f4e2c50c0f4c46200945c978/sklearn/model_selection/_split.py#L1778-L1779
        (
            "test_size",
            "If train_size is also None, it will be set to 0.1.",
            [
                (
                    "test_size",
                    ParameterIsNone("If train_size is also None", "train_size", also=True),
                    ParameterWillBeSetTo("it will be set to 0.1", "this_parameter", "0.1"),
                ),
            ],
        ),
        # https://github.com/scikit-learn/scikit-learn/blob/5d145bf760539d40f4e2c50c0f4c46200945c978/sklearn/neighbors/_nearest_centroid.py#L58
        (
            "metric",
            "metric='precomputed' was deprecated and now raises an error",
            [
                (
                    "metric",
                    ParameterHasValue(
                        "metric equals precomputed was deprecated and now raises an error",
                        "metric",
                        "precomputed",
                    ),
                    ParameterIsIllegal("raises an error"),
                ),
            ],
        ),
        # https://github.com/scikit-learn/scikit-learn/blob/5d145bf760539d40f4e2c50c0f4c46200945c978/sklearn/pipeline.py#L1011
        (
            "transformer_weight",
            "Raises ValueError if key not present in transformer_list",
            [
                (
                    "transformer_weight",
                    Condition("Raises ValueError if key not present in transformer_list"),
                    ParameterIsIllegal("Raises ValueError"),
                ),
            ],
        ),
        # https://github.com/scikit-learn/scikit-learn/blob/4b352163d555d85f721e68a520a4b19b7a406637/sklearn/decomposition/_dict_learning.py#L1904
        (
            "max_iter",
            "If ``max_iter`` is not None, ``n_iter`` is ignored.",
            [
                (
                    "max_iter",
                    ParameterHasValue("If max_iter is not None, n_iter is ignored", "max_iter", "not None"),
                    ParameterIsIgnored("ignored", "n_iter"),
                ),
            ],
        ),
        # this case was derived from the previous one
        (
            "max_iter",
            "If ``max_iter`` is not None, ``n_iter`` will be ignored.",
            [
                (
                    "max_iter",
                    ParameterHasValue("If max_iter is not None, n_iter will be ignored", "max_iter", "not None"),
                    ParameterIsIgnored("ignored", "n_iter"),
                ),
            ],
        ),
        # https://github.com/scikit-learn/scikit-learn/blob/4b352163d555d85f721e68a520a4b19b7a406637/sklearn/cluster/_spectral.py#L450
        (
            "n_neighbors",
            "Ignored for ``affinity='rbf'``.",
            [
                (
                    "n_neighbors",
                    ParameterHasValue("Ignored for affinity equals rbf", "affinity", "rbf"),
                    ParameterIsIgnored("ignored", "this_parameter"),
                ),
            ],
        ),
        # https://github.com/scikit-learn/scikit-learn/blob/457b02c61a2f3cd353d2997929b67a3ef890bf60/sklearn/cluster/_agglomerative.py#L782
        (
            "affinity",
            "If linkage is 'ward', only 'euclidean' is accepted.",
            [
                (
                    "affinity",
                    ParameterHasValue("If linkage is ward", "linkage", "ward"),
                    ParameterWillBeSetTo("only euclidean is accepted", "this_parameter", "euclidean")
                ),
            ],
        ),
        # https://github.com/scikit-learn/scikit-learn/blob/457b02c61a2f3cd353d2997929b67a3ef890bf60/sklearn/datasets/_samples_generator.py#L915C9-L916
        (
            "centers",
            "If n_samples is array-like, centers must be either None or an array of length equal to the length of "
            "n_samples.",
            [
                (
                    "centers",
                    ParameterHasType("If n_samples is array-like", "n_samples", "array-like"),
                    ParameterIsRestricted("centers must be either None or an array of length equal to the length of "
                                          "n_samples")
                )
            ]
        ),
        # https://github.com/scikit-learn/scikit-learn/blob/457b02c61a2f3cd353d2997929b67a3ef890bf60/sklearn/decomposition/_nmf.py#L1942-L1943C46
        (
            "random_state",
            "Used for initialisation (when ``init`` == 'nndsvdar' or 'random'), and in Coordinate Descent.",
            [
                (
                    "random_state",
                    ParameterHasValue(
                        "Used for initialisation (when init equals nndsvdar",
                        "init",
                        "nndsvdar"
                    ),
                    ParameterIsIgnored("not ignored")
                ),
                (
                    "random_state",
                    ParameterHasValue(
                        "Used for initialisation (when init equals random",
                        "init",
                        "random"
                    ),
                    ParameterIsIgnored("not ignored")
                )
            ]
        ),
        # https://github.com/scikit-learn/scikit-learn/blob/93e22cdd8dff96fa3870475f40e435083bce8ad0/sklearn/decomposition/_dict_learning.py#L2013C75-L2014C31
        (
            "max_no_improvement",
            "Used only if `max_iter` is not None.",
            [
                (
                    "max_no_improvement",
                    ParameterHasValue(
                        "Used only if max_iter is not None",
                        "max_iter",
                        "not None"
                    ),
                    ParameterIsIgnored("not ignored")
                ),
            ]
        ),
        # https://github.com/scikit-learn/scikit-learn/blob/93e22cdd8dff96fa3870475f40e435083bce8ad0/sklearn/decomposition/_nmf.py#L1474C1-L1475C46
        (
            "random_state",
            " Used for initialisation (when ``init`` == 'nndsvdar' or 'random'), and in Coordinate Descent.",
            [
                (
                    "random_state",
                    ParameterHasValue(
                        "Used for initialisation (when init equals nndsvdar",
                        "init",
                        "nndsvdar"
                    ),
                    ParameterIsIgnored("not ignored")
                ),
                (
                    "random_state",
                    ParameterHasValue(
                        "Used for initialisation (when init equals random",
                        "init",
                        "random"
                    ),
                    ParameterIsIgnored("not ignored")
                ),
            ]
        ),
    ],
)
def test_extract_param_dependencies(
    param_name: str,
    description: str,
    expected_dependencies: list[tuple[str, _CONDTION_TYPE, _ACTION_TYPE]],
) -> None:
    extracted_dependencies = extract_param_dependencies(param_name, description)

    assert len(extracted_dependencies) == len(expected_dependencies)

    for idx, extracted_dep in enumerate(extracted_dependencies):
        expected_dep: tuple[str, _CONDTION_TYPE, _ACTION_TYPE] = expected_dependencies[idx]
        _assert_condition(extracted_dep[1], expected_dep[1])
        _assert_action(extracted_dep[2], expected_dep[2])


@pytest.mark.parametrize(
    ("dictionary", "expected_class"),
    [
        (
            {
                "variant": "condition",
                "condition": "Only available if x is a vector",
                "dependee": "x",
                "combined_with": [],
            },
            Condition(condition="Only available if x is a vector", dependee="x", combined_with=[]),
        ),
        (
            {
                "variant": "in_relation",
                "condition": "if x > y",
                "combined_with": [],
                "left_dependee": "x",
                "right_dependee": "y",
                "rel_op": ">",
            },
            ParametersInRelation(cond="if x > y", left_dependee="x", right_dependee="y", rel_op=">"),
        ),
        (
            {
                "variant": "has_value",
                "condition": "Only available if x equals auto",
                "dependee": "x",
                "value": "auto",
                "combined_with": [],
                "check_dependee": False,
                "also": False,
            },
            ParameterHasValue(
                cond="Only available if x equals auto",
                dependee="x",
                value="auto",
                combined_with=[],
                check_dependee=False,
                also=False,
            ),
        ),
        ({"variant": "no_value", "condition": "x has no value"}, ParameterHasNotValue("x has no value")),
        (
            {"variant": "is_none", "condition": "Only available if x is None", "dependee": "x", "also": False},
            ParameterIsNone(cond="Only available if x is None", dependee="x", also=False),
        ),
        (
            {
                "variant": "has_type",
                "condition": "Only available if x is an integer",
                "dependee": "x",
                "type": "integer",
            },
            ParameterHasType(cond="Only available if x is an integer", dependee="x", type_="integer"),
        ),
        (
            {"variant": "no_type", "condition": "if x is not callable", "dependee": "x", "type": "not callable"},
            ParameterDoesNotHaveType(cond="if x is not callable", dependee="x", type_="not callable"),
        ),
    ],
)
def test_cond_dict_methods(dictionary: dict[str, Any], expected_class: Condition) -> None:
    from_dict_class = Condition.from_dict(dictionary)
    assert from_dict_class == expected_class
    assert expected_class.to_dict() == dictionary


@pytest.mark.parametrize(
    ("dictionary", "expected_class"),
    [
        ({"variant": "action", "action": "will be set to None"}, Action(action="will be set to None")),
        (
            {"variant": "is_ignored", "action": "ignored", "dependee": "this_parameter"},
            ParameterIsIgnored(action_="ignored", dependee="this_parameter"),
        ),
        ({"variant": "is_illegal", "action": "raises KeyError"}, ParameterIsIllegal(action_="raises KeyError")),
        (
            {"variant": "will_be_set", "action": "y will be set to None", "depender": "y", "value": "None"},
            ParameterWillBeSetTo(action_="y will be set to None", depender="y", value_="None"),
        ),
        (
            {"variant": "is_restricted", "action": "x must be between 0 and 1"},
            ParameterIsRestricted(action_="x must be between 0 and 1"),
        ),
    ],
)
def test_action_dict_methods(dictionary: dict[str, Any], expected_class: Action) -> None:
    from_dict_class = Action.from_dict(dictionary)
    assert from_dict_class == expected_class
    assert expected_class.to_dict() == dictionary


def test_cond_key_error() -> None:
    d = {"variant": "super_condition", "condition": "this must be super variable"}

    with pytest.raises(KeyError):
        Condition.from_dict(d)


def test_action_key_error() -> None:
    d = {"variant": "is_super_restricted", "action": "x must be 1 in all cases"}

    with pytest.raises(KeyError):
        Action.from_dict(d)
