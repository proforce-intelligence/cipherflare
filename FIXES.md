# Issues Fixed

## 1. Database Schema Error
**Problem**: `no such column: alerts.deactivated_at`
**Solution**: 
- Created migration script `scripts/migrate_database.py` to add missing column
- Added automatic migration on app startup
- Made code backward-compatible to handle missing column gracefully

## 2. File Serving 404 Errors
**Problem**: Files couldn't be accessed via `/files/` endpoint
**Solution**:
- Mounted StaticFiles middleware to serve the `dark_web_results` directory
- Changed file viewing from modal to direct download/open in new tab
- Added proper file path resolution in API

## 3. Crypto/Auth Errors
**Problem**: Worker fails when credentials aren't encrypted
**Solution**:
- Already fixed in previous update: crypto_utils.py now handles both encrypted and plaintext credentials
- Falls back gracefully if decryption fails

## 4. Threat Intelligence Not Updating
**Problem**: Alert counts stuck at 0
**Solution**:
- Fixed database query to exclude non-existent column during migration period
- Alerts API now returns proper array format
- Frontend properly handles empty states

## Running the Migration

The migration runs automatically on app startup. To manually run it:

\`\`\`bash
cd backend
python scripts/migrate_database.py
\`\`\`

## File Access

Files are now served via StaticFiles middleware:
- Text files: Click "View Text" to open in new tab
- Screenshots: Click "View Screenshot" to open in new tab  
- HTML: Click "Download HTML" to download

The files are served from `/files/` endpoint which maps to the `dark_web_results` directory.
