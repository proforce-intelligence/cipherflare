from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from app.services.es_client import ESClient
from app.services.kafka_producer import KafkaProducer
from app.services.llm_summarizer import generate_findings_summary
import logging
import uuid
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["search"])

es_client = None
kafka_producer = None

def get_es():
    global es_client
    if not es_client:
        es_client = ESClient()
    return es_client

def get_kafka():
    global kafka_producer
    if not kafka_producer:
        kafka_producer = KafkaProducer()
    return kafka_producer

@router.get("/search")
async def search_dark_web(
    keyword: str = Query(..., min_length=1, max_length=255),
    max_results: Optional[int] = Query(None, ge=1, le=10000),
    include_summary: bool = Query(False),
    model_choice: str = Query("gemini-2.5-flash", description="LLM model: gemini-2.5-flash (default), gpt-5-mini, claude-sonnet-4-5, etc."),
    pgp_verify: bool = Query(False, description="Verify .onion site legitimacy via PGP")
):
    """
    Hybrid search: returns pre-indexed findings instantly + queues fresh scrape
    Query Parameters:
        - keyword: Search term (required)
        - max_results: Max results to return (1-10000, default None for unlimited scraping)
        - include_summary: If true, generates LLM-based summary of findings
        - model_choice: LLM model to use (gemini-2.5-flash is default)
        - pgp_verify: If true, verifies .onion site legitimacy via PGP
    """
    try:
        user_id = None
        
        # Step 1: Query pre-indexed findings from Elasticsearch
        es = get_es()
        indexed_findings = await es.search_by_keyword(
            keyword=keyword,
            user_id=user_id,
            max_results=max_results or 200,
            min_relevance=0.5
        )
        
        # Step 2: Queue fresh scrape job to Kafka (non-blocking, optional)
        job_id = str(uuid.uuid4())
        kafka = get_kafka()
        
        job_payload = {
            "job_id": job_id,
            "keyword": keyword,
            "max_results": max_results,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "job_type": "ad_hoc"
        }
        
        await kafka.produce("ad_hoc_jobs", job_payload)
        
        kafka_status = "queued" if kafka.is_connected else "pending (Kafka unavailable)"
        
        summary = None
        if include_summary and indexed_findings:
            logger.info(f"Generating LLM summary with model {model_choice}, pgp_verify={pgp_verify}")
            summary = await generate_findings_summary(
                keyword, 
                indexed_findings, 
                model_choice=model_choice,
                pgp_verify=pgp_verify
            )
        
        response_data = {
            "success": True,
            "indexed_findings": indexed_findings,
            "indexed_count": len(indexed_findings),
            "job_id": job_id,
            "message": f"Returned {len(indexed_findings)} pre-indexed results. Fresh scrape {kafka_status}.",
            "keyword": keyword,
            "max_results": max_results or "unlimited",
            "model_used": model_choice,
            "pgp_verification_enabled": pgp_verify,
            "summary": summary
        }
        
        return JSONResponse(content=response_data, status_code=200)
    
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        return JSONResponse(content={"error": f"Search failed: {str(e)}"}, status_code=500)

@router.get("/findings/job/{job_id}")
async def get_findings_for_job(
    job_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    include_summary: bool = Query(False),
    model_choice: str = Query("gemini-2.5-flash", description="LLM model to use"),
    pgp_verify: bool = Query(False, description="Verify .onion site legitimacy via PGP")
):
    """
    Get findings for a specific job (as they are indexed in real-time)
    """
    try:
        es = get_es()
        findings = await es.search_by_job_id(job_id)
        
        # Pagination
        total = len(findings)
        paginated = findings[offset:offset+limit]
        
        summary = None
        if include_summary and findings:
            logger.info(f"Generating LLM summary for job {job_id} with model {model_choice}")
            summary = await generate_findings_summary(
                job_id, 
                findings,
                model_choice=model_choice,
                pgp_verify=pgp_verify
            )
        
        response_data = {
            "success": True,
            "job_id": job_id,
            "total": total,
            "offset": offset,
            "limit": limit,
            "findings": paginated,
            "model_used": model_choice,
            "pgp_verification_enabled": pgp_verify,
            "summary": summary
        }
        
        return JSONResponse(content=response_data, status_code=200)
    except Exception as e:
        logger.error(f"Job findings retrieval failed: {str(e)}")
        return JSONResponse(content={"error": "Failed to retrieve findings"}, status_code=500)

@router.get("/findings/summary/{job_id}")
async def get_findings_summary(
    job_id: str,
    model: str = Query("gemini-2.5-flash", description="LLM model to use (default: gemini-2.5-flash)"),
    pgp_verify: bool = Query(False, description="Include PGP verification results")
):
    """
    New endpoint to generate or retrieve LLM summary for a completed job
    Get an LLM-generated intelligence summary for a specific job's findings
    
    Query Parameters:
        - model: LLM model to use (gemini-2.5-flash is default, but can switch to gpt-5-mini, claude-sonnet-4-5, etc.)
        - pgp_verify: Whether to verify .onion site legitimacy via PGP
    """
    try:
        es = get_es()
        findings = await es.search_by_job_id(job_id)
        
        if not findings:
            return JSONResponse(
                content={"error": "No findings found for this job"},
                status_code=404
            )
        
        logger.info(f"Generating summary for job {job_id} with model {model}")
        summary = await generate_findings_summary(
            job_id, 
            findings, 
            model_choice=model,
            pgp_verify=pgp_verify
        )
        
        return JSONResponse(content=summary, status_code=200)
    except Exception as e:
        logger.error(f"Summary generation failed: {str(e)}")
        return JSONResponse(content={"error": f"Summary generation failed: {str(e)}"}, status_code=500)

@router.get("/models/available")
async def get_available_models():
    """
    Get list of available LLM models for summary generation
    Allows users to choose which LLM provider to use
    """
    from app.services.llm_utils import get_model_choices
    try:
        models = get_model_choices()
        return JSONResponse(
            content={
                "success": True,
                "available_models": models,
                "default_model": "gemini-2.5-flash",
                "description": "Use any of these models in model_choice parameter. Google Gemini is the default."
            },
            status_code=200
        )
    except Exception as e:
        logger.error(f"Failed to retrieve models: {str(e)}")
        return JSONResponse(content={"error": "Failed to retrieve models"}, status_code=500)

@router.get("/stats")
async def get_stats():
    """
    Get aggregated dark web threat statistics
    """
    try:
        user_id = None
        es = get_es()
        stats = await es.get_stats(user_id=user_id)
        
        response_data = {
            "success": True,
            "statistics": stats
        }
        
        return JSONResponse(content=response_data, status_code=200)
    except Exception as e:
        logger.error(f"Stats retrieval failed: {str(e)}")
        return JSONResponse(content={"error": "Failed to retrieve stats"}, status_code=500)
