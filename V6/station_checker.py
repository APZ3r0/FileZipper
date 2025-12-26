import os
import zipfile
import logging
from . import database
from .google_drive_connector import GoogleDriveConnector
from .onedrive_connector import OneDriveConnector

log = logging.getLogger(__name__)

def test_packing(temp_dir="."):
    """
    Tests the packing functionality by creating and then deleting a small zip file.

    Returns:
        bool: True if the zip file was created and deleted successfully, False otherwise.
    """
    log.info("Running packing station check...")
    test_file_name = os.path.join(temp_dir, "packing_test_file.txt")
    zip_file_name = os.path.join(temp_dir, "packing_test.zip")

    try:
        # 1. Create a dummy file to be zipped
        log.debug(f"Creating dummy file: {test_file_name}")
        with open(test_file_name, "w") as f:
            f.write("This is a test.")

        # 2. Create the zip archive
        log.debug(f"Creating zip file: {zip_file_name}")
        with zipfile.ZipFile(zip_file_name, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(test_file_name, os.path.basename(test_file_name))

        # 3. Verify the zip file exists
        if not os.path.exists(zip_file_name):
            raise IOError("Zip file was not created.")
        
        log.info("Packing station check successful.")
        return True

    except Exception as e:
        log.error(f"Packing station check failed: {e}", exc_info=True)
        return False

    finally:
        # 4. Clean up created files
        if os.path.exists(test_file_name):
            log.debug(f"Cleaning up dummy file: {test_file_name}")
            os.remove(test_file_name)
        if os.path.exists(zip_file_name):
            log.debug(f"Cleaning up zip file: {zip_file_name}")
            os.remove(zip_file_name)

def test_shipping(temp_dir="."):
    """
    Tests the shipping functionality by uploading and deleting a test file
    to all configured cloud destinations.

    Returns:
        bool: True if all destinations were tested successfully, False otherwise.
    """
    log.info("Running shipping station check...")
    connectors = {
        'gdrive': GoogleDriveConnector,
        'onedrive': OneDriveConnector
    }
    
    try:
        destinations = database.list_destinations()
    except Exception as e:
        log.error(f"Could not retrieve destinations from database: {e}", exc_info=True)
        return False

    cloud_destinations = [d for d in destinations if d[3] in connectors]

    if not cloud_destinations:
        log.info("No cloud destinations configured. Shipping check skipped.")
        return True # Nothing to test

    test_file_name = os.path.join(temp_dir, "shipping_test_file.txt")
    try:
        # Create a dummy file for uploading
        with open(test_file_name, "w") as f:
            f.write("This is a shipping test file.")

        for dest_id, dest_name, dest_location, dest_provider in cloud_destinations:
            log.info(f"Testing destination '{dest_name}' ({dest_provider})...")
            remote_file_id = None
            try:
                connector = connectors[dest_provider]()
                
                # Upload the file
                log.debug(f"Uploading test file to '{dest_location}'")
                remote_file_id = connector.upload_file(test_file_name, dest_location)
                if not remote_file_id:
                    log.error(f"Upload to '{dest_name}' failed.")
                    return False
                log.info(f"Upload to '{dest_name}' successful, file ID: {remote_file_id}")

            except Exception as e:
                log.error(f"An error occurred during test for destination '{dest_name}': {e}", exc_info=True)
                return False
            finally:
                # Clean up the remote file
                if remote_file_id:
                    log.debug(f"Deleting remote test file: {remote_file_id}")
                    if not connector.delete_file(remote_file_id):
                        log.warning(f"Failed to delete remote test file '{remote_file_id}' from '{dest_name}'. Manual cleanup may be required.")
                        # We don't return False here, as the core functionality worked, but we log a stern warning.
    
    finally:
        # Clean up the local dummy file
        if os.path.exists(test_file_name):
            os.remove(test_file_name)

    log.info("Shipping station check fully successful for all destinations.")
    return True


if __name__ == '__main__':
    # For direct testing
    logging.basicConfig(level=logging.DEBUG)
    if test_packing():
        print("Packing test SUCCEEDED.")
    else:
        print("Packing test FAILED.")
    
    # You would need a dummy database with destinations for this to work
    # if test_shipping():
    #     print("Shipping test SUCCEEDED.")
    # else:
    #     print("Shipping test FAILED.")
