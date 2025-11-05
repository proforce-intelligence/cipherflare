import asyncio
from elasticsearch import AsyncElasticsearch
from datetime import datetime
from typing import List, Dict
import os

es_client = AsyncElasticsearch(os.getenv("ES_URL"))

async def init_ilm():
    policy = {"policy": {"phases": {"hot": {"actions": {}}, "delete": {"min_age": "30d", "actions": {"delete": {}}}}}
    await es_client.ilm.put_lifecycle(name="darkweb_30d_ttl", body=policy)
    template = {"index_patterns": ["dark_web_findings*"], "template": {"settings": {"index.lifecycle.name": "darkweb_30d_ttl"}}}
    await es_client.indices.put_index_template(name="darkweb_template", body=template)
    await es_client.indices.create(index="dark_web_findings", ignore=400)

async def search_findings(keyword: str, max_age_days: int = 30, min_risk: str = "medium") -> List[Dict]:
    query = {
        "query": {"bool": {"must": [{"multi_match": {"query": keyword}}], "filter": [{"range": {"scraped_at": {"gte": f"now-{max_age_days}d"}}}, {"term": {"risk_level": min_risk}}]}},
        "sort": [{"relevance_score": "desc"}, {"scraped_at": "desc"}],
        "size": 50
    }
    res = await es_client.search(index="dark_web_findings", body=query)
    return [hit["_source"] for hit in res["hits"]["hits"]]

async def index_finding(finding: Dict):
    finding["scraped_at"] = datetime.utcnow().isoformat()
    await es_client.index(index="dark_web_findings", document=finding)

async def get_job_findings(job_id: str) -> List[Dict]:
    query = {"query": {"term": {"job_id": job_id}}}
    res = await es_client.search(index="dark_web_findings", body=query)
    return [hit["_source"] for hit in res["hits"]["hits"]]