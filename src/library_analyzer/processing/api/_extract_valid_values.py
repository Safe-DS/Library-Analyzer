import re
from dataclasses import dataclass
from typing import Any

from spacy import Language
from spacy.matcher import Matcher
from spacy.tokens import Doc, Span

from library_analyzer.utils import load_language

_quotes = {"ORTH": {"IN": ["'", '"', "`"]}}
_quotes_without_backticks = {"ORTH": {"IN": ["'", '"']}}
_quotes_at_least_one = {"ORTH": {"IN": ["'", '"', "`"]}, "OP": "+"}
_quotes_optional = {"ORTH": {"IN": ["'", '"', "`"]}, "OP": "?"}

_enum_valid_values_are = [{"LOWER": {"IN": ["valid", "possible", "accepted"]}}, {"LOWER": "values"}, {"LOWER": "are"}]

_enum_when_set_to = [{"LOWER": "when"}, {"LOWER": "set"}, {"LOWER": "to"}]

_enum_if_listing = [
    {"ORTH": "If"},
    _quotes_at_least_one,
    {"OP": "{1,1}"},
    _quotes_at_least_one,
    {"ORTH": {"IN": [",", ":"]}},
]

_enum_if_special_vals = [
    {"ORTH": "If"},
    _quotes_optional,
    {"LOWER": {"IN": ["false", "true", "none"]}},
    _quotes_optional,
]

_enum_hyphened_single_val = [
    {"ORTH": "-"},
    _quotes_at_least_one,
    {},
    _quotes_at_least_one,
    {"ORTH": {"IN": [",", ":"]}, "OP": "?"},
]

_enum_hyphened_special_vals = [
    {"ORTH": "-"},
    _quotes_optional,
    {"LOWER": {"IN": ["false", "true", "none"]}},
    _quotes_optional,
]

_enum_type_curly = [{"ORTH": "{"}, {"OP": "+"}, {"ORTH": "}"}]

_enum_str = [{"LOWER": "of", "OP": "?"}, {"LOWER": "str"}]
_enum_bool = [{"LOWER": {"IN": ["bool", "false", "true"]}}]

_enum_single_val_bool_none = [{"ORTH": {"IN": ["True", "False", "None"]}}, {"ORTH": ":", "OP": "?"}]

_enum_single_val_quoted = [
    _quotes_without_backticks,
    {"ORTH": {"NOT_IN": ["'", "`", '"']}, "OP": "+"},
    _quotes_without_backticks,
]

_enum_string_inputs_supported = [
    {"LOWER": "string"},
    {"LOWER": "inputs"},
    {"ORTH": ","},
    {"OP": "+"},
    {"LOWER": "are"},
    {"LOWER": "supported"},
]

_enum_single_val_respective = [
    {"LOWER": {"IN": ["resp.", "respective"]}},
]


@dataclass
class MatcherConfiguration:
    _nlp: Language = None
    _descr_matcher: Matcher = None
    _type_matcher: Matcher = None

    # Rules to be checked
    single_val_type_string: bool = True
    when_set_to: bool = True
    valid_values_are: bool = True
    type_curly: bool = True
    if_listings: bool = True
    single_vals: bool = True
    string_inputs: bool = True
    hyphened_single: bool = True

    def __post_init__(self) -> None:
        self._nlp = load_language("en_core_web_sm")
        self._descr_matcher = Matcher(self._nlp.vocab)
        self._type_matcher = Matcher(self._nlp.vocab)

        self._type_matcher.add("ENUM_STR", [_enum_str], greedy="LONGEST")
        self._type_matcher.add("ENUM_BOOL", [_enum_bool])

        if self.when_set_to:
            self._descr_matcher.add("ENUM_SINGLE_VAL_WHEN", [_enum_when_set_to], on_match=_extract_single_value)
        if self.if_listings:
            self._descr_matcher.add(
                "ENUM_SINGLE_VAL_IF",
                [_enum_if_listing, _enum_if_special_vals],
                on_match=_extract_single_value,
                greedy="FIRST",
            )
        if self.valid_values_are:
            self._descr_matcher.add("ENUM_VALID_VALUES_ARE", [_enum_valid_values_are], on_match=_extract_list)
        if self.type_curly:
            self._type_matcher.add("ENUM_TYPE_CURLY", [_enum_type_curly], on_match=_extract_list)
        if self.single_vals:
            self._type_matcher.add(
                "ENUM_TYPE_SINGLE_VALS",
                [_enum_single_val_quoted, _enum_single_val_bool_none],
                on_match=_extract_indented_single_value,
                greedy="FIRST",
            )
        if self.string_inputs:
            self._descr_matcher.add("ENUM_STRING_INPUTS", [_enum_string_inputs_supported], on_match=_extract_list)
        if self.hyphened_single:
            self._descr_matcher.add(
                "ENUM_HYPHENED_SINGLE",
                [_enum_hyphened_special_vals, _enum_hyphened_single_val],
                on_match=_extract_single_value,
                greedy="FIRST",
            )

    def get_descr_matcher(self) -> Matcher:
        return self._descr_matcher

    def get_type_matcher(self) -> Matcher:
        return self._type_matcher

    def get_nlp(self) -> Language:
        return self._nlp


