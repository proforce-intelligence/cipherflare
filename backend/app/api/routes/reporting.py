# # app/api/v1/reporting.py (add/replace with this)
# 
# from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import select, or_
# from typing import Optional
# from datetime import datetime
# 
# from app.database.database import get_db
# from app.core.security import get_current_user
# from app.models.report import Report, ReportType, ReportStatus
# from app.models.job import Job, JobType
# from app.models.monitoring_job import MonitoringJob
# from app.models.monitoring_result import MonitoringResult
# from app.services.es_client import ESClient
# from app.services.report_generator import generate_pdf_report
# from app.services.report_llm import generate_report_content
# 
# router = APIRouter(prefix="/api/v1", tags=["reporting"])
# 
# @router.post("/reports/generate-targeted")
# async def generate_targeted_report(
#     background_tasks: BackgroundTasks,
#     report_type: ReportType = Query(..., description="Type of report"),
#     report_title: str = Query(..., min_length=5, description="Title for this report"),
#     job_name: Optional[str] = Query(None, description="Job name / keyword from search jobs"),
#     monitor_title: Optional[str] = Query(None, description="Title from monitoring jobs"),
#     date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
#     date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
#     model_choice: str = Query("llama3.1", description="Ollama model name"),
#     current_user: dict = Depends(get_current_user),
#     db: AsyncSession = Depends(get_db)
# ):
#     user_id = current_user.get("sub")
#     if not user_id:
#         raise HTTPException(status_code=401, detail="Authentication required")
# 
#     if not report_title.strip():
#         raise HTTPException(status_code=400, detail="Report title is required")
# 
#     if not job_name and not monitor_title:
#         raise HTTPException(
#             status_code=400,
#             detail="Provide at least one of: job_name or monitor_title"
#         )
# 
#     report = Report(
#         user_id=user_id,
#         title=report_title.strip(),
#         report_type=report_type,
#         status=ReportStatus.GENERATING,
#         filters={
#             "job_name": job_name,
#             "monitor_title": monitor_title,
#             "date_from": date_from,
#             "date_to": date_to,
#             "model_choice": model_choice
#         }
#     )
# 
#     db.add(report)
#     await db.commit()
#     await db.refresh(report)
# 
#     background_tasks.add_task(
#         create_targeted_report_task,
#         report_id=report.id,
#         db=db
#     )
# 
#     return {
#         "success": True,
#         "report_id": str(report.id),
#         "status": "generating",
#         "message": f"Generating {report_type.value} report: '{report_title}'",
#         "targeted": {
#             "job_name": job_name,
#             "monitor_title": monitor_title
#         }
#     }
# 
# 
# async def create_targeted_report_task(report_id: str, db: AsyncSession):
#     logger.info(f"Starting targeted report generation: {report_id}")
# 
#     try:
#         # Fetch report
#         result = await db.execute(select(Report).where(Report.id == report_id))
#         report = result.scalar_one_or_none()
#         if not report:
#             logger.error(f"Report not found: {report_id}")
#             return
# 
#         report.progress = 0
#         report.status = ReportStatus.GENERATING
#         await db.commit()
# 
#         # ── Find relevant job IDs ──────────────────────────────────────
#         search_job_ids = []
#         monitor_job_ids = []
# 
#         filters = report.filters or {}
# 
#         # 1. Search jobs by job_name / keyword
#         if filters.get("job_name"):
#             job_name = filters["job_name"].strip()
#             search_result = await db.execute(
#                 select(Job.id)
#                 .where(Job.user_id == report.user_id)
#                 .where(Job.job_type == JobType.AD_HOC)
#                 .where(or_(
#                     Job.keyword.ilike(f"%{job_name}%"),
#                     Job.payload.ilike(f"%{job_name}%")  # fallback if job_name stored in payload
#                 ))
#             )
#             search_job_ids = [str(row[0]) for row in search_result.all()]
# 
#         # 2. Monitoring jobs by title
#         if filters.get("monitor_title"):
#             monitor_title = filters["monitor_title"].strip()
#             monitor_result = await db.execute(
#                 select(MonitoringJob.id)
#                 .where(MonitoringJob.user_id == report.user_id)
#                 .where(MonitoringJob.title == monitor_title)
#             )
#             monitor_job_ids = [str(row[0]) for row in monitor_result.all()]
# 
#         if not search_job_ids and not monitor_job_ids:
#             raise ValueError("No matching jobs found for the given job_name or monitor_title")
# 
#         report.progress = 10
#         await db.commit()
# 
#         # ── Collect findings ────────────────────────────────────────────
#         all_findings = []
# 
#         es = ESClient()
# 
#         # Search jobs (Elasticsearch)
#         for job_id in search_job_ids:
#             findings = await es.search_by_job_id(job_id)
#             all_findings.extend(findings)
# 
#         # Monitoring results (DB)
#         if monitor_job_ids:
#             monitor_result = await db.execute(
#                 select(MonitoringResult)
#                 .where(MonitoringResult.user_id == report.user_id)
#                 .where(MonitoringResult.monitor_job_id.in_([uuid.UUID(jid) for jid in monitor_job_ids]))
#                 .order_by(MonitoringResult.created_at.desc())
#             )
#             rows = monitor_result.scalars().all()
# 
#             for row in rows:
#                 all_findings.append({
#                     "id": str(row.id),
#                     "title": row.title,
#                     "risk_level": row.risk_level,
#                     "risk_score": row.risk_score,
#                     "indicators": row.threat_indicators or [],
#                     "created_at": row.created_at.isoformat() if row.created_at else None,
#                     "source": "monitoring",
#                     "source_url": row.target_url,
#                     "text_excerpt": row.text_excerpt,
#                     # Add more fields as needed
#                 })
# 
#         # ── Progress: 30% ──
#         report.progress = 30
#         await db.commit()
# 
#         # ── Generate LLM content ───────────────────────────────────────
#         report_content = await generate_report_content(
#             report_type=report.report_type.value,
#             title=report.title,
#             findings=all_findings,
#             jobs_count=len(search_job_ids) + len(monitor_job_ids),
#             time_period="All available data",
#             model_choice=filters.get("model_choice", "llama3.1")
#         )
# 
#         report.progress = 60
#         await db.commit()
# 
#         # ── Render PDF ──────────────────────────────────────────────────
#         filepath, size_mb = await generate_pdf_report(
#             report=report,
#             content=report_content,
#             findings=all_findings
#         )
# 
#         # Final stats
#         threats_count = len([
#             f for f in all_findings
#             if f.get("risk_level", "").lower() in ["high", "critical"]
#         ])
#         indicators_count = sum(
#             len(f.get("indicators", [])) for f in all_findings
#         )
# 
#         report.status = ReportStatus.COMPLETED
#         report.progress = 100
#         report.file_path = filepath
#         report.file_size_mb = size_mb
#         report.threats_count = threats_count
#         report.indicators_count = indicators_count
#         report.completed_at = datetime.utcnow()
# 
#         await db.commit()
# 
#         logger.info(f"Targeted report {report_id} completed")
# 
#     except Exception as e:
#         logger.exception(f"Targeted report failed: {report_id}")
#         if report:
#             report.status = ReportStatus.FAILED
#             report.progress = 0
#             report.error_message = str(e)[:500]
#             await db.commit()
# 
# @router.get("/reports/{report_id}/status")
# async def get_report_status(
#     report_id: str,
#     current_user: dict = Depends(get_current_user),
#     db: AsyncSession = Depends(get_db)
# ):
#     """
#     Get current status and progress of a report generation
#     Used for polling / progress bar in UI
#     """
#     try:
#         report_uuid = uuid.UUID(report_id)
#     except ValueError:
#         raise HTTPException(400, "Invalid report ID")
# 
#     result = await db.execute(
#         select(Report).where(
#             Report.id == report_uuid,
#             Report.user_id == current_user.get("sub")
#         )
#     )
#     report = result.scalar_one_or_none()
# 
#     if not report:
#         raise HTTPException(404, "Report not found or access denied")
# 
#     return {
#         "success": True,
#         "report_id": report_id,
#         "status": report.status.value,
#         "progress": report.progress,
#         "title": report.title,
#         "type": report.report_type.value,
#         "created_at": report.created_at.isoformat(),
#         "completed_at": report.completed_at.isoformat() if report.completed_at else None,
#         "error_message": report.error_message if report.status == ReportStatus.FAILED else None,
#         "download_url": (
#             f"/api/v1/reports/{report_id}/download"
#             if report.status == ReportStatus.COMPLETED and report.file_path
#             else None
#         )
#     }
# # ────────────────────────────────────────────────
# #               List all generated reports
# # ────────────────────────────────────────────────
# 
# 
# @router.get("/reports")
# async def list_reports(
#     # Pagination parameters
#     page: int = Query(1, ge=1, description="Page number (starts from 1)"),
#     page_size: int = Query(10, ge=5, le=50, description="Number of reports per page (5–50)"),
#     
#     # Optional filters (you can extend later)
#     status: Optional[str] = Query(None, description="Filter by status (pending/generating/completed/failed)"),
#     
#     db: AsyncSession = Depends(get_db),
#     current_user: dict = Depends(get_current_user)
# ):
#     """
#     List user's generated reports with pagination
#     """
#     user_id = current_user.get("sub")
#     if not user_id:
#         raise HTTPException(status_code=401, detail="Authentication required")
# 
#     # Calculate offset
#     offset = (page - 1) * page_size
# 
#     # Base query
#     query = select(Report).where(Report.user_id == user_id)
# 
#     # Optional status filter
#     if status:
#         try:
#             status_enum = ReportStatus(status.lower())
#             query = query.where(Report.status == status_enum)
#         except ValueError:
#             raise HTTPException(
#                 status_code=422,
#                 detail=f"Invalid status value. Must be one of: {', '.join(ReportStatus.__members__.keys())}"
#             )
# 
#     # Order by most recent first
#     query = query.order_by(Report.created_at.desc())
# 
#     # Get total count (for pagination metadata)
#     count_query = select(func.count()).select_from(query.subquery())
#     total_result = await db.execute(count_query)
#     total = total_result.scalar_one() or 0
# 
#     # Get paginated results
#     paginated_query = query.offset(offset).limit(page_size)
#     result = await db.execute(paginated_query)
#     reports = result.scalars().all()
# 
#     # Build response
#     return {
#         "success": True,
#         "pagination": {
#             "total": total,
#             "page": page,
#             "page_size": page_size,
#             "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
#             "has_next": offset + len(reports) < total,
#             "has_previous": page > 1
#         },
#         "reports": [
#             {
#                 "id": str(r.id),
#                 "code": f"RPT-{str(r.id)[:8].upper()}",
#                 "title": r.title,
#                 "type": r.report_type.value.capitalize(),
#                 "date": r.created_at.strftime("%Y-%m-%d"),
#                 "size": r.file_size_mb or "-",
#                 "status": r.status.value,
#                 "progress": r.progress if hasattr(r, 'progress') else 0,
#                 "threats": r.threats_count or 0,
#                 "indicators": r.indicators_count or 0,
#                 "download_url": (
#                     f"/api/v1/reports/{r.id}/download"
#                     if r.file_path and r.status == ReportStatus.COMPLETED
#                     else None
#                 ),
#                 "preview_url": (
#                     f"/api/v1/reports/{r.id}/preview"
#                     if r.file_path and r.status == ReportStatus.COMPLETED
#                     else None
#                 ),
#                 "error": r.error_message if r.status == ReportStatus.FAILED else None
#             }
#             for r in reports
#         ]
#     }
# 
# # ────────────────────────────────────────────────
# #               Download completed report
# # ────────────────────────────────────────────────
# 
# @router.get("/reports/{report_id}/download")
# async def download_report(
#     report_id: str,
#     db: AsyncSession = Depends(get_db),
#     current_user: dict = Depends(get_current_user)
# ):
#     try:
#         report_uuid = uuid.UUID(report_id)
#     except ValueError:
#         raise HTTPException(400, "Invalid report ID")
# 
#     result = await db.execute(
#         select(Report).where(
#             Report.id == report_uuid,
#             Report.user_id == current_user["sub"]
#         )
#     )
#     report = result.scalar_one_or_none()
# 
#     if not report:
#         raise HTTPException(404, "Report not found or access denied")
# 
#     if report.status != ReportStatus.COMPLETED:
#         raise HTTPException(400, f"Report is {report.status.value} — not ready for download")
# 
#     if not report.file_path or not os.path.exists(report.file_path):
#         raise HTTPException(404, "Report file not found on server")
# 
#     return FileResponse(
#         path=report.file_path,
#         filename=f"{report.title.replace(' ', '_')}.pdf",
#         media_type="application/pdf"
#     )
# 
# 
# 
# @router.get("/reports/{report_id}/preview")
# async def preview_report(
#     report_id: str,
#     current_user: dict = Depends(get_current_user),
#     db: AsyncSession = Depends(get_db)
# ):
#     """
#     Returns an HTML preview of the report for the owner
#     Useful for the "Preview" button in the UI
#     """
#     try:
#         report_uuid = uuid.UUID(report_id)
#     except ValueError:
#         raise HTTPException(400, "Invalid report ID")
# 
#     result = await db.execute(
#         select(Report).where(
#             Report.id == report_uuid,
#             Report.user_id == current_user.get("sub")
#         )
#     )
#     report = result.scalar_one_or_none()
# 
#     if not report:
#         raise HTTPException(404, "Report not found or you don't have access")
# 
#     if report.status != ReportStatus.COMPLETED:
#         raise HTTPException(400, f"Report is {report.status.value} — not ready for preview")
# 
#     # Option 1: If you stored the raw markdown/text content → render it
#     # Option 2: Re-generate preview using the same template logic as PDF
# 
#     # We'll use Jinja2 + same template as PDF generation for consistency
#     try:
#         template_name = {
#             ReportType.COMPREHENSIVE: "comprehensive.html",
#             ReportType.EXECUTIVE: "executive.html",
#             ReportType.TECHNICAL: "technical.html"
#         }[report.report_type]
# 
#         template = env.get_template(template_name)
# 
#         # Re-fetch findings for accurate preview (or store them if you want to optimize)
#         es = ESClient()
#         findings = await es.search_all_user_findings(
#             user_id=report.user_id,
#             keyword=report.filters.get("keyword"),
#             date_from=report.filters.get("date_from"),
#             date_to=report.filters.get("date_to")
#         )
# 
#         html_content = template.render(
#             report=report,
#             findings=findings[:100],  # limit for preview
#             generated_at=datetime.utcnow().strftime("%B %d, %Y at %H:%M UTC"),
#             total_threats=len([f for f in findings if f.get("risk_level") in ["high", "critical"]]),
#             total_indicators=sum(len(f.get("indicators", [])) for f in findings)
#         )
# 
#         return HTMLResponse(content=html_content)
# 
#     except Exception as e:
#         logger.exception(f"Preview generation failed for report {report_id}")
#         raise HTTPException(500, f"Failed to generate preview: {str(e)}")
# 
# 
# # ────────────────────────────────────────────────
# #               SHARE ENDPOINT (create share link)
# # ────────────────────────────────────────────────
# 
# @router.post("/reports/{report_id}/share")
# async def share_report(
#     report_id: str,
#     expires_in_hours: int = Query(24, ge=1, le=168, description="Link expiration in hours (1–168)"),
#     current_user: dict = Depends(get_current_user),
#     db: AsyncSession = Depends(get_db)
# ):
#     """
#     Generate a temporary shareable public link for a completed report
#     """
#     try:
#         report_uuid = uuid.UUID(report_id)
#     except ValueError:
#         raise HTTPException(400, "Invalid report ID")
# 
#     result = await db.execute(
#         select(Report).where(
#             Report.id == report_uuid,
#             Report.user_id == current_user.get("sub")
#         )
#     )
#     report = result.scalar_one_or_none()
# 
#     if not report:
#         raise HTTPException(404, "Report not found or access denied")
# 
#     if report.status != ReportStatus.COMPLETED:
#         raise HTTPException(400, "Only completed reports can be shared")
# 
#     if not report.file_path:
#         raise HTTPException(400, "Report file is missing")
# 
#     # Generate or refresh share token
#     now = datetime.now(timezone.utc)
#     if (
#         not report.share_token or
#         not report.share_expires_at or
#         report.share_expires_at < now
#     ):
#         report.share_token = secrets.token_urlsafe(32)
#         report.share_expires_at = now + timedelta(hours=expires_in_hours)
#         report.is_publicly_shared = True
#         await db.commit()
#         await db.refresh(report)
# 
#     # Build share URL (replace with your actual domain in production)
#     base_url = "http://localhost:8000"  # ← change to your real domain!
#     share_url = f"{base_url}/api/v1/reports/shared/{report.share_token}"
# 
#     return {
#         "success": True,
#         "share_url": share_url,
#         "expires_at": report.share_expires_at.isoformat(),
#         "expires_in_hours": expires_in_hours,
#         "report_id": report_id,
#         "title": report.title
#     }
# 
# 
# # ────────────────────────────────────────────────
# #       PUBLIC VIEW ENDPOINT (via share token)
# # ────────────────────────────────────────────────
# 
# @router.get("/reports/shared/{share_token}")
# async def view_shared_report(
#     share_token: str,
#     db: AsyncSession = Depends(get_db)
# ):
#     """
#     Public endpoint — view or download a shared report using the share token
#     No authentication required
#     """
#     result = await db.execute(
#         select(Report).where(Report.share_token == share_token)
#     )
#     report = result.scalar_one_or_none()
# 
#     if not report:
#         raise HTTPException(404, "Shared report not found")
# 
#     if not report.is_publicly_shared:
#         raise HTTPException(403, "This report is no longer publicly shared")
# 
#     # Fix: Make both datetimes timezone-aware for comparison
#     now = datetime.now(timezone.utc)
#     
#     # If share_expires_at is naive (from DB), make it aware (assume UTC)
#     expires_at = report.share_expires_at
#     if expires_at and expires_at.tzinfo is None:
#         expires_at = expires_at.replace(tzinfo=timezone.utc)
# 
#     if expires_at and expires_at < now:
#         raise HTTPException(410, "This share link has expired")
# 
#     if not report.file_path or not os.path.exists(report.file_path):
#         raise HTTPException(404, "Report file is no longer available")
# 
#     # Serve the PDF file directly
#     return FileResponse(
#         path=report.file_path,
#         filename=f"{report.title.replace(' ', '_')}.pdf",
#         media_type="application/pdf",
#         headers={
#             "Content-Disposition": f"inline; filename={report.title.replace(' ', '_')}.pdf"
#         }
#     )
# 
# 
# 
# @router.get("/reports/{report_id}")
# async def get_report_details(
#     report_id: str,
#     current_user: dict = Depends(get_current_user),
#     db: AsyncSession = Depends(get_db)
# ):
#     """
#     Get detailed metadata for a specific report
#     Returns complete information including filters, stats, sharing status, and action URLs
#     """
#     try:
#         report_uuid = uuid.UUID(report_id)
#     except ValueError:
#         raise HTTPException(status_code=400, detail="Invalid report ID format")
# 
#     # Fetch the report with user ownership check
#     result = await db.execute(
#         select(Report).where(
#             Report.id == report_uuid,
#             Report.user_id == current_user.get("sub")
#         )
#     )
#     report = result.scalar_one_or_none()
# 
#     if not report:
#         raise HTTPException(
#             status_code=404, 
#             detail="Report not found or you don't have access to this report"
#         )
# 
#     # Calculate derived fields
#     report_code = f"RPT-{str(report.id)[:8].upper()}"
#     is_ready = report.status == ReportStatus.COMPLETED and report.file_path
#     is_failed = report.status == ReportStatus.FAILED
#     is_generating = report.status == ReportStatus.GENERATING
# 
#     # Build action URLs
#     base_url = "http://localhost:8000"  # ← Replace with your actual domain in production
#     action_urls = {
#         "download": f"/api/v1/reports/{report_id}/download" if is_ready else None,
#         "preview": f"/api/v1/reports/{report_id}/preview" if is_ready else None,
#         "status": f"/api/v1/reports/{report_id}/status" if is_generating else None,
#         "share": f"/api/v1/reports/{report_id}/share" if is_ready else None,
#         "share_url": (
#             f"{base_url}/api/v1/reports/shared/{report.share_token}" 
#             if report.share_token and report.is_publicly_shared and report.share_expires_at 
#             else None
#         )
#     }
# 
#     # Format dates
#     created_at = report.created_at.isoformat() if report.created_at else None
#     completed_at = report.completed_at.isoformat() if report.completed_at else None
# 
#     # Format share expiration
#     share_expires_at = None
#     if report.share_expires_at:
#         expires = report.share_expires_at
#         if expires.tzinfo is None:
#             expires = expires.replace(tzinfo=timezone.utc)
#         share_expires_at = expires.isoformat()
# 
#     # Format filters (make them readable)
#     formatted_filters = report.filters or {}
#     if formatted_filters.get("date_from"):
#         formatted_filters["date_from_display"] = formatted_filters["date_from"]
#     if formatted_filters.get("date_to"):
#         formatted_filters["date_to_display"] = formatted_filters["date_to"]
#     if formatted_filters.get("keyword"):
#         formatted_filters["keyword_display"] = formatted_filters["keyword"]
# 
#     # Calculate time elapsed (if completed)
#     time_elapsed = None
#     if report.completed_at and report.created_at:
#         elapsed_seconds = (report.completed_at - report.created_at).total_seconds()
#         if elapsed_seconds < 60:
#             time_elapsed = f"{int(elapsed_seconds)}s"
#         elif elapsed_seconds < 3600:
#             time_elapsed = f"{int(elapsed_seconds // 60)}m"
#         else:
#             time_elapsed = f"{int(elapsed_seconds // 3600)}h"
# 
#     # Sharing status (fixed comparison)
#     now_utc = datetime.now(timezone.utc)
#     expires_at = report.share_expires_at
#     if expires_at and expires_at.tzinfo is None:
#         expires_at = expires_at.replace(tzinfo=timezone.utc)
# 
#     sharing_status = {
#         "is_shared": report.is_publicly_shared,
#         "share_token": report.share_token,
#         "expires_at": share_expires_at,
#         "is_expired": bool(expires_at and expires_at < now_utc),
#         "share_url": action_urls["share_url"]
#     }
# 
#     return {
#         "success": True,
#         "report": {
#             # Basic info
#             "id": str(report.id),
#             "code": report_code,
#             "title": report.title,
#             "type": report.report_type.value,
#             "type_display": report.report_type.value.replace("_", " ").title(),
# 
#             # Status & progress
#             "status": report.status.value,
#             "progress": report.progress or 0,
#             "is_ready": is_ready,
#             "is_generating": is_generating,
#             "is_failed": is_failed,
# 
#             # Stats
#             "threats_count": report.threats_count or 0,
#             "indicators_count": report.indicators_count or 0,
#             "file_size_mb": report.file_size_mb or None,
# 
#             # Timestamps
#             "created_at": created_at,
#             "completed_at": completed_at,
#             "time_elapsed": time_elapsed,
#             "updated_at": report.updated_at.isoformat() if report.updated_at else None,
# 
#             # Filters used
#             "filters": formatted_filters,
#             "model_used": formatted_filters.get("model_choice", "gemini-2.5-flash"),
# 
#             # File & actions
#             "file_path": report.file_path,
#             "action_urls": action_urls,
# 
#             # Sharing
#             "sharing": sharing_status,
# 
#             # Error (if any)
#             "error_message": report.error_message if is_failed else None
#         }
#     }
# 
# 
# @router.delete("/reports/{report_id}")
# async def delete_report(
#     report_id: str,
#     current_user: dict = Depends(get_current_user),
#     db: AsyncSession = Depends(get_db)
# ):
#     """
#     Delete a report and its associated PDF file (if exists)
# 
#     - Only the owner can delete
#     - Cannot delete reports that are still generating
#     - Physically removes the PDF file from disk
#     - Permanently deletes the record from the database
#     """
#     try:
#         report_uuid = uuid.UUID(report_id)
#     except ValueError:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Invalid report ID format"
#         )
# 
#     # Fetch report with ownership check
#     result = await db.execute(
#         select(Report).where(
#             Report.id == report_uuid,
#             Report.user_id == current_user.get("sub")
#         )
#     )
#     report = result.scalar_one_or_none()
# 
#     if not report:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Report not found or you don't have permission to delete it"
#         )
# 
#     # Prevent deletion of in-progress reports
#     if report.status == ReportStatus.GENERATING:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Cannot delete a report that is currently being generated. Please wait until it completes or fails."
#         )
# 
#     try:
#         # Delete physical file if it exists
#         if report.file_path and os.path.exists(report.file_path):
#             try:
#                 os.remove(report.file_path)
#                 logger.info(f"Deleted report file: {report.file_path}")
#             except OSError as e:
#                 logger.warning(f"Failed to delete file {report.file_path}: {e}")
#                 # Continue anyway — don't fail the whole operation
# 
#         # Delete from database
#         await db.execute(
#             delete(Report).where(Report.id == report_uuid)
#         )
#         await db.commit()
# 
#         logger.info(f"Report {report_id} ({report.title}) deleted by user {current_user.get('sub')}")
# 
#         return {
#             "success": True,
#             "message": f"Report '{report.title}' (ID: {report_id}) has been deleted",
#             "report_id": report_id,
#             "title": report.title
#         }
# 
#     except Exception as e:
#         await db.rollback()
#         logger.exception(f"Failed to delete report {report_id}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to delete report: {str(e)}"
#         )





        # app/api/v1/reporting.py

