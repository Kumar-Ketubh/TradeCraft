# backend/app/adapters/hashing.py
import hashlib
from typing import Optional


def compute_content_hash(text: Optional[str]) -> str:
    """
    Compute a deterministic SHA-256 lowercase hexadecimal string from normalized text.
    If text is None, it is treated as an empty string.
    """
    if text is None:
        text = ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
