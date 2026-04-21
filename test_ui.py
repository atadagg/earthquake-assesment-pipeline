import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import json
import sys
from pathlib import Path
import os
import traceback

# Add project root to path securely and import necessary parts
sys.path.insert(0, str(Path(__file__).parent))
import main
from detector.scraper.scraper import scrape_all_pages, get_headers
from detector.earthquake_patterns import is_earthquake_baslik

class EarthquakeTesterUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Earthquake Pipeline Direct Tester")
        self.geometry("900x600")

        # If anything goes wrong during UI build, surface it clearly (otherwise Tk can look like a blank grey window).
        def _tk_report_callback_exception(exc, val, tb):
            print("UI ERROR (callback):", exc, val, file=sys.stderr)
            traceback.print_tb(tb)
        self.report_callback_exception = _tk_report_callback_exception

        # A small visible marker so we can confirm widgets are rendering at all.
        self._debug_label = tk.Label(self, text="UI initializing...", fg="white", bg="#444")
        self._debug_label.place(x=10, y=10)

        # macOS: make sure the window is brought to front and ttk widgets render reliably.
        # Some system Tk builds can show an empty-looking window unless we force a theme and lift.
        try:
            style = ttk.Style()
            # Prefer a theme that exists on most Tk builds.
            for candidate in ("aqua", "clam", "default"):
                if candidate in style.theme_names():
                    style.theme_use(candidate)
                    break
        except Exception:
            pass

        # Suppress Tk deprecation warning if user wants it.
        # (No-op unless env var is set; keeps behavior explicit.)
        os.environ.setdefault("TK_SILENCE_DEPRECATION", os.environ.get("TK_SILENCE_DEPRECATION", ""))
        
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

        # Force window to the front after widgets are created.
        self.after(50, self._bring_to_front)
        self.after(100, lambda: self._debug_label.config(text="UI hazır. Classifier yükleniyor..."))
        self.after(120, self._start_classifier_load)

    def _bring_to_front(self):
        try:
            self.update_idletasks()
            self.deiconify()
            self.lift()
            self.focus_force()
            # Temporarily set topmost to ensure visibility, then restore.
            self.attributes("-topmost", True)
            self.after(150, lambda: self.attributes("-topmost", False))
        except Exception:
            pass

    def _start_classifier_load(self):
        # Ensure the window paints at least once before doing heavier work.
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
        # Note: top_clf may be None if TF-IDF models are not trained yet. That's OK:
        # pipeline will still run keyword-based components.
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
        
        # Input Frame
        input_frame = ttk.Frame(tab_frame)
        input_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(input_frame, text="Ekşi Sözlük URL:").pack(side='left', padx=(0, 5))
        self.url_entry = ttk.Entry(input_frame)
        self.url_entry.pack(side='left', fill='x', expand=True, padx=5)
        self.url_entry.insert(0, "https://eksisozluk.com/30-mart-2026-mersindeki-yaya-gecidi-kazasi--8088071")
        
        self.test_btn = ttk.Button(input_frame, text="Test URL", command=self.on_test_url, state="disabled")
        self.test_btn.pack(side='right', padx=5)
        
        # Results Frame
        results_frame = ttk.Frame(tab_frame)
        results_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Aggregate Counters
        self.stats_lbl = ttk.Label(results_frame, text="Damage: 0 | Need: 0 | Info: 0 | Other: 0 | Total: 0", font=("Arial", 10, "bold"))
        self.stats_lbl.pack(anchor='w', pady=(0, 5))
        
        # Treeview to display entries
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
        
        btn_frame = ttk.Frame(tab_frame)
        btn_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(btn_frame, text="Run Detector Test", command=self.on_test_gundem).pack(side='left')
        
        self.gundem_out = scrolledtext.ScrolledText(tab_frame, height=10, state='disabled')
        self.gundem_out.pack(fill='both', expand=True, padx=5, pady=5)

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
        if not url:
            messagebox.showwarning("Warning", "Please enter a valid URL.")
            return
            
        self.test_btn.config(state='disabled')
        self.set_stats("Scraping in progress... this might take several seconds.")
        # Clear treeview
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        threading.Thread(target=self._scrape_and_classify, args=(url,), daemon=True).start()
        
    def _scrape_and_classify(self, url):
        try:
            # 1. Scrape
            headers = get_headers()
            entries, metadata = scrape_all_pages(url, headers)
            
            if not entries:
                self.after(0, lambda: self.set_stats("No entries found or scraping failed."))
                return

            counts = {"H": 0, "Y": 0, "B": 0, "Other": 0}
            
            # 2. Classify each
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
                
                self.after(0, self.log_tree, tree_vals)
            
            stats_str = f"Damage (H): {counts['H']} | Need (Y): {counts['Y']} | Info (B): {counts['B']} | Other: {counts['Other']} | Total: {len(entries)}"
            self.after(0, lambda: self.set_stats(stats_str))
            
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", f"An error occurred: {str(e)}"))
            self.after(0, lambda: self.set_stats("Error occurred."))
        finally:
            self.after(0, lambda: self.test_btn.config(state='normal'))
            
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
