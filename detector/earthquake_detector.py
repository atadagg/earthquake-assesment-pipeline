"""
Live Earthquake Detection System
Monitors Ekşi Sözlük gündem every 30 seconds for earthquake başlıks
"""
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
import json
import os
import sys
import subprocess
from pathlib import Path
from earthquake_patterns import is_earthquake_baslik

# thread_registry.py lives at the repo root (one level up from detector/).
sys.path.insert(0, str(Path(__file__).parent.parent))
from thread_registry import ThreadRegistry, ThreadStatus

# Configuration
GUNDEM_URL = "https://eksisozluk.com/basliklar/gundem"
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
POLL_INTERVAL = 30  # seconds
HEARTBEAT_INTERVAL = 2  # Log heartbeat every N fetches (120 fetches = 1 hour with 30s polling)

# Data directories
DATA_DIR = "data"
LOGS_DIR = "logs"
SCRAPER_DATA_DIR = os.path.join(DATA_DIR, "scrapers")
DETECTED_EVENTS_FILE = os.path.join(DATA_DIR, "detected_events.jsonl")
REGISTRY_FILE = os.path.join(DATA_DIR, "thread_registry.json")
GUNDEM_LOG_FILE = os.path.join(LOGS_DIR, "gundem_monitor.log")
SCRAPER_WORKER_PATH = os.path.join("scraper", "scraper_worker.py")


def setup_directories():
    """Create data and logs directories"""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)
    os.makedirs(SCRAPER_DATA_DIR, exist_ok=True)


