import tkinter as tk
from tkinter import messagebox, ttk
from . import database
from . import job_manager
from . import add_job_ui
from .job_runner import run_job_in_thread, ConflictResolution
from datetime import datetime, timezone, timedelta
import logging
import threading
import os

log = logging.getLogger(__name__)

def open_run_jobs_window(root):
    log.info("Opening Run Jobs window...")
    jobs_win = tk.Toplevel(root)
    jobs_win.title("Run Jobs")
    jobs_win.geometry("1200x600")

    # Title bar for station status
    title_bar = tk.Label(jobs_win, text="Station Ready Status", bg="yellow", fg="red", font=("Arial", 14, "bold"))
    title_bar.pack(padx=5, pady=(5,0), fill="x", anchor="n")

    # Main container for all status-related widgets
    main_status_frame = tk.Frame(jobs_win, bd=2, relief=tk.SOLID, bg="lightgray")
    main_status_frame.pack(padx=5, pady=5, fill="x", anchor="n")
    main_status_frame.grid_columnconfigure((0, 2, 4, 6), weight=1)  # Make status columns expandable

    # --- Status Text Row ---
    status_text_frame = tk.Frame(main_status_frame, bg="lightgray")
    status_text_frame.grid(row=0, column=0, columnspan=7, sticky="ew", padx=2, pady=2)
    status_text_frame.grid_columnconfigure((0, 2, 4, 6), weight=1)

    status_packing_label = tk.Label(status_text_frame, text="Packing: ---", bg="lightgray", font=("Arial", 10))
    status_packing_label.grid(row=0, column=0, sticky="ew")
    ttk.Separator(status_text_frame, orient='horizontal').grid(row=1, column=0, sticky="ew", pady=(0, 2))

    separator1 = ttk.Separator(status_text_frame, orient='vertical')
    separator1.grid(row=0, column=1, rowspan=2, sticky='ns', padx=10)

    status_scheduling_label = tk.Label(status_text_frame, text="Scheduling: ---", bg="lightgray", font=("Arial", 10))
    status_scheduling_label.grid(row=0, column=2, sticky="ew")
    ttk.Separator(status_text_frame, orient='horizontal').grid(row=1, column=2, sticky="ew", pady=(0, 2))

    separator2 = ttk.Separator(status_text_frame, orient='vertical')
    separator2.grid(row=0, column=3, rowspan=2, sticky='ns', padx=10)

    status_shipping_label = tk.Label(status_text_frame, text="Shipping: ---", bg="lightgray", font=("Arial", 10))
    status_shipping_label.grid(row=0, column=4, sticky="ew")
    ttk.Separator(status_text_frame, orient='horizontal').grid(row=1, column=4, sticky="ew", pady=(0, 2))

    separator3 = ttk.Separator(status_text_frame, orient='vertical')
    separator3.grid(row=0, column=5, rowspan=2, sticky='ns', padx=10)

    status_notification_label = tk.Label(status_text_frame, text="Notification Center: ---", bg="lightgray", font=("Arial", 10))
    status_notification_label.grid(row=0, column=6, sticky="ew")
    ttk.Separator(status_text_frame, orient='horizontal').grid(row=1, column=6, sticky="ew", pady=(0, 2))

    # --- Bulb Indicator Row ---
    bulb_frame = tk.Frame(main_status_frame, bg="lightgray")
    bulb_frame.grid(row=1, column=0, columnspan=7, sticky="ew", padx=2, pady=(5,2))
    bulb_frame.grid_columnconfigure((0, 2, 4, 6), weight=1)

    # Create and place bulb indicators
    bulb_size = 20
    bulb_padding = 5  # Padding around the bulb in the canvas
    
    # --- Packing Bulb ---
    canvas_packing = tk.Canvas(bulb_frame, width=bulb_size+bulb_padding, height=bulb_size+bulb_padding, bg="lightgray", highlightthickness=0)
    canvas_packing.create_oval(bulb_padding/2, bulb_padding/2, bulb_size, bulb_size, fill="grey", outline="black", width=1)
    canvas_packing.grid(row=0, column=0) # Removed sticky="ew" to allow centering

    # --- Scheduling Bulb ---
    canvas_scheduling = tk.Canvas(bulb_frame, width=bulb_size+bulb_padding, height=bulb_size+bulb_padding, bg="lightgray", highlightthickness=0)
    canvas_scheduling.create_oval(bulb_padding/2, bulb_padding/2, bulb_size, bulb_size, fill="grey", outline="black", width=1)
    canvas_scheduling.grid(row=0, column=2)

    # --- Shipping Bulb ---
    canvas_shipping = tk.Canvas(bulb_frame, width=bulb_size+bulb_padding, height=bulb_size+bulb_padding, bg="lightgray", highlightthickness=0)
    canvas_shipping.create_oval(bulb_padding/2, bulb_padding/2, bulb_size, bulb_size, fill="grey", outline="black", width=1)
    canvas_shipping.grid(row=0, column=4) # Removed sticky="ew" to allow centering

    # --- Notification Bulb ---
    canvas_notification = tk.Canvas(bulb_frame, width=bulb_size+bulb_padding, height=bulb_size+bulb_padding, bg="lightgray", highlightthickness=0)
    canvas_notification.create_oval(bulb_padding/2, bulb_padding/2, bulb_size, bulb_size, fill="grey", outline="black", width=1)
    canvas_notification.grid(row=0, column=6) # Removed sticky="ew" to allow centering

    # --- Station Status Update Logic ---
    from . import station_manager

    def _update_bulb_colors():
        """Updates the bulb colors based on the station_manager status."""
        statuses = station_manager.get_all_statuses()
        
        # Mapping of station names to their canvas and bulb item
        bulb_map = {
            station_manager.PACKING: canvas_packing,
            station_manager.SCHEDULING: canvas_scheduling,
            station_manager.SHIPPING: canvas_shipping,
            station_manager.NOTIFICATION: canvas_notification,
        }

        for station, canvas in bulb_map.items():
            color = statuses.get(station, station_manager.COLOR_GREY)
            # The oval is the first (and only) item on the canvas, so its ID is 1
            canvas.itemconfig(1, fill=color)
        log.debug("Updated bulb colors.")

    # --- End of Station Status Update Logic ---

    # Frame for Clock
    clock_frame = tk.Frame(jobs_win, bg="#f7f7f7", bd=3, relief=tk.SOLID)
    clock_frame.pack(padx=10, pady=(10,15), fill="x")
    clock_label = tk.Label(clock_frame, font=("Arial", 12), bg="#f7f7f7")
    clock_label.pack()

    jobs_win._clock_after_id = None
    def _update_clock():
        now = datetime.now()
        current_time = now.strftime("%Y-%m-%d %H:%M:%S")
        clock_label.config(text=current_time)
        jobs_win._clock_after_id = jobs_win.after(1000, _update_clock)

    _update_clock()

    # Frame for Running Jobs
    running_jobs_frame = tk.LabelFrame(jobs_win, text="Currently Running Jobs", bg="#f7f7f7", padx=10, pady=10)
    running_jobs_frame.pack(padx=10, pady=10, fill="x")

    running_cols = ("name", "status", "start_time", "elapsed_time")
    running_tree = ttk.Treeview(running_jobs_frame, columns=running_cols, show="headings", height=3)
    running_tree.heading("name", text="Job Name")
    running_tree.heading("status", text="Status")
    running_tree.heading("start_time", text="Start Time")
    running_tree.heading("elapsed_time", text="Elapsed Time")
    running_tree.column("name", width=300, anchor="w")
    running_tree.column("status", width=120, anchor="w")
    running_tree.column("start_time", width=150, anchor="w")
    running_tree.column("elapsed_time", width=150, anchor="w")
    running_tree.pack(fill="x", expand=True)

    # Define colors for job statuses
    from .job_manager import (
        STATUS_IDLE, STATUS_PENDING, STATUS_PACKAGING, STATUS_AWAITING_TRANSFER, 
        STATUS_TRANSFERRING, STATUS_VERIFYING, STATUS_NOTIFYING_SENDER, 
        STATUS_COMPLETED, STATUS_FAILED
    )

    STATUS_COLORS = {
        STATUS_IDLE: '#E0E0E0',       # Light Gray
        STATUS_PENDING: '#FFFFCC',    # Light Yellow
        STATUS_PACKAGING: '#ADD8E6',  # Light Blue
        STATUS_AWAITING_TRANSFER: '#FFDDC1', # Light Orange
        STATUS_TRANSFERRING: '#90EE90', # Light Green
        STATUS_VERIFYING: '#AFEEEE',  # Pale Turquoise
        STATUS_NOTIFYING_SENDER: '#DDA0DD', # Plum (light purple)
        STATUS_COMPLETED: '#CCFFCC', # Pale Green
        STATUS_FAILED: '#FFCCCC',    # Pale Red
        "Unknown": '#F0F0F0',         # Very Light Gray
        "Running": '#ADD8E6',         # Light Blue
    }

    # Configure tags for Treeview styling
    style = ttk.Style()
    for status, color in STATUS_COLORS.items():
        style.map(f'{status}.Treeview', background=[('selected', style.lookup('Treeview', 'fieldbackground')), ('!selected', color)])
        style.configure(f'{status}.Treeview', background=color) # For non-selected state

    jobs_frame = tk.Frame(jobs_win, bg="#f7f7f7", bd=2, relief=tk.GROOVE)
    jobs_frame.pack(padx=8, pady=8, fill="both", expand=True)

    jobs_toolbar = tk.Frame(jobs_frame, bg="#f7f7f7")
    jobs_toolbar.pack(fill="x", padx=4, pady=4)
    tk.Label(jobs_toolbar, text="Jobs:", bg="#f7f7f7").pack(side=tk.LEFT)
    
    jobs_tree_frame = tk.Frame(jobs_frame)
    jobs_tree_frame.pack(fill="both", expand=True, padx=4, pady=(0,4))
    
    job_cols = ("name", "status", "schedule", "day_of_week", "next_run_at", "last_run_status", "last_run_at", "source", "destination", "move_files", "send_email", "recipient_email")
    jobs_tree = ttk.Treeview(jobs_tree_frame, columns=job_cols, show="headings", height=5)
    jobs_tree.heading("name", text="Job Name", anchor="w")
    jobs_tree.heading("status", text="Status", anchor="w")
    jobs_tree.heading("schedule", text="Schedule", anchor="w")
    jobs_tree.heading("day_of_week", text="Day", anchor="w")
    jobs_tree.heading("next_run_at", text="Next Run", anchor="w")
    jobs_tree.heading("last_run_status", text="Last Status", anchor="w")
    jobs_tree.heading("last_run_at", text="Last Run", anchor="w")
    jobs_tree.heading("source", text="Source Path", anchor="w")
    jobs_tree.heading("destination", text="Destination", anchor="w")
    jobs_tree.heading("move_files", text="Move Files", anchor="w")
    jobs_tree.heading("send_email", text="Send Email", anchor="w")
    jobs_tree.heading("recipient_email", text="Recipient Email", anchor="w")
    
    jobs_tree.column("name", width=120, anchor="w")
    jobs_tree.column("status", width=80, anchor="w")
    jobs_tree.column("schedule", width=80, anchor="w")
    jobs_tree.column("day_of_week", width=90, anchor="w")
    jobs_tree.column("next_run_at", width=140, anchor="w")
    jobs_tree.column("last_run_status", width=100, anchor="w")
    jobs_tree.column("last_run_at", width=140, anchor="w")
    jobs_tree.column("source", width=200, anchor="w")
    jobs_tree.column("destination", width=200, anchor="w")
    jobs_tree.column("move_files", width=80, anchor="center")
    jobs_tree.column("send_email", width=80, anchor="center")
    jobs_tree.column("recipient_email", width=200, anchor="w")
    
    jobs_vscroll = ttk.Scrollbar(jobs_tree_frame, orient=tk.VERTICAL, command=jobs_tree.yview)
    jobs_tree.configure(yscrollcommand=jobs_vscroll.set)
    jobs_vscroll.pack(side=tk.RIGHT, fill="y")
    jobs_tree.pack(fill="both", expand=True)

    _after_id = None
    def _update_running_jobs_ui():
        for i in running_tree.get_children():
            running_tree.delete(i)
        now = datetime.now(timezone.utc)
        for job_info in job_manager.get_running_jobs():
            job_data = job_info['data']
            job_type = job_info['type']
            start_time = job_info['start_time']
            status = job_info['status']
            job_id = job_data['id']

            elapsed = now - start_time
            elapsed_str = str(elapsed).split('.')[0]
            start_time_str = start_time.astimezone().strftime('%Y-%m-%d %H:%M:%S')
            
            job_name = job_data.get('name', 'Unknown Job')
            
            # Apply tag for coloring
            tag = status if status in STATUS_COLORS else "Unknown"
            running_tree.insert("", "end", values=(job_name, status, start_time_str, elapsed_str), iid=job_id, tags=(tag,))
        global _after_id
        _after_id = jobs_win.after(1000, _update_running_jobs_ui)

    # New function to update the Treeview on the main thread
    def _update_jobs_treeview_gui(jobs):
        log.debug("_update_jobs_treeview_gui: Clearing existing jobs from treeview.")
        for i in jobs_tree.get_children():
            jobs_tree.delete(i)
        log.debug(f"_update_jobs_treeview_gui: Starting to insert {len(jobs)} jobs into treeview.")
        for job in jobs:
            # Unpack the new 19-column job tuple from the JOIN query
            (job_id, name, source, dest_location, dest_provider, move_files, _, 
             status, last_run, last_run_status, schedule, next_run_at, 
             schedule_hour, schedule_minute, schedule_date, schedule_day_of_week, 
             send_email, recipient_email, dest_id) = job

            move_files_str = "Yes" if move_files == 1 else "No"
            send_email_str = "Yes" if send_email == 1 else "No"
            last_run_disp = datetime.fromisoformat(last_run).astimezone().strftime('%Y-%m-%d %H:%M:%S') if last_run else ""
            
            next_run_at_disp = ""
            if next_run_at:
                try:
                    utc_dt = datetime.fromisoformat(next_run_at)
                    local_dt = utc_dt.astimezone()
                    next_run_at_disp = local_dt.strftime('%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError):
                    next_run_at_disp = "N/A"
            
            display_schedule = schedule or "Manual"
            display_day_of_week = schedule_day_of_week if schedule == "Weekly" else ""
            
            # Create the values tuple for the treeview
            values = (
                name, status or STATUS_IDLE, display_schedule, display_day_of_week, 
                next_run_at_disp, last_run_status or "", last_run_disp, 
                source, f"{dest_provider}://{dest_location}", move_files_str, 
                send_email_str, recipient_email
            )
            
            # Apply tag for coloring
            tag = status if status in STATUS_COLORS else STATUS_IDLE
            jobs_tree.insert("", "end", values=values, iid=str(job_id), tags=(tag,))

        log.debug("_update_jobs_treeview_gui: Finished inserting jobs into treeview.")
        # Restore normal button state
        refresh_button.config(state=tk.NORMAL)
        run_job_button.config(state=tk.NORMAL)
        edit_job_button.config(state=tk.NORMAL)
        delete_job_button.config(state=tk.NORMAL)


    # New function to fetch jobs in a separate thread
    def _fetch_jobs_thread_target():
        log.debug("_fetch_jobs_thread_target: Calling database.list_jobs().")
        jobs = database.list_jobs()
        log.info(f"_fetch_jobs_thread_target: Found {len(jobs)} jobs in the database.")
        # Schedule the GUI update on the main thread
        jobs_win.after(0, _update_jobs_treeview_gui, jobs)


    def _refresh_jobs_list():
        log.info("Refreshing jobs list. Starting async fetch.")
        # Disable buttons to indicate loading
        refresh_button.config(state=tk.DISABLED)
        run_job_button.config(state=tk.DISABLED)
        edit_job_button.config(state=tk.DISABLED)
        delete_job_button.config(state=tk.DISABLED)

        # Clear existing entries and show loading message
        for i in jobs_tree.get_children():
            jobs_tree.delete(i)
        jobs_tree.insert("", "end", values=("Loading jobs...", "", "", "", "", "", "", "", "", "", "", "", ""), iid="loading")
        
        # Start fetching jobs in a separate thread
        thread = threading.Thread(target=_fetch_jobs_thread_target)
        thread.daemon = True # Allow the thread to exit with the main program
        thread.start()

    def _run_job_async_target(job_id_to_run, jobs_win_ref):
        log.debug("_run_job_async_target: Calling database.list_jobs() to find job ID %d.", job_id_to_run)
        all_jobs = database.list_jobs()
        job_to_run = None
        for job in all_jobs:
            if job[0] == job_id_to_run:
                job_to_run = job
                break
        
        # Restore button states on the main thread after fetching jobs
        jobs_win_ref.after(0, lambda: [
            refresh_button.config(state=tk.NORMAL),
            run_job_button.config(state=tk.NORMAL),
            edit_job_button.config(state=tk.NORMAL),
            delete_job_button.config(state=tk.NORMAL)
        ])

        if not job_to_run:
            log.error(f"Could not find job details for job ID: {job_id_to_run}")
            jobs_win_ref.after(0, lambda: messagebox.showerror("Error", "Could not find the selected job details."))
            return
        
        # The job_to_run tuple is already in the correct format from the new DB query.
        # Just check for source path existence before running.
        source_path = job_to_run[2]
        job_name = job_to_run[1]
        if not os.path.exists(source_path):
            log.error(f"Source path for job '{job_name}' does not exist: {source_path}")
            jobs_win_ref.after(0, lambda: messagebox.showerror("Error", f"Source path for job '{job_name}' does not exist:\n{source_path}"))
            return
        
        log.info(f"Starting job '{job_name}' in a new thread.")
        stop_event = threading.Event()
        t = threading.Thread(target=run_job_in_thread, args=(job_to_run, stop_event, ConflictResolution.RENAME, jobs_win, None, None, _refresh_jobs_list))
        t.daemon = False
        t.start()


    def _run_selected_job():
        log.info("'_run_selected_job' triggered.")
        selected_item = jobs_tree.selection()
        if not selected_item:
            log.warning("Run job triggered but no job selected.")
            messagebox.showinfo("Info", "Select a job to run.")
            return
        job_id = int(selected_item[0])
        log.info(f"Attempting to run job with ID: {job_id}. Fetching details asynchronously.")
        
        # Disable buttons to indicate loading/processing
        refresh_button.config(state=tk.DISABLED)
        run_job_button.config(state=tk.DISABLED)
        edit_job_button.config(state=tk.DISABLED)
        delete_job_button.config(state=tk.DISABLED)

        # Start fetching job details and running job in a separate thread
        thread = threading.Thread(target=_run_job_async_target, args=(job_id, jobs_win))
        thread.daemon = True
        thread.start()

    def _edit_job_async_target(job_id_to_edit, jobs_win_ref, refresh_callback_ref):
        log.debug("_edit_job_async_target: Calling database.list_jobs() to find job ID %d.", job_id_to_edit)
        all_jobs = database.list_jobs()
        job_to_edit = None
        for job in all_jobs:
            if job[0] == job_id_to_edit:
                job_to_edit = job
                break
        
        # Restore button states on the main thread after fetching jobs
        jobs_win_ref.after(0, lambda: [
            refresh_button.config(state=tk.NORMAL),
            run_job_button.config(state=tk.NORMAL),
            edit_job_button.config(state=tk.NORMAL),
            delete_job_button.config(state=tk.NORMAL)
        ])

        if job_to_edit:
            log.info(f"Opening 'add job' window to edit job ID: {job_id_to_edit}")
            jobs_win_ref.after(0, lambda: add_job_ui.open_add_job_window(jobs_win_ref, job_to_edit=job_to_edit, refresh_callback=refresh_callback_ref))
        else:
            log.error(f"Could not find job details for editing job ID: {job_id_to_edit}")
            jobs_win_ref.after(0, lambda: messagebox.showerror("Error", "Could not find the selected job details."))


    def _edit_selected_job():
        log.info("'_edit_selected_job' triggered.")
        selected_item = jobs_tree.selection()
        if not selected_item:
            log.warning("Edit job triggered but no job selected.")
            messagebox.showinfo("Info", "Select a job to edit.")
            return
        job_id = int(selected_item[0])
        log.info(f"Attempting to edit job with ID: {job_id}. Fetching details asynchronously.")
        
        # Disable buttons to indicate loading/processing
        refresh_button.config(state=tk.DISABLED)
        run_job_button.config(state=tk.DISABLED)
        edit_job_button.config(state=tk.DISABLED)
        delete_job_button.config(state=tk.DISABLED)

        # Start fetching job details in a separate thread
        thread = threading.Thread(target=_edit_job_async_target, args=(job_id, jobs_win, _refresh_jobs_list))
        thread.daemon = True
        thread.start()

    def _delete_selected_job():
        log.info("'_delete_selected_job' triggered.")
        selected_item = jobs_tree.selection()
        if not selected_item:
            log.warning("Delete job triggered but no job selected.")
            messagebox.showinfo("Info", "Select a job to delete.")
            return
        item_values = jobs_tree.item(selected_item[0], "values")
        job_name = item_values[0]
        log.info(f"Attempting to delete job: '{job_name}'")
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete the job '{job_name}'?"):
            try:
                log.info(f"User confirmed deletion of job '{job_name}'.")
                database.delete_job(job_name)
                _refresh_jobs_list()
            except Exception as e:
                log.error(f"Failed to delete job '{job_name}': {e}", exc_info=True)
                messagebox.showerror("Error", f"Failed to delete job: {e}")
    
    def _stop_selected_job():
        log.info("'_stop_selected_job' triggered.")
        selected_item = running_tree.selection()
        if not selected_item:
            log.warning("Stop job triggered but no running job selected.")
            messagebox.showinfo("Info", "Select a running job to stop.")
            return
        job_id = int(selected_item[0])
        log.info(f"Attempting to stop job with ID: {job_id}")
        job_manager.stop_job(job_id)

    def _stop_all_jobs():
        log.info("'_stop_all_jobs' triggered.")
        job_manager.stop_all_jobs()

    def on_close():
        log.info("Closing Run Jobs window.")
        if job_manager.get_running_jobs():
            if not messagebox.askyesno("Confirm", "Jobs are currently running. Are you sure you want to exit?"):
                log.info("User cancelled closing window due to running jobs.")
                return
        global _after_id
        if _after_id:
            jobs_win.after_cancel(_after_id)
        if jobs_win._clock_after_id:
            jobs_win.after_cancel(jobs_win._clock_after_id)
            jobs_win._clock_after_id = None
        job_manager.remove_listener(_update_running_jobs_ui)
        station_manager.remove_listener(_update_bulb_colors) # Deregister listener
        jobs_win.destroy()

    jobs_win.protocol("WM_DELETE_WINDOW", on_close)
    job_manager.add_listener(_update_running_jobs_ui)
    station_manager.add_listener(_update_bulb_colors) # Register listener
    
    _update_running_jobs_ui()
    _update_bulb_colors() # Initial call to set colors

    tk.Button(jobs_toolbar, text="Add Job", command=lambda: add_job_ui.open_add_job_window(jobs_win, refresh_callback=_refresh_jobs_list)).pack(side=tk.LEFT, padx=6)
    edit_job_button = tk.Button(jobs_toolbar, text="Edit Job", command=_edit_selected_job)
    edit_job_button.pack(side=tk.LEFT, padx=6)
    delete_job_button = tk.Button(jobs_toolbar, text="Delete Job", command=_delete_selected_job)
    delete_job_button.pack(side=tk.LEFT, padx=6)
    run_job_button = tk.Button(jobs_toolbar, text="Run Job", command=_run_selected_job, bg="#4CAF50", fg="white")
    run_job_button.pack(side=tk.LEFT, padx=6)
    tk.Button(jobs_toolbar, text="Stop Job", command=_stop_selected_job, bg="#f44336", fg="white").pack(side=tk.LEFT, padx=6)
    tk.Button(jobs_toolbar, text="Stop All Jobs", command=_stop_all_jobs, bg="#f44336", fg="white").pack(side=tk.LEFT, padx=6)
    refresh_button = tk.Button(jobs_toolbar, text="Refresh", command=_refresh_jobs_list)
    refresh_button.pack(side=tk.LEFT, padx=6)
    tk.Button(jobs_toolbar, text="Main Menu", command=on_close).pack(side=tk.RIGHT, padx=6)

    _refresh_jobs_list()