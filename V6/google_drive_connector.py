import os
import time
import logging
from .cloud_interface import CloudStorageProvider
from .auth_manager import get_drive_service  # Import the central authenticator
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

log = logging.getLogger(__name__)

class GoogleDriveConnector(CloudStorageProvider):
    """
    A connector for interacting with Google Drive.
    This class now acts as a wrapper for the Google Drive API service,
    with authentication being handled by the central auth_manager.
    """

    def __init__(self):
        # Get the service from the central authentication manager
        self.service = get_drive_service()

    def get_display_name(self) -> str:
        return "Google Drive"

    def authenticate(self):
        """
        This method is now a stub to satisfy the abstract base class.
        Authentication is handled centrally by the auth_manager.
        """
        return True

    def is_authenticated(self) -> bool:
        """Checks if the service object is available."""
        return self.service is not None

    def get_free_space(self) -> int | None:
        """
        Returns the available free space in Google Drive in bytes.
        """
        if not self.is_authenticated():
            log.warning("Cannot get free space, service not available.")
            return None

        try:
            log.info("Fetching Google Drive storage quota.")
            about = self.service.about().get(fields="storageQuota").execute()
            quota = about.get('storageQuota', {})
            free_space = int(quota.get('limit', 0)) - int(quota.get('usage', 0))
            log.info(f"Available space: {free_space / (1024**3):.2f} GB")
            return free_space
        except HttpError as e:
            log.error(f"Failed to get Google Drive free space: {e}", exc_info=True)
            return None

    def _get_folder_id(self, folder_name: str) -> str | None:
        """Finds the ID of a folder by name, or creates it if not found."""
        if not self.is_authenticated():
            return None
        
        try:
            query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
            results = self.service.files().list(q=query, fields="files(id, name)").execute()
            items = results.get('files', [])

            if items:
                folder_id = items[0]['id']
                log.info(f"Found folder '{folder_name}' with ID: {folder_id}")
                return folder_id
            else:
                log.info(f"Folder '{folder_name}' not found, creating it.")
                file_metadata = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
                folder = self.service.files().create(body=file_metadata, fields='id').execute()
                folder_id = folder.get('id')
                log.info(f"Created folder '{folder_name}' with ID: {folder_id}")
                return folder_id
        except HttpError as e:
            log.error(f"An error occurred while finding/creating the folder '{folder_name}': {e}", exc_info=True)
            return None

    def upload_file(self, local_path: str, remote_folder: str) -> str | None:
        """
        Uploads a single file to the specified remote folder using a multipart upload.
        This is simpler and more reliable for smaller files than a resumable session.
        """
        if not self.is_authenticated():
            log.error("Cannot upload file, service not available.")
            return None
        
        folder_id = self._get_folder_id(remote_folder)
        if not folder_id:
            return None
            
        file_metadata = {'name': os.path.basename(local_path), 'parents': [folder_id]}
        
        try:
            # Use resumable=False to force a single multipart upload request.
            media = MediaFileUpload(local_path, resumable=False)
            log.info(f"Starting multipart upload of '{local_path}' to folder '{remote_folder}'.")
            
            request = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            )
            
            # For multipart upload, we execute it directly.
            response = request.execute()
            
            file_id = response.get('id')
            log.info(f"File '{local_path}' uploaded successfully with File ID: {file_id}")
            return file_id

        except HttpError as e:
            log.error(f"An error occurred during file upload: {e}", exc_info=True)
            return None
        except Exception as e:
            log.error(f"A non-HTTP error occurred during file upload: {e}", exc_info=True)
            return None

    def download_file(self, remote_file_id: str, local_path: str) -> bool:
        """
        Downloads a single file from the cloud in a memory-efficient way.
        """
        if not self.is_authenticated():
            log.error("Cannot download file, service not available.")
            return False
        
        try:
            log.info(f"Starting download of file ID '{remote_file_id}' to '{local_path}'.")
            request = self.service.files().get_media(fileId=remote_file_id)
            
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            with open(local_path, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request, chunksize=5*1024*1024)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    if status:
                        log.debug(f"Downloaded {int(status.progress() * 100)}%.")
            
            log.info(f"File '{remote_file_id}' downloaded successfully to '{local_path}'.")
            return True
        except HttpError as e:
            log.error(f"An error occurred during file download: {e}", exc_info=True)
            return False
        except Exception as e:
            log.error(f"A non-HTTP error occurred during file download: {e}", exc_info=True)
            return False

    def get_remote_file_hash(self, remote_file_id: str) -> str | None:
        """
        Retrieves the MD5 hash of a file in Google Drive.
        """
        if not self.is_authenticated():
            log.warning("Cannot get remote hash, service not available.")
            return None

        try:
            log.info(f"Fetching MD5 hash for file ID: {remote_file_id}")
            file_metadata = self.service.files().get(fileId=remote_file_id, fields='md5Checksum').execute()
            md5_hash = file_metadata.get('md5Checksum')
            log.info(f"MD5 hash found: {md5_hash}")
            return md5_hash
        except HttpError as e:
            log.error(f"Failed to get remote file hash for ID {remote_file_id}: {e}", exc_info=True)
            return None

    def delete_file(self, remote_file_id: str) -> bool:
        """
        Permanently deletes a file from Google Drive.
        """
        if not self.is_authenticated():
            log.warning("Cannot delete file, service not available.")
            return False

        try:
            log.info(f"Attempting to delete file ID: {remote_file_id}")
            self.service.files().delete(fileId=remote_file_id).execute()
            log.info(f"Successfully deleted file ID: {remote_file_id}")
            return True
        except HttpError as e:
            log.error(f"Failed to delete file ID {remote_file_id}: {e}", exc_info=True)
            return False


