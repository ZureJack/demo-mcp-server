from __future__ import annotations

from abc import ABC, abstractmethod
from typing import NamedTuple, Literal


class SymbolData(NamedTuple):
    name: str
    file_path: str
    line: int
    column: int
    kind: Literal["definition", "declaration"]
    symbol_type: Literal["function", "variable", "type", "macro", "struct", "union", "enum"]
    definition: str
    start_line: int
    end_line: int


class SymbolStorage(ABC):
    @abstractmethod
    def add_symbols(self, symbols: list[SymbolData]) -> None: ...

    @abstractmethod
    def remove_file(self, file_path: str) -> None: ...

    @abstractmethod
    def find_by_name(self, name: str) -> list[SymbolData]: ...

    @abstractmethod
    def find_by_name_contains(self, part: str) -> list[SymbolData]: ...

    @abstractmethod
    def stats(self) -> dict: ...

    @abstractmethod
    def clear(self) -> None: ...

    @abstractmethod
    def close(self) -> None: ...
