import re
from dataclasses import dataclass, field
from typing import Any

import spacy
from spacy import Language
from spacy.matcher import Matcher
from spacy.tokens import Doc, Span


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
            self._function_list.append(_extract_from_description_if_listing)
        if self.indented_listings:
            self._function_list.append(_extract_from_description_indented_listing)
        if self.when_set_to:
            self._function_list.append(_extract_from_description_when_set_to)


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
    Extract all valid literals from the type and description string.

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
    Extract all valid values of the parameter type string to be examined that were enclosed in curly braces.

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
    Extract all valid values from the listing of the parameter type string to be examined.

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


def _extract_from_description_if_listing(description: str) -> set[str]:
    """Extract the 'if listing' pattern.

    Detect all substrings starting with 'if' and satisfying one of the following cases:
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


def _extract_from_description_indented_listing(description: str) -> set[str]:
    """Extract the 'indented listing' pattern.

    Detect all substrings that appear in an indented list and match one of the following cases:
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


def _extract_from_description_when_set_to(description: str) -> set[str]:
    """Extract the 'when set to' pattern.

    Detect all substrings starting with 'when set to' and satisfying one of the following cases:
    A value between single or double quotes, False, True, or None.

    Parameters
    ----------
    Description string of the parameter to be examined.

    Returns
    -------
    set[str]
        A set of valid literals from the parameter description to be examined.
    """
    pattern = r"When set to (\"[^\"]*\"|'[^']*'|None|True|False)"
    matches = re.findall(pattern, description, re.IGNORECASE)
    return set(matches)







_enum_valid_values_are = [
    {"LOWER": "valid"},
    {"LOWER": "values"},
    {"LOWER": "are"}
]

_enum_when_set_to = [
    {"LOWER": "when"},
    {"LOWER": "set"},
    {"LOWER": "to"}
]

_enum_indented_if_listing = [
    {"LOWER": "if"},
    {"ORTH": {"IN": ["'", '"', "True", "False", "None"]}},
    {}
]

_enum_type_curly = [
    {"ORTH": "{"},
    {"IS_ASCII": True, "OP": "+"},
    {"ORTH": "}"}
]

_enum_str = [
    {"LOWER": "str"}
]

_enum_single_val_bool_none = [
    {"ORTH": {"IN": ["True", "False", "None"]}},
    {"ORTH": ":"}
]

_enum_single_val_quoted = [
    {"ORTH": {"IN": ["'", '"']}},
    {"OP": "+"},
    {"ORTH": {"IN": ["'", '"']}},
    {"ORTH": ":"}
]


@dataclass
class MatcherConfiguration:
    _nlp: Language = None
    _matcher: Matcher = None

    # Rules to be checked
    when_set_to: bool = True
    valid_values_are: bool = True
    type_curly: bool = True
    indented_if_listings: bool = True
    single_vals: bool = True

    def __post_init__(self) -> None:
        self._nlp = spacy.load("en_core_web_sm")
        self._matcher = Matcher(self._nlp.vocab)

        self._matcher.add("ENUM_STR", [_enum_str])

        if self.when_set_to:
            self._matcher.add("ENUM_WHEN_SET_TO", [_enum_when_set_to], on_match=_extract_single_value)
        if self.valid_values_are:
            self._matcher.add("ENUM_VALID_VALUES_ARE", [_enum_valid_values_are], on_match=_extract_list)
        if self.type_curly:
            self._matcher.add("ENUM_TYPE_CURLY", [_enum_type_curly], on_match=_extract_list)
        if self.indented_if_listings:
            self._matcher.add("ENUM_INDENTED_IF_LISTING", [_enum_indented_if_listing], on_match=_extract_indented_value)
        if self.single_vals:
            self._matcher.add("ENUM_SINGLE_VALS", [_enum_single_val_quoted, _enum_single_val_bool_none],
                              on_match=_extract_indented_single_value)

    def get_matcher(self) -> Matcher:
        return self._matcher

    def get_nlp(self) -> Language:
        return self._nlp


_extracted = []


def _extract_list(
    nlp_matcher: Matcher,  # noqa : ARG001
    doc: Doc,
    i: int,  # noqa : ARG001
    nlp_matches: list[tuple[Any, ...]]  # noqa : ARG001
) -> Any | None:
    found_list = False
    found_minus = False
    ex = []

    for token in doc:
        if token.text in ["[", "{"]:
            found_list = True
        elif token.text in ["]", "}"]:
            break

        if found_list and token.text not in ["'", '"', ",", "[", "{", "}"]:
            if token.text in ["True", "False"]:
                ex.append("True")
                ex.append("False")
            else:
                if token.text in ["-", "_", " "]:
                    found_minus = True
                    ex[len(ex) - 1] += token.text
                    continue
                elif found_minus:
                    ex[len(ex) - 1] += token.text
                    found_minus = False
                    continue

                ex.append(token.text)

    ex = ['"' + x + '"' for x in ex]
    _extracted.extend(ex)

    return None


def _extract_single_value(
    nlp_matcher: Matcher,  # noqa : ARG001
    doc: Doc, i: int,
    nlp_matches: list[tuple[Any, ...]]
) -> Any | None:
    _, _, end = nlp_matches[i]
    value = '"' + doc[end + 1].text + '"'
    _extracted.append(value)

    return None

def _extract_indented_single_value(
    nlp_matcher: Matcher,  # noqa : ARG001
    doc: Doc,
    i: int,
    nlp_matches: list[tuple[Any, ...]]
) -> Any | None:

    _, start, end = nlp_matches[i]
    value = doc[start:end-1]
    value = value.text

    if value[0] in ["'", '"']:
        value = value.replace("'", '"')

    _extracted.append(value)

    return None



def _extract_indented_value(nlp_matcher: Matcher, doc: Doc, i: int, nlp_matches: list[tuple[Any, ...]]) -> Any | None:
    _, start, end = nlp_matches[i]
    # text_ = doc[start:end].text.strip()

    span_ = doc[start:end]
    found_quotes = False

    for token in span_:
        if token.text == "None":
            _extracted.append("None")
        elif token.text in ["True", "False"]:
            _extracted.append("True")
            _extracted.append("False")
        elif token.text in ["'", '"']:
            found_quotes = not found_quotes
        elif found_quotes:
            _extracted.append('"' + token.text + '"')

    return None


def _nlp_matches_to_readable_matches(
    nlp_matches: list[tuple[int, int, int]], nlp_: Language, doc_: Doc
) -> list[tuple[str, Span]]:
    return [(nlp_.vocab.strings[match_id], doc_[start:end]) for match_id, start, end in nlp_matches]




def extract(description: str, type_string: str) -> set[str]:
    _extracted.clear()

    nlp = MATCHER_CONFIG.get_nlp()
    matcher = MATCHER_CONFIG.get_matcher()

    none_and_bool = {"False", "None", "True"}

    desc_doc = nlp.make_doc(" ".join(description.split()))
    type_doc = nlp.make_doc(type_string)

    desc_matches = matcher(desc_doc)
    desc_matches = _nlp_matches_to_readable_matches(desc_matches, nlp, desc_doc)

    type_matches = matcher(type_doc)
    type_matches = _nlp_matches_to_readable_matches(type_matches, nlp, type_doc)

    extracted_set = set(_extracted)

    if any(x[0] == "ENUM_STR" for x in type_matches) and not extracted_set.difference(none_and_bool):
        extracted_set.add("unlistable_str")

    return extracted_set

MATCHER_CONFIG = MatcherConfiguration()



