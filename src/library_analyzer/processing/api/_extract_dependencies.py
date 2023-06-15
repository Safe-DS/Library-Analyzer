from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import spacy
from spacy import Language
from spacy.displacy import serve
from spacy.matcher import DependencyMatcher, Matcher

if TYPE_CHECKING:
    from spacy.tokens import Doc


@dataclass
class Condition:
    condition: str = ""
    dependee: str = ""
    value: str = ""

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Condition:
        return cls(d["condition"], d["dependee"], d["value"])

    def to_dict(self) -> dict[str, Any]:
        return {"condition": self.condition,
                "dependee": self.dependee,
                "value": self.value}


class ParameterHasValue(Condition):
    def __init__(self, condition: str, dependee: str, value: str) -> None:
        super().__init__(condition, dependee, value)


class ParameterIsNone(Condition):
    def __init__(self, condition: str, dependee: str) -> None:
        super().__init__(condition, dependee, "None")


class ParameterIsNotCallable(Condition):
    def __init__(self, condition, dependee):
        super().__init__(condition, dependee, "not callable")


@dataclass
class Action:  # maybe Consequence?
    action: str

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Action:
        return cls(d["action"])

    def to_dict(self) -> dict[str, Any]:
        return {"action": self.action}


class ParameterIsIgnored(Action):
    def __init__(self, action: str) -> None:
        super().__init__(action)


class ParameterIsIllegal(Action):
    def __init__(self, action: str) -> None:
        super().__init__(action)


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


def _extract_only_condition_and_action(
    matcher: DependencyMatcher,
    doc: Doc,
    i: int,
    matches: list[tuple[Any, ...]],
) -> Any | None:

    match = matches[i]
    start = min(match[1])
    end = max(match[1]) + 2

    dependee = doc[match[1][3]].nbor(-1).text
    value = doc[match[1][3]].nbor(1).text
    condition_string = doc[start:end].text

    if value == "None":
        cond = ParameterIsNone(condition_string, dependee)
    elif value == "not":
        value += " " + doc[match[1][3]].nbor(2).text
        condition_string += " " + doc[end].text
        if value == "not callable":
            cond = ParameterIsNotCallable(condition_string, dependee)
        else:
            cond = ParameterHasValue(condition_string, dependee, value)
    else:
        cond = ParameterHasValue(condition_string, dependee, value)

    _condition_list.append(cond)
    _action_list.append(ParameterIsIgnored("not ignored"))

    if (end < len(doc)) and (doc[end].text in ["or", ","]):
        conditional_start_string = doc[match[1][1]:match[1][2] + 1].text
        string_shortened = conditional_start_string + " " + doc[end + 1:].text
        doc_shortened = _nlp(string_shortened)
        matcher(doc_shortened)
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

    dependee = doc[match[1][1]].nbor(-1).text
    value = doc[match[1][1]].nbor(1).text
    condition_string = doc[start:end].text

    if value == "None":
        cond = ParameterIsNone(condition_string, dependee)
    else:
        cond = ParameterHasValue(condition_string, dependee, value)

    _condition_list.append(cond)
    _action_list.append(ParameterIsIgnored("ignored"))

    return None


def extract_param_dependencies(
    param_qname: str = "",
    description: str = "",
    serve_sent=False,
    show_matches=False
) -> list[tuple[str, Condition, Action]]:
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

    for idx, condition in enumerate(_condition_list):
        dependency_tuples.append((param_qname, condition, _action_list[idx]))

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
        "REL_OP": ">",
        "RIGHT_ID": "condition_start",
        "RIGHT_ATTRS": {"DEP": {"IN": ["advmod", "mark"]}, "POS": "SCONJ"}
    }
]






_pattern_hyphened_values = [{"IS_ASCII": True}, {"ORTH": "-"}, {"IS_ASCII": True}]
_pattern_hyphened_values2 = [{"IS_ASCII": True}, {"ORTH": "-"}, {"IS_ASCII": True}, {"ORTH": "-"}, {"IS_ASCII": True}]


_condition_list: list[Condition] = []
_action_list: list[Action] = []

_nlp = spacy.load("en_core_web_sm")

_matcher = Matcher(_nlp.vocab)
_matcher.add("HYPHENED_VALUE", [_pattern_hyphened_values, _pattern_hyphened_values2], greedy="LONGEST")

# Insert hyphen-merger after Tokenizer into the pipeline
_nlp.add_pipe("hyphen_merger", first=True)

_dep_matcher = DependencyMatcher(_nlp.vocab)
_dep_matcher.add("DEPENDENCY_COND_ONLY_VERB", [_dep_cond_only_verb], on_match=_extract_only_condition_and_action)
_dep_matcher.add("DEPENDENCY_COND_ONLY_ADJ", [_dep_cond_only_adj], on_match=_extract_only_condition_and_action)
_dep_matcher.add("DEPENDENCY_COND_IGNORED", [_dep_cond_ignored], on_match=_extract_ignored_condition_action)


if __name__ == "__main__":

    text = "Only applies if analyzer is not callable. Only available if penalty is None. " \
           "Only available if analyzer=='bier' or wither=='wein'"  # noqa: ISC002

    text2 = "Only available if penalty equals Nice or pentTest equals bad"
    text3 = "This parameter is ignored when fit_intercept is False."
    text4 = "This parameter is ignored when the solver is set to 'liblinear' regardless of whether 'multi_class' is specified or not. "

    example = "Only available if bootstrap is True."
    ex = "int | list[str, int] | bool"

    deps = extract_param_dependencies("appendix", description=ex, serve_sent=True, show_matches=False)

    for name, condition, action in deps:
        print(f"\n::::: {name} :::::\n"
              f"Condition :: {condition.condition}, dependee: {condition.dependee}, value: {condition.value}, type: {type(condition)}\n"
              f"Action :: {action.action}, type: {type(action)}")

