import os
import zipfile
import subprocess
import sys
import threading
import sqlite3
from datetime import datetime, timezone, timedelta
import io
import webbrowser
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
import time
from enum import Enum
import json
import logging

from . import database
from . import job_manager
from .job_manager import (
    STATUS_IDLE, STATUS_PENDING, STATUS_PACKAGING, STATUS_AWAITING_TRANSFER, 
    STATUS_TRANSFERRING, STATUS_VERIFYING, STATUS_NOTIFYING_SENDER, 
    STATUS_COMPLETED, STATUS_FAILED
)
from .email_utils import send_email
from .google_drive_connector import GoogleDriveConnector
from .onedrive_connector import OneDriveConnector
from . import config_utils
from .auth_manager import get_gmail_service # Import the central gmail service getter
from . import station_manager


def send_gmail_notification(subject, body, recipient_email):
    """Sends an email using the Gmail API via the central auth_manager."""
    import base64
    from email.message import EmailMessage
    
    log.info("Attempting to send Gmail notification.")
    try:
        service = get_gmail_service()
        if not service:
            log.warning("Could not send email because Gmail service is not available.")
            return

        message = EmailMessage()
        message.set_content(body)
        message['To'] = recipient_email
        message['From'] = 'me'
        message['Subject'] = subject
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {'raw': encoded_message}
        
        send_message = service.users().messages().send(userId="me", body=create_message).execute()
        log.info(f'Message Id: {send_message["id"]}')
    except Exception as e:
        log.error("Failed to send Gmail notification.", exc_info=True)

# --- UI Imports and Setup ---
try:
    import tkinter as tk
    from tkinter import messagebox
except ImportError:
    tk = None

class ConflictResolution(Enum):
    OVERWRITE = "overwrite"
    RENAME = "rename"
    CANCEL = "cancel"

# --- Process Pool and Logging Setup ---
_process_executor = ProcessPoolExecutor()
import atexit
atexit.register(_process_executor.shutdown, wait=True)
log = logging.getLogger(__name__)

# --- Helper Functions ---
def _is_image_file(path: str) -> bool:
    if not path: return False
    return path.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif", ".heic"))

def resolve_save_conflict(zip_dest: str, on_conflict_action: ConflictResolution | str | None = None) -> str | None:
    if not os.path.exists(zip_dest):
        return zip_dest

    action_str = on_conflict_action.value if isinstance(on_conflict_action, ConflictResolution) else on_conflict_action

    if action_str:
        if action_str == 'overwrite':
            return zip_dest
        elif action_str == 'rename':
            count = 1
            while True:
                name, ext = os.path.splitext(zip_dest)
                new_dest = f"{name}_{count}{ext}"
                if not os.path.exists(new_dest): return new_dest
                count += 1
        elif action_str == 'cancel':
            return None

    if tk:
        response = messagebox.askyesnocancel("File Exists", f"'{os.path.basename(zip_dest)}' already exists. Overwrite?")
        if response is True: return zip_dest
        elif response is False:
            count = 1
            while True:
                name, ext = os.path.splitext(zip_dest)
                new_dest = f"{name}_{count}{ext}"
                if not os.path.exists(new_dest): return new_dest
                count += 1
        else: return None
    else:
        while True:
            response = input(f"'{os.path.basename(zip_dest)}' exists. [O]verwrite, [R]ename, or [C]ancel? ").lower()
            if response in ("o", "overwrite"): return zip_dest
            elif response in ("r", "rename"):
                count = 1
                while True:
                    name, ext = os.path.splitext(zip_dest)
                    new_dest = f"{name}_{count}{ext}"
                    if not os.path.exists(new_dest): return new_dest
                    count += 1
            elif response in ("c", "cancel"): return None

