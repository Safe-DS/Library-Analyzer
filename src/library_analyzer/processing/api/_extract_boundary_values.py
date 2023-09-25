from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, TypeAlias

from numpy import inf
from spacy.matcher import Matcher

from library_analyzer.processing.api.model import BoundaryType
from library_analyzer.utils import load_language

if TYPE_CHECKING:
    from spacy.tokens import Doc, Span

_Numeric: TypeAlias = int | float


@dataclass
class BoundaryList:
    _boundaries: set[BoundaryType] = field(default_factory=set[BoundaryType])

    def add_boundary(self, match_label: str, type_: str, match_string: Span = None) -> None:
        """Add a boundary according to the matched rule.

        Parameters
        ----------
        match_label
            Label of the matched rule
        type_
            Base type of the boundary to be created
        match_string
            Span containing the string matched by the corresponding rule.
            This parameter is not required for every rule.

        """
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
                boundary = _create_interval_boundary(match_string, type_)
                if boundary is not None:
                    self._boundaries.add(boundary)
            case "BOUNDARY_AT_LEAST":
                self._boundaries.add(_create_at_least_boundary(match_string, type_))
            case "BOUNDARY_INTERVAL_RELATIONAL":
                self._boundaries.add(_create_interval_relational_boundary(match_string, type_))
            case "BOUNDARY_TYPE_REL_VAL":
                self._boundaries.add(_create_type_rel_val_boundary(match_string, type_))
            case "BOUNDARY_INTERVAL_IN_BRACKETS":
                boundary = _create_interval_in_brackets_boundary(match_string, type_)
                if boundary is not None:
                    self._boundaries.add(boundary)

    def get_boundaries(self) -> set[BoundaryType]:
        return self._boundaries


type_funcs = {"float": float, "int": int}

_nlp = load_language("en_core_web_sm")
_matcher = Matcher(_nlp.vocab)

_rel_ops = {"ORTH": {"IN": ["GT$", "LT$", "GEQ$", "LEQ$"]}}

_boundary_type = {"LOWER": {"IN": ["float", "int"]}}

_boundary_type_rel_val = [_boundary_type, _rel_ops, {"LIKE_NUM": True}]

_boundary_rel_interval = [{"LIKE_NUM": True}, _rel_ops, {}, _rel_ops, {"LIKE_NUM": True}]

_boundary_and_rel_interval = [
    _rel_ops,
    {"LIKE_NUM": True},
    {"ORTH": {"IN": ["and", "or"]}},
    _rel_ops,
    {"LIKE_NUM": True},
]

_boundary_at_least = [{"LOWER": "at"}, {"LOWER": "least"}, {"LIKE_NUM": True}]

_boundary_min = [{"LOWER": "min"}, {"ORTH": "."}, {"LIKE_NUM": True}]

_boundary_interval = [
    {"LOWER": {"IN": ["in", "within"]}},
    {"LOWER": "the", "OP": "?"},
    {"LOWER": {"IN": ["range", "interval"]}, "OP": "?"},
    {"LOWER": "of", "OP": "?"},
    {"ORTH": {"IN": ["(", "["]}},
    {},
    {"ORTH": ","},
    {},
    {"ORTH": {"IN": [")", "]"]}},
]


_boundary_value_in = [
    {"LOWER": {"FUZZY": "value"}},
    {"LOWER": {"IN": ["is", "in"]}},
    {"ORTH": {"IN": ["(", "["]}},
    {},
    {"ORTH": ","},
    {},
    {"ORTH": {"IN": [")", "]"]}},
]


_boundary_non_negative = [
    {"LOWER": {"IN": ["non", "not"]}},
    {"ORTH": {"IN": ["-", "_"]}, "OP": "?"},
    {"LOWER": "negative"},
]

_boundary_positive = [{"LOWER": "strictly", "OP": "?"}, {"LOWER": "positive"}]

