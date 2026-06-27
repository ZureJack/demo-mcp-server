from __future__ import annotations

import os
import threading
from pathlib import Path
from threading import Timer

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .storage import SymbolStorage
from .scanner import reparse_file


class CFileHandler(FileSystemEventHandler):
    def __init__(
        self,
        project_dir: str,
        config: dict,
        storage: SymbolStorage,
        scan_lock: threading.Lock,
    ):
        self._project_dir = project_dir
        self._config = config
        self._storage = storage
        self._scan_lock = scan_lock
        self._debounce_ms = config.get("debounce_ms", 500)
        self._debounce_timers: dict[str, Timer] = {}
        self._extensions = tuple(config.get("include_extensions", [".c", ".h"]))
        self._exclude_dirs = set(config.get("exclude_dirs", []))

    def _is_target(self, path: str) -> bool:
        if not path.endswith(self._extensions):
            return False
        rel = os.path.relpath(path, self._project_dir)
        parts = Path(rel).parts
        return not any(p in self._exclude_dirs for p in parts)

    def _schedule(self, path: str) -> None:
        timer = self._debounce_timers.pop(path, None)
        if timer is not None:
            timer.cancel()
        t = Timer(self._debounce_ms / 1000, self._process_file, args=[path])
        self._debounce_timers[path] = t
        t.start()

    def on_modified(self, event) -> None:
        if not event.is_directory and self._is_target(event.src_path):
            self._schedule(event.src_path)

    def on_created(self, event) -> None:
        if not event.is_directory and self._is_target(event.src_path):
            self._schedule(event.src_path)

    def on_deleted(self, event) -> None:
        if not event.is_directory and self._is_target(event.src_path):
            with self._scan_lock:
                rel = os.path.relpath(event.src_path, self._project_dir)
                self._storage.remove_file(rel)

    def _process_file(self, path: str) -> None:
        with self._scan_lock:
            rel = os.path.relpath(path, self._project_dir)
            try:
                symbols = reparse_file(path, self._project_dir, self._config)
                self._storage.remove_file(rel)
                if symbols:
                    self._storage.add_symbols(symbols)
            except Exception:
                pass


class FileWatcher:
    def __init__(self, project_dir: str, config: dict, storage: SymbolStorage, scan_lock: threading.Lock):
        self._project_dir = project_dir
        self._config = config
        self._storage = storage
        self._scan_lock = scan_lock
        self._observer: Observer | None = None
        self._handler = CFileHandler(project_dir, config, storage, scan_lock)

    def start(self) -> None:
        if self._observer is not None:
            return
        self._observer = Observer()
        self._observer.schedule(self._handler, self._project_dir, recursive=True)
        self._observer.start()

    def stop(self) -> None:
        if self._observer is None:
            return
        self._observer.stop()
        self._observer.join()
        self._observer = None

    @property
    def is_running(self) -> bool:
        return self._observer is not None and self._observer.is_alive()