def zip_path(target_path: str, output_root: str | None = None, on_conflict_action: ConflictResolution | str | None = None) -> tuple[str, str | None, int, int]:
    log.info(f"Starting zip process for target: {target_path}")
    
    num_files = 0
    total_size = 0
    if os.path.isdir(target_path):
        for root, _, files in os.walk(target_path):
            for f in files:
                fp = os.path.join(root, f)
                if not os.path.islink(fp):
                    num_files += 1
                    total_size += os.path.getsize(fp)
    else:
        num_files = 1
        total_size = os.path.getsize(target_path)

    output_root = output_root or os.path.join(os.path.abspath(os.path.dirname(__file__)), "Zipped")
    os.makedirs(output_root, exist_ok=True)

    name = os.path.basename(target_path.rstrip(os.sep)) or "archive"
    zip_dest_initial = os.path.join(output_root, f"{name}.zip")
    
    zip_dest = resolve_save_conflict(zip_dest_initial, on_conflict_action=on_conflict_action)
    if zip_dest is None:
        return "cancelled", None, 0, 0
    
    action = "overwritten" if zip_dest == zip_dest_initial and os.path.exists(zip_dest_initial) else "created"
    if zip_dest != zip_dest_initial: action = "renamed"

    log.info(f"Creating zip file at: {zip_dest}")
    with zipfile.ZipFile(zip_dest, "w", zipfile.ZIP_DEFLATED) as zipf:
        if os.path.isdir(target_path):
            for root, _, files in os.walk(target_path):
                for f in files:
                    fp = os.path.join(root, f)
                    arc = os.path.relpath(fp, start=target_path)
                    arc_for_zip = arc.replace(os.sep, '/')
                    zipf.write(fp, arc_for_zip)
                    info = zipf.getinfo(arc_for_zip)
                    database._record_file(original_path=fp, arcname=arc, zip_path=zip_dest, file_size=info.file_size, mtime=os.path.getmtime(fp), compressed_size=info.compress_size)
        else:
            zipf.write(target_path, arcname=name)
            info = zipf.getinfo(name)
            database._record_file(original_path=target_path, arcname=name, zip_path=zip_dest, file_size=info.file_size, mtime=os.path.getmtime(target_path), compressed_size=info.compress_size)
    return action, zip_dest, num_files, total_size

