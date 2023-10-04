from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, TypeAlias

from spacy import Language
from spacy.matcher import DependencyMatcher, Matcher

from library_analyzer.utils import load_language

if TYPE_CHECKING:
    from spacy.tokens import Doc, Token

_condition_list: list[Condition] = []
_action_list: list[Action] = []
_combined_condition: list[str] = []
_nlp = load_language("en_core_web_sm")
_merger_matcher = Matcher(_nlp.vocab)
_dep_matcher = DependencyMatcher(_nlp.vocab)

_none_phrases = ["None", "unspecified"]
_encoded_rel_ops = {"$GT$": ">", "$LT$": "<", "$GEQ$": ">=", "$LEQ$": "<="}

_has_value_phrases = ["equals", "is", "are", "used"]

_has_value_phrases_splitting = [
    "equals",
    "$gt$",
    "$lt$",
    "$geq$",
    "$leq$",
]

_passive_has_value_phrases = ["used"]

_special_values = ["none", "true", "false"]

_implicit_ignored_phrases = [
    "only used",
    "only supported",
    "only applies",
]

_types = [
    "bool",
    "boolean",
    "str",
    "string",
    "int",
    "integer",
    "float",
    "array-like",
]

@dataclass
class Condition:
    class Variant(str, Enum):
        CONDITION = "condition"
        IN_RELATION = "in_relation"
        HAS_VALUE = "has_value"
        NO_VALUE = "no_value"
        IS_NONE = "is_none"
        HAS_TYPE = "has_type"
        NO_TYPE = "no_type"

    condition: str = ""
    dependee: str = ""
    combined_with: list[Condition] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Condition:
        match d["variant"]:
            case Condition.Variant.CONDITION.value:
                return cls(
                    d["condition"],
                    d["dependee"],
                    [Condition.from_dict(cond_dict) for cond_dict in d["combined_with"]],
                )
            case Condition.Variant.IN_RELATION.value:
                return ParametersInRelation.from_dict(d)
            case Condition.Variant.HAS_VALUE.value:
                return ParameterHasValue.from_dict(d)
            case Condition.Variant.NO_VALUE.value:
                return ParameterHasNotValue.from_dict(d)
            case Condition.Variant.IS_NONE.value:
                return ParameterIsNone.from_dict(d)
            case Condition.Variant.HAS_TYPE.value:
                return ParameterHasType.from_dict(d)
            case Condition.Variant.NO_TYPE.value:
                return ParameterDoesNotHaveType.from_dict(d)
            case _:
                raise KeyError("unknown variant found")

    def to_dict(self) -> dict[str, Any]:
        return {
            "variant": Condition.Variant.CONDITION.value,
            "condition": self.condition,
            "dependee": self.dependee,
            "combined_with": [cond.to_dict() for cond in self.combined_with],
        }


class ParametersInRelation(Condition):
    def __init__(
        self,
        cond: str,
        left_dependee: str,
        right_dependee: str,
        rel_op: str,
        combined: list[_CONDTION_TYPE] | None = None
    ):
        combined_list = combined or []
        super().__init__(cond, combined_with=combined_list)
        self.left_dependee = left_dependee
        self.right_dependee = right_dependee
        self.rel_op = rel_op

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Condition:
        return cls(d["condition"], d["left_dependee"], d["right_dependee"], d["rel_op"])

    def to_dict(self) -> dict[str, Any]:
        return {
            "variant": Condition.Variant.IN_RELATION.value,
            "condition": self.condition,
            "combined_with": [cond.to_dict() for cond in self.combined_with],
            "left_dependee": self.left_dependee,
            "right_dependee": self.right_dependee,
            "rel_op": self.rel_op,
        }


class ParameterHasValue(Condition):
    def __init__(
        self,
        cond: str,
        dependee: str,
        value: str,
        combined_with: list[Condition] | None = None,
        check_dependee: bool = False,
        also: bool = False,
    ) -> None:
        combined_with_list = combined_with if combined_with is not None else []
        super().__init__(cond, dependee, combined_with_list)
        self.check_dependee: bool = check_dependee
        self.value: str = value
        self.also = also

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Condition:
        return cls(
            d["condition"],
            d["dependee"],
            d["value"],
            [Condition.from_dict(cond_dict) for cond_dict in d["combined_with"]],
            d["check_dependee"],
            d["also"],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "variant": Condition.Variant.HAS_VALUE.value,
            "condition": self.condition,
            "dependee": self.dependee,
            "value": self.value,
            "combined_with": [cond.to_dict() for cond in self.combined_with],
            "check_dependee": self.check_dependee,
            "also": self.also,
        }


class ParameterHasNotValue(Condition):
    def __init__(self, cond: str) -> None:
        super().__init__(cond)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Condition:
        return cls(d["condition"])

    def to_dict(self) -> dict[str, Any]:
        return {"variant": Condition.Variant.NO_VALUE.value, "condition": self.condition}


class ParameterIsNone(Condition):
    def __init__(self, cond: str, dependee: str, also: bool = False) -> None:
        super().__init__(cond, dependee)
        self.also = also

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Condition:
        return cls(d["condition"], d["dependee"], d["also"])

    def to_dict(self) -> dict[str, Any]:
        return {
            "variant": Condition.Variant.IS_NONE.value,
            "condition": self.condition,
            "dependee": self.dependee,
            "also": self.also,
        }


class ParameterDoesNotHaveType(Condition):
    def __init__(self, cond: str, dependee: str, type_: str) -> None:
        super().__init__(cond, dependee)
        self.type_: str = type_

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Condition:
        return cls(d["condition"], d["dependee"], d["type"])

    def to_dict(self) -> dict[str, Any]:
        return {
            "variant": Condition.Variant.NO_TYPE.value,
            "condition": self.condition,
            "dependee": self.dependee,
            "type": self.type_,
        }


