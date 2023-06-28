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


_condition_list: list[Condition] = []
_action_list: list[Action] = []
_combined_condition: list[str] = []
_nlp = load_language("en_core_web_sm")
_matcher = Matcher(_nlp.vocab)
_dep_matcher = DependencyMatcher(_nlp.vocab)

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


@Language.component("merger")
def _merger(doc: Doc) -> Doc:
    matched_spans = []
    matches = _matcher(doc)

    for match_id, start, end in matches:
        match_id_str = _nlp.vocab.strings[match_id]
        matched_spans.append((match_id_str, doc[start:end]))

    with doc.retokenize() as retokenizer:
        # matched_spans = filter_spans(matched_spans)
        for match_id_str, span_ in matched_spans:
            if match_id_str == "AUXPASS":
                attrs = {"POS": "AUX"}
            else:
                attrs = {}

            retokenizer.merge(span_, attrs)

    return doc



def _check_passiveness(action_token: Token, match: tuple[Any, ...]) -> bool:
    for child in action_token.children:
        if child.dep_ == "auxpass":
            match[1].append(child.i)
            return True
    return False

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

def _shorten_and_check_string(dependee: str, action_token) -> None:
    sconj_idx = 0
    and_or_idx = 0
    doc = action_token.doc
    change = False
    for descendant in action_token.subtree:
        if descendant.pos_ == "SCONJ":
            sconj_idx = descendant.i + 1

        elif descendant.text in ["and", "or", "with"]:
            change = True
            if descendant.text == "and":
                _combined_condition.append(dependee)

            and_or_idx = descendant.i + 1
            first_dep_val = doc[and_or_idx - 2]
            print(first_dep_val.text)
            for child in first_dep_val.children:
                # if child.dep_ == "conj" and child.nbor(-1).text in ["and", "or"] and child.nbor(1).pos_ not in ["AUX", "VERB"]:
                if child.nbor(-1).text in ["and", "or"] and child.nbor(1).pos_ not in ["AUX", "VERB"]:
                    sconj_idx += 2

    if change:
        shortened_string = doc[:sconj_idx].text + " " + doc[and_or_idx:].text
        shortened_doc = _nlp(shortened_string)
        _dep_matcher(shortened_doc)



def _check_shortened_string(doc: Doc, cond_start_str: str, dependee: str,  end: int, passive: bool = False) -> bool:

    if passive:
        pass
    elif (end < len(doc)) and (doc[end].text in ["or", ",", "and", "with"]):
        if doc[end].text in ["and", "with"]:
            _combined_condition.append(dependee)

        string_shortened = cond_start_str + " " + doc[end + 1:].text

        if doc[end].text == "or":
            first_dep_value = doc[end - 1]
            for child in first_dep_value.children:
                if child.dep_ == "conj" and child.nbor(1).pos_ not in ["AUX", "VERB"]:
                    print(f"child: {child.text}, nbor(1): {child.nbor(1).text}, nbor.pos_: {child.nbor(1).pos_}")
                    string_shortened = doc[:end-1].text + " " + doc[child.i:].text

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
    action_token = doc[match[1][3]]
    condition_string = doc[start:end].text

    dependee, value = _extract_dependee_value(action_token)

    if len(value.split(" ")) == 2:
        condition_string += " " + doc[end].text

    _add_condition(dependee, value, condition_string)
    _action_list.append(ParameterIsIgnored("not ignored"))

    cond_start_str = doc[match[1][1]:match[1][2] + 1].text

    # _check_shortened_string(doc, cond_start_str, dependee, end)
    _shorten_and_check_string(dependee, action_token)
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
    action_token = doc[match[1][2]]

    dependee, value = _extract_dependee_value(action_token, passive=True)

    condition_string = doc[start:end].text

    _add_condition(dependee, value, condition_string, passive=True)
    _action_list.append(ParameterIsIgnored("not ignored"))

    # cond_start_str = doc[match[1][1]:match[1][0] + 1].text
    # _check_shortened_string(doc, cond_start_str, dependee, end)
    _shorten_and_check_string(dependee, action_token)

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

    action_token = doc[match[1][1]]

    passive = _check_passiveness(action_token, match)

    dependee, value = _extract_dependee_value(action_token, passive)
    # if passive:
    #     dependee, value = _extract_dependee_value(action_token, passive=True)
    # else:
    #     dependee, value = _extract_dependee_value(action_token)

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

    passive = _check_passiveness(action_token, match)

    if passive:
        _extract_only_passive_condition_action(matcher, doc, i, matches)
    else:
        condition_string = doc[start:end].text
        dependee, value = _extract_dependee_value(action_token)

        _add_condition(dependee, value, condition_string)
        _action_list.append(ParameterIsIgnored("not ignored"))

    return None


def _extract_used_condition_action(
    matcher: DependencyMatcher,  # noqa: ARG001
    doc: Doc,
    i: int,
    matches: list[tuple[Any, ...]],
) -> Any | None:

    match = matches[i]
    start = min(match[1])
    end = max(match[1]) + 2
    action_token = doc[match[1][1]]

    passive = _check_passiveness(action_token, match)

    dependee, value = _extract_dependee_value(action_token, passive)

    condition_string = doc[start:end].text

    _add_condition(dependee, value, condition_string, passive)
    _action_list.append(ParameterIsIgnored("not ignored"))

    # cond_start_str = doc[match[1][0]:match[1][2] + 1].text
    # _check_shortened_string(doc, cond_start_str, dependee, end)
    _shorten_and_check_string(dependee, action_token)
    return None

