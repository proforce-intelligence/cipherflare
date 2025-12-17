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

OUTPUT_BASE = Path(os.getenv("OUTPUT_BASE", "./dark_web_results"))

@router.get("/{file_path:path}")
async def serve_file(file_path: str):
    """
    Serve screenshot, text, or HTML files from the results directory
    """
    try:
        # Security: Ensure the path is within OUTPUT_BASE
        full_path = (OUTPUT_BASE / file_path).resolve()
        
        # Prevent directory traversal attacks
        if not str(full_path).startswith(str(OUTPUT_BASE.resolve())):
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
