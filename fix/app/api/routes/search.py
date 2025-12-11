from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from app.services.es_client import ESClient
from app.services.kafka_producer import KafkaProducer
import logging
import uuid
from datetime import datetime

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
    max_results: int = Query(50, ge=1, le=200)
):
    """
    Hybrid search: returns pre-indexed findings instantly + queues fresh scrape
    Query Parameters:
        - keyword: Search term (required)
        - max_results: Max results to return (1-200, default 50)
    """
    try:
        user_id = None  # Anonymous searches for now
        
        # Step 1: Query pre-indexed findings from Elasticsearch
        es = get_es()
        indexed_findings = await es.search_by_keyword(
            keyword=keyword,
            user_id=user_id,
            max_results=max_results,
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
        
        response_data = {
            "success": True,
            "indexed_findings": indexed_findings,
            "indexed_count": len(indexed_findings),
            "job_id": job_id,
            "message": f"Returned {len(indexed_findings)} pre-indexed results. Fresh scrape {kafka_status}.",
            "keyword": keyword,
            "max_results": max_results
        }
        
        return JSONResponse(content=response_data, status_code=200)
    
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        return JSONResponse(content={"error": f"Search failed: {str(e)}"}, status_code=500)

@router.get("/findings/job/{job_id}")
async def get_findings_for_job(
    job_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
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
        
        response_data = {
            "success": True,
            "job_id": job_id,
            "total": total,
            "offset": offset,
            "limit": limit,
            "findings": paginated
        }
        
        return JSONResponse(content=response_data, status_code=200)
    except Exception as e:
        logger.error(f"Job findings retrieval failed: {str(e)}")
        return JSONResponse(content={"error": "Failed to retrieve findings"}, status_code=500)

@router.get("/stats")
async def get_stats():
    """
    Get aggregated dark web threat statistics
    """
    try:
        user_id = None  # Anonymous stats for now
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
