"""
Earthquake Pipeline — Main Orchestrator

Four daemon threads:
  Detector       polls Ekşi gündem, pushes EarthquakeEvents onto event_queue
  WorkerManager  spawns/tracks scraper worker subprocesses, reaps dead ones
  DiffWatcher    polls diff directories for new files, pushes DiffBatches onto process_queue
  EntryProcessor classifies + extracts entries, writes results to SQLite
"""

import json
import logging
import os
import queue
import signal
import sqlite3
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Path setup — make all sub-packages importable from repo root
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "detector"))
sys.path.insert(0, str(ROOT / "classifiers"))
sys.path.insert(0, str(ROOT / "classifiers" / "damage"))
sys.path.insert(0, str(ROOT / "extractors"))

from thread_registry import ThreadRegistry, ThreadStatus
from earthquake_patterns import is_earthquake_baslik
from earthquake_detector import fetch_gundem
from needs_classifier import KeywordClassifier
from keyword_matcher import KeywordMatcher, KeywordLoader
from address_extractor import AddressExtractor
from top_level_classifier import TopLevelClassifier

# ---------------------------------------------------------------------------
# Paths & config
# ---------------------------------------------------------------------------
DATA_DIR         = ROOT / "data"
LOGS_DIR         = ROOT / "logs"
SCRAPER_DATA_DIR = DATA_DIR / "scrapers"
REGISTRY_FILE    = str(DATA_DIR / "thread_registry.json")
DB_FILE          = str(DATA_DIR / "pipeline.db")
WORKER_SCRIPT    = str(ROOT / "detector" / "scraper" / "scraper_worker.py")

DETECTOR_INTERVAL = 30   # seconds between gündem polls
REAP_INTERVAL     = 60   # seconds between worker health checks
WATCH_INTERVAL    = 10   # seconds between diff directory scans

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOGS_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(threadName)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(LOGS_DIR / "pipeline.log"), encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared inter-thread state
# ---------------------------------------------------------------------------
event_queue: queue.Queue   = queue.Queue()   # Detector → WorkerManager
process_queue: queue.Queue = queue.Queue()   # DiffWatcher → EntryProcessor

worker_handles: dict[str, subprocess.Popen] = {}
worker_log_files: dict[str, object] = {}
worker_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Data transfer objects
# ---------------------------------------------------------------------------

@dataclass
class EarthquakeEvent:
    earthquake_id: str
    thread_path: str
    url: str