from fastapi import (
    APIRouter,
    BackgroundTasks,
    HTTPException,
    Query,
    Response,
    Depends,
)
from fastapi.responses import FileResponse, HTMLResponse

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, delete
from typing import Optional
from datetime import datetime
import uuid
import os
import logging
import secrets

from app.database.database import get_db
from app.models.report import Report, ReportType, ReportStatus
from app.models.job import Job, JobType
from app.models.monitoring_job import MonitoringJob
from app.models.monitoring_result import MonitoringResult
from app.services.es_client import ESClient
from app.services.report_generator import generate_pdf_report
from app.services.report_llm import generate_report_content

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["reporting"])


@router.post("/reports/generate-targeted")
async def generate_targeted_report(
    background_tasks: BackgroundTasks,
    report_type: ReportType = Query(..., description="Type of report"),
    report_title: str = Query(..., min_length=5, description="Title for this report"),
    job_name: Optional[str] = Query(None, description="Job name / keyword from search jobs"),
    monitor_title: Optional[str] = Query(None, description="Title from monitoring jobs"),
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    model_choice: str = Query("llama3.1", description="Ollama model name"),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a targeted report (no authentication required)
    """
    if not report_title.strip():
        raise HTTPException(status_code=400, detail="Report title is required")

    if not job_name and not monitor_title:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one of: job_name or monitor_title"
        )

    report = Report(
        user_id=None,  # no user association anymore
        title=report_title.strip(),
        report_type=report_type,
        status=ReportStatus.GENERATING,
        filters={
            "job_name": job_name,
            "monitor_title": monitor_title,
            "date_from": date_from,
            "date_to": date_to,
            "model_choice": model_choice
        }
    )

    db.add(report)
    await db.commit()
    await db.refresh(report)

    background_tasks.add_task(
        create_targeted_report_task,
        report_id=report.id,
        db=db
    )

    return {
        "success": True,
        "report_id": str(report.id),
        "status": "generating",
        "message": f"Generating {report_type.value} report: '{report_title}'",
        "targeted": {
            "job_name": job_name,
            "monitor_title": monitor_title
        }
    }


async def create_targeted_report_task(report_id: str, db: AsyncSession):
    logger.info(f"Starting targeted report generation: {report_id}")

    try:
        # Fetch report
        result = await db.execute(select(Report).where(Report.id == report_id))
        report = result.scalar_one_or_none()
        if not report:
            logger.error(f"Report not found: {report_id}")
            return

        report.progress = 0
        report.status = ReportStatus.GENERATING
        await db.commit()

        # ── Find relevant job IDs ──────────────────────────────────────
        search_job_ids = []
        monitor_job_ids = []

        filters = report.filters or {}

        # 1. Search jobs by job_name / keyword
        if filters.get("job_name"):
            job_name = filters["job_name"].strip()
            search_result = await db.execute(
                select(Job.id)
                .where(Job.user_id == report.user_id)
                .where(Job.job_type == JobType.AD_HOC)
                .where(or_(
                    Job.keyword.ilike(f"%{job_name}%"),
                    Job.payload.ilike(f"%{job_name}%")  # fallback if job_name stored in payload
                ))
            )
            search_job_ids = [str(row[0]) for row in search_result.all()]

        # 2. Monitoring jobs by title
        if filters.get("monitor_title"):
            monitor_title = filters["monitor_title"].strip()
            monitor_result = await db.execute(
                select(MonitoringJob.id)
                .where(MonitoringJob.user_id == report.user_id)
                .where(MonitoringJob.title == monitor_title)
            )
            monitor_job_ids = [str(row[0]) for row in monitor_result.all()]

        if not search_job_ids and not monitor_job_ids:
            raise ValueError("No matching jobs found for the given job_name or monitor_title")

        report.progress = 10
        await db.commit()

        # ── Collect findings ────────────────────────────────────────────
        all_findings = []

        es = ESClient()

        # Search jobs (Elasticsearch)
        for job_id in search_job_ids:
            findings = await es.search_by_job_id(job_id)
            all_findings.extend(findings)

        # Monitoring results (DB)
        if monitor_job_ids:
            monitor_result = await db.execute(
                select(MonitoringResult)
                .where(MonitoringResult.user_id == report.user_id)
                .where(MonitoringResult.monitor_job_id.in_([uuid.UUID(jid) for jid in monitor_job_ids]))
                .order_by(MonitoringResult.created_at.desc())
            )
            rows = monitor_result.scalars().all()

            for row in rows:
                all_findings.append({
                    "id": str(row.id),
                    "title": row.title,
                    "risk_level": row.risk_level,
                    "risk_score": row.risk_score,
                    "indicators": row.threat_indicators or [],
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "source": "monitoring",
                    "source_url": row.target_url,
                    "text_excerpt": row.text_excerpt,
                    # Add more fields as needed
                })

        # ── Progress: 30% ──
        report.progress = 30
        await db.commit()

        # ── Generate LLM content ───────────────────────────────────────
        report_content = await generate_report_content(
            report_type=report.report_type.value,
            title=report.title,
            findings=all_findings,
            jobs_count=len(search_job_ids) + len(monitor_job_ids),
            time_period="All available data",
            model_choice=filters.get("model_choice", "llama3.1")
        )

        report.progress = 60
        await db.commit()

        # ── Render PDF ──────────────────────────────────────────────────
        filepath, size_mb = await generate_pdf_report(
            report=report,
            content=report_content,
            findings=all_findings
        )

        # Final stats
        threats_count = len([
            f for f in all_findings
            if f.get("risk_level", "").lower() in ["high", "critical"]
        ])
        indicators_count = sum(
            len(f.get("indicators", [])) for f in all_findings
        )

        report.status = ReportStatus.COMPLETED
        report.progress = 100
        report.file_path = filepath
        report.file_size_mb = size_mb
        report.threats_count = threats_count
        report.indicators_count = indicators_count
        report.completed_at = datetime.utcnow()

        await db.commit()

        logger.info(f"Targeted report {report_id} completed")

    except Exception as e:
        logger.exception(f"Targeted report failed: {report_id}")
        if report:
            report.status = ReportStatus.FAILED
            report.progress = 0
            report.error_message = str(e)[:500]
            await db.commit()


@router.get("/reports/{report_id}/status")
async def get_report_status(
    report_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get current status and progress of a report generation — public
    """
    try:
        report_uuid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(400, "Invalid report ID")

    result = await db.execute(select(Report).where(Report.id == report_uuid))
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(404, "Report not found")

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


@router.get("/reports")
async def list_reports(
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    page_size: int = Query(10, ge=5, le=50, description="Number of reports per page (5–50)"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
):
    """
    List all generated reports (public — no user filter)
    """
    offset = (page - 1) * page_size

    query = select(Report)

    if status:
        try:
            status_enum = ReportStatus(status.lower())
            query = query.where(Report.status == status_enum)
        except ValueError:
            raise HTTPException(422, f"Invalid status. Must be one of: {', '.join(ReportStatus.__members__.keys())}")

    query = query.order_by(Report.created_at.desc())

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one() or 0

    paginated_query = query.offset(offset).limit(page_size)
    result = await db.execute(paginated_query)
    reports = result.scalars().all()

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
                "progress": r.progress or 0,
                "threats": r.threats_count or 0,
                "indicators": r.indicators_count or 0,
                "download_url": f"/api/v1/reports/{r.id}/download" if r.file_path else None,
                "error": r.error_message if r.status == ReportStatus.FAILED else None
            }
            for r in reports
        ]
    }


