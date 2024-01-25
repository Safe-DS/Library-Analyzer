# Project Guidelines

This document describes general guidelines for the Library Analyzer.

## Docstrings

The docstrings **should** use the [numpydoc](https://numpydoc.readthedocs.io/en/latest/format.html) format. The
descriptions **should not** start with "this" and **should** use imperative mood. Docstrings **should not** contain
type hints, since they are already specified in the code. Refer to the subsections below for more details on how to
document specific API elements.

!!! success "**DO**:"

    ```py
    def add_ints(a: int, b: int) -> int:
        """Add two integers."""
        return a + b
    ```

!!! failure "**DON'T**:"

    ```py
    def add_ints(a: int, b: int) -> int:
        """This function adds two integers."""
        return a + b
    ```

!!! failure "**DON'T**:"

    ```py
    def add_ints(a: int, b: int) -> int:
        """Adds two integers."""
        return a + b
    ```

### Modules

All modules should have

* A one-line description ([short summary][short-summary-section]).
* A longer description if needed ([extended summary][extended-summary-section]).

Example:

```py
"""Containers for tabular data."""
```

### Classes

All classes should have

* A one-line description ([short summary][short-summary-section]).
* A longer description if needed ([extended summary][extended-summary-section]).
* A description of the parameters of their `__init__` method ([`Parameters` section][parameters-section]). Omit types
  and default values.
* Examples that show how to use them correctly ([`Examples` section][examples-section]).

Example:

```py
"""
A row is a collection of named values.

Parameters
----------
data
    The data. If None, an empty row is created.

Examples
--------
>>> from safeds.data.tabular.containers import Row
>>> row = Row({"a": 1, "b": 2})
"""
```

### Functions

All functions should have

* A one-line description ([short summary][short-summary-section]).
* A longer description if needed ([extended summary][extended-summary-section]).
* A description of their parameters ([`Parameters` section][parameters-section]). Omit types
  and default values.
* A description of their results ([`Returns` section][returns-section]). Specify a name for the return value but omit
  its type. Note that the colon after the name is required here, otherwise it will be interpreted as a type.
* A description of any exceptions that may be raised and under which conditions that may
  happen ([`Raises` section][raises-section]).
* A description of any warnings that may be issued and under which conditions that may
  happen ([`Warns` section][warns-section]).
* Examples that show how to use them correctly ([`Examples` section][examples-section]).

Example:

```py
"""
Return the value of a specified column.

Parameters
----------
column_name
    The column name.

Returns
-------
value :
    The column value.

Raises
------
UnknownColumnNameError
    If the row does not contain the specified column.

Examples
--------
>>> from safeds.data.tabular.containers import Row
>>> row = Row({"a": 1, "b": 2})
>>> row.get_value("a")
1
"""
```

## Tests

We aim for 100% line coverage, so automated tests should be added for any new function.

### File structure

Tests belong in the [`tests`][tests-folder] folder. The file structure in the tests folder should mirror the file
structure of the [`src`][src-folder] folder.

### Naming

Names of test functions shall start with `test_should_` followed by a description of the expected behaviour,
e.g. `test_should_add_column`.

!!! success "**DO**:"

    ```py
    def test_should_raise_if_less_than_or_equal_to_0(self, number_of_trees) -> None:
        with pytest.raises(ValueError, match="The parameter 'number_of_trees' has to be greater than 0."):
            ...
    ```

!!! failure "**DON'T**:"

    ```py
    def test_value_error(self, number_of_trees) -> None:
        with pytest.raises(ValueError, match="The parameter 'number_of_trees' has to be greater than 0."):
            ...
    ```

### Parametrization

Tests should be parametrized using `@pytest.mark.parametrize`, even if there is only a single test case. This makes it
easier to add new test cases in the future. Test cases should be given descriptive IDs.

!!! success "**DO**:"

    ```py
    @pytest.mark.parametrize("number_of_trees", [0, -1], ids=["zero", "negative"])
    def test_should_raise_if_less_than_or_equal_to_0(self, number_of_trees) -> None:
        with pytest.raises(ValueError, match="The parameter 'number_of_trees' has to be greater than 0."):
            RandomForest(number_of_trees=number_of_trees)
    ```

!!! failure "**DON'T**:"

    ```py
    def test_should_raise_if_less_than_0(self, number_of_trees) -> None:
        with pytest.raises(ValueError, match="The parameter 'number_of_trees' has to be greater than 0."):
            RandomForest(number_of_trees=-1)

    def test_should_raise_if_equal_to_0(self, number_of_trees) -> None:
        with pytest.raises(ValueError, match="The parameter 'number_of_trees' has to be greater than 0."):
            RandomForest(number_of_trees=0)
    ```

## Code style

### Consistency

If there is more than one way to solve a particular task, check how it has been solved at other places in the codebase
and stick to that solution.

### Sort exported classes in `__init__.py`

Classes defined in a module that other classes shall be able to import must be defined in a list named `__all__` in the
module's `__init__.py` file. This list should be sorted alphabetically, to reduce the likelihood of merge conflicts when
adding new classes to it.

!!! success "**DO**:"

    ```py
    __all__ = [
        "Column",
        "Row",
        "Table",
        "TaggedTable",
    ]
    ```

!!! failure "**DON'T**:"

    ```py
    __all__ = [
        "Table",
        "TaggedTable",
        "Column",
        "Row",
    ]
    ```

[src-folder]: https://github.com/Safe-DS/Library/tree/main/src
[tests-folder]: https://github.com/Safe-DS/Library/tree/main/tests
[short-summary-section]: https://numpydoc.readthedocs.io/en/latest/format.html#short-summary
[extended-summary-section]: https://numpydoc.readthedocs.io/en/latest/format.html#extended-summary
[parameters-section]: https://numpydoc.readthedocs.io/en/latest/format.html#parameters
[returns-section]: https://numpydoc.readthedocs.io/en/latest/format.html#returns
[raises-section]: https://numpydoc.readthedocs.io/en/latest/format.html#raises
[warns-section]: https://numpydoc.readthedocs.io/en/latest/format.html#warns
[examples-section]: https://numpydoc.readthedocs.io/en/latest/format.html#examples