class ParameterHasType(Condition):
    def __init__(self, cond: str, dependee: str, type_: str) -> None:
        super().__init__(cond, dependee)
        self.type_ = type_

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Condition:
        return cls(d["condition"], d["dependee"], d["type"])

    def to_dict(self) -> dict[str, Any]:
        return {
            "variant": Condition.Variant.HAS_TYPE.value,
            "condition": self.condition,
            "dependee": self.dependee,
            "type": self.type_,
        }


@dataclass
class Action:
    action: str = ""

    class Variant(Enum):
        ACTION = "action"
        IS_IGNORED = "is_ignored"
        IS_ILLEGAL = "is_illegal"
        WILL_BE_SET = "will_be_set"
        IS_RESTRICTED = "is_restricted"

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Action:
        match d["variant"]:
            case Action.Variant.ACTION.value:
                return cls(d["action"])
            case Action.Variant.IS_IGNORED.value:
                return ParameterIsIgnored.from_dict(d)
            case Action.Variant.IS_ILLEGAL.value:
                return ParameterIsIllegal.from_dict(d)
            case Action.Variant.WILL_BE_SET.value:
                return ParameterWillBeSetTo.from_dict(d)
            case Action.Variant.IS_RESTRICTED.value:
                return ParameterIsRestricted.from_dict(d)
            case _:
                raise KeyError("unknown variant found")

    def to_dict(self) -> dict[str, Any]:
        return {"variant": Action.Variant.ACTION.value, "action": self.action}


class ParameterIsIgnored(Action):
    def __init__(self, action_: str, dependee: str = "this_parameter") -> None:
        super().__init__(action_)
        self.dependee = dependee

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Action:
        return cls(d["action"], d["dependee"])

    def to_dict(self) -> dict[str, Any]:
        return {"variant": Action.Variant.IS_IGNORED.value, "action": self.action, "dependee": self.dependee}


class ParameterIsIllegal(Action):
    def __init__(self, action_: str) -> None:
        super().__init__(action_)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Action:
        return cls(d["action"])

    def to_dict(self) -> dict[str, Any]:
        return {"variant": Action.Variant.IS_ILLEGAL.value, "action": self.action}


class ParameterWillBeSetTo(Action):
    def __init__(self, action_: str, depender: str, value_: str) -> None:
        super().__init__(action_)
        self.depender = depender
        self.value_ = value_

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Action:
        return cls(d["action"], d["depender"], d["value"])

    def to_dict(self) -> dict[str, Any]:
        return {
            "variant": Action.Variant.WILL_BE_SET.value,
            "action": self.action,
            "depender": self.depender,
            "value": self.value_,
        }


class ParameterIsRestricted(Action):
    def __init__(self, action_: str) -> None:
        super().__init__(action_)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Action:
        return cls(d["action"])

    def to_dict(self) -> dict[str, Any]:
        return {"variant": Action.Variant.IS_RESTRICTED.value, "action": self.action}


@Language.component("merger")
def _merger(doc: Doc) -> Doc:
    """Pipeline component that combines certain occurring token patterns into a common token.

    Parameters
    ----------
    doc
        Doc object of the previous pipeline component

    Returns
    -------
    Doc
        Doc object for the next pipeline component.
        If 'merger' is the last pipeline component, the final Doc object is output.

    """
    matched_spans = []
    matches = _merger_matcher(doc)

    for match_id, start, end in matches:
        match_id_str = _nlp.vocab.strings[match_id]
        matched_spans.append((match_id_str, doc[start:end]))

    with doc.retokenize() as retokenizer:
        for match_id_str, span_ in matched_spans:
            if match_id_str == "AUXPASS":
                attrs = {"POS": "AUX"}
            elif match_id_str == "REL_OPS":
                attrs = {"POS": "SYM"}
            else:
                attrs = {}

            retokenizer.merge(span_, attrs)

    return doc


def _check_passiveness(action_token: Token, match: tuple[Any, ...]) -> bool:
    """Check if the action verb is used in passive form.

    Parameters
    ----------
    action_token
        Token of the action verb

    match
        Match object of the pattern found by the dependency matcher that contains the action verb.

    Returns
    -------
        bool
            True is returned if the verb is used in passive form.

    """
    for child in action_token.children:
        if child.dep_ == "auxpass":
            match[1].append(child.i)
            return True
    return False


