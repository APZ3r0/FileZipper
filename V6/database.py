import os
import sqlite3
from datetime import datetime, timezone, timedelta
import threading
import logging

# Set up a logger for this module
_log = logging.getLogger(__name__)

# Database (records each file added to archives)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "filezipper_records.db")

_db_lock = threading.Lock()
_connection = None

def get_connection(path: str = DB_PATH) -> sqlite3.Connection:
    """Get a thread-safe database connection."""
    global _connection
    if _connection is None:
        _log.info("Creating new database connection to %s", path)
        _connection = sqlite3.connect(path, timeout=30, check_same_thread=False)
        _connection.execute("PRAGMA journal_mode=WAL;")
    return _connection

def _init_db(path: str = DB_PATH) -> None:
    """Initializes the database schema, creating tables and adding columns if they don't exist."""
    _log.info(f"Initializing database at {path}")
    with _db_lock:
        conn = get_connection(path)
        try:
            # --- Zipped Files Table ---
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS zipped_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_path TEXT NOT NULL,
                    arcname TEXT NOT NULL,
                    zip_path TEXT NOT NULL,
                    file_size INTEGER,
                    mtime REAL,
                    compressed_size INTEGER,
                    location TEXT,
                    description TEXT,
                    recorded_at TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_arcname ON zipped_files(arcname);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_zip_path ON zipped_files(zip_path);")

            # --- Destinations Table ---
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS destinations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    location TEXT NOT NULL,
                    provider TEXT NOT NULL DEFAULT 'local'
                )
                """
            )
            
            # --- Jobs Table (Final Schema) ---
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    source_path TEXT NOT NULL,
                    destination_id INTEGER,
                    move_files INTEGER NOT NULL DEFAULT 0,
                    schedule TEXT DEFAULT 'Manual',
                    schedule_hour INTEGER DEFAULT 0,
                    schedule_minute INTEGER DEFAULT 0,
                    schedule_date TEXT,
                    schedule_day_of_week TEXT,
                    send_email_on_completion INTEGER NOT NULL DEFAULT 0,
                    recipient_email TEXT,
                    status TEXT DEFAULT 'Idle',
                    last_run_at TEXT,
                    last_run_status TEXT,
                    next_run_at TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (destination_id) REFERENCES destinations (id)
                )
                """
            )
            
            # --- Migrations for older schemas ---
            # For zipped_files table
            cur = conn.execute("PRAGMA table_info(zipped_files);")
            cols = {r[1] for r in cur.fetchall()}
            if "location" not in cols:
                conn.execute("ALTER TABLE zipped_files ADD COLUMN location TEXT;")
            if "description" not in cols:
                conn.execute("ALTER TABLE zipped_files ADD COLUMN description TEXT;")
            
            # For destinations table
            cur = conn.execute("PRAGMA table_info(destinations);")
            cols = {r[1] for r in cur.fetchall()}
            if "provider" not in cols:
                conn.execute("ALTER TABLE destinations ADD COLUMN provider TEXT NOT NULL DEFAULT 'local';")
                
            # --- Restore History Table ---
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS restore_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_name TEXT NOT NULL,
                    destination_path TEXT NOT NULL,
                    status TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    files_restored TEXT
                )
                """
            )

            conn.commit()
            _log.info("Database initialization and migration check complete.")
        except Exception as e:
            _log.error(f"Error initializing database: {e}", exc_info=True)
            pass

def _record_file(
    original_path: str,
    arcname: str,
    zip_path: str,
    file_size: int | None,
    mtime: float | None,
    compressed_size: int | None,
    location: str | None = None,
    description: str | None = None,
    path: str = DB_PATH,
) -> None:
    """Insert a file record into the DB. Best-effort; do not raise on DB errors."""
    _log.debug("Attempting to record file: %s", original_path)
    with _db_lock:
        conn = get_connection(path)
        try:
            conn.execute(
                """
                INSERT INTO zipped_files
                    (original_path, arcname, zip_path, file_size, mtime, compressed_size, location, description, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    os.path.abspath(original_path),
                    arcname,
                    os.path.abspath(zip_path),
                    file_size,
                    mtime,
                    compressed_size,
                    location,
                    description,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()
            _log.info("Successfully recorded file: %s", original_path)
        except Exception as e:
            _log.error("Failed to record file '%s': %s", original_path, e, exc_info=True)
            pass


def search_files(query: str, limit: int = 200, path: str = DB_PATH):
    """Search the DB for arcname/original_path/description substrings (case-insensitive). Returns rows including location and description."""
    _log.info("Searching files with query: '%s', limit: %d", query, limit)
    like = f"%{query}%"
    with _db_lock:
        conn = get_connection(path)
        try:
            if not query:
                cur = conn.execute(
                    """
                    SELECT original_path, arcname, zip_path, file_size, mtime, compressed_size, location, description, recorded_at
                    FROM zipped_files
                    ORDER BY recorded_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                )
            else:
                cur = conn.execute(
                    """
                    SELECT original_path, arcname, zip_path, file_size, mtime, compressed_size, location, description, recorded_at
                    FROM zipped_files
                    WHERE arcname LIKE ? OR original_path LIKE ? OR description LIKE ?
                    COLLATE NOCASE
                    ORDER BY recorded_at DESC
                    LIMIT ?
                    """,
                    (like, like, like, limit),
                )
            rows = cur.fetchall()
            _log.info("Found %d files matching query.", len(rows))
            return rows
        except Exception as e:
            _log.error("Error during file search for query '%s': %s", query, e, exc_info=True)
            return []


def add_job(
    name: str,
    source_path: str,
    destination_id: int,
    move_files: bool,
    schedule: str,
    next_run_at: datetime | None = None,
    schedule_hour: int | None = None,
    schedule_minute: int | None = None,
    schedule_date: str | None = None,
    schedule_day_of_week: str | None = None,
    send_email_on_completion: bool = False,
    recipient_email: str | None = None,
    path: str = DB_PATH,
) -> None:
    """Add a new job to the database."""
    _log.info("Adding job '%s'", name)
    with _db_lock:
        conn = get_connection(path)
        try:
            now = datetime.now(timezone.utc)
            conn.execute(
                """
                INSERT INTO jobs (name, source_path, destination_id, move_files, created_at, status, schedule, next_run_at, schedule_hour, schedule_minute, schedule_date, schedule_day_of_week, send_email_on_completion, recipient_email)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    os.path.abspath(source_path),
                    destination_id,
                    1 if move_files else 0,
                    now.isoformat(),
                    "Idle",
                    schedule,
                    next_run_at.isoformat() if next_run_at else None,
                    schedule_hour,
                    schedule_minute,
                    schedule_date,
                    schedule_day_of_week,
                    1 if send_email_on_completion else 0,
                    recipient_email,
                ),
            )
            conn.commit()
            _log.info("Successfully added job '%s'", name)
        except Exception as e:
            _log.error("Error adding job '%s': %s", name, e, exc_info=True)
            pass

