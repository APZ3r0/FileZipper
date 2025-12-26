# job_manager.py

import threading

_running_jobs = {}
_lock = threading.Lock()
_listeners = []
_root = None  # To hold a reference to the main Tkinter window

# Job Statuses
STATUS_IDLE = "Idle" # For scheduled jobs not actively running
STATUS_PENDING = "Pending" # Job is queued or about to start processing
STATUS_PACKAGING = "Packaging" # Files are being zipped
STATUS_AWAITING_TRANSFER = "Awaiting Transfer" # Package ready for upload
STATUS_TRANSFERRING = "Transferring" # Upload in progress
STATUS_VERIFYING = "Verifying" # Upload verification (e.g., hash check, cloud confirmation)
STATUS_NOTIFYING_SENDER = "Notifying Sender" # Email notification being sent
STATUS_COMPLETED = "Completed" # All steps finished successfully
STATUS_FAILED = "Failed" # Job encountered an unrecoverable error

def set_root(root):
    """Set the root Tkinter window for safe after() calls."""
    global _root
    _root = root

from datetime import datetime, timezone
import os

def add_job(job_data, job_type, stop_event):
    with _lock:
        job_id = job_data.get('id', os.urandom(16).hex())
        job_data['id'] = job_id
        _running_jobs[job_id] = {
            'data': job_data,
            'type': job_type,
            'start_time': datetime.now(timezone.utc),
            'stop_event': stop_event,
            'status': STATUS_PENDING # Use the new constant
        }
    _notify_listeners()
    return job_id

def remove_job(job_id):
    with _lock:
        if job_id in _running_jobs:
            del _running_jobs[job_id]
    _notify_listeners()

def update_job_status(job_id, status):
    with _lock:
        if job_id in _running_jobs:
            _running_jobs[job_id]['status'] = status
    _notify_listeners()

def stop_job(job_id):
    with _lock:
        if job_id in _running_jobs:
            _running_jobs[job_id]['stop_event'].set()

def stop_all_jobs():
    with _lock:
        for job_id in list(_running_jobs.keys()): # Use list to avoid RuntimeError for changing dict size
            if job_id in _running_jobs:
                _running_jobs[job_id]['stop_event'].set()

def get_running_jobs():
    with _lock:
        return list(_running_jobs.values())


def add_listener(listener):
    if listener not in _listeners:
        _listeners.append(listener)

def remove_listener(listener):
    try:
        _listeners.remove(listener)
    except ValueError:
        pass # Listener already removed

def _notify_listeners():
    if not _root:
        # If no GUI root is set, call directly (for non-GUI modes, though currently unused)
        for listener in _listeners:
            try:
                listener()
            except Exception:
                # In non-GUI mode, if a listener fails, we don't want to crash the scheduler
                pass
        return

    # Schedule the listener calls on the main GUI thread
    for listener in _listeners:
        _root.after(0, listener)