def _preprocess_docstring(docstring: str) -> str:
    """
    Preprocess docstring to make it easier to parse.

    1. Remove cluttered punctuation around parameter references
    2. Encode relational operators.
    3. Set '=', ==' to 'equals' and set '!=' to 'does not equal'
    4. Handle cases of step two where the signs are not separate tokens, e.g. "a=b".
    5. Normalize specific substrings
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

    docstring = re.sub(r">=", "$GEQ$", docstring)
    docstring = re.sub(r"<=", "$LEQ$", docstring)
    docstring = re.sub(r"<", "$LT$", docstring)
    docstring = re.sub(r">", "$GT$", docstring)

    docstring = re.sub(r"is greater than or equal to", "$GEQ$", docstring)
    docstring = re.sub(r"is less than or equal to", "$LEQ$", docstring)
    docstring = re.sub(r"is greater than", "$GT$", docstring)
    docstring = re.sub(r"is less than", "$LT$", docstring)

    docstring = re.sub(r"!=", " does not equal ", docstring)
    docstring = re.sub(r"==?", " equals ", docstring)
    docstring = re.sub(r"\s+", " ", docstring)

    docstring = re.sub(r"not set", "None", docstring)
    docstring = re.sub(r"not specified", "None", docstring)

    docstring = re.sub(r"none", "None", docstring)

    return re.sub(r"is set to", "equals", docstring)


def _shorten_and_check_string(dependee: str, action_token_index: int, doc: Doc) -> None:
    """
    Check for multiple conditions in the Doc object, which are linked with an 'and' or 'or'.

    The first condition found is removed and the new truncated Doc object is passed back to the dependency matcher.

    Parameters
    ----------
    dependee
        First found dependee

    action_token_index
        Token index of the action token of the dependee found first

    doc
        Doc object to be checked for multiple conditions.

    """
    start_phrase: str = ""
    end_phrase: str = ""
    seperator_idxs = []
    has_value_idxs = []
    special_value_idxs = []
    type_idxs = []
    if_when_idx = -1
    left_bracket_idx = -1
    right_bracket_idx = -1

    for token in doc:
        token_text = token.text.lower()
        if token_text in ["if", "when"]:
            if_when_idx = token.i
        elif token_text in _has_value_phrases_splitting or (
            token_text in _passive_has_value_phrases and token.i > 0 and token.nbor(-1).text in ["is", "are"]
        ):
            has_value_idxs.append(token.i)
        elif token_text in _special_values and token.nbor(-1).text in ["is", "are", "not"]:
            special_value_idxs.append(token.i)
        elif token_text in ["and", "or", ","] and token.nbor(1).text not in ["and", "or"]:
            if token_text == "and" and left_bracket_idx == -1:
                _combined_condition.append(dependee)
            seperator_idxs.append(token.i)
        elif token_text in _types:
            type_idxs.append(token.i)
        elif token_text == "(":
            left_bracket_idx = token.i
        elif token_text == ")":
            right_bracket_idx = token.i

    value_idxs_cnt = len(has_value_idxs) + len(special_value_idxs)

    if seperator_idxs and left_bracket_idx != -1 and right_bracket_idx != -1:
        seperator_idxs = list(filter(lambda idx: left_bracket_idx < idx < right_bracket_idx, seperator_idxs))
        for idx in seperator_idxs:
            if doc[idx].text == "and":
                _combined_condition.append(dependee)
                break

    if seperator_idxs:
        # <start_phrase>...<param_with_val>, <param_with_val>, <and | or> <param_with_val> <end_phrase>
        if len(seperator_idxs) == value_idxs_cnt - 1:
            if has_value_idxs:
                seperator_idx = seperator_idxs[0]
                start_phrase = doc[: if_when_idx + 1].text
                end_phrase = doc[seperator_idx + 1 :].text

        # <start_phrase> ... <param>, <param>, <and | or> <param> <end_phrase_with_val>
        elif action_token_index > max(seperator_idxs):
            seperator_idx = seperator_idxs[-1]
            end_phrase = doc[seperator_idx + 2 :].text
            if doc[seperator_idx].text in ["and", "or"] and doc[seperator_idx - 1].text == ",":
                start_phrase = doc[: seperator_idx - 1].text
            else:
                start_phrase = doc[:seperator_idx].text

        # <start_phrase with param> ... <val>, <val>, <and | or> <val> <end_phrase>
        elif action_token_index < min(seperator_idxs):
            seperator_idx = seperator_idxs[0]
            end_phrase = doc[seperator_idx + 1 :].text
            start_phrase = doc[: action_token_index + 1].text

    shortened_sent = start_phrase + " " + end_phrase
    shortened_doc = _nlp(shortened_sent)

    _dep_matcher(shortened_doc)


def _extract_dependee_value(action_token: Token, passive: bool = False) -> tuple[str, str]:
    """Extract the dependee and its value using the passed action verb token.

    Parameters
    ----------
    action_token
        Action verb token.

    passive
        True if the action verb is in passive form.

    Returns
    -------
    tuple[str, str]
        Tuple containing the dependee and its value.

    """
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


def _add_condition(
    dependee: str,
    value: str,
    cond_str: str,
    passive: bool = False,
    also: bool = False,
    relational: bool = False,
    **kwargs: str
) -> None:
    """Add a condition to the global condition list.

    Parameters
    ----------
    dependee
        dependee of the condition

    value
        value of the dependee

    cond_str
        String of the condition to add

    passive
        True if the action verb is in passive form.

    also
        True if the dependee has the same value as the depender.

    """
    cond: Condition
    type_ = ""

    if value in _types:
        type_ = value
    elif len(value.split(" ")) == 2:
        type_ = value.split(" ")[1].lower()

    if value in _none_phrases or dependee in _none_phrases:
        dependee_ = dependee if dependee not in _none_phrases else value
        cond = ParameterIsNone(cond_str, dependee_)
        cond.also = also
    elif value == "not callable":
        cond = ParameterDoesNotHaveType(cond_str, dependee, value)
    elif type_ in _types:
        cond = ParameterHasType(cond_str, dependee, type_)
    elif relational:
        cond = ParametersInRelation(cond_str, kwargs["left"], kwargs["right"], kwargs["rel_op"])
    else:
        cond = ParameterHasValue(cond_str, dependee, value)
        cond.also = also
        cond.check_dependee = passive

    if _combined_condition:
        cond.combined_with.append(Condition.from_dict(_condition_list[-1].to_dict()))
        _condition_list.pop()
        _action_list.pop()

    _condition_list.append(cond)


def _extract_must_be_condition(
    matcher: DependencyMatcher,  # noqa: ARG001
    doc: Doc,
    i: int,
    matches: list[tuple[Any, ...]],
) -> Any | None:
    """on-match function for the spaCy DependencyMatcher.

    Extract the condition that contains the phrase 'must be'
    and add the corresponding action to the global actions list.

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
    restriction: Action
    match = matches[i]
    start = min(match[1])

    cond_token = doc[match[1][0]]
    action_token = doc[match[1][2]]

    end = cond_token.i + 2
    token_before_end = doc[end - 1]

    if token_before_end.text == "not" or token_before_end.pos_ == "DET":
        end += 1

    condition_string = doc[start:end].text
    action_string = doc[action_token.i : -1].text

    if (action_token.nbor(-1).is_punct or action_token.nbor(2).pos_ != "SCONJ") and action_token.nbor(
        1,
    ).text.lower() not in _special_values:
        dependee, dependee_value = _extract_dependee_value(cond_token)
        action_string = doc[action_token.i - 1 : -1].text
        restriction = ParameterIsRestricted(action_string)

    else:
        dependee, dependee_value = _extract_dependee_value(cond_token)
        depender, depender_value = _extract_dependee_value(action_token)
        if depender.lower() in ["it", "and"]:
            depender = "this_parameter"
        restriction = ParameterWillBeSetTo(action_string, depender, depender_value)

    _add_condition(dependee, dependee_value, condition_string)
    _action_list.append(restriction)

    return None


