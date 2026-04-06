import sqlite3
import pandas as pd
import logging
import argparse
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")
log = logging.getLogger(__name__)

def export_to_excel(db_path: str, output_path: str) -> None:
    """
    Export the entries and results from the SQLite database to an Excel file.
    """
    db_file = Path(db_path)
    if not db_file.exists():
        raise FileNotFoundError(f"Database file not found: {db_path}")

    query = """
        SELECT 
            e.entry_id,
            e.thread_path,
            e.earthquake_id,
            e.author,
            e.timestamp,
            e.content,
            e.scraped_at,
            e.first_seen_at,
            r.is_damage,
            r.is_need,
            r.is_info,
            r.need_labels,
            r.damage_keywords,
            r.extracted_address,
            r.processed_at
        FROM entries e
        LEFT JOIN results r ON e.entry_id = r.entry_id
    """

    try:
        log.info(f"Connecting to database at {db_path}...")
        with sqlite3.connect(db_path) as conn:
            df = pd.read_sql_query(query, conn)
            
        log.info(f"Fetched {len(df)} rows. Exporting to {output_path}...")
        df.to_excel(output_path, index=False)
        log.info("Export completed successfully.")
        
    except sqlite3.Error as e:
        log.error(f"Database error: {e}")
        raise
    except Exception as e:
        log.error(f"Error during export: {e}")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export database to Excel.")
    parser.add_argument("--db", default="data/pipeline.db", help="Path to SQLite database file")
    parser.add_argument("--out", default="data/export.xlsx", help="Path to output Excel file")
    args = parser.parse_args()
    
    export_to_excel(args.db, args.out)
