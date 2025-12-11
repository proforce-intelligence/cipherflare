#!/bin/bash

# Fast startup script - assumes setup.sh already completed

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$PROJECT_DIR/venv"
PYTHON_BIN="$VENV_DIR/bin/python"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[*]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_error() { echo -e "${RED}[!]${NC} $1"; }

log_info "Running pre-flight checks..."

# Check Playwright browsers
if ! "$PYTHON_BIN" -c "from playwright.async_api import async_playwright; print('[✓] Playwright ready')" 2>/dev/null; then
    log_error "Playwright browsers not installed!"
    log_info "Running: $PYTHON_BIN -m playwright install"
    "$PYTHON_BIN" -m playwright install || {
        log_error "Failed to install Playwright. Check internet connection."
        exit 1
    }
fi

# Check Kafka
if ! nc -zv localhost 9092 &>/dev/null; then
    log_error "Kafka is not running on localhost:9092"
    exit 1
fi
log_success "Kafka is accessible"

# Start Docker Elasticsearch
log_info "Starting Docker Elasticsearch..."
cd "$PROJECT_DIR"
docker-compose -f docker-compose-parrot.yml up -d elasticsearch 2>/dev/null || podman-compose -f docker-compose-parrot.yml up -d elasticsearch 2>/dev/null || {
    log_error "Failed to start Elasticsearch"
    exit 1
}

log_info "Waiting for Elasticsearch..."
for i in {1..30}; do
    if curl -s http://localhost:9200 > /dev/null 2>&1; then
        log_success "Elasticsearch is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        log_error "Elasticsearch failed to start"
        exit 1
    fi
    sleep 1
done

# Setup ES index
log_info "Setting up Elasticsearch index..."
"$PYTHON_BIN" "$PROJECT_DIR/scripts/setup_es.py" 2>&1 | tail -5

export PYTHONPATH="$PROJECT_DIR"

# Start API
log_info "Starting API server on http://localhost:8000..."
cd "$PROJECT_DIR"
"$PYTHON_BIN" -m uvicorn app.api.main:app --host 0.0.0.0 --port 8000 > /tmp/cipherflare_api.log 2>&1 &
API_PID=$!
echo $API_PID > /tmp/cipherflare_api.pid
sleep 3

if ! kill -0 $API_PID 2>/dev/null; then
    log_error "API server failed to start"
    cat /tmp/cipherflare_api.log
    exit 1
fi
log_success "API server started (PID: $API_PID)"

# Start workers
log_info "Starting 2 worker processes..."
for i in {1..2}; do
    "$PYTHON_BIN" -m app.services.worker > /tmp/cipherflare_worker_$i.log 2>&1 &
    WORKER_PID=$!
    echo $WORKER_PID >> /tmp/cipherflare_workers.pid
    log_success "Worker $i started (PID: $WORKER_PID)"
    sleep 2
done

log_success "All services started!"
log_info "API Docs: http://localhost:8000/docs"
log_info "View logs: tail -f /tmp/cipherflare_*.log"
