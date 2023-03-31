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
            self._function_list.append(_extract_from_type_and_or)


def extract_valid_literals(param_description: str, param_type: str) -> set[str]:
    description_config: DescriptionStringConfiguration = DescriptionStringConfiguration()
    type_config: TypeStringConfiguration = TypeStringConfiguration()

    def _execute_pattern(string: str, config: Configuration) -> set[str]:
        result = set()
        for pattern_function in config.get_function_list():
            result.update(pattern_function(string))
        return result

    matches = _execute_pattern(param_type, type_config)

    if matches:
        return matches

    matches = _execute_pattern(param_description, description_config)

    return matches


def _extract_from_type_curly_enum(type_string: str) -> set[str]:
    matches = re.findall(r"\{(.*?)}", type_string)
    extracted = []

    for match in matches:
        splitted = re.split(r", ", match)
        extracted.extend(splitted)

    return set(extracted)


def _extract_from_type_and_or(type_string: str) -> set[str]:
    # Two values seperated by 'and' or 'or' with single# quotes
    single_and_or_pattern = r"('[^']*')\s*(?:and|or)\s*('[^']*')"
    # Two values seperated by 'and' or 'or' with double quotes
    double_and_or_pattern = r"(\"[^\"]*\")\s*(?:and|or)\s*(\"[^\"]*\")"

    extracted = set()

    matches = re.findall(single_and_or_pattern, type_string)

    if not matches:
        matches = re.findall(double_and_or_pattern, type_string)

    for x, y in matches:
        extracted.add(x)
        extracted.add(y)

    return extracted


def _extract_from_description_if_listings(description: str) -> set[str]:
    # Detection of substrings starting with 'if' and satisfying one of the following cases:
    # A value between single or double quotes, False, True, or None.
    pattern = r"[-\+\*]?\s*If\s*('[^']*'|\"[^\"]*\"|True|False|None)"
    matches = re.findall(pattern, description)
    return set(matches)


def _extract_from_description_indented_listings(description: str) -> set[str]:
    # Detect substrings that appear in an indented list and match one of the following cases:
    # A value between single or double quotes, False, True, or None.
    pattern = r"[-\+\*]?\s+(\"[^\"]*\"|'[^']*'|None|True|False):"
    matches = re.findall(pattern, description)
    return set(matches)


def _extract_from_descritpion_when_set_to(description: str) -> set[str]:
    # Detection of substrings starting with 'when set to' and satisfying one of the following cases:
    # A value between single or double quotes, False, True, or None.
    pattern = r"When set to (\"[^\"]*\"|'[^']*'|None|True|False)"
    matches = re.findall(pattern, description, re.IGNORECASE)
    return set(matches)