def _extract_only_condition_action(
    matcher: DependencyMatcher,  # noqa: ARG001
    doc: Doc,
    i: int,
    matches: list[tuple[Any, ...]],
) -> Any | None:
    """on-match function for the spaCy DependencyMatcher.

    Extract the condition that contains the phrase 'Only <VERB | ADJ> <if | when | ...>'
    and add the corresponding action to the global actions list.

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
    match = matches[i]
    start = min(match[1])
    end = max(match[1]) + 2
    action_token = doc[match[1][3]]
    condition_string = doc[start:end].text

    dependee, value = _extract_dependee_value(action_token)

    if len(value.split()) == 2:
        condition_string += " " + doc[end].text

    _add_condition(dependee, value, condition_string)

    _action_list.append(ParameterIsIgnored("not ignored"))

    _shorten_and_check_string(dependee, action_token.i, doc)

    return None


def _extract_only_passive_condition_action(
    doc: Doc,
    match: tuple[Any, ...],
) -> Any | None:
    """Extract the passive 'only <if | when | ...>' conditon.

    Extract the condition of a Doc object that start with the phrase "Only <if | when |. ..>"
    and contain the action verb in passive form.

    Parameters
    ----------
    doc
        Doc object that is checked for the active rules.

    match
        Dependency match that was found by the corresponding pattern from the dependency matcher.

    """
    start = min(match[1])
    end = max(match[1]) + 1
    action_token = doc[match[1][2]]

    dependee, value = _extract_dependee_value(action_token, passive=True)

    condition_string = doc[start:end].text

    _add_condition(dependee, value, condition_string, passive=True)
    _action_list.append(ParameterIsIgnored("not ignored"))

    _shorten_and_check_string(dependee, action_token.i, doc)

    return None


def _extract_ignored_condition_action(
    matcher: DependencyMatcher,  # noqa: ARG001
    doc: Doc,
    i: int,
    matches: list[tuple[Any, ...]],
) -> Any | None:
    """on-match function for the spaCy DependencyMatcher.

    Extract the condition that contains the phrase 'ignored'
    and add the corresponding action to the global actions list.

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
    ignored_parameter = "this_parameter"
    match = matches[i]
    start = min(match[1])
    ignored_idx = match[1][0]

    if ignored_idx > match[1][2]:
        end = ignored_idx + 1
    else:
        end = max(match[1]) + 2

    action_token = doc[match[1][1]]

    passive = _check_passiveness(action_token, match)

    dependee, value = _extract_dependee_value(action_token, passive)

    token_before_end = doc[end - 1]
    if token_before_end.text == "not" or token_before_end.pos_ == "DET":
        end += 1

    condition_string = doc[start:end].text

    if ignored_idx > 0:
        verb_before_ignored = doc[ignored_idx - 1].text

        if verb_before_ignored in ["is", "are", "will be"]:
            ignored_parameter = doc[ignored_idx - 2].text

        if ignored_parameter.lower() in ["this", "it", "parameter"]:
            ignored_parameter = "this_parameter"

    _add_condition(dependee, value, condition_string)
    _action_list.append(ParameterIsIgnored("ignored", ignored_parameter))

    return None


def _extract_pure_only_condition_action(
    matcher: DependencyMatcher,  # noqa: ARG001
    doc: Doc,
    i: int,
    matches: list[tuple[Any, ...]],
) -> Any | None:
    """on-match function for the spaCy DependencyMatcher.

    Extract the condition that contains the phrase 'Only <if | when | ...>'
    and add the corresponding action to the global actions list.

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
    match = matches[i]
    action_token = doc[match[1][2]]
    start = min(match[1])
    end = max(match[1]) + 2

    only_token = doc[match[1][1]]
    if only_token.i > 0 and only_token.nbor(-1).text == "Used":
        return None

    passive = _check_passiveness(action_token, match)

    if passive:
        _extract_only_passive_condition_action(doc, match)
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
    """on-match function for the spaCy DependencyMatcher.

    Extract the condition that contains the phrase 'Used <if | when | ...>'
    and add the corresponding action to the global actions list.

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
    match = matches[i]
    start = min(match[1])
    end = max(match[1]) + 2
    action_token = doc[match[1][1]]

    if _nlp.vocab.strings[match[0]] == "DEPENDENCY_COND_WHEN_BRACKETS" and len(matches) > 1:
        matches.pop(i)
        return None

    passive = _check_passiveness(action_token, match)

    dependee, value = _extract_dependee_value(action_token, passive)
    token_before_end = doc[end - 1]
    if token_before_end.text == "not" or token_before_end.pos_ == "DET":
        end += 1

    condition_string = doc[start:end].text
    _add_condition(dependee, value, condition_string, passive)
    _action_list.append(ParameterIsIgnored("not ignored"))

    _shorten_and_check_string(dependee, action_token.i, doc)

    return None