def run_job_in_thread(job, stop_event, on_conflict, root_widget=None, status_variable=None, dest_var=None, refresh_callback=None):
    (job_id, name, path, dest_location, dest_provider, move_files, _, _, _, _, 
     schedule, _, schedule_hour, schedule_minute, schedule_date, _, 
     send_email_on_completion, recipient_email, dest_id) = job
    
    log.info(f"run_job_in_thread started for job '{name}' (ID: {job_id}) with provider '{dest_provider}'")

    job_status_final = STATUS_FAILED # Use new constant for final status
    final_message = ""
    num_files = 0
    total_size = 0
    effective_zip_path_for_query = None # Initialize for broader scope
    remote_uri = None # Initialize for broader scope
    connectors = {
        'gdrive': GoogleDriveConnector,
        'onedrive': OneDriveConnector
    }
    
    def update_status(message, current_job_status=None): # Added current_job_status parameter
        nonlocal final_message
        final_message = message
        if root_widget and status_variable:
            root_widget.after(0, status_variable.set, message)
        else:
            log.info(f"Job Status Update for '{name}': {message}")
        if job_id and current_job_status: # Only update job_manager if a specific status is provided
            job_manager.update_job_status(job_id, current_job_status)

    def db_update_job_status(*args):
        if root_widget:
            root_widget.after(0, database.update_job_status, *args)
        else:
            database.update_job_status(*args)
    
    try:
        job_data = {
            'id': job_id,
            'name': name,
            'source_path': path,
            'dest_location': dest_location,
            'dest_provider': dest_provider
        }
        job_manager.add_job(job_data, 'backup', stop_event) # This sets initial in-memory status to STATUS_PENDING

        if job_id:
            db_update_job_status(job_id, STATUS_PENDING, None, None, None) # Use STATUS_PENDING
            update_status("Initializing job...", STATUS_PENDING) # Update with PENDING

        last_run_time = datetime.now(timezone.utc)
        next_run_at = None
        if schedule == "Daily":
            next_run_at = (last_run_time + timedelta(days=1)).replace(hour=schedule_hour, minute=schedule_minute, second=0, microsecond=0)
        elif schedule == "Hourly":
            next_run_at = (last_run_time + timedelta(hours=1)).replace(minute=schedule_minute, second=0, microsecond=0)
        
        next_run_at_iso = next_run_at.isoformat() if next_run_at else None

        
        log.info(f"Full job tuple received: {job}")
        log.info(f"Job '{name}' starting with provider '{dest_provider}' and dest_location '{dest_location}'")

        if stop_event.is_set(): raise InterruptedError("Job was cancelled before start.")
        
        update_status("Zipping files...", STATUS_PACKAGING) # Update with PACKAGING
        log.info(f"Calling zip_path for job '{name}'")
        effective_on_conflict = on_conflict or ConflictResolution.RENAME

        from .config_utils import load_setting
        output_root_for_zip = dest_location if dest_provider == 'local' else load_setting('staging_path')
        if not output_root_for_zip:
             raise ValueError("Destination/Staging path not configured.")

        station_manager.set_status(station_manager.PACKING, station_manager.COLOR_ORANGE)
        try:
            zip_future = _process_executor.submit(zip_path, path, output_root_for_zip, effective_on_conflict)
            action, dest, num_files, total_size = zip_future.result()
        finally:
            # Reset status to green, as the 'working' state is over.
            # The initial check determines if the station is 'red'.
            station_manager.set_status(station_manager.PACKING, station_manager.COLOR_GREEN)
        
        if action == "cancelled" or dest is None:
            raise InterruptedError("Zip operation was cancelled or failed.")

        update_status(f"Package created: {os.path.basename(dest)}", STATUS_AWAITING_TRANSFER) # Update with AWAITING_TRANSFER

        # --- Refactored Cloud Upload Logic ---
        if dest_provider in connectors:
            update_status(f"Uploading to {dest_provider}...", STATUS_TRANSFERRING) # Update with TRANSFERRING
            
            station_manager.set_status(station_manager.SHIPPING, station_manager.COLOR_ORANGE)
            try:
                connector = connectors[dest_provider]()
                remote_file_id = connector.upload_file(local_path=dest, remote_folder=dest_location)
            finally:
                station_manager.set_status(station_manager.SHIPPING, station_manager.COLOR_GREEN)

            if remote_file_id:
                job_status_final = STATUS_COMPLETED # Change to use new constant
                remote_uri = f"{dest_provider}://{remote_file_id}"
                database.update_archive_remote_path(dest, remote_uri)
                update_status(f"Upload complete ({connector.get_display_name()}).", STATUS_VERIFYING) # Update with VERIFYING
                log.info(f"Successfully uploaded to {dest_provider} for job '{name}'")
                os.remove(dest)
                log.info(f"Removed local staged file '{dest}' after upload.")
                final_status_db = STATUS_COMPLETED if schedule == "Once" else STATUS_IDLE # Use new constants
                effective_zip_path_for_query = remote_uri # Set here for successful cloud upload
            else:
                raise RuntimeError(f"Upload to {dest_provider} failed.")
        else:
            log.info(f"Provider '{dest_provider}' not in connectors dict; treating as local job.")
            job_status_final = STATUS_COMPLETED # Change to use new constant
            update_status(f"Completed locally: {os.path.basename(dest)}", STATUS_COMPLETED) # Update with COMPLETED
            log.info(f"Job '{name}' completed locally.")
            final_status_db = STATUS_COMPLETED if schedule == "Once" else STATUS_IDLE # Use new constants
            effective_zip_path_for_query = dest # Set here for successful local zip

        if job_id:
            db_update_job_status(job_id, final_status_db, last_run_time.isoformat(), job_status_final, next_run_at_iso)

    except InterruptedError as e:
        job_status_final = STATUS_FAILED # Use new constant
        update_status(f"Job cancelled.", STATUS_FAILED) # Update with FAILED
        log.warning(f"Job '{name}' was interrupted: {e}")
        if job_id:
            db_update_job_status(job_id, STATUS_IDLE, last_run_time.isoformat(), job_status_final, next_run_at_iso) # Use new constant
    except Exception as e:
        job_status_final = STATUS_FAILED # Use new constant
        update_status(f"Job failed: {e}", STATUS_FAILED) # Update with FAILED
        log.critical(f"An unhandled error occurred in job '{name}': {e}", exc_info=True)
        if job_id:
            db_update_job_status(job_id, STATUS_IDLE, last_run_time.isoformat(), job_status_final, next_run_at_iso) # Use new constant
    finally:
        job_manager.remove_job(job_id)
        log.info(f"run_job_in_thread finished for job '{name}'.")
        
        file_list_body = ""
        if job_status_final == STATUS_COMPLETED and effective_zip_path_for_query: # Use new constant
            files_in_archive = database.get_files_in_zip_archive(effective_zip_path_for_query)
            if files_in_archive:
                file_list_body += "\n\nFiles in archive:\n"
                for file_record in files_in_archive:
                    # (original_path, arcname, zip_path, file_size, mtime, compressed_size, location, description, recorded_at)
                    file_name = os.path.basename(file_record[1]) # arcname
                    file_size_bytes = file_record[4]
                    
                    def format_size(size_bytes):
                        if size_bytes is None:
                            return "N/A"
                        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                            if size_bytes < 1024.0:
                                return f"{size_bytes:3.1f} {unit}"
                            size_bytes /= 1024.0
                        return f"{size_bytes:.1f} PB"

                    file_list_body += f"- {file_name} ({format_size(file_size_bytes)})\n"


        if send_email_on_completion and recipient_email:
            update_status("Sending email notification...", STATUS_NOTIFYING_SENDER) # Update with NOTIFYING_SENDER
            subject = f"Job '{name}' Completion Status: {job_status_final}" # Use new constant
            body = f"The job '{name}' finished with status: {job_status_final}.\n\nFinal message: {final_message}\n\nFiles processed: {num_files}\nTotal size: {total_size / 1024 / 1024:.2f} MB{file_list_body}"
            send_gmail_notification(subject, body, recipient_email)
            update_status("Email notification sent.", STATUS_COMPLETED) # Email sent, can go back to completed or maintain notifying sender for a brief moment.
            
        if refresh_callback:
            if root_widget:
                root_widget.after(0, refresh_callback)
            else:
                refresh_callback()

