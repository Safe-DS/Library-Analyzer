import pytest
from library_analyzer.processing.api import (
    Action,
    Condition,
    ParameterHasValue,
    ParameterIsIgnored,
    ParameterIsNone,
    ParameterIsNotCallable,
    extract_param_dependencies,
)


@pytest.mark.parametrize(
    ("param_name", "description", "expected_dependencies"),
    [
        (
            "penalty",
            "Only used if solver is set to 'lbfgs'.",
            [
                (
                    "penalty",
                    ParameterHasValue("Only used if solver is lbfgs", "solver", "lbfgs"),
                    ParameterIsIgnored("not ignored")
                )
            ]
        ),
        (
            "solver",
            "Only available when penalty equals 0.05.",
            [
                (
                    "solver",
                    ParameterHasValue("Only available when penalty equals 0.05", "penalty", "0.05"),
                    ParameterIsIgnored("not ignored")
                )
            ]
        ),
        (
            "penalty",
            "Only applies when solver=='lbfgs'.",
            [
                (
                    "penalty",
                    ParameterHasValue("Only applies when solver equals lbfgs", "solver", "lbfgs"),
                    ParameterIsIgnored("not ignored")
                )
            ]
        ),
        (
            "solver",
            "Only used when penalty is None.",
            [
                (
                    "solver",
                    ParameterIsNone("Only used when penalty is None", "penalty"),
                    ParameterIsIgnored("not ignored")
                )
            ]
        ),
        (
            "penalty",
            "Only available if solver='lbfgs' or solver='linear'.",
            [
                (
                    "penalty",
                    ParameterHasValue("Only available if solver equals lbfgs", "solver", "lbfgs"),
                    ParameterIsIgnored("not ignored")
                ),
                (
                    "penalty",
                    ParameterHasValue("Only available if solver equals linear", "solver", "linear"),
                    ParameterIsIgnored("not ignored")
                )
            ]
        ),
        (
            "preprocessor",
            "Only applies if analyzer is not callable.",
            [
                (
                    "preprocessor",
                    ParameterIsNotCallable("Only applies if analyzer is not callable", "analyzer"),
                    ParameterIsIgnored("not ignored")
                )
            ]
        ),
        (
            "validation_fraction",
            "Only used if n_iter_no_change is set to an integer.",
            [
                (
                    "validation_fraction",
                    ParameterHasValue("Only used if n_iter_no_change is an integer", "n_iter_no_change", "an integer"),
                    ParameterIsIgnored("not ignored")
                )
            ]
        ),
        (
            "n_jobs",
            "Only when self.fit_intercept is True.",
            [
                (
                    "n_jobs",
                    ParameterHasValue("Only when self.fit_intercept is True", "self.fit_intercept", "True"),
                    ParameterIsIgnored("not ignored")
                )
            ]
        ),
        (
            "n_jobs",
            "Useful only when the solver 'liblinear' is used and self.fit_intercept is set to True.",
            [
                (
                    "n_jobs",
                    ParameterHasValue(
                        "only when the solver liblinear is used", "solver", "liblinear", "self.fit_intercept",
                        check_dependee=True
                    ),
                    ParameterIsIgnored("not ignored")
                ),
                (
                    "n_jobs",
                    ParameterHasValue("only when self.fit_intercept is True", "self.fit_intercept", "True", "solver"),
                    ParameterIsIgnored("not ignored")
                )
            ]
        ),
        (
            "n_jobs",
            "This parameter is ignored when the solver is set to 'liblinear' regardless of whether 'multi_class' is "
            "specified or not.",
            [
                (
                    "n_jobs",
                    ParameterHasValue("ignored when the solver is liblinear", "solver", "liblinear"),
                    ParameterIsIgnored("ignored")
                )
            ]
        ),
        (
            "penalty",
            "When solver equals adam, this will be ignored.",
            [
                (
                    "penalty",
                    ParameterHasValue("When solver equals adam, this will be ignored.", "solver", "adam"),
                    ParameterIsIgnored("ignored")
                )
            ]
        ),

    ]
)
def test_extract_param_dependencies(
    param_name: str,
    description: str,
    expected_dependencies: list[tuple[str, Condition, Action]]
) -> None:
    assert extract_param_dependencies(param_name, description, show_matches=True) == expected_dependencies
