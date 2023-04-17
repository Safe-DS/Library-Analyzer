import spacy
from spacy.matcher import Matcher
from typing import Any

nlp = spacy.load("en_core_web_sm")
matcher = Matcher(nlp.vocab)

boundary_interval = [
    {"LOWER": "in"},
    {"LOWER": "the"},
    {"LOWER": {"IN": ["range", "interval"]}},
    {"LOWER": "of", "OP": "?"},
    {"ORTH": {"IN": ["(", "["]}},
    {"LIKE_NUM": True},
    {"ORTH": ","},
    {"LIKE_NUM": True},
    {"ORTH": {"IN": [")", "]"]}}
]

boundary_non_negative = [
    {"LOWER": {"IN": ["non", "not"]}},
    {"ORTH": {"IN": ["-", "_"]}, "OP": "?"},
    {"LOWER": "negative"}
 ]

boundary_positive = [
    {"LOWER": "strictly", "OP": "?"},
    {"LOWER": "positive"}
]

boundary_non_positive =[
    {"LOWER": {"IN": ["non", "not"]}},
    {"ORTH": {"IN": ["-", "_"]}, "OP": "?"},
    {"LOWER": "positive"}
]

boundary_negative = [
    {"LOWER": "strictly", "OP": "?"},
    {"LOWER": "negative"}
]

boundary_between = [
    {"LOWER": "between"},
    {"LIKE_NUM": True},
    {"LOWER": "and"},
    {"LIKE_NUM": True}
]

boundary_type = [
    {"LOWER": "if", "OP": "?"},
    {"LOWER": {"IN": ["float", "double", "int"]}}
]

matcher.add("BOUNDARY_INTERVAL", [boundary_interval])
matcher.add("BOUNDARY_POSITIVE", [boundary_positive])
matcher.add("BOUNDARY_NON_NEGATIVE", [boundary_non_negative])
matcher.add("BOUNDARY_NEGATIVE", [boundary_negative])
matcher.add("BOUNDARY_NON_POSITIVE", [boundary_non_positive])
matcher.add("BOUNDARY_BETWEEN", [boundary_between])
matcher.add("BOUNDARY_TYPE", [boundary_type])


def extract_boundary(type_string: str, description: str) -> set[tuple[str, tuple[Any, bool], tuple[Any, bool]]]:

    boundaries = set()
    type_funcs = {"float": float, "double": float, "int": int}

    type_doc = nlp(type_string)
    description_doc = nlp(description)
    type_matches = matcher(type_doc)
    type_matches = [type_doc[start:end] for match_id, start, end in type_matches]
    desc_matches = matcher(description_doc)
    desc_matches = [(nlp.vocab.strings[match_id], description_doc[start:end])
                    for match_id, start, end in desc_matches]

    if len(type_matches) == 1:
        type_ = type_matches[0].text
        type_func = type_funcs[type_]
        match_label, match_string = desc_matches[0]

        if match_label == "BOUNDARY_POSITIVE":
            boundaries.add((type_, (type_func(0), False), ("infinity", False)))
        elif match_label == "BOUNDARY_NON_NEGATIVE":
            boundaries.add((type_, (type_func(0), True), ("infinity", False)))
        elif match_label == "BOUNDARY_NEGATIVE":
            boundaries.add((type_, ("negative infinity", False), (type_func(0), False)))
        elif match_label == "BOUNDARY_NON_POSITIVE":
            boundaries.add((type_, ("negative infinity", False), (type_func(0), True)))
        elif match_label == "BOUNDARY_BETWEEN":
            values = []
            for token in match_string:
                if token.like_num:
                    values.append(token.text)
            boundaries.add((
                type_,
                (type_func(min(values)), True),
                (type_func(max(values)), True)
            ))
        elif match_label == "BOUNDARY_INTERVAL":
            values = []
            paranthesis = []
            for token in match_string:
                if token.text in ["(", "[", ")", "]"]:
                    paranthesis.append(token.text)
                if token.like_num:
                    values.append(token.text)
            boundaries.add((
                type_,
                (type_func(min(values)), paranthesis[0] == "["),
                (type_func(max(values)), paranthesis[1] == "]")
            ))




    # if len(type_matches) != 0:
    #
    #
    #     for match_label, value in desc_matches:
    #             if match_label == "BOUNDARY_POSITIVE":
    #                 boundaries.add()

    return boundaries


if __name__ == '__main__':

    desc = "Momentum for gradient descent update. Should be between 0 and 1. Only used when solver='sgd'."
    type_ = "float"

    t = extract_boundary(type_, desc)
    print(t)
