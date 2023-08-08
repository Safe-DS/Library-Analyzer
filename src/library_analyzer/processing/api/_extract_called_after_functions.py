from dataclasses import dataclass
from typing import Any
import re
from spacy.tokens import Doc

from library_analyzer.utils import load_language
from spacy.matcher import Matcher

_nlp = load_language("en_core_web_sm")
_matcher = Matcher(_nlp.vocab)
_called_after_functions: list[str] = []
_after_or_before = ""


@dataclass
class CalledAfterValues:
    function_name: str
    called_after_functions: list[str]
    after_or_before: str


_must_be_called_after = [
    {"LOWER": "must"},
    {"LOWER": "be"},
    {"LOWER": "called"},
    {"LOWER": "after"}
]

_must_be_called_before = [
    {"LOWER": "must"},
    {"LOWER": "be"},
    {"LOWER": "called"},
    {"LOWER": "before"}
]

_is_called = [
    {"LOWER": {"IN": ["before", "after"]}},
    {},
    {"OP": "?"},
    {"OP": "?"},
    {"LOWER": "is"},
    {"LOWER": "called"}
]


def _preprocess_docstring(docstring: str) -> str:
    """
    Preprocess docstring to make it easier to parse.

    1. Remove cluttered punctuation around parameter references
    2. Set '=', ==' to 'equals' and set '!=' to 'does not equal'
    4. Handle cases of step two where the signs are not separate tokens, e.g. "a=b".
    Note ordered dict since "=" is a substring of the other symbols.

    Parameters
    ----------
    docstring
        The docstring to be processed.

    Returns
    -------
        str
            The processed docstring.
    """
    docstring = re.sub(r'["“”`]', "", docstring)
    docstring = re.sub(r"'", "", docstring)

    docstring = re.sub(r"!=", " does not equal ", docstring)
    docstring = re.sub(r"==?", " equals ", docstring)
    return re.sub(r"\s+", " ", docstring)


def _extract_function(
    matcher: Matcher,  # noqa: ARG001
    doc: Doc,
    i: int,
    matches: list[tuple[Any, ...]],
) -> Any | None:
    """on-match function for the spaCy Matcher.

    Extract the function that must be called before or after a function.

    Parameters
    ----------
    matcher
        Parameter is ignored.
    doc
        Doc object that is checked for the active rules.

    i
        Index of the match that was recognized by the rule.

    matches
        List of matches found by the matcher.

    """
    global _after_or_before
    match_ = matches[i]
    match_id_string = _nlp.vocab.strings[match_[0]]

    if match_id_string == "CALLED_AFTER:MUST_BE_CALLED_AFTER":
        _after_or_before = "after"
        after_token = doc[match_[2]]
        func_names = [after_token.text]

        if after_token.nbor(1).text == "or":
            func_names.append(after_token.nbor(2).text)

    elif match_id_string == "CALLED_AFTER:MUST_BE_CALLED_BEFORE":
        _after_or_before = "before"
        first_token = doc[match_[1]]
        func_names = [first_token.nbor(-1).text]

        if first_token.nbor(-2).text == "or":
            func_names.append(first_token.nbor(-3).text)

    elif match_id_string == "CALLED_AFTER:IS_CALLED":
        _after_or_before = "after"
        func_names = [doc[match_[2] + 1].text]

    else:
        raise KeyError(f"Unknown match_id_string({match_id_string}) was found")

    for func_name in func_names:
        _called_after_functions.append(func_name)
    return None


def extract_called_after_functions(function_qname: str, description: str) -> CalledAfterValues:
    """Extract all CalledAfter functions of the function to be examined.

    Parameters
    ----------
    function_qname
        Quality name of the function to be examined.

    description
        Description of the function to be examined.

    Returns
    -------
    CalledAfterValues
        All Called-After functions are returned that were found in the context of the function to be examined.

    """
    _called_after_functions.clear()

    description_preprocessed = _preprocess_docstring(description)
    description_doc = _nlp.make_doc(description_preprocessed)
    _matcher(description_doc)

    return CalledAfterValues(function_qname, _called_after_functions, _after_or_before)


_matcher.add("CALLED_AFTER:MUST_BE_CALLED_BEFORE", [_must_be_called_before], on_match=_extract_function)
_matcher.add("CALLED_AFTER:MUST_BE_CALLED_AFTER", [_must_be_called_after], on_match=_extract_function)
_matcher.add("CALLED_AFTER:IS_CALLED", [_is_called], greedy="LONGEST", on_match=_extract_function)
