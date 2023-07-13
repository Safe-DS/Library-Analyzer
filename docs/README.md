# Library Analyzer

[![PyPI](https://img.shields.io/pypi/v/library-analyzer)](https://pypi.org/project/library-analyzer)
[![Main](https://github.com/Safe-DS/Library-Analyzer/actions/workflows/main.yml/badge.svg)](https://github.com/Safe-DS/Library-Analyzer/actions/workflows/main.yml)
[![codecov](https://codecov.io/gh/Safe-DS/Library-Analyzer/branch/main/graph/badge.svg?token=UyCUY59HKM)](https://codecov.io/gh/Safe-DS/Library-Analyzer)
[![Documentation Status](https://readthedocs.org/projects/library-analyzer/badge/?version=stable)](https://library-analyzer.safeds.com)

Analysis of Python libraries and code that uses them.

## Installation

Get the latest version from [PyPI](https://pypi.org/project/library-analyzer):

```shell
pip install library-analyzer
```

## Documentation

You can find the full documentation [here](https://library-analyzer.safeds.com).

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

## Contributing

We welcome contributions from everyone. As a starting point, check the following resources:

* [Setting up a development environment](https://library-analyzer.safeds.com/en/latest/development/environment/)
* [Contributing page](https://github.com/Safe-DS/Library-Analyzer/contribute)

If you need further help, please [use our discussion forum][forum].

[forum]: https://github.com/orgs/Safe-DS/discussions
