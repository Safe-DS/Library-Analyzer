import pytest
from library_analyzer.processing.api._extract_valid_values import extract_valid_literals


@pytest.mark.parametrize(
    ("type_", "description", "expected_literals"),
    [
        (
            "str",
            (
                'If "mean", then replace missing values using the mean along each column. '
                'If "median", then replace missing values using the median along each column. '
                'If "most_frequent", then replace missing using the most frequent value along each column. '
                'If "constant", then replace missing values with fill_value.'
            ),
            ['"mean"', '"median"', '"most_frequent"', '"constant"'],
        ),
        ("str or bool", "Valid values are [False, None, 'allow-nan']", ["True", "False", "None", '"allow-nan"']),
        ("str or bool", "Valid values are [False, None, 'sparse matrix']", ["True", "False", "None", '"sparse matrix"']),
        ("str or bool", "Valid values are 'allow-nan', 'lbfgs', None and 'False'.", ["None", "True", "False", '"lbfgs"', '"allow-nan"']),
        ("str or bool", "If `'None'`, this parameter will use the default value.", ["unlistable_str", "None", "True", "False"]),
        ("str or bool", "If `'alpha'` is a callable, the estimator will use it to calculate the value.", ["unlistable_str","True", "False"]),
        ("str or bool", "If False, the estimator will only use the default calculation.", ["unlistable_str","True", "False"]),
        ("str, float", "If float, the value must be between 0 and 1.", ["unlistable_str"]),
        (
            "str",
            (
                "If 'mean', then replace missing values using the mean along each column."
                "If 'median', then replace "
                "missing values using the median along each column. If 'most_frequent', then replace missing using the "
                "most frequent value along each column. If 'constant', then replace missing values with fill_value."
            ),
            ['"median"', '"most_frequent"', '"constant"', '"mean"'],
        ),
        (
            "str, list or tuple of str",
            (
                'Attribute name(s) given as string or a list/tuple of strings Eg.: ["coef_", "estimator_", ...],'
                ' "coef_" If None, estimator is considered fitted if there exist an attribute that ends with a'
                " underscore and does not start with double underscore."
            ),
            ["None", "unlistable_str"],
        ),
        (
            "bool or 'allow-nan'",
            (
                "Whether to raise an error on np.inf, np.nan, pd.NA in X. This parameter does not influence whether y"
                " can have np.inf, np.nan, pd.NA values. The possibilities are: \n\n\tTrue: Force all values of X to be"
                " finite. \n\tFalse: accepts np.inf, np.nan, pd.NA in X. \n\t'allow-nan': accepts only np.nan or pd.NA"
                " values in X. Values cannot be infinite. \n\n.. versionadded: 0.20 force_all_finite accepts the string"
                " 'allow-nan'. \n\n.. versionchanged: 0.23 Accepts pd.NA and converts it into np.nan"
            ),
            ['"allow-nan"', "False", "True"],
        ),
        (
            '{"random", "best"}',
            (
                'The strategy used to choose the split at each node. Supported strategies are "best" to choose the best'
                ' split and "random" to choose the best random split.'
            ),
            ['"best"', '"random"'],
        ),
        (
            "bool or str",
            (
                "When set to True, change the display of 'values' and/or 'samples' to be proportions and percentages "
                "respectively."
            ),
            ["False", "True", "unlistable_str"],
        ),
        (
            "int, RandomState instance or None",
            (
                "Controls the randomness of the estimator. The features are always randomly permuted at each split,"
                ' even if splitter is set to "best". When max_features < n_features, the algorithm will select'
                " max_features at random at each split before finding the best split among them. But the best found"
                " split may vary across different runs, even if max_features=n_features. That is the case, if the"
                " improvement of the criterion is identical for several splits and one split has to be selected at"
                " random. To obtain a deterministic behaviour during fitting, random_state has to be fixed to an"
                " integer. See :term:Glossary <random_state> for details."
            ),
            ["None"],
        ),
        ("float", "Independent term in kernel function. It is only significant in 'poly' and 'sigmoid'.", []),
        (
            "float",
            (
                "When self.fit_intercept is True, instance vector x becomes [x, self.intercept_scaling], i.e. a"
                ' "synthetic" feature with constant value equals to intercept_scaling is appended to the instance'
                " vector. The intercept becomes intercept_scaling * synthetic feature weight Note! the synthetic"
                " feature weight is subject to l1/l2 regularization as all other features. To lessen the effect of"
                " regularization on synthetic feature weight (and therefore on the intercept) intercept_scaling has to"
                " be increased."
            ),
            [],
        ),
    ],
)
def test_extract_values(type_: str, description: str, expected_literals: list) -> None:
    assert extract_valid_literals(description, type_) == set(expected_literals)
