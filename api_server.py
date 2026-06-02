"""
Earthquake Pipeline — FastAPI Backend

Wraps existing pipeline logic (classifiers, scraper, detector, DB) as REST API
endpoints for the React frontend. Also provides a WebSocket endpoint for
real-time pipeline log streaming.

Start with:
    uvicorn api_server:app --reload --port 8000
"""

import asyncio
import json
import logging
import os
import queue
import sqlite3
import sys
import threading
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Path setup — reuse the same path logic as main.py
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "classifiers"))
sys.path.insert(0, str(ROOT / "classifiers" / "damage"))
sys.path.insert(0, str(ROOT / "detector"))
sys.path.insert(0, str(ROOT / "extractors"))
sys.path.insert(0, str(ROOT / "need"))

import main
from detector.earthquake_patterns import is_earthquake_baslik

# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------
DB_FILE = str(ROOT / "data" / "pipeline.db")
REGISTRY_FILE = str(ROOT / "data" / "thread_registry.json")
EXPORT_DIR = ROOT / "data"

# Classifier state
_classifiers_loaded = False
_classifiers_loading = False
_top_clf = None
_needs_clf = None
_damage_clf = None

# Pipeline state
_pipeline_running = False
_pipeline_stop_event: Optional[threading.Event] = None
_pipeline_registry = None
_pipeline_threads: List[threading.Thread] = []

# WebSocket log broadcasting
_ws_clients: set = set()
_log_queue: queue.Queue = queue.Queue()


# ---------------------------------------------------------------------------
# Custom log handler that broadcasts to WebSocket clients
# ---------------------------------------------------------------------------
class WebSocketLogHandler(logging.Handler):
    def emit(self, record):
        msg = self.format(record)
        _log_queue.put(msg)


# ---------------------------------------------------------------------------
# Lifespan — load classifiers on startup
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    # Ensure data dir and DB exist
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "data" / "scrapers").mkdir(exist_ok=True)
    if Path(DB_FILE).exists():
        pass  # DB already exists
    else:
        main.init_db()

    # Start classifier loading in background
    threading.Thread(target=_load_classifiers_bg, daemon=True).start()

    # Attach log handler
    handler = WebSocketLogHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s] [%(threadName)s] %(message)s", "%H:%M:%S"))
    main.log.addHandler(handler)

    # Start log broadcaster
    _broadcast_task = asyncio.create_task(_broadcast_logs())

    yield

    # Shutdown
    _broadcast_task.cancel()
    if _pipeline_running:
        _stop_pipeline()


def _load_classifiers_bg():
    global _classifiers_loaded, _classifiers_loading, _top_clf, _needs_clf, _damage_clf
    _classifiers_loading = True
    try:
        _top_clf, _needs_clf, _damage_clf = main._load_classifiers()
        _classifiers_loaded = True
        main.log.info("API: Classifiers loaded successfully")
    except Exception as e:
        main.log.error(f"API: Failed to load classifiers: {e}")
    finally:
        _classifiers_loading = False


async def _broadcast_logs():
    """Continuously read from log queue and broadcast to WebSocket clients."""
    while True:
        try:
            # Check queue periodically
            await asyncio.sleep(0.1)
            messages = []
            while not _log_queue.empty():
                try:
                    messages.append(_log_queue.get_nowait())
                except queue.Empty:
                    break
            if messages and _ws_clients:
                data = json.dumps({"type": "logs", "messages": messages})
                dead = set()
                for ws in _ws_clients.copy():
                    try:
                        await ws.send_text(data)
                    except Exception:
                        dead.add(ws)
                _ws_clients -= dead
        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(1)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="Earthquake Pipeline API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class ScrapeRequest(BaseModel):
    url: str
    max_entries: int = 500
    classify: bool = True


class DetectRequest(BaseModel):
    titles: List[str]


class InjectRequest(BaseModel):
    url: str


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def _safe_json_loads(value):
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        try:
            return json.loads(s)
        except Exception:
            return value
    return value


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "classifiers_loaded": _classifiers_loaded,
        "classifiers_loading": _classifiers_loading,
        "pipeline_running": _pipeline_running,
    }