def extract_param_dependencies(
    param_qname: str,
    description: str,
    serve_sent=False,
    show_matches=False
) -> list[tuple[str, Condition, Action]]:

    _condition_list.clear()
    _action_list.clear()
    _combined_condition.clear()

    dependency_tuples: list[tuple[str, Condition, Action]] = []

    description_preprocessed = _preprocess_docstring(description)
    print(description_preprocessed)
    description_doc = _nlp(description_preprocessed)

    if serve_sent:
        serve(description_doc, auto_select_port=True)

    matches = _dep_matcher(description_doc)

    if show_matches:
        for match in matches:
            print(_nlp.vocab.strings[match[0]])
            arr = [(description_doc[idx].text, idx) for idx in match[1]]
            print("Tokens: ", arr)
    for idx, cond in enumerate(_condition_list):
        dependency_tuples.append((param_qname, cond, _action_list[idx]))

    return dependency_tuples


_conditional_only = {
    "LEFT_ID": "condition_head",
    "REL_OP": ">",
    "RIGHT_ID": "conditional_only",
    # "RIGHT_ATTRS": {"LOWER": {"IN": ["only", "used"]}}
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
        # "RIGHT_ATTRS": {"ORTH": "Only"}
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
        "RIGHT_ATTRS": {"POS": {"IN": ["VERB", "AUX"]}, "DEP": {"NOT_IN": ["auxpass"]}}
    },
    {
        "LEFT_ID": "condition_head",
        "REL_OP": ">",
        "RIGHT_ID": "condition_start",
        "RIGHT_ATTRS": {"DEP": {"IN": ["advmod", "mark"]}, "POS": "SCONJ"}
    }
]

_dep_cond_used = [
    # {"RIGHT_ID": "conditional_used", "RIGHT_ATTRS": {"LOWER": "used"}},
    {"RIGHT_ID": "conditional_used", "RIGHT_ATTRS": {"ORTH": "Used"}},
    {
        "LEFT_ID": "conditional_used",
        "REL_OP": ">",
        "RIGHT_ID": "action_head",
        "RIGHT_ATTRS": {"POS": {"IN": ["AUX", "VERB"]}, "DEP": {"IN": ["advcl", "ccomp"]}}
    },
    {
        "LEFT_ID": "action_head",
        "REL_OP": ">",
        "RIGHT_ID": "condition_start",
        "RIGHT_ATTRS": {"POS": "SCONJ", "DEP": {"IN": ["advmod", "mark"]}}
    }
]


_pattern_hyphened_values = [{"IS_ASCII": True}, {"ORTH": "-"}, {"IS_ASCII": True}]
_pattern_hyphened_values2 = [{"IS_ASCII": True}, {"ORTH": "-"}, {"IS_ASCII": True}, {"ORTH": "-"}, {"IS_ASCII": True}]
_pattern_will_be = [{"LOWER": "will"}, {"LOWER": "be"}]


_matcher.add("HYPHENED_VALUE", [_pattern_hyphened_values, _pattern_hyphened_values2], greedy="LONGEST")
_matcher.add("AUXPASS", [_pattern_will_be])

# Insert hyphen-merger after Tokenizer into the pipeline
_nlp.add_pipe("merger", after="tagger")


_dep_matcher.add("DEPENDENCY_IMPLICIT_IGNORED_ONLY", [_dep_cond_only_verb, _dep_cond_only_adj],
                 on_match=_extract_only_condition_action)
_dep_matcher.add("DEPENDENCY_IMPLICIT_IGNORED_PURE_ONLY", [_dep_cond_only], on_match=_extract_pure_only_condition_action)

_dep_matcher.add("DEPENDENCY_IMPLICIT_IGNORED_USED", [_dep_cond_used], on_match=_extract_used_condition_action)

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

    example6 = "When solver equals adam, this will be ignored."
    example7 = "This parameter is ignored when fit_intercept is False."
    example8 = "Will be ignored when solver is set to adam."



    example9 = "This parameter is ignored when the solver is set to 'liblinear' regardless of whether 'multi_class' is specified or not."
    example10 = "This parameter will be ignored if the solver adam will be used."

    example11 = "When solver equals adam-correct, this will be ignored."

    example12 = "Used when penalty is adam."
    example13 = "Used for shuffling the data, when shuffle is set to True."
    example14 = "Used for shuffling the data, when shuffle equals True."
    example15 = "Used when solver == 'sag' or 'saga' to shuffle the data."
    example16 = "Used when the 'randomized' or 'arpack' solvers are used."


    fail1 = "Useful only when the solver 'liblinear' is used and self.fit_intercept is set to True."


    # deps = extract_param_dependencies("appendix", description=example12, serve_sent=False, show_matches=False)
    deps = extract_param_dependencies("appendix", description=fail1, serve_sent=False, show_matches=False)



    for name, condition, action in deps:
        print(f"\n::::: {name} :::::\n"
              f"Condition :: {condition.condition}, dependee: {condition.dependee}, value: {condition.value}, type: {type(condition)}, combines: {condition.combined_with}, check: {condition.check_dependee}\n"
              f"Action :: {action.action}, type: {type(action)}")