def _extract_relational_condition(
    matcher: DependencyMatcher,  # noqa: ARG001
    doc: Doc,
    i: int,
    matches: list[tuple[Any, ...]],
) -> Any | None:
    """on-match function for the spaCy DependencyMatcher.

    Extract the condition that contains the phrase '<dependee1> <rel_op> <dependee2>'
    and add the corresponding action to the global actions list.

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
    match_ = matches[i]
    relational_matches_cnt = 0
    for m in matches:
        if m[0] == match_[0]:
            relational_matches_cnt += 1

    if match_[1][0] != min(match_[1]) or relational_matches_cnt > 1:
        matches.pop(i)
        return None

    action_token = doc[match_[1][0]]
    cond_token = doc[match_[1][2]]
    left_dependee = cond_token.nbor(-1).text
    right_dependee = cond_token.nbor(1).text

    depender, value = _extract_dependee_value(action_token)

    rel_op = " " + _encoded_rel_ops[cond_token.text] + " "

    condition_string = doc[match_[1][1] : cond_token.i].text + rel_op + doc[cond_token.i + 1].text

    _add_condition(
        dependee="",
        value="",
        cond_str=condition_string,
        relational=True,
        left=left_dependee,
        right=right_dependee,
        rel_op=rel_op.strip()
    )

    action_string_doc = doc[: match_[1][1]]
    action_string = action_string_doc.text

    if action_string.lower() in _implicit_ignored_phrases:
        _action_list.append(ParameterIsIgnored("not ignored"))
    else:
        _action_list.append(ParameterWillBeSetTo(action_string, depender, value))

    return None


def _extract_raise_error(
    matcher: DependencyMatcher,  # noqa: ARG001
    doc: Doc,
    i: int,
    matches: list[tuple[Any, ...]],
) -> Any | None:
    """on-match function for the spaCy DependencyMatcher.

    Extract the condition that contains the phrase 'raises <ERROR>'
    and add the corresponding action to the global actions list.

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
    match_ = matches[i]
    match_id_string = _nlp.vocab.strings[match_[0]]

    if match_id_string == "DEPENDENCY_COND_RAISE_ERROR_START":
        action_string = doc[match_[1][1] : match_[1][0] + 1].text
        cond = Condition(doc.text)
    else:
        dependee, value_ = _extract_dependee_value(doc[match_[1][3]])
        action_string = doc[match_[1][1] : match_[1][0] + 1].text
        cond = ParameterHasValue(doc.text, dependee, value_)

    _condition_list.append(cond)
    _action_list.append(ParameterIsIllegal(action_string))

    return None


def _extract_cond_only_noun(
    matcher: DependencyMatcher,  # noqa: ARG001
    doc: Doc,
    i: int,
    matches: list[tuple[Any, ...]],
) -> Any | None:
    """on-match function for the spaCy DependencyMatcher.

    Extract the condition that contains the phrase 'Only <NOUN> [...] <passive verb>'
    and add the corresponding action to the global actions list.

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
    action_: Action

    match_ = matches[i]
    parameter_token = doc[match_[1][2]]
    start = min(match_[1])
    end = max(match_[1]) + 1
    matched_str = doc[start:end].text
    parameter = parameter_token.text
    value_ = parameter_token.nbor(-1).text

    _add_condition(parameter, value_, matched_str)
    action_ = ParameterIsIgnored("not ignored")

    _action_list.append(action_)
    return None


def _extract_cond_also_value(
    matcher: DependencyMatcher,  # noqa: ARG001
    doc: Doc,
    i: int,
    matches: list[tuple[Any, ...]],
) -> Any | None:
    """on-match function for the spaCy DependencyMatcher.

    Extract the condition that contains the phrase '... <AUX | VERB> also ...'
    and add the corresponding action to the global actions list.

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
    match_ = matches[i]

    cond_start = match_[1][1]
    cond_end = match_[1][2] + 2

    action_start = match_[1][3] - 2
    action_end = match_[1][3] + 3

    cond_string = doc[cond_start:cond_end].text

    dependee = doc[match_[1][0]].nbor(-1).text
    value = doc[match_[1][2]].nbor(1).text
    set_value = doc[match_[1][3]].nbor(2).text

    _add_condition(dependee, value, cond_string, also=True)

    action_string_doc = doc[action_start:action_end]
    action_string = action_string_doc.text

    _action_list.append(ParameterWillBeSetTo(action_string, "this_parameter", set_value))

    return None


def _extract_if_only_accepted(
    matcher: DependencyMatcher,  # noqa: ARG001
    doc: Doc,
    i: int,
    matches: list[tuple[Any, ...]],
) -> Any | None:
    action: Action
    match_ = matches[i]
    prev_match = matches[i - 1]

    if len(matches) > 1 and _nlp.vocab.strings[prev_match[0]] == "DEPENDENCY_COND_ONLY_NOUN":
        matches.pop(i - 1)
        _condition_list.pop()
        _action_list.pop()

    cond_start = match_[1][1]

    cond_end = match_[1][0] + 2
    cond_verb_token = doc[match_[1][0]]

    dependee, value = _extract_dependee_value(cond_verb_token)

    cond_str = doc[cond_start:cond_end].text

    _add_condition(dependee, value, cond_str)

    action_start = match_[1][3]
    action_end = match_[1][2]

    action_value = doc[action_start + 1].text

    action_string_doc = doc[action_start : action_end + 1]
    action_string = action_string_doc.text

    action = ParameterWillBeSetTo(action_string, "this_parameter", action_value)

    _action_list.append(action)

    return None