def update_job(
    job_id: int,
    name: str,
    source_path: str,
    destination_id: int,
    move_files: bool,
    schedule: str,
    next_run_at: datetime | None = None,
    schedule_hour: int | None = None,
    schedule_minute: int | None = None,
    schedule_date: str | None = None,
    schedule_day_of_week: str | None = None,
    send_email_on_completion: bool = False,
    recipient_email: str | None = None,
    path: str = DB_PATH,
) -> None:
    """Update an existing job in the database."""
    _log.info("Updating job ID %d", job_id)
    with _db_lock:
        conn = get_connection(path)
        try:
            conn.execute(
                """
                UPDATE jobs 
                SET name = ?, source_path = ?, destination_id = ?, move_files = ?, schedule = ?, next_run_at = ?, schedule_hour = ?, schedule_minute = ?, schedule_date = ?, schedule_day_of_week = ?, send_email_on_completion = ?, recipient_email = ?
                WHERE id = ?
                """,
                (
                    name,
                    os.path.abspath(source_path),
                    destination_id,
                    1 if move_files else 0,
                    schedule,
                    next_run_at.isoformat() if next_run_at else None,
                    schedule_hour,
                    schedule_minute,
                    schedule_date,
                    schedule_day_of_week,
                    1 if send_email_on_completion else 0,
                    recipient_email,
                    job_id,
                ),
            )
            conn.commit()
            _log.info("Successfully updated job ID %d", job_id)
        except Exception as e:
            _log.error("Error updating job ID %d: %s", job_id, e, exc_info=True)
            pass


def update_destination(name: str, location: str, provider: str, path: str = DB_PATH) -> None:
    """Update an existing destination in the database."""
    _log.info("Updating destination '%s'", name)
    with _db_lock:
        conn = get_connection(path)
        try:
            processed_location = os.path.abspath(location) if provider == 'local' else location
            conn.execute(
                """
                UPDATE destinations 
                SET location = ?, provider = ?
                WHERE name = ?
                """,
                (processed_location, provider, name),
            )
            conn.commit()
            _log.info("Successfully updated destination '%s'", name)
        except Exception as e:
            _log.error("Error updating destination '%s': %s", name, e, exc_info=True)
            pass


