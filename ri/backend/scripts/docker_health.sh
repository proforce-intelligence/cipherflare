#!/bin/bash

echo "=== Docker Services Health Check ==="
echo ""

# Check if docker-compose is up
COMPOSE_STATUS=$(docker-compose -f docker-compose-parrot.yml ps 2>&1 | grep -c "Up")

if [ "$COMPOSE_STATUS" -gt 0 ]; then
    echo "[✓] Docker Compose is running"
    echo ""
    docker-compose -f docker-compose-parrot.yml ps
else
    echo "[!] Docker services not running. Start with:"
    echo "    docker-compose -f docker-compose-parrot.yml up -d"
    exit 1
fi

echo ""
echo "[*] Checking service connectivity..."
echo ""

# Check Elasticsearch
ES_HEALTH=$(curl -s http://localhost:9200/_cluster/health 2>/dev/null | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))")
if [ "$ES_HEALTH" == "green" ] || [ "$ES_HEALTH" == "yellow" ]; then
    echo "[✓] Elasticsearch: HEALTHY ($ES_HEALTH)"
else
    echo "[!] Elasticsearch: UNHEALTHY"
fi

# Check Kafka
if timeout 2 bash -c 'cat < /dev/null > /dev/tcp/localhost/9092' 2>/dev/null; then
    echo "[✓] Kafka: HEALTHY"
else
    echo "[!] Kafka: UNHEALTHY"
fi

# Check Python services
PYTHON_PROCS=$(pgrep -f "uvicorn\|app.services.worker" | wc -l)
if [ "$PYTHON_PROCS" -gt 0 ]; then
    echo "[✓] Python services: RUNNING ($PYTHON_PROCS processes)"
else
    echo "[!] Python services: NOT RUNNING"
fi

echo ""
echo "[✓] Health check complete"
