from __future__ import annotations

import sqlite3
from pathlib import Path
from . import SymbolData, SymbolStorage


class SqliteStorage(SymbolStorage):
    def __init__(self, db_path: str | Path):
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._init_db()

    def _init_db(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS symbols (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                file_path   TEXT NOT NULL,
                line        INTEGER NOT NULL,
                column      INTEGER NOT NULL,
                kind        TEXT NOT NULL,
                symbol_type TEXT NOT NULL,
                definition  TEXT NOT NULL,
                start_line  INTEGER NOT NULL,
                end_line    INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_sym_name ON symbols(name);
            CREATE INDEX IF NOT EXISTS idx_sym_file ON symbols(file_path);
            CREATE INDEX IF NOT EXISTS idx_sym_type ON symbols(symbol_type);
        """)
        self._conn.commit()

    def add_symbols(self, symbols: list[SymbolData]) -> None:
        rows = [
            (s.name, s.file_path, s.line, s.column, s.kind,
             s.symbol_type, s.definition, s.start_line, s.end_line)
            for s in symbols
        ]
        self._conn.executemany(
            "INSERT INTO symbols (name, file_path, line, column, kind, "
            "symbol_type, definition, start_line, end_line) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        self._conn.commit()

    def remove_file(self, file_path: str) -> None:
        self._conn.execute("DELETE FROM symbols WHERE file_path = ?", (file_path,))
        self._conn.commit()

    def find_by_name(self, name: str) -> list[SymbolData]:
        rows = self._conn.execute(
            "SELECT name, file_path, line, column, kind, symbol_type, "
            "definition, start_line, end_line FROM symbols WHERE name = ? "
            "ORDER BY file_path, line",
            (name,),
        ).fetchall()
        return [SymbolData(*r) for r in rows]

    def find_by_name_contains(self, part: str) -> list[SymbolData]:
        rows = self._conn.execute(
            "SELECT name, file_path, line, column, kind, symbol_type, "
            "definition, start_line, end_line FROM symbols "
            "WHERE name LIKE ? ORDER BY name, file_path, line",
            (f"%{part}%",),
        ).fetchall()
        return [SymbolData(*r) for r in rows]

    def stats(self) -> dict:
        file_count = self._conn.execute(
            "SELECT COUNT(DISTINCT file_path) FROM symbols"
        ).fetchone()[0]
        symbol_count = self._conn.execute(
            "SELECT COUNT(*) FROM symbols"
        ).fetchone()[0]
        return {
            "file_count": file_count,
            "symbol_count": symbol_count,
            "status": "ready",
        }

    def clear(self) -> None:
        self._conn.execute("DELETE FROM symbols")
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
