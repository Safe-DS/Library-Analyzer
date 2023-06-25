from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from spacy import Language
from spacy.displacy import serve
from spacy.matcher import DependencyMatcher, Matcher

from library_analyzer.utils import load_language

if TYPE_CHECKING:
    from spacy.tokens import Doc, Token


@dataclass
class Condition:
    condition: str = ""
    dependee: str = ""
    value: str = ""
    combined_with: str = ""
    check_dependee: bool = False

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Condition:
        return cls(d["condition"], d["dependee"], d["value"])

    def to_dict(self) -> dict[str, Any]:
        return {"condition": self.condition,
                "dependee": self.dependee,
                "value": self.value}


class ParameterHasValue(Condition):
    def __init__(
        self, cond: str, dependee: str, value: str, combined_with: str = "", check_dependee: bool = False
    ) -> None:
        super().__init__(cond, dependee, value, combined_with, check_dependee)


class ParameterIsNone(Condition):
    def __init__(self, cond: str, dependee: str) -> None:
        super().__init__(cond, dependee, "None")


class ParameterIsNotCallable(Condition):
    def __init__(self, cond, dependee):
        super().__init__(cond, dependee, "not callable")


@dataclass
class Action:  # maybe Consequence?
    action: str

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Action:
        return cls(d["action"])

    def to_dict(self) -> dict[str, Any]:
        return {"action": self.action}


class ParameterIsIgnored(Action):
    def __init__(self, action_: str) -> None:
        super().__init__(action_)


class ParameterIsIllegal(Action):
    def __init__(self, action_: str) -> None:
        super().__init__(action_)


@Language.component("hyphen_merger")
def _hyphen_merger(doc: Doc) -> Doc:
    matched_spans = []
    matches = _matcher(doc)

    for _, start, end in matches:
        matched_spans.append(doc[start:end])
    with doc.retokenize() as retokenizer:
        # matched_spans = filter_spans(matched_spans)
        for span_ in matched_spans:
            retokenizer.merge(span_)

    return doc


def _preprocess_docstring(docstring: str) -> str:
    """
    Preprocess docstring to make it easier to parse.

    1. Remove cluttered punctuation around parameter references
    2. Set '=', ==' to 'equals' and set '!=' to 'does not equal'
    3. Handle cases of step two where the signs are not separate tokens, e.g. "a=b".
    Note ordered dict since "=" is a substring of the other symbols.
    """
    docstring = re.sub(r'["“”`]', "", docstring)
    docstring = re.sub(r"'", "", docstring)
    docstring = re.sub(r"!=", " does not equal ", docstring)
    docstring = re.sub(r"==?", " equals ", docstring)
    docstring = re.sub(r"\s+", " ", docstring)

    docstring = re.sub(r"none", "None", docstring)
    docstring = re.sub(r"is set to", "is", docstring)
    return docstring


def _check_shortened_string(doc: Doc, cond_start_str: str, dependee: str,  end: int) -> bool:

    if (end < len(doc)) and (doc[end].text in ["or", ",", "and", "with"]):
        if doc[end].text in ["and", "with"]:
            _combined_condition.append(dependee)

        string_shortened = cond_start_str + " " + doc[end + 1:].text
        doc_shortened = _nlp(string_shortened)

        _dep_matcher(doc_shortened)

        return True
    return False


def _extract_dependee_value(action_token: Token, passive: bool = False) -> tuple[str, str]:
    # print(action_token.doc.text)
    # arr = [(token.text, token.i) for token in action_token.doc]
    # print(arr)
    # print("ACTION: ", action_token.i)
    if passive:
        dependee = action_token.nbor(-3).text
        value = action_token.nbor(-2).text

    else:
        dependee = action_token.nbor(-1).text
        value_token = action_token.nbor(1)
        value = value_token.text

        if value_token.pos_ in ["DET", "PART"]:
            value += " " + action_token.nbor(2).text

    return dependee, value


def _add_condition(dependee: str, value: str, cond_str: str, passive: bool = False) -> None:

    if value == "None" or dependee == "None":
        dependee_ = dependee if dependee != "None" else value
        cond = ParameterIsNone(cond_str, dependee_)
    elif value == "not callable":
        cond = ParameterIsNotCallable(cond_str, dependee)
    else:
        cond = ParameterHasValue(cond_str, dependee, value)

    if passive:
        cond.check_dependee = True

    if _combined_condition:
        _condition_list[-1].combined_with = dependee
        cond.combined_with = _condition_list[-1].dependee

    _condition_list.append(cond)