_boundary_non_positive = [
    {"LOWER": {"IN": ["non", "not"]}},
    {"ORTH": {"IN": ["-", "_"]}, "OP": "?"},
    {"LOWER": "positive"},
]

_boundary_negative = [{"LOWER": "strictly", "OP": "?"}, {"LOWER": "negative"}]

_boundary_between = [
    {"LOWER": "strictly", "OP": "?"},
    {"LOWER": "between"},
    {"LIKE_NUM": True},
    {"LOWER": "and"},
    {"LIKE_NUM": True},
]

_boundary_interval_in_brackets = [
    _boundary_type,
    {"ORTH": "("},
    {"ORTH": {"IN": ["(", "["]}},
    {},
    {"ORTH": ","},
    {},
    {"ORTH": {"IN": [")", "]"]}},
    {"ORTH": ")"},
]


def _check_negative_pattern(
    matcher: Matcher,  # noqa: ARG001
    doc: Doc,  # noqa: ARG001
    i: int,
    matches: list[tuple[Any, ...]],
) -> Any | None:
    """on-match function for the spaCy Matcher.

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


def _check_positive_pattern(
    matcher: Matcher,  # noqa: ARG001
    doc: Doc,  # noqa: ARG001
    i: int,
    matches: list[tuple[Any, ...]],
) -> Any | None:
    """on-match function for the spaCy Matcher.

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


def _check_interval_relational_pattern(
    matcher: Matcher,  # noqa: ARG001
    doc: Doc,  # noqa: ARG001
    i: int,
    matches: list[tuple[Any, ...]],
) -> Any | None:
    """on-match function for the spaCy Matcher.

    Delete the BOUNDARY_TYPE_REL_VAL match if the BOUNDARY_INTERVAL_RELATIONAL rule has been detected.

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
    if _nlp.vocab.strings[previous_id] == "BOUNDARY_TYPE_REL_VAL":
        matches.remove(matches[i - 1])

    return None


def _check_interval(
    matcher: Matcher,  # noqa: ARG001
    doc: Doc,  # noqa: ARG001
    i: int,
    matches: list[tuple[Any, ...]],
) -> Any | None:
    """on-match function for the spaCy Matcher.

    Delete the BOUNDARY_INTERVAL match if the BOUNDARY_INTERVAL rule has been already detected.

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
    if _nlp.vocab.strings[previous_id] == "BOUNDARY_INTERVAL" and (len(matches) > 1):
        matches.remove(matches[i - 1])

    return None


_matcher.add("BOUNDARY_AT_LEAST", [_boundary_at_least, _boundary_min])
_matcher.add("BOUNDARY_INTERVAL", [_boundary_interval, _boundary_value_in], on_match=_check_interval)
_matcher.add("BOUNDARY_POSITIVE", [_boundary_positive], on_match=_check_positive_pattern)
_matcher.add("BOUNDARY_NON_NEGATIVE", [_boundary_non_negative])
_matcher.add("BOUNDARY_NEGATIVE", [_boundary_negative], on_match=_check_negative_pattern)
_matcher.add("BOUNDARY_NON_POSITIVE", [_boundary_non_positive])
_matcher.add("BOUNDARY_BETWEEN", [_boundary_between], greedy="LONGEST")
_matcher.add(
    "BOUNDARY_INTERVAL_RELATIONAL",
    [_boundary_rel_interval, _boundary_and_rel_interval],
    on_match=_check_interval_relational_pattern,
)
_matcher.add("BOUNDARY_TYPE", [[_boundary_type]])
_matcher.add("BOUNDARY_TYPE_REL_VAL", [_boundary_type_rel_val])
_matcher.add("BOUNDARY_INTERVAL_IN_BRACKETS", [_boundary_interval_in_brackets])


def _get_type_value(type_: str, value: _Numeric | str) -> _Numeric:
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
    numbers = {
        "zero": 0,
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
    }
    if isinstance(value, str) and value.lower() in numbers:
        value = numbers[value]

    return type_funcs[type_.lower()](value)


