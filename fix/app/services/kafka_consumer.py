# app/services/kafka_consumer.py
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
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
        bootstrap_servers: Optional[str] = None
    ):
        self.topics = topics
        self.group_id = group_id
        default_bootstrap = os.getenv("KAFKA_BOOTSTRAP", "127.0.0.1:9092")
        self.bootstrap_servers = bootstrap_servers or default_bootstrap
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
                    max_poll_interval_ms=300000,        # 5 minutes
                    session_timeout_ms=60000,
                    heartbeat_interval_ms=30000,
                    request_timeout_ms=60000,
                    connections_max_idle_ms=540000
                )
                await self.consumer.start()
                logger.info(f"[Kafka consumer connected to {self.bootstrap_servers}")
                return
            except Exception as e:
                logger.warning(f"[!] Connection attempt {attempt+1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(5 * (attempt + 1))
                else:
                    logger.error(f"[!] Kafka consumer connection failed after {max_retries} attempts")
                    raise

    async def consume(self, message_handler: Callable):
        """Start consuming messages"""
        if not self.consumer:
            await self.connect()

        try:
            async for msg in self.consumer:
                try:
                    job_id = msg.value.get('job_id', 'unknown')
                    logger.info(f"[Message from {msg.topic}: {job_id}")
                    await message_handler(msg.topic, msg.value)
                except Exception as e:
                    logger.error(f"[!] Message processing failed: {e}", exc_info=True)
                    continue
        except Exception as e:
            logger.error(f"[!] Consumer loop crashed: {e}", exc_info=True)
            raise

    async def close(self):
        if self.consumer:
            await self.consumer.stop()
            logger.info("[Kafka consumer closed]")


class KafkaProducerConsumer(KafkaConsumer):
    """Consumer + Producer for sending status updates"""
    def __init__(self, bootstrap_servers: Optional[str] = None):
        super().__init__(
            topics=["ad_hoc_jobs", "monitor_jobs"],
            group_id="dark-web-workers",
            bootstrap_servers=bootstrap_servers
        )
        self.producer = None

    async def connect_producer(self):
        if self.producer:
            return
        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                request_timeout_ms=60000,
                connections_max_idle_ms=540000
            )
            await self.producer.start()
            logger.info("[Kafka producer connected]")
        except Exception as e:
            logger.error(f"[!] Producer failed: {e}")
            raise

    async def send_status(self, job_id: str, status: str, details: dict = None):
        if not self.producer:
            await self.connect_producer()

        message = {
            "job_id": job_id,
            "status": status,
            "details": details or {}
        }

        try:
            await self.producer.send_and_wait("status_updates", message)
        except Exception as e:
            logger.error(f"[!] Failed to send status: {e}")

    async def close(self):
        if self.producer:
            await self.producer.stop()
        await super().close()
