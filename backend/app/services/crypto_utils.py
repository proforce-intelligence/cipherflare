"""
Encryption utilities for sensitive data like credentials
"""

import os
import logging
from cryptography.fernet import Fernet
from typing import Optional

logger = logging.getLogger(__name__)

# Use a consistent encryption key from environment variable
# In production, use AWS KMS, HashiCorp Vault, or similar
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", Fernet.generate_key().decode())

def get_cipher():
    """Get Fernet cipher with encryption key"""
    try:
        return Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)
    except Exception as e:
        logger.error(f"[Crypto] Failed to initialize cipher: {e}")
        raise

def encrypt_credential(plaintext: str) -> Optional[str]:
    """Encrypt a credential string"""
    if not plaintext:
        return None
    
    try:
        cipher = get_cipher()
        encrypted = cipher.encrypt(plaintext.encode())
        return encrypted.decode()
    except Exception as e:
        logger.error(f"[Crypto] Encryption failed: {e}")
        raise

def decrypt_credential(encrypted: str) -> Optional[str]:
    """Decrypt a credential string"""
    if not encrypted:
        return None
    
    try:
        # This handles cases where credentials weren't encrypted
        cipher = get_cipher()
        
        # Try to decrypt
        try:
            decrypted = cipher.decrypt(encrypted.encode())
            return decrypted.decode()
        except Exception as decrypt_error:
            # If decryption fails, the credential might already be plaintext
            logger.warning(f"[Crypto] Credential appears to be plaintext, not encrypted: {str(decrypt_error)[:50]}")
            return encrypted  # Return as-is if not encrypted
            
    except Exception as e:
        logger.error(f"[Crypto] Decryption failed: {e}")
        logger.warning(f"[Crypto] Returning plaintext credential due to decryption error")
        return encrypted
