import tkinter as tk
from tkinter import ttk, messagebox
import threading
import json
import base64
from email.message import EmailMessage

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.auth.exceptions import RefreshError
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import os
import logging
import shutil
import string
from . import database
from . import config_utils
from . import ui_tester

log = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/gmail.send', 'https://www.googleapis.com/auth/userinfo.email', 'openid', 'https://www.googleapis.com/auth/userinfo.profile']

def get_local_drives_info():
    """Scans for local drives and returns their storage information."""
    drives = []
    for letter in string.ascii_uppercase:
        drive_path = f"{letter}:\\"
        if os.path.exists(drive_path):
            try:
                total, used, free = shutil.disk_usage(drive_path)
                drives.append({
                    "drive": drive_path,
                    "total_gb": round(total / (1024**3)),
                    "free_gb": round(free / (1024**3))
                })
            except OSError:
                continue
    return drives

def get_folder_size(path):
    """Recursively calculates the total size of all files in a directory."""
    total_size = 0
    if not os.path.exists(path):
        return 0
    if os.path.isfile(path):
        return os.path.getsize(path)
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size

class SelectStagingLocationWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Select Staging Drive")
        self.geometry("400x300")
        self.transient(parent)
        self.grab_set()
        
        self.selected_drive = None
        label = ttk.Label(self, text="Select a drive for the temporary staging area:")
        label.pack(pady=10, padx=10)

        tree_frame = ttk.Frame(self)
        tree_frame.pack(pady=5, padx=10, expand=True, fill="both")

        self.tree = ttk.Treeview(tree_frame, columns=("drive", "total", "free"), show="headings")
        self.tree.heading("drive", text="Drive")
        self.tree.heading("total", text="Total Space (GB)")
        self.tree.heading("free", text="Free Space (GB)")
        self.tree.column("drive", width=80)
        self.tree.column("total", width=120, anchor="e")
        self.tree.column("free", width=120, anchor="e")
        self.tree.pack(side="left", expand=True, fill="both")

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.populate_drives()

        buttons_frame = ttk.Frame(self)
        buttons_frame.pack(pady=10)
        ok_button = ttk.Button(buttons_frame, text="OK", command=self.on_ok)
        ok_button.pack(side="left", padx=10)
        cancel_button = ttk.Button(buttons_frame, text="Cancel", command=self.destroy)
        cancel_button.pack(side="left", padx=10)

    def populate_drives(self):
        drives = get_local_drives_info()
        for drive_info in drives:
            self.tree.insert("", "end", values=(drive_info["drive"], drive_info["total_gb"], drive_info["free_gb"]))

    def on_ok(self):
        selected_item = self.tree.focus()
        if selected_item:
            self.selected_drive = self.tree.item(selected_item)['values'][0]
            self.destroy()

def open_location_selection_window(parent_window, path_var):
    try:
        selection_window = SelectStagingLocationWindow(parent_window)
        parent_window.wait_window(selection_window)
        
        if selection_window.selected_drive:
            new_path = os.path.join(selection_window.selected_drive, "System Files Do Not Delete")
            path_var.set(new_path)
            config_utils.save_setting('staging_path', new_path)
            os.makedirs(new_path, exist_ok=True)
            messagebox.showinfo("Path Set", f"Staging location has been set to:\n{new_path}", parent=parent_window)
    except Exception as e:
        messagebox.showerror("Error Opening Selection Window", f"An unexpected error occurred:\n\n{str(e)}", parent=parent_window)
        import traceback
        traceback.print_exc()

