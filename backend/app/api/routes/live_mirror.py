"""
Live Mirror API - Real-time .onion site mirroring with history & diff support
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
from difflib import unified_diff


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["live_mirror"])

# Global live mirror manager
_live_mirror_manager: Optional[LiveMirrorManager] = None

def get_live_mirror_manager() -> LiveMirrorManager:
    global _live_mirror_manager
    if _live_mirror_manager is None:
        _live_mirror_manager = LiveMirrorManager()
    return _live_mirror_manager


@router.post("/monitor/live")
async def start_live_mirror(
    url: str = Query(..., description="Full .onion URL to mirror", min_length=10, pattern=r"^http://.*\.onion"),
    javascript_enabled: bool = Query(False, description="Enable JavaScript (security risk)"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
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
    await websocket.accept()

    manager = get_live_mirror_manager()
    session = manager.get_session(session_id)

    if not session:
        await websocket.send_json({"type": "error", "message": "Session not found"})
        await websocket.close()
        return

    try:
        logger.info(f"[LiveMirror] WebSocket connected for session {session_id}")

        # Send initial snapshot + analysis
        snapshot_data = await session.get_snapshot()
        await websocket.send_json({"type": "snapshot", "data": snapshot_data})

        # Check for high-risk alert on initial snapshot
        analysis = snapshot_data.get("analysis", {})
        if analysis.get("risk_score", 0) >= 70:
            await websocket.send_json({
                "type": "high_risk_alert",
                "data": {
                    "risk_score": analysis["risk_score"],
                    "alerts": analysis.get("alerts", []),
                    "timestamp": snapshot_data["timestamp"],
                    "url": snapshot_data["current_url"]
                }
            })

        while session.is_active:
            try:
                message = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=2.0
                )

                msg_type = message.get("type")

                # === NEW: Handle interactive user actions ===
                if msg_type in ["click", "type", "press_key", "scroll", "submit"]:
                    success = await session.execute_action(message)
                    if success:
                        # Give time for JavaScript / page to react
                        await asyncio.sleep(0.8)  # adjustable delay
                        # Capture and send updated snapshot
                        snapshot_data = await session.get_snapshot()
                        await websocket.send_json({"type": "snapshot", "data": snapshot_data})

                        # Also check for new high-risk alert after action
                        analysis = snapshot_data.get("analysis", {})
                        if analysis.get("risk_score", 0) >= 70:
                            await websocket.send_json({
                                "type": "high_risk_alert",
                                "data": {
                                    "risk_score": analysis["risk_score"],
                                    "alerts": analysis.get("alerts", []),
                                    "timestamp": snapshot_data["timestamp"],
                                    "url": snapshot_data["current_url"]
                                }
                            })
                    else:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Action execution failed"
                        })

                # Existing handlers
                elif msg_type == "refresh":
                    snapshot_data = await session.get_snapshot()
                    await websocket.send_json({"type": "snapshot", "data": snapshot_data})

                    # Check alert on refresh
                    analysis = snapshot_data.get("analysis", {})
                    if analysis.get("risk_score", 0) >= 70:
                        await websocket.send_json({
                            "type": "high_risk_alert",
                            "data": {
                                "risk_score": analysis["risk_score"],
                                "alerts": analysis.get("alerts", []),
                                "timestamp": snapshot_data["timestamp"],
                                "url": snapshot_data["current_url"]
                            }
                        })

                elif msg_type == "navigate":
                    url = message.get("url")
                    if url:
                        success = await session.navigate(url)
                        if success:
                            # Delay for page load
                            await asyncio.sleep(1.0)
                            snapshot_data = await session.get_snapshot()
                            await websocket.send_json({"type": "snapshot", "data": snapshot_data})

                            # Check alert after navigation
                            analysis = snapshot_data.get("analysis", {})
                            if analysis.get("risk_score", 0) >= 70:
                                await websocket.send_json({
                                    "type": "high_risk_alert",
                                    "data": {
                                        "risk_score": analysis["risk_score"],
                                        "alerts": analysis.get("alerts", []),
                                        "timestamp": snapshot_data["timestamp"],
                                        "url": snapshot_data["current_url"]
                                    }
                                })
                        else:
                            await websocket.send_json({"type": "error", "message": "Navigation failed"})

            except asyncio.TimeoutError:
                # Periodic snapshot + analysis
                snapshot_data = await session.get_snapshot()
                await websocket.send_json({"type": "snapshot", "data": snapshot_data})

                # Alert on periodic high-risk
                analysis = snapshot_data.get("analysis", {})
                if analysis.get("risk_score", 0) >= 70:
                    await websocket.send_json({
                        "type": "high_risk_alert",
                        "data": {
                            "risk_score": analysis["risk_score"],
                            "alerts": analysis.get("alerts", []),
                            "timestamp": snapshot_data["timestamp"],
                            "url": snapshot_data["current_url"]
                        }
                    })

            except WebSocketDisconnect:
                logger.info(f"[LiveMirror] WebSocket disconnected for session {session_id}")
                break

    except Exception as e:
        logger.error(f"[LiveMirror] WebSocket error for session {session_id}: {e}")
        await websocket.send_json({"type": "error", "message": str(e)})

    finally:
        await websocket.close()
        logger.info(f"[LiveMirror] WebSocket closed for session {session_id}")
# === NEW ENDPOINTS: History & Diff ===

@router.get("/monitor/live/{session_id}/snapshots")
async def list_session_snapshots(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get list of all saved snapshots for this session (for timeline)"""
    manager = get_live_mirror_manager()
    session = manager.get_session(session_id)

    if not session or session.user_id != current_user.get("sub"):
        raise HTTPException(status_code=403, detail="Not authorized")

    return {
        "snapshots": [
            {
                "id": s.id,
                "timestamp": s.timestamp.isoformat(),
                "url": s.current_url,
                "title": s.title
            }
            for s in session.snapshots
        ]
    }


