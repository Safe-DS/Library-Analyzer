from typing import Any

from scipy.stats import binom

from library_analyzer.processing.annotations.model import (
    AnnotationStore,
    ConstantAnnotation,
    EnumReviewResult,
    OmittedAnnotation,
    OptionalAnnotation,
    RequiredAnnotation,
    ValueAnnotation,
)
from library_analyzer.processing.api.model import API, Parameter, ParameterAssignment
from library_analyzer.processing.usages.model import UsageCountStore
from library_analyzer.utils import pluralize

from ._constants import autogen_author


def _generate_value_annotations(api: API, usages: UsageCountStore, annotations: AnnotationStore) -> None:
    for parameter in api.parameters().values():
        # Don't create annotations for variadic parameters
        if parameter.assigned_by in (
            ParameterAssignment.POSITIONAL_VARARG,
            ParameterAssignment.NAMED_VARARG,
        ):
            continue

        parameter_values = usages.most_common_parameter_values(parameter.id)

        if len(parameter_values) == 1:
            _generate_constant_annotation(parameter, parameter_values[0], annotations)
        elif len(parameter_values) > 1:
            _generate_required_or_optional_annotation(parameter, usages, annotations)


def _generate_constant_annotation(
    parameter: Parameter,
    sole_stringified_value: str,
    annotations: AnnotationStore,
) -> None:
    """
    Collect all parameters that are only ever assigned a single value.

    Parameters
    ----------
    parameter: Parameter
        Parameter to be annotated
    sole_stringified_value: str
        The sole value that is assigned to the parameter
    annotations: AnnotationStore
        AnnotationStore object.
    """
    # Always set to original default value
    if sole_stringified_value == parameter.default_value:
        annotations.valueAnnotations.append(
            OmittedAnnotation(
                target=parameter.id,
                authors=[autogen_author],
                reviewers=[],
                comment="I omitted this parameter because it is always set to the original default value "
                f"({parameter.default_value}).",
                reviewResult=EnumReviewResult.NONE,
            ),
        )
        return

    default_value_type, default_value = _get_type_and_value_for_stringified_value(sole_stringified_value)
    if default_value_type is not None:
        annotations.valueAnnotations.append(
            ConstantAnnotation(
                target=parameter.id,
                authors=[autogen_author],
                reviewers=[],
                comment="I replaced this parameter with a constant because it is always set to the same literal value "
                f"({sole_stringified_value}).",
                reviewResult=EnumReviewResult.NONE,
                defaultValueType=default_value_type,
                defaultValue=default_value,
            ),
        )
    else:
        annotations.valueAnnotations.append(
            RequiredAnnotation(
                target=parameter.id,
                authors=[autogen_author],
                reviewers=[],
                comment="I made this parameter required because, even though it is always set to the same value "
                f"({sole_stringified_value}), that value is not a literal.",
                reviewResult=EnumReviewResult.NONE,
            ),
        )


def _generate_required_or_optional_annotation(
    parameter: Parameter,
    usages: UsageCountStore,
    annotations: AnnotationStore,
) -> None:
    most_common_values = usages.most_common_parameter_values(parameter.id)
    if len(most_common_values) < 2:
        return

    # If the most common value is not a stringified literal, make parameter required
    if not _is_stringified_literal(most_common_values[0]):
        annotations.valueAnnotations.append(
            RequiredAnnotation(
                target=parameter.id,
                authors=[autogen_author],
                reviewers=[],
                comment=f"I made this parameter required because the most common value ({most_common_values[0]}) is "
                "not a literal.",
                reviewResult=EnumReviewResult.NONE,
            ),
        )
        return

    # Compute metrics
    most_common_value_count = usages.n_value_usages(parameter.id, most_common_values[0])
    second_most_common_value_count = usages.n_value_usages(parameter.id, most_common_values[1])

    # Add appropriate annotation
    should_be_required, comment = _should_be_required(
        most_common_values[0],
        most_common_value_count,
        most_common_values[1],
        second_most_common_value_count,
    )
    if should_be_required:
        annotations.valueAnnotations.append(
            RequiredAnnotation(
                target=parameter.id,
                authors=[autogen_author],
                reviewers=[],
                comment=comment,
                reviewResult=EnumReviewResult.NONE,
            ),
        )
    else:
        (
            default_value_type,
            default_value,
        ) = _get_type_and_value_for_stringified_value(most_common_values[0])
        if default_value_type is not None:  # Just for mypy, always true
            annotations.valueAnnotations.append(
                OptionalAnnotation(
                    target=parameter.id,
                    authors=[autogen_author],
                    reviewers=[],
                    comment=comment,
                    reviewResult=EnumReviewResult.NONE,
                    defaultValueType=default_value_type,
                    defaultValue=default_value,
                ),
            )