@app.get("/api/stats")
async def get_stats():
    try:
        conn = _get_db()
        cur = conn.cursor()

        cur.execute("SELECT count(*) FROM entries")
        total_entries = cur.fetchone()[0]

        cur.execute("SELECT count(*) FROM results")
        total_processed = cur.fetchone()[0]

        cur.execute("SELECT COALESCE(sum(is_damage),0), COALESCE(sum(is_need),0), COALESCE(sum(is_info),0) FROM results")
        row = cur.fetchone()
        damage, need, info = row[0], row[1], row[2]

        cur.execute("SELECT count(*) FROM results WHERE is_damage = 0 AND is_need = 0 AND is_info = 0")
        none_count = cur.fetchone()[0]

        cur.execute("SELECT count(DISTINCT extracted_address) FROM results WHERE extracted_address IS NOT NULL AND extracted_address != ''")
        addr_count = cur.fetchone()[0]

        conn.close()

        return {
            "total_entries": total_entries,
            "total_processed": total_processed,
            "damage": damage,
            "need": need,
            "info": info,
            "none": none_count,
            "addresses_found": addr_count,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/entries")
async def get_entries(
    earthquake_id: Optional[str] = None,
    thread_path: Optional[str] = None,
    label: Optional[str] = None,
    keyword: Optional[str] = None,
    need_label: Optional[str] = None,
    content: Optional[str] = None,
    only_address: bool = False,
    limit: int = Query(default=50, le=5000),
    offset: int = 0,
):
    try:
        conn = _get_db()
        cur = conn.cursor()

        query = """
            SELECT e.entry_id, e.thread_path, e.earthquake_id, e.author, e.timestamp,
                   e.content, e.scraped_at, e.first_seen_at,
                   r.is_damage, r.is_need, r.is_info, r.need_labels,
                   r.damage_keywords, r.extracted_address, r.processed_at
            FROM entries e
            LEFT JOIN results r ON e.entry_id = r.entry_id
            WHERE 1=1
        """
        params = []

        if earthquake_id:
            query += " AND e.earthquake_id = ?"
            params.append(earthquake_id)
        if thread_path:
            query += " AND e.thread_path = ?"
            params.append(thread_path)
        if label:
            if "H" in label:
                query += " AND r.is_damage = 1"
            if "Y" in label:
                query += " AND r.is_need = 1"
            if "B" in label:
                query += " AND r.is_info = 1"
        if keyword:
            query += " AND r.damage_keywords LIKE ?"
            params.append(f"%{keyword}%")
        if need_label:
            query += " AND r.need_labels LIKE ?"
            params.append(f"%{need_label}%")
        if content:
            query += " AND e.content LIKE ?"
            params.append(f"%{content}%")
        if only_address:
            query += " AND r.extracted_address IS NOT NULL AND r.extracted_address != ''"

        query += " ORDER BY r.processed_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cur.execute(query, params)
        rows = cur.fetchall()

        entries = []
        for row in rows:
            entry = dict(row)
            entry["need_labels"] = _safe_json_loads(entry.get("need_labels"))
            entry["damage_keywords"] = _safe_json_loads(entry.get("damage_keywords"))
            entries.append(entry)

        # Get total count for pagination
        count_query = "SELECT count(*) FROM entries e LEFT JOIN results r ON e.entry_id = r.entry_id WHERE 1=1"
        count_params = []
        if earthquake_id:
            count_query += " AND e.earthquake_id = ?"
            count_params.append(earthquake_id)
        if thread_path:
            count_query += " AND e.thread_path = ?"
            count_params.append(thread_path)

        cur.execute(count_query, count_params)
        total = cur.fetchone()[0]

        conn.close()

        return {"entries": entries, "total": total, "limit": limit, "offset": offset}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/threads")
async def get_threads():
    try:
        registry_path = Path(REGISTRY_FILE)
        if not registry_path.exists():
            return {"threads": [], "error": None}

        raw = json.loads(registry_path.read_text(encoding="utf-8"))
        # Handle both list and dict formats
        if isinstance(raw, list):
            threads = [r for r in raw if isinstance(r, dict)]
        elif isinstance(raw, dict):
            threads_dict = raw.get("threads", raw)
            if isinstance(threads_dict, dict):
                threads = [{"thread_path": k, **v} for k, v in threads_dict.items()]
            else:
                threads = threads_dict if isinstance(threads_dict, list) else []
        else:
            threads = []

        return {"threads": threads, "error": None}
    except Exception as e:
        return {"threads": [], "error": str(e)}


@app.get("/api/filters")
async def get_filter_options():
    """Return distinct earthquake_ids and thread_paths for filter dropdowns."""
    try:
        conn = _get_db()
        cur = conn.cursor()

        cur.execute("SELECT DISTINCT earthquake_id FROM entries WHERE earthquake_id IS NOT NULL ORDER BY earthquake_id")
        eq_ids = [row[0] for row in cur.fetchall()]

        cur.execute("SELECT DISTINCT thread_path FROM entries WHERE thread_path IS NOT NULL ORDER BY thread_path")
        thread_paths = [row[0] for row in cur.fetchall()]

        conn.close()
        return {"earthquake_ids": eq_ids, "thread_paths": thread_paths}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/scrape-classify")
async def scrape_and_classify(req: ScrapeRequest):
    if not _classifiers_loaded and req.classify:
        return JSONResponse(
            status_code=503,
            content={"error": "Classifier'lar henüz yükleniyor. Lütfen birkaç saniye bekleyin."},
        )

    try:
        import importlib
        import detector.scraper.scraper as scraper_module
        importlib.reload(scraper_module)
        from detector.scraper.scraper import scrape_all_pages, get_headers

        # Force-reload address extractor and main to prevent Python import caching issues
        import address_extractor
        importlib.reload(address_extractor)
        import main
        importlib.reload(main)

        headers = get_headers()
        loop = asyncio.get_event_loop()
        entries, metadata = await loop.run_in_executor(
            None, lambda: scrape_all_pages(req.url, headers, max_entries=req.max_entries)
        )

        if not entries:
            return {"entries": [], "metadata": metadata, "stats": {}}

        entries = entries[: req.max_entries]

        if not req.classify:
            return {"entries": entries, "metadata": metadata, "stats": {}}

        # Classify
        results = []
        counts = {"H": 0, "Y": 0, "B": 0, "Other": 0}

        for entry in entries:
            result = main._classify(entry, _top_clf, _needs_clf, _damage_clf)
            labels = []
            if result["is_damage"]:
                labels.append("H")
                counts["H"] += 1
            if result["is_need"]:
                labels.append("Y")
                counts["Y"] += 1
            if result["is_info"]:
                labels.append("B")
                counts["B"] += 1
            if not labels:
                labels.append("Other")
                counts["Other"] += 1

            results.append({
                **entry,
                **result,
                "labels": labels,
            })

        counts["total"] = len(entries)
        return {"entries": results, "metadata": metadata, "stats": counts}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/detect")
async def detect_patterns(req: DetectRequest):
    results = []
    for title in req.titles:
        title = title.strip()
        if not title:
            continue
        match = is_earthquake_baslik(title)
        results.append({
            "title": title,
            "matched": bool(match),
            "parsed": match,
        })
    matched_count = sum(1 for r in results if r["matched"])
    return {"results": results, "matched": matched_count, "total": len(results)}


@app.post("/api/pipeline/start")
async def start_pipeline():
    global _pipeline_running, _pipeline_stop_event, _pipeline_registry, _pipeline_threads

    if _pipeline_running:
        return {"status": "already_running"}

    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "data" / "scrapers").mkdir(exist_ok=True)
    main.init_db()

    _pipeline_stop_event = threading.Event()
    _pipeline_registry = main.ThreadRegistry(REGISTRY_FILE)

    _pipeline_threads = [
        threading.Thread(target=main.detector_thread, args=(_pipeline_registry, _pipeline_stop_event), name="Detector", daemon=True),
        threading.Thread(target=main.worker_manager_thread, args=(_pipeline_registry, _pipeline_stop_event), name="WorkerManager", daemon=True),
        threading.Thread(target=main.diff_watcher_thread, args=(_pipeline_registry, _pipeline_stop_event), name="DiffWatcher", daemon=True),
        threading.Thread(target=main.entry_processor_thread, args=(_pipeline_stop_event,), name="EntryProcessor", daemon=True),
    ]

    for t in _pipeline_threads:
        t.start()

    _pipeline_running = True
    main.log.info("API: Pipeline started via web UI")
    return {"status": "started"}


