import os
import logging
import _io
from flask import current_app

logger = logging.getLogger(__name__)


def get_supabase_client():
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_KEY", "").strip()
    if not url or not key:
        return None
    try:
        from supabase import create_client
    except Exception:
        logger.warning("Supabase package not available; falling back to local uploads")
        return None

    try:
        return create_client(url, key)
    except Exception:
        logger.exception("Failed to create Supabase client")
        return None


def store_pod_bytes(
    filename, file_bytes, content_type=None, bucket_name=None, instance_path=None
):
    """Store bytes either in Supabase (if configured) or on local disk.

    Returns a marker string for supabase uploads ("supabase:bucket/path") or
    a local filename.
    """
    supa = get_supabase_client()
    if supa:
        bucket = bucket_name or os.getenv("SUPABASE_BUCKET", "pod-uploads")
        object_path = f"consignments/{filename}"
        supa.storage.from_(bucket).upload(
            object_path,
            _io.BytesIO(file_bytes),
            {"content-type": content_type or "application/octet-stream"},
        )
        return f"supabase:{bucket}/{object_path}"

    upload_folder = os.path.join(
        (instance_path or current_app.instance_path), "uploads"
    )
    os.makedirs(upload_folder, exist_ok=True)
    dest_path = os.path.join(upload_folder, filename)
    with open(dest_path, "wb") as file_handle:
        file_handle.write(file_bytes)
    return filename


def delete_pod_file(pod_value, instance_path=None):
    if not pod_value:
        return

    if isinstance(pod_value, str) and pod_value.startswith("supabase:"):
        client = get_supabase_client()
        if not client:
            return
        try:
            _, rest = pod_value.split(":", 1)
            bucket, object_path = rest.split("/", 1)
            client.storage.from_(bucket).remove([object_path])
        except Exception:
            logger.exception("Failed to remove POD from Supabase")
        return

    upload_folder = os.path.join(
        (instance_path or current_app.instance_path), "uploads"
    )
    pod_path = os.path.normpath(os.path.join(upload_folder, pod_value))
    if pod_path.startswith(os.path.abspath(upload_folder)) and os.path.exists(pod_path):
        try:
            os.remove(pod_path)
        except Exception:
            logger.exception("Failed to remove POD file from disk")


def get_pod_url(pod_value, ttl=None):
    """Return a URL for the given pod_value when possible.

    - If `pod_value` is an absolute http(s) URL, return it unchanged.
    - If `pod_value` is a Supabase marker ("supabase:bucket/path"), attempt
      to create a short signed URL (or fall back to public URL). Returns None
      when no URL can be generated (e.g., supabase not configured).
    """
    if not pod_value or not isinstance(pod_value, str):
        return None

    if pod_value.startswith("http://") or pod_value.startswith("https://"):
        return pod_value

    if pod_value.startswith("supabase:"):
        client = get_supabase_client()
        if not client:
            return None
        try:
            _, rest = pod_value.split(":", 1)
            bucket, object_path = rest.split("/", 1)
            if ttl is None:
                ttl = int(os.getenv("SUPABASE_SIGNED_URL_TTL", "30"))
            signed = client.storage.from_(bucket).create_signed_url(object_path, ttl)
            url = None
            if isinstance(signed, dict):
                url = (
                    signed.get("signedURL")
                    or signed.get("signed_url")
                    or signed.get("signedUrl")
                )
            if not url:
                pub = client.storage.from_(bucket).get_public_url(object_path)
                url = pub.get("publicURL") or pub.get("publicUrl")
            return url
        except Exception:
            logger.exception("Error generating Supabase POD URL")
            try:
                pub = client.storage.from_(bucket).get_public_url(object_path)
                return pub.get("publicURL") or pub.get("publicUrl")
            except Exception:
                return None

    return None
