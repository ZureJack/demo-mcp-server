from __future__ import annotations

from collections import defaultdict
from . import SymbolData, SymbolStorage


class MemoryStorage(SymbolStorage):
    def __init__(self):
        self._by_name: dict[str, list[SymbolData]] = defaultdict(list)
        self._by_file: dict[str, list[SymbolData]] = defaultdict(list)

    def add_symbols(self, symbols: list[SymbolData]) -> None:
        for sym in symbols:
            self._by_name[sym.name].append(sym)
            self._by_file[sym.file_path].append(sym)

    def remove_file(self, file_path: str) -> None:
        removed = self._by_file.pop(file_path, [])
        for sym in removed:
            lst = self._by_name.get(sym.name)
            if lst:
                self._by_name[sym.name] = [s for s in lst if s.file_path != file_path]

    def find_by_name(self, name: str) -> list[SymbolData]:
        return self._by_name.get(name, [])

    def find_by_name_contains(self, part: str) -> list[SymbolData]:
        result = []
        for name, symbols in self._by_name.items():
            if part in name:
                result.extend(symbols)
        return result

    def stats(self) -> dict:
        total = sum(len(v) for v in self._by_name.values())
        return {
            "file_count": len(self._by_file),
            "symbol_count": total,
            "status": "ready",
        }

    def clear(self) -> None:
        self._by_name.clear()
        self._by_file.clear()

    def close(self) -> None:
        self.clear()