@dataclass
class DiffBatch:
    diff_file: Path
    thread_path: str
    earthquake_id: str
    entries: list


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def init_db():
    conn = sqlite3.connect(DB_FILE)

    # One-time migration: drop results table if it uses the old single-label schema
    cols = [row[1] for row in conn.execute("PRAGMA table_info(results)").fetchall()]
    if cols and "top_category" in cols:
        conn.execute("DROP TABLE results")
        conn.commit()
        log.info("Migrated results table to multi-label schema")

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS entries (
            entry_id      TEXT PRIMARY KEY,
            thread_path   TEXT NOT NULL,
            earthquake_id TEXT NOT NULL,
            author        TEXT,
            timestamp     TEXT,
            content       TEXT,
            scraped_at    TEXT,
            first_seen_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS results (
            entry_id          TEXT PRIMARY KEY,
            is_damage         INTEGER,   -- 1 = H (hasar)
            is_need           INTEGER,   -- 1 = Y (yardım)
            is_info           INTEGER,   -- 1 = B (bilgi)
            need_labels       TEXT,      -- JSON array e.g. ["G","S","B"]
            damage_keywords   TEXT,      -- JSON array of matched severity keywords
            extracted_address TEXT,
            processed_at      TEXT,
            FOREIGN KEY (entry_id) REFERENCES entries(entry_id)
        );

        CREATE INDEX IF NOT EXISTS idx_eq_id  ON entries(earthquake_id);
        CREATE INDEX IF NOT EXISTS idx_damage ON results(is_damage);
        CREATE INDEX IF NOT EXISTS idx_need   ON results(is_need);
    """)
    conn.commit()
    conn.close()
    log.info(f"DB ready: {DB_FILE}")


# ---------------------------------------------------------------------------
# Thread 1 — Detector
# ---------------------------------------------------------------------------

def detector_thread(registry: ThreadRegistry, stop_event: threading.Event):
    log.info("Started — polling every %ds", DETECTOR_INTERVAL)
    while not stop_event.is_set():
        try:
            basliks = fetch_gundem()
            for baslik in basliks:
                pattern = is_earthquake_baslik(baslik["title"])
                if not pattern:
                    continue
                earthquake_id = (
                    f"{pattern['day']}-{pattern['month']}-"
                    f"{pattern['year']}-{pattern['province']}"
                )
                thread_path = baslik["url"].split("?")[0].lstrip("/")
                if not registry.is_tracked(thread_path):
                    url = f"https://eksisozluk.com/{thread_path}"
                    event_queue.put(EarthquakeEvent(earthquake_id, thread_path, url))
                    log.info("Earthquake detected: %s → %s", earthquake_id, thread_path)
        except Exception as e:
            log.error("Detector error: %s", e)
        stop_event.wait(timeout=DETECTOR_INTERVAL)


# ---------------------------------------------------------------------------
# Thread 2 — Worker Manager
# ---------------------------------------------------------------------------

def worker_manager_thread(registry: ThreadRegistry, stop_event: threading.Event):
    log.info("Started")
    while not stop_event.is_set():
        # Drain the event queue
        while True:
            try:
                event = event_queue.get_nowait()
                _spawn_worker(event, registry)
            except queue.Empty:
                break
            except Exception as e:
                log.error("Spawn error: %s", e)

        _reap_workers(registry)
        stop_event.wait(timeout=REAP_INTERVAL)


def _spawn_worker(event: EarthquakeEvent, registry: ThreadRegistry):
    # Bug 1 fix: skip if a worker is already running for this thread
    with worker_lock:
        if event.thread_path in worker_handles:
            log.info("Worker already running for %s — skipping duplicate event", event.thread_path)
            return

    thread_dir = SCRAPER_DATA_DIR / event.thread_path
    thread_dir.mkdir(parents=True, exist_ok=True)
    state_file = str(thread_dir / "state.json")
    output_dir = str(thread_dir / "diffs")

    registry.register(event.thread_path, event.url, event.earthquake_id, str(thread_dir))

    try:
        log_fh = open(thread_dir / "worker.log", "a")
        proc = subprocess.Popen(
            [sys.executable, WORKER_SCRIPT,
             event.url, state_file, output_dir, REGISTRY_FILE],
            stdout=log_fh,
            stderr=subprocess.STDOUT,
        )
        with worker_lock:
            worker_handles[event.thread_path] = proc
            worker_log_files[event.thread_path] = log_fh
        registry.update(event.thread_path, worker_pid=proc.pid, status=ThreadStatus.ACTIVE)
        log.info("Spawned worker for %s (PID %d)", event.thread_path, proc.pid)
    except Exception as e:
        log.error("Failed to spawn worker for %s: %s", event.thread_path, e)
        registry.update(event.thread_path, status=ThreadStatus.DEAD)


def _reap_workers(registry: ThreadRegistry):
    with worker_lock:
        dead = [p for p, proc in worker_handles.items() if proc.poll() is not None]
    for path in dead:
        with worker_lock:
            proc = worker_handles.pop(path)
            log_fh = worker_log_files.pop(path, None)
        if log_fh:
            log_fh.close()
        record = registry.get(path)
        if record and record.status == ThreadStatus.ACTIVE:
            registry.update(path, status=ThreadStatus.DEAD)
            log.warning("Worker for %s died unexpectedly (exit %d) — re-queuing for respawn", path, proc.returncode)
            # Bug 2 fix: re-enqueue so WorkerManager respawns it on the next cycle
            event_queue.put(EarthquakeEvent(record.earthquake_id, path, record.url))
        else:
            log.info("Worker for %s exited cleanly", path)


# ---------------------------------------------------------------------------
# Thread 3 — Diff Watcher
# ---------------------------------------------------------------------------

def diff_watcher_thread(registry: ThreadRegistry, stop_event: threading.Event):
    log.info("Started — scanning every %ds", WATCH_INTERVAL)
    seen: set[str] = set()

    while not stop_event.is_set():
        try:
            for diff_file in sorted(SCRAPER_DATA_DIR.glob("*/diffs/diff_*.json")):
                key = str(diff_file)
                if key in seen:
                    continue
                seen.add(key)
                try:
                    with open(diff_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    new_entries = data.get("new", [])
                    if not new_entries:
                        continue
                    # Path structure: scrapers/<thread_path>/diffs/diff_*.json
                    thread_path = diff_file.parent.parent.name
                    record = registry.get(thread_path)
                    earthquake_id = record.earthquake_id if record else "unknown"
                    process_queue.put(DiffBatch(diff_file, thread_path, earthquake_id, new_entries))
                    log.info("Queued %d entries from %s", len(new_entries), diff_file.name)
                except Exception as e:
                    log.error("Error reading %s: %s", diff_file, e)
        except Exception as e:
            log.error("Watcher scan error: %s", e)
        stop_event.wait(timeout=WATCH_INTERVAL)


# ---------------------------------------------------------------------------
# Thread 4 — Entry Processor
# ---------------------------------------------------------------------------

def _load_classifiers():
    # Level 1 — independent binary classifiers (H / Y / B)
    top_clf = TopLevelClassifier()
    try:
        top_clf.load()
        log.info("Top-level classifiers loaded (H, Y, B)")
    except FileNotFoundError as e:
        log.warning("Top-level models not found — run: python classifiers/top_level_classifier.py train classifiers/data.xlsx\n%s", e)
        top_clf = None

    # Level 2a — needs (K/G/S/B/I/Y/H/U/M/F)
    needs_clf = KeywordClassifier(
        keywords_file=str(ROOT / "classifiers" / "category_keywords.txt"),
        threshold=1,
    )

    # Level 2b — damage severity keywords
    damage_keywords = KeywordLoader.load_from_file(str(ROOT / "classifiers" / "damage" / "keywords.txt"))
    damage_clf = KeywordMatcher(damage_keywords)

    AddressExtractor.load_turkey_data(str(ROOT / "extractors" / "turkiye.json"))
    log.info("All classifiers and extractor loaded")
    return top_clf, needs_clf, damage_clf


def _classify(entry: dict, top_clf, needs_clf, damage_clf) -> dict:
    content = entry.get("content", "")

    # -- Level 1: independent binary labels H / Y / B --
    is_damage = is_need = is_info = 0
    if top_clf is not None:
        try:
            labels = top_clf.predict(content)
            is_damage = labels["H"]
            is_need   = labels["Y"]
            is_info   = labels["B"]
        except Exception as e:
            log.error("Top-level classifier error: %s", e)

    # -- Level 2a: needs (run when Y=1) --
    need_labels = None
    if is_need:
        predictions = needs_clf.predict_single(content)
        if predictions:
            need_labels = [p["category"] for p in predictions]

    # -- Level 2b: damage keywords (run when H=1) --
    damage_keywords_found = None
    if is_damage:
        matched = damage_clf.get_matched_keywords(content)
        if matched:
            damage_keywords_found = matched

    # -- Extractor: address (run when any positive label) --
    extracted_address = None
    if is_damage or is_need or is_info:
        try:
            result = AddressExtractor.extract_address(content)
            if result != "ADDRESS NOT DETECTED":
                extracted_address = result
        except Exception:
            pass

    return {
        "is_damage":       is_damage,
        "is_need":         is_need,
        "is_info":         is_info,
        "need_labels":     json.dumps(need_labels, ensure_ascii=False) if need_labels else None,
        "damage_keywords": json.dumps(damage_keywords_found, ensure_ascii=False) if damage_keywords_found else None,
        "extracted_address": extracted_address,
    }


def entry_processor_thread(stop_event: threading.Event):
    log.info("Started")
    top_clf, needs_clf, damage_clf = _load_classifiers()
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    try:
        while not stop_event.is_set():
            try:
                batch: DiffBatch = process_queue.get(timeout=5)
            except queue.Empty:
                continue

            processed = 0
            for entry in batch.entries:
                try:
                    conn.execute(
                        """INSERT OR IGNORE INTO entries
                           (entry_id, thread_path, earthquake_id, author, timestamp, content, scraped_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (entry["id"], batch.thread_path, batch.earthquake_id,
                         entry.get("author"), entry.get("timestamp"),
                         entry.get("content"), entry.get("scraped_at")),
                    )
                    result = _classify(entry, top_clf, needs_clf, damage_clf)
                    conn.execute(
                        """INSERT OR REPLACE INTO results
                           (entry_id, is_damage, is_need, is_info,
                            need_labels, damage_keywords, extracted_address, processed_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (entry["id"],
                         result["is_damage"], result["is_need"], result["is_info"],
                         result["need_labels"], result["damage_keywords"],
                         result["extracted_address"], datetime.now().isoformat()),
                    )
                    conn.commit()
                    processed += 1
                except Exception as e:
                    log.error("Skipping entry %s: %s", entry.get("id"), e)

            log.info("Processed %d/%d entries from %s",
                     processed, len(batch.entries), batch.diff_file.name)
    finally:
        conn.close()
        log.info("DB connection closed")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    DATA_DIR.mkdir(exist_ok=True)
    SCRAPER_DATA_DIR.mkdir(exist_ok=True)

    init_db()

    registry = ThreadRegistry(REGISTRY_FILE)
    log.info("Registry loaded: %d known threads", len(registry.get_all()))

    stop_event = threading.Event()

    def _shutdown(sig, frame):
        log.info("Signal %s — initiating graceful shutdown", sig)
        stop_event.set()
        with worker_lock:
            for path, proc in worker_handles.items():
                proc.terminate()
                log.info("Sent SIGTERM to worker %s (PID %d)", path, proc.pid)

    signal.signal(signal.SIGINT,  _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    threads = [
        threading.Thread(target=detector_thread,        args=(registry, stop_event), name="Detector",       daemon=True),
        threading.Thread(target=worker_manager_thread,  args=(registry, stop_event), name="WorkerManager",  daemon=True),
        threading.Thread(target=diff_watcher_thread,    args=(registry, stop_event), name="DiffWatcher",    daemon=True),
        threading.Thread(target=entry_processor_thread, args=(stop_event,),          name="EntryProcessor", daemon=True),
    ]

    for t in threads:
        t.start()
        log.info("Thread started: %s", t.name)

    log.info("Pipeline running — Ctrl+C to stop")
    stop_event.wait()
    log.info("Stopping threads...")
    for t in threads:
        t.join(timeout=10)
    log.info("Shutdown complete")


if __name__ == "__main__":
    main()