def add_destination(name: str, location: str, provider: str, path: str = DB_PATH) -> None:
    """Add a new destination to the database."""
    _log.info("Adding destination '%s' at '%s' with provider '%s'", name, location, provider)
    with _db_lock:
        conn = get_connection(path)
        try:
            # For local paths, store the absolute path. For cloud, store the identifier as is.
            processed_location = os.path.abspath(location) if provider == 'local' else location
            conn.execute(
                """
                INSERT INTO destinations (name, location, provider)
                VALUES (?, ?, ?)
                """,
                (name, processed_location, provider),
            )
            conn.commit()
            _log.info("Successfully added destination '%s'", name)
        except Exception as e:
            _log.error("Error adding destination '%s': %s", name, e, exc_info=True)
            pass


def update_job_status(
    job_id: int,
    status: str,
    last_run_at: str | None,
    last_run_status: str | None,
    next_run_at: str | None = None,
    path: str = DB_PATH,
) -> None:
    """Update the status of a job."""
    _log.info("Updating status for job ID %d to '%s'", job_id, status)
    with _db_lock:
        conn = get_connection(path)
        try:
            conn.execute(
                "UPDATE jobs SET status = ?, last_run_at = ?, last_run_status = ?, next_run_at = ? WHERE id = ?",
                (status, last_run_at, last_run_status, next_run_at, job_id),
            )
            conn.commit()
            _log.info("Successfully updated status for job ID %d", job_id)
        except Exception as e:
            _log.error("Error updating status for job ID %d: %s", job_id, e, exc_info=True)
            pass



def delete_job(job_name: str, path: str = DB_PATH) -> None:
    """Delete a job from the database by name."""
    _log.info("Deleting job '%s'", job_name)
    with _db_lock:
        conn = get_connection(path)
        try:
            conn.execute("DELETE FROM jobs WHERE name = ?", (job_name,))
            conn.commit()
            _log.info("Successfully deleted job '%s'", job_name)
        except Exception as e:
            _log.error("Error deleting job '%s': %s", job_name, e, exc_info=True)
            pass


def delete_destination(name: str, path: str = DB_PATH) -> None:
    """Delete a destination from the database by name."""
    _log.info("Deleting destination '%s'", name)
    with _db_lock:
        conn = get_connection(path)
        try:
            conn.execute("DELETE FROM destinations WHERE name = ?", (name,))
            conn.commit()
            _log.info("Successfully deleted destination '%s'", name)
        except Exception as e:
            _log.error("Error deleting destination '%s': %s", name, e, exc_info=True)
            pass


def list_jobs(path: str = DB_PATH) -> list:
    """List all jobs from the database, joining with destinations to get provider info."""
    _log.info("Listing all jobs.")
    with _db_lock:
        conn = get_connection(path)
        try:
            cur = conn.execute(
                """
                SELECT 
                    j.id, j.name, j.source_path, d.location, d.provider, j.move_files, 
                    j.created_at, j.status, j.last_run_at, j.last_run_status, j.schedule, 
                    j.next_run_at, j.schedule_hour, j.schedule_minute, j.schedule_date, 
                    j.schedule_day_of_week, j.send_email_on_completion, j.recipient_email, j.destination_id
                FROM jobs j
                LEFT JOIN destinations d ON j.destination_id = d.id
                ORDER BY j.created_at DESC
                """
            )
            rows = cur.fetchall()
            _log.info("Found %d jobs.", len(rows))
            return rows
        except Exception as e:
            _log.error("Error listing jobs: %s", e, exc_info=True)
            return []


def get_job_by_name(name: str, path: str = DB_PATH):
    """Get a job from the database by name, joining with destination info."""
    _log.info("Getting job by name: '%s'", name)
    with _db_lock:
        conn = get_connection(path)
        try:
            cur = conn.execute(
                """
                SELECT 
                    j.id, j.name, j.source_path, d.location, d.provider, j.move_files, 
                    j.created_at, j.status, j.last_run_at, j.last_run_status, j.schedule, 
                    j.next_run_at, j.schedule_hour, j.schedule_minute, j.schedule_date, 
                    j.schedule_day_of_week, j.send_email_on_completion, j.recipient_email, j.destination_id
                FROM jobs j
                LEFT JOIN destinations d ON j.destination_id = d.id
                WHERE j.name = ?
                """,
                (name,),
            )
            row = cur.fetchone()
            if row:
                _log.info("Found job '%s'", name)
            else:
                _log.warning("Job '%s' not found.", name)
            return row
        except Exception as e:
            _log.error("Error getting job '%s': %s", name, e, exc_info=True)
            return None


def update_archive_remote_path(local_zip_path: str, remote_uri: str, path: str = DB_PATH):
    """Updates the zip_path for all records matching a local path to a new remote URI."""
    _log.info(f"Updating archive path from '{local_zip_path}' to '{remote_uri}'")
    with _db_lock:
        conn = get_connection(path)
        try:
            conn.execute(
                "UPDATE zipped_files SET zip_path = ? WHERE zip_path = ?",
                (remote_uri, os.path.abspath(local_zip_path))
            )
            conn.commit()
            _log.info("Successfully updated archive path.")
        except Exception as e:
            _log.error(f"Error updating archive path: {e}", exc_info=True)


