from __future__ import annotations

import re
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar


class AbstractType(metaclass=ABCMeta):
    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> AbstractType | None:
        if d is None:
            return None

        value: AbstractType | None = NamedType.from_dict(d)
        if value is not None:
            return value

        value = EnumType.from_dict(d)
        if value is not None:
            return value

        value = BoundaryType.from_dict(d)
        if value is not None:
            return value

        value = ListType.from_dict(d)
        if value is not None:
            return value

        value = DictType.from_dict(d)
        if value is not None:
            return value

        value = SetType.from_dict(d)
        if value is not None:
            return value

        value = OptionalType.from_dict(d)
        if value is not None:
            return value

        value = LiteralType.from_dict(d)
        if value is not None:
            return value

        value = FinalType.from_dict(d)
        if value is not None:
            return value

        value = TupleType.from_dict(d)
        if value is not None:
            return value

        return UnionType.from_dict(d)

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        pass


@dataclass(frozen=True)
class NamedType(AbstractType):
    name: str

    @classmethod
    def from_dict(cls, d: Any) -> NamedType | None:
        if d.get("kind", "") == cls.__name__:
            return NamedType(d["name"])
        return None

    @classmethod
    def from_string(cls, string: str) -> NamedType:
        return NamedType(string)

    def to_dict(self) -> dict[str, str]:
        return {"kind": self.__class__.__name__, "name": self.name}


@dataclass(frozen=True)
class EnumType(AbstractType):
    values: frozenset[str] = field(default_factory=frozenset)
    full_match: str = field(default="", compare=False)

    @classmethod
    def from_dict(cls, d: Any) -> EnumType | None:
        if d["kind"] == cls.__name__:
            return EnumType(d["values"])
        return None

    @classmethod
    def from_string(cls, string: str) -> EnumType | None:
        def remove_backslash(e: str) -> str:
            e = e.replace(r"\"", '"')
            e = e.replace(r"\'", "'")
            return e

        enum_match = re.search(r"{(.*?)}", string)
        if enum_match:
            quotes = "'\""
            values = set()
            enum_str = enum_match.group(1)
            value = ""
            inside_value = False
            curr_quote = None
            for i, char in enumerate(enum_str):
                if char in quotes and (i == 0 or (i > 0 and enum_str[i - 1] != "\\")):
                    if not inside_value:
                        inside_value = True
                        curr_quote = char
                    elif inside_value:
                        if curr_quote == char:
                            inside_value = False
                            curr_quote = None
                            values.add(remove_backslash(value))
                            value = ""
                        else:
                            value += char
                elif inside_value:
                    value += char

            return EnumType(frozenset(values), enum_match.group(0))

        return None

    def update(self, enum: EnumType) -> EnumType:
        values = set(self.values)
        values.update(enum.values)
        return EnumType(frozenset(values))

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.__class__.__name__, "values": set(self.values)}


@dataclass(frozen=True)
class BoundaryType(AbstractType):
    NEGATIVE_INFINITY: ClassVar = "NegativeInfinity"
    INFINITY: ClassVar = "Infinity"

    base_type: str
    min: float | int | str
    max: float | int | str
    min_inclusive: bool
    max_inclusive: bool

    full_match: str = field(default="", compare=False)

    @classmethod
    def _is_inclusive(cls, bracket: str) -> bool:
        if bracket in ("(", ")"):
            return False
        if bracket in ("[", "]"):
            return True
        raise ValueError(f"{bracket} is not one of []()")

    @classmethod
    def from_dict(cls, d: Any) -> BoundaryType | None:
        if d["kind"] == cls.__name__:
            return BoundaryType(
                d["base_type"],
                d["min"],
                d["max"],
                d["min_inclusive"],
                d["max_inclusive"],
            )
        return None

    @classmethod
    def from_string(cls, string: str) -> BoundaryType | None:
        pattern = r"""(?P<base_type>float|int)?[ ]  # optional base type of either float or int
                    (in|of)[ ](the[ ])?(range|interval)[ ](of[ ])?  # 'in' or 'of', optional 'the', 'range' or 'interval', optional 'of'
                    `?(?P<min_bracket>[\[(])(?P<min>[-+]?\d+(.\d*)?|negative_infinity),[ ]  # left side of the range
                    (?P<max>[-+]?\d+(.\d*)?|infinity)(?P<max_bracket>[\])])`?"""  # right side of the range
        match = re.search(pattern, string, re.VERBOSE)

        if match is not None:
            base_type = match.group("base_type")
            if base_type is None:
                base_type = "float"

            min_value: str | int | float = match.group("min")
            if min_value != "negative_infinity":
                if base_type == "int":
                    min_value = int(min_value)
                else:
                    min_value = float(min_value)
            else:
                min_value = BoundaryType.NEGATIVE_INFINITY

            max_value: str | int | float = match.group("max")
            if max_value != "infinity":
                if base_type == "int":
                    max_value = int(max_value)
                else:
                    max_value = float(max_value)
            else:
                max_value = BoundaryType.INFINITY

            min_bracket = match.group("min_bracket")
            max_bracket = match.group("max_bracket")
            min_inclusive = BoundaryType._is_inclusive(min_bracket)
            max_inclusive = BoundaryType._is_inclusive(max_bracket)

            return BoundaryType(
                base_type=base_type,
                min=min_value,
                max=max_value,
                min_inclusive=min_inclusive,
                max_inclusive=max_inclusive,
                full_match=match.group(0),
            )

        return None

    def __eq__(self, __o: object) -> bool:
        if isinstance(__o, BoundaryType):
            eq = (
                self.base_type == __o.base_type
                and self.min == __o.min
                and self.min_inclusive == __o.min_inclusive
                and self.max == __o.max
            )
            if eq:
                if self.max == BoundaryType.INFINITY:
                    return True
                return self.max_inclusive == __o.max_inclusive
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.__class__.__name__,
            "base_type": self.base_type,
            "min": self.min,
            "max": self.max,
            "min_inclusive": self.min_inclusive,
            "max_inclusive": self.max_inclusive,
        }


