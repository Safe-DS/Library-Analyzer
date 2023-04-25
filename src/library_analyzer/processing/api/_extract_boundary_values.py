import spacy
from spacy.matcher import Matcher
from spacy.tokens import Span
from typing import Union
from numpy import inf
from dataclasses import dataclass, field

Numeric = Union[int, float]
BoundaryValueType = tuple[str, tuple[Numeric | str, bool], tuple[Numeric | str, bool]]


@dataclass
class BoundaryList:
    _boundaries: set[BoundaryValueType] = field(default_factory=set[BoundaryValueType])

    def add_boundary(self, match_label: str, type_: str, match_string: Span = None) -> None:
        match match_label:
            case "BOUNDARY_NON_POSITIVE":
                self._boundaries.add(_create_non_positive_boundary(type_))
            case "BOUNDARY_POSITIVE":
                self._boundaries.add(_create_positive_boundary(type_))
            case "BOUNDARY_NON_NEGATIVE":
                self._boundaries.add(_create_non_negative_boundary(type_))
            case "BOUNDARY_NEGATIVE":
                self._boundaries.add(_create_negative_boundary(type_))
            case "BOUNDARY_BETWEEN":
                self._boundaries.add(_create_between_boundary(match_string, type_))
            case "BOUNDARY_INTERVAL":
                self._boundaries.add(_create_interval_boundary(match_string, type_))
            case "BOUNDARY_AT_LEAST":
                self._boundaries.add(_create_at_least_boundary(match_string, type_))

    def get_boundaries(self):
        return self._boundaries


type_funcs = {"float": float, "int": int}

_nlp = spacy.load("en_core_web_sm")
_matcher = Matcher(_nlp.vocab)

_boundary_at_least = [
    {"LOWER": "at"},
    {"LOWER": "least"},
    {"LIKE_NUM": True}
]

_boundary_min = [
    {"LOWER": "min"},
    {"ORTH": "."},
    {"LIKE_NUM": True}
]

_boundary_interval = [
    {"LOWER": "in"},
    {"LOWER": "the"},
    {"LOWER": {"IN": ["range", "interval"]}},
    {"LOWER": "of", "OP": "?"},
    {"ORTH": {"IN": ["(", "["]}},
    {},
    {"ORTH": ","},
    {},
    {"ORTH": {"IN": [")", "]"]}}
]

_boundary_value_in = [
    {"LOWER": {"FUZZY": "value"}},
    {"LOWER": {"IN": ["is", "in"]}},
    {"ORTH": {"IN": ["(", "["]}},
    {},
    {"ORTH": ","},
    {},
    {"ORTH": {"IN": [")", "]"]}}

]


_boundary_non_negative = [
    {"LOWER": {"IN": ["non", "not"]}},
    {"ORTH": {"IN": ["-", "_"]}, "OP": "?"},
    {"LOWER": "negative"}
 ]

_boundary_positive = [
    {"LOWER": "strictly", "OP": "?"},
    {"LOWER": "positive"}
]

_boundary_non_positive =[
    {"LOWER": {"IN": ["non", "not"]}},
    {"ORTH": {"IN": ["-", "_"]}, "OP": "?"},
    {"LOWER": "positive"}
]

_boundary_negative = [
    {"LOWER": "strictly", "OP": "?"},
    {"LOWER": "negative"}
]

_boundary_between = [
    {"LOWER": "between"},
    {"LIKE_NUM": True},
    {"LOWER": "and"},
    {"LIKE_NUM": True}
]

_boundary_type = [
    # {"LOWER": "if", "OP": "?"},
    {"LOWER": {"IN": ["float", "double", "int"]}}
]


def _check_negative_pattern(matcher, doc, i, matches):
    previous_id, _, _ = matches[i - 1]
    if _nlp.vocab.strings[previous_id] == "BOUNDARY_NON_NEGATIVE":
        matches.remove(matches[i])


def _check_positive_pattern(matcher, doc, i, matches):
    previous_id, _, _ = matches[i - 1]
    if _nlp.vocab.strings[previous_id] == "BOUNDARY_NON_POSITIVE":
        matches.remove(matches[i])


_matcher.add("BOUNDARY_AT_LEAST", [_boundary_at_least, _boundary_min])
_matcher.add("BOUNDARY_INTERVAL", [_boundary_interval, _boundary_value_in])
_matcher.add("BOUNDARY_POSITIVE", [_boundary_positive], on_match=_check_positive_pattern)
_matcher.add("BOUNDARY_NON_NEGATIVE", [_boundary_non_negative])
_matcher.add("BOUNDARY_NEGATIVE", [_boundary_negative], on_match=_check_negative_pattern)
_matcher.add("BOUNDARY_NON_POSITIVE", [_boundary_non_positive])
_matcher.add("BOUNDARY_BETWEEN", [_boundary_between])
_matcher.add("BOUNDARY_TYPE", [_boundary_type])