@router.get("/monitor/live/{session_id}/snapshot/{snapshot_id}")
async def get_specific_snapshot(
    session_id: str,
    snapshot_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Retrieve a specific historical snapshot (HTML + screenshot)"""
    manager = get_live_mirror_manager()
    session = manager.get_session(session_id)

    if not session or session.user_id != current_user.get("sub"):
        raise HTTPException(status_code=403, detail="Not authorized")

    snapshot = session.get_snapshot_by_id(snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    return {
        "id": snapshot.id,
        "timestamp": snapshot.timestamp.isoformat(),
        "html": snapshot.html,
        "screenshot": snapshot.screenshot_base64,
        "url": snapshot.current_url,
        "title": snapshot.title
    }


@router.get("/monitor/live/{session_id}/diff")
async def get_snapshot_diff(
    session_id: str,
    base_id: int = Query(..., description="Base (older) snapshot ID"),
    compare_id: int = Query(..., description="Compare (newer) snapshot ID"),
    current_user: dict = Depends(get_current_user)
):
    """Get text diff (unified diff) between two snapshots"""
    manager = get_live_mirror_manager()
    session = manager.get_session(session_id)

    if not session or session.user_id != current_user.get("sub"):
        raise HTTPException(status_code=403, detail="Not authorized")

    base = session.get_snapshot_by_id(base_id)
    compare = session.get_snapshot_by_id(compare_id)

    if not base or not compare:
        raise HTTPException(status_code=404, detail="One or both snapshots not found")

    # Unified diff of HTML content
    diff_lines = unified_diff(
        base.html.splitlines(keepends=True),
        compare.html.splitlines(keepends=True),
        fromfile=f"snapshot_{base.id}.html",
        tofile=f"snapshot_{compare.id}.html",
        n=3  # context lines
    )
    text_diff = "".join(diff_lines)

    return {
        "base": {
            "id": base.id,
            "timestamp": base.timestamp.isoformat(),
            "url": base.current_url,
            "title": base.title,
            "screenshot": base.screenshot_base64
        },
        "compare": {
            "id": compare.id,
            "timestamp": compare.timestamp.isoformat(),
            "url": compare.current_url,
            "title": compare.title,
            "screenshot": compare.screenshot_base64
        },
        "text_diff": text_diff,
        # Visual diff is recommended to be calculated client-side using pixelmatch.js
    }

# @router.get("/monitor/live/{session_id}/analysis/{snapshot_id}")
# async def get_snapshot_analysis(
#     session_id: str,
#     snapshot_id: int,
#     current_user: dict = Depends(get_current_user)
# ):
#     """Get AI-powered content analysis for a specific historical snapshot"""
#     manager = get_live_mirror_manager()
#     session = manager.get_session(session_id)
# 
#     if not session or session.user_id != current_user.get("sub"):
#         raise HTTPException(status_code=403, detail="Not authorized")
# 
#     snapshot = session.get_snapshot_by_id(snapshot_id)
#     if not snapshot:
#         raise HTTPException(status_code=404, detail="Snapshot not found")
# 
#     # Re-analyze on demand (or you could store analysis in Snapshot if you want)
#     analysis = await session._analyze_content(snapshot.text)
#     return {"analysis": analysis}