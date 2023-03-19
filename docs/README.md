# Library Analyzer

[![PyPI](https://img.shields.io/pypi/v/library-analyzer)](https://pypi.org/project/library-analyzer)
[![Main](https://github.com/Safe-DS/Library-Analyzer/actions/workflows/main.yml/badge.svg)](https://github.com/Safe-DS/Library-Analyzer/actions/workflows/main.yml)
[![codecov](https://codecov.io/gh/Safe-DS/Library-Analyzer/branch/main/graph/badge.svg?token=UyCUY59HKM)](https://codecov.io/gh/Safe-DS/Library-Analyzer)
[![Documentation Status](https://readthedocs.org/projects/library-analyzer/badge/?version=latest)](https://library-analyzer.safe-ds.com)

Analysis of Python libraries and code that uses them.

## Documentation

You can find the full documentation [here](https://library-analyzer.safe-ds.com).

## Installation

Get the latest version from [PyPI](https://pypi.org/project/library-analyzer):

```shell
pip install library-analyzer
```

## Example usage

1. Analyze the API of a library:
    ```shell
    analyze-library api -p sklearn -o out
    ```
2. Analyze client code of a library:
    ```shell
    analyze-library usages -p sklearn -c "Kaggle Kernels" -o out
    ```
3. Generate annotations for the library:
    ```shell
    analyze-library annotations -a data/api/sklearn__api.json -u data/usages/sklearn__usage_counts.json -o out/annotations.json
    ```
4. Migrate annotations for a new version of the library:
    ```shell
    analyze-library migrate -a1 data/api/scikit-learn_v0.24.2_api.json -a2 data/api/sklearn__apiv2.json -a data/annotations/annotations.json -o out
    ```
