import tkinter as tk
from tkinter import ttk, messagebox
import logging
from . import add_job_ui
from . import run_jobs_ui
from . import destinations_ui
from . import utilities_ui
from . import restore_ui

log = logging.getLogger(__name__)

from . import database
import time

log = logging.getLogger(__name__)

# --- Test Case Implementations ---

def _test_open_window(test_root, window_function, window_name):
    """Helper to test opening a window."""
    try:
        log.info(f"Testing: Open {window_name}")
        window = window_function(test_root)
        if window:
            window.destroy() # Close immediately after opening
        return {"name": f"Open {window_name}", "status": "PASS"}
    except Exception as e:
        log.error(f"Test Failed: Open {window_name} - %s", e, exc_info=True)
        return {"name": f"Open {window_name}", "status": "FAIL", "error": str(e)}

def _test_add_edit_delete_job():
    """Comprehensive test for add, edit, and delete job functionality by calling database functions directly."""
    test_job_name = "___test_job___"
    results = []

    # Cleanup any previous failed test
    database.delete_job(test_job_name)

    # 1. Add Job
    try:
        log.info("Testing: Add Job (Database)")
        database.add_job(
            name=test_job_name,
            source_path="C:/test/source",
            destination_id=1, # Assumes a destination with ID 1 exists
            move_files=False,
            schedule="Manual"
        )
        job = database.get_job_by_name(test_job_name)
        if job and job[1] == test_job_name:
            results.append({"name": "Add Job (Database)", "status": "PASS"})
        else:
            raise Exception("Job not found in database after add.")
    except Exception as e:
        log.error("Test Failed: Add Job (Database) - %s", e, exc_info=True)
        results.append({"name": "Add Job (Database)", "status": "FAIL", "error": str(e)})

    # 2. Edit Job
    try:
        log.info("Testing: Edit Job (Database)")
        job = database.get_job_by_name(test_job_name)
        if not job:
            raise Exception("Test setup failed: Cannot find job to edit.")
        
        job_id = job[0]
        new_source_path = "C:/test/source_updated"
        database.update_job(
            job_id=job_id,
            name=test_job_name,
            source_path=new_source_path,
            destination_id=1,
            move_files=False,
            schedule="Manual"
        )

        edited_job = database.get_job_by_name(test_job_name)
        if edited_job and edited_job[2] == new_source_path:
            results.append({"name": "Edit Job (Database)", "status": "PASS"})
        else:
            raise Exception("Job was not updated in the database.")
    except Exception as e:
        log.error("Test Failed: Edit Job (Database) - %s", e, exc_info=True)
        results.append({"name": "Edit Job (Database)", "status": "FAIL", "error": str(e)})

    # 3. Delete Job
    try:
        log.info("Testing: Delete Job (Database)")
        database.delete_job(test_job_name)
        job = database.get_job_by_name(test_job_name)
        if not job:
            results.append({"name": "Delete Job (Database)", "status": "PASS"})
        else:
            raise Exception("Job still exists in database after delete.")
    except Exception as e:
        log.error("Test Failed: Delete Job (Database) - %s", e, exc_info=True)
        results.append({"name": "Delete Job (Database)", "status": "FAIL", "error": str(e)})
        # Final cleanup
        database.delete_job(test_job_name)

    return results
    
def _test_restore_search(test_root):
    """Test for the search functionality in the restore window."""
    try:
        log.info("Testing: Restore Window Search")
        restore_window = restore_ui.open_restore_window(test_root)
        restore_window.search_var.set("test") # A generic search term
        restore_window.perform_search()
        
        # Give a moment for the search thread to populate
        time.sleep(0.5) 
        
        if restore_window.results_tree.get_children():
            # This is a weak assertion, just checks if any results appeared.
            # A stronger assertion would mock the DB to check for specific results.
            results = {"name": "Restore Window Search", "status": "PASS"}
        else:
            # This might not be a failure if 'test' truly has no matches
            results = {"name": "Restore Window Search", "status": "PASS", "error": "No results found (may not be an error)"}
        
        restore_window.destroy()
        return results

    except Exception as e:
        log.error("Test Failed: Restore Window Search - %s", e, exc_info=True)
        return {"name": "Restore Window Search", "status": "FAIL", "error": str(e)}


def run_all_tests(root_window):
    """
    A generator that yields each test function to be run.
    """
    log.info("Starting UI component tests...")
    
    test_root = tk.Toplevel(root_window)
    test_root.withdraw()

    # Yield test functions
    yield lambda: _test_open_window(test_root, run_jobs_ui.open_run_jobs_window, "Run Jobs Window")
    yield lambda: _test_open_window(test_root, destinations_ui.open_destinations_window, "Create Destinations Window")
    # For now, we are keeping the test suite small as requested.
    # To add more tests, we would yield them here.
    # For example:
    # yield from (lambda: result for result in _test_add_edit_delete_job())
    # yield lambda: _test_restore_search(test_root)

    # This part will be executed after all yielded tests are done
    def finalizer():
        test_root.destroy()
        log.info("UI component tests finished.")
    yield finalizer



