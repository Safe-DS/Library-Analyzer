import re

from dataclasses import dataclass
from typing import Any

from spacy import Language
from spacy.matcher import Matcher
from spacy.tokens import Doc, Span

from library_analyzer.utils import load_language



_enum_valid_values_are = [{"LOWER": {"IN": ["valid", "possible", "accepted"]}}, {"LOWER": "values"}, {"LOWER": "are"}]

_enum_when_set_to = [{"LOWER": "when"}, {"LOWER": "set"}, {"LOWER": "to"}]

_enum_if_listing = [
    {"ORTH": "If"},
    {"ORTH": {"IN": ["'", '"', "`"]}, "OP": "?"},
    {},
    {"ORTH": {"IN": ["'", '"', "`"]}, "OP": "?"},
    {"ORTH": {"IN": [",", ":"]}, "OP": "?"}
]

_enum_type_curly = [{"ORTH": "{"}, {"OP": "+"}, {"ORTH": "}"}]

_enum_str = [{"LOWER": "str"}]
_enum_bool = [{"LOWER": {"IN": ["bool", "false", "true"]}}]

_enum_single_val_bool_none = [{"ORTH": {"IN": ["True", "False", "None"]}}, {"ORTH": ":", "OP": "?"}]

_enum_single_val_quoted = [{"ORTH": {"IN": ["'", '"']}}, {"OP": "+"}, {"ORTH": {"IN": ["'", '"']}}, {"ORTH": ":"}]

_enum_type_single_val = [
    {"ORTH": {"IN": ["'", "`", '"']}},
    {},
    {"ORTH": {"IN": ["'", "`", '"']}}
]



@dataclass
class MatcherConfiguration:
    _nlp: Language = None
    _matcher: Matcher = None

    # Rules to be checked
    single_val_type_string: bool = True
    when_set_to: bool = True
    valid_values_are: bool = True
    type_curly: bool = True
    if_listings: bool = True
    single_vals: bool = True

    def __post_init__(self) -> None:
        self._nlp = load_language("en_core_web_sm")
        self._matcher = Matcher(self._nlp.vocab)

        self._matcher.add("ENUM_STR", [_enum_str])
        self._matcher.add("ENUM_BOOL", [_enum_bool])

        if self.single_val_type_string:
            self._matcher.add("ENUM_TYPE_SINGLE_VAL", [_enum_type_single_val], greedy="LONGEST")
        if self.when_set_to:
            self._matcher.add("ENUM_SINGLE_VAL_WHEN", [_enum_when_set_to], on_match=_extract_single_value)
        if self.if_listings:
            self._matcher.add(
                "ENUM_SINGLE_VAL_IF",
                [_enum_if_listing],
                on_match=_extract_single_value,
                greedy="FIRST"
            )
        if self.valid_values_are:
            self._matcher.add("ENUM_VALID_VALUES_ARE", [_enum_valid_values_are], on_match=_extract_list)
        if self.type_curly:
            self._matcher.add("ENUM_TYPE_CURLY", [_enum_type_curly], on_match=_extract_list)
        if self.single_vals:
            self._matcher.add(
                "ENUM_SINGLE_VALS",
                [_enum_single_val_quoted, _enum_single_val_bool_none],
                on_match=_extract_indented_single_value,
                greedy="LONGEST"
            )

    def get_matcher(self) -> Matcher:
        return self._matcher

    def get_nlp(self) -> Language:
        return self._nlp


_extracted = []


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
    i: int,  # noqa: ARG001
    nlp_matches: list[tuple[Any, ...]],  # noqa: ARG001
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

    for token in doc[end:]:
        print(token.text)
        if token.text in ["[", "{"]:
            found_list = True
            continue
        elif token.text in ["]", "}"]:
            break

        if found_list and token.text not in seperators_opener and token.text not in quotes:
            if token.text in ["True", "False", "bool"]:
                ex.append("True")
                ex.append("False")
            else:

                if token.nbor(-1).text in quotes and token.nbor(-2).text not in seperators_opener:
                    _merge_with_last_value_in_list(ex, token.text)
                elif token.nbor(-1).text not in seperators_opener and token.nbor(-1).text not in quotes:
                    _merge_with_last_value_in_list(ex, token.text)
                else:
                    ex.append(token.text)
        else:

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
    _, start, end = nlp_matches[i]

    match_label = MATCHER_CONFIG.get_nlp().vocab.strings[nlp_matches[i][0]]
    if match_label == "ENUM_SINGLE_VAL_IF":
        next_token_idx = start + 1
        end = next_token_idx
        next_token = doc[next_token_idx]
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

    if value[0] in ["'", '"']:
        value = value.replace("'", '"')

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
    matcher = MATCHER_CONFIG.get_matcher()
    type_match_labels = []

    none_and_bool = {"False", "None", "True"}

    description = _preprocess_docstring(description)
    desc_doc = nlp.make_doc(" ".join(description.split()))

    type_string = _preprocess_docstring(type_string, True)
    type_doc = nlp.make_doc(type_string)

    matches = matcher(desc_doc)
    print([nlp.vocab.strings[m[0]] for m in matches])

    type_matches = matcher(type_doc)
    type_matches = _nlp_matches_to_readable_matches(type_matches, nlp, type_doc)

    if type_matches:
        type_match_labels = [match_label for match_label, _ in type_matches]

        for match_label, match_span in type_matches:
            if match_label == "ENUM_TYPE_SINGLE_VAL":
                if "ENUM_SINGLE_VALS" not in type_match_labels and "ENUM_TYPE_CURLY" not in type_match_labels:
                    substituted_string = re.sub(r"['`]+", '"', match_span.text)
                    _extracted.append(substituted_string)

    print(type_match_labels)

    for val in _extracted:
        if val in ["True", "False"] and "ENUM_BOOL" not in type_match_labels:
            _extracted.remove(val)

    extracted_set = set(_extracted)

    is_enum_str = False
    for label, match_span in type_matches:
        if label == "ENUM_STR" and len(type_doc) > 1 and match_span[0].nbor(-1).text != "of":
            is_enum_str = True

    if is_enum_str and not extracted_set.difference(none_and_bool):
        extracted_set.add("unlistable_str")

    return extracted_set


MATCHER_CONFIG = MatcherConfiguration()

if __name__ == '__main__':

    # descr = "The default error message is, \"This %(name)s instance is not fitted\nyet. Call 'fit' with appropriate arguments before using this\nestimator.\"\n\nFor custom messages if \"%(name)s\" is present in the message string,\nit is substituted for the estimator name.\n\nEg. : \"Estimator, %(name)s, must be fitted before sparsifying\"."
    # descr = "Learning rate schedule for weight updates.\n\n- 'constant' is a constant learning rate given by\n  'learning_rate_init'.\n\n- 'invscaling' gradually decreases the learning rate at each\n  time step 't' using an inverse scaling exponent of 'power_t'.\n  effective_learning_rate = learning_rate_init / pow(t, power_t)\n\n- 'adaptive' keeps the learning rate constant to\n  'learning_rate_init' as long as training loss keeps decreasing.\n  Each time two consecutive epochs fail to decrease training loss by at\n  least tol, or fail to increase validation score by at least tol if\n  'early_stopping' is on, the current learning rate is divided by 5.\n\nOnly used when ``solver='sgd'``."
    # type_ = "{'constant', 'invscaling', 'adaptive'}"

    descr = "If bool, bla bla la."
    type_ = "bool"

    # print(descr)
    s = extract_valid_literals(descr, type_)
    print(s)
