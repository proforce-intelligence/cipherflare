"""
Live Mirror API - Real-time .onion site mirroring
"""

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.database import get_db
from app.api.deps import get_current_user
from app.services.live_mirror_manager import LiveMirrorManager
import logging
import asyncio
import json
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["live_mirror"])

# Global live mirror manager
_live_mirror_manager: Optional[LiveMirrorManager] = None

def get_live_mirror_manager() -> LiveMirrorManager:
    """Get or create live mirror manager instance"""
    global _live_mirror_manager
    if _live_mirror_manager is None:
        _live_mirror_manager = LiveMirrorManager()
    return _live_mirror_manager

@router.post("/monitor/live")
async def start_live_mirror(
    url: str = Query(..., description="Full .onion URL to mirror", min_length=10, regex=r"^http://.*\.onion"),
    javascript_enabled: bool = Query(False, description="Enable JavaScript (security risk)"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Start a live mirroring session for a .onion URL
    Returns session_id and WebSocket URL
    """
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    manager = get_live_mirror_manager()
    
    try:
        session_id = await manager.create_session(user_id, url, javascript_enabled)
        
        if not session_id:
            raise HTTPException(status_code=500, detail="Failed to create live mirror session")
        
        logger.info(f"[LiveMirror] Started session {session_id} for {url}")
        
        return {
            "success": True,
            "session_id": session_id,
            "message": f"Live mirroring started for {url}",
            "websocket_url": f"/api/v1/ws/live/{session_id}",
            "config": {
                "url": url,
                "javascript_enabled": javascript_enabled,
                "timeout_minutes": manager.session_timeout_minutes
            }
        }
    except Exception as e:
        logger.error(f"[LiveMirror] Failed to start session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/monitor/live/{session_id}/navigate")
async def navigate_live_mirror(
    session_id: str,
    url: str = Query(..., description="URL to navigate to"),
    current_user: dict = Depends(get_current_user)
):
    """Navigate to a different URL in an active live mirror session"""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    manager = get_live_mirror_manager()
    session = manager.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    success = await session.navigate(url)
    
    if not success:
        raise HTTPException(status_code=500, detail="Navigation failed")
    
    return {
        "success": True,
        "message": f"Navigated to {url}",
        "current_url": url
    }

@router.delete("/monitor/live/{session_id}")
async def stop_live_mirror(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Stop an active live mirror session"""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    manager = get_live_mirror_manager()
    session = manager.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    await manager.close_session(session_id)
    
    return {
        "success": True,
        "message": "Live mirror session stopped"
    }

@router.websocket("/ws/live/{session_id}")
async def live_mirror_websocket(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for live mirror streaming
    Streams page snapshots (HTML + screenshots) to client
    """
    await websocket.accept()
    
    manager = get_live_mirror_manager()
    session = manager.get_session(session_id)
    
    if not session:
        await websocket.send_json({"type": "error", "message": "Session not found"})
        await websocket.close()
        return
    
    try:
        logger.info(f"[LiveMirror] WebSocket connected for session {session_id}")
        
        # Send initial snapshot
        snapshot = await session.get_snapshot()
        await websocket.send_json({"type": "snapshot", "data": snapshot})
        
        # Stream updates
        while session.is_active:
            try:
                # Wait for client message or timeout
                message = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=2.0
                )
                
                # Handle client requests
                if message.get("type") == "refresh":
                    snapshot = await session.get_snapshot()
                    await websocket.send_json({"type": "snapshot", "data": snapshot})
                elif message.get("type") == "navigate":
                    url = message.get("url")
                    if url:
                        success = await session.navigate(url)
                        if success:
                            snapshot = await session.get_snapshot()
                            await websocket.send_json({"type": "snapshot", "data": snapshot})
                        else:
                            await websocket.send_json({"type": "error", "message": "Navigation failed"})
                
            except asyncio.TimeoutError:
                # No message from client, send periodic update
                snapshot = await session.get_snapshot()
                await websocket.send_json({"type": "snapshot", "data": snapshot})
            except WebSocketDisconnect:
                logger.info(f"[LiveMirror] WebSocket disconnected for session {session_id}")
                break
    
    except Exception as e:
        logger.error(f"[LiveMirror] WebSocket error for session {session_id}: {e}")
        await websocket.send_json({"type": "error", "message": str(e)})
    
    finally:
        await websocket.close()
        logger.info(f"[LiveMirror] WebSocket closed for session {session_id}")
