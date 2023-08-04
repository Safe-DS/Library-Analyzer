import pytest
from library_analyzer.processing.api import extract_called_after_functions, CalledAfterValues

@pytest.mark.parametrize(
    ("function_qname", "description", "expected_values"),
    [
        # https://github.com/matplotlib/matplotlib/blob/d073a3636662ffb165b830f3b88cc3f1f4f40823/lib/matplotlib/axes/_axes.py#L3443-L3445
        (
            "errorbar",
            "To use limits with inverted axes, `~.Axes.set_xlim` or `~.Axes.set_ylim` must be called before "
            ":meth:`errorbar`.",
            CalledAfterValues("errorbar", ["~.Axes.set_ylim", "~.Axes.set_xlim"], "before")
        ),

        # Tescase was derived from the previous one
        (
            "errorbar",
            "To use limits with inverted axes, :meth:`errorbar` must be called after "
            "`~.Axes.set_xlim` or `~.Axes.set_ylim`",
            CalledAfterValues("errorbar", ["~.Axes.set_xlim", "~.Axes.set_ylim"], "after")
        ),

        # Created Testcase without example
        (
            "errorbar",
            "Before errorbar is called, '~.Axes.set_xlim' must be called.",
            CalledAfterValues("errorbar", ["~.Axes.set_xlim"], "after")
        )
    ]
)
def test_extract_called_after_functions(
    function_qname: str, description: str, expected_values: CalledAfterValues
) -> None:
    assert extract_called_after_functions(function_qname, description) == expected_values

