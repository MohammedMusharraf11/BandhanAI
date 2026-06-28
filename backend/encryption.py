"""
Fernet symmetric encryption for OAuth tokens stored in the integrations table.

Usage:
    from encryption import encrypt_token, decrypt_token
    
    encrypted = encrypt_token("my-secret-token")
    plaintext = decrypt_token(encrypted)

The encryption key is read from the ENCRYPTION_KEY environment variable.
Generate a key with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

import os
from cryptography.fernet import Fernet, InvalidToken

_key = os.getenv("ENCRYPTION_KEY")
_cipher = Fernet(_key.encode()) if _key else None


def encrypt_token(plaintext: str) -> str:
    """
    Encrypt a plaintext string (e.g., an OAuth token).
    Returns a URL-safe base64-encoded ciphertext string.
    
    Raises:
        RuntimeError: If ENCRYPTION_KEY is not configured.
    """
    if not _cipher:
        raise RuntimeError(
            "ENCRYPTION_KEY not configured. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    return _cipher.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_token(ciphertext: str) -> str:
    """
    Decrypt a Fernet-encrypted ciphertext string back to plaintext.
    
    Raises:
        RuntimeError: If ENCRYPTION_KEY is not configured.
        cryptography.fernet.InvalidToken: If the token is invalid or the key is wrong.
    """
    if not _cipher:
        raise RuntimeError(
            "ENCRYPTION_KEY not configured. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    return _cipher.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