def _extract_only_condition_action(
    matcher: DependencyMatcher,  # noqa: ARG001
    doc: Doc,
    i: int,
    matches: list[tuple[Any, ...]],
) -> Any | None:

    match = matches[i]
    start = min(match[1])
    end = max(match[1]) + 2

    condition_string = doc[start:end].text

    dependee, value = _extract_dependee_value(action_token=doc[match[1][3]])

    if len(value.split(" ")) == 2:
        condition_string += " " + doc[end].text

    _add_condition(dependee, value, condition_string)
    _action_list.append(ParameterIsIgnored("not ignored"))

    cond_start_str = doc[match[1][1]:match[1][2] + 1].text

    _check_shortened_string(doc, cond_start_str, dependee, end)
    # if (end < len(doc)) and (doc[end].text in ["or", ",", "and", "with"]):
    #     if doc[end].text in ["and", "with"]:
    #         _combined_condition.append(dependee)

    return None


def _extract_only_passive_condition_action(
    matcher: DependencyMatcher,  # noqa: ARG001
    doc: Doc,
    i: int,
    matches: list[tuple[Any, ...]],
) -> Any | None:

    match = matches[i]
    start = min(match[1])
    end = max(match[1]) + 1

    dependee, value = _extract_dependee_value(action_token=doc[match[1][2]], passive=True)

    condition_string = doc[start:end].text

    _add_condition(dependee, value, condition_string, passive=True)
    _action_list.append(ParameterIsIgnored("not ignored"))

    cond_start_str = doc[match[1][1]:match[1][0] + 1].text
    _check_shortened_string(doc, cond_start_str, dependee, end)

    return None


def _extract_ignored_condition_action(
    matcher: DependencyMatcher,  # noqa: ARG001
    doc: Doc,
    i: int,
    matches: list[tuple[Any, ...]],
) -> Any | None:

    match = matches[i]
    start = min(match[1])
    end = max(match[1]) + 2

    dependee, value = _extract_dependee_value(action_token=doc[match[1][1]])
    condition_string = doc[start:end].text

    _add_condition(dependee, value, condition_string)
    _action_list.append(ParameterIsIgnored("ignored"))

    return None


def _extract_pure_only_condition_action(
    matcher: DependencyMatcher,  # noqa: ARG001
    doc: Doc,
    i: int,
    matches: list[tuple[Any, ...]],
) -> Any | None:

    match = matches[i]
    action_token = doc[match[1][2]]
    start = min(match[1])
    end = max(match[1]) + 2
    passive = False

    for child in action_token.children:
        if child.dep_ == "auxpass":
            matches[i][1].append(child.i)
            passive = True
            break

    if passive:
        _extract_only_passive_condition_action(matcher, doc, i, matches)
    else:
        condition_string = doc[start:end].text
        dependee, value = _extract_dependee_value(action_token)

        _add_condition(dependee, value, condition_string)
        _action_list.append(ParameterIsIgnored("not ignored"))

    return None


def extract_param_dependencies(
    param_qname: str = "",
    description: str = "",
    serve_sent=False,
    show_matches=False
) -> list[tuple[str, Condition, Action]]:
    print(description)
    _condition_list.clear()
    _action_list.clear()
    dependency_tuples: list[tuple[str, Condition, Action]] = []

    description_preprocessed = _preprocess_docstring(description)
    description_doc = _nlp(description_preprocessed)

    if serve_sent:
        serve(description_doc, auto_select_port=True)

    matches = _dep_matcher(description_doc)

    if show_matches:
        for match in matches:
            print(_nlp.vocab.strings[match[0]])
            arr = [(description_doc[idx].text, idx) for idx in match[1]]
            print(arr)

    for idx, cond in enumerate(_condition_list):
        dependency_tuples.append((param_qname, cond, _action_list[idx]))

    return dependency_tuples


_conditional_only = {
    "LEFT_ID": "condition_head",
    "REL_OP": ">",
    "RIGHT_ID": "conditional_only",
    "RIGHT_ATTRS": {"LOWER": "only"}
}

_dep_cond_only_verb = [
    {"RIGHT_ID": "condition_head", "RIGHT_ATTRS": {"POS": "VERB"}},
    _conditional_only,
    {
        "LEFT_ID": "condition_head",
        "REL_OP": ".",
        "RIGHT_ID": "action_start",
        "RIGHT_ATTRS": {"POS": "SCONJ"}
     },
    {
        "LEFT_ID": "action_start",
        "REL_OP": "<",
        "RIGHT_ID": "action",
        "RIGHT_ATTRS": {"POS": {"IN": ["AUX", "VERB"]}}

    }
]

