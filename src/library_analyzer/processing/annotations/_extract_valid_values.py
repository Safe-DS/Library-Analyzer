import re



def extract_valid_literals(param_description: str, param_type: str) -> set[str]:

    type_string_patterns = [_extract_from_type_and_or, _extract_from_type_curly_enum]
    description_string_patterns = [_extract_from_description_if_listings, _extract_from_description_indented_listings]
    matches = set()

    for pattern in type_string_patterns:
        matches = pattern(param_type)
        if matches:
            return set(matches)

    for pattern in description_string_patterns:
        matches = pattern(param_description)
        if matches:
            return set(matches)

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


if __name__ == '__main__':
    print(extract_valid_literals("If 'mean' than you can lunch. If None you cannot lunch.", "str"))




