from pathlib import Path
import tempfile

from config import get_settings


class StorageService:
    def __init__(self):
        self.settings = get_settings()

    def download(self, object_key: str, file_name: str) -> Path:
        suffix = Path(file_name).suffix or ".pdf"
        destination = Path(tempfile.mkdtemp(prefix="insuramind-doc-")) / f"input{suffix}"

        from minio import Minio

        endpoint = self.settings.minio_endpoint.replace("http://", "").replace("https://", "")
        secure = self.settings.minio_endpoint.startswith("https://")
        client = Minio(
            endpoint,
            access_key=self.settings.minio_access_key,
            secret_key=self.settings.minio_secret_key,
            secure=secure,
        )
        client.fget_object(self.settings.minio_bucket, object_key, str(destination))
        return destination