def _create_non_positive_boundary(type_: str) -> BoundaryType:
    """Create a BoundaryType with predefined extrema.

    Create a BoundaryType that describes the non-positive value range of the given type.

    Parameters
    ----------
    type_
        Base type of Boundary

    Returns
    -------
    BoundaryType

    """
    return BoundaryType(
        type_,
        min=BoundaryType.NEGATIVE_INFINITY,
        max=_get_type_value(type_, 0),
        min_inclusive=False,
        max_inclusive=True,
    )


def _create_positive_boundary(type_: str) -> BoundaryType:
    """Create a BoundaryType with predefined extrema.

    Create a BoundaryType that describes the positive value range of the given type.

    Parameters
    ----------
    type_
        Base type of Boundary

    Returns
    -------
    BoundaryType

    """
    return BoundaryType(
        type_,
        min=_get_type_value(type_, 0),
        max=BoundaryType.INFINITY,
        min_inclusive=False,
        max_inclusive=False,
    )


def _create_non_negative_boundary(type_: str) -> BoundaryType:
    """Create a BoundaryType with predefined extrema.

    Create a BoundaryType that describes the non-negative value range of the given type.

    Parameters
    ----------
    type_
        Base type of Boundary

    Returns
    -------
    BoundaryType

    """
    return BoundaryType(
        type_,
        min=_get_type_value(type_, 0),
        max=BoundaryType.INFINITY,
        min_inclusive=True,
        max_inclusive=False,
    )


def _create_negative_boundary(type_: str) -> BoundaryType:
    """Create a BoundaryType with predefined extrema.

    Create a BoundaryType that describes the negative value range of the given type.

    Parameters
    ----------
    type_
        Base type of Boundary

    Returns
    -------
    BoundaryType

    """
    # return type_, ("negative infinity", False), (_get_type_value(type_, 0), False)
    return BoundaryType(
        type_,
        min=BoundaryType.NEGATIVE_INFINITY,
        max=_get_type_value(type_, 0),
        min_inclusive=False,
        max_inclusive=False,
    )


def _create_between_boundary(match_string: Span, type_: str) -> BoundaryType:
    """Create a BoundaryType with individual extrema.

    Create a BoundaryType whose extrema are extracted from the passed match string.

    Parameters
    ----------
    match_string
        Match string containing the extrema of the value range.
    type_
        Base type of Boundary

    Returns
    -------
    BoundaryType

    """
    values = []
    min_incl = True
    max_incl = True
    for token in match_string:
        if token.text == "strictly":
            min_incl = False
            max_incl = False
        if token.like_num:
            values.append(_get_type_value(type_, token.text))
    return BoundaryType(type_, min=min(values), max=max(values), min_inclusive=min_incl, max_inclusive=max_incl)


def _create_at_least_boundary(match_string: Span, type_: str) -> BoundaryType:
    """Create a BoundaryType with individual minimum.

    Create a BoundaryType whose minimum is extracted from the passed match string.

    Parameters
    ----------
    match_string
        Match string containing the minimum of the value range.
    type_
        Base type of Boundary

    Returns
    -------
    BoundaryType

    """
    value: _Numeric = 0
    for token in match_string:
        if token.like_num:
            value = _get_type_value(type_, token.text)
    return BoundaryType(type_, min=value, max=BoundaryType.INFINITY, min_inclusive=True, max_inclusive=False)


