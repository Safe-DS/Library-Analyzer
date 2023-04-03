import re
from dataclasses import dataclass, field


@dataclass
class Configuration:
    _function_list: list = field(default_factory=list)

    def get_function_list(self) -> list:
        return self._function_list


@dataclass
class DescriptionStringConfiguration(Configuration):
    if_listings: bool = True
    indented_listings: bool = True
    when_set_to: bool = True

    def __post_init__(self) -> None:
        if self.if_listings:
            self._function_list.append(_extract_from_description_if_listings)
        if self.indented_listings:
            self._function_list.append(_extract_from_description_indented_listings)
        if self.when_set_to:
            self._function_list.append(_extract_from_descritpion_when_set_to)


@dataclass
class TypeStringConfiguration(Configuration):
    curly_enum: bool = True
    and_or_enum: bool = True

    def __post_init__(self) -> None:
        if self.curly_enum:
            self._function_list.append(_extract_from_type_curly_enum)
        if self.and_or_enum:
            self._function_list.append(_extract_from_type_listing)


def extract_valid_literals(param_description: str, param_type: str) -> set[str]:
    """
    Function that extracts all valid literals from the type and description string.

    Parameters
    ----------
    param_description: str
        Description string of the parameter to be examined.

    param_type: str
        Type string of the parameter to be examined.


    Returns
    -------
    set[str]
        A set of valid, extracted values of the parameter to be examined.
    """

    description_config: DescriptionStringConfiguration = DescriptionStringConfiguration()
    type_config: TypeStringConfiguration = TypeStringConfiguration()
    none_and_bool = {"False", "None", "True"}

    def _execute_pattern(string: str, config: Configuration) -> set[str]:
        # Function to execute all pattern functions from config
        result = set()
        for pattern_function in config.get_function_list():
            result.update(pattern_function(string))
        return result

    matches = _execute_pattern(param_type, type_config)

    description_matches = _execute_pattern(param_description, description_config)

    # Check if there are matching values in the description that are not True, False or None
    # when 'str' occurs in the type string. If this is not the case, unlistable_str is returned as a 'valid' value.
    if description_matches:
        matches.update(description_matches)
        if "str" in matches:
            if not description_matches.difference(none_and_bool):
                matches.add("unlistable_str")
            matches.remove("str")

    return matches


def _extract_from_type_curly_enum(type_string: str) -> set[str]:
    """
    Extraction of valid values of the parameter type string to be examined, enclosed in curly brackets.

    Parameters
    ----------
    type_string: str
        Type string of the parameter to be examined.

    Returns
    -------
    set[str]
        A set of valid values from the parameter description to be examined.
    """

    matches = re.findall(r"\{(.*?)}", type_string)
    extracted = []

    for match in matches:
        splitted = re.split(r", ", match)
        extracted.extend(splitted)

    return set(extracted)


def _extract_from_type_listing(type_string: str) -> set[str]:
    """
    Extraction of valid values from the listing of the parameter type string to be examined.

    Parameters
    ----------
    type_string: str
        Type string of the parameter to be examined.

    Returns
    -------
    set[str]
        A set of valid values from the parameter description to be examined.
    """

    # Multiple values seperated by ',', 'and' or 'or' with single# quotes
    single_and_or_pattern = r"('[^']*'|bool|str)\s*(?:and|or|,)?"
    # Multiple values seperated by ',', 'and' or'or' with double quotes
    double_and_or_pattern = r"(\"[^\"]*\"|bool|str)\s*(?:and|or|,)?"

    matches = re.findall(single_and_or_pattern, type_string)

    if not matches:
        matches = re.findall(double_and_or_pattern, type_string)

    extracted = set(matches)

    if "bool" in extracted:
        extracted.remove("bool")
        extracted.add("False")
        extracted.add("True")

    return extracted


def _extract_from_description_if_listings(description: str) -> set[str]:
    """
    Detection of substrings starting with 'if' and satisfying one of the following cases:
    A value between single or double quotes, False, True, or None.

    Parameters
    ----------
    description: str
        Description string of the parameter to be examined.

    Returns
    -------
    set[str]
        A set of valid values from the parameter description to be examined.
    """

    pattern = r"[-\+\*]?\s*If\s*('[^']*'|\"[^\"]*\"|True|False|None)"
    matches = re.findall(pattern, description)
    return set(matches)


def _extract_from_description_indented_listings(description: str) -> set[str]:
    """
    Detect substrings that appear in an indented list and match one of the following cases:
    A value between single or double quotes, False, True, or None.

    Parameters
    ----------
    description: str
        Description string of the parameter to be examined.


    Returns
    -------
    set[str]
        A set of valid values from the parameter description to be examined.
    """

    pattern = r"[-\+\*]?\s+(\"[^\"]*\"|'[^']*'|None|True|False):"
    matches = re.findall(pattern, description)
    return set(matches)


def _extract_from_descritpion_when_set_to(description: str) -> set[str]:
    """
    Detection of substrings starting with 'when set to' and satisfying one of the following cases:
    A value between single or double quotes, False, True, or None.

    Parameters
    ----------
    Description string of the parameter to be examined.

    Returns
    -------
    set[str]
        A set of valid values from the parameter description to be examined.
    """

    pattern = r"When set to (\"[^\"]*\"|'[^']*'|None|True|False)"
    matches = re.findall(pattern, description, re.IGNORECASE)
    return set(matches)
