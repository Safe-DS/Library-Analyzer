from __future__ import annotations

from enum import Enum


class DocstringStyle(Enum):
    PLAINTEXT = ("plaintext",)
    NUMPY = ("numpy",)
    EPYDOC = "epydoc"

    def __str__(self) -> str:
        return self.name

    @staticmethod
    def from_string(key: str) -> DocstringStyle:
        try:
            return DocstringStyle[key.upper()]
        except KeyError as err:
            raise ValueError(f"Unknown docstring style: {key}") from err