def log_message(message: str, to_file: bool = True):
    """Log message to console and optionally to file"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] {message}"
    print(log_line)

    if to_file:
        with open(GUNDEM_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_line + '\n')


def spawn_scraper_worker(url: str, url_path: str, earthquake_id: str, registry: ThreadRegistry):
    """
    Register the thread in the central registry and spawn a scraper worker.

    Args:
        url:           Full URL (e.g. https://eksisozluk.com/deprem--123456)
        url_path:      URL path after .com/ (e.g. deprem--123456)
        earthquake_id: Identifier for the earthquake event this thread belongs to
        registry:      Shared ThreadRegistry instance
    """
    thread_path = url_path.lstrip('/')
    thread_dir = os.path.join(SCRAPER_DATA_DIR, thread_path)
    os.makedirs(thread_dir, exist_ok=True)

    state_file = os.path.join(thread_dir, "state.json")
    output_dir = os.path.join(thread_dir, "diffs")

    # Registry is the source of truth for whether a worker is already running.
    if registry.has_active_worker(thread_path):
        log_message(f"⚠️  Worker already active for {thread_path} (registry)")
        return False

    # Register the thread before spawning so the worker can update it.
    registry.register(thread_path, url, earthquake_id, thread_dir)

    try:
        proc = subprocess.Popen(
            [
                sys.executable,
                SCRAPER_WORKER_PATH,
                url,
                state_file,
                output_dir,
                REGISTRY_FILE,   # worker will update registry on lifecycle events
            ],
            stdout=open(os.path.join(thread_dir, "worker.log"), 'a'),
            stderr=subprocess.STDOUT,
        )

        log_message(f"✓ Spawned scraper worker for {thread_path} (PID {proc.pid})")
        log_message(f"   Worker output: {thread_dir}/worker.log")
        return True

    except Exception as e:
        log_message(f"❌ Failed to spawn scraper worker: {e}")
        registry.update(thread_path, status=ThreadStatus.DEAD)
        return False


def save_earthquake_event(baslik_data: dict, pattern_match: dict, earthquake_id: str, registry: ThreadRegistry):
    """Save detected earthquake event to file and spawn scraper worker"""
    event = {
        'detected_at': datetime.now().isoformat(),
        'baslik': baslik_data,
        'earthquake_info': pattern_match,
        'earthquake_id': earthquake_id
    }

    with open(DETECTED_EVENTS_FILE, 'a', encoding='utf-8') as f:
        json.dump(event, f, ensure_ascii=False)
        f.write('\n')

    log_message(f"🚨 EARTHQUAKE DETECTED: {pattern_match['day']} {pattern_match['month_name']} "
                f"{pattern_match['year']} - {pattern_match['province'].upper()}")
    log_message(f"   Başlık: {baslik_data['title']}")
    log_message(f"   URL: https://eksisozluk.com{baslik_data['url']}")
    log_message(f"   Entry count: {baslik_data['entry_count']}")
    log_message(f"   Confidence: {pattern_match['confidence']}")

    # Remove query parameters like ?a=popular before passing to scraper
    clean_url_path = baslik_data['url'].split('?')[0]
    full_url = f"https://eksisozluk.com{clean_url_path}"
    spawn_scraper_worker(full_url, clean_url_path, earthquake_id, registry)


def fetch_gundem():
    """Fetch gündem page and extract all başlıks"""
    try:
        headers = {'User-Agent': USER_AGENT}
        response = requests.get(GUNDEM_URL, headers=headers, timeout=20)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        topic_list = soup.find('ul', class_='topic-list')

        if not topic_list:
            log_message("⚠️  Could not find topic-list")
            return []

        basliks = []
        for li in topic_list.find_all('li'):
            a_tag = li.find('a')
            if a_tag and a_tag.get('href'):
                title = a_tag.get_text(strip=True)
                small_tag = a_tag.find('small')
                if small_tag:
                    entry_count = small_tag.get_text(strip=True)
                    title = title.replace(entry_count, '').strip()
                else:
                    entry_count = "0"

                url = a_tag.get('href')
                basliks.append({
                    'title': title,
                    'url': url,
                    'entry_count': entry_count,
                    'timestamp': datetime.now().isoformat()
                })

        return basliks

    except requests.exceptions.RequestException as e:
        log_message(f"❌ HTTP error: {e}")
        return []
    except Exception as e:
        log_message(f"❌ Error: {e}")
        return []


def monitor_earthquakes():
    """Main monitoring loop"""
    setup_directories()

    registry = ThreadRegistry(REGISTRY_FILE)

    log_message("=" * 50)
    log_message("    Ekşi Sözlük Earthquake Detection System STARTED")
    log_message(f"   Polling interval: {POLL_INTERVAL} seconds")
    log_message(f"   Heartbeat interval: every {HEARTBEAT_INTERVAL} fetches (~{HEARTBEAT_INTERVAL * POLL_INTERVAL // 60} minutes)")
    log_message(f"   Monitoring: {GUNDEM_URL}")
    log_message("=" * 50)

    fetch_count = 0

    while True:
        try:
            basliks = fetch_gundem()
            fetch_count += 1

            if basliks:
                # Heartbeat: log every N fetches to show system is alive
                if fetch_count % HEARTBEAT_INTERVAL == 0:
                    log_message(f"System healthy: {fetch_count} checks completed, monitoring continues...")

                # Check each başlık for earthquake pattern
                for baslik in basliks:
                    pattern_match = is_earthquake_baslik(baslik['title'])

                    if pattern_match:
                        earthquake_id = (
                            f"{pattern_match['day']}-{pattern_match['month']}-"
                            f"{pattern_match['year']}-{pattern_match['province']}"
                        )
                        clean_url_path = baslik['url'].split('?')[0]
                        thread_path = clean_url_path.lstrip('/')

                        # Registry is the source of truth — skip if already tracked.
                        if not registry.is_tracked(thread_path):
                            save_earthquake_event(baslik, pattern_match, earthquake_id, registry)

            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            log_message("=" * 80)
            log_message(f"🛑 Monitoring stopped by user (completed {fetch_count} checks)")
            log_message("=" * 80)
            break
        except Exception as e:
            log_message(f"❌ Unexpected error in main loop: {e}")
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    monitor_earthquakes()
