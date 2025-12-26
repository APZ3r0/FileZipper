
import sched
import threading
import time
from datetime import datetime, timedelta, timezone
from . import database
from . import job_manager
from .job_runner import run_job_in_thread, ConflictResolution

def run_job(job_to_run):
    """Starts a job in a new thread."""
    # The job_to_run tuple is already in the correct format.
    # We just need to extract the few values needed for the check.
    job_id, name, source_path, *_ = job_to_run

    if not os.path.exists(source_path):
        print(f"Error: Source path for job '{name}' does not exist: {source_path}")
        database.update_job_status(job_id, "Idle", datetime.now(timezone.utc).isoformat(), "Failed", None)
        return
    
    stop_event = threading.Event()
    t = threading.Thread(target=run_job_in_thread, args=(job_to_run, stop_event, ConflictResolution.RENAME))
    t.daemon = False
    t.start()


def check_and_run_jobs():
    """
    Checks for scheduled jobs that are due to run and initiates them.
    """
    print("Checking for scheduled jobs...")
    jobs = database.list_jobs()
    now = datetime.now(timezone.utc)

    for job in jobs:
        # Unpack the full 19-column tuple
        (job_id, name, _, _, _, _, _, status, _, _, _, next_run_at_iso, 
         _, _, _, _, _, _, _) = job

        if next_run_at_iso and (status is None or status.lower() == 'idle'):
            try:
                # Ensure next_run_at is timezone-aware for correct comparison
                next_run_at = datetime.fromisoformat(next_run_at_iso)
                if next_run_at.tzinfo is None:
                    next_run_at = next_run_at.replace(tzinfo=timezone.utc)
                
                if next_run_at <= now:
                    print(f"Job '{name}' is due to run. Starting job...")
                    run_job(job)
            except Exception as e:
                print(f"Error processing job '{name}' in scheduler: {e}")

def scheduler_loop(stop_event):
    """The main loop for the scheduler thread."""
    while not stop_event.is_set():
        try:
            check_and_run_jobs()
        except Exception as e:
            print(f"Error in scheduler loop: {e}")
        time.sleep(60) # Check every 60 seconds

def start_scheduler():
    """
    Starts the background scheduler in a separate thread.
    Returns the thread object and an event to stop it.
    """
    stop_event = threading.Event()
    scheduler_thread = threading.Thread(target=scheduler_loop, args=(stop_event,))
    scheduler_thread.daemon = True
    scheduler_thread.start()
    print("Scheduler started.")
    return scheduler_thread, stop_event
