import dataclasses
import re

# @dataclasses.dataclass
# class DescriptionStringConfiguration:
#     _extract_from_description_if_listings: bool = True
#     _extract_from_description_indented_listings: bool = True
#
#     def _build_function_list(self):
#         if _extract_from_description_if_listings:
#             self._function_list.append(_extract_from_description_if_listings)


def extract_valid_literals(param_description: str, param_type: str) -> set[str]:
    type_string_configuration = {
        _extract_from_type_curly_enum: True,
        _extract_from_type_and_or: True
    }

    description_string_configuration = {
        _extract_from_description_if_listings: True,
        _extract_from_description_indented_listings: True
    }

    def _execute_pattern(string: str, config: dict) -> set[str]:
        result = set()
        for pattern_function in config.keys():
            if config[pattern_function]:
                result = pattern_function(string)
            if result:
                break
        return result

    matches = _execute_pattern(param_type, type_string_configuration)

    if matches:
        return matches

    matches = _execute_pattern(param_description, description_string_configuration)

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
    pattern = r"[-+*]?\s*If\s*('\w*'|\"\w*\"|True|False|None)"
    matches = re.findall(pattern, description)
    return set(matches)


def _extract_from_description_indented_listings(description: str) -> set[str]:
    pattern = r"\s+(\"\w*\"|'\w*'|None|True|False):"
    matches = re.findall(pattern, description)
    return set(matches)
