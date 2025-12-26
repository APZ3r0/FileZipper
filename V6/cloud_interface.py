from abc import ABC, abstractmethod

class CloudStorageProvider(ABC):
    """
    An abstract base class that defines the interface for a cloud storage provider.
    This ensures that all cloud connectors (Google Drive, OneDrive, etc.)
    have a consistent set of methods for the application to use.
    """

    @abstractmethod
    def authenticate(self):
        """
        Handles the authentication flow (e.g., OAuth2) to get valid credentials.
        Should return True on success, False on failure.
        """
        pass

    @abstractmethod
    def is_authenticated(self) -> bool:
        """
        Checks if the provider has valid, non-expired credentials.
        :return: True if authenticated, False otherwise.
        """
        pass

    @abstractmethod
    def get_free_space(self) -> int | None:
        """
        Returns the available free space in the cloud storage in bytes.
        Returns None if the information could not be retrieved.
        """
        pass

    @abstractmethod
    def upload_file(self, local_path: str, remote_folder: str) -> str | None:
        """
        Uploads a single file to the specified remote folder.
        This method should handle the entire resumable upload process.

        :param local_path: The local path of the file to upload.
        :param remote_folder: The name or ID of the remote folder to upload into.
        :return: The ID of the newly created remote file, or None on failure.
        """
        pass

    @abstractmethod
    def download_file(self, remote_file_id: str, local_path: str) -> bool:
        """
        Downloads a single file from the cloud.

        :param remote_file_id: The unique identifier of the file in the cloud.
        :param local_path: The local path to save the downloaded file to.
        :return: True on success, False on failure.
        """
        pass

    @abstractmethod
    def get_remote_file_hash(self, remote_file_id: str) -> str | None:
        """
        Retrieves the hash (e.g., MD5) of a file that is already in the cloud.

        :param remote_file_id: The unique identifier of the file in the cloud.
        :return: The hash string of the remote file, or None if not available.
        """
        pass

    @abstractmethod
    def get_display_name(self) -> str:
        """
        Returns a user-friendly name for the cloud provider (e.g., "Google Drive").
        """
        pass
