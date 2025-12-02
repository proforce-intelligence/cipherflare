from aiokafka import AIOKafkaConsumer
import json
import os
import logging
import asyncio
from typing import Callable, Optional

logger = logging.getLogger(__name__)

class KafkaConsumer:
    def __init__(
        self,
        topics: list,
        group_id: str = "dark-web-workers",
        bootstrap_servers: str = None
    ):
        self.topics = topics
        self.group_id = group_id
        default_bootstrap = os.getenv("KAFKA_BOOTSTRAP", "127.0.0.1:9092")
        self.bootstrap_servers = default_bootstrap.split(",")
        self.consumer = None
    
    async def connect(self, max_retries: int = 5):
        """Initialize Kafka consumer with retry logic"""
        for attempt in range(max_retries):
            try:
                self.consumer = AIOKafkaConsumer(
                    *self.topics,
                    bootstrap_servers=self.bootstrap_servers,
                    group_id=self.group_id,
                    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                    auto_offset_reset='earliest',
                    enable_auto_commit=True,
                    request_timeout_ms=30000,
                    connections_max_idle_ms=540000
                )
                await self.consumer.start()
                logger.info(f"[✓] Kafka consumer connected to {self.bootstrap_servers}")
                return
            except Exception as e:
                logger.warning(f"[!] Connection attempt {attempt+1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(5 * (attempt + 1))
                else:
                    logger.error(f"[!] Kafka consumer connection failed after {max_retries} attempts")
                    raise
    
    async def consume(self, message_handler: Callable):
        """
        Start consuming messages and process with handler
        message_handler: async function(topic, message) -> None
        """
        if not self.consumer:
            await self.connect()
        
        try:
            async for msg in self.consumer:
                try:
                    logger.info(f"[→] Message from {msg.topic}: {msg.value.get('job_id', 'unknown')}")
                    await message_handler(msg.topic, msg.value)
                except Exception as e:
                    logger.error(f"[!] Message processing failed: {e}")
                    # Continue processing even if one message fails
                    continue
        except Exception as e:
            logger.error(f"[!] Consumer error: {e}")
            raise
    
    async def close(self):
        """Close consumer connection"""
        if self.consumer:
            await self.consumer.stop()
            logger.info("[✓] Kafka consumer closed")

class KafkaProducerConsumer:
    """Combined producer and consumer for status updates"""
    def __init__(self, bootstrap_servers: str = None):
        default_bootstrap = os.getenv("KAFKA_BOOTSTRAP", "127.0.0.1:9092")
        self.bootstrap_servers = default_bootstrap.split(",")
        self.producer = None
    
    async def connect(self):
        """Initialize producer for status updates"""
        try:
            from aiokafka import AIOKafkaProducer
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                request_timeout_ms=30000,
                connections_max_idle_ms=540000
            )
            await self.producer.start()
        except Exception as e:
            logger.error(f"[!] Producer initialization failed: {e}")
            raise
    
    async def send_status(self, job_id: str, status: str, details: dict = None):
        """Send job status update"""
        if not self.producer:
            await self.connect()
        
        message = {
            "job_id": job_id,
            "status": status,
            "details": details or {}
        }
        
        try:
            await self.producer.send_and_wait("status_updates", message)
        except Exception as e:
            logger.error(f"[!] Status update failed: {e}")
    
    async def close(self):
        """Close producer"""
        if self.producer:
            await self.producer.stop()