def _get_type_value(type_: str, value: Numeric | str) -> Numeric:
    return type_funcs[type_](value)


def _create_non_positive_boundary(type_: str) -> BoundaryValueType:
    return type_, ("negative infinity", False), (_get_type_value(type_, 0), True)


def _create_positive_boundary(type_: str) -> BoundaryValueType:
    return type_, (_get_type_value(type_, 0), False), ("infinity", False)


def _create_non_negative_boundary(type_: str) -> BoundaryValueType:
    return type_, (_get_type_value(type_, 0), True), ("infinity", False)


def _create_negative_boundary(type_: str) -> BoundaryValueType:
    return type_, ("negative infinity", False), (_get_type_value(type_, 0), False)


def _create_between_boundary(match_string: Span, type_: str) -> BoundaryValueType:
    values = []
    for token in match_string:
        if token.like_num:
            values.append(_get_type_value(type_, token.text))
    return type_, (min(values), True), (max(values), True)


def _create_at_least_boundary(match_string: Span, type_: str) -> BoundaryValueType:
    value = None
    for token in match_string:
        if token.like_num:
            value = _get_type_value(type_, token.text)
    return type_, (value, True), ("infinity", False)


def _create_interval_boundary(match_string: Span, type_: str) -> BoundaryValueType:
    values = []
    brackets = []
    for token in match_string:
        if token.text in ["(", "[", ")", "]"]:
            brackets.append(token.text)
        if token.like_num:
            values.append(_get_type_value(type_, token.text))

        if token.text in ["inf", "infty", "infinty"]:
            values.append(inf)
        elif token.text in ["negative inf", "negative infty", "negative infinity"]:
            values.append(-inf)

    minimum = ("negative infinity", False) if -inf in values else (min(values), brackets[0] == "[")
    maximum = ("infinity", False) if inf in values else (max(values), brackets[1] == "]")

    return type_, minimum, maximum



def extract_boundary(type_string: str, description: str) -> set[BoundaryValueType]:

    boundaries = BoundaryList()

    type_doc = _nlp(type_string)
    description_doc = _nlp(description)

    type_matches = _matcher(type_doc)
    type_matches = [(_nlp.vocab.strings[match_id], type_doc[start:end]) for match_id, start, end in type_matches]
    desc_matches = _matcher(description_doc)
    desc_matches = [(_nlp.vocab.strings[match_id], description_doc[start:end])
                    for match_id, start, end in desc_matches]

    if type_matches:
        type_list = []
        other_list = []
        match_label = None

        for match in type_matches:
            if match[0] == "BOUNDARY_TYPE":
                type_list.append(match[1].text)
            else:
                other_list.append(match[0])

        type_length = len(type_list)

        if type_length == 1:
            type_text = type_list[0]
            match_string = None

            if len(other_list) == 1:
                match_label = other_list[0]

            elif len(desc_matches) > 0:
                match_label, match_string = desc_matches[0]
                if match_label == "BOUNDARY_TYPE":
                    type_text = match_string.text
                    match_label, match_string = desc_matches[1]

            boundaries.add_boundary(match_label, type_text, match_string)

        elif type_length > 1:
            type_id = 0
            other_id = 0
            matches = []
            found_type = False
            for match_label, match_string in desc_matches:
                if match_label == "BOUNDARY_TYPE":
                    if found_type:
                        other_id += 1
                    matches.append({"id": type_id, "match_label": match_label, "match_string": match_string})
                    type_id += 1
                    found_type = True

                else:
                    matches.append({"id": other_id, "match_label": match_label, "match_string": match_string})
                    other_id += 1
                    if found_type:
                        found_type = False

            for i in range(max(type_id, other_id)):
                same_id = [match for match in matches if match['id'] == i]
                if len(same_id) == 2:
                    type_ = ""
                    match_string = ""
                    match_label = ""

                    for match in same_id:

                        if match["match_label"] == "BOUNDARY_TYPE":
                            type_ = match["match_string"].text
                        else:
                            match_label = match["match_label"]
                            match_string = match["match_string"]

                        boundaries.add_boundary(match_label, type_, match_string)

    return boundaries.get_boundaries()

