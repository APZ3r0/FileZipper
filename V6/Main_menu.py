import tkinter as tk
from tkinter import messagebox
from . import run_jobs_ui
from . import destinations_ui
from . import restore_ui
from . import add_job_ui
from . import search_ui # Import the search UI
from datetime import datetime
from . import job_scheduler
from . import job_manager
import logging
from . import utilities_ui # Added for v7

class MainMenu(tk.Tk):
    log = logging.getLogger(__name__)

    def __init__(self):
        super().__init__()
        self.log.info("Initializing MainMenu...")
        self.title("Main Menu")
        self.geometry("300x350")
        self._clock_after_id = None
        
        # Frame for Clock
        self.clock_frame = tk.Frame(self, bg="#f7f7f7", bd=3, relief=tk.SOLID)
        self.clock_frame.pack(padx=10, pady=(10,15), fill="x")
        self.clock_label = tk.Label(self.clock_frame, font=("Arial", 12), bg="#f7f7f7")
        self.clock_label.pack()
        self._update_clock()
        
        button_frame = tk.Frame(self)
        button_frame.pack(pady=10)

        self.btn_add_job = tk.Button(button_frame, text="Add Job", command=self.open_add_job)
        self.btn_add_job.grid(row=0, column=0, padx=5, pady=5)
        
        self.btn_run_jobs = tk.Button(button_frame, text="Run Jobs", command=self.open_run_jobs)
        self.btn_run_jobs.grid(row=0, column=1, padx=5, pady=5)
        
        self.btn_create_destinations = tk.Button(button_frame, text="Create Destinations", command=self.open_create_destinations)
        self.btn_create_destinations.grid(row=1, column=0, columnspan=2, padx=5, pady=5)
        
        self.btn_advanced_search = tk.Button(button_frame, text="Advanced Search", command=self.open_advanced_search)
        self.btn_advanced_search.grid(row=2, column=0, columnspan=2, padx=5, pady=5)
        
        self.btn_restore_files = tk.Button(button_frame, text="Restore Files", command=self.open_restore_window)
        self.btn_restore_files.grid(row=3, column=0, columnspan=2, padx=5, pady=5)

        self.btn_utilities = tk.Button(button_frame, text="Utilities", command=self.open_utilities_window)
        self.btn_utilities.grid(row=4, column=0, padx=5, pady=5)

        self.btn_exit = tk.Button(button_frame, text="Exit Application", command=self.on_exit)
        self.btn_exit.grid(row=4, column=1, padx=5, pady=5)
        
        self.scheduler_thread, self.stop_scheduler_event = job_scheduler.start_scheduler()
        self.log.info("MainMenu initialized. Entering mainloop...")
        
    def on_exit(self):
        self.log.info("on_exit called.")
        
        # Stop the clock updater
        if self._clock_after_id:
            self.log.info("Cancelling clock update.")
            self.after_cancel(self._clock_after_id)
            self._clock_after_id = None
        
        # Check for running jobs and ask for confirmation
        if job_manager.get_running_jobs():
            self.log.warning("Jobs are running, asking user for confirmation to exit.")
            if messagebox.askyesno("Confirm Exit", "Jobs are currently running. Do you want to stop them and exit?"):
                self.log.info("User confirmed to stop jobs and exit.")
                job_manager.stop_all_jobs()
                # Begin check to shutdown safely
                self._shutdown_if_safe()
            else:
                self.log.info("User cancelled exit due to running jobs.")
                # If user cancels, re-enable the clock
                self._update_clock()
                return
        else:
            # No jobs running, shutdown immediately
            self._shutdown_if_safe()

    def _shutdown_if_safe(self):
        """Checks if jobs are still running. If not, proceeds with shutdown."""
        if job_manager.get_running_jobs():
            self.log.info("Waiting for running jobs to terminate...")
            self.after(100, self._shutdown_if_safe) # Check again in 100ms
        else:
            self.log.info("All jobs terminated. Proceeding with final shutdown.")
            # Stop the scheduler thread
            self.log.info("Setting stop_scheduler_event and joining scheduler thread.")
            self.stop_scheduler_event.set()
            self.scheduler_thread.join(timeout=2.0)
            self.log.info("Scheduler thread joined. Destroying GUI.")
            self.destroy()

    def check_jobs_and_exit(self):
        if job_manager.get_running_jobs():
            self.after(1000, self.check_jobs_and_exit)
        else:
            self.log.info("No running jobs. Stopping scheduler and exiting.")
            self.stop_scheduler_event.set()
            self.scheduler_thread.join(timeout=2.0) # Increased timeout slightly
            self.destroy()
            
    def _update_clock(self):
        now = datetime.now()
        current_time = now.strftime("%Y-%m-%d %H:%M:%S")
        self.clock_label.config(text=current_time)
        self._clock_after_id = self.after(1000, self._update_clock)
        
    def open_add_job(self):
        self.log.info("Opening Add Job window...")
        add_job_ui.open_add_job_window(self)
        
    def open_run_jobs(self):
        self.log.info("Opening Run Jobs window...")
        run_jobs_ui.open_run_jobs_window(self)
        
    def open_create_destinations(self):
        self.log.info("Opening Create Destinations window...")
        destinations_ui.open_destinations_window(self)
        
    def open_advanced_search(self):
        self.log.info("Opening Advanced Search window...")
        search_ui.open_search_window(self) # Still points to old module name
        
    def open_utilities_window(self):
        self.log.info("Opening Utilities window...")
        utilities_ui.open_utilities_window(self)

    def open_restore_window(self):
        self.log.info("Opening Restore Files window...")
        restore_ui.open_restore_window(self)

if __name__ == "__main__":
    # --- Setup Program Execution Logging ---
    exec_logger = logging.getLogger() # Get the root logger
    exec_logger.setLevel(logging.DEBUG)
    
    # Enable logging for googleapiclient
    logging.getLogger('googleapiclient').setLevel(logging.DEBUG)

    # Create a file handler for program execution
    exec_handler = logging.FileHandler('program_execution.log', mode='a')
    exec_handler.setLevel(logging.DEBUG)
    print(f"DEBUG: Program execution log handler level set to: {exec_handler.level}")
    # Create a logging format
    exec_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    exec_handler.setFormatter(exec_formatter)
    # Add the handler to the root logger
    exec_logger.addHandler(exec_handler)

    # Initialize the database connection and schema here, once at startup
    from . import database
    database.get_connection() # Establish the global connection
    database._init_db() # Initialize the schema (tables, migrations)

    # --- Run Station Checks ---
    from . import station_checker
    from . import station_manager
    if station_checker.test_packing():
        station_manager.set_status(station_manager.PACKING, station_manager.COLOR_GREEN)
    else:
        station_manager.set_status(station_manager.PACKING, station_manager.COLOR_RED)

    if station_checker.test_shipping():
        station_manager.set_status(station_manager.SHIPPING, station_manager.COLOR_GREEN)
    else:
        station_manager.set_status(station_manager.SHIPPING, station_manager.COLOR_RED)
    # --------------------------

    app = MainMenu()
    job_manager.set_root(app) # Set the root for safe GUI updates
    app.protocol("WM_DELETE_WINDOW", app.on_exit)
    try:
        app.mainloop()
    except Exception as e:
        exec_logger.critical("Exception caught in mainloop: %s", e, exc_info=True)
    finally:
        exec_logger.info("Mainloop exited.")
        logging.shutdown()
        print("Mainloop exited. Logging has been shut down.")