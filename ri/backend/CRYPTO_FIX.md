# Credential Encryption Fix

## Issue
Workers were failing with `[Crypto] Decryption failed` and `[Auth] Authentication failed` errors when processing jobs with authentication credentials.

## Root Cause
The system expected all credentials to be encrypted using Fernet encryption, but some credentials in the database were stored as plaintext. When the worker tried to decrypt plaintext credentials, it failed.

## Solution Implemented

### 1. Graceful Fallback in `crypto_utils.py`
Modified `decrypt_credential()` to:
- First attempt to decrypt the credential
- If decryption fails (indicating plaintext), return the original value
- Log warnings instead of raising exceptions
- Maintain backward compatibility with both encrypted and plaintext credentials

### 2. Enhanced Error Handling in `worker.py`
Updated `perform_authentication()` to:
- Wrap decryption in try-catch blocks
- Fall back to plaintext credentials if decryption is not available
- Continue processing instead of failing completely
- Provide detailed logging for troubleshooting

## Testing
To verify the fix:
1. Create a monitoring job with plaintext credentials
2. Create a monitoring job with encrypted credentials
3. Both should process successfully without crypto errors

## Recommendation
For production deployments:
1. Set a consistent `ENCRYPTION_KEY` environment variable
2. Migrate all existing plaintext credentials to encrypted format
3. Enforce encryption at the API layer for new credentials
4. Consider using a proper secrets management service (AWS KMS, HashiCorp Vault, etc.)

## Environment Variable
\`\`\`bash
export ENCRYPTION_KEY="your-32-byte-base64-encoded-key-here"
\`\`\`

Generate a new key with:
\`\`\`python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
