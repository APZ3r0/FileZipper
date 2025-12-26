import logging
import httplib2
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google_auth_httplib2 import AuthorizedHttp
import os

log = logging.getLogger(__name__)

# --- Constants ---
CLIENT_SECRET_FILE = 'client_secret_846456975010-em6adqe1id3bq8ehssis1llhsr8l1r64.apps.googleusercontent.com.json'
TOKEN_FILE = 'token.json'
SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive.metadata.readonly',
    'https://www.googleapis.com/auth/gmail.send'
]

class _AuthManager:
    """
    A singleton class to manage Google API authentication and service creation.
    Ensures that credentials and service objects are created only once.
    """
    _instance = None
    _creds = None
    _drive_service = None
    _gmail_service = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(_AuthManager, cls).__new__(cls)
        return cls._instance

    def _authenticate(self):
        """
        Handles the full authentication flow, including token refresh.
        This is the core logic that ensures we have valid credentials.
        """
        if self._creds and self._creds.valid:
            return True

        if os.path.exists(TOKEN_FILE):
            try:
                self._creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
            except Exception as e:
                log.error(f"Failed to load credentials from {TOKEN_FILE}: {e}")
                self._creds = None

        if not self._creds or not self._creds.valid:
            if self._creds and self._creds.expired and self._creds.refresh_token:
                log.info("Google API token is expired, attempting to refresh.")
                try:
                    self._creds.refresh(Request())
                    log.info("Google API token refreshed successfully.")
                except Exception as e:
                    log.error(f"Failed to refresh Google API token: {e}. Re-authentication is required.")
                    self._creds = None # Force re-authentication
            
            if not self._creds:
                log.info("No valid credentials found, starting full OAuth flow.")
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
                    self._creds = flow.run_local_server(port=0)
                    log.info("OAuth flow completed successfully.")
                except Exception as e:
                    log.error(f"Failed to complete OAuth flow: {e}", exc_info=True)
                    return False

            # Save the new or refreshed credentials
            with open(TOKEN_FILE, 'w') as token:
                token.write(self._creds.to_json())
                log.info(f"Credentials saved to {TOKEN_FILE}")
        
        return self._creds and self._creds.valid

    def _get_service(self, service_name, version):
        """Generic method to get a Google API service object."""
        if not self._authenticate():
            log.error("Authentication failed. Cannot create API service.")
            return None
        
        try:
            http_with_timeout = httplib2.Http(timeout=60)
            authorized_http = AuthorizedHttp(self._creds, http=http_with_timeout)
            service = build(service_name, version, http=authorized_http)
            log.info(f"Google API service '{service_name}' built successfully with a 60-second timeout.")
            return service
        except Exception as e:
            log.error(f"Failed to build Google {service_name} service: {e}", exc_info=True)
            return None

    def get_drive_service(self):
        """Returns a pre-built, authenticated Google Drive service object."""
        if not self._drive_service:
            self._drive_service = self._get_service('drive', 'v3')
        return self._drive_service

    def get_gmail_service(self):
        """Returns a pre-built, authenticated Gmail service object."""
        if not self._gmail_service:
            self._gmail_service = self._get_service('gmail', 'v1')
        return self._gmail_service

# --- Public Functions ---
# These are the functions that the rest of the application should use.

_auth_manager_instance = _AuthManager()

def get_drive_service():
    """Provides global access to the Drive service singleton."""
    return _auth_manager_instance.get_drive_service()

def get_gmail_service():
    """Provides global access to the Gmail service singleton."""
    return _auth_manager_instance.get_gmail_service()
