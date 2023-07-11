from __future__ import annotations

from enum import Enum


class DocstringStyle(Enum):
    # AUTO = "auto",
    PLAINTEXT = "plaintext"
    EPYDOC = "epydoc"
    GOOGLE = "google"
    NUMPY = "numpy"
    REST = "rest"

    def __str__(self) -> str:
        return self.name

    @staticmethod
    def from_string(key: str) -> DocstringStyle:
        try:
            return DocstringStyle[key.upper()]
        except KeyError as err:
            raise ValueError(f"Unknown docstring style: {key}") from err
