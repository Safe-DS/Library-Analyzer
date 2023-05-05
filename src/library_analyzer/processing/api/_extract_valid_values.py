from dataclasses import dataclass
from typing import Any

import spacy
from spacy import Language
from spacy.matcher import Matcher
from spacy.tokens import Doc, Span

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
    # {}
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
    nlp_matches: list[tuple[Any, ...]],  # noqa : ARG001
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
    next_token = doc[end]
    text = ""

    if next_token.text in ["True", "False"]:
        _extracted.append("True")
        _extracted.append("False")
    elif next_token.text == "None":
        _extracted.append("None")
    elif next_token.text in ["'", '"']:
        for token in doc[end+1:]:
            if token.text in ["'", '"']:
                break
            else:
                text += token.text
        _extracted.append('"' + text + '"')

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


def _extract_indented_value(
    nlp_matcher: Matcher, # noqa : ARG001
    doc: Doc,
    i: int,
    nlp_matches: list[tuple[Any, ...]]
) -> Any | None:
    _, start, end = nlp_matches[i]

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


def extract_valid_literals(description: str, type_string: str) -> set[str]:
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



