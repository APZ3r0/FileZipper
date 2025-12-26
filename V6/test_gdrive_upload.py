import os
import logging
import zipfile # Added for zip functionality
from .google_drive_connector import GoogleDriveConnector

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

def create_dummy_zip_file(output_zip_path: str, files_to_zip: list[str]) -> bool:
    """
    Creates a zip file containing the specified files.
    Returns True on success, False on failure.
    """
    try:
        with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in files_to_zip:
                if os.path.exists(file_path):
                    zipf.write(file_path, os.path.basename(file_path))
                    log.info(f"Added '{file_path}' to zip file.")
                else:
                    log.warning(f"File not found for zipping: {file_path}")
                    return False
        log.info(f"Dummy zip file created successfully: {output_zip_path}")
        return True
    except Exception as e:
        log.error(f"Error creating dummy zip file: {e}")
        return False

def test_google_drive_upload_and_backup():
    log.info("Starting Google Drive upload and backup test...")

    connector = GoogleDriveConnector()

    log.info("Attempting to authenticate with Google Drive...")
    # The authenticate method will open a browser for user interaction if needed.
    if connector.authenticate():
        log.info("Authentication successful.")

        # --- Test 1: Regular file upload ---
        local_file_name = "dummy_upload.txt"
        local_file_path = os.path.join(os.path.dirname(__file__), local_file_name)
        remote_folder_name_upload = "Gemini_CLI_Test_Uploads" # A specific folder for test uploads

        if not os.path.exists(local_file_path):
            log.error(f"Local file not found: {local_file_path}. Please create it before running this test.")
            return

        log.info(f"Attempting to upload '{local_file_name}' to Google Drive folder '{remote_folder_name_upload}'...")
        file_id = connector.upload_file(local_file_path, remote_folder_name_upload)

        if file_id:
            log.info(f"File uploaded successfully! Remote File ID: {file_id}")
            log.info(f"Verify in your Google Drive under the folder '{remote_folder_name_upload}'.")
        else:
            log.error("Regular file upload failed.")

        log.info("-" * 50)

        # --- Test 2: Zip file creation and upload for backup ---
        backup_folder_name = "Gemini_CLI_Backup_Folder"
        output_zip_filename = "dummy_backup.zip"
        output_zip_path = os.path.join(os.path.dirname(__file__), output_zip_filename)
        
        files_to_include_in_zip = [local_file_path] # Use the existing dummy_upload.txt

        log.info(f"Attempting to create dummy zip file: {output_zip_filename}...")
        if create_dummy_zip_file(output_zip_path, files_to_include_in_zip):
            log.info(f"Attempting to upload '{output_zip_filename}' to Google Drive folder '{backup_folder_name}'...")
            zip_file_id = connector.upload_file(output_zip_path, backup_folder_name)

            if zip_file_id:
                log.info(f"Zip file uploaded successfully! Remote File ID: {zip_file_id}")
                log.info(f"Verify in your Google Drive under the folder '{backup_folder_name}'.")
                # Clean up the local dummy zip file
                os.remove(output_zip_path)
                log.info(f"Removed local dummy zip file: {output_zip_path}")
            else:
                log.error("Zip file upload failed.")
        else:
            log.error("Failed to create dummy zip file.")
    else:
        log.error("Google Drive authentication failed. Please check your client_secret.json and internet connection.")
        log.info("Make sure 'client_secret_846456975010-em6adqe1id3bq8ehssis1llhsr8l1r64.apps.googleusercontent.com.json' is in the project root directory.")

if __name__ == '__main__':
    test_google_drive_upload_and_backup()