_CONDTION_TYPE: TypeAlias = ParametersInRelation | ParameterHasValue | ParameterHasNotValue | ParameterIsNone | ParameterHasType | ParameterDoesNotHaveType | Condition
_ACTION_TYPE: TypeAlias = ParameterIsIgnored | ParameterIsIllegal | ParameterWillBeSetTo | ParameterIsRestricted | Action


def extract_param_dependencies(
    param_qname: str,
    description: str,
) -> list[tuple[str, _CONDTION_TYPE, _ACTION_TYPE]]:
    """Extract all dependencies.

    Parameters
    ----------
    param_qname
        qname of the parameter to be examined.

    description
        description string of the parameter to be examined.


    Returns
    -------
    list[tuple]
        List of all found dependencies.
        A dependency tuple always consists of the parameter name, the condition and the resulting action.

    """
    _condition_list.clear()
    _action_list.clear()
    _combined_condition.clear()

    current_name = param_qname

    dependency_tuples: list[tuple[str, _CONDTION_TYPE, _ACTION_TYPE]] = []

    description_preprocessed = _preprocess_docstring(description)
    description_doc = _nlp(description_preprocessed)
    for sent in description_doc.sents:

        _dep_matcher(sent)

    for idx, cond in enumerate(_condition_list):
        dependency_tuples.append((param_qname, cond, _action_list[idx]))

    return dependency_tuples


_conditional_only = {
    "LEFT_ID": "condition_head",
    "REL_OP": ">",
    "RIGHT_ID": "conditional_only",
    "RIGHT_ATTRS": {"LOWER": "only"},
}

# only <VERB> ... <if | when | ...> ... <action VERB>
_dep_cond_only_verb = [
    {"RIGHT_ID": "condition_head", "RIGHT_ATTRS": {"POS": "VERB"}},
    _conditional_only,
    {"LEFT_ID": "condition_head", "REL_OP": ".", "RIGHT_ID": "action_start", "RIGHT_ATTRS": {"POS": "SCONJ"}},
    # {"LEFT_ID": "action_start", "REL_OP": "<", "RIGHT_ID": "action", "RIGHT_ATTRS": {"POS": {"IN": ["AUX", "VERB"]}}},
    {
        "LEFT_ID": "action_start",
        "REL_OP": "<",
        "RIGHT_ID": "action",
        "RIGHT_ATTRS": {"ORTH": {"IN": _has_value_phrases}},
    },
]

# only <ADJ> ... <if | when | ...> ... <action VERB>
_dep_cond_only_adj = [
    {"RIGHT_ID": "condition_head", "RIGHT_ATTRS": {"POS": "ADJ"}},
    _conditional_only,
    {"LEFT_ID": "condition_head", "REL_OP": ".", "RIGHT_ID": "action_start", "RIGHT_ATTRS": {"POS": "SCONJ"}},
    # {"LEFT_ID": "action_start", "REL_OP": "<", "RIGHT_ID": "action", "RIGHT_ATTRS": {"POS": {"IN": ["AUX", "VERB"]}}},
    {
        "LEFT_ID": "action_start",
        "REL_OP": "<",
        "RIGHT_ID": "action",
        "RIGHT_ATTRS": {"ORTH": {"IN": _has_value_phrases}},
    },
]

# only  <if | when | ...> ... <action VERB>
_dep_cond_only = [
    {"RIGHT_ID": "condition_head", "RIGHT_ATTRS": {"POS": "SCONJ", "DEP": {"IN": ["mark", "advmod"]}}},
    {"LEFT_ID": "condition_head", "REL_OP": ";", "RIGHT_ID": "conditional_only", "RIGHT_ATTRS": {"LOWER": "only"}},
    # {
    #     "LEFT_ID": "condition_head",
    #     "REL_OP": "<",
    #     "RIGHT_ID": "action_head",
    #     "RIGHT_ATTRS": {"POS": {"IN": ["VERB", "AUX"]}},
    # },
    {
        "LEFT_ID": "condition_head",
        "REL_OP": "<",
        "RIGHT_ID": "action_head",
        "RIGHT_ATTRS": {"ORTH": {"IN": _has_value_phrases}},
    },
]

# only <NOUN> ... <passive action VERB>
_dep_cond_only_noun = [
    {"RIGHT_ID": "action_head", "RIGHT_ATTRS": {"POS": {"IN": ["AUX", "VERB"]}}},
    {"LEFT_ID": "action_head", "REL_OP": ">", "RIGHT_ID": "auxpass", "RIGHT_ATTRS": {"DEP": "auxpass"}},
    {"LEFT_ID": "action_head", "REL_OP": ">", "RIGHT_ID": "parameter", "RIGHT_ATTRS": {"DEP": "nsubjpass"}},
    {"LEFT_ID": "parameter", "REL_OP": ">", "RIGHT_ID": "conditional_only", "RIGHT_ATTRS": {"LOWER": "only"}},
]

# ... ignored <if | when | ...> ... <action VERB>
_dep_cond_ignored = [
    {"RIGHT_ID": "action_head", "RIGHT_ATTRS": {"LOWER": "ignored"}},
    {
        "LEFT_ID": "action_head",
        "REL_OP": ">",
        "RIGHT_ID": "condition_head",
        # "RIGHT_ATTRS": {"POS": {"IN": ["VERB", "AUX"]}, "DEP": {"NOT_IN": ["auxpass"]}},
        "RIGHT_ATTRS": {"ORTH": {"IN": _has_value_phrases}},
    },
    {
        "LEFT_ID": "condition_head",
        "REL_OP": ">",
        "RIGHT_ID": "condition_start",
        "RIGHT_ATTRS": {"DEP": {"IN": ["advmod", "mark"]}, "POS": "SCONJ"},
    },
]