@router.get("/reports/{report_id}/download")
async def download_report(
    report_id: str,
    db: AsyncSession = Depends(get_db)
):
    try:
        report_uuid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(400, "Invalid report ID")

    result = await db.execute(select(Report).where(Report.id == report_uuid))
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(404, "Report not found")

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
    db: AsyncSession = Depends(get_db)
):
    try:
        report_uuid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(400, "Invalid report ID")

    result = await db.execute(select(Report).where(Report.id == report_uuid))
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(404, "Report not found")

    if report.status != ReportStatus.COMPLETED:
        raise HTTPException(400, f"Report is {report.status.value} — not ready for preview")

    # Your preview logic here (Jinja2 or static HTML)
    # Example placeholder:
    return HTMLResponse(content="<h1>Report Preview</h1><p>Public preview content...</p>")


@router.post("/reports/{report_id}/share")
async def share_report(
    report_id: str,
    expires_in_hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db)
):
    try:
        report_uuid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(400, "Invalid report ID")

    result = await db.execute(select(Report).where(Report.id == report_uuid))
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(404, "Report not found")

    if report.status != ReportStatus.COMPLETED:
        raise HTTPException(400, "Only completed reports can be shared")

    now = datetime.utcnow()
    report.share_token = secrets.token_urlsafe(32)
    report.share_expires_at = now + timedelta(hours=expires_in_hours)
    report.is_publicly_shared = True
    await db.commit()

    base_url = "http://192.168.1.100:8000"  # change in production
    share_url = f"{base_url}/api/v1/reports/shared/{report.share_token}"

    return {
        "success": True,
        "share_url": share_url,
        "expires_at": report.share_expires_at.isoformat(),
        "expires_in_hours": expires_in_hours,
        "report_id": report_id,
        "title": report.title
    }