@app.post("/api/pipeline/stop")
async def stop_pipeline():
    global _pipeline_running
    if not _pipeline_running:
        return {"status": "not_running"}

    _stop_pipeline()
    return {"status": "stopped"}


def _stop_pipeline():
    global _pipeline_running
    if _pipeline_stop_event:
        _pipeline_stop_event.set()

    with main.worker_lock:
        for path, proc in main.worker_handles.items():
            try:
                proc.terminate()
            except Exception:
                pass

    for t in _pipeline_threads:
        t.join(timeout=5)

    _pipeline_running = False
    main.log.info("API: Pipeline stopped via web UI")


@app.get("/api/pipeline/status")
async def pipeline_status():
    return {
        "running": _pipeline_running,
        "classifiers_loaded": _classifiers_loaded,
        "classifiers_loading": _classifiers_loading,
    }


@app.post("/api/pipeline/inject")
async def inject_url(req: InjectRequest):
    if not _pipeline_running:
        return JSONResponse(status_code=400, content={"error": "Pipeline çalışmıyor"})

    try:
        thread_path = req.url.split("eksisozluk.com/")[-1].split("?")[0].strip("/")
        event = main.EarthquakeEvent("ui-injected-event", thread_path, req.url)
        main.event_queue.put(event)
        main.log.info(f"API: Injected URL into pipeline → {thread_path}")
        return {"status": "injected", "thread_path": thread_path}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/validate")
