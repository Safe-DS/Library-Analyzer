import pytest
from typing import Union
from library_analyzer.processing.api._extract_boundary_values import extract_boundary

Numeric = Union[int, float]
BoundaryValueType = tuple[str, tuple[Numeric | str, bool], tuple[Numeric | str, bool]]

@pytest.mark.parametrize(
    ("type_string", "description", "expected_boundary"),
    [
        (
            "float",
            "Damping factor in the range [0.5, 1.0) is the extent to which the current value is maintained relative to incoming values (weighted 1 - damping). This in order to avoid numerical oscillations when updating these values (messages).",
            [("float", (0.5, True), (1.0, False))]
        ),
        (
            "float",
            "An upper bound on the fraction of training errors and a lower bound of the fraction of support vectors. Should be in the interval (0, 1]. By default 0.5 will be taken.",
            [("float", (0.0, False), (1.0, True))]
        ),
        (
            "non-negative float",
            "Complexity parameter used for Minimal Cost-Complexity Pruning. The subtree with the largest cost complexity that is smaller than ccp_alpha will be chosen. By default, no pruning is performed. See :ref:minimal_cost_complexity_pruning for details.",
            [("float", (0.0, True), ("infinity", False))]
        ),
        (
            "{'scale', 'auto'} or float",
            "Kernel coefficient for 'rbf', 'poly' and 'sigmoid'.\n\nif gamma='scale' (default) is passed then it uses 1 / (n_features * X.var()) as value of gamma,\nif 'auto', uses 1 / n_features\nif float, must be non-negative.\n\n.. versionchanged: 0.22 The default value of gamma changed from 'auto' to 'scale'.",
            [("float", (0.0, True), ("infinity", False))]
        ),
        (
            "int",
            "Degree of the polynomial kernel function ('poly'). Must be non-negative. Ignored by all other kernels.",
            [("int", (0, True), ("infinity", False))]
        ),
        (
            "int",
            "The verbosity level. The default, zero, means silent mode. Range of values is [0, inf].",
            [("int", (0, True), ("infinity", False))]
        ),
        (
            "float",
            "Momentum for gradient descent update. Should be between 0 and 1. Only used when solver='sgd'.",
            [("float", (0.0, True), (1.0, True))]
        ),
        (
            "float",
            "Regularization parameter. The strength of the regularization is inversely proportional to C. Must be strictly positive.",
            [("float", (0.0, False), ("infinity", False))]
        ),
        (
            "int or float",
            "If bootstrap is True, the number of samples to draw from X to train each base estimator.\n\nIf None (default), then draw X.shape[0] samples.\nIf int, then draw max_samples samples.\n    If float, then draw max_samples * X.shape[0] samples. Thus, max_samples should be in the interval (0.0, 1.0].\n\n.. versionadded: 0.22",
            [("float", (0.0, False), (1.0, True))]
        ),
        (
            "int or float",
            "If bootstrap is True, the number of samples to draw from X to train each base estimator.\n\nIf None (default), then draw X.shape[0] samples.\nIf int, then max_samples values in [0, 10].\n    If float, then draw max_samples * X.shape[0] samples. Thus, max_samples should be in the interval (0.0, 1.0].\n\n.. versionadded: 0.22",
            [("int", (0, True), (10, True)),("float", (0.0, False), (1.0, True))]
        ),
        (
            "bool",
            "Whether to allow array.ndim > 2",
            []
        ),
        (
           "dict, list of dicts, \"balanced\", or None",
            "Weights associated with classes in the form {class_label: weight}. If not given, all classes are supposed to have weight one. For multi-output problems, a list of dicts can be provided in the same order as the columns of y.\n\nNote that for multioutput (including multilabel) weights should be defined for each class of every column in its own dict. For example, for four-class multilabel classification weights should be [{0: 1, 1: 1}, {0: 1, 1: 5}, {0: 1, 1: 1}, {0: 1, 1: 1}] instead of [{1:1}, {2:5}, {3:1}, {4:1}].\n\nThe \"balanced\" mode uses the values of y to automatically adjust weights inversely proportional to class frequencies in the input data: n_samples / (n_classes * np.bincount(y)).\n\nFor multi-output, the weights of each column of y will be multiplied.",
           []
        ),
        (
            "int, RandomState instance or None",
            "Controls the randomness of the estimator. The features are always randomly permuted at each split, even if splitter is set to \"best\". When max_features < n_features, the algorithm will select max_features at random at each split before finding the best split among them. But the best found split may vary across different runs, even if max_features=n_features. That is the case, if the improvement of the criterion is identical for several splits and one split has to be selected at random. To obtain a deterministic behaviour during fitting, random_state has to be fixed to an integer. See :term:Glossary <random_state> for details.",
            []
        ),
        (
            "{'ovo', 'ovr'}",
            "Whether to return a one-vs-rest ('ovr') decision function of shape (n_samples, n_classes) as all other classifiers, or the original one-vs-one ('ovo') decision function of libsvm which has shape (n_samples, n_classes * (n_classes - 1) / 2). However, note that internally, one-vs-one ('ovo') is always used as a multi-class strategy to train models; an ovr matrix is only constructed from the ovo matrix. The parameter is ignored for binary classification.\n\n.. versionchanged: 0.19 decision_function_shape is 'ovr' by default.\n\n.. versionadded: 0.17 decision_function_shape='ovr' is recommended.\n\n.. versionchanged: 0.17 Deprecated decision_function_shape='ovo' and None.",
            []
        )


    ]
)
def test_extract_boundaries(type_string: str, description: str, expected_boundary: set[BoundaryValueType]) -> None:
    assert extract_boundary(type_string, description) == set(expected_boundary)