def _should_be_required(
    most_common_value: str,
    most_common_value_count: int,
    second_most_common_value: str,
    second_most_common_value_count: int,
) -> tuple[bool, str]:
    """
    Determine whether the parameter should be required or optional.

    Parameters
    ----------
    most_common_value: int
        The most common value
    most_common_value_count: int
        How often the most common value is used
    second_most_common_value: int
        The second most common value
    second_most_common_value_count: int
        How often the second most common value is used

    Returns
    -------
    should_be_required: bool
        True means the parameter should be required, False means it should be optional.
    explanation: str
        An explanation why the parameter should be required or optional.
    """
    # Shortcut to speed up the check
    if most_common_value_count == second_most_common_value_count:
        return (
            True,
            f"I made this parameter required because there is no single most common value ({most_common_value} and "
            f"{second_most_common_value} are both used {pluralize(most_common_value_count, 'time')}).",
        )

    # Precaution to ensure proper order of most_common_value_count and second_most_common_value_count
    if second_most_common_value_count > most_common_value_count:
        most_common_value_count, second_most_common_value_count = (
            second_most_common_value_count,
            most_common_value_count,
        )

    total = most_common_value_count + second_most_common_value_count

    # Our null hypothesis is that the user chooses between the most common and second most common value by a fair coin
    # toss. Unless this hypothesis is rejected, we make the parameter required. We reject the hypothesis if the p-value
    # is less than or equal to 5%. The p-value is the probability that we observe results that are at least as extreme
    # as the values we observed, assuming the null hypothesis is true.
    p_value = 2 * sum(binom.pmf(i, total, 0.5) for i in range(most_common_value_count, total + 1))
    significance_level = 0.05

    if p_value <= significance_level:
        return (
            False,
            "I made this parameter optional because there is a statistically significant most common value (p-value "
            f"{p_value:.2%} <= significance level {significance_level:.0%}).",
        )
    return (
        True,
        "I made this parameter required because there is no statistically significant most common value (p-value "
        f"({p_value:.2%}) > significance level ({significance_level:.0%}).",
    )


def _is_stringified_literal(stringified_value: str) -> bool:
    default_type, _ = _get_type_and_value_for_stringified_value(stringified_value)
    return default_type is not None


def _get_type_and_value_for_stringified_value(
    stringified_value: str,
) -> tuple[ValueAnnotation.DefaultValueType | None, Any]:
    if stringified_value == "None":
        return ValueAnnotation.DefaultValueType.NONE, None
    if stringified_value in ("True", "False"):
        return ValueAnnotation.DefaultValueType.BOOLEAN, stringified_value == "True"
    if _is_float(stringified_value):
        return ValueAnnotation.DefaultValueType.NUMBER, float(stringified_value)
    if stringified_value[0] == "'" and stringified_value[-1] == "'":
        return ValueAnnotation.DefaultValueType.STRING, stringified_value[1:-1]
    return None, None


def _is_float(stringified_value: str) -> bool:
    try:
        float(stringified_value)
    except ValueError:
        return False
    else:
        return True