_dep_cond_ignored_at_beginning = [
    {"RIGHT_ID": "action_head", "RIGHT_ATTRS": {"ORTH": "Ignored"}},
    {
        "LEFT_ID": "action_head",
        "REL_OP": "<",
        "RIGHT_ID": "condition_head",
        "RIGHT_ATTRS": {"ORTH": {"IN": _has_value_phrases}},
    },
    {"LEFT_ID": "action_head", "REL_OP": ">", "RIGHT_ID": "for", "RIGHT_ATTRS": {"ORTH": "for"}},
]

# Used ... <if | when | ...> ... <action VERB>
_dep_cond_used = [
    {"RIGHT_ID": "conditional_used", "RIGHT_ATTRS": {"ORTH": "Used"}},
    {
        "LEFT_ID": "conditional_used",
        "REL_OP": ">",
        "RIGHT_ID": "action_head",
        "RIGHT_ATTRS": {"POS": {"IN": ["AUX", "VERB"]}, "DEP": {"IN": ["advcl", "ccomp"]}},
    },
    {
        "LEFT_ID": "action_head",
        "REL_OP": ">",
        "RIGHT_ID": "condition_start",
        "RIGHT_ATTRS": {"POS": "SCONJ", "DEP": {"IN": ["advmod", "mark"]}},
    },
]

# Used ... <if | when | ...> ... <action VERB>
# Depending on parameter names or parameter values, the part-of-speech tag may change, so the dependency tree changes.
_dep_cond_used2 = [
    {"RIGHT_ID": "conditional_used", "RIGHT_ATTRS": {"ORTH": "Used"}},
    {
        "LEFT_ID": "conditional_used",
        "REL_OP": "<",
        "RIGHT_ID": "action_head",
        "RIGHT_ATTRS": {"POS": {"IN": ["AUX", "VERB"]}},
    },
    {"LEFT_ID": "conditional_used", "REL_OP": ">>", "RIGHT_ID": "condition_start", "RIGHT_ATTRS": {"POS": "SCONJ"}},
]

# ... (<if | when | ...> ... <action VERB>)
_dep_cond_when = [
    {"RIGHT_ID": "condition_start", "RIGHT_ATTRS": {"POS": "SCONJ", "DEP": {"IN": ["mark", "advmod"]}}},
    {
        "LEFT_ID": "condition_start",
        "REL_OP": "<",
        "RIGHT_ID": "action_head",
        "RIGHT_ATTRS": {"POS": {"IN": ["AUX", "VERB"]}},
    },
    {"LEFT_ID": "condition_start", "REL_OP": ";", "RIGHT_ID": "punctuation", "RIGHT_ATTRS": {"ORTH": "("}},
    {
        "LEFT_ID": "condition_start",
        "REL_OP": ".*",
        "RIGHT_ID": "action_verb",
        "RIGHT_ATTRS": {"LOWER": {"IN": ["equals", "is"]}},
    },
    {"LEFT_ID": "action_verb", "REL_OP": ".*", "RIGHT_ID": "right_bracket", "RIGHT_ATTRS": {"ORTH": ")"}},
]

# <If | When | ...> ... <action VERB>  must be ...
_dep_cond_if_must_be1 = [
    {"RIGHT_ID": "action_head", "RIGHT_ATTRS": {"POS": {"IN": ["VERB", "AUX"]}}},
    {
        "LEFT_ID": "action_head",
        "REL_OP": ">",
        "RIGHT_ID": "action_start",
        "RIGHT_ATTRS": {"POS": "SCONJ", "DEP": {"IN": ["mark", "advmod"]}},
    },
    {"LEFT_ID": "action_head", "REL_OP": "<", "RIGHT_ID": "must_be", "RIGHT_ATTRS": {"ORTH": "must be"}},
]

# <If | When | ...> ... <action VERB>  must be ...
# Depending on parameter names or parameter values, the part-of-speech tag may change, so the dependency tree changes.
_dep_cond_if_must_be2 = [
    {"RIGHT_ID": "action_head", "RIGHT_ATTRS": {"POS": {"IN": ["VERB", "AUX"]}}},
    {
        "LEFT_ID": "action_head",
        "REL_OP": ">",
        "RIGHT_ID": "action_start",
        "RIGHT_ATTRS": {"POS": "SCONJ", "DEP": {"IN": ["mark", "advmod"]}},
    },
    {"LEFT_ID": "action_head", "REL_OP": "$++", "RIGHT_ID": "must_be", "RIGHT_ATTRS": {"ORTH": "must be"}},
]

# ... <equals | is>  .. <if | when| ...> ... <dependee1> <rel_op> <dependee2>
_dep_cond_relational = [
    {"RIGHT_ID": "action_head", "RIGHT_ATTRS": {"ORTH": {"IN": ["equals", "is", "used"]}}},
    {
        "LEFT_ID": "action_head",
        "REL_OP": ">>",
        "RIGHT_ID": "sconj",
        "RIGHT_ATTRS": {"POS": "SCONJ", "DEP": {"IN": ["mark", "advmod"]}},
    },
    {
        "LEFT_ID": "sconj",
        "REL_OP": ".*",
        "RIGHT_ID": "rel_operator",
        "RIGHT_ATTRS": {"POS": "SYM", "ORTH": {"IN": ["$LT$", "$GT$", "$GEQ$", "$LEQ$"]}},
    },
]

