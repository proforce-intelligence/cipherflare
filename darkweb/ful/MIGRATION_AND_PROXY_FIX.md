# Database Migration & Live Mirror Proxy Fix

## Issues Resolved

### 1. Database Schema Error
**Problem**: `alerts.deactivated_at` column missing, causing SQLite errors
**Solution**: Automatic migration on app startup
- Added migration function in `app/main.py`
- Runs on every app start, checks if column exists
- Adds column if missing, logs if already present
- No manual SQL script execution needed

### 2. Live Mirror Not Interactive
**Problem**: Live mirror showing static HTML only, no clickable links or navigation
**Solution**: Implemented interactive proxy endpoint
- New `/api/v1/monitor/live/{session_id}/proxy` endpoint
- Rewrites HTML to route all links through proxy
- Allows full navigation within the .onion site
- Intercepts form submissions
- Uses iframe for seamless browsing experience

## Features Added

### Interactive Proxy
- Click any link to navigate
- Form submissions supported
- All URLs routed through secure proxy
- Maintains active Playwright session
- Real-time navigation tracking

### Frontend Improvements
- Iframe-based viewer for native browsing experience
- "Open in new tab" button for full-screen viewing
- Better loading states and error handling
- Sandbox security for iframe

## Usage

1. **Database Migration**: Automatic - just restart the backend
2. **Live Mirror**: Start a session, then click any link to browse interactively

The live mirror now functions like a real browser with full interactivity!
