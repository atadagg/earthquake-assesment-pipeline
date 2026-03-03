"""
Central thread registry for the earthquake pipeline.

Tracks all known Ekşi Sözlük threads and their lifecycle across all pipeline
components: detector, scrapers, classifiers, and extractors.

A thread is the unit of work. Multiple threads can belong to the same
earthquake event (earthquake_id), and threads can merge on the platform —
this registry records those relationships so downstream components can
correlate entries correctly.
"""

import json
import os
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

DEFAULT_REGISTRY_FILE = "data/thread_registry.json"


class ThreadStatus:
    ACTIVE = "active"       # Worker is running, thread has entries
    MERGED = "merged"       # Entry count hit 0; Ekşi merged this thread elsewhere
    DEAD = "dead"           # Worker exited unexpectedly
    COMPLETED = "completed" # Thread concluded naturally


@dataclass
class ThreadRecord:
    thread_path: str              # e.g. "deprem--123456"
    url: str                      # Full URL
    earthquake_id: str            # e.g. "3-2-2025-kahramanmaras"
    status: str                   # ThreadStatus constant
    discovered_at: str            # ISO timestamp
    data_dir: str                 # Directory where diffs/state are written
    worker_pid: Optional[int] = None
    merge_target: Optional[str] = None  # thread_path this merged into (if known)
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())


class ThreadRegistry:
    """
    Persistent, thread-safe registry of all earthquake threads.

    Persisted atomically to a JSON file so state survives restarts.
    Safe to import and use from multiple pipeline components in the same
    process. Worker subprocesses can also write to it since all writes
    go through atomic file rename.
    """

    def __init__(self, registry_file: str = DEFAULT_REGISTRY_FILE):
        self.registry_file = registry_file
        self._lock = threading.Lock()
        self._records: Dict[str, ThreadRecord] = {}
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self):
        path = Path(self.registry_file)
        if not path.exists():
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for item in data:
                record = ThreadRecord(**item)
                self._records[record.thread_path] = record
        except Exception as e:
            print(f"[ThreadRegistry] Warning: could not load registry: {e}")

    def _save(self):
        """Atomically write registry to disk."""
        path = Path(self.registry_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = f"{self.registry_file}.tmp.{os.getpid()}"
        try:
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(
                    [asdict(r) for r in self._records.values()],
                    f, ensure_ascii=False, indent=2
                )
                f.flush()
                os.fsync(f.fileno())
            os.rename(tmp, self.registry_file)
        except Exception as e:
            print(f"[ThreadRegistry] Error saving registry: {e}")
            try:
                Path(tmp).unlink(missing_ok=True)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register(self, thread_path: str, url: str, earthquake_id: str, data_dir: str) -> ThreadRecord:
        """
        Register a new thread. Returns the existing record unchanged if
        thread_path is already tracked — idempotent by design.
        """
        with self._lock:
            if thread_path in self._records:
                return self._records[thread_path]
            record = ThreadRecord(
                thread_path=thread_path,
                url=url,
                earthquake_id=earthquake_id,
                status=ThreadStatus.ACTIVE,
                discovered_at=datetime.now().isoformat(),
                data_dir=data_dir,
            )
            self._records[thread_path] = record
            self._save()
            return record

    def get(self, thread_path: str) -> Optional[ThreadRecord]:
        with self._lock:
            return self._records.get(thread_path)

    def update(self, thread_path: str, **kwargs) -> bool:
        """
        Update fields on an existing record. Silently ignores unknown fields.
        Returns False if thread_path is not registered.
        """
        with self._lock:
            record = self._records.get(thread_path)
            if record is None:
                return False
            for key, val in kwargs.items():
                if hasattr(record, key):
                    setattr(record, key, val)
            record.last_updated = datetime.now().isoformat()
            self._save()
            return True

    def is_tracked(self, thread_path: str) -> bool:
        with self._lock:
            return thread_path in self._records

    def has_active_worker(self, thread_path: str) -> bool:
        with self._lock:
            record = self._records.get(thread_path)
            return record is not None and record.status == ThreadStatus.ACTIVE

    def get_by_earthquake_id(self, earthquake_id: str) -> List[ThreadRecord]:
        """Return all threads that belong to the same earthquake event."""
        with self._lock:
            return [r for r in self._records.values() if r.earthquake_id == earthquake_id]

    def get_all_active(self) -> List[ThreadRecord]:
        with self._lock:
            return [r for r in self._records.values() if r.status == ThreadStatus.ACTIVE]

    def get_all(self) -> List[ThreadRecord]:
        with self._lock:
            return list(self._records.values())
