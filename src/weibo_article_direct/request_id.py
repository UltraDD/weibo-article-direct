from __future__ import annotations

import base64
import hashlib
import time

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

_EDITOR_SECRET = b"wb-editor-v5"


def build_request_id(uid: str, timestamp_ms: int | None = None) -> str:
    """Build the editor request identifier from the current owner UID and time."""

    normalized_uid = str(uid).strip()
    if not normalized_uid:
        raise ValueError("uid is required")
    now_ms = int(time.time() * 1000) if timestamp_ms is None else int(timestamp_ms)
    plaintext = f"{normalized_uid}&{now_ms}".encode()
    key = hashlib.sha256(_EDITOR_SECRET).digest()
    padder = padding.PKCS7(algorithms.AES.block_size).padder()
    padded = padder.update(plaintext) + padder.finalize()
    encryptor = Cipher(algorithms.AES(key), modes.ECB()).encryptor()
    encrypted = encryptor.update(padded) + encryptor.finalize()
    return base64.urlsafe_b64encode(encrypted).decode("ascii").rstrip("=")