def run_restore_job_in_thread(job_data, stop_event, root_widget=None, refresh_callback=None):
    job_id = None
    restore_history_id = -1
    job_name = f"Restore to {os.path.basename(job_data.get('destination_path'))}"
    job_status_final = STATUS_FAILED # Use new constant
    recipient_email = job_data.get('email')

    def update_status(message, current_job_status=None): # Added current_job_status parameter
        if job_id and current_job_status: # Only update job_manager if a specific status is provided
            job_manager.update_job_status(job_id, current_job_status)
        log.info(f"Restore Job Status Update for '{job_name}': {message}")

    try:
        job_id = job_manager.add_job(job_data, 'restore', stop_event)
        update_status("Initializing restore...", STATUS_PENDING) # Use new constant
        start_time = datetime.now(timezone.utc)

        files_to_restore = job_data.get('files_to_restore')
        destination_path = job_data.get('destination_path')
        if not files_to_restore or not destination_path:
            raise ValueError("Missing files to restore or destination path.")

        files_restored_json = json.dumps([f['arcname'] for f in files_to_restore])
        restore_history_id = database.add_restore_history(job_name, destination_path, start_time.isoformat(), "Initializing", files_restored_json)


        if stop_event.is_set(): raise InterruptedError("Restore job was cancelled before start.")

        # Group files by the backup set they belong to
        grouped_files = {}
        for file_info in files_to_restore:
            zip_path = file_info['zip_path']
            if zip_path not in grouped_files:
                grouped_files[zip_path] = []
            grouped_files[zip_path].append(file_info['arcname'])

        staging_path = config_utils.load_setting('staging_path')
        if not staging_path:
            raise Exception("Staging path not set. Please set it in Utilities.")

        for zip_path, arcnames in grouped_files.items():
            if stop_event.is_set(): raise InterruptedError("Restore job was cancelled.")
            
            local_zip_path = None
            try:
                if zip_path.startswith('gdrive://'):
                    update_status(f"Downloading {os.path.basename(zip_path)}", STATUS_TRANSFERRING) # Use new constant
                    file_id = zip_path.replace('gdrive://', '')
                    connector = GoogleDriveConnector()
                    if not connector.authenticate():
                        raise Exception("Failed to authenticate with Google Drive.")
                    
                    local_zip_path = os.path.join(staging_path, file_id)
                    success = connector.download_file(file_id, local_zip_path)
                    if not success:
                        raise Exception(f"Failed to download {zip_path}")
                else:
                    local_zip_path = zip_path
                
                if stop_event.is_set(): raise InterruptedError("Restore job was cancelled.")

                update_status(f"Extracting from {os.path.basename(local_zip_path)}", STATUS_PACKAGING) # Using packaging for extraction
                with zipfile.ZipFile(local_zip_path, 'r') as zf:
                    log.info(f"Extracting {len(arcnames)} files to '{destination_path}' from '{local_zip_path}'")
                    for arcname in arcnames:
                        if stop_event.is_set(): raise InterruptedError("Restore job was cancelled.")
                        
                        # Replace backslashes with forward slashes for zipfile compatibility
                        arcname_for_zip = arcname.replace(os.sep, '/')
                        
                        log.info(f"Extracting '{arcname_for_zip}'...")
                        zf.extract(arcname_for_zip, path=destination_path)
                        log.info(f"Extracted '{arcname_for_zip}' successfully.")

            finally:
                if zip_path.startswith('gdrive://') and local_zip_path and os.path.exists(local_zip_path):
                    os.remove(local_zip_path)
        
        job_status_final = STATUS_COMPLETED # Use new constant
        update_status("Restore complete.", STATUS_COMPLETED) # Use new constant

    except InterruptedError as e:
        job_status_final = STATUS_FAILED # Use new constant
        update_status("Restore cancelled.", STATUS_FAILED) # Use new constant
        log.warning(f"Restore job '{job_name}' was interrupted: {e}")
    except Exception as e:
        job_status_final = STATUS_FAILED # Use new constant
        update_status(f"Restore failed: {e}", STATUS_FAILED) # Use new constant
        log.critical(f"An unhandled error occurred in restore job '{job_name}': {e}", exc_info=True)
    finally:
        end_time = datetime.now(timezone.utc).isoformat()
        if restore_history_id != -1:
            database.update_restore_history(restore_history_id, end_time, job_status_final) # Use new constant

        if job_id:
            job_manager.remove_job(job_id)
        
        file_list_body = ""
        if job_status_final == STATUS_COMPLETED and files_to_restore: # Use new constant
            file_list_body += "\n\nFiles restored:\n"
            for file_info in files_to_restore:
                file_list_body += f"- {os.path.basename(file_info['arcname'])}\n"


        if recipient_email:
            update_status("Sending email notification...", STATUS_NOTIFYING_SENDER) # Use new constant
            subject = f"Restore Job '{job_name}' Completion Status: {job_status_final}" # Use new constant
            body = f"The restore job '{job_name}' finished with status: {job_status_final}.{file_list_body}"
            send_gmail_notification(subject, body, recipient_email)
            update_status("Email notification sent.", STATUS_COMPLETED) # Email sent, can go back to completed or maintain notifying sender for a brief moment.

        log.info(f"run_restore_job_in_thread finished for job '{job_name}'.")
        if refresh_callback:
            if root_widget:
                root_widget.after(0, refresh_callback)
            else:
                refresh_callback()