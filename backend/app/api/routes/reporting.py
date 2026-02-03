# app/api/v1/reporting.py
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
from typing import Optional
import os
import logging
import secrets
import uuid

from app.database.database import get_db
from app.api.deps import get_current_user
from app.models.report import Report, ReportType, ReportStatus
from app.services.es_client import ESClient
from app.services.report_generator import generate_pdf_report
from app.services.report_llm import generate_report_content
from app.services.report_generator import env

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["reporting"])




@router.post("/reports/generate")
async def generate_report(
    background_tasks: BackgroundTasks,
    report_type: ReportType = Query(..., description="Type of report"),
    title: str = Query(..., min_length=5, description="Report title"),
    keyword: str = Query(None, description="Filter by keyword"),
    date_from: str = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: str = Query(None, description="End date (YYYY-MM-DD)"),
    model_choice: str = Query("gemini-2.5-flash", description="LLM model for content generation"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Start generation of a threat intelligence report (executive, technical, or comprehensive)
    """
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    if not title.strip():
        raise HTTPException(status_code=400, detail="Title is required")

    # Create report record
    report = Report(
        user_id=user_id,
        title=title.strip(),
        report_type=report_type,
        status=ReportStatus.GENERATING,
        filters={
            "keyword": keyword,
            "date_from": date_from,
            "date_to": date_to,
            "model_choice": model_choice
        }
    )

    db.add(report)
    await db.commit()
    await db.refresh(report)

    # Queue background generation
    background_tasks.add_task(
        create_report_task,
        report_id=report.id,
        db=db
    )

    return {
        "success": True,
        "report_id": str(report.id),
        "status": "generating",
        "message": f"{report_type.value.title()} report generation has started",
        "title": title
    }


async def create_report_task(report_id: str, db: AsyncSession):
    """
    Background task with progress updates:
    - Fetches findings
    - Generates LLM content
    - Renders PDF
    - Updates progress in DB
    """
    logger.info(f"Starting report generation task for report_id={report_id}")

    try:
        # Fetch report
        result = await db.execute(select(Report).where(Report.id == report_id))
        report = result.scalar_one_or_none()

        if not report:
            logger.error(f"Report {report_id} not found")
            return

        # ── Progress: 0% ──
        report.progress = 0
        report.status = ReportStatus.GENERATING
        await db.commit()

        # Fetch findings
        es = ESClient()
        findings = await es.search_all_user_findings(
            user_id=report.user_id,
            keyword=report.filters.get("keyword"),
            date_from=report.filters.get("date_from"),
            date_to=report.filters.get("date_to")
        )

        # ── Progress: 20% ──
        report.progress = 20
        await db.commit()

        logger.info(f"Found {len(findings)} findings for report {report_id}")

        # Get stats
        user_stats = await es.get_stats(user_id=report.user_id)

        # Count distinct jobs
        job_ids = set(f.get("job_id") for f in findings if f.get("job_id"))
        jobs_count = len(job_ids)

        time_period = "All time"
        date_from = report.filters.get("date_from")
        date_to = report.filters.get("date_to")
        if date_from or date_to:
            time_period = f"{date_from or '–'} to {date_to or 'present'}"

        # Generate LLM content
        report_content = await generate_report_content(
            report_type=report.report_type.value,
            title=report.title,
            findings=findings,
            jobs_count=jobs_count,
            time_period=time_period,
            model_choice=report.filters.get("model_choice", "gemini-2.5-flash")
        )

        # ── Progress: 40% ──
        report.progress = 40
        await db.commit()

        logger.info(f"LLM content generated ({len(report_content)} chars)")

        # Render PDF
        # ── Progress: 70% ──
        report.progress = 70
        await db.commit()

        filepath, size_mb = await generate_pdf_report(
            report=report,
            content=report_content,
            findings=findings,
            user_stats=user_stats
        )

        # Calculate stats
        threats_count = len([
            f for f in findings
            if isinstance(f, dict) and f.get("risk_level", "").lower() in ["high", "critical"]
        ])
        indicators_count = sum(
            len(f.get("indicators", [])) for f in findings if isinstance(f, dict)
        )

        # Final update
        report.status = ReportStatus.COMPLETED
        report.progress = 100
        report.file_path = filepath
        report.file_size_mb = size_mb
        report.threats_count = threats_count
        report.indicators_count = indicators_count
        report.completed_at = datetime.utcnow()

        await db.commit()

        logger.info(
            f"Report {report_id} completed | "
            f"size={size_mb}, threats={threats_count}, indicators={indicators_count}"
        )

    except Exception as e:
        logger.exception(f"Report generation failed for {report_id}")
        if report:
            report.status = ReportStatus.FAILED
            report.progress = 0  # or keep last known progress
            report.error_message = str(e)[:500]
            try:
                await db.commit()
            except Exception as commit_err:
                logger.error(f"Failed to save failure state: {commit_err}")



@router.get("/reports/{report_id}/status")
async def get_report_status(
    report_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current status and progress of a report generation
    Used for polling / progress bar in UI
    """
    try:
        report_uuid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(400, "Invalid report ID")

    result = await db.execute(
        select(Report).where(
            Report.id == report_uuid,
            Report.user_id == current_user.get("sub")
        )
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(404, "Report not found or access denied")

    return {
        "success": True,
        "report_id": report_id,
        "status": report.status.value,
        "progress": report.progress,
        "title": report.title,
        "type": report.report_type.value,
        "created_at": report.created_at.isoformat(),
        "completed_at": report.completed_at.isoformat() if report.completed_at else None,
        "error_message": report.error_message if report.status == ReportStatus.FAILED else None,
        "download_url": (
            f"/api/v1/reports/{report_id}/download"
            if report.status == ReportStatus.COMPLETED and report.file_path
            else None
        )
    }
# ────────────────────────────────────────────────
#               List all generated reports
# ────────────────────────────────────────────────


@router.get("/reports")
async def list_reports(
    # Pagination parameters
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    page_size: int = Query(10, ge=5, le=50, description="Number of reports per page (5–50)"),
    
    # Optional filters (you can extend later)
    status: Optional[str] = Query(None, description="Filter by status (pending/generating/completed/failed)"),
    
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    List user's generated reports with pagination
    """
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Calculate offset
    offset = (page - 1) * page_size

    # Base query
    query = select(Report).where(Report.user_id == user_id)

    # Optional status filter
    if status:
        try:
            status_enum = ReportStatus(status.lower())
            query = query.where(Report.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid status value. Must be one of: {', '.join(ReportStatus.__members__.keys())}"
            )

    # Order by most recent first
    query = query.order_by(Report.created_at.desc())

    # Get total count (for pagination metadata)
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one() or 0

    # Get paginated results
    paginated_query = query.offset(offset).limit(page_size)
    result = await db.execute(paginated_query)
    reports = result.scalars().all()

    # Build response
    return {
        "success": True,
        "pagination": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
            "has_next": offset + len(reports) < total,
            "has_previous": page > 1
        },
        "reports": [
            {
                "id": str(r.id),
                "code": f"RPT-{str(r.id)[:8].upper()}",
                "title": r.title,
                "type": r.report_type.value.capitalize(),
                "date": r.created_at.strftime("%Y-%m-%d"),
                "size": r.file_size_mb or "-",
                "status": r.status.value,
                "progress": r.progress if hasattr(r, 'progress') else 0,
                "threats": r.threats_count or 0,
                "indicators": r.indicators_count or 0,
                "download_url": (
                    f"/api/v1/reports/{r.id}/download"
                    if r.file_path and r.status == ReportStatus.COMPLETED
                    else None
                ),
                "preview_url": (
                    f"/api/v1/reports/{r.id}/preview"
                    if r.file_path and r.status == ReportStatus.COMPLETED
                    else None
                ),
                "error": r.error_message if r.status == ReportStatus.FAILED else None
            }
            for r in reports
        ]
    }

# ────────────────────────────────────────────────
#               Download completed report
# ────────────────────────────────────────────────

@router.get("/reports/{report_id}/download")
async def download_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        report_uuid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(400, "Invalid report ID")

    result = await db.execute(
        select(Report).where(
            Report.id == report_uuid,
            Report.user_id == current_user["sub"]
        )
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(404, "Report not found or access denied")

    if report.status != ReportStatus.COMPLETED:
        raise HTTPException(400, f"Report is {report.status.value} — not ready for download")

    if not report.file_path or not os.path.exists(report.file_path):
        raise HTTPException(404, "Report file not found on server")

    return FileResponse(
        path=report.file_path,
        filename=f"{report.title.replace(' ', '_')}.pdf",
        media_type="application/pdf"
    )



@router.get("/reports/{report_id}/preview")
async def preview_report(
    report_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns an HTML preview of the report for the owner
    Useful for the "Preview" button in the UI
    """
    try:
        report_uuid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(400, "Invalid report ID")

    result = await db.execute(
        select(Report).where(
            Report.id == report_uuid,
            Report.user_id == current_user.get("sub")
        )
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(404, "Report not found or you don't have access")

    if report.status != ReportStatus.COMPLETED:
        raise HTTPException(400, f"Report is {report.status.value} — not ready for preview")

    # Option 1: If you stored the raw markdown/text content → render it
    # Option 2: Re-generate preview using the same template logic as PDF

    # We'll use Jinja2 + same template as PDF generation for consistency
    try:
        template_name = {
            ReportType.COMPREHENSIVE: "comprehensive.html",
            ReportType.EXECUTIVE: "executive.html",
            ReportType.TECHNICAL: "technical.html"
        }[report.report_type]

        template = env.get_template(template_name)

        # Re-fetch findings for accurate preview (or store them if you want to optimize)
        es = ESClient()
        findings = await es.search_all_user_findings(
            user_id=report.user_id,
            keyword=report.filters.get("keyword"),
            date_from=report.filters.get("date_from"),
            date_to=report.filters.get("date_to")
        )

        html_content = template.render(
            report=report,
            findings=findings[:100],  # limit for preview
            generated_at=datetime.utcnow().strftime("%B %d, %Y at %H:%M UTC"),
            total_threats=len([f for f in findings if f.get("risk_level") in ["high", "critical"]]),
            total_indicators=sum(len(f.get("indicators", [])) for f in findings)
        )

        return HTMLResponse(content=html_content)

    except Exception as e:
        logger.exception(f"Preview generation failed for report {report_id}")
        raise HTTPException(500, f"Failed to generate preview: {str(e)}")


# ────────────────────────────────────────────────
#               SHARE ENDPOINT (create share link)
# ────────────────────────────────────────────────

@router.post("/reports/{report_id}/share")
async def share_report(
    report_id: str,
    expires_in_hours: int = Query(24, ge=1, le=168, description="Link expiration in hours (1–168)"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a temporary shareable public link for a completed report
    """
    try:
        report_uuid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(400, "Invalid report ID")

    result = await db.execute(
        select(Report).where(
            Report.id == report_uuid,
            Report.user_id == current_user.get("sub")
        )
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(404, "Report not found or access denied")

    if report.status != ReportStatus.COMPLETED:
        raise HTTPException(400, "Only completed reports can be shared")

    if not report.file_path:
        raise HTTPException(400, "Report file is missing")

    # Generate or refresh share token
    now = datetime.now(timezone.utc)
    if (
        not report.share_token or
        not report.share_expires_at or
        report.share_expires_at < now
    ):
        report.share_token = secrets.token_urlsafe(32)
        report.share_expires_at = now + timedelta(hours=expires_in_hours)
        report.is_publicly_shared = True
        await db.commit()
        await db.refresh(report)

    # Build share URL (replace with your actual domain in production)
    base_url = "http://localhost:8000"  # ← change to your real domain!
    share_url = f"{base_url}/api/v1/reports/shared/{report.share_token}"

    return {
        "success": True,
        "share_url": share_url,
        "expires_at": report.share_expires_at.isoformat(),
        "expires_in_hours": expires_in_hours,
        "report_id": report_id,
        "title": report.title
    }


# ────────────────────────────────────────────────
#       PUBLIC VIEW ENDPOINT (via share token)
# ────────────────────────────────────────────────

@router.get("/reports/shared/{share_token}")
async def view_shared_report(
    share_token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Public endpoint — view or download a shared report using the share token
    No authentication required
    """
    result = await db.execute(
        select(Report).where(Report.share_token == share_token)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(404, "Shared report not found")

    if not report.is_publicly_shared:
        raise HTTPException(403, "This report is no longer publicly shared")

    now = datetime.now(timezone.utc)
    if report.share_expires_at and report.share_expires_at < now:
        raise HTTPException(410, "This share link has expired")

    if not report.file_path or not os.path.exists(report.file_path):
        raise HTTPException(404, "Report file is no longer available")

    # Serve the PDF file directly
    return FileResponse(
        path=report.file_path,
        filename=f"{report.title.replace(' ', '_')}.pdf",
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename={report.title.replace(' ', '_')}.pdf"
        }
    )



@router.get("/reports/{report_id}")
async def get_report_details(
    report_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed metadata for a specific report
    Returns complete information including filters, stats, sharing status, and action URLs
    """
    try:
        report_uuid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid report ID format")

    # Fetch the report with user ownership check
    result = await db.execute(
        select(Report).where(
            Report.id == report_uuid,
            Report.user_id == current_user.get("sub")
        )
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=404, 
            detail="Report not found or you don't have access to this report"
        )

    # Calculate derived fields
    report_code = f"RPT-{str(report.id)[:8].upper()}"
    is_ready = report.status == ReportStatus.COMPLETED and report.file_path
    is_failed = report.status == ReportStatus.FAILED
    is_generating = report.status == ReportStatus.GENERATING

    # Build action URLs
    base_url = "http://localhost:8000"  # ← Replace with your actual domain
    action_urls = {
        "download": f"/api/v1/reports/{report_id}/download" if is_ready else None,
        "preview": f"/api/v1/reports/{report_id}/preview" if is_ready else None,
        "status": f"/api/v1/reports/{report_id}/status" if is_generating else None,
        "share": f"/api/v1/reports/{report_id}/share" if is_ready else None,
        "share_url": (
            f"{base_url}/api/v1/reports/shared/{report.share_token}" 
            if report.share_token and report.is_publicly_shared and report.share_expires_at 
            else None
        )
    }

    # Format dates
    created_at = report.created_at.isoformat() if report.created_at else None
    completed_at = report.completed_at.isoformat() if report.completed_at else None
    share_expires_at = report.share_expires_at.isoformat() if report.share_expires_at else None

    # Format filters (make them readable)
    formatted_filters = report.filters or {}
    if formatted_filters.get("date_from"):
        formatted_filters["date_from_display"] = formatted_filters["date_from"]
    if formatted_filters.get("date_to"):
        formatted_filters["date_to_display"] = formatted_filters["date_to"]
    if formatted_filters.get("keyword"):
        formatted_filters["keyword_display"] = formatted_filters["keyword"]

    # Calculate time elapsed (if completed)
    time_elapsed = None
    if report.completed_at and report.created_at:
        elapsed_seconds = (report.completed_at - report.created_at).total_seconds()
        if elapsed_seconds < 60:
            time_elapsed = f"{int(elapsed_seconds)}s"
        elif elapsed_seconds < 3600:
            time_elapsed = f"{int(elapsed_seconds // 60)}m"
        else:
            time_elapsed = f"{int(elapsed_seconds // 3600)}h"

    # Sharing status
    sharing_status = {
        "is_shared": report.is_publicly_shared,
        "share_token": report.share_token,
        "expires_at": share_expires_at,
        "is_expired": (
            report.share_expires_at 
            and report.share_expires_at < datetime.now(timezone.utc)
        ),
        "share_url": action_urls["share_url"]
    }

    return {
        "success": True,
        "report": {
            # Basic info
            "id": str(report.id),
            "code": report_code,
            "title": report.title,
            "type": report.report_type.value,
            "type_display": report.report_type.value.replace("_", " ").title(),

            # Status & progress
            "status": report.status.value,
            "progress": report.progress or 0,
            "is_ready": is_ready,
            "is_generating": is_generating,
            "is_failed": is_failed,

            # Stats
            "threats_count": report.threats_count or 0,
            "indicators_count": report.indicators_count or 0,
            "file_size_mb": report.file_size_mb or None,

            # Timestamps
            "created_at": created_at,
            "completed_at": completed_at,
            "time_elapsed": time_elapsed,
            "updated_at": report.updated_at.isoformat() if report.updated_at else None,

            # Filters used
            "filters": formatted_filters,
            "model_used": formatted_filters.get("model_choice", "gemini-2.5-flash"),

            # File & actions
            "file_path": report.file_path,
            "action_urls": action_urls,

            # Sharing
            "sharing": sharing_status,

            # Error (if any)
            "error_message": report.error_message if is_failed else None
        }
    }


@router.delete("/reports/{report_id}")
async def delete_report(
    report_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a report and its associated PDF file (if exists)

    - Only the owner can delete
    - Cannot delete reports that are still generating
    - Physically removes the PDF file from disk
    - Permanently deletes the record from the database
    """
    try:
        report_uuid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid report ID format"
        )

    # Fetch report with ownership check
    result = await db.execute(
        select(Report).where(
            Report.id == report_uuid,
            Report.user_id == current_user.get("sub")
        )
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found or you don't have permission to delete it"
        )

    # Prevent deletion of in-progress reports
    if report.status == ReportStatus.GENERATING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a report that is currently being generated. Please wait until it completes or fails."
        )

    try:
        # Delete physical file if it exists
        if report.file_path and os.path.exists(report.file_path):
            try:
                os.remove(report.file_path)
                logger.info(f"Deleted report file: {report.file_path}")
            except OSError as e:
                logger.warning(f"Failed to delete file {report.file_path}: {e}")
                # Continue anyway — don't fail the whole operation

        # Delete from database
        await db.execute(
            delete(Report).where(Report.id == report_uuid)
        )
        await db.commit()

        logger.info(f"Report {report_id} ({report.title}) deleted by user {current_user.get('sub')}")

        return {
            "success": True,
            "message": f"Report '{report.title}' (ID: {report_id}) has been deleted",
            "report_id": report_id,
            "title": report.title
        }

    except Exception as e:
        await db.rollback()
        logger.exception(f"Failed to delete report {report_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete report: {str(e)}"
        )