async def run_validation():
    if not _classifiers_loaded:
        return JSONResponse(status_code=503, content={"error": "Classifier'lar henüz yükleniyor."})

    try:
        import pandas as pd
        from sklearn.model_selection import train_test_split
        import sklearn.metrics as metrics

        loop = asyncio.get_event_loop()

        def _run():
            excel_path = ROOT / "classifiers" / "data.xlsx"
            df = pd.read_excel(excel_path)

            train_labels = df["AOD"].astype(str).str.strip().apply(lambda v: 1 if "H" in str(v) else 0)
            _, val_df = train_test_split(df, test_size=0.1, stratify=train_labels, random_state=42)

            y_true = {"H": [], "Y": [], "B": []}
            y_pred = {"H": [], "Y": [], "B": []}

            for _, row in val_df.iterrows():
                text = str(row["TEXT"])
                aod = str(row["AOD"])

                for L in ["H", "Y", "B"]:
                    y_true[L].append(1 if L in aod else 0)

                res = main._classify({"content": text}, _top_clf, _needs_clf, _damage_clf)
                y_pred["H"].append(res["is_damage"])
                y_pred["Y"].append(res["is_need"])
                y_pred["B"].append(res["is_info"])

            results = {}
            for L in ["H", "Y", "B"]:
                t, p = y_true[L], y_pred[L]
                results[L] = {
                    "accuracy": round(metrics.accuracy_score(t, p), 4),
                    "precision": round(metrics.precision_score(t, p, zero_division=0), 4),
                    "recall": round(metrics.recall_score(t, p, zero_division=0), 4),
                    "f1": round(metrics.f1_score(t, p, zero_division=0), 4),
                }

            return {"results": results, "sample_count": len(val_df)}

        result = await loop.run_in_executor(None, _run)
        return result

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/validate/damage")
async def run_damage_validation():
    if not _classifiers_loaded:
        return JSONResponse(status_code=503, content={"error": "Classifier'lar henüz yükleniyor."})

    try:
        import pandas as pd
        import sklearn.metrics as metrics

        loop = asyncio.get_event_loop()

        def _run():
            excel_path = ROOT / "classifiers" / "damage" / "Deprem_Hasarlı_Data.xlsx"
            if not excel_path.exists():
                excel_path = ROOT / "classifiers" / "damage" / "Deprem Hasarlı Data.xlsx"
            df = pd.read_excel(excel_path)

            y_true = []
            y_pred = []

            for _, row in df.iterrows():
                text = str(row["TEXT"])
                aod = str(row["AOD"]).strip()
                if aod == "nan":
                    continue

                is_true_damage = 1 if aod in ["AH", "ÇH", "OH", "HH"] else 0
                y_true.append(is_true_damage)

                res = main._classify({"content": text}, _top_clf, _needs_clf, _damage_clf)
                y_pred.append(res["is_damage"])

            return {
                "results": {
                    "DMG": {
                        "accuracy": round(metrics.accuracy_score(y_true, y_pred), 4),
                        "precision": round(metrics.precision_score(y_true, y_pred, zero_division=0), 4),
                        "recall": round(metrics.recall_score(y_true, y_pred, zero_division=0), 4),
                        "f1": round(metrics.f1_score(y_true, y_pred, zero_division=0), 4),
                    }
                },
                "sample_count": len(y_true),
            }

        result = await loop.run_in_executor(None, _run)
        return result

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/export")
async def export_excel():
    try:
        sys.path.insert(0, str(ROOT / "test"))
        import export

        output_path = str(EXPORT_DIR / "pipeline_export.xlsx")
        export.export_to_excel(DB_FILE, output_path)
        return FileResponse(output_path, filename="pipeline_export.xlsx", media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.delete("/api/clear-db")
async def clear_database():
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("DELETE FROM results")
        cur.execute("DELETE FROM entries")
        conn.commit()
        conn.close()
        return {"status": "cleared"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ---------------------------------------------------------------------------
# WebSocket for live logs
# ---------------------------------------------------------------------------
@app.websocket("/ws/logs")
async def ws_logs(websocket: WebSocket):
    await websocket.accept()
    _ws_clients.add(websocket)
    try:
        while True:
            # Keep connection alive, listen for any client messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        _ws_clients.discard(websocket)
    except Exception:
        _ws_clients.discard(websocket)
