import aiokafka
from aiokafka import AIOKafkaProducer
import json
import os

async def get_producer():
    producer = AIOKafkaProducer(bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS"))
    await producer.start()
    return producer

async def send_job(topic: str, payload: dict):
    producer = await get_producer()
    await producer.send_and_wait(topic, json.dumps(payload).encode("utf-8"))
    await producer.stop()