@dataclass(frozen=True)
class UnionType(AbstractType):
    types: list[AbstractType]

    @classmethod
    def from_dict(cls, d: Any) -> UnionType | None:
        if d["kind"] == cls.__name__:
            types = []
            for element in d["types"]:
                type_ = AbstractType.from_dict(element)
                if type_ is not None:
                    types.append(type_)
            return UnionType(types)
        return None

    def to_dict(self) -> dict[str, Any]:
        type_list = []
        for t in self.types:
            type_list.append(t.to_dict())

        return {"kind": self.__class__.__name__, "types": type_list}

    def __hash__(self) -> int:
        return hash(frozenset(self.types))


@dataclass(frozen=True)
class ListType(AbstractType):
    types: list[AbstractType]

    @classmethod
    def from_dict(cls, d: Any) -> ListType | None:
        if d["kind"] == cls.__name__:
            types = []
            for element in d["types"]:
                type_ = AbstractType.from_dict(element)
                if type_ is not None:
                    types.append(type_)
            return ListType(types)
        return None

    def to_dict(self) -> dict[str, Any]:
        type_list = [
            t.to_dict()
            for t in self.types
        ]

        return {"kind": self.__class__.__name__, "types": type_list}

    def __hash__(self) -> int:
        return hash(frozenset(self.types))


# todo Sind Hashes hier (und bei anderen Klassen wie Set und List) sinnvoll,
#  da das Objekt veränderbar ist? Normales List Objekt hat ja auch kein Hash
@dataclass(frozen=True)
class DictType(AbstractType):
    key_type: AbstractType
    value_type: AbstractType

    @classmethod
    def from_dict(cls, d: Any) -> DictType | None:
        if d["kind"] == cls.__name__:
            return DictType(d["key_type"], d["value_type"])
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.__class__.__name__,
            "key_type": self.key_type,
            "value_type": self.value_type,
        }

    def __hash__(self) -> int:
        return hash(frozenset([self.key_type, self.value_type]))


@dataclass(frozen=True)
class SetType(AbstractType):
    types: list[AbstractType]

    @classmethod
    def from_dict(cls, d: Any) -> SetType | None:
        if d["kind"] == cls.__name__:
            types = []
            for element in d["types"]:
                type_ = AbstractType.from_dict(element)
                if type_ is not None:
                    types.append(type_)
            return SetType(types)
        return None

    def to_dict(self) -> dict[str, Any]:
        type_list = [
            t.to_dict()
            for t in self.types
        ]

        return {"kind": self.__class__.__name__, "types": type_list}

    def __hash__(self) -> int:
        return hash(frozenset(self.types))


@dataclass(frozen=True)
class OptionalType(AbstractType):
    type_: AbstractType | None

    @classmethod
    def from_dict(cls, d: Any) -> OptionalType | None:
        if d["kind"] == cls.__name__:
            return OptionalType(d["type"] or None)
        return None

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.__class__.__name__, "type": self.type_}

    def __hash__(self) -> int:
        return hash(frozenset([self.type_]))


@dataclass(frozen=True)
class LiteralType(AbstractType):
    literals: list[str | int | float | bool]

    @classmethod
    def from_dict(cls, d: Any) -> LiteralType | None:
        if d["kind"] == cls.__name__:
            literals = list(d["literals"])
            return LiteralType(literals)
        return None

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.__class__.__name__, "literals": self.literals}

    def __hash__(self) -> int:
        return hash(frozenset(self.literals))


@dataclass(frozen=True)
class FinalType(AbstractType):
    type_: AbstractType

    @classmethod
    def from_dict(cls, d: Any) -> FinalType | None:
        if d["kind"] == cls.__name__:
            return FinalType(d["type"])
        return None

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.__class__.__name__, "type": self.type_}

    def __hash__(self) -> int:
        return hash(frozenset([self.type_]))


