# Library Analyzer

Analysis of Python libraries and code that uses them.

## Installation

1. Install Python 3.10.
2. Install [poetry](https://python-poetry.org/docs/master/#installation).
3. **Only the first time**, install dependencies:
    ```shell
    poetry install
    ```
4. Create a shell with poetry:
    ```shell
    poetry shell
    ```

## Example usage

1. Analyze an API:
    ```shell
    analyze-library api -p sklearn -o out
    ```
2. Analyze client code of this API:
    ```shell
    analyze-library usages -p sklearn -c "Kaggle Kernels" -o out
    ```
3. Generate annotations for the API:
    ```shell
    analyze-library annotations -a data/api/sklearn__api.json -u data/usages/sklearn__usage_counts.json -o out/annotations.json
    ```
4. Migrate annotations for a new version of the API:
    ```shell
    analyze-library migrate -a1 data/api/scikit-learn_v0.24.2_api.json -a2 data/api/sklearn__apiv2.json -a data/annotations/annotations.json -o out
    ```
