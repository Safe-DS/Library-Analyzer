from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

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
_matcher = Matcher(_nlp.vocab)
_dep_matcher = DependencyMatcher(_nlp.vocab)


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
    combined_with: str = ""

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Condition:
        match d["variant"]:
            case Condition.Variant.CONDITION:
                return cls(d["condition"], d["dependee"], d["combined_with"])
            case Condition.Variant.IN_RELATION:
                return ParametersInRelation.from_dict(d)
            case Condition.Variant.HAS_VALUE:
                return ParameterHasValue.from_dict(d)
            case Condition.Variant.NO_VALUE:
                return ParameterHasNotValue.from_dict(d)
            case Condition.Variant.IS_NONE:
                return ParameterIsNone.from_dict(d)
            case Condition.Variant.HAS_TYPE:
                return ParameterHasType.from_dict(d)
            case Condition.Variant.NO_TYPE:
                return ParameterDoesNotHaveType.from_dict(d)
            case _:
                raise KeyError("unknown variant found")

    def to_dict(self) -> dict[str, Any]:
        return {
            "variant": Condition.Variant.CONDITION,
            "condition": self.condition,
            "dependee": self.dependee,
            "combined_with": self.combined_with,
        }


class ParametersInRelation(Condition):
    def __init__(self, cond: str, left_dependee: str, right_dependee: str, rel_op: str):
        super().__init__(cond)
        self.left_dependee = left_dependee
        self.right_dependee = right_dependee
        self.rel_op = rel_op

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Condition:
        return cls(d["condition"], d["left_dependee"], d["right_dependee"], d["rel_op"])

    def to_dict(self) -> dict[str, Any]:
        return {
            "variant": Condition.Variant.IN_RELATION,
            "condition": self.condition,
            "combined_with": self.combined_with,
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
        combined_with: str = "",
        check_dependee: bool = False,
        also: bool = False,
    ) -> None:
        super().__init__(cond, dependee, combined_with)
        self.check_dependee: bool = check_dependee
        self.value: str = value
        self.also = also

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Condition:
        return cls(d["condition"], d["dependee"], d["value"], d["combined_with"], d["check_dependee"], d["also"])

    def to_dict(self) -> dict[str, Any]:
        return {
            "variant": Condition.Variant.HAS_VALUE,
            "condition": self.condition,
            "dependee": self.dependee,
            "value": self.value,
            "combined_with": self.combined_with,
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
        return {"variant": Condition.Variant.NO_VALUE, "condition": self.condition}


class ParameterIsNone(Condition):
    def __init__(self, cond: str, dependee: str, also: bool = False) -> None:
        super().__init__(cond, dependee)
        self.also = also

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Condition:
        return cls(d["condition"], d["dependee"], d["also"])

    def to_dict(self) -> dict[str, Any]:
        return {
            "variant": Condition.Variant.IS_NONE,
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
            "variant": Condition.Variant.NO_TYPE,
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
            "variant": Condition.Variant.HAS_TYPE,
            "condition": self.condition,
            "dependee": self.dependee,
            "type": self.type_,
        }


@dataclass
class Action:
    action: str

    class Variant(str, Enum):
        ACTION = "action"
        IS_IGNORED = "is_ignored"
        IS_ILLEGAL = "is_illegal"
        WILL_BE_SET = "will_be_set"
        IS_RESTRICTED = "is_restricted"

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Action:
        match d["variant"]:
            case Action.Variant.ACTION:
                return cls(d["action"])
            case Action.Variant.IS_IGNORED:
                return ParameterIsIgnored.from_dict(d)
            case Action.Variant.IS_ILLEGAL:
                return ParameterIsIllegal.from_dict(d)
            case Action.Variant.WILL_BE_SET:
                return ParameterWillBeSetTo.from_dict(d)
            case Action.Variant.IS_RESTRICTED:
                return ParameterIsRestricted.from_dict(d)
            case _:
                raise KeyError("unknown variant found")

    def to_dict(self) -> dict[str, Any]:
        return {"variant": Action.Variant.ACTION, "action": self.action}


class ParameterIsIgnored(Action):
    def __init__(self, action_: str) -> None:
        super().__init__(action_)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Action:
        return cls(d["action"])

    def to_dict(self) -> dict[str, Any]:
        return {"variant": Action.Variant.IS_IGNORED, "action": self.action}


class ParameterIsIllegal(Action):
    def __init__(self, action_: str) -> None:
        super().__init__(action_)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Action:
        return cls(d["action"])

    def to_dict(self) -> dict[str, Any]:
        return {"variant": Action.Variant.IS_ILLEGAL, "action": self.action}


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
            "variant": Action.Variant.WILL_BE_SET,
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
        return {"variant": Action.Variant.IS_RESTRICTED, "action": self.action}


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
        # matched_spans = filter_spans(matched_spans)
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

    docstring = re.sub(r"!=", " does not equal ", docstring)
    docstring = re.sub(r"==?", " equals ", docstring)
    docstring = re.sub(r"\s+", " ", docstring)

    docstring = re.sub(r"none", "None", docstring)
    docstring = re.sub(r"is set to", "is", docstring)

    return docstring


def _shorten_and_check_string(dependee: str, doc: Doc, passive: bool = False) -> None:
    """Shorten and recheck the passed Doc object if there is a multiple condition.

    The Doc-Object is checked for multiple conditions, which are linked with an 'and' or 'or'.
    The first condition found is removed and the new truncated Doc object is passed back to the dependency matcher.

    Parameters
    ----------
    dependee
        First found dependee

    doc
        Doc object to be checked for multiple conditions.

    passive
        True if the action verb is in passive form.

    """
    sconj_idx = 0
    and_or_idx = 0
    change = False

    for token in doc:
        if token.pos_ == "SCONJ":
            sconj_idx = token.i + 1

        elif token.text in ["and", "or"]:
            if len(doc) > token.i + 3 and token.nbor(2).text == "by":
                change = False
            else:
                change = True

            if token.text == "and":
                _combined_condition.append(dependee)

            and_or_idx = token.i + 1
            first_dep_val = doc[and_or_idx - 2]

            for child in first_dep_val.children:
                if (
                    (0 < child.i < len(doc) - 2)
                    and child.nbor(-1).text in ["and", "or"]
                    and child.nbor(1).pos_ not in ["AUX", "VERB"]
                ):
                    if passive:
                        and_or_idx += 1
                        sconj_idx = and_or_idx - 2
                    else:
                        sconj_idx += 2

            if not passive:
                break

    if change:
        shortened_string = doc[:sconj_idx].text + " " + doc[and_or_idx:].text
        shortened_doc = _nlp(shortened_string)
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


def _add_condition(dependee: str, value: str, cond_str: str, passive: bool = False, also: bool = False) -> None:
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
    types = ["integer", "float", "bool", "str", "string"]
    type_ = value.split(" ")[1].lower() if len(value.split(" ")) == 2 else ""

    if value == "None" or dependee == "None":
        dependee_ = dependee if dependee != "None" else value
        cond = ParameterIsNone(cond_str, dependee_)
        cond.also = also
    elif value == "not callable":
        cond = ParameterDoesNotHaveType(cond_str, dependee, value)
    elif type_ in types:
        cond = ParameterHasType(cond_str, dependee, type_)
    else:
        cond = ParameterHasValue(cond_str, dependee, value)
        cond.also = also
        cond.check_dependee = passive

    if _combined_condition:
        _condition_list[-1].combined_with = dependee
        cond.combined_with = _condition_list[-1].dependee

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

    condition_string = doc[start : cond_token.i + 2].text
    action_string = doc[action_token.i : -1].text

    if action_token.nbor(-1).is_punct:
        dependee, dependee_value = _extract_dependee_value(cond_token)
        restriction = ParameterIsRestricted(action_string)
    else:
        dependee, dependee_value = _extract_dependee_value(cond_token)
        depender, depender_value = _extract_dependee_value(action_token)
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

    _shorten_and_check_string(dependee, doc)

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

    _shorten_and_check_string(dependee, doc, passive=True)

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
    match = matches[i]
    start = min(match[1])

    if match[1][0] > match[1][2]:
        end = match[1][0] + 1
    else:
        end = max(match[1]) + 2

    action_token = doc[match[1][1]]

    passive = _check_passiveness(action_token, match)

    dependee, value = _extract_dependee_value(action_token, passive)

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

    passive = _check_passiveness(action_token, match)

    dependee, value = _extract_dependee_value(action_token, passive)

    condition_string = doc[start:end].text

    _add_condition(dependee, value, condition_string, passive)
    _action_list.append(ParameterIsIgnored("not ignored"))

    _shorten_and_check_string(dependee, doc, passive)

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
    action_token = doc[match_[1][0]]
    cond_token = doc[match_[1][2]]
    left_dependee = cond_token.nbor(-1).text
    right_dependee = cond_token.nbor(1).text

    depender, value = _extract_dependee_value(action_token)

    match cond_token.text:
        case "$GT$":
            rel_op = " > "
        case "$LT$":
            rel_op = " < "
        case "$GEQ$":
            rel_op = " >= "
        case "$LEQ$":
            rel_op = " <= "
        case _:
            rel_op = ""

    condition_string = doc[match_[1][1] : cond_token.i].text + rel_op + doc[cond_token.i + 1 : -1].text
    action_string = doc[: match_[1][1]].text

    _condition_list.append(ParametersInRelation(condition_string, left_dependee, right_dependee, rel_op.strip()))
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
    cond: Condition

    match_ = matches[i]
    parameter_token = doc[match_[1][2]]
    start = min(match_[1])
    end = max(match_[1]) + 1
    matched_str = doc[start:end].text
    parameter = parameter_token.text
    value_ = parameter_token.nbor(-1).text

    matcher_matches = _matcher(doc)

    match_id_strings = [(_nlp.vocab.strings[match_id], start_, end_) for match_id, start_, end_ in matcher_matches]

    # If the condition is spread over two sentences, the phrase 'in this case' in the second sentence indicates this.
    if any(match_id_string == "IN_THIS_CASE" for match_id_string, _, _ in match_id_strings):
        cond_start = -1
        cond_end = -1
        action_ = ParameterWillBeSetTo(matched_str, parameter, value_)

        for match_id_string, start_, end_ in match_id_strings:
            if match_id_string == "COND_VALUE_ASSIGNMENT":
                cond_start = start_
                cond_end = end_
                break

        # If a condition and an action were found in the first block,
        # the condition from the first sentence is additionally used for the action from the second sentence.
        if cond_start != -1 and (len(_condition_list) > 0) and (len(_condition_list) == len(_action_list)):
            cond = _condition_list[-1]
        else:
            cond_string = doc[cond_start : cond_end + 1].text
            value_ = doc[cond_end].text

            if cond_end - cond_start == 3:
                dependee = "this_parameter"
            else:
                dependee = doc[start + 1].text

            cond = ParameterHasValue(cond_string, dependee, value_)

        _condition_list.append(cond)

    else:
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
    action_string = doc[action_start:action_end].text

    dependee = doc[match_[1][0]].nbor(-1).text
    value = doc[match_[1][2]].nbor(1).text
    set_value = doc[match_[1][3]].nbor(2).text

    _add_condition(dependee, value, cond_string, also=True)

    _action_list.append(ParameterWillBeSetTo(action_string, "this_parameter", set_value))

    return None


def extract_param_dependencies(
    param_qname: str,
    description: str,
) -> list[tuple[str, Condition, Action]]:
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

    dependency_tuples: list[tuple[str, Condition, Action]] = []

    description_preprocessed = _preprocess_docstring(description)
    description_doc = _nlp(description_preprocessed)

    _dep_matcher(description_doc)

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
    {"LEFT_ID": "action_start", "REL_OP": "<", "RIGHT_ID": "action", "RIGHT_ATTRS": {"POS": {"IN": ["AUX", "VERB"]}}},
]

