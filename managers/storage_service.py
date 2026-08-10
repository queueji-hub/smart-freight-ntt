import os
import io
from abc import ABC, abstractmethod

class StorageProvider(ABC):
    """Abstract base class for Document Storage Providers (Local, S3, Supabase)."""

    @abstractmethod
    def upload(self, tenant_id: str, document_id: str, version: str, filename: str, file_bytes: bytes) -> str:
        """Upload a file and return the abstract storage key."""
        pass

    @abstractmethod
    def download(self, storage_key: str) -> bytes:
        """Download a file by its abstract storage key."""
        pass

    @abstractmethod
    def delete(self, storage_key: str) -> bool:
        """Delete a file by its abstract storage key."""
        pass

    @abstractmethod
    def exists(self, storage_key: str) -> bool:
        """Check if a file exists."""
        pass

    @abstractmethod
    def get_url(self, storage_key: str, expires_in: int = 3600) -> str:
        """Get a signed or direct URL for the file."""
        pass


class LocalStorageProvider(StorageProvider):
    """Local filesystem fallback provider for development."""

    def __init__(self, base_dir: str = "storage"):
        self.base_dir = base_dir

    def _get_path(self, storage_key: str) -> str:
        return os.path.join(self.base_dir, storage_key)

    def upload(self, tenant_id: str, document_id: str, version: str, filename: str, file_bytes: bytes) -> str:
        import re
        def _sec(val: str) -> str:
            val = re.sub(r'[^a-zA-Z0-9_.-]', '_', str(val))
            return val.strip('_')
        
        storage_key = os.path.join(_sec(tenant_id), _sec(document_id), _sec(version), _sec(filename))
        full_path = self._get_path(storage_key)
        
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as f:
            f.write(file_bytes)
            
        return storage_key

    def download(self, storage_key: str) -> bytes:
        full_path = self._get_path(storage_key)
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File not found: {storage_key}")
        with open(full_path, "rb") as f:
            return f.read()

    def delete(self, storage_key: str) -> bool:
        full_path = self._get_path(storage_key)
        if os.path.exists(full_path):
            os.remove(full_path)
            return True
        return False

    def exists(self, storage_key: str) -> bool:
        return os.path.exists(self._get_path(storage_key))

    def get_url(self, storage_key: str, expires_in: int = 3600) -> str:
        # Local storage doesn't easily support signed URLs natively without a proxy server.
        # Returning the relative path for now, but in production, Streamlit handles download via UI.
        return f"/download?key={storage_key}"


class SupabaseStorageProvider(StorageProvider):
    """Supabase object storage provider (Production)."""

    def __init__(self, bucket_name: str = "documents"):
        self.bucket_name = bucket_name
        import streamlit as st
        # Initialize Supabase client if available
        try:
            from supabase import create_client, Client
            url = st.secrets["SUPABASE_URL"]
            key = st.secrets["SUPABASE_KEY"]
            self.client: Client = create_client(url, key)
        except Exception as e:
            self.client = None

    def upload(self, tenant_id: str, document_id: str, version: str, filename: str, file_bytes: bytes) -> str:
        if not self.client:
            raise Exception("Supabase client not initialized")
        
        storage_key = f"{tenant_id}/{document_id}/{version}/{filename}"
        res = self.client.storage.from_(self.bucket_name).upload(
            path=storage_key,
            file=file_bytes,
            file_options={"content-type": "application/octet-stream"}
        )
        # Check res for errors if needed
        return storage_key

    def download(self, storage_key: str) -> bytes:
        if not self.client:
            raise Exception("Supabase client not initialized")
            
        res = self.client.storage.from_(self.bucket_name).download(storage_key)
        return res

    def delete(self, storage_key: str) -> bool:
        if not self.client:
            return False
            
        res = self.client.storage.from_(self.bucket_name).remove([storage_key])
        return len(res) > 0

    def exists(self, storage_key: str) -> bool:
        # Complex to check existence directly without listing, often download throws exception
        try:
            # We can use list to check
            parts = storage_key.split('/')
            if len(parts) > 1:
                path = '/'.join(parts[:-1])
                files = self.client.storage.from_(self.bucket_name).list(path)
                return any(f['name'] == parts[-1] for f in files)
            return False
        except:
            return False

    def get_url(self, storage_key: str, expires_in: int = 3600) -> str:
        if not self.client:
            return ""
        return self.client.storage.from_(self.bucket_name).create_signed_url(storage_key, expires_in)["signedURL"]


# Singleton Factory Pattern
_storage_provider = None

def get_storage_provider() -> StorageProvider:
    global _storage_provider
    if _storage_provider is None:
        import streamlit as st
        provider_type = st.secrets.get("STORAGE_PROVIDER", "LOCAL").upper()
        if provider_type == "SUPABASE":
            try:
                _storage_provider = SupabaseStorageProvider()
            except Exception as e:
                print(f"Failed to init Supabase storage, falling back to LOCAL: {e}")
                _storage_provider = LocalStorageProvider()
        else:
            _storage_provider = LocalStorageProvider()
            
    return _storage_provider

