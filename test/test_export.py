import unittest
import sqlite3
import tempfile
import os
import pandas as pd
from pathlib import Path
from export import export_to_excel

class TestExportToExcel(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_pipeline.db")
        self.output_path = os.path.join(self.temp_dir.name, "output.xlsx")
        
        conn = sqlite3.connect(self.db_path)
        conn.executescript("""
            CREATE TABLE entries (
                entry_id      TEXT PRIMARY KEY,
                thread_path   TEXT NOT NULL,
                earthquake_id TEXT NOT NULL,
                author        TEXT,
                timestamp     TEXT,
                content       TEXT,
                scraped_at    TEXT,
                first_seen_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE results (
                entry_id          TEXT PRIMARY KEY,
                is_damage         INTEGER,
                is_need           INTEGER,
                is_info           INTEGER,
                need_labels       TEXT,
                damage_keywords   TEXT,
                extracted_address TEXT,
                processed_at      TEXT,
                FOREIGN KEY (entry_id) REFERENCES entries(entry_id)
            );
        """)
        conn.execute(
            "INSERT INTO entries (entry_id, thread_path, earthquake_id, author, timestamp, content, scraped_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("1", "path/to/thread", "eq-1", "testuser", "2023-01-01", "Help needed here", "2023-01-01")
        )
        conn.execute(
            "INSERT INTO results (entry_id, is_damage, is_need, is_info, need_labels, damage_keywords, extracted_address, processed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("1", 1, 1, 0, '["G"]', '["yıkıldı"]', "123 Main St", "2023-01-01")
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_export_creates_file_and_valid_content(self):
        export_to_excel(self.db_path, self.output_path)
        
        self.assertTrue(os.path.exists(self.output_path))
        
        df = pd.read_excel(self.output_path)
        
        self.assertEqual(len(df), 1)
        self.assertEqual(str(df.iloc[0]["entry_id"]), "1")
        self.assertEqual(df.iloc[0]["author"], "testuser")
        self.assertEqual(df.iloc[0]["is_damage"], 1)
        self.assertEqual(df.iloc[0]["extracted_address"], "123 Main St")

if __name__ == "__main__":
    unittest.main()