# @router.get("/reports/shared/{share_token}")
# async def view_shared_report(
#     share_token: str,
#     db: AsyncSession = Depends(get_db)
# ):
#     result = await db.execute(select(Report).where(Report.share_token == share_token))
#     report = result.scalar_one_or_none()
# 
#     if not report:
#         raise HTTPException(404, "Shared report not found")
# 
#     if not report.is_publicly_shared:
#         raise HTTPException(403, "This report is no longer publicly shared")
# 
#     now = datetime.utcnow()
#     if report.share_expires_at and report.share_expires_at < now:
#         raise HTTPException(410, "This share link has expired")
# 
#     if not report.file_path or not os.path.exists(report.file_path):
#         raise HTTPException(404, "Report file not available")
# 
#     return FileResponse(
#         path=report.file_path,
#         filename=f"{report.title.replace(' ', '_')}.pdf",
#         media_type="application/pdf",
#         headers={"Content-Disposition": f"inline; filename={report.title.replace(' ', '_')}.pdf"}
#     )

@router.get("/reports/shared/{share_token}")
async def view_shared_report(
    share_token: str,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Report).where(Report.share_token == share_token))
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(404, "Shared report not found")

    if not report.is_publicly_shared:
        raise HTTPException(403, "This report is no longer publicly shared")

    now = datetime.utcnow()
    if report.share_expires_at and report.share_expires_at < now:
        raise HTTPException(410, "This share link has expired")

    if not report.file_path or not os.path.exists(report.file_path):
        raise HTTPException(404, "Report file not available")

    return FileResponse(
        path=report.file_path,
        filename=f"{report.title.replace(' ', '_')}.pdf",
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={report.title.replace(' ', '_')}.pdf"}
    )


