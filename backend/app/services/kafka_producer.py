from aiokafka import AIOKafkaProducer
import json
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class KafkaProducer:
    def __init__(self, bootstrap_servers: str = None):
        default_bootstrap = os.getenv("KAFKA_BOOTSTRAP", "127.0.0.1:9092")
        self.bootstrap_servers = default_bootstrap.split(",")
        self.producer = None
        self.is_connected = False
    
    async def connect(self):
        """Initialize Kafka producer with retry logic"""
        max_retries = 5
        for attempt in range(max_retries):
            try:
                self.producer = AIOKafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    request_timeout_ms=10000,
                    connections_max_idle_ms=540000
                )
                await self.producer.start()
                self.is_connected = True
                logger.info(f"[✓] Kafka producer connected to {self.bootstrap_servers}")
                return
            except Exception as e:
                logger.warning(f"[!] Kafka connection attempt {attempt+1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    import asyncio
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    self.is_connected = False
                    raise Exception(f"Failed to connect to Kafka after {max_retries} attempts: {e}")
    
    async def produce(self, topic: str, payload: Dict[str, Any]):
        """Send message to Kafka topic"""
        if not self.producer:
            await self.connect()
        
        if not self.is_connected:
            raise Exception("Kafka producer not connected")
        
        try:
            await self.producer.send_and_wait(topic, payload)
            logger.info(f"[✓] Message sent to {topic}: {payload.get('job_id', 'unknown')}")
        except Exception as e:
            logger.error(f"[!] Failed to produce to {topic}: {e}")
            raise
    
    async def close(self):
        """Close producer connection"""
        if self.producer:
            await self.producer.stop()
            logger.info("[✓] Kafka producer closed")