# Raises <ERROR>...<if | when | ...>
_dep_cond_raise_error_start = [
    {"RIGHT_ID": "error", "RIGHT_ATTRS": {"ORTH": {"REGEX": r".*Error"}}},
    {"LEFT_ID": "error", "REL_OP": ">", "RIGHT_ID": "action_head", "RIGHT_ATTRS": {"LOWER": {"FUZZY1": "raise"}}},
    {"LEFT_ID": "error", "REL_OP": ".", "RIGHT_ID": "cond_start", "RIGHT_ATTRS": {"POS": "SCONJ"}},
]

# ... <equals | is> ... <ERROR> will be risen.
_dep_cond_raise_error_end = [
    {"RIGHT_ID": "error", "RIGHT_ATTRS": {"LOWER": "error"}},
    {"LEFT_ID": "error", "REL_OP": "<", "RIGHT_ID": "action_head", "RIGHT_ATTRS": {"LEMMA": "raise"}},
    {"LEFT_ID": "action_head", "REL_OP": "<", "RIGHT_ID": "verb", "RIGHT_ATTRS": {"POS": "VERB"}},
    {"LEFT_ID": "verb", "REL_OP": ">>", "RIGHT_ID": "cond_head", "RIGHT_ATTRS": {"ORTH": {"IN": ["is", "equals"]}}},
]

# ... <VERB> also ...
_dep_cond_param_also_value = [
    {"RIGHT_ID": "cond_head", "RIGHT_ATTRS": {"POS": {"IN": ["AUX", "VERB"]}}},
    {
        "LEFT_ID": "cond_head",
        "REL_OP": ">",
        "RIGHT_ID": "cond_start",
        "RIGHT_ATTRS": {"POS": "SCONJ", "DEP": {"IN": ["mark", "advmod"]}},
    },
    {"LEFT_ID": "cond_head", "REL_OP": ">", "RIGHT_ID": "also", "RIGHT_ATTRS": {"LOWER": "also"}},
    {"LEFT_ID": "cond_head", "REL_OP": "<", "RIGHT_ID": "action_head", "RIGHT_ATTRS": {"POS": "VERB"}},
]

_dep_if_only_accepted = [
    {"RIGHT_ID": "cond_head", "RIGHT_ATTRS": {"ORTH": {"IN": ["equals", "is"]}}},
    {"LEFT_ID": "cond_head", "REL_OP": ">", "RIGHT_ID": "conditional_if", "RIGHT_ATTRS": {"ORTH": "If"}},
    {"LEFT_ID": "cond_head", "REL_OP": "<", "RIGHT_ID": "accepted", "RIGHT_ATTRS": {"ORTH": "accepted"}},
    {"LEFT_ID": "accepted", "REL_OP": ">>", "RIGHT_ID": "action_only", "RIGHT_ATTRS": {"ORTH": "only"}},
]

_dep_matcher.add(
    "DEPENDENCY_IMPLICIT_IGNORED_ONLY",
    [_dep_cond_only_verb, _dep_cond_only_adj],
    on_match=_extract_only_condition_action,
)
_dep_matcher.add(
    "DEPENDENCY_IMPLICIT_IGNORED_PURE_ONLY",
    [_dep_cond_only],
    on_match=_extract_pure_only_condition_action,
)

_dep_matcher.add(
    "DEPENDENCY_IMPLICIT_IGNORED_USED",
    [_dep_cond_used, _dep_cond_used2],
    on_match=_extract_used_condition_action,
)

_dep_matcher.add(
    "DEPENDENCY_COND_IGNORED",
    [_dep_cond_ignored, _dep_cond_ignored_at_beginning],
    on_match=_extract_ignored_condition_action,
)

_dep_matcher.add("DEPENDENCY_COND_WHEN_BRACKETS", [_dep_cond_when], on_match=_extract_used_condition_action)

_dep_matcher.add(
    "DEPENDENCY_COND_MUST_BE",
    [_dep_cond_if_must_be1, _dep_cond_if_must_be2],
    on_match=_extract_must_be_condition,
)

_dep_matcher.add("DEPENDENCY_COND_RELATIONAL", [_dep_cond_relational], on_match=_extract_relational_condition)

_dep_matcher.add("DEPENDENCY_COND_ONLY_NOUN", [_dep_cond_only_noun], on_match=_extract_cond_only_noun)

_dep_matcher.add("DEPENDENCY_COND_ALSO_VALUE", [_dep_cond_param_also_value], on_match=_extract_cond_also_value)

_dep_matcher.add("DEPENDENCY_COND_RAISE_ERROR_START", [_dep_cond_raise_error_start], on_match=_extract_raise_error)
_dep_matcher.add("DEPENDENCY_COND_RAISE_ERROR_END", [_dep_cond_raise_error_end], on_match=_extract_raise_error)

_dep_matcher.add("DEPENDENCY_IF_ONLY_ACCEPTED", [_dep_if_only_accepted], on_match=_extract_if_only_accepted)

_pattern_hyphened_values = [{"IS_ASCII": True}, {"ORTH": "-"}, {"IS_ASCII": True}]
_pattern_hyphened_values2 = [{"IS_ASCII": True}, {"ORTH": "-"}, {"IS_ASCII": True}, {"ORTH": "-"}, {"IS_ASCII": True}]
_pattern_aux_be = [{"LOWER": {"IN": ["must", "will"]}}, {"LOWER": "be"}]
_pattern_rel_ops = [
    {"ORTH": "$"},
    {"ORTH": {"IN": ["LT$", "GT$", "LEQ$", "GEQ$"]}},
]

_merger_matcher.add("HYPHENED_VALUE", [_pattern_hyphened_values, _pattern_hyphened_values2], greedy="LONGEST")
_merger_matcher.add("AUXPASS", [_pattern_aux_be])
_merger_matcher.add("REL_OPS", [_pattern_rel_ops])

# Insert merger after Tagger into the pipeline
_nlp.add_pipe("merger", after="tagger")