def _create_interval_boundary(match_string: Span, type_: str) -> BoundaryType | None:
    """Create a BoundaryType with individual extrema.

    Create a BoundaryType whose extrema are extracted from the passed match string.

    Parameters
    ----------
    match_string
        Match string containing the extrema of the value range.
    type_
        Base type of Boundary

    Returns
    -------
    BoundaryType

    """
    scientific_notation = r"[+\-]?\d+[eE][+\-]?\d+"
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
        elif re.match(scientific_notation, token.text) is not None:
            values.append(float(token.text))

    if len(values) != 2:
        return None

    type_func = type_funcs[type_]

    if -inf in values:
        minimum = BoundaryType.NEGATIVE_INFINITY
        min_incl = False
    else:
        minimum = type_func(min(values))
        min_incl = brackets[0] == "["

    if inf in values:
        maximum = BoundaryType.INFINITY
        max_incl = False
    else:
        maximum = type_func(max(values))
        max_incl = brackets[1] == "]"

    return BoundaryType(type_, min=minimum, max=maximum, min_inclusive=min_incl, max_inclusive=max_incl)


def _create_interval_relational_boundary(match_string: Span, type_: str) -> BoundaryType:
    """Create a BoundaryType with individual extrema.

    Create a BoundaryType whose extrema are extracted from the passed match string.

    Parameters
    ----------
    match_string
        Match string containing the extrema of the value range.
    type_
        Base type of Boundary

    Returns
    -------
    BoundaryType

    """
    relational_ops = []
    values = []
    and_or_found = False

    for token in match_string:
        if token.like_num:
            values.append(token.text)
        else:
            match token.text:
                case "LT$":
                    relational_ops.append("<")
                case "GT$":
                    relational_ops.append(">")
                case "LEQ$":
                    relational_ops.append("<=")
                case "GEQ$":
                    relational_ops.append(">=")
                case "and" | "or":
                    and_or_found = True

    type_func = type_funcs[type_]

    minimum = type_func(min(values))
    maximum = type_func(max(values))

    if not and_or_found:
        min_incl = (relational_ops[0] == "<=") or (relational_ops[1] == ">=")
        max_incl = (relational_ops[1] == "<=") or (relational_ops[0] == ">=")
    else:
        min_incl = ">=" in relational_ops
        max_incl = "<=" in relational_ops

    return BoundaryType(type_, min=minimum, max=maximum, min_inclusive=min_incl, max_inclusive=max_incl)


def _create_type_rel_val_boundary(match_string: Span, type_: str) -> BoundaryType:
    """Create a BoundaryType with individual minimum or maximum.

    Create a BoundaryType whose minimum or maximum is extracted from the passed match string.

    Parameters
    ----------
    match_string
        Match string containing the extrema of the value range.
    type_
        Base type of Boundary

    Returns
    -------
    BoundaryType

    """
    val: _Numeric = 0
    min_: _Numeric | str = 0
    max_: _Numeric | str = 0

    rel_op = ""
    type_func = type_funcs[type_]
    min_incl = False
    max_incl = False

    for token in match_string:
        if token.like_num:
            val = type_func(token.text)
        else:
            match token.text:
                case "LT$":
                    rel_op = "<"
                case "GT$":
                    rel_op = ">"
                case "LEQ$":
                    rel_op = "<="
                case "GEQ$":
                    rel_op = ">="

    # type (< | <=) val
    if rel_op in ["<", "<="]:
        min_ = BoundaryType.NEGATIVE_INFINITY
        max_ = val
        if rel_op == "<=":
            max_incl = True

    # type (> | >=) val
    elif rel_op in [">", ">="]:
        min_ = val
        max_ = BoundaryType.INFINITY
        if rel_op == ">=":
            min_incl = True

    return BoundaryType(type_, min=min_, max=max_, min_inclusive=min_incl, max_inclusive=max_incl)


def _create_interval_in_brackets_boundary(match_string: Span, type_: str) -> BoundaryType | None:
    span_ = match_string[2:-1]

    return _create_interval_boundary(span_, type_)