@router.get("/reports/{report_id}")
async def get_report_details(
    report_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed metadata for a specific report — public
    """
    try:
        report_uuid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid report ID format")

    result = await db.execute(select(Report).where(Report.id == report_uuid))
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(404, "Report not found")

    # Calculate derived fields (same as before)
    report_code = f"RPT-{str(report.id)[:8].upper()}"
    is_ready = report.status == ReportStatus.COMPLETED and report.file_path
    is_failed = report.status == ReportStatus.FAILED
    is_generating = report.status == ReportStatus.GENERATING

    base_url = "http://192.168.1.100:8000"  # change in production
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

    created_at = report.created_at.isoformat() if report.created_at else None
    completed_at = report.completed_at.isoformat() if report.completed_at else None

    share_expires_at = None
    if report.share_expires_at:
        expires = report.share_expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        share_expires_at = expires.isoformat()

    formatted_filters = report.filters or {}
    if formatted_filters.get("date_from"):
        formatted_filters["date_from_display"] = formatted_filters["date_from"]
    if formatted_filters.get("date_to"):
        formatted_filters["date_to_display"] = formatted_filters["date_to"]
    if formatted_filters.get("keyword"):
        formatted_filters["keyword_display"] = formatted_filters["keyword"]

    time_elapsed = None
    if report.completed_at and report.created_at:
        elapsed_seconds = (report.completed_at - report.created_at).total_seconds()
        if elapsed_seconds < 60:
            time_elapsed = f"{int(elapsed_seconds)}s"
        elif elapsed_seconds < 3600:
            time_elapsed = f"{int(elapsed_seconds // 60)}m"
        else:
            time_elapsed = f"{int(elapsed_seconds // 3600)}h"

    now_utc = datetime.now(timezone.utc)
    expires_at = report.share_expires_at
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    sharing_status = {
        "is_shared": report.is_publicly_shared,
        "share_token": report.share_token,
        "expires_at": share_expires_at,
        "is_expired": bool(expires_at and expires_at < now_utc),
        "share_url": action_urls["share_url"]
    }

    return {
        "success": True,
        "report": {
            "id": str(report.id),
            "code": report_code,
            "title": report.title,
            "type": report.report_type.value,
            "type_display": report.report_type.value.replace("_", " ").title(),
            "status": report.status.value,
            "progress": report.progress or 0,
            "is_ready": is_ready,
            "is_generating": is_generating,
            "is_failed": is_failed,
            "threats_count": report.threats_count or 0,
            "indicators_count": report.indicators_count or 0,
            "file_size_mb": report.file_size_mb or None,
            "created_at": created_at,
            "completed_at": completed_at,
            "time_elapsed": time_elapsed,
            "updated_at": report.updated_at.isoformat() if report.updated_at else None,
            "filters": formatted_filters,
            "model_used": formatted_filters.get("model_choice", "gemini-2.5-flash"),
            "file_path": report.file_path,
            "action_urls": action_urls,
            "sharing": sharing_status,
            "error_message": report.error_message if is_failed else None
        }
    }


@router.delete("/reports/{report_id}")
async def delete_report(
    report_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a report and its associated PDF file (if exists) — public
    """
    try:
        report_uuid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid report ID format"
        )

    result = await db.execute(select(Report).where(Report.id == report_uuid))
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(404, "Report not found")

    if report.status == ReportStatus.GENERATING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a report that is currently being generated."
        )

    try:
        # Delete physical file if exists
        if report.file_path and os.path.exists(report.file_path):
            try:
                os.remove(report.file_path)
                logger.info(f"Deleted report file: {report.file_path}")
            except OSError as e:
                logger.warning(f"Failed to delete file {report.file_path}: {e}")

        # Delete from database
        await db.execute(delete(Report).where(Report.id == report_uuid))
        await db.commit()

        logger.info(f"Report {report_id} ({report.title}) deleted")

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

