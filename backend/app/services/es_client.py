from elasticsearch import Elasticsearch, NotFoundError
from elasticsearch.helpers import bulk
import os
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class ESClient:
    def __init__(self, url: str = None):
        self.url = url or os.getenv("ES_URL", "http://localhost:9200")
        self.client = Elasticsearch([self.url])
        self.index_name = "dark_web_findings"
    
    async def index_finding(self, finding: Dict[str, Any]) -> str:
        """Index a single finding to Elasticsearch"""
        try:
            result = self.client.index(
                index=self.index_name,
                id=finding.get("id"),
                body=finding
            )
            return result["_id"]
        except Exception as e:
            logger.error(f"Failed to index finding: {e}")
            raise
    
    async def bulk_index(self, findings: List[Dict[str, Any]]) -> tuple:
        """Bulk index multiple findings"""
        try:
            actions = [
                {
                    "_index": self.index_name,
                    "_id": finding.get("id"),
                    "_source": finding
                }
                for finding in findings
            ]
            success, failed = bulk(self.client, actions, raise_on_error=False)
            return success, failed
        except Exception as e:
            logger.error(f"Bulk indexing failed: {e}")
            raise
    
    async def search_by_keyword(
        self,
        keyword: str,
        user_id: Optional[str] = None,
        min_relevance: float = 0.5,
        max_results: int = 50,
        days_back: int = 30
    ) -> List[Dict[str, Any]]:
        """Search findings by keyword with filters"""
        try:
            query = {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": keyword,
                                "fields": ["title^2", "text_excerpt", "entities.emails", "keywords_found"],
                                "fuzziness": "AUTO"
                            }
                        }
                    ],
                    "filter": [
                        {"range": {"scraped_at": {"gte": f"now-{days_back}d"}}},
                        {"range": {"relevance_score": {"gte": min_relevance * 100}}}
                    ]
                }
            }
            
            # Add user filter if provided
            if user_id:
                query["bool"]["filter"].append({"term": {"user_id": user_id}})
            
            result = self.client.search(
                index=self.index_name,
                query=query,
                size=min(max_results, 200),
                sort=[{"relevance_score": "desc"}]
            )
            
            findings = []
            for hit in result["hits"]["hits"]:
                finding = hit["_source"]
                finding["_id"] = hit["_id"]
                findings.append(finding)
            
            return findings
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    async def search_by_job_id(self, job_id: str) -> List[Dict[str, Any]]:
        """Get all findings for a specific job"""
        try:
            result = self.client.search(
                index=self.index_name,
                query={"term": {"job_id": job_id}},
                size=500
            )
            
            findings = []
            for hit in result["hits"]["hits"]:
                finding = hit["_source"]
                finding["_id"] = hit["_id"]
                findings.append(finding)
            
            return findings
        except Exception as e:
            logger.error(f"Job search failed: {e}")
            return []
    
    async def get_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get aggregated statistics"""
        try:
            agg_query = {
                "risk_distribution": {
                    "terms": {"field": "risk_level"}
                },
                "top_keywords": {
                    "terms": {"field": "keywords_found", "size": 10}
                },
                "threat_sentiment_dist": {
                    "terms": {"field": "threat_sentiment"}
                }
            }
            
            filter_clause = []
            if user_id:
                filter_clause.append({"term": {"user_id": user_id}})
            
            query = {"match_all": {}} if not filter_clause else {"bool": {"filter": filter_clause}}
            
            result = self.client.search(
                index=self.index_name,
                query=query,
                aggs=agg_query,
                size=0
            )
            
            aggs = result.get("aggregations", {})
            return {
                "total_findings": result["hits"]["total"]["value"],
                "risk_distribution": {b["key"]: b["doc_count"] for b in aggs.get("risk_distribution", {}).get("buckets", [])},
                "top_keywords": [b["key"] for b in aggs.get("top_keywords", {}).get("buckets", [])],
                "threat_sentiment": {b["key"]: b["doc_count"] for b in aggs.get("threat_sentiment_dist", {}).get("buckets", [])}
            }
        except Exception as e:
            logger.error(f"Stats aggregation failed: {e}")
            return {}
    
    def close(self):
        """Close Elasticsearch connection"""
        self.client.close()
