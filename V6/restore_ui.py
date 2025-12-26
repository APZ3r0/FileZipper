import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from . import database
import os
import threading
import zipfile
from .google_drive_connector import GoogleDriveConnector
from . import job_runner
from . import job_manager
from . import run_jobs_ui


class RestoreWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Search and Restore Files")
        self.geometry("1000x700")

        # Main frame
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Search frame
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill=tk.X, pady=5)

        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=60)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        search_button = ttk.Button(search_frame, text="Search", command=self.perform_search)
        search_button.pack(side=tk.LEFT)

        # Results frame
        results_frame = ttk.Labelframe(main_frame, text="Search Results", padding="10")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.results_tree = ttk.Treeview(results_frame, columns=("checked", "filename", "description", "backup_set", "arcname", "zip_path"), show="headings")
        self.results_tree.heading("checked", text="✓")
        self.results_tree.heading("filename", text="File Name")
        self.results_tree.heading("description", text="Description")
        self.results_tree.heading("backup_set", text="Backup Set")
        self.results_tree.column("checked", width=30, anchor="center", stretch=tk.NO)
        self.results_tree.column("filename", width=200, anchor="w")
        self.results_tree.column("description", width=300, anchor="w")
        self.results_tree.column("backup_set", width=200, anchor="w")
        self.results_tree.column("arcname", width=0, stretch=tk.NO) # Hidden
        self.results_tree.column("zip_path", width=0, stretch=tk.NO) # Hidden
        self.results_tree.pack(fill=tk.BOTH, expand=True)

        self.results_tree.bind("<Button-1>", self.toggle_checkbox)

        # Frame for email notification
        email_frame = ttk.Frame(main_frame)
        email_frame.pack(fill=tk.X, pady=5)
        ttk.Label(email_frame, text="Email for notification:").pack(side=tk.LEFT, padx=(0, 5))
        self.email_var = tk.StringVar()
        email_entry = ttk.Entry(email_frame, textvariable=self.email_var, width=40)
        email_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Restore Button
        restore_button = ttk.Button(main_frame, text="Restore Selected Files", command=self.restore_selected_files)
        restore_button.pack(pady=10)

    def toggle_checkbox(self, event):
        row_id = self.results_tree.identify_row(event.y)
        if not row_id:
            return
        
        current_value = self.results_tree.set(row_id, "checked")
        if current_value == "✓":
            self.results_tree.set(row_id, "checked", " ")
        else:
            self.results_tree.set(row_id, "checked", "✓")

    def perform_search(self):
        query = self.search_var.get()
        # Clear previous results
        for i in self.results_tree.get_children():
            self.results_tree.delete(i)
        
        # Run search in a thread to keep UI responsive
        threading.Thread(target=self._search_thread, args=(query,), daemon=True).start()

    def _search_thread(self, query):
        results = database.search_files(query)
        # Update UI from the main thread
        self.after(0, self._populate_results, results)

    def _populate_results(self, results):
        for row in results:
            original_path, arcname, zip_path, file_size, mtime, compressed_size, location, description, recorded_at = row
            filename = os.path.basename(arcname)
            description = description or ""
            backup_set = zip_path
            self.results_tree.insert("", "end", values=(" ", filename, description, backup_set, arcname, zip_path))

    def restore_selected_files(self):
        selected_items = []
        for item_id in self.results_tree.get_children():
            if self.results_tree.set(item_id, "checked") == "✓":
                selected_items.append(self.results_tree.item(item_id, "values"))

        if not selected_items:
            messagebox.showinfo("No Selection", "Please select files to restore.", parent=self)
            return

        destination_path = filedialog.askdirectory(title="Select Destination Folder for Restore")
        if not destination_path:
            return

        files_to_restore = []
        for values in selected_items:
            arcname = values[4]
            zip_path = values[5]
            files_to_restore.append({'arcname': arcname, 'zip_path': zip_path})

        job_data = {
            'files_to_restore': files_to_restore,
            'destination_path': destination_path,
            'name': f"Restore to {os.path.basename(destination_path)}",
            'email': self.email_var.get()
        }
        
        stop_event = threading.Event()
        # The root window is the MainMenu instance, which is the parent of this window.
        root_widget = self.master 
        
        thread = threading.Thread(target=job_runner.run_restore_job_in_thread, args=(job_data, stop_event, root_widget, None))
        thread.daemon = True
        thread.start()
        
        self.destroy() # Close the restore window
        run_jobs_ui.open_run_jobs_window(root_widget)




def open_restore_window(parent):
    RestoreWindow(parent)
