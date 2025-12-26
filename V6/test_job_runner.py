import unittest
from unittest.mock import MagicMock, patch, call
import threading
import os
import sys
from datetime import datetime, timezone

# Add the parent directory of V6 to the Python path to allow for imports
# This is necessary because we are running this script directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from V6 import job_runner
from V6.job_manager import (
    STATUS_IDLE, STATUS_PENDING, STATUS_PACKAGING, STATUS_AWAITING_TRANSFER, 
    STATUS_TRANSFERRING, STATUS_VERIFYING, STATUS_NOTIFYING_SENDER, 
    STATUS_COMPLETED, STATUS_FAILED
)

class TestJobRunner(unittest.TestCase):

    @patch('V6.job_runner.database')
    @patch('V6.job_runner.job_manager')
    @patch('V6.job_runner._process_executor')
    def test_local_job_status_transitions(self, mock_executor, mock_job_manager, mock_database):
        """
        Tests the status transitions for a simple, successful local job.
        """
        # --- MOCK SETUP ---
        # Mock the zip process to return a successful result immediately
        mock_zip_future = MagicMock()
        mock_zip_future.result.return_value = ('created', '/fake/path/archive.zip', 5, 1024)
        mock_executor.submit.return_value = mock_zip_future

        # Lists to capture the status updates
        job_manager_statuses = []
        database_statuses = []

        # Mock the update functions to record the statuses
        def capture_jm_status(job_id, status):
            job_manager_statuses.append(status)

        def capture_db_status(job_id, status, last_run_at, last_run_status, next_run_at):
            database_statuses.append(status)

        mock_job_manager.update_job_status.side_effect = capture_jm_status
        mock_database.update_job_status.side_effect = capture_db_status
        
        # --- JOB DATA ---
        job_data = (
            1,  # id
            'Test Job',  # name
            '/fake/source',  # source_path
            '/fake/destination',  # dest_location
            'local',  # dest_provider
            False,  # move_files
            datetime.now(timezone.utc).isoformat(), # created_at
            'Idle', # status
            None, # last_run_at
            None, # last_run_status
            'Once', # schedule
            None, # next_run_at
            0, # schedule_hour
            0, # schedule_minute
            None, # schedule_date
            None, # schedule_day_of_week
            False, # send_email_on_completion
            None, # recipient_email
            1 # destination_id
        )
        stop_event = threading.Event()

        # --- RUN THE JOB ---
        job_runner.run_job_in_thread(
            job=job_data, 
            stop_event=stop_event, 
            on_conflict='rename',
            root_widget=None, # Running without GUI
        )

        # --- ASSERTIONS ---
        # Expected statuses for the job_manager (in-memory, real-time)
        expected_jm_statuses = [
            STATUS_PENDING,
            STATUS_PACKAGING,
            STATUS_AWAITING_TRANSFER,
            STATUS_COMPLETED,
        ]
        
        # Expected final status written to the database
        expected_db_final_status = STATUS_COMPLETED
        
        print("\n--- Test Results for Local Job ---")
        print(f"Expected Job Manager Statuses: {expected_jm_statuses}")
        print(f"Actual Job Manager Statuses:   {job_manager_statuses}")
        
        # We check that the database was updated to PENDING at the start,
        # and then to its final state.
        self.assertEqual(mock_database.update_job_status.call_count, 2, "Database status should be updated twice (start and end).")
        
        initial_db_call = mock_database.update_job_status.call_args_list[0]
        final_db_call = mock_database.update_job_status.call_args_list[1]
        
        self.assertEqual(initial_db_call.args[1], STATUS_PENDING, "Initial database status should be PENDING.")
        self.assertEqual(final_db_call.args[1], expected_db_final_status, "Final database status should be COMPLETED.")
        
        self.assertEqual(job_manager_statuses, expected_jm_statuses, "The in-memory job statuses did not transition as expected.")

    @patch('os.remove')
    @patch('V6.job_runner.GoogleDriveConnector')
    @patch('V6.job_runner.database')
    @patch('V6.job_runner.job_manager')
    @patch('V6.job_runner._process_executor')
    def test_gdrive_job_status_transitions(self, mock_executor, mock_job_manager, mock_database, mock_gdrive_connector, mock_os_remove):
        """
        Tests the status transitions for a successful Google Drive upload job.
        """
        # --- MOCK SETUP ---
        mock_zip_future = MagicMock()
        mock_zip_future.result.return_value = ('created', '/fake/staging/archive.zip', 5, 1024)
        mock_executor.submit.return_value = mock_zip_future

        # Mock the GoogleDriveConnector instance and its methods
        mock_connector_instance = MagicMock()
        mock_connector_instance.upload_file.return_value = 'fake_gdrive_file_id'
        mock_connector_instance.get_display_name.return_value = 'Google Drive'
        mock_gdrive_connector.return_value = mock_connector_instance
        
        # Mock the config loader to return a fake staging path
        with patch('V6.config_utils.load_setting', return_value='/fake/staging') as mock_load_setting:

            job_manager_statuses = []
            def capture_jm_status(job_id, status):
                job_manager_statuses.append(status)

            mock_job_manager.update_job_status.side_effect = capture_jm_status
            
            # --- JOB DATA ---
            job_data = (
                2, 'Gdrive Job', '/fake/source', 'gdrive_folder_id', 'gdrive', False,
                datetime.now(timezone.utc).isoformat(), 'Idle', None, None, 'Once', None,
                0, 0, None, None, False, None, 2
            )
            stop_event = threading.Event()

            # --- RUN THE JOB ---
            job_runner.run_job_in_thread(
                job=job_data, 
                stop_event=stop_event, 
                on_conflict='rename',
                root_widget=None,
            )

            # --- ASSERTIONS ---
            expected_jm_statuses = [
                STATUS_PENDING,
                STATUS_PACKAGING,
                STATUS_AWAITING_TRANSFER,
                STATUS_TRANSFERRING,
                STATUS_VERIFYING,
            ]
            
            print("\n--- Test Results for GDrive Job ---")
            print(f"Expected Job Manager Statuses: {expected_jm_statuses}")
            print(f"Actual Job Manager Statuses:   {job_manager_statuses}")

            self.assertEqual(job_manager_statuses, expected_jm_statuses, "The in-memory job statuses for GDrive job did not transition as expected.")
            
            # Verify the database was updated correctly at the end
            final_db_call = mock_database.update_job_status.call_args
            self.assertEqual(final_db_call.args[1], STATUS_COMPLETED, "Final database status should be COMPLETED for GDrive job.")
            
            # Verify the local staged file was removed
            mock_os_remove.assert_called_once_with('/fake/staging/archive.zip')
                
if __name__ == '__main__':
    unittest.main()