def _analyze_matches(matches: list[tuple[str, Span]], boundaries: BoundaryList) -> None:
    """Analyze the passed match list for boundaries to be created.

    Parameters
    ----------
    matches
        Matches found by spaCy Matcher.

    boundaries
        BoundaryList object that creates and contains the matching boundary objects.

    """
    type_id = 0
    other_id = 0
    processed_matches = []
    found_type = False
    # Assignment of the found boundaries to the corresponding data type
    for match_label, match_string in matches:
        if match_label == "BOUNDARY_TYPE":
            if found_type:
                other_id += 1
            processed_matches.append({"id": type_id, "match_label": match_label, "match_string": match_string})
            type_id += 1
            found_type = True

        else:
            processed_matches.append({"id": other_id, "match_label": match_label, "match_string": match_string})
            other_id += 1
            if found_type:
                found_type = False

    # Creation of the matching BoundaryTypes
    for i in range(max(type_id, other_id)):
        same_id = [match for match in processed_matches if match["id"] == i]
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


def _preprocess_docstring(docstring: str) -> str:
    """
    Preprocess docstring to make it easier to parse.

    1. Encode relational operators
    2. Remove back ticks
    3. Transform multiple whitespaces to one

    Parameters
    ----------
    docstring
        The docstring to be processed.

    Returns
    -------
        str
            The processed docstring.
    """
    docstring = re.sub(r">=", "GEQ$", docstring)
    docstring = re.sub(r"<=", "LEQ$", docstring)
    docstring = re.sub(r"<", "LT$", docstring)
    docstring = re.sub(r">", "GT$", docstring)

    docstring = re.sub(r"`", "", docstring)
    return re.sub(r"\s+", " ", docstring)


def extract_boundary(description: str, type_string: str) -> set[BoundaryType]:
    """Extract valid BoundaryTypes.

    Extract valid BoundaryTypes described by predefined rules.

    Parameters
    ----------
    description
        Description string of the parameter to be examined.

    type_string
        Type string of the parameter to be examined.

    Returns
    -------
    set[BoundaryType]
        A set containing valid BoundaryTypes.
    """
    boundaries = BoundaryList()

    type_string = _preprocess_docstring(type_string)
    type_doc = _nlp(type_string)

    type_matches = _matcher(type_doc)
    type_matches = [(_nlp.vocab.strings[match_id], type_doc[start:end]) for match_id, start, end in type_matches]

    description_preprocessed = _preprocess_docstring(description)
    description_doc = _nlp(description_preprocessed)

    desc_matches = []
    for sent in description_doc.sents:
        d_matches = _matcher(sent)
        d_matches = [(_nlp.vocab.strings[match_id], sent[start:end]) for match_id, start, end in d_matches]
        desc_matches.extend(d_matches)

    if type_matches:
        type_list = []  # Possible numeric data types that may be used with the parameter to be examined.
        restriction_list = []  # Restrictions of the type such as non-negative
        match_label = ""

        for match in type_matches:
            if match[0] == "BOUNDARY_TYPE":
                type_list.append(match[1].text)
            else:
                restriction_list.append(match)

        type_length = len(type_list)

        # If the length of the found types is 1, the boundary type is described only in the type string
        # and the value range only in the description string.

        if type_length == 1:
            type_text = type_list[0]
            match_string: Span | None = None

            if len(restriction_list) == 1:
                match_label = restriction_list[0][0]
                match_string = restriction_list[0][1]

            # Checking the description for boundaries if no restriction was found in the type string
            elif len(desc_matches) > 0:
                match_label, match_string = desc_matches[0]
                for m_label, m_string in desc_matches:
                    if m_label == "BOUNDARY_INTERVAL":
                        match_label = m_label
                        match_string = m_string
                        break

                if match_label == "BOUNDARY_TYPE" and len(desc_matches) > 1:
                    type_text = match_string.text
                    match_label, match_string = desc_matches[1]

            boundaries.add_boundary(match_label, type_text, match_string)

        elif type_length > 1:
            found_type_rel_val = any(match[0] == "BOUNDARY_TYPE_REL_VAL" for match in type_matches)

            if found_type_rel_val:
                _analyze_matches(type_matches, boundaries)
            else:
                _analyze_matches(desc_matches, boundaries)

    return boundaries.get_boundaries()
