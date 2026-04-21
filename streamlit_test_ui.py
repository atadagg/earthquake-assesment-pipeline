import json
import os
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).parent
DB_FILE = PROJECT_ROOT / "data" / "pipeline.db"
THREAD_REGISTRY_FILE = PROJECT_ROOT / "data" / "thread_registry.json"
SCRAPERS_DIR = PROJECT_ROOT / "data" / "scrapers"


def _safe_json_loads(value: Any) -> Any:
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


@st.cache_data(show_spinner=False, ttl=2)
def load_thread_registry() -> Tuple[pd.DataFrame, Optional[str]]:
    if not THREAD_REGISTRY_FILE.exists():
        return pd.DataFrame(), f"Thread registry bulunamadı: {THREAD_REGISTRY_FILE}"

    try:
        raw = json.loads(THREAD_REGISTRY_FILE.read_text(encoding="utf-8"))
        # Beklenen yapı: {"threads": {"thread_path": {...ThreadRecord...}, ...}}
        threads = raw.get("threads") or {}
        rows = []
        for thread_path, rec in threads.items():
            if isinstance(rec, dict):
                row = {"thread_path": thread_path, **rec}
            else:
                row = {"thread_path": thread_path, "record": rec}
            rows.append(row)
        df = pd.DataFrame(rows)
        return df, None
    except Exception as e:
        return pd.DataFrame(), f"Thread registry okunamadı: {e}"


@st.cache_data(show_spinner=False, ttl=2)
def load_db_tables() -> Tuple[pd.DataFrame, pd.DataFrame, Optional[str]]:
    if not DB_FILE.exists():
        return pd.DataFrame(), pd.DataFrame(), f"DB bulunamadı: {DB_FILE}"

    try:
        con = sqlite3.connect(str(DB_FILE))
        entries = pd.read_sql_query("SELECT * FROM entries", con)
        results = pd.read_sql_query("SELECT * FROM results", con)
        con.close()
        return entries, results, None
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame(), f"DB okunamadı: {e}"


def join_entries_results(entries: pd.DataFrame, results: pd.DataFrame) -> pd.DataFrame:
    if entries.empty and results.empty:
        return pd.DataFrame()
    if results.empty:
        return entries.copy()
    if entries.empty:
        return results.copy()
    df = entries.merge(results, on="entry_id", how="left", suffixes=("", "_r"))

    for col in ("need_labels", "damage_keywords"):
        if col in df.columns:
            df[col] = df[col].apply(_safe_json_loads)

    return df


@st.cache_resource(show_spinner=False)
def load_runtime_components():
    """
    Heavy imports / initializations are cached by Streamlit.
    This uses existing pipeline code (main._load_classifiers, main._classify).
    """
    import main

    top_clf, needs_clf, damage_clf = main._load_classifiers()
    return main, top_clf, needs_clf, damage_clf


