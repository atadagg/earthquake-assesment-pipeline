# earthquake-pipeline

Real-time pipeline that monitors Ekşi Sözlük for earthquake threads, scrapes new entries,
classifies them (damage / need / both / other), extracts addresses, and stores results in SQLite.
Designed to deliver structured situational-awareness data to emergency-response teams.

---

## Architecture

```
                     ┌─────────────────────────────────────────────────────┐
                     │                     main.py                         │
                     │                                                     │
  eksisozluk.com ──► │  Thread 1: Detector        ──► event_queue         │
                     │  Thread 2: WorkerManager   ◄── event_queue         │
                     │             │ spawns subprocess per thread          │
                     │             ▼                                       │
                     │  scraper_worker.py  ──► data/scrapers/*/diffs/     │
                     │                                                     │
                     │  Thread 3: DiffWatcher     ──► process_queue       │
                     │  Thread 4: EntryProcessor  ◄── process_queue       │
                     │             │ classifies + extracts                 │
                     │             ▼                                       │
                     │          data/pipeline.db                           │
                     └─────────────────────────────────────────────────────┘
```

| Thread | Role |
|---|---|
| **Detector** | Polls `eksisozluk.com/basliklar/gundem` every 30 s; pushes new earthquake threads onto `event_queue` |
| **WorkerManager** | Spawns a `scraper_worker.py` subprocess per thread; reaps dead workers every 60 s |
| **DiffWatcher** | Scans `data/scrapers/*/diffs/` for new diff files every 10 s; pushes batches onto `process_queue` |
| **EntryProcessor** | Classifies entries (TF-IDF + keyword), extracts addresses, writes to SQLite |

---

## Installation

```bash
pip install -r requirements.txt
```

---

## First-time setup

Train the top-level classifier (H/Y/HY/B) before the first run.
The model is written to `data/toplevel_model.joblib` (gitignored, regenerate at any time):

```bash
python classifiers/top_level_classifier.py train classifiers/data.xlsx
```

Without this step the pipeline still runs — it falls back to running both L2 classifiers on
every entry, which is correct but less accurate.

---

## Running

```bash
python main.py
```

Stop with **Ctrl+C** (SIGINT) or `kill <pid>` (SIGTERM). The pipeline shuts down gracefully:
workers receive SIGTERM, the DB connection is flushed and closed, threads are joined.

---

## Data directory structure

```
data/
├── pipeline.db                   # SQLite: tables `entries` and `results`
├── thread_registry.json          # Persisted registry of known EkşiSözlük threads
└── scrapers/
    └── <thread-slug>/
        ├── state.json            # Scraper cursor state
        ├── worker.log            # Subprocess stdout/stderr
        └── diffs/
            └── diff_<ts>.json   # New-entry batches written by the worker
```

Reset state by deleting `data/` (except `data.xlsx` which lives under `classifiers/`).

---

## Classifier labels

| Classifier | Labels |
|---|---|
| Top-level | `H` damage · `Y` need · `HY` both · `B` other |
| Needs (multi-label) | `K` food · `G` clothing · `S` shelter · `B` blanket · `I` medicine · `Y` fuel · `H` rescue · `U` transport · `M` communication · `F` financial |
| Damage keywords | Matched severity keywords from `classifiers/damage/keywords.txt` |

---

## What's next

- **PostgreSQL migration** — the supervisor has requested replacing SQLite with PostgreSQL.
  The `EntryProcessor` writes through a single `sqlite3.connect()` call; swapping the driver
  and connection string is the main change required.
