import spacy
from spacy.matcher import Matcher
from spacy.tokens import Span, Doc
from typing import Union, Any
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
            case "BOUNDARY_INTERVAL_RELATIONAL":
                self._boundaries.add(_create_interval_relational_boundary(match_string, type_))

    def get_boundaries(self) -> set[BoundaryValueType]:
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

_boundary_gtlt_gtlt = [
    {"LIKE_NUM": True},
    {"ORTH": {"IN": ["<", ">"]}},
    {},
    {"ORTH": {"IN": ["<", ">"]}},
    {"LIKE_NUM": True}
]

_boundary_geqleq_geqleq = [
    {"LIKE_NUM": True},
    {"ORTH": {"IN": ["<", ">"]}},
    {"ORTH": "="},
    {},
    {"ORTH": {"IN": ["<", ">"]}},
    {"ORTH": "="},
    {"LIKE_NUM": True}
]

_boundary_gtlt_geqleq = [
    {"LIKE_NUM": True},
    {"ORTH": {"IN": ["<", ">"]}},
    {},
    {"ORTH": {"IN": ["<", ">"]}},
    {"ORTH": "="},
    {"LIKE_NUM": True}
]

_boundary_geqleq_gtlt = [
    {"LIKE_NUM": True},
    {"ORTH": {"IN": ["<", ">"]}},
    {"ORTH": "="},
    {},
    {"ORTH": {"IN": ["<", ">"]}},
    {"LIKE_NUM": True}
]

_boundary_and_gtlt_gtlt = [
    {"ORTH": {"IN": ["<", ">"]}},
    {"LIKE_NUM": True},
    {"ORTH": {"IN": ["and", "or"]}},
    {"ORTH": {"IN": ["<", ">"]}},
    {"LIKE_NUM": True}
]

_boundary_and_geqleq_geqleq = [
    {"ORTH": {"IN": ["<", ">"]}},
    {"ORTH": "="},
    {"LIKE_NUM": True},
    {"ORTH": {"IN": ["and", "or"]}},
    {"ORTH": {"IN": ["<", ">"]}},
    {"ORTH": "="},
    {"LIKE_NUM": True}
]

_boundary_and_gtlt_geqleq = [
    {"ORTH": {"IN": ["<", ">"]}},
    {"LIKE_NUM": True},
    {"ORTH": {"IN": ["and", "or"]}},
    {"ORTH": {"IN": ["<", ">"]}},
    {"ORTH": "="},
    {"LIKE_NUM": True}
]

_boundary_and_geqleq_gtlt = [
    {"ORTH": {"IN": ["<", ">"]}},
    {"ORTH": "="},
    {"LIKE_NUM": True},
    {"ORTH": {"IN": ["and", "or"]}},
    {"ORTH": {"IN": ["<", ">"]}},
    {"LIKE_NUM": True}
]

_boundary_type = [
    {"LOWER": {"IN": ["float", "double", "int"]}}
]


def _check_negative_pattern(matcher: Matcher, doc: Doc, i: int, matches: list[tuple[Any, ...]]) -> Any | None:
    """on-match function for the spaCy Matcher

    Delete the BOUNDARY_NEGATIVE match if the BOUNDARY_NON_NEGATIVE rule has already been detected.

    Parameters
    ----------
    matcher
        Parameter is ignored.
    doc
        Parameter is ignored.
    i
        Index of the match that was recognized by the rule.

    matches
        List of matches found by the matcher

    """
    previous_id, _, _ = matches[i - 1]
    if _nlp.vocab.strings[previous_id] == "BOUNDARY_NON_NEGATIVE":
        matches.remove(matches[i])

    return None


def _check_positive_pattern(matcher: Matcher, doc: Doc, i: int, matches: list[tuple[Any, ...]]) -> Any | None:
    """on-match function for the spaCy Matcher

    Delete the BOUNDARY_POSITIVE match if the BOUNDARY_NON_POSITIVE rule has already been detected.

    Parameters
    ----------
    matcher
        Parameter is ignored.
    doc
        Parameter is ignored.
    i
        Index of the match that was recognized by the rule.

    matches
        List of matches found by the matcher

    """
    previous_id, _, _ = matches[i - 1]
    if _nlp.vocab.strings[previous_id] == "BOUNDARY_NON_POSITIVE":
        matches.remove(matches[i])

    return None