_extracted: list[str] = []


def _merge_with_last_value_in_list(value_list: list[str], merge_value: str) -> None:
    """Merge the last value of a list with the passed merge_value.

    Parameters
    ----------
    value_list
        list of string values
    merge_value
        value to be merged

    """
    if merge_value in ["-", "_"] or value_list[-1][-1] in ["-", "_"]:
        value_list[-1] += merge_value
    else:
        value_list[-1] += " " + merge_value


def _extract_list(
    nlp_matcher: Matcher,  # noqa: ARG001
    doc: Doc,
    i: int,
    nlp_matches: list[tuple[Any, ...]],
) -> Any | None:
    """on-match function for the spaCy Matcher.

    Extract the first collection of valid string values that occurs after the matched string.

    Parameters
    ----------
    nlp_matcher
        Parameter is ignored.
    doc
        Doc object that is checked for the active rules.
    i
        Parameter is ignored.
    nlp_matches
        List of matches found by the matcher

    """
    found_list = False
    quotes = ["'", "`", '"']
    seperators_opener = [",", "[", "{", "or", "and"]
    ex = []
    quote_start = False
    last_token = False
    value = ""

    match_ = nlp_matches[i]
    end = match_[2]
    start = match_[1]

    label = MATCHER_CONFIG.get_nlp().vocab.strings[match_[0]]

    if label == "ENUM_STRING_INPUTS":
        end = start + 2
    elif label == "ENUM_TYPE_CURLY":
        end = start

    for token in doc[end:]:
        if token.text in ["[", "{"]:
            found_list = True
            continue
        elif token.text in ["]", "}"]:
            break

        if found_list and token.text not in seperators_opener and token.text not in quotes:
            first_left_nbor = token.nbor(-1).text
            if token.i > 1:
                second_left_nbor = token.nbor(-2).text
            else:
                second_left_nbor = "'"

            if token.text in ["True", "False", "bool"]:
                ex.append("True")
                ex.append("False")
            elif token.text == "None":
                ex.append("None")

            elif (
                (first_left_nbor in quotes and second_left_nbor not in seperators_opener)
                or (first_left_nbor not in seperators_opener and first_left_nbor not in quotes)
                and ex
            ):
                _merge_with_last_value_in_list(ex, token.text)

            elif token.nbor(-1).text in quotes or token.nbor(1).text in quotes:
                ex.append(token.text)

        elif not found_list:
            if token.text in ["or", "and"]:
                last_token = True

            if token.text in quotes:
                if quote_start:
                    ex.append(value)
                    value = ""

                if last_token and quote_start:
                    break

                quote_start = not quote_start
                continue

            if quote_start:
                value += token.text

            if not quote_start and token.text in ["True", "False", "None"]:
                ex.append(token.text)

                if last_token:
                    break

    ex = ['"' + x + '"' if x not in ["True", "False", "None"] else x for x in ex]
    _extracted.extend(ex)

    return None


def _extract_single_value(
    nlp_matcher: Matcher,  # noqa: ARG001
    doc: Doc,
    i: int,
    nlp_matches: list[tuple[Any, ...]],
) -> Any | None:
    """on-match function for the spaCy Matcher.

    Extract the first value that occurs after the matched string.

    Parameters
    ----------
    nlp_matcher
        Parameter is ignored.
    doc
        Doc object that is checked for the active rules.
    i
        Index of the match that was recognized by the rule.
    nlp_matches
        List of matches found by the matcher.

    """
    text = ""
    match_id, start, end = nlp_matches[i]

    match_label = MATCHER_CONFIG.get_nlp().vocab.strings[match_id]
    if match_label in ["ENUM_SINGLE_VAL_IF", "ENUM_HYPHENED_SINGLE"]:
        next_token_idx = start + 1
        next_token = doc[next_token_idx]
        quotes = ["'", '"', "`"]

        if next_token.text in quotes and next_token.nbor(1).text in quotes:
            end = next_token_idx + 1
        else:
            end = next_token_idx

    else:
        next_token = doc[end]

    if next_token.text in ["True", "False", "bool"]:
        _extracted.append("True")
        _extracted.append("False")
    elif next_token.text == "None":
        _extracted.append("None")
    elif next_token.text in ["'", '"', "`"]:
        for token in doc[end + 1 :]:
            if token.text in ["'", '"', "`"]:
                break
            else:
                text += token.text

        if text == "None":
            _extracted.append("None")
        elif text in ["False", "True"]:
            _extracted.append("False")
            _extracted.append("True")
        elif text in ["int", "float"]:
            return None
        elif text != "":
            _extracted.append('"' + text + '"')

    return None