def list_destinations(path: str = DB_PATH) -> list:
    """List all destinations from the database."""
    _log.info("Listing all destinations.")
    with _db_lock:
        conn = get_connection(path)
        try:
            cur = conn.execute("SELECT id, name, location, provider FROM destinations ORDER BY name")
            rows = cur.fetchall()
            _log.info("Found %d destinations.", len(rows))
            return rows
        except Exception as e:
            _log.error("Error listing destinations: %s", e, exc_info=True)
            return []

def find_duplicate_files(path: str = DB_PATH) -> dict:
    """Finds files with the same name across different zip archives."""
    _log.info("Searching for duplicate files in the database.")
    duplicates = {}
    with _db_lock:
        conn = get_connection(path)
        try:
            # First, find all arcnames that appear more than once
            cur_dups = conn.execute(
                """
                SELECT arcname, COUNT(*)
                FROM zipped_files
                GROUP BY arcname
                HAVING COUNT(*) > 1
                """
            )
            duplicate_arcnames = [row[0] for row in cur_dups.fetchall()]
            _log.info("Found %d potential duplicate filenames.", len(duplicate_arcnames))

            # For each duplicate arcname, get all the zip paths
            for arcname in duplicate_arcnames:
                cur_paths = conn.execute(
                    "SELECT zip_path FROM zipped_files WHERE arcname = ?", (arcname,)
                )
                # Use a set to store unique zip paths, then convert to a list
                locations = list(set([row[0] for row in cur_paths.fetchall()]))
                if len(locations) > 1: # Only a duplicate if in more than one location
                    duplicates[arcname] = sorted(locations)
            
            _log.info("Confirmed %d files with duplicates in different locations.", len(duplicates))
            return duplicates
        except Exception as e:
            _log.error("Error finding duplicate files: %s", e, exc_info=True)
            return {}

def add_restore_history(job_name: str, destination_path: str, start_time: str, status: str, files_restored: str, path: str = DB_PATH) -> int:
    """Add a new restore job to the history and return the new row ID."""
    _log.info("Adding restore job '%s' to history.", job_name)
    with _db_lock:
        conn = get_connection(path)
        try:
            cur = conn.execute(
                """
                INSERT INTO restore_history (job_name, destination_path, start_time, status, files_restored)
                VALUES (?, ?, ?, ?, ?)
                """,
                (job_name, destination_path, start_time, status, files_restored),
            )
            conn.commit()
            _log.info("Successfully added restore job '%s' to history.", job_name)
            return cur.lastrowid
        except Exception as e:
            _log.error("Error adding restore job '%s' to history: %s", job_name, e, exc_info=True)
            return -1

def update_restore_history(restore_id: int, end_time: str, status: str, path: str = DB_PATH) -> None:
    """Update a restore job in the history with its end time and final status."""
    _log.info("Updating restore job ID %d with status '%s'", restore_id, status)
    with _db_lock:
        conn = get_connection(path)
        try:
            conn.execute(
                "UPDATE restore_history SET end_time = ?, status = ? WHERE id = ?",
                (end_time, status, restore_id),
            )
            conn.commit()
            _log.info("Successfully updated restore job ID %d.", restore_id)
        except Exception as e:
            _log.error("Error updating restore job ID %d: %s", restore_id, e, exc_info=True)
            pass

def list_restore_history(path: str = DB_PATH) -> list:
    """List all restore jobs from the history."""
    _log.info("Listing all restore jobs from history.")
    with _db_lock:
        conn = get_connection(path)
        try:
            cur = conn.execute(
                """
                SELECT id, job_name, destination_path, status, start_time, end_time, files_restored
                FROM restore_history
                ORDER BY start_time DESC
                """
            )
            rows = cur.fetchall()
            _log.info("Found %d restore jobs in history.", len(rows))
            return rows
        except Exception as e:
            _log.error("Error listing restore history: %s", e, exc_info=True)
            return []
def get_files_in_zip_archive(zip_path: str, path: str = DB_PATH) -> list:
    """List all files recorded for a specific zip archive."""
    _log.info("Listing all files for zip archive: '%s'", zip_path)
    with _db_lock:
        conn = get_connection(path)
        try:
            cur = conn.execute(
                """
                SELECT original_path, arcname, zip_path, file_size, mtime, compressed_size, location, description, recorded_at
                FROM zipped_files
                WHERE zip_path = ?
                ORDER BY arcname ASC
                """,
                (zip_path,),
            )
            rows = cur.fetchall()
            _log.info("Found %d files in archive '%s'.", len(rows), zip_path)
            return rows
        except Exception as e:
            _log.error("Error listing files for zip archive '%s': %s", zip_path, e, exc_info=True)
            return []

