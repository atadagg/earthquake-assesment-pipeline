#!/usr/bin/env python3
"""
Scraper Worker — periodically scrapes an Ekşi Sözlük thread and writes diffs.

Shuts down when entry count reaches 0 (platform merged the thread elsewhere).
Optionally integrates with the central ThreadRegistry to report lifecycle events.

Usage:
    python scraper_worker.py <url> <state_file> <output_dir> [registry_file]
"""

import json
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

# scraper.py lives in the same directory — import its pure functions directly.
sys.path.insert(0, str(Path(__file__).parent))
from scraper import (
    scrape_all_pages,
    validate_entries,
    load_state,
    compute_diff,
    save_state_atomic,
    get_headers,
)

# thread_registry.py lives at the repo root (detector/scraper/ → detector/ → root).
_REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))
try:
    from thread_registry import ThreadRegistry, ThreadStatus
    _REGISTRY_AVAILABLE = True
except ImportError:
    _REGISTRY_AVAILABLE = False

SCRAPE_INTERVAL = 300  # seconds between scrapes


class ScraperWorker:
    def __init__(self, url: str, state_file: str, output_dir: str, registry_file: str = None):
        self.url = url
        self.state_file = state_file
        self.output_dir = output_dir
        self.consecutive_failures = 0
        self.running = True

        # Derive thread_path from URL for registry keying.
        self.thread_path = url.split("eksisozluk.com/")[-1].rstrip("/")

        # Registry is optional — worker functions correctly without it.
        self.registry: ThreadRegistry | None = None
        if registry_file and _REGISTRY_AVAILABLE:
            self.registry = ThreadRegistry(registry_file)

        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

        Path(output_dir).mkdir(parents=True, exist_ok=True)

        self.log(f"Worker started for: {url}")
        self.log(f"State file:   {state_file}")
        self.log(f"Output dir:   {output_dir}")
        self.log(f"Scrape interval: {SCRAPE_INTERVAL}s")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def log(self, message: str):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] [Worker-{os.getpid()}] {message}", flush=True)

    def _handle_shutdown(self, signum, frame):
        self.log(f"Received signal {signum}, shutting down gracefully...")
        self.running = False

    def _update_registry(self, **kwargs):
        if self.registry:
            self.registry.update(self.thread_path, **kwargs)

    # ------------------------------------------------------------------
    # Core scrape logic
    # ------------------------------------------------------------------

    def scrape_and_diff(self) -> dict | None:
        """
        Scrape the thread and compute a diff against the previous state.
        Saves updated state. Returns the diff dict, or None on failure.
        """
        headers = get_headers()
        current_entries, metadata = scrape_all_pages(self.url, headers)

        if not current_entries:
            self.log("Scraper returned no entries.")
            return None

        valid_entries, _ = validate_entries(current_entries)
        if not valid_entries:
            self.log("No valid entries after validation.")
            return None

        previous_state = load_state(self.state_file)

        if previous_state:
            diff = compute_diff(valid_entries, previous_state)
        else:
            # First run — treat all entries as new.
            diff = {
                'new': valid_entries,
                'edited': [],
                'deleted': [],
                'summary': {
                    'new_count': len(valid_entries),
                    'edited_count': 0,
                    'deleted_count': 0,
                    'total_current': len(valid_entries),
                    'total_previous': 0,
                },
            }

        save_state_atomic(valid_entries, self.state_file)
        return {**diff, 'metadata': metadata}

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self):
        self.log("Starting scraper worker loop...")
        self._update_registry(worker_pid=os.getpid(), status=ThreadStatus.ACTIVE)

        iteration = 0

        while self.running:
            iteration += 1
            self.log(f"--- Scrape iteration #{iteration} ---")

            result = self.scrape_and_diff()

            if result is None:
                self.consecutive_failures += 1
                self.log(f"Scraping failed (consecutive failures: {self.consecutive_failures}) — will retry.")
            else:
                total = result.get('summary', {}).get('total_current', -1)

                if total == 0:
                    # Platform merged this thread into another URL.
                    self.log("Entry count reached 0 — thread has been merged. Shutting down.")
                    self._update_registry(status=ThreadStatus.MERGED)
                    break

                new_count = result.get('summary', {}).get('new_count', 0)
                if new_count > 0:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    diff_file = Path(self.output_dir) / f"diff_{timestamp}.json"
                    with open(diff_file, 'w', encoding='utf-8') as f:
                        json.dump(result, f, ensure_ascii=False, indent=2)
                    self.log(f"Saved {new_count} new entries → {diff_file}")

                self.consecutive_failures = 0
                self.log(f"Thread active with {total} entries. Continuing...")

            if self.running:
                self.log(f"Sleeping {SCRAPE_INTERVAL}s until next scrape...")
                chunk = SCRAPE_INTERVAL // 10
                for _ in range(10):
                    if not self.running:
                        break
                    time.sleep(chunk)

        self.log(f"Worker shutting down after {iteration} iteration(s).")


def main():
    if len(sys.argv) < 4:
        print(
            "Usage: scraper_worker.py <url> <state_file> <output_dir> [registry_file]",
            file=sys.stderr,
        )
        sys.exit(1)

    url = sys.argv[1]
    state_file = sys.argv[2]
    output_dir = sys.argv[3]
    registry_file = sys.argv[4] if len(sys.argv) > 4 else None

    worker = ScraperWorker(url, state_file, output_dir, registry_file)
    worker.run()


if __name__ == '__main__':
    main()
