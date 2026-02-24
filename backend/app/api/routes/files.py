"""
File serving endpoint for screenshots and scraped text
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import logging
import os

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/files", tags=["files"])

# Robust directory detection
# Try environment variable, then common locations
env_output = os.getenv("OUTPUT_BASE")
if env_output:
    OUTPUT_BASE = Path(env_output).resolve()
else:
    # Check if we are running from root or backend
    cwd = Path.cwd()
    possible_paths = [
        cwd / "dark_web_results",
        cwd / "backend" / "dark_web_results",
        Path("/home/rootkit/cipherflare/backend/dark_web_results")
    ]
    
    OUTPUT_BASE = possible_paths[0] # Default
    for p in possible_paths:
        if p.exists() and p.is_dir():
            OUTPUT_BASE = p.resolve()
            break

logger.info(f"Serving files from: {OUTPUT_BASE}")

@router.get("/{file_path:path}")
async def serve_file(file_path: str):
    """
    Serve screenshot, text, or HTML files from the results directory
    """
    try:
        # Normalize the incoming path
        # The path from frontend usually starts with 'dark_web_results/'
        clean_path = file_path
        
        # Remove common redundant prefixes if they exist
        prefixes_to_strip = ["./", "backend/", "dark_web_results/"]
        
        for prefix in prefixes_to_strip:
            if clean_path.startswith(prefix):
                clean_path = clean_path[len(prefix):]
        
        # Special case: check if it still starts with dark_web_results after stripping other things
        if clean_path.startswith("dark_web_results/"):
            clean_path = clean_path[len("dark_web_results/"):]

        full_path = (OUTPUT_BASE / clean_path).resolve()
        
        # Log resolution for debugging if it fails
        if not full_path.exists():
            logger.error(f"File not found: {full_path} (Requested: {file_path})")
            # Try one more fallback: join directly if it was a deep path
            alt_path = (OUTPUT_BASE.parent / file_path).resolve()
            if alt_path.exists() and str(alt_path).startswith(str(OUTPUT_BASE.parent.resolve())):
                full_path = alt_path
            else:
                raise HTTPException(status_code=404, detail="File not found")
        
        # Security: Ensure the path is within a valid results directory
        # We allow OUTPUT_BASE or its parent (to be safe during transitions)
        safe_root = OUTPUT_BASE.parent.resolve()
        if not str(full_path).startswith(str(safe_root)):
            logger.warning(f"Access denied attempt: {full_path} outside of {safe_root}")
            raise HTTPException(status_code=403, detail="Access denied")
        
        if not full_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        if not full_path.is_file():
            raise HTTPException(status_code=400, detail="Not a file")
        
        # Determine media type
        suffix = full_path.suffix.lower()
        media_type = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.txt': 'text/plain',
            '.html': 'text/html',
        }.get(suffix, 'application/octet-stream')
        
        return FileResponse(
            path=str(full_path),
            media_type=media_type,
            filename=full_path.name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File serving error: {e}")
        raise HTTPException(status_code=500, detail="Failed to serve file")
