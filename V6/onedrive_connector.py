import os
import logging
from .cloud_interface import CloudStorageProvider

try:
    import msal
    import requests
except ImportError:
    msal = None
    requests = None

log = logging.getLogger(__name__)

ONEDRIVE_SCOPES = ["Files.ReadWrite", "offline_access", "User.Read"]

class OneDriveConnector(CloudStorageProvider):
    """A connector for interacting with Microsoft OneDrive using the MS Graph API."""

    def __init__(self):
        self.access_token = None
        self._ensure_deps()

    def _ensure_deps(self):
        if msal is None or requests is None:
            raise ImportError("msal and requests libraries are required for OneDrive. Please install with: pip install msal requests")

    def get_display_name(self) -> str:
        return "OneDrive"

    def authenticate(self) -> bool:
        """
        Handles the authentication flow for OneDrive using MSAL's device code flow.
        Requires the MSAL_CLIENT_ID environment variable to be set.
        """
        log.info("Authenticating with OneDrive...")
        client_id = os.environ.get("MSAL_CLIENT_ID")
        if not client_id:
            log.error("MSAL_CLIENT_ID environment variable not set.")
            return False

        app = msal.PublicClientApplication(client_id)
        # We'll leverage MSAL's token cache for persistence across sessions
        token_cache = msal.SerializableTokenCache()

        if os.path.exists("onedrive_token_cache.bin"):
            token_cache.deserialize(open("onedrive_token_cache.bin", "r").read())
        
        accounts = app.get_accounts()
        result = None
        if accounts:
            log.info("Found cached account, attempting to acquire token silently.")
            result = app.acquire_token_silent(ONEDRIVE_SCOPES, account=accounts[0])

        if not result:
            log.info("No suitable token in cache, starting device code flow.")
            flow = app.initiate_device_flow(scopes=ONEDRIVE_SCOPES)
            if "message" not in flow:
                log.error(f"Failed to start device flow: {flow.get('error_description')}")
                return False
            
            print(flow["message"]) # Instruct user to go to a URL and enter a code
            result = app.acquire_token_by_device_flow(flow)

        if "access_token" in result:
            self.access_token = result["access_token"]
            # Save the cache every time we get a new token
            if token_cache.has_state_changed:
                with open("onedrive_token_cache.bin", "w") as f:
                    f.write(token_cache.serialize())
            log.info("OneDrive authentication successful.")
            return True
        else:
            log.error(f"OneDrive authentication failed: {result.get('error_description')}")
            self.access_token = None
            return False

    def is_authenticated(self) -> bool:
        """Checks if the OneDrive connector has an access token."""
        return self.access_token is not None

    def get_free_space(self) -> int | None:
        """Returns the available free space in OneDrive in bytes."""
        if not self.access_token:
            if not self.authenticate():
                return None

        try:
            log.info("Fetching OneDrive storage quota.")
            url = "https://graph.microsoft.com/v1.0/me/drive"
            headers = {"Authorization": f"Bearer {self.access_token}"}
            resp = requests.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            quota = data.get('quota', {})
            free_space = quota.get('remaining', 0)
            log.info(f"Available OneDrive space: {free_space / (1024**3):.2f} GB")
            return free_space
        except Exception as e:
            log.error(f"Failed to get OneDrive free space: {e}")
            return None

    def _create_upload_session(self, remote_path: str) -> str:
        url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{remote_path}:/createUploadSession"
        headers = {"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"}
        resp = requests.post(url, headers=headers, json={"item": {"@microsoft.graph.conflictBehavior": "rename"}})
        resp.raise_for_status()
        return resp.json()["uploadUrl"]

    def _chunked_upload(self, local_path: str, upload_url: str) -> dict:
        total_size = os.path.getsize(local_path)
        chunk_size = 4 * 1024 * 1024 # 4MB chunks
        with open(local_path, "rb") as f:
            start = 0
            while start < total_size:
                chunk = f.read(chunk_size)
                if not chunk: break
                end = start + len(chunk) - 1
                headers = {"Content-Length": str(len(chunk)), "Content-Range": f"bytes {start}-{end}/{total_size}"}
                resp = requests.put(upload_url, headers=headers, data=chunk)
                
                if resp.status_code in (200, 201): # Final response
                    return resp.json()
                resp.raise_for_status() # Raise for other errors
                start = end + 1
        raise IOError("Chunked upload did not complete successfully.")

    def upload_file(self, local_path: str, remote_folder: str) -> str | None:
        """Uploads a file to OneDrive, using chunked upload for large files."""
        if not self.access_token:
            if not self.authenticate():
                return None
        
        remote_path = f"{remote_folder}/{os.path.basename(local_path)}"
        log.info(f"Starting upload of '{local_path}' to OneDrive at '{remote_path}'")
        try:
            upload_url = self._create_upload_session(remote_path)
            result = self._chunked_upload(local_path, upload_url)
            file_id = result.get('id')
            log.info(f"File uploaded successfully to OneDrive with ID: {file_id}")
            return file_id
        except Exception as e:
            log.error(f"An error occurred during OneDrive file upload: {e}")
            return None

    def download_file(self, remote_file_id: str, local_path: str) -> bool:
        """Downloads a file from OneDrive."""
        if not self.access_token:
            if not self.authenticate():
                return False
        
        try:
            log.info(f"Starting download of file ID '{remote_file_id}' to '{local_path}'.")
            url = f"https://graph.microsoft.com/v1.0/me/drive/items/{remote_file_id}/content"
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            with requests.get(url, headers=headers, stream=True) as r:
                r.raise_for_status()
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                with open(local_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            log.info(f"File '{remote_file_id}' downloaded successfully to '{local_path}'.")
            return True
        except Exception as e:
            log.error(f"Failed to download file from OneDrive: {e}")
            return False

    def get_remote_file_hash(self, remote_file_id: str) -> str | None:
        """Retrieves the hash (sha256) of a file in OneDrive."""
        if not self.access_token:
            if not self.authenticate():
                return None

        try:
            log.info(f"Fetching hash for file ID: {remote_file_id}")
            url = f"https://graph.microsoft.com/v1.0/me/drive/items/{remote_file_id}?$select=file"
            headers = {"Authorization": f"Bearer {self.access_token}"}
            resp = requests.get(url, headers=headers)
            resp.raise_for_status()
            hashes = resp.json().get('file', {}).get('hashes', {})
            # Prefer sha256, but fall back to others if needed
            sha256_hash = hashes.get('sha256Hash') or hashes.get('quickXorHash')
            log.info(f"Hash found: {sha256_hash}")
            return sha256_hash
        except Exception as e:
            log.error(f"Failed to get remote file hash for ID {remote_file_id}: {e}")
            return None

    def delete_file(self, remote_file_id: str) -> bool:
        """
        Permanently deletes a file from OneDrive.
        """
        if not self.access_token:
            if not self.authenticate():
                return False

        try:
            log.info(f"Attempting to delete file ID: {remote_file_id}")
            url = f"https://graph.microsoft.com/v1.0/me/drive/items/{remote_file_id}"
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            resp = requests.delete(url, headers=headers)
            resp.raise_for_status() # Will raise an exception for 4xx or 5xx status codes
            
            log.info(f"Successfully deleted file ID: {remote_file_id}")
            return True
        except Exception as e:
            log.error(f"Failed to delete file ID {remote_file_id}: {e}", exc_info=True)
            return False