relational_patterns = [
    _boundary_gtlt_gtlt, _boundary_geqleq_geqleq, _boundary_geqleq_gtlt, _boundary_gtlt_geqleq,
    _boundary_and_gtlt_gtlt, _boundary_and_geqleq_geqleq, _boundary_and_geqleq_gtlt, _boundary_and_gtlt_geqleq
]

_matcher.add("BOUNDARY_AT_LEAST", [_boundary_at_least, _boundary_min])
_matcher.add("BOUNDARY_INTERVAL", [_boundary_interval, _boundary_value_in])
_matcher.add("BOUNDARY_POSITIVE", [_boundary_positive], on_match=_check_positive_pattern)
_matcher.add("BOUNDARY_NON_NEGATIVE", [_boundary_non_negative])
_matcher.add("BOUNDARY_NEGATIVE", [_boundary_negative], on_match=_check_negative_pattern)
_matcher.add("BOUNDARY_NON_POSITIVE", [_boundary_non_positive])
_matcher.add("BOUNDARY_BETWEEN", [_boundary_between])
_matcher.add("BOUNDARY_INTERVAL_RELATIONAL", relational_patterns)
_matcher.add("BOUNDARY_TYPE", [_boundary_type])


def _get_type_value(type_: str, value: Numeric | str) -> Numeric:
    """Transform the passed value to the value matching type_.

    Parameters
    ----------
    type_
        Type to be transformed to.
    value
        Value to be transformed.

    Returns
    -------
    Numeric
        Transformed value.
    """
    return type_funcs[type_](value)


def _create_non_positive_boundary(type_: str) -> BoundaryValueType:
    """Create a BoundaryValueType with predefined extrema.

    Create a BoundaryValueType that describes the non-positive value range of the given type.

    Parameters
    ----------
    type_
        Boundary type

    Returns
    -------
    BoundaryValueType
        Triple consisting of the type, the minimum and the maximum of the boundary.
        The boolean value of the extrema indicates whether the value is included in the value range.
    """
    return type_, ("negative infinity", False), (_get_type_value(type_, 0), True)


def _create_positive_boundary(type_: str) -> BoundaryValueType:
    """Create a BoundaryValueType with predefined extrema.

    Create a BoundaryValueType that describes the positive value range of the given type.

    Parameters
    ----------
    type_
        Boundary type

    Returns
    -------
    BoundaryValueType
        Triple consisting of the type, the minimum and the maximum of the boundary.
        The boolean value of the extrema indicates whether the value is included in the value range.
    """
    return type_, (_get_type_value(type_, 0), False), ("infinity", False)


def _create_non_negative_boundary(type_: str) -> BoundaryValueType:
    """Create a BoundaryValueType with predefined extrema.

    Create a BoundaryValueType that describes the non-negative value range of the given type.

    Parameters
    ----------
    type_
        Boundary type

    Returns
    -------
    BoundaryValueType
        Triple consisting of the type, the minimum and the maximum of the boundary.
        The boolean value of the extrema indicates whether the value is included in the value range.
    """
    return type_, (_get_type_value(type_, 0), True), ("infinity", False)


def _create_negative_boundary(type_: str) -> BoundaryValueType:
    """Create a BoundaryValueType with predefined extrema.

    Create a BoundaryValueType that describes the negative value range of the given type.

    Parameters
    ----------
    type_
        Boundary type

    Returns
    -------
    BoundaryValueType
        Triple consisting of the type, the minimum and the maximum of the boundary.
        The boolean value of the extrema indicates whether the value is included in the value range.
    """
    return type_, ("negative infinity", False), (_get_type_value(type_, 0), False)


def _create_between_boundary(match_string: Span, type_: str) -> BoundaryValueType:
    """Create a BoundaryValueType with individual extrema.

    Create a 'between' BoundaryValueType whose extrema are extracted from the passed match string.

    Parameters
    ----------
    match_string
        Match string containing the extrema of the value range.
    type_
        Boundary Type

    Returns
    -------
    BoundaryValueType
        Triple consisting of the type, the minimum and the maximum of the boundary.
        The boolean value of the extrema indicates whether the value is included in the value range.

    """
    values = []
    for token in match_string:
        if token.like_num:
            values.append(_get_type_value(type_, token.text))
    return type_, (min(values), True), (max(values), True)


