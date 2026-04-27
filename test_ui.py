# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import json
import sys
import logging
import sqlite3
from pathlib import Path
import os
import traceback
import pandas as pd
from sklearn.model_selection import train_test_split

# Add project root to path securely and import necessary parts
sys.path.insert(0, str(Path(__file__).parent))
import main
from detector.scraper.scraper import scrape_all_pages, get_headers
from detector.earthquake_patterns import is_earthquake_baslik

import queue

class WidgetLogger(logging.Handler):
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        msg = self.format(record)
        self.log_queue.put(msg)

class EarthquakeTesterUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Earthquake Pipeline Simulation Dashboard")
        self.geometry("950x700")

        def _tk_report_callback_exception(exc, val, tb):
            print("UI ERROR (callback):", exc, val, file=sys.stderr)
            traceback.print_tb(tb)
        self.report_callback_exception = _tk_report_callback_exception

        self._debug_label = tk.Label(self, text="UI initializing...", fg="white", bg="#444")
        self._debug_label.place(x=10, y=10)

        try:
            style = ttk.Style()
            for candidate in ("aqua", "clam", "default"):
                if candidate in style.theme_names():
                    style.theme_use(candidate)
                    break
        except Exception:
            pass

        os.environ.setdefault("TK_SILENCE_DEPRECATION", os.environ.get("TK_SILENCE_DEPRECATION", ""))

        self.log_queue = queue.Queue()
        self._check_log_queue()

        self.ui_task_queue = queue.Queue()
        self._check_ui_queue()
        
        # Classifiers are loaded in background to avoid a blank/grey window on macOS
        # before Tk enters the event loop.
        self.top_clf = None
        self.needs_clf = None
        self.damage_clf = None
        self.classifiers_loaded = False

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        self._build_url_tab()
        self._build_gundem_tab()
        self._build_live_pipeline_tab()
        self._build_stats_tab()
        self._build_validation_tab()

        self.after(50, self._bring_to_front)
        self.after(100, lambda: self._debug_label.config(text="UI hazır. Classifier yükleniyor..."))
        self.after(120, self._start_classifier_load)

    def _bring_to_front(self):
        try:
            self.update_idletasks()
            self.deiconify()
            self.lift()
            self.focus_force()
            self.attributes("-topmost", True)
            self.after(150, lambda: self.attributes("-topmost", False))
        except Exception:
            pass

    def _start_classifier_load(self):
        try:
            self.update_idletasks()
        except Exception:
            pass
        threading.Thread(target=self._load_classifiers_bg, daemon=True).start()

    def _load_classifiers_bg(self):
        try:
            top, needs, damage = main._load_classifiers()
            self.top_clf, self.needs_clf, self.damage_clf = top, needs, damage
            self.classifiers_loaded = True
            self.after(0, self._on_classifiers_ready)
        except Exception as e:
            self.after(0, lambda: self._on_classifiers_failed(e))

    def _on_classifiers_ready(self):
        self._debug_label.config(text="Classifier yüklendi. URL test hazır.")
        try:
            self.test_btn.config(state="normal")
        except Exception:
            pass

    def _on_classifiers_failed(self, e: Exception):
        self._debug_label.config(text="Classifier yüklenemedi (terminal loguna bak).")
        messagebox.showerror("Classifier Load Error", str(e))
        
    def _build_url_tab(self):
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="URL Tester")
        
        input_frame = ttk.Frame(tab_frame)
        input_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(input_frame, text="Ekşi Sözlük URL:").pack(side='left', padx=(0, 5))
        self.url_entry = ttk.Entry(input_frame)
        self.url_entry.pack(side='left', fill='x', expand=True, padx=5)
        self.url_entry.insert(0, "https://eksisozluk.com/9-mart-2026-denizli-depremi--8081428")
        
        self.test_btn = ttk.Button(input_frame, text="Test URL", command=self.on_test_url, state="disabled")
        self.test_btn.pack(side='right', padx=5)
        
        results_frame = ttk.Frame(tab_frame)
        results_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.stats_lbl = ttk.Label(results_frame, text="Damage: 0 | Need: 0 | Info: 0 | Other: 0 | Total: 0", font=("Arial", 10, "bold"))
        self.stats_lbl.pack(anchor='w', pady=(0, 5))
        
        columns = ("ID", "Author", "Labels", "Keywords", "Address", "Content")
        self.tree = ttk.Treeview(results_frame, columns=columns, show="headings")
        self.tree.heading("ID", text="ID")
        self.tree.heading("Author", text="Author")
        self.tree.heading("Labels", text="Labels")
        self.tree.heading("Keywords", text="Damage KWs")
        self.tree.heading("Address", text="Address Extracted")
        self.tree.heading("Content", text="Content Snippet")
        
        self.tree.column("ID", width=60, stretch=False)
        self.tree.column("Author", width=100, stretch=False)
        self.tree.column("Labels", width=80, stretch=False)
        self.tree.column("Keywords", width=120, stretch=False)
        self.tree.column("Address", width=150, stretch=False)
        self.tree.column("Content", stretch=True)
        
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

    def _build_gundem_tab(self):
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="Gündem Topic Tester")
        
        inst_lbl = ttk.Label(tab_frame, text="Paste topic titles below (one per line) to test if the Detector flags them as earthquake threads:")
        inst_lbl.pack(anchor='w', padx=5, pady=5)
        
        input_frame = ttk.Frame(tab_frame)
        input_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.topics_text = scrolledtext.ScrolledText(input_frame, height=10)
        self.topics_text.pack(fill='both', expand=True)
        default_topics = "9 mart 2026 denizli depremi\ngalatasaray fenerbahçe derbisi\n30 mart 2026 mersin depremi\niş başvurularında istenen absürt şartlar"
        self.topics_text.insert(tk.END, default_topics)
        
        btn_frame = ttk.Frame(tab_frame)
        btn_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(btn_frame, text="Run Detector Test", command=self.on_test_gundem).pack(side='left')
        
        self.gundem_out = scrolledtext.ScrolledText(tab_frame, height=10, state='disabled')
        self.gundem_out.pack(fill='both', expand=True, padx=5, pady=5)

    def _build_live_pipeline_tab(self):
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="Live Pipeline")
        
        # Pipeline Controls
        ctrl_frame = ttk.Frame(tab_frame)
        ctrl_frame.pack(fill='x', padx=5, pady=5)
        
        self.start_pipe_btn = ttk.Button(ctrl_frame, text="Start Pipeline", command=self.on_start_pipeline)
        self.start_pipe_btn.pack(side='left', padx=5)
        
        self.stop_pipe_btn = ttk.Button(ctrl_frame, text="Stop Pipeline", command=self.on_stop_pipeline, state='disabled')
        self.stop_pipe_btn.pack(side='left', padx=5)

        ttk.Separator(tab_frame, orient='horizontal').pack(fill='x', pady=5)
        
        # Injector Controls
        inj_frame = ttk.Frame(tab_frame)
        inj_frame.pack(fill='x', padx=5, pady=5)
        ttk.Label(inj_frame, text="Inject Link directly into pipeline (Overrides detector):").pack(side='left', padx=(0, 5))
        self.inject_url_entry = ttk.Entry(inj_frame)
        self.inject_url_entry.pack(side='left', fill='x', expand=True, padx=5)
        self.inject_btn = ttk.Button(inj_frame, text="Inject Now", command=self.on_inject, state='disabled')
        self.inject_btn.pack(side='right', padx=5)

        # Logging output
        self.live_log_text = scrolledtext.ScrolledText(tab_frame, height=20)
        self.live_log_text.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Tie up Python's logging module to test UI output
        self.log_handler = WidgetLogger(self.log_queue)
        self.log_handler.setFormatter(logging.Formatter("[%(asctime)s] [%(threadName)s] %(message)s", "%H:%M:%S"))
        main.log.addHandler(self.log_handler)

    def _check_log_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                if hasattr(self, 'live_log_text'):
                    self.live_log_text.insert(tk.END, msg + '\n')
                    self.live_log_text.see(tk.END)
        except queue.Empty:
            pass
        # Reschedule check every 100ms
        self.after(100, self._check_log_queue)

    def _check_ui_queue(self):
        try:
            while True:
                item = self.ui_task_queue.get_nowait()
                if len(item) == 2:
                    task, args = item
                    task(*args)
                elif len(item) == 3:
                    task, args, kwargs = item
                    task(*args, **kwargs)
        except queue.Empty:
            pass
        self.after(100, self._check_ui_queue)

    def _build_stats_tab(self):
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="Analytics & Performance")
        
        # --- Top Section: Dashboard KPIs ---
        kpi_frame = ttk.Frame(tab_frame)
        kpi_frame.pack(fill='x', padx=5, pady=10)
        
        # Throughput Frame
        thru_frame = ttk.LabelFrame(kpi_frame, text="Pipeline Throughput")
        thru_frame.pack(side='left', fill='both', expand=True, padx=5)
        self.lbl_total_scraped = ttk.Label(thru_frame, text="Total Scraped: 0", font=("Arial", 12))
        self.lbl_total_scraped.pack(anchor='w', padx=10, pady=(5, 2))
        self.lbl_total_processed = ttk.Label(thru_frame, text="Processed Results: 0", font=("Arial", 12))
        self.lbl_total_processed.pack(anchor='w', padx=10, pady=(2, 5))
        
        # Classification Distribution Frame
        dist_frame = ttk.LabelFrame(kpi_frame, text="Tag Distribution Analytics")
        dist_frame.pack(side='left', fill='both', expand=True, padx=5)
        self.lbl_dist_h = ttk.Label(dist_frame, text="Damage (H): 0", font=("Arial", 11, "bold"))
        self.lbl_dist_h.pack(anchor='w', padx=10, pady=(5, 1))
        self.lbl_dist_y = ttk.Label(dist_frame, text="Needs (Y): 0", font=("Arial", 11, "bold"))
        self.lbl_dist_y.pack(anchor='w', padx=10, pady=1)
        self.lbl_dist_b = ttk.Label(dist_frame, text="Info (B): 0", font=("Arial", 11, "bold"))
        self.lbl_dist_b.pack(anchor='w', padx=10, pady=(1, 1))
        self.lbl_dist_n = ttk.Label(dist_frame, text="None: 0", font=("Arial", 11, "bold"))
        self.lbl_dist_n.pack(anchor='w', padx=10, pady=(1, 5))
        
        # Actions Frame
        act_frame = ttk.Frame(kpi_frame)
        act_frame.pack(side='right', fill='y', padx=5)
        ttk.Button(act_frame, text="Refresh Metrics", command=self.on_refresh_stats).pack(fill='x', pady=2)
        ttk.Button(act_frame, text="Export to Excel", command=self.on_export_excel).pack(fill='x', pady=2)
        ttk.Button(act_frame, text="Clear Database", command=self.on_clear_db).pack(fill='x', pady=2)
        
        # --- Bottom Section: Live Feed ---
        ttk.Label(tab_frame, text="Real-Time Classification Feed (Latest 50 Entries):", font=("Arial", 10, "bold")).pack(anchor='w', padx=10, pady=(10, 0))

        columns = ("ID", "Date", "Labels", "Keywords", "Address", "Content")
        self.db_tree = ttk.Treeview(tab_frame, columns=columns, show="headings", height=15)
        self.db_tree.heading("ID", text="ID")
        self.db_tree.heading("Date", text="Extracted Date")
        self.db_tree.heading("Labels", text="Labels")
        self.db_tree.heading("Keywords", text="Damage KWs")
        self.db_tree.heading("Address", text="Address Extracted")
        self.db_tree.heading("Content", text="Content")
        
        self.db_tree.column("ID", width=70, stretch=False)
        self.db_tree.column("Date", width=120, stretch=False)
        self.db_tree.column("Labels", width=80, stretch=False)
        self.db_tree.column("Keywords", width=140, stretch=False)
        self.db_tree.column("Address", width=140, stretch=False)
        self.db_tree.column("Content", stretch=True)
        
        scrollbar = ttk.Scrollbar(tab_frame, orient=tk.VERTICAL, command=self.db_tree.yview)
        self.db_tree.configure(yscroll=scrollbar.set)
        
        self.db_tree.pack(side='left', fill='both', expand=True, padx=(10, 0), pady=10)
        scrollbar.pack(side='right', fill='y', padx=(0, 10), pady=10)

        self.on_refresh_stats()

    def _build_validation_tab(self):
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="Validation Benchmark")
        
        btn_frame = ttk.Frame(tab_frame)
        btn_frame.pack(fill='x', padx=5, pady=10)
        
        self.run_val_btn = ttk.Button(btn_frame, text="Benchmark General Pipeline", command=self.on_run_validation)
        self.run_val_btn.pack(side='left', padx=5)
        
        self.run_dmg_btn = ttk.Button(btn_frame, text="Benchmark Damage Lexicon", command=self.on_run_damage_validation)
        self.run_dmg_btn.pack(side='left', padx=5)
        
        self.val_status_lbl = ttk.Label(btn_frame, text="Ready.")
        self.val_status_lbl.pack(side='left', padx=10)
        
        # Metric block
        self.val_metrics_frame = ttk.Frame(tab_frame)
        self.val_metrics_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create custom label frames for H, Y, B and DMG
        self.score_labels = {}
        for label, title in [("H", "General Damage Model (H)"), ("Y", "Needs Model (Y)"), ("B", "Info Model (B)"), ("DMG", "Damage Lexical Rules (Severity Data)")]:
            lf = ttk.LabelFrame(self.val_metrics_frame, text=title)
            lf.pack(side='top', fill='x', pady=5)
            
            lbl = ttk.Label(lf, text="Accuracy: -- | Precision: -- | Recall: -- | F1-Score: --", font=("Courier", 12))
            lbl.pack(anchor='w', padx=10, pady=10)
            self.score_labels[label] = lbl

    def on_run_validation(self):
        self.run_val_btn.config(state='disabled')
        self.val_status_lbl.config(text="Loading dataset and predicting... please wait.")
        threading.Thread(target=self._run_validation_thread, daemon=True).start()

    def _run_validation_thread(self):
        try:
            excel_path = Path(__file__).parent / "classifiers" / "data.xlsx"
            df = pd.read_excel(excel_path)
            
            # Quick 10% sub-sample exactly like how we trained
            train_labels = df["AOD"].astype(str).str.strip().apply(lambda v: 1 if "H" in str(v) else 0)
            _, val_df = train_test_split(df, test_size=0.1, stratify=train_labels, random_state=42)
            
            y_true = {"H": [], "Y": [], "B": []}
            y_pred = {"H": [], "Y": [], "B": []}
            
            for _, row in val_df.iterrows():
                text = str(row["TEXT"])
                aod = str(row["AOD"])
                
                # true logic
                for L in ["H", "Y", "B"]:
                    y_true[L].append(1 if L in aod else 0)
                
                # pipeline prediction
                res = main._classify({"content": text}, self.top_clf, self.needs_clf, self.damage_clf)
                y_pred["H"].append(res["is_damage"])
                y_pred["Y"].append(res["is_need"])
                y_pred["B"].append(res["is_info"])
            
            def update_ui():
                import sklearn.metrics as metrics
                for L in ["H", "Y", "B"]:
                    t = y_true[L]
                    p = y_pred[L]
                    acc = metrics.accuracy_score(t, p)
                    prec = metrics.precision_score(t, p, zero_division=0)
                    rec = metrics.recall_score(t, p, zero_division=0)
                    f1 = metrics.f1_score(t, p, zero_division=0)
                    txt = f"Accuracy: {acc:.2%} | Precision: {prec:.4f} | Recall: {rec:.4f} | F1-Score: {f1:.4f}"
                    self.score_labels[L].config(text=txt)
                
                self.val_status_lbl.config(text=f"Completed quick test on {len(val_df)} test samples.")
                self.run_val_btn.config(state='normal')

            self.ui_task_queue.put((update_ui, []))

        except Exception as e:
            self.ui_task_queue.put((self.val_status_lbl.config, [], {"text": f"Error: {e}"}))
            self.ui_task_queue.put((self.run_val_btn.config, [], {"state": "normal"}))

    def on_run_damage_validation(self):
        self.run_dmg_btn.config(state='disabled')
        self.val_status_lbl.config(text="Loading Damage Dataset and matching keywords... please wait.")
        threading.Thread(target=self._run_damage_validation_thread, daemon=True).start()

    def _run_damage_validation_thread(self):
        try:
            excel_path = Path(__file__).parent / "classifiers" / "damage" / "Deprem_Hasarlı_Data.xlsx"
            df = pd.read_excel(excel_path)
            
            # For lexical rules, there is no training data leakage. Safe to test all rows.
            y_true = []
            y_pred = []
            
            for _, row in df.iterrows():
                text = str(row["TEXT"])
                aod = str(row["AOD"]).strip()
                if aod == 'nan': continue
                
                # True if the annotation is one of the damage severity codes (ÇH, AH, OH, HH)
                is_true_damage = 1 if aod in ["AH", "ÇH", "OH", "HH"] else 0
                y_true.append(is_true_damage)
                
                # pipeline prediction
                res = main._classify({"content": text}, self.top_clf, self.needs_clf, self.damage_clf)
                y_pred.append(res["is_damage"])
            
            def update_ui():
                import sklearn.metrics as metrics
                
                acc = metrics.accuracy_score(y_true, y_pred)
                prec = metrics.precision_score(y_true, y_pred, zero_division=0)
                rec = metrics.recall_score(y_true, y_pred, zero_division=0)
                f1 = metrics.f1_score(y_true, y_pred, zero_division=0)
                txt = f"Accuracy: {acc:.2%} | Precision: {prec:.4f} | Recall: {rec:.4f} | F1-Score: {f1:.4f}"
                self.score_labels["DMG"].config(text=txt)
                
                self.val_status_lbl.config(text=f"Completed Damage Lexicon benchmark on {len(y_true)} testing items.")
                self.run_dmg_btn.config(state='normal')

            self.ui_task_queue.put((update_ui, []))

        except Exception as e:
            self.ui_task_queue.put((self.val_status_lbl.config, [], {"text": f"Error: {e}"}))
            self.ui_task_queue.put((self.run_dmg_btn.config, [], {"state": "normal"}))

    def on_export_excel(self):
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")], initialfile="pipeline_export.xlsx")
        if not path: return
        try:
            sys.path.insert(0, str(Path(__file__).parent / "test"))
            import export
            export.export_to_excel(main.DB_FILE, path)
            messagebox.showinfo("Export Successful", f"Wrote full database to {path}")
        except Exception as e:
            messagebox.showerror("Export Failed", str(e))

    def on_clear_db(self):
        answer = messagebox.askyesno("Confirm Clear", "Are you sure you want to permanently delete ALL entries and results from the database?")
        if not answer: return
        
        try:
            conn = sqlite3.connect(main.DB_FILE)
            cur = conn.cursor()
            cur.execute("DELETE FROM results")
            cur.execute("DELETE FROM entries")
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Database cleared successfully.")
            self.on_refresh_stats()
        except Exception as e:
            messagebox.showerror("Clear Error", str(e))

    # --- Actions ---

    def on_start_pipeline(self):
        self.start_pipe_btn.config(state='disabled')
        self.stop_pipe_btn.config(state='normal')
        self.inject_btn.config(state='normal')
        
        self.pipeline_stop_event = threading.Event()
        self.pipeline_registry = main.ThreadRegistry(main.REGISTRY_FILE)
        
        self.pipeline_threads = [
            threading.Thread(target=main.detector_thread, args=(self.pipeline_registry, self.pipeline_stop_event), name="Detector", daemon=True),
            threading.Thread(target=main.worker_manager_thread, args=(self.pipeline_registry, self.pipeline_stop_event), name="WorkerManager", daemon=True),
            threading.Thread(target=main.diff_watcher_thread, args=(self.pipeline_registry, self.pipeline_stop_event), name="DiffWatcher", daemon=True),
            threading.Thread(target=main.entry_processor_thread, args=(self.pipeline_stop_event,), name="EntryProcessor", daemon=True),
        ]
        
        for t in self.pipeline_threads:
            t.start()
            
        main.log.info("UI: Live Pipeline backend daemons have successfully started.")

    def on_stop_pipeline(self):
        self.stop_pipe_btn.config(state='disabled')
        main.log.info("UI: Sending graceful stop signal to threads...")
        self.pipeline_stop_event.set()
        
        # Stop worker processes gracefully
        with main.worker_lock:
            for path, proc in main.worker_handles.items():
                proc.terminate()
                main.log.info(f"UI: Terminated subprocess worker {proc.pid}")
                
        def await_stop():
            for t in self.pipeline_threads:
                t.join(timeout=3)
            self.ui_task_queue.put((self.start_pipe_btn.config, (), {"state": "normal"}))
            self.ui_task_queue.put((self.inject_btn.config, (), {"state": "disabled"}))
            main.log.info("UI: Pipeline execution is fully stopped.")
            
        threading.Thread(target=await_stop, daemon=True).start()

    def on_inject(self):
        url = self.inject_url_entry.get().strip()
        if not url: return
        
        try:
            thread_path = url.split("eksisozluk.com/")[-1].split("?")[0].strip("/")
            event = main.EarthquakeEvent("ui-injected-event", thread_path, url)
            main.event_queue.put(event)
            main.log.info(f"UI: Pushed mock URL injection into global queue -> {thread_path}")
            self.inject_url_entry.delete(0, tk.END)
        except Exception as e:
            messagebox.showerror("Injection Error", str(e))

    def on_refresh_stats(self):
        try:
            conn = sqlite3.connect(main.DB_FILE)
            cur = conn.cursor()
            cur.execute("SELECT count(*) FROM entries")
            total_entries = cur.fetchone()[0]
            
            cur.execute("SELECT count(*) FROM results")
            total_processed = cur.fetchone()[0]
            
            cur.execute("SELECT sum(is_damage), sum(is_need), sum(is_info) FROM results")
            row = cur.fetchone()
            damage = row[0] if row[0] is not None else 0
            need = row[1] if row[1] is not None else 0
            info = row[2] if row[2] is not None else 0
            
            cur.execute("SELECT count(*) FROM results WHERE is_damage = 0 AND is_need = 0 AND is_info = 0")
            none_count = cur.fetchone()[0]
            
            self.lbl_total_scraped.config(text=f"Total Scraped: {total_entries:,}")
            self.lbl_total_processed.config(text=f"Processed Results: {total_processed:,}")
            
            self.lbl_dist_h.config(text=f"Damage (H): {damage:,}")
            self.lbl_dist_y.config(text=f"Needs (Y): {need:,}")
            self.lbl_dist_b.config(text=f"Info (B): {info:,}")
            self.lbl_dist_n.config(text=f"None: {none_count:,}")

            # Pull latest results
            for item in self.db_tree.get_children():
                self.db_tree.delete(item)
                
            cur.execute("""
                SELECT e.entry_id, e.timestamp, r.is_damage, r.is_need, r.is_info, 
                       r.damage_keywords, r.extracted_address, e.content
                FROM entries e 
                JOIN results r ON e.entry_id = r.entry_id
                ORDER BY r.processed_at DESC LIMIT 50
            """)
            for row in cur.fetchall():
                eid, ts, d, n, i, kw, addr, content = row
                labels = []
                if d: labels.append("H")
                if n: labels.append("Y")
                if i: labels.append("B")
                
                content_snip = (str(content)[:100].replace("\n", " ") + "...") if content else ""
                
                self.db_tree.insert("", tk.END, values=(
                    eid, ts, ",".join(labels), kw or "", addr or "", content_snip
                ))

            conn.close()
        except Exception as e:
            if hasattr(self, 'lbl_total_scraped'):
                self.lbl_total_scraped.config(text=f"Error reading DB: {e}")

    # --- Existing Tools Methods ---

    def log_tree(self, entry_data):
        self.tree.insert("", tk.END, values=entry_data)
        
    def out_gundem(self, msg):
        self.gundem_out.config(state='normal')
        self.gundem_out.insert(tk.END, msg + "\n")
        self.gundem_out.see(tk.END)
        self.gundem_out.config(state='disabled')

    def clear_gundem(self):
        self.gundem_out.config(state='normal')
        self.gundem_out.delete(1.0, tk.END)
        self.gundem_out.config(state='disabled')

    def set_stats(self, msg):
        self.stats_lbl.config(text=msg)

    def on_test_url(self):
        url = self.url_entry.get().strip()
        if not url: return
            
        self.test_btn.config(state='disabled')
        self.set_stats("Scraping in progress... this might take several seconds.")
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        threading.Thread(target=self._scrape_and_classify, args=(url,), daemon=True).start()
        
    def _scrape_and_classify(self, url):
        try:
            headers = get_headers()
            entries, metadata = scrape_all_pages(url, headers)
            
            if not entries:
                self.after(0, lambda: self.set_stats("No entries found or scraping failed."))
                return

            counts = {"H": 0, "Y": 0, "B": 0, "Other": 0}
            
            for entry in entries:
                if not self.classifiers_loaded or self.needs_clf is None or self.damage_clf is None:
                    raise RuntimeError("Classifier'lar henüz yüklenmedi. Lütfen biraz bekleyip tekrar deneyin.")
                result = main._classify(entry, self.top_clf, self.needs_clf, self.damage_clf)
                
                labels = []
                if result['is_damage']: 
                    labels.append('H')
                    counts["H"] += 1
                if result['is_need']: 
                    labels.append('Y')
                    counts["Y"] += 1
                if result['is_info']: 
                    labels.append('B')
                    counts["B"] += 1
                if not labels:
                    labels.append('Other')
                    counts["Other"] += 1
                    
                label_str = ",".join(labels)
                content_snip = str(entry.get('content', ''))[:100].replace("\n", " ") + "..."
                kw_str = result.get('damage_keywords') or ""
                addr_str = result.get('extracted_address') or ""
                need_lbls = result.get('need_labels') or ""
                if need_lbls:
                    kw_str += f" | Needs: {need_lbls}"
                
                tree_vals = (
                    entry.get('id', ''),
                    entry.get('author', ''),
                    label_str,
                    kw_str,
                    addr_str,
                    content_snip
                )
                
                self.ui_task_queue.put((self.log_tree, (tree_vals,)))
            
            stats_str = f"Damage (H): {counts['H']} | Need (Y): {counts['Y']} | Info (B): {counts['B']} | Other: {counts['Other']} | Total: {len(entries)}"
            self.ui_task_queue.put((self.set_stats, (stats_str,)))
            
        except Exception as e:
            self.ui_task_queue.put((messagebox.showerror, ("Error", f"An error occurred: {str(e)}")))
            self.ui_task_queue.put((self.set_stats, ("Error occurred.",)))
        finally:
            self.ui_task_queue.put((self.test_btn.config, (), {"state": "normal"}))
            
    def on_test_gundem(self):
        topics = self.topics_text.get(1.0, tk.END).strip().split('\n')
        self.clear_gundem()
        
        found = 0
        for topic in topics:
            t = topic.strip()
            if not t: continue
            
            pattern = is_earthquake_baslik(t)
            if pattern:
                found += 1
                self.out_gundem(f"[MATCH] {t}")
                self.out_gundem(f"   -> Parsed metadata: {pattern}")
            else:
                self.out_gundem(f"[IGNORE] {t}")
                
        self.out_gundem(f"\n--- Total matched: {found}/{len([t for t in topics if t.strip()])} ---")

if __name__ == "__main__":
    app = EarthquakeTesterUI()
    app.mainloop()