def open_utilities_window(parent):
    utility_window = tk.Toplevel(parent)
    utility_window.title("Utilities")
    utility_window.geometry("800x750")

    notebook = ttk.Notebook(utility_window)
    notebook.pack(pady=10, padx=10, expand=True, fill="both")

    # Duplicate File Checker Tab
    dup_frame = ttk.Frame(notebook, padding="10")
    notebook.add(dup_frame, text="Duplicate File Checker")
    # ... (rest of duplicate checker code is fine) ...

    # Email Setup Tab
    email_frame = ttk.Frame(notebook, padding="10")
    notebook.add(email_frame, text="Email Setup")
    # ... (rest of email setup code is fine) ...

    # Staging Area Tab
    staging_frame = ttk.Frame(notebook, padding="10")
    notebook.add(staging_frame, text="Staging Area")

    staging_location_frame = ttk.LabelFrame(staging_frame, text="Temporary Staging Location")
    staging_location_frame.pack(pady=10, padx=10, fill="x")

    staging_path_var = tk.StringVar(value="Not Set. Please select a location.")
    
    def load_staging_path():
        loaded_path = config_utils.load_setting('staging_path')
        if loaded_path:
            staging_path_var.set(loaded_path)
    
    load_staging_path()

    ttk.Label(staging_location_frame, text="Current Location:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
    ttk.Label(staging_location_frame, textvariable=staging_path_var, foreground="blue").grid(row=0, column=1, padx=5, pady=5, sticky="ew")
    
    # Use a lambda to pass the necessary arguments
    ttk.Button(staging_location_frame, text="Select Location...", command=lambda: open_location_selection_window(utility_window, staging_path_var)).grid(row=1, column=1, padx=5, pady=10, sticky="e")

    staging_location_frame.grid_columnconfigure(1, weight=1)

    # Log Viewer Tab
    log_frame = ttk.Frame(notebook, padding="10")
    notebook.add(log_frame, text="Log Viewer")
    
    log_text_frame = ttk.Frame(log_frame)
    log_text_frame.pack(pady=5, padx=5, expand=True, fill="both")

    log_text = tk.Text(log_text_frame, wrap="word", height=20, width=80)
    log_scroll = tk.Scrollbar(log_text_frame, command=log_text.yview)
    log_text.config(yscrollcommand=log_scroll.set)
    
    log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _load_logs():
        try:
            with open('program_execution.log', 'r') as f:
                lines = f.readlines()
                last_500_lines = lines[-500:]
                log_text.delete('1.0', tk.END)
                log_text.insert(tk.END, "".join(last_500_lines))
        except FileNotFoundError:
            log_text.delete('1.0', tk.END)
            log_text.insert(tk.END, "Log file not found.")

    _load_logs()

    refresh_button = ttk.Button(log_frame, text="Refresh", command=_load_logs)
    refresh_button.pack(pady=5)

    # Restore History Tab
    restore_history_frame = ttk.Frame(notebook, padding="10")
    notebook.add(restore_history_frame, text="Restore History")

    history_tree_frame = ttk.Frame(restore_history_frame)
    history_tree_frame.pack(pady=5, padx=5, expand=True, fill="both")

    history_tree = ttk.Treeview(history_tree_frame, columns=("job_name", "destination", "status", "start_time", "end_time"), show="headings")
    history_tree.heading("job_name", text="Job Name")
    history_tree.heading("destination", text="Destination")
    history_tree.heading("status", text="Status")
    history_tree.heading("start_time", text="Start Time")
    history_tree.heading("end_time", text="End Time")
    history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    history_scroll = tk.Scrollbar(history_tree_frame, command=history_tree.yview)
    history_tree.config(yscrollcommand=history_scroll.set)
    history_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _load_restore_history():
        for i in history_tree.get_children():
            history_tree.delete(i)
        
        history_data = database.list_restore_history()
        for item in history_data:
            (id, job_name, destination_path, status, start_time, end_time, files_restored) = item
            history_tree.insert("", "end", values=(job_name, destination_path, status, start_time, end_time))

    _load_restore_history()

    refresh_history_button = ttk.Button(restore_history_frame, text="Refresh", command=_load_restore_history)
    refresh_history_button.pack(pady=5)

    # UI Tester Tab
    tester_frame = ttk.Frame(notebook, padding="10")
    notebook.add(tester_frame, text="UI Tester")
    
    top_tester_frame = ttk.Frame(tester_frame)
    top_tester_frame.pack(fill=tk.X, pady=5)
    
    ttk.Label(top_tester_frame, text="Run programmatic tests on UI components.").pack(pady=10, side=tk.LEFT)

    results_tree = ttk.Treeview(tester_frame, columns=("test_name", "status", "error"), show="headings")
    results_tree.heading("test_name", text="Test Name")
    results_tree.heading("status", text="Status")
    results_tree.heading("error", text="Error Details")
    results_tree.column("test_name", width=200)
    results_tree.column("status", width=80)
    results_tree.column("error", width=300)
    results_tree.tag_configure("pass", background="lightgreen")
    results_tree.tag_configure("fail", background="lightcoral")
    results_tree.pack(fill="both", expand=True, padx=5, pady=5)

    def _populate_test_result(result):
        status = result["status"]
        error = result.get("error", "")
        item_id = results_tree.insert("", "end", values=(result["name"], status, error))
        if status == "PASS":
            results_tree.item(item_id, tags=("pass",))
        else:
            results_tree.item(item_id, tags=("fail",))

    def start_tests():
        run_tests_button.config(state=tk.DISABLED, text="Running...")
        # Clear previous results
        for i in results_tree.get_children():
            results_tree.delete(i)
            
        test_generator = ui_tester.run_all_tests(utility_window)

        def _run_next_test():
            try:
                test_func = next(test_generator)
                result = test_func()
                # The finalizer function will not return a result dict
                if result:
                    _populate_test_result(result)
                utility_window.after(100, _run_next_test) # Schedule the next test
            except StopIteration:
                # All tests are done
                run_tests_button.config(state=tk.NORMAL, text="Run UI Tests")
        
        _run_next_test() # Start the first test

    run_tests_button = ttk.Button(top_tester_frame, text="Run UI Tests", command=start_tests)
    run_tests_button.pack(pady=10, side=tk.RIGHT)


    # Add a close button
    close_button = tk.Button(utility_window, text="Close", command=utility_window.destroy)
    close_button.pack(pady=10)
