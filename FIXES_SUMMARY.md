# Fixes Applied - Job Results and File Preview

## Issues Fixed

### 1. React Error: "Objects are not valid as a React child"
**Problem**: The `summary` field from the AI summary API was an object being rendered directly in React.

**Solution**: Updated `frontend/app/investigations/page.tsx` to properly extract the text from the summary object:
\`\`\`tsx
{typeof aiSummary.summary === "string"
  ? aiSummary.summary
  : aiSummary.summary?.summary || "No summary available"}
\`\`\`

### 2. File Paths Not Working
**Problem**: Files were saved with absolute paths like `/path/to/dark_web_results/...` but the file serving API needed relative paths from `dark_web_results/`.

**Solution**: Updated `backend/app/services/worker.py` to save relative paths:
\`\`\`python
meta["screenshot_file"] = str(shot_path.relative_to(OUTPUT_BASE))
meta["text_file"] = str(text_path.relative_to(OUTPUT_BASE))
meta["raw_html_file"] = str(html_path.relative_to(OUTPUT_BASE))
\`\`\`

### 3. No Preview Buttons for Screenshots and Text
**Problem**: Users couldn't view the scraped content easily.

**Solution**: 
- Added file serving endpoints in `backend/app/api/routes/files.py`:
  - `/api/v1/files/screenshot?path=...`
  - `/api/v1/files/text?path=...`
  - `/api/v1/files/html?path=...`
- Added preview buttons in the findings display with modal dialogs
- Screenshots display as images
- Text files display in formatted `<pre>` blocks

### 4. Auto-Generate Summary Removed
**Problem**: Summary was being generated automatically when clicking on completed jobs, causing delays.

**Solution**: 
- Removed auto-generation from `handleViewJobResults`
- Added dedicated "Generate AI Summary" button that only appears when viewing results
- Summary is generated on-demand and cached in state

## File Structure

Files are now saved with this structure:
\`\`\`
dark_web_results/
├── {keyword}_{timestamp}_{job_id}/
│   ├── {site_hash}_{url_hash}/
│   │   ├── {site_hash}_{url_hash}.html
│   │   ├── {site_hash}_{url_hash}.png
│   │   └── {site_hash}_{url_hash}.txt
\`\`\`

And stored in Elasticsearch as relative paths:
\`\`\`json
{
  "screenshot_file": "{keyword}_{timestamp}_{job_id}/{site_hash}_{url_hash}/{file}.png",
  "text_file": "{keyword}_{timestamp}_{job_id}/{site_hash}_{url_hash}/{file}.txt",
  "html_file": "{keyword}_{timestamp}_{job_id}/{site_hash}_{url_hash}/{file}.html"
}
\`\`\`

## API Endpoints

### Get Screenshot
\`\`\`
GET /api/v1/files/screenshot?path={relative_path}
\`\`\`

### Get Text Content
\`\`\`
GET /api/v1/files/text?path={relative_path}
\`\`\`

### Generate AI Summary
\`\`\`
GET /api/v1/findings/summary/{job_id}?model={model}&pgp_verify={bool}
\`\`\`

## Testing Checklist

- [x] Click on completed job to view results
- [x] Results display without React errors
- [x] "View Screenshot" button opens modal with image
- [x] "View Text" button opens modal with text content
- [x] "Generate AI Summary" button generates summary on demand
- [x] Summary displays properly as text
- [x] Export button works correctly
- [x] File paths are properly encoded in URLs
- [x] Security: Directory traversal is prevented in file serving

## Debug Logs Added

Added debug console.log statements to track:
- API responses from job results
- Screenshot and text file paths
- Text fetch errors with response details

These can be viewed in the browser console for troubleshooting.
