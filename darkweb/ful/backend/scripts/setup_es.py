#!/usr/bin/env python3
"""
Setup Elasticsearch index and ILM policy for dark web findings
Run this script once before starting the application
"""

from elasticsearch import Elasticsearch
import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ES_URL = os.getenv("ES_URL", "http://localhost:9200")
INDEX_NAME = "dark_web_findings"

def setup_ilm_policy():
    """Create ILM policy for 30-day retention"""
    client = Elasticsearch(
        [ES_URL],
        request_timeout=10,
        max_retries=3,
        retry_on_timeout=True,
        api_key=None
    )
    
    policy = {
        "policy": {
            "phases": {
                "hot": {
                    "min_age": "0d",
                    "actions": {
                        "rollover": {
                            "max_docs": 1000000,
                            "max_size": "50GB"
                        }
                    }
                },
                "warm": {
                    "min_age": "7d",
                    "actions": {
                        "set_priority": {
                            "priority": 50
                        }
                    }
                },
                "delete": {
                    "min_age": "30d",
                    "actions": {
                        "delete": {}
                    }
                }
            }
        }
    }
    
    try:
        response = client.transport.perform_request(
            "PUT",
            "/_ilm/policy/dark_web_findings_policy",
            body=policy
        )
        logger.info("[✓] ILM policy created/updated: dark_web_findings_policy")
        return True
    except Exception as e:
        logger.warning(f"[!] ILM policy creation warning (may still work): {e}")
        return True
    finally:
        client.close()

def setup_index():
    """Create index template with settings and mappings"""
    client = Elasticsearch(
        [ES_URL],
        request_timeout=10,
        max_retries=3,
        retry_on_timeout=True
    )
    
    index_settings = {
        "settings": {
            "number_of_shards": 3,
            "number_of_replicas": 0,
            "index.lifecycle.name": "dark_web_findings_policy",
            "index.lifecycle.rollover_alias": INDEX_NAME
        },
        "mappings": {
            "properties": {
                "url": {
                    "type": "keyword"
                },
                "title": {
                    "type": "text",
                    "analyzer": "standard"
                },
                "text_excerpt": {
                    "type": "text",
                    "analyzer": "standard"
                },
                "description": {
                    "type": "text"
                },
                "risk_level": {
                    "type": "keyword"
                },
                "risk_score": {
                    "type": "float"
                },
                "relevance_score": {
                    "type": "float"
                },
                "threat_sentiment": {
                    "type": "keyword"
                },
                "sentiment": {
                    "type": "keyword"
                },
                "entities": {
                    "type": "nested",
                    "properties": {
                        "emails": {"type": "keyword"},
                        "btc_addresses": {"type": "keyword"},
                        "eth_addresses": {"type": "keyword"},
                        "xmr_addresses": {"type": "keyword"},
                        "pgp_keys": {"type": "text"}
                    }
                },
                "keywords_found": {
                    "type": "keyword"
                },
                "threat_indicators": {
                    "type": "text"
                },
                "language": {
                    "type": "keyword"
                },
                "scraped_at": {
                    "type": "date"
                },
                "created_at": {
                    "type": "date"
                },
                "job_id": {
                    "type": "keyword"
                },
                "user_id": {
                    "type": "keyword"
                },
                "screenshot_file": {
                    "type": "keyword"
                },
                "text_file": {
                    "type": "keyword"
                },
                "html_file": {
                    "type": "keyword"
                },
                "safe_name": {
                    "type": "keyword"
                },
                "metadata": {
                    "type": "object",
                    "enabled": False
                }
            }
        }
    }
    
    try:
        try:
            client.indices.delete(index=INDEX_NAME)
            logger.info(f"[*] Deleted existing index: {INDEX_NAME}")
        except:
            pass
        
        client.indices.create(index=INDEX_NAME, body=index_settings)
        logger.info(f"[✓] Index created: {INDEX_NAME}")
        return True
    except Exception as e:
        logger.error(f"[!] Failed to create index: {e}")
        return False
    finally:
        client.close()

if __name__ == "__main__":
    logger.info("=== Elasticsearch Setup ===")
    logger.info(f"Elasticsearch URL: {ES_URL}")
    
    setup_ilm_policy()
    
    if not setup_index():
        logger.error("Failed to create index")
        sys.exit(1)
    
    logger.info("[✓] Elasticsearch setup complete!")