def _extract_indented_single_value(
    nlp_matcher: Matcher,  # noqa: ARG001
    doc: Doc,
    i: int,
    nlp_matches: list[tuple[Any, ...]],
) -> Any | None:
    """on-match function for the spaCy Matcher.

    Extract the standalone indented values.

    Parameters
    ----------
    nlp_matcher
        Parameter is ignored.
    doc
        Doc object that is checked for the active rules.
    i
        Index of the match that was recognized by the rule.
    nlp_matches
        List of matches found by the matcher.

    """
    _, start, end = nlp_matches[i]
    if end - start == 1:
        value = doc[start:end]
    else:
        value = doc[start : end - 1]

    value = value.text

    if value[0] in ["'", "`", '"']:
        value = re.sub(r"['`]", '"', value)
        if value[-1] != '"':
            value = value + '"'

    _extracted.append(value)

    return None


def _nlp_matches_to_readable_matches(
    nlp_matches: list[tuple[int, int, int]],
    nlp_: Language,
    doc_: Doc,
) -> list[tuple[str, Span]]:
    """Transform the matches list into a readable list.

    Parameters
    ----------
    nlp_matches
        list of spaCy matches
    nlp_
        spaCy natural language pipeline
    doc_
        Doc object that is checked for the active rules.

    """
    return [(nlp_.vocab.strings[match_id], doc_[start:end]) for match_id, start, end in nlp_matches]


def _preprocess_docstring(docstring: str, is_type_string: bool = False) -> str:
    """
    Preprocess docstring to make it easier to parse.

    Transform multiple back ticks to one back tick and replace multiple whitespaces with one whitespace if the
    docstrng to be processed is a type string.

    Parameters
    ----------
    docstring
        The docstring to be processed.

    Returns
    -------
        str
            The processed docstring.
    """
    docstring = re.sub(r"`+", "`", docstring)

    if is_type_string:
        docstring = re.sub(r"\s+", " ", docstring)

    return docstring


def extract_valid_literals(description: str, type_string: str) -> set[str]:
    """Extract all valid literals.

    Parameters
    ----------
    description
        Description string of the parameter to be examined.
    type_string
        Type string of the prameter to be examined.


    Returns
    -------
    set[str]
        Set of extracted literals.

    """
    _extracted.clear()

    nlp = MATCHER_CONFIG.get_nlp()
    descr_matcher = MATCHER_CONFIG.get_descr_matcher()
    type_matcher = MATCHER_CONFIG.get_type_matcher()

    type_match_labels = []

    none_and_bool = {"False", "None", "True"}

    description = _preprocess_docstring(description)
    desc_doc = nlp.make_doc(" ".join(description.split()))

    type_string = _preprocess_docstring(type_string, is_type_string=True)
    type_doc = nlp.make_doc(type_string)

    descr_matcher(desc_doc)

    type_matches = type_matcher(type_doc)
    type_matches = _nlp_matches_to_readable_matches(type_matches, nlp, type_doc)

    if type_matches:
        type_match_labels = [match_label for match_label, _ in type_matches]

        if "ENUM_BOOL" in type_match_labels:
            _extracted.append("True")
            _extracted.append("False")

        for match_label, match_span in type_matches:
            if match_label == "ENUM_TYPE_SINGLE_VALS" and "ENUM_TYPE_CURLY" not in type_match_labels:
                substituted_string = re.sub(r"['`]+", '"', match_span.text)
                _extracted.append(substituted_string)
    values_to_be_removed = []
    for val in _extracted:
        if val in ["True", "False"] and "ENUM_BOOL" not in type_match_labels:
            values_to_be_removed.append(val)
        if val[0] == '"' and not val[1:-1].isalpha():
            for c in val[1:-1]:
                if c in ["!", "§", "$", "%", "&", "/", "=", "?", "*", "~"]:
                    _extracted.remove(val)
                    break

    for val in values_to_be_removed:
        _extracted.remove(val)

    extracted_set = set(_extracted)

    is_enum_str = False
    for label, match_span in type_matches:
        if label == "ENUM_STR" and match_span.text != "of str":
            is_enum_str = True

    if is_enum_str and not extracted_set.difference(none_and_bool):
        extracted_set.add("unlistable_str")

    return extracted_set


MATCHER_CONFIG = MatcherConfiguration()