def classify_entries(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    main, top_clf, needs_clf, damage_clf = load_runtime_components()
    out: List[Dict[str, Any]] = []
    for e in entries:
        r = main._classify(e, top_clf, needs_clf, damage_clf)
        out.append({**e, **r})
    return out


def scrape_url(url: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    from detector.scraper.scraper import scrape_all_pages, get_headers

    headers = get_headers()
    entries, metadata = scrape_all_pages(url, headers)
    return entries or [], metadata or {}


def render_overview(df_joined: pd.DataFrame):
    st.subheader("Genel Özet")
    if df_joined.empty:
        st.info("Henüz DB’de veri yok (veya DB okunamadı). Pipeline çalıştırıp tekrar deneyin.")
        return

    total = len(df_joined)
    h = int((df_joined.get("is_damage") == 1).sum()) if "is_damage" in df_joined.columns else 0
    y = int((df_joined.get("is_need") == 1).sum()) if "is_need" in df_joined.columns else 0
    b = int((df_joined.get("is_info") == 1).sum()) if "is_info" in df_joined.columns else 0
    addr = int(df_joined.get("extracted_address").notna().sum()) if "extracted_address" in df_joined.columns else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Toplam entry", total)
    c2.metric("Hasar (H)", h)
    c3.metric("Yardım (Y)", y)
    c4.metric("Bilgi (B)", b)
    c5.metric("Adres bulundu", addr)


def render_db_browser(df_joined: pd.DataFrame):
    st.subheader("DB Browser (entries ⨝ results)")
    if df_joined.empty:
        st.warning("Gösterilecek veri yok.")
        return

    with st.sidebar:
        st.header("Filtreler")

        eq_ids = sorted([x for x in df_joined.get("earthquake_id", pd.Series(dtype=str)).dropna().unique().tolist()])
        thread_paths = sorted([x for x in df_joined.get("thread_path", pd.Series(dtype=str)).dropna().unique().tolist()])

        sel_eq = st.multiselect("earthquake_id", options=eq_ids, default=[])
        sel_thread = st.multiselect("thread_path", options=thread_paths, default=[])

        label_filter = st.multiselect("Etiket (H/Y/B)", options=["H", "Y", "B"], default=[])
        keyword_contains = st.text_input("damage_keywords içinde ara", value="")
        need_contains = st.text_input("need_labels içinde ara", value="")
        content_contains = st.text_input("content içinde ara", value="")

        only_with_address = st.checkbox("Sadece adres bulunanlar", value=False)

        limit = st.slider("Satır limiti", min_value=50, max_value=5000, value=500, step=50)

    df = df_joined.copy()

    if sel_eq and "earthquake_id" in df.columns:
        df = df[df["earthquake_id"].isin(sel_eq)]
    if sel_thread and "thread_path" in df.columns:
        df = df[df["thread_path"].isin(sel_thread)]

    if label_filter:
        if "H" in label_filter and "is_damage" in df.columns:
            df = df[df["is_damage"] == 1]
        if "Y" in label_filter and "is_need" in df.columns:
            df = df[df["is_need"] == 1]
        if "B" in label_filter and "is_info" in df.columns:
            df = df[df["is_info"] == 1]

    if only_with_address and "extracted_address" in df.columns:
        df = df[df["extracted_address"].notna() & (df["extracted_address"].astype(str).str.strip() != "")]

    if keyword_contains and "damage_keywords" in df.columns:
        q = keyword_contains.strip().lower()
        df = df[df["damage_keywords"].astype(str).str.lower().str.contains(q, na=False)]

    if need_contains and "need_labels" in df.columns:
        q = need_contains.strip().lower()
        df = df[df["need_labels"].astype(str).str.lower().str.contains(q, na=False)]

    if content_contains and "content" in df.columns:
        q = content_contains.strip().lower()
        df = df[df["content"].astype(str).str.lower().str.contains(q, na=False)]

    st.caption(f"Filtre sonrası: {len(df)} satır")
    st.dataframe(df.head(limit), use_container_width=True, height=520)


def render_thread_registry():
    st.subheader("Thread Registry (data/thread_registry.json)")
    df, err = load_thread_registry()
    if err:
        st.warning(err)
        return
    if df.empty:
        st.info("thread_registry.json boş görünüyor.")
        return

    cols = [c for c in ["thread_path", "earthquake_id", "status", "url", "worker_pid", "data_dir", "discovered_at", "last_updated"] if c in df.columns]
    st.dataframe(df[cols].sort_values(by=[c for c in ["last_updated", "discovered_at"] if c in df.columns], ascending=False), use_container_width=True, height=420)


def render_url_tester():
    st.subheader("URL Tester (scrape + classify)")
    st.write("Ekşi başlık URL’si ver, entry’leri çekip mevcut sınıflandırıcılarla etiketleyelim.")

    url = st.text_input("Ekşi URL", value="https://eksisozluk.com/30-mart-2026-mersindeki-yaya-gecidi-kazasi--8088071")
    max_entries = st.slider("Maks entry", min_value=10, max_value=2000, value=200, step=10)
    do_classify = st.checkbox("Sınıflandır (H/Y/B + ihtiyaç + hasar keyword + adres)", value=True)

    if st.button("Çalıştır", type="primary"):
        with st.spinner("Scrape yapılıyor..."):
            entries, meta = scrape_url(url.strip())
        st.success(f"Scrape tamam: {len(entries)} entry")
        st.json(meta)

        entries = entries[:max_entries]

        if not do_classify:
            st.dataframe(pd.DataFrame(entries), use_container_width=True, height=520)
            return

        with st.spinner("Sınıflandırma yapılıyor..."):
            rows = classify_entries(entries)
        df = pd.DataFrame(rows)

        # Pretty columns
        show_cols = [c for c in ["id", "author", "timestamp", "is_damage", "is_need", "is_info", "need_labels", "damage_keywords", "extracted_address", "content"] if c in df.columns]
        st.dataframe(df[show_cols], use_container_width=True, height=520)


def render_detector_tester():
    st.subheader("Detector Pattern Tester (is_earthquake_baslik)")
    st.write("Başlıkları satır satır ver; detector eşleşmesini görelim.")

    sample = "\n".join(
        [
            "6 şubat 2023 kahramanmaraş depremi",
            "30 mart 2026 mersindeki yaya gecidi kazasi",
            "23 nisan 2026 istanbul depremi",
        ]
    )
    text = st.text_area("Başlıklar (her satır 1 başlık)", value=sample, height=140)
    if st.button("Test Et"):
        from detector.earthquake_patterns import is_earthquake_baslik

        lines = [l.strip() for l in text.splitlines() if l.strip()]
        out = []
        for t in lines:
            m = is_earthquake_baslik(t)
            out.append({"title": t, "match": bool(m), "parsed": m})
        st.dataframe(pd.DataFrame(out), use_container_width=True)


def main_app():
    st.set_page_config(page_title="Earthquake Pipeline Test UI", layout="wide")
    st.title("Earthquake Pipeline — Test Arayüzü")

    st.caption(f"Proje kökü: {PROJECT_ROOT}")
    st.caption(f"DB: {DB_FILE}")

    entries, results, db_err = load_db_tables()
    if db_err:
        st.warning(db_err)
        df_joined = pd.DataFrame()
    else:
        df_joined = join_entries_results(entries, results)

    tab_overview, tab_db, tab_threads, tab_url, tab_detector = st.tabs(
        ["Özet", "DB Browser", "Thread Registry", "URL Tester", "Detector Tester"]
    )

    with tab_overview:
        render_overview(df_joined)

    with tab_db:
        render_db_browser(df_joined)

    with tab_threads:
        render_thread_registry()

    with tab_url:
        render_url_tester()

    with tab_detector:
        render_detector_tester()

    with st.sidebar:
        st.divider()
        st.write("Güncelle")
        if st.button("Cache temizle ve yenile"):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.rerun()


if __name__ == "__main__":
    main_app()

