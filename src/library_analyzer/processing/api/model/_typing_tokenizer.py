from enum import Enum
from typing import Final, Literal


class TypingTokenType(Enum):
    """Token Enum."""

    KO = "KO"  # ","
    KA = "KA"  # "["
    KZ = "KZ"  # "]"
    PI = "PI"  # "|"

    TYG = "TYG"  # Typing-module type-class; e.g. "Union", "Optional", etc
    TYP = "TYP"  # python built-in type; e.g. "int", "str", etc.

    SINGLE_QUOTATION = "SINGLE_QUOTATION"  # ' char
    DOUBLE_QUOTATION = "DOUBLE_QUOTATION"  # " char
    NUMBER = "NUMBER"
    BOOLEAN = "BOOLEAN"
    NONE = "NONE"
    WORD = "WORD"  # Misc. strings in Literal typings


class TypingToken:
    """Token."""

    _type: Final[TypingTokenType]
    _lexeme: Final[str]
    _literal: Final[object]

    def __init__(self, type_: TypingTokenType, lexeme: str, literal: object):
        self._type = type_
        self._lexeme = lexeme
        self._literal = literal


class TypingScanner:
    """Scanner."""

    _source: Final[str]
    _tokens: Final[list[TypingToken]] = []
    _start: int = 0
    _current: int = 0

    possible_typings = [
        "List", "Dict", "Optional", "Final", "Set", "Tuple", "List", "Literal", "Union",
        "set", "tuple", "dict", "list",
    ]
    possible_built_in_types = ["bool", "int", "str", "tuple", "list", "float", "None", "dict"]

    def __init__(self, source: str):
        self._source = source

    def scan_tokens(self) -> list[TypingToken]:
        """Scan the source string for tokens."""
        while not self._is_at_end():
            # We are at the beginning of the next lexeme
            self._start = self._current
            self._scan_token()
        return self._tokens

    def _is_at_end(self) -> bool:
        return self._current >= len(self._source)

    def _scan_token(self) -> None:
        c: str = self._peek()

        match c:
            case "[":
                self._current += 1
                self._add_token(TypingTokenType.KA)
                return
            case "]":
                self._current += 1
                self._add_token(TypingTokenType.KZ)
                return
            case ",":
                self._current += 1
                self._add_token(TypingTokenType.KO)
                return
            case "|":
                self._current += 1
                self._add_token(TypingTokenType.PI)
                return
            case "'":
                self._string_in_quotes("'")
                self._current += 1
                return
            case '"':
                self._string_in_quotes('"')
                self._current += 1
                return

        if c.isdigit():
            self._number()
        elif self._is_alpha(c):
            self._identifier()
        else:
            raise ScanningError("Unexpected character.")

    def _identifier(self) -> None:
        while self._is_alpha_numeric(self._peek()):
            self._advance()

        text = self._source[self._start:self._current]

        # Check if it's a typing object
        if text in self.possible_typings:
            return self._add_token(TypingTokenType.TYG)
        # Check if it's a build-in type
        elif text in self.possible_built_in_types:
            return self._add_token(TypingTokenType.TYP)
        # Check if it's a boolean
        elif text in ("True", "False"):
            return self._add_token(TypingTokenType.BOOLEAN, text == "True")
        elif text == "None":
            return self._add_token(TypingTokenType.NONE, None)

        self._add_token(TypingTokenType.WORD)

    @staticmethod
    def _is_alpha(c: str) -> bool:
        return ("a" <= c <= "z") or ("A" <= c <= "Z")

    def _is_alpha_numeric(self, c: str) -> bool:
        return self._is_alpha(c) or c.isdigit()

    def _advance(self) -> str:
        self._current += 1
        if self._current >= len(self._source):
            return ""
        return self._source[self._current]

    def _add_token(self, type_: TypingTokenType, literal: object = None) -> None:
        text: str = self._source[self._start:self._current]
        self._tokens.append(TypingToken(type_, text, literal))

    def _peek(self) -> str:
        if self._is_at_end():
            return ""  # "\0"
        return self._source[self._current]

    def _string_in_quotes(self, string_type: Literal['"'] | Literal["'"]) -> None:
        while self._peek_next() != string_type and not self._is_at_end():
            self._advance()

        if self._is_at_end():
            raise ScanningError("Unterminated string.")

        # The closing " or '
        self._advance()

        # Without the surrounding quotes.
        self._start += 1
        value: str = self._source[self._start:self._current]

        token = TypingTokenType.SINGLE_QUOTATION if string_type == "'" else TypingTokenType.DOUBLE_QUOTATION
        self._add_token(token, value)

    def _number(self) -> None:
        while self._peek().isdigit():
            self._advance()

        # Look for a fractional part.
        if self._peek() == "." and self._peek_next().isdigit():
            # Consume the "."
            self._advance()

            while self._peek().isdigit():
                self._advance()

        source = self._source[self._start:self._current]
        number_literal: int | float = float(source) if "." in source else int(source)

        self._add_token(TypingTokenType.NUMBER, number_literal)

    def _peek_next(self) -> str:
        if self._current + 1 >= len(self._source):
            return ""
        return self._source[self._current + 1]


class ScanningError(Exception):
    """Class for a ScanningError."""

    def __init__(self, message) -> None:
        self.message = message

    def __str__(self) -> str:
        """Return an error message."""
        return f"ScanningError: {self.message}"
