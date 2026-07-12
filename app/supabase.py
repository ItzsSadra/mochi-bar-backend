import os
import logging
from supabase import create_client, Client

logger = logging.getLogger(__name__)

_client: Client | None = None

BUCKET = "images"


def get_supabase() -> Client:
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_ANON_KEY")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_ANON_KEY must be set")
        _client = create_client(url, key)
    return _client


def upload_to_storage(folder: str, filename: str, data: bytes, content_type: str) -> str:
    path = f"{folder}/{filename}"
    supabase = get_supabase()
    supabase.storage.from_(BUCKET).upload(
        path,
        data,
        {"content-type": content_type, "cache-control": "3600"},
    )
    public_url = supabase.storage.from_(BUCKET).get_public_url(path)
    logger.info("Uploaded to Supabase Storage: %s", path)
    return public_url


def delete_from_storage(path: str) -> None:
    supabase = get_supabase()
    try:
        supabase.storage.from_(BUCKET).remove([path])
        logger.info("Deleted from Supabase Storage: %s", path)
    except Exception:
        logger.warning("Failed to delete from Supabase Storage: %s", path, exc_info=True)


def extract_storage_path(file_path: str) -> str | None:
    prefix = f"/storage/v1/object/public/{BUCKET}/"
    if prefix in file_path:
        return file_path.split(prefix, 1)[1]
    return None