def _create_at_least_boundary(match_string: Span, type_: str) -> BoundaryValueType:
    """Create a BoundaryValueType with individual minimum.

    Create a BoundaryValueType whose minimum is extracted from the passed match string.

    Parameters
    ----------
    match_string
        Match string containing the minimum of the value range.
    type_
        Boundary Type

    Returns
    -------
    BoundaryValueType
        Triple consisting of the type, the minimum and the maximum of the boundary.
        The boolean value of the extrema indicates whether the value is included in the value range.

    """
    value: Numeric = 0
    for token in match_string:
        if token.like_num:
            value = _get_type_value(type_, token.text)
    return type_, (value, True), ("infinity", False)


def _create_interval_boundary(match_string: Span, type_: str) -> BoundaryValueType:
    """Create a BoundaryValueType with individual extrema.

    Create a BoundaryValueType whose extrema are extracted from the passed match string.

    Parameters
    ----------
    match_string
        Match string containing the extrema of the value range.
    type_
        Boundary Type

    Returns
    -------
    BoundaryValueType
        Triple consisting of the type, the minimum and the maximum of the boundary.
        The boolean value of the extrema indicates whether the value is included in the value range.

    """
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

    type_func = type_funcs[type_]
    minimum = ("negative infinity", False) if -inf in values else (type_func(min(values)), brackets[0] == "[")
    maximum = ("infinity", False) if inf in values else (type_func(max(values)), brackets[1] == "]")

    return type_, minimum, maximum


def _create_interval_relational_boundary(match_string: Span, type_: str) -> BoundaryValueType:
    """Create a BoundaryValueType with individual extrema.

    Create a BoundaryValueType whose extrema are extracted from the passed match string.

    Parameters
    ----------
    match_string
        Match string containing the extrema of the value range.
    type_
        Boundary Type

    Returns
    -------
    BoundaryValueType
        Triple consisting of the type, the minimum and the maximum of the boundary.
        The boolean value of the extrema indicates whether the value is included in the value range.

    """
    relational_ops = []
    values = []
    and_or_found = False

    for token in match_string:
        if token.text in ["<", ">"]:
            relational_ops.append(token.text)
        elif token.text == "=":
            relational_ops[len(relational_ops) - 1] += token.text
        elif token.like_num:
            values.append(token.text)
        elif token.text in ["and", "or"]:
            and_or_found = True
    type_func = type_funcs[type_]

    if not and_or_found:
        minimum = (type_func(min(values)), (relational_ops[0] == "<=") or (relational_ops[1] == ">="))
        maximum = (type_func(max(values)), (relational_ops[1] == "<=") or (relational_ops[0] == ">="))
    else:
        minimum = (type_func(min(values)), ">=" in relational_ops)
        maximum = (type_func(max(values)), "<=" in relational_ops)

    return type_, minimum, maximum


def extract_boundary(description: str, type_string: str) -> set[BoundaryValueType]:
    """Extract valid BoundaryValueTypes.

    Extract valid BoundaryValueTypes described by predefined rules.

    Parameters
    ----------
    description
        Description string of the parameter to be examined.

    type_string
        Type string of the parameter to be examined.

    Returns
    -------
    set[BoundaryValueType]
        A set containing valid BoundaryValueTypes.
    """

    boundaries = BoundaryList()

    type_doc = _nlp(type_string)
    type_matches = _matcher(type_doc)
    type_matches = [(_nlp.vocab.strings[match_id], type_doc[start:end]) for match_id, start, end in type_matches]

    description_doc = _nlp(description)
    desc_matches = _matcher(description_doc)
    desc_matches = [(_nlp.vocab.strings[match_id], description_doc[start:end])
                    for match_id, start, end in desc_matches]

    if type_matches:
        type_list = []  # Possible numeric data types that may be used with the parameter to be examined.
        restriction_list = [] # Restrictions of the type such as non-negative
        match_label = ""

        for match in type_matches:
            if match[0] == "BOUNDARY_TYPE":
                type_list.append(match[1].text)
            else:
                restriction_list.append(match[0])

        type_length = len(type_list)

        # If the length of the found types is 1, the boundary type is described only in the type string
        # and the value range only in the description string.

        if type_length == 1:
            type_text = type_list[0]
            match_string = None

            if len(restriction_list) == 1:
                match_label = restriction_list[0]

            # Checking the description for boundaries if no restriction was found in the type string
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

            # Assignment of the found boundaries to the corresponding data type
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

            # Creation of the matching BoundaryValueTypes
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

