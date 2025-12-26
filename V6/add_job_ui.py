import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from . import database
import os
import sqlite3
import threading
from datetime import datetime, timezone, timedelta
from . import destinations_ui
import logging
from .config_utils import load_setting # Needed for size calculations
import logging

log = logging.getLogger(__name__)

try:
    from tkcalendar import Calendar
except ImportError:
    Calendar = None

class AddJobWindow(tk.Toplevel):
    def __init__(self, parent, job_to_edit=None, refresh_callback=None):
        super().__init__(parent)
        self.title("Add Job" if job_to_edit is None else "Edit Job")
        self.geometry("600x600") # Slightly increased height for new info
        self.configure(bg="#f7f7f7")

        self.job_to_edit = job_to_edit
        self.refresh_callback = refresh_callback
        self.dest_map = {} # Will map name to {'id': id, 'location': loc, 'provider': provider}

        # --- Variables ---
        self.job_name_var = tk.StringVar()
        self.job_source_var = tk.StringVar()
        self.job_dest_name_var = tk.StringVar()
        self.job_move_files_var = tk.BooleanVar()
        self.job_schedule_var = tk.StringVar(value="Manual")
        self.job_schedule_hour_var = tk.StringVar(value="0")
        self.job_schedule_minute_var = tk.StringVar(value="0")
        self.job_schedule_date_var = tk.StringVar(value="")
        self.job_schedule_day_of_week_var = tk.StringVar()
        self.job_send_email_var = tk.BooleanVar()
        self.job_recipient_email_var = tk.StringVar()
        self.source_size_var = tk.StringVar(value="Source Size: (select folder)")
        self.dest_space_var = tk.StringVar(value="Destination Free Space: (select destination)")

        self._create_widgets()
        self._refresh_destinations()
        self._load_initial_data()
        self._update_schedule_widgets()
        
        # Initial calls to populate dynamic elements
        if self.job_source_var.get():
            threading.Thread(target=self._update_source_size_async, args=(self.job_source_var.get(),), daemon=True).start()
        if self.job_dest_name_var.get():
            threading.Thread(target=self._update_dest_space_async, args=(self.job_dest_name_var.get(),), daemon=True).start()

        self.transient(parent)
        self.grab_set()
        parent.wait_window(self)

    def _create_widgets(self):
        # --- Job Name ---
        tk.Label(self, text="Job Name:", bg="#f7f7f7").grid(row=0, column=0, padx=8, pady=8, sticky="w")
        tk.Entry(self, textvariable=self.job_name_var, width=40).grid(row=0, column=1, columnspan=2, padx=8, pady=8, sticky="ew")

        # --- Source Path ---
        tk.Label(self, text="Source Path:", bg="#f7f7f7").grid(row=1, column=0, padx=8, pady=8, sticky="w")
        tk.Entry(self, textvariable=self.job_source_var, width=40).grid(row=1, column=1, padx=8, pady=8, sticky="ew")
        tk.Button(self, text="Browse", command=self._browse_source_path).grid(row=1, column=2, padx=(0,8), pady=8)

        # --- Schedule ---
        schedule_frame = tk.LabelFrame(self, text="Schedule", bg="#f7f7f7", padx=10, pady=10)
        schedule_frame.grid(row=2, column=0, columnspan=3, padx=8, pady=8, sticky="ew")
        
        schedule_options = ["Manual", "Daily", "Hourly", "Once", "Weekly"]
        self.schedule_menu = ttk.Combobox(schedule_frame, textvariable=self.job_schedule_var, values=schedule_options, state="readonly")
        self.schedule_menu.grid(row=0, column=0, padx=5, pady=5)
        self.time_frame = tk.Frame(schedule_frame, bg="#f7f7f7")
        tk.Label(self.time_frame, text="Time (24h):", bg="#f7f7f7").pack(side=tk.LEFT)
        ttk.Spinbox(self.time_frame, from_=0, to=23, textvariable=self.job_schedule_hour_var, width=5, format="%02.0f").pack(side=tk.LEFT)
        tk.Label(self.time_frame, text=":", bg="#f7f7f7").pack(side=tk.LEFT)
        ttk.Spinbox(self.time_frame, from_=0, to=59, textvariable=self.job_schedule_minute_var, width=5, format="%02.0f").pack(side=tk.LEFT)

        self.date_frame = tk.Frame(schedule_frame, bg="#f7f7f7")
        tk.Label(self.date_frame, text="Date:", bg="#f7f7f7").pack(side=tk.LEFT)
        self.date_entry = tk.Entry(self.date_frame, textvariable=self.job_schedule_date_var)
        self.date_entry.pack(side=tk.LEFT)
        tk.Button(self.date_frame, text="...", command=self._select_date).pack(side=tk.LEFT)

        self.day_of_week_frame = tk.Frame(schedule_frame, bg="#f7f7f7")
        tk.Label(self.day_of_week_frame, text="Day of Week:", bg="#f7f7f7").pack(side=tk.LEFT)
        day_options = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        self.day_menu = ttk.Combobox(self.day_of_week_frame, textvariable=self.job_schedule_day_of_week_var, values=day_options, state="readonly")
        self.day_menu.pack(side=tk.LEFT)

        self.job_schedule_var.trace_add("write", self._update_schedule_widgets)

        # --- Destination ---
        tk.Label(self, text="Destination:", bg="#f7f7f7").grid(row=3, column=0, padx=8, pady=8, sticky="w")
        self.dest_frame = tk.Frame(self, bg="#f7f7f7")
        self.dest_frame.grid(row=3, column=1, columnspan=2, padx=8, pady=8, sticky="ew")
        self.dest_combo = ttk.Combobox(self.dest_frame, textvariable=self.job_dest_name_var, width=48, state="readonly")
        self.dest_combo.pack(side=tk.LEFT, fill="x", expand=True)
        tk.Button(self.dest_frame, text="Manage...", command=self._open_manage_destinations).pack(side=tk.LEFT, padx=(4,0))
        self.dest_combo.bind("<<ComboboxSelected>>", self._on_dest_selected)

        # --- Other Job Options ---
        tk.Checkbutton(self, text="Move Files (deletes originals after backup)", variable=self.job_move_files_var, bg="#f7f7f7").grid(row=4, column=1, padx=8, pady=8, sticky="w")

        # --- Email Notification ---
        email_frame = tk.LabelFrame(self, text="Email Notification", bg="#f7f7f7", padx=10, pady=10)
        email_frame.grid(row=5, column=0, columnspan=3, padx=8, pady=8, sticky="ew")
        tk.Checkbutton(email_frame, text="Send email on completion", variable=self.job_send_email_var, bg="#f7f7f7").pack(anchor="w")
        tk.Label(email_frame, text="Recipient Email:", bg="#f7f7f7").pack(anchor="w")
        tk.Entry(email_frame, textvariable=self.job_recipient_email_var, width=40).pack(anchor="w", fill="x")

        # --- Size Info ---
        info_frame = tk.Frame(self, bg="#f7f7f7")
        info_frame.grid(row=6, column=0, columnspan=3, padx=8, pady=4, sticky="ew")
        tk.Label(info_frame, textvariable=self.source_size_var, bg="#f7f7f7", anchor="w").pack(fill="x")
        tk.Label(info_frame, textvariable=self.dest_space_var, bg="#f7f7f7", anchor="w").pack(fill="x")

        # --- Save/Cancel Buttons ---
        tk.Button(self, text="Save Job", command=self._save_job).grid(row=7, column=1, padx=8, pady=16, sticky="e")
        
        self.grid_columnconfigure(1, weight=1)

    def _load_initial_data(self):
        if self.job_to_edit:
            (job_id, name, source, _, _, move_files, _, _, _, _, 
             schedule, _, schedule_hour, schedule_minute, schedule_date, 
             schedule_day_of_week, send_email, recipient_email, dest_id) = self.job_to_edit

            self.job_name_var.set(name)
            self.job_source_var.set(source)
            self.job_move_files_var.set(bool(move_files))
            self.job_schedule_var.set(schedule or "Manual")
            self.job_schedule_hour_var.set(str(schedule_hour or 0))
            self.job_schedule_minute_var.set(str(schedule_minute or 0))
            self.job_schedule_date_var.set(schedule_date or "")
            self.job_schedule_day_of_week_var.set(schedule_day_of_week or "")
            self.job_send_email_var.set(bool(send_email))
            self.job_recipient_email_var.set(recipient_email or "")
            
            for name, details in self.dest_map.items():
                if details['id'] == dest_id:
                    self.job_dest_name_var.set(name)
                    break

    def _refresh_destinations(self):
        destinations = database.list_destinations()
        self.dest_map.clear()
        dest_names = []
        for dest_id, name, loc, provider in destinations:
            self.dest_map[name] = {'id': dest_id, 'location': loc, 'provider': provider}
            dest_names.append(name)
        self.dest_combo['values'] = dest_names
        
        # Select the first destination if none is selected and there are options
        if not self.job_dest_name_var.get() and dest_names:
            self.job_dest_name_var.set(dest_names[0])
            self._on_dest_selected(None) # Manually trigger selection event

    def _open_manage_destinations(self):
        destinations_ui.open_destinations_window(self, refresh_callback=self._refresh_destinations)

    def _browse_source_path(self):
        import threading
        path = filedialog.askdirectory()
        if path:
            self.job_source_var.set(path)
            threading.Thread(target=self._update_source_size_async, args=(path,), daemon=True).start()

    def _update_source_size_async(self, path):
        from .utilities_ui import get_folder_size
        try:
            self.source_size_var.set("Source Size: Calculating...")
            size_bytes = get_folder_size(path)
            size_gb = size_bytes / (1024**3)
            self.source_size_var.set(f"Source Size: {size_gb:.2f} GB")
        except Exception:
            self.source_size_var.set(f"Source Size: Error calculating size.")

    def _on_dest_selected(self, event):
        import threading
        selected_dest = self.job_dest_name_var.get()
        if selected_dest:
            threading.Thread(target=self._update_dest_space_async, args=(selected_dest,), daemon=True).start()

    def _update_dest_space_async(self, dest_name):
        import shutil
        from .google_drive_connector import GoogleDriveConnector
        
        try:
            self.dest_space_var.set("Destination Free Space: Checking...")
            dest_details = self.dest_map.get(dest_name)
            if not dest_details:
                self.dest_space_var.set("Destination Free Space: Invalid")
                return

            provider = dest_details['provider']
            location = dest_details['location']
            free_space = None

            if provider == 'local':
                if os.path.exists(location):
                    _, _, free_space = shutil.disk_usage(location)
                else:
                    self.dest_space_var.set("Destination Free Space: Path does not exist")
                    return
            elif provider == 'gdrive':
                # The connector now gets its service from the auth_manager
                connector = GoogleDriveConnector()
                if not connector.is_authenticated():
                    self.dest_space_var.set(f"Destination Free Space: {connector.get_display_name()} Auth Failed")
                    return
                free_space = connector.get_free_space()
            # Placeholder for other providers like onedrive
            elif provider == 'onedrive':
                self.dest_space_var.set("Destination Free Space: OneDrive not fully implemented.")
                return

            if free_space is not None:
                free_gb = free_space / (1024**3)
                self.dest_space_var.set(f"Destination Free Space: {free_gb:.2f} GB")
            else:
                self.dest_space_var.set("Destination Free Space: Could not retrieve")

        except Exception as e:
            log.error(f"Error updating destination space for '{dest_name}': {e}", exc_info=True)
            self.dest_space_var.set(f"Destination Free Space: Error")

    def _select_date(self):
        if Calendar is None:
            messagebox.showinfo("Info", "The tkcalendar library is not installed.", parent=self)
            return
        
        def on_date_select():
            self.job_schedule_date_var.set(cal.selection_get().strftime('%Y-%m-%d'))
            top.destroy()

        top = tk.Toplevel(self)
        cal = Calendar(top, selectmode='day', date_pattern='y-mm-dd')
        cal.pack(padx=10, pady=10)
        ttk.Button(top, text="Ok", command=on_date_select).pack()

    def _update_schedule_widgets(self, *args):
        schedule_type = self.job_schedule_var.get()
        
        self.time_frame.grid_remove()
        self.date_frame.grid_remove()
        self.day_of_week_frame.grid_remove()

        if schedule_type in ["Daily", "Hourly", "Once", "Weekly"]:
            self.time_frame.grid(row=0, column=1, padx=5, pady=5)
        
        if schedule_type == "Once":
            self.date_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="w")
        
        if schedule_type == "Weekly":
            self.day_of_week_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="w")

    def _save_job(self):
        name = self.job_name_var.get().strip()
        source = self.job_source_var.get().strip()
        dest_name = self.job_dest_name_var.get().strip()

        if not name or not source or not dest_name:
            messagebox.showerror("Error", "Job Name, Source, and Destination are required.", parent=self)
            return

        dest_details = self.dest_map.get(dest_name)
        if not dest_details:
            messagebox.showerror("Error", "Invalid destination selected.", parent=self)
            return
        
        dest_id = dest_details['id']
        
        schedule = self.job_schedule_var.get()
        schedule_hour = int(self.job_schedule_hour_var.get())
        schedule_minute = int(self.job_schedule_minute_var.get())
        schedule_date = self.job_schedule_date_var.get()
        schedule_day_of_week = self.job_schedule_day_of_week_var.get()
        send_email = self.job_send_email_var.get()
        recipient_email = self.job_recipient_email_var.get().strip()

        if send_email and not recipient_email:
            messagebox.showerror("Error", "Recipient email is required when email notification is enabled.", parent=self)
            return
        if schedule == "Once" and not schedule_date:
            messagebox.showerror("Error", "Please enter a date for the 'Once' schedule.", parent=self)
            return
        if schedule == "Weekly" and not schedule_day_of_week:
            messagebox.showerror("Error", "Please select a day for the 'Weekly' schedule.", parent=self)
            return
        now = datetime.now()
        next_run_at = None
        if schedule == "Daily":
            next_run_at = (now + timedelta(days=1)).replace(hour=schedule_hour, minute=schedule_minute, second=0, microsecond=0)
        elif schedule == "Hourly":
            next_run_at = (now + timedelta(hours=1)).replace(minute=schedule_minute, second=0, microsecond=0)
        elif schedule == "Once" and schedule_date:
            local_dt = datetime.strptime(f"{schedule_date} {schedule_hour}:{schedule_minute}", "%Y-%m-%d %H:%M")
            next_run_at = local_dt.astimezone()
        elif schedule == "Weekly" and schedule_day_of_week:
            days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            current_day_of_week = now.weekday()
            target_day_of_week = days_of_week.index(schedule_day_of_week)
            days_until_next = target_day_of_week - current_day_of_week
            if days_until_next <= 0: days_until_next += 7
            next_run_at = (now + timedelta(days=days_until_next)).replace(hour=schedule_hour, minute=schedule_minute, second=0, microsecond=0)

        try:
            if self.job_to_edit:
                database.update_job(self.job_to_edit[0], name, source, dest_id, self.job_move_files_var.get(), schedule, next_run_at=next_run_at, schedule_hour=schedule_hour, schedule_minute=schedule_minute, schedule_date=schedule_date, schedule_day_of_week=schedule_day_of_week, send_email_on_completion=send_email, recipient_email=recipient_email)
            else:
                database.add_job(name, source, dest_id, self.job_move_files_var.get(), schedule, next_run_at=next_run_at, schedule_hour=schedule_hour, schedule_minute=schedule_minute, schedule_date=schedule_date, schedule_day_of_week=schedule_day_of_week, send_email_on_completion=send_email, recipient_email=recipient_email)
            
            if self.refresh_callback:
                logging.info("Calling refresh_callback to update job list.")
                self.refresh_callback()
            self.destroy()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "A job with this name already exists.", parent=self)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save job: {e}", parent=self)

def open_add_job_window(parent, job_to_edit=None, refresh_callback=None):
    try:
        AddJobWindow(parent, job_to_edit, refresh_callback)
    except Exception as e:
        messagebox.showerror("Error Opening Window", f"An unexpected error occurred while opening the Add Job window:\n\n{str(e)}")
        import traceback
        traceback.print_exc()
