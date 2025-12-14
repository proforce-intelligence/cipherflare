# Environment Variable Fix for GOOGLE_API_KEY

## Problem
The API was failing to load `GOOGLE_API_KEY` or `GEMINI_API_KEY` even though they were set in `.env`.

## Root Cause
The `config.py` file was loading the environment variables but the application needed to be restarted to pick up changes.

## Solution Applied
1. Updated `config.py` to check both `GOOGLE_API_KEY` and `GEMINI_API_KEY` (with fallback)
2. Ensured proper environment variable loading

## Steps to Fix

### 1. Verify your .env file has the key
\`\`\`bash
cat .env | grep -E "GOOGLE_API_KEY|GEMINI_API_KEY"
\`\`\`

You should see:
\`\`\`
GOOGLE_API_KEY="AIzaSyCrBD1GwEU3rtTD7tdhSkucXS8ohpvpZJk"
GEMINI_API_KEY="AIzaSyCrBD1GwEU3rtTD7tdhSkucXS8ohpvpZJk"
\`\`\`

### 2. Restart the API server
**This is the most important step!** The server must be restarted to load new environment variables.

\`\`\`bash
# Stop the API server
pkill -f "uvicorn app.main:app"

# Or if running with a specific script
# Ctrl+C to stop it

# Start it again
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
\`\`\`

### 3. Test the API
\`\`\`bash
# Check if the environment variable is loaded
curl "http://localhost:8000/api/v1/findings/job/YOUR_JOB_ID?include_summary=true&model_choice=gemini-2.5-flash"
\`\`\`

## Verification

After restarting, you should NOT see these errors in the logs:
\`\`\`
ERROR:app.services.llm_utils:Failed to instantiate LLM gemini-2.5-flash: 1 validation error for ChatGoogleGenerativeAI
  Value error, API key required for Gemini Developer API
\`\`\`

## Note
- Environment variables are loaded when the Python process starts
- Changes to `.env` require a process restart to take effect
- Make sure your API key is valid and has the necessary permissions
