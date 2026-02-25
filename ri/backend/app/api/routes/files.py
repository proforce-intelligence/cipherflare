"""
File serving endpoint for screenshots and scraped text
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import logging
import os
import glob

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/files", tags=["files"])

# DEFINITIVE ROOT DETECTION
# We force detection of the 'dark_web_results' folder wherever it may be
def get_output_base():
    # 1. Check ENV
    env_output = os.getenv("OUTPUT_BASE")
    if env_output:
        return Path(env_output).resolve()
    
    # 2. Check common absolute locations
    possible_roots = [
        Path("/home/rootkit/cipherflare/backend/dark_web_results"),
        Path("/home/rootkit/cipherflare/dark_web_results"),
        Path(os.getcwd()) / "backend" / "dark_web_results",
        Path(os.getcwd()) / "dark_web_results"
    ]
    
    for p in possible_roots:
        if p.exists() and p.is_dir():
            return p.resolve()
    
    return possible_roots[0] # Fallback to default

OUTPUT_BASE = get_output_base()
logger.info(f"[*] File Server active. Base directory: {OUTPUT_BASE}")

@router.get("/{file_path:path}")
async def serve_file(file_path: str):
    """
    Serve screenshot files with high-resiliency path resolution
    """
    try:
        # Normalize the filename
        filename = Path(file_path).name
        
        # 1. TRY DIRECT RESOLUTION
        # Strip all known prefixes to get the relative part
        clean_rel_path = file_path
        for prefix in ["./", "backend/", "dark_web_results/", "/"]:
            if clean_rel_path.startswith(prefix):
                clean_rel_path = clean_rel_path[len(prefix):]
        
        full_path = (OUTPUT_BASE / clean_rel_path).resolve()
        
        # 2. IF DIRECT FAILED, TRY FILENAME SEARCH (The "Bulletproof" method)
        if not full_path.exists():
            logger.info(f"[!] Path failed: {full_path}. Searching for: {filename}")
            # Search recursively for the filename within the results directory
            search_pattern = str(OUTPUT_BASE / "**" / filename)
            matches = glob.glob(search_pattern, recursive=True)
            
            if matches:
                full_path = Path(matches[0]).resolve()
                logger.info(f"[✓] File recovered via search: {full_path}")
            else:
                # One last try: Search one level up in case 'backend' is the parent
                search_pattern_alt = str(OUTPUT_BASE.parent / "**" / filename)
                matches_alt = glob.glob(search_pattern_alt, recursive=True)
                if matches_alt:
                    full_path = Path(matches_alt[0]).resolve()
                    logger.info(f"[✓] File recovered via parent search: {full_path}")
                else:
                    logger.error(f"[×] 404 - File not found anywhere: {filename}")
                    raise HTTPException(status_code=404, detail="Screenshot not found on disk")

        # 3. SECURITY CHECK
        # Ensure we are only serving from the cipherflare project directory
        if "cipherflare" not in str(full_path):
            raise HTTPException(status_code=403, detail="Access denied")
        
        if not full_path.is_file():
            raise HTTPException(status_code=400, detail="Path is a directory, not a file")
        
        # 4. SERVE
        return FileResponse(
            path=str(full_path),
            media_type="image/png" if full_path.suffix.lower() == ".png" else "application/octet-stream",
            filename=full_path.name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Critical error serving file: {e}")
        raise HTTPException(status_code=500, detail=str(e))
