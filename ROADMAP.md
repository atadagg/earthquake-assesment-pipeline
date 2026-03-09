# Roadmap — Possible Improvements

Roughly ordered by expected impact.

---

## Classification

### 1. Train BERT (Turkish) for H / Y / B
The current TF-IDF + LinearSVC classifiers achieve ~87–96% F1 depending on the label.
Dilara's notebooks (`dilarawork/Notebooks/UpdatedTamDepremBert.ipynb`) show Turkish BERT
(`dbmdz/bert-base-turkish-cased`) gains +1–3% F1 on each binary task and handles edge cases
better. The bottleneck is that training requires a GPU. Recommended path:
- Fine-tune on Google Colab (T4 is sufficient, ~15 min per binary task)
- Export with `model.save_pretrained()` and `tokenizer.save_pretrained()`
- Add a `BertTopLevelClassifier` that wraps the three saved models
- Make `TopLevelClassifier` interchangeable (same `.predict(text) → dict` interface)

### 2. Damage severity classifier (AH / ÇH)
Currently the pipeline uses a simple keyword list to flag damage severity.
Dilara's `dilarawork/Notebooks/UpdateHasarlıDepremTfidf.ipynb` trained a TF-IDF +
LogisticRegression model on the "Deprem Hasarlı Data.xlsx" dataset and achieved 87.6% accuracy
(BERT reached 90.4%). The training data is not in the repo — recover it from Colab or re-annotate.
Once available:
- Add `classifiers/severity_classifier.py` (same pattern as `top_level_classifier.py`)
- Train and save to `data/model_severity.joblib`
- In `_classify()`, call it instead of `damage_clf.get_matched_keywords()` when `is_damage=1`
- Store result as `damage_severity TEXT` (`AH` / `ÇH`) in `results`

### 3. Needs sub-classifier (K / G / S / B / I / Y / H / U / M / F)
The current needs classifier is pure keyword matching — no training required, but accuracy is
unknown and there is no evaluation. Annotation of the needs sub-labels is in progress.
Once annotation is done:
- Train a multi-label classifier (Binary Relevance + TF-IDF or BERT)
- Evaluate per-label F1, especially for rare categories (F = financial, M = communication)
- Replace `KeywordClassifier.predict_single()` with the trained model

### 4. Active learning loop
When annotation throughput is the bottleneck, use the pipeline's own output to prioritise:
- Sample entries where the model is least confident (decision function close to 0 for LinearSVC)
- Surface them to annotators first
- Retrain incrementally

---

## Infrastructure

### 5. PostgreSQL migration
The supervisor has requested a "real" database. The pipeline writes through a single
`sqlite3.connect()` call in `entry_processor_thread`. Migration steps:
- Add `psycopg2-binary` (or `asyncpg`) to `requirements.txt`
- Replace `sqlite3.connect(DB_FILE)` with a `psycopg2` connection
- Move credentials to environment variables / `.env` (add `.env` to `.gitignore`)
- Write a one-off migration script to move existing SQLite rows to Postgres
- Consider connection pooling (`psycopg2.pool`) since the processor thread is long-lived

### 6. Worker respawn for dead threads
Currently the `WorkerManager` only spawns workers for new events (threads seen for the first
time by the Detector). If a worker dies and the thread is still active on Ekşi, it is never
re-scraped. Fix: in `_reap_workers`, check if the thread is still live (e.g. posted within
the last N hours) and re-enqueue it.

### 7. WorkerManager responsiveness
The `WorkerManager` sleeps for `REAP_INTERVAL` (60 s) between queue drains. A new earthquake
thread detected by the Detector can sit in `event_queue` for up to 60 s before a worker is
spawned. Fix: replace `stop_event.wait(REAP_INTERVAL)` with a blocking `event_queue.get(timeout=REAP_INTERVAL)` so the manager wakes immediately on a new event.

### 8. Deduplication of events
If the Detector fires for the same thread twice before the WorkerManager wakes up (can happen
when `DETECTOR_INTERVAL < REAP_INTERVAL`), two workers are spawned for the same thread.
Entries are deduped by `INSERT OR IGNORE` but two redundant processes run. Fix: check
`worker_handles` before spawning.

### 9. Monitoring / alerting
- Expose a `/status` HTTP endpoint (or write a status JSON file) showing: threads tracked,
  workers alive, entries processed, last detection time
- Alert (email / Slack webhook) when no new entries are seen for > N minutes during an active
  earthquake event

---

## Data

### 10. Expand training data
The current training set (`classifiers/data.xlsx`) has 8 222 rows with no "N" (neither) class.
Dilara's "Deprem Tam Data.xlsx" has 18 628 rows including 10 397 N-class rows. Training on the
larger dataset with the N class will improve specificity (fewer false positives on background
chatter). Recover from Colab or re-export from the annotation tool.

### 11. Versioned model artefacts
Model `.joblib` files are in `data/` (gitignored). There is no record of which training data
version produced which model. Add a `data/model_manifest.json` that records training date,
data file hash, sample count, and per-label F1 at training time.