_dep_cond_only_adj = [
    {"RIGHT_ID": "condition_head", "RIGHT_ATTRS": {"POS": "ADJ"}},
    _conditional_only,
    {
        "LEFT_ID": "condition_head",
        "REL_OP": ".",
        "RIGHT_ID": "action_start",
        "RIGHT_ATTRS": {"POS": "SCONJ"}
     },
    {
        "LEFT_ID": "action_start",
        "REL_OP": "<",
        "RIGHT_ID": "action",
        "RIGHT_ATTRS": {"POS": {"IN": ["AUX", "VERB"]}}

    }
]

_dep_cond_only = [
    {"RIGHT_ID": "condition_head", "RIGHT_ATTRS": {"POS": "SCONJ", "DEP": {"IN": ["mark", "advmod"]}}},
    {
        "LEFT_ID": "condition_head",
        "REL_OP": ";",
        "RIGHT_ID": "conditional_only",
        "RIGHT_ATTRS": {"LOWER": "only"}
    },
    {
        "LEFT_ID": "condition_head",
        "REL_OP": "<",
        "RIGHT_ID": "action_head",
        "RIGHT_ATTRS": {"POS": {"IN": ["VERB", "AUX"]}}
    }
]

_dep_cond_ignored = [
    {"RIGHT_ID": "action_head", "RIGHT_ATTRS": {"LOWER": "ignored"}},
    {
        "LEFT_ID": "action_head",
        "REL_OP": ">",
        "RIGHT_ID": "condition_head",
        "RIGHT_ATTRS": {"POS": {"IN": ["VERB", "AUX"]}}
    },
    {
        "LEFT_ID": "condition_head",
        "REL_OP": ">>",
        "RIGHT_ID": "condition_start",
        "RIGHT_ATTRS": {"DEP": {"IN": ["advmod", "mark"]}, "POS": "SCONJ"}
    }
]


_pattern_hyphened_values = [{"IS_ASCII": True}, {"ORTH": "-"}, {"IS_ASCII": True}]
_pattern_hyphened_values2 = [{"IS_ASCII": True}, {"ORTH": "-"}, {"IS_ASCII": True}, {"ORTH": "-"}, {"IS_ASCII": True}]


_condition_list: list[Condition] = []
_action_list: list[Action] = []
_combined_condition: list[str] = []

_nlp = load_language("en_core_web_sm")

_matcher = Matcher(_nlp.vocab)
_matcher.add("HYPHENED_VALUE", [_pattern_hyphened_values, _pattern_hyphened_values2], greedy="LONGEST")

# Insert hyphen-merger after Tokenizer into the pipeline
_nlp.add_pipe("hyphen_merger", first=True)

_dep_matcher = DependencyMatcher(_nlp.vocab)
_dep_matcher.add("DEPENDENCY_COND_ONLY", [_dep_cond_only_verb, _dep_cond_only_adj],
                 on_match=_extract_only_condition_action)
_dep_matcher.add("DEPENDENCY_COND_ONLY2", [_dep_cond_only], on_match=_extract_pure_only_condition_action)

_dep_matcher.add("DEPENDENCY_COND_IGNORED", [_dep_cond_ignored], on_match=_extract_ignored_condition_action)


if __name__ == "__main__":

    text = "Only applies if analyzer is not callable. Only available if penalty is None. " \
           "Only available if analyzer=='bier' or wither=='wein'"  # noqa: ISC002

    text2 = "Only available if penalty equals Nice or pentTest equals bad"

    text4 = "This parameter is ignored when the solver is set to 'liblinear' regardless of whether 'multi_class' is specified or not. "

    example = "Useful only when the solver 'liblinear' is used and self.fit_intercept is set to True."
    example2 = "Only used if n_iter_no_change is set to an integer."
    example3 = "Useful only when the solver 'liblinear' is used and self.fit_intercept is set to True."
    example4 = "Only used if solver='liblinear' and penalty is set to 'random'."
    example5 = "Only when self.fit_intercept is True."

    example6 = "When solver is adam, this will be ignored."
    example7 = "This parameter is ignored when fit_intercept is False."
    example8 = "Will be ignored when solver is set to adam."

    example9 = "Used independently when solver is set to adam."

    deps = extract_param_dependencies("appendix", description=example9, serve_sent=False, show_matches=True)

    for name, condition, action in deps:
        print(f"\n::::: {name} :::::\n"
              f"Condition :: {condition.condition}, dependee: {condition.dependee}, value: {condition.value}, type: {type(condition)}, combines: {condition.combined_with}\n"
              f"Action :: {action.action}, type: {type(action)}")