@dataclass(frozen=True)
class TupleType(AbstractType):
    types: list[AbstractType]

    @classmethod
    def from_dict(cls, d: Any) -> TupleType | None:
        if d["kind"] == cls.__name__:
            types = []
            for element in d["types"]:
                type_ = AbstractType.from_dict(element)
                if type_ is not None:
                    types.append(type_)
            return TupleType(types)
        return None

    def to_dict(self) -> dict[str, Any]:
        type_list = [
            t.to_dict()
            for t in self.types
        ]

        return {"kind": self.__class__.__name__, "types": type_list}

    def __hash__(self) -> int:
        return hash(frozenset(self.types))

def _dismantel_structure(type_structure: str) -> list:
    current_type = ""
    result = []

    type_structure = type_structure.replace(" ", "")

    while True:
        i = 0
        for i, char in enumerate(type_structure):
            if char == "[":
                try:
                    brackets_content, remaining_content = _parse_bracket_content(type_structure[i + 1:])
                except TypeParsingError:
                    raise TypeParsingError(f"Missing brackets in the following string:\n{type_structure}")

                result.append(current_type + "[" + brackets_content + "]")
                type_structure = remaining_content
                current_type = ""
                break
            elif char == ",":
                if current_type:
                    result.append(current_type)
                    current_type = ""
            else:
                current_type += char

        if len(type_structure) == 0 or i + 1 == len(type_structure):
            break

    if current_type:
        result.append(current_type)

    return result


def _parse_bracket_content(substring: str) -> (str, str):
    brackets_content = ""
    bracket_count = 0
    for i, char in enumerate(substring):
        if char == "[":
            bracket_count += 1
        elif char == "]" and bracket_count:
            bracket_count -= 1
        elif char == "]" and not bracket_count:
            return brackets_content, substring[i + 1:]

        brackets_content += char
    raise TypeParsingError("")


def _create_type(type_string: str) -> AbstractType:
    # Structures, which only take one type argument
    structures = {"Final": FinalType, "Optional": OptionalType}
    for key in list(structures.keys()):
        regex = r"^" + key + r"\[(.*)\]$"
        match = re.match(regex, type_string)
        if match:
            content = match.group(1)
            return structures[key](_create_type(content))

    # List-like structures, which take multiple type arguments
    structures = {"List": ListType, "Set": SetType, "Tuple": TupleType, "Union": UnionType}
    for key in list(structures.keys()):
        regex = r"^" + key + r"\[(.*)\]$"
        match = re.match(regex, type_string)
        if match:
            content = match.group(1)
            content = content.replace(" ", "")
            content_elements = _dismantel_structure(content)
            return structures[key]([_create_type(element) for element in content_elements])

    # Misc. special structures
    match = re.match(r"^Dict\[(.*)\]$", type_string)
    if match:
        content = match.group(1)
        content = content.replace(" ", "")
        content_elements = _dismantel_structure(content)
        if len(content_elements) != 2:
            raise TypeParsingError(f"Could not parse Dict from the following string:\n{type_string}")
        return DictType(
            _create_type(content_elements[0]),
            _create_type(content_elements[1]),
        )

    # Todo
    match = re.match(r"^Literal\[(.*)\]$", type_string)
    if match:
        content = match.group(1)
        return LiteralType(content)

    return NamedType(type_string)


def create_type(type_string: str, description: str) -> AbstractType | None:
    types: list[AbstractType] = []

    # Collapse whitespaces
    type_string = re.sub(r"\s+", " ", type_string)

    # Get boundary from description
    boundary = BoundaryType.from_string(description)
    if boundary is not None:
        types.append(boundary)

    # Find all enums and remove them from doc_string
    enum_array_matches = re.findall(r"\{.*?}", type_string)
    type_string = re.sub(r"\{.*?}", " ", type_string)
    for enum in enum_array_matches:
        enum_type = EnumType.from_string(enum)
        if enum_type is not None:
            types.append(enum_type)

    # Remove default value from doc_string
    type_string = re.sub("default=.*", " ", type_string)

    # Create a list with all values and types
    # ") or (" must be replaced by a very unlikely string ("&%&") so that it is not removed when filtering out.
    # The string will be replaced by ") or (" again after filtering out.
    type_string = re.sub(r"\) or \(", "&%&", type_string)
    type_string = re.sub(r" ?, ?or ", ", ", type_string)
    type_string = re.sub(r" or ", ", ", type_string)
    type_string = re.sub("&%&", ") or (", type_string)

    brackets = 0
    build_string = ""
    for c in type_string:
        if c == "(":
            brackets += 1
        elif c == ")":
            brackets -= 1

        if brackets > 0:
            build_string += c
            continue

        if brackets == 0 and c != ",":
            build_string += c
        elif brackets == 0 and c == ",":
            # remove leading and trailing whitespaces
            build_string = build_string.strip()
            if build_string != "":
                named = NamedType.from_string(build_string)
                types.append(named)
                build_string = ""

    build_string = build_string.strip()

    # Append the last remaining entry
    if build_string != "":
        named = NamedType.from_string(build_string)
        types.append(named)

    if len(types) == 1:
        return types[0]
    if len(types) == 0:
        return None
    return UnionType(types)


class TypeParsingError(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return f"TypeParsingException: {self.message}"