# only <ADJ> ... <if | when | ...> ... <action VERB>
_dep_cond_only_adj = [
    {"RIGHT_ID": "condition_head", "RIGHT_ATTRS": {"POS": "ADJ"}},
    _conditional_only,
    {"LEFT_ID": "condition_head", "REL_OP": ".", "RIGHT_ID": "action_start", "RIGHT_ATTRS": {"POS": "SCONJ"}},
    {"LEFT_ID": "action_start", "REL_OP": "<", "RIGHT_ID": "action", "RIGHT_ATTRS": {"POS": {"IN": ["AUX", "VERB"]}}},
]

# only  <if | when | ...> ... <action VERB>
_dep_cond_only = [
    {"RIGHT_ID": "condition_head", "RIGHT_ATTRS": {"POS": "SCONJ", "DEP": {"IN": ["mark", "advmod"]}}},
    {"LEFT_ID": "condition_head", "REL_OP": ";", "RIGHT_ID": "conditional_only", "RIGHT_ATTRS": {"LOWER": "only"}},
    {
        "LEFT_ID": "condition_head",
        "REL_OP": "<",
        "RIGHT_ID": "action_head",
        "RIGHT_ATTRS": {"POS": {"IN": ["VERB", "AUX"]}},
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
        "RIGHT_ATTRS": {"POS": {"IN": ["VERB", "AUX"]}, "DEP": {"NOT_IN": ["auxpass"]}},
    },
    {
        "LEFT_ID": "condition_head",
        "REL_OP": ">",
        "RIGHT_ID": "condition_start",
        "RIGHT_ATTRS": {"DEP": {"IN": ["advmod", "mark"]}, "POS": "SCONJ"},
    },
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
    {"RIGHT_ID": "action_head", "RIGHT_ATTRS": {"ORTH": {"IN": ["equals", "is"]}}},
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

_dep_matcher.add(
    "DEPENDENCY_IMPLICIT_IGNORED_ONLY",
    [_dep_cond_only_verb, _dep_cond_only_adj],
    on_match=_extract_only_condition_action,
)
_dep_matcher.add(
    "DEPENDENCY_IMPLICIT_IGNORED_PURE_ONLY", [_dep_cond_only], on_match=_extract_pure_only_condition_action,
)

_dep_matcher.add(
    "DEPENDENCY_IMPLICIT_IGNORED_USED", [_dep_cond_used, _dep_cond_used2], on_match=_extract_used_condition_action,
)

_dep_matcher.add("DEPENDENCY_COND_IGNORED", [_dep_cond_ignored], on_match=_extract_ignored_condition_action)

_dep_matcher.add("DEPENDENCY_COND_WHEN_BRACKETS", [_dep_cond_when], on_match=_extract_used_condition_action)

_dep_matcher.add(
    "DEPENDENCY_COND_MUST_BE", [_dep_cond_if_must_be1, _dep_cond_if_must_be2], on_match=_extract_must_be_condition,
)

_dep_matcher.add("DEPENDENCY_COND_RELATIONAL", [_dep_cond_relational], on_match=_extract_relational_condition)

_dep_matcher.add("DEPENDENCY_COND_ONLY_NOUN", [_dep_cond_only_noun], on_match=_extract_cond_only_noun)

_dep_matcher.add("DEPENDENCY_COND_ALSO_VALUE", [_dep_cond_param_also_value], on_match=_extract_cond_also_value)

_dep_matcher.add("DEPENDENCY_COND_RAISE_ERROR_START", [_dep_cond_raise_error_start], on_match=_extract_raise_error)
_dep_matcher.add("DEPENDENCY_COND_RAISE_ERROR_END", [_dep_cond_raise_error_end], on_match=_extract_raise_error)

_pattern_hyphened_values = [{"IS_ASCII": True}, {"ORTH": "-"}, {"IS_ASCII": True}]
_pattern_hyphened_values2 = [{"IS_ASCII": True}, {"ORTH": "-"}, {"IS_ASCII": True}, {"ORTH": "-"}, {"IS_ASCII": True}]
_pattern_aux_be = [{"LOWER": {"IN": ["must", "will"]}}, {"LOWER": "be"}]
_pattern_rel_ops = [
    {"ORTH": "$"},
    {"ORTH": {"IN": ["LT$", "GT$", "LEQ$", "GEQ$"]}},
]

_pattern_in_this_case = [{"LOWER": "in"}, {"LOWER": "this"}, {"LOWER": "case"}]

_pattern_cond_value_assignment = [
    {"ORTH": {"IN": ["When", "If"]}},
    {"OP": "?"},
    {"LOWER": {"IN": ["equals", "set", "is"]}},
    {"LOWER": "to", "OP": "?"},
]

_merger_matcher.add("HYPHENED_VALUE", [_pattern_hyphened_values, _pattern_hyphened_values2], greedy="LONGEST")
_merger_matcher.add("AUXPASS", [_pattern_aux_be])
_merger_matcher.add("REL_OPS", [_pattern_rel_ops])

_matcher.add("IN_THIS_CASE", [_pattern_in_this_case])
_matcher.add("COND_VALUE_ASSIGNMENT", [_pattern_cond_value_assignment], greedy="LONGEST")

# Insert merger after Tagger into the pipeline
_nlp.add_pipe("merger", after="tagger")
