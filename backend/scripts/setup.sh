#!/bin/bash

# Dark Web Threat Intelligence - Complete Setup & Start Script
# Assumes Kafka is already running (see KAFKA_SETUP_GUIDE.md)
# Starts: API + Workers + Docker Elasticsearch

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$PROJECT_DIR/venv"
PYTHON_BIN="$VENV_DIR/bin/python"
PIP_BIN="$VENV_DIR/bin/pip"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[*]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_error() { echo -e "${RED}[!]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[⚠]${NC} $1"; }

# Menu system
show_menu() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}Dark Web Threat Intelligence System${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo "1. Setup (first-time installation)"
    echo "2. Clean Reinstall (fixes dependency issues)"
    echo "3. Start Services (API + Workers + Docker Elasticsearch)"
    echo "4. Stop Services"
    echo "5. Status Check"
    echo "6. View Logs"
    echo "7. Test API"
    echo "8. Clean Up"
    echo "9. Exit"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -n "Select option [1-9]: "
}

# Setup function
setup_project() {
    log_info "Starting setup..."
    
    # Check Python version
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 not found. Install Python 3.10+"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    log_success "Python $PYTHON_VERSION found"
    
    # Check Docker
    if ! command -v docker &> /dev/null && ! command -v podman &> /dev/null; then
        log_error "Docker/Podman not found. Install Docker for Elasticsearch"
        exit 1
    fi
    log_success "Container runtime found"
    
    # Check Kafka
    log_info "Checking if Kafka is running..."
    if ! nc -zv localhost 9092 &>/dev/null; then
        log_error "Kafka is not running on localhost:9092"
        log_info "See KAFKA_SETUP_GUIDE.md for setup instructions"
        exit 1
    fi
    log_success "Kafka is accessible"
    
    # Create virtual environment
    if [ ! -d "$VENV_DIR" ]; then
        log_info "Creating virtual environment..."
        python3 -m venv "$VENV_DIR"
    fi
    
    # Activate and upgrade pip
    log_info "Upgrading pip..."
    if ! "$PIP_BIN" install --upgrade pip setuptools wheel 2>&1 | tee /tmp/pip_upgrade.log; then
        log_error "Failed to upgrade pip"
        cat /tmp/pip_upgrade.log
        exit 1
    fi
    log_success "Pip upgraded"
    
    log_info "Installing dependencies from requirements.txt..."
    if ! "$PIP_BIN" install -r "$PROJECT_DIR/requirements.txt" 2>&1 | tee /tmp/pip_install.log; then
        log_error "Failed to install requirements"
        log_warn "Showing last 20 lines of error:"
        tail -20 /tmp/pip_install.log
        log_info "Run option 2 (Clean Reinstall) to fix dependency issues"
        exit 1
    fi
    log_success "Dependencies installed successfully"
    
    log_info "Installing Playwright browsers (this may take 2-3 minutes)..."
    if ! "$PYTHON_BIN" -m playwright install 2>&1 | tee /tmp/playwright_install.log; then
        log_error "Failed to install Playwright browsers"
        log_warn "This is required for scraping. Try running manually:"
        log_warn "  $PYTHON_BIN -m playwright install"
        log_warn "Or install browsers system-wide first"
    else
        log_success "Playwright browsers installed"
    fi
    
    log_info "Setting up Elasticsearch index (requires ES running)..."
    if docker ps 2>/dev/null | grep -q elasticsearch || podman ps 2>/dev/null | grep -q elasticsearch; then
        sleep 2
        "$PYTHON_BIN" "$PROJECT_DIR/scripts/setup_es.py" 2>&1 | tee /tmp/es_setup.log || log_warn "ES setup may need retry"
    else
        log_warn "Elasticsearch not running - will setup after Docker start"
    fi
    
    log_success "Setup complete!"
}

# Clean reinstall function
clean_reinstall() {
    log_info "Starting clean reinstall..."
    
    if [ ! -f "$PROJECT_DIR/scripts/clean_reinstall.sh" ]; then
        log_error "clean_reinstall.sh not found"
        exit 1
    fi
    
    bash "$PROJECT_DIR/scripts/clean_reinstall.sh"
    
    if [ $? -eq 0 ]; then
        log_success "Clean reinstall complete!"
        log_info "Run option 3 to start services"
    else
        log_error "Clean reinstall failed"
        exit 1
    fi
}

start_services() {
    log_info "Starting services (API + Workers + Docker Elasticsearch)..."
    
    # Verify Kafka is running
    log_info "Verifying Kafka is running..."
    if ! nc -zv localhost 9092 &>/dev/null; then
        log_error "Kafka is not running on localhost:9092"
        log_info "Start Kafka using: sudo systemctl start kafka"
        log_info "See KAFKA_SETUP_GUIDE.md for setup instructions"
        return 1
    fi
    log_success "Kafka is running"
    
    # Start Docker Elasticsearch only
    log_info "Starting Docker Elasticsearch..."
    cd "$PROJECT_DIR"
    docker-compose -f docker-compose-parrot.yml up -d elasticsearch 2>/dev/null || podman-compose -f docker-compose-parrot.yml up -d elasticsearch 2>/dev/null || {
        log_error "Failed to start Elasticsearch"
        return 1
    }
    
    log_info "Waiting for Elasticsearch to be ready..."
    for i in {1..30}; do
        if curl -s http://localhost:9200 > /dev/null 2>&1; then
            log_success "Elasticsearch is ready"
            break
        fi
        if [ $i -eq 30 ]; then
            log_error "Elasticsearch failed to start"
            return 1
        fi
        sleep 1
    done
    
    # Setup ES index with retry logic
    log_info "Setting up Elasticsearch index..."
    for attempt in {1..3}; do
        log_info "Attempt $attempt/3 to setup Elasticsearch..."
        if "$PYTHON_BIN" "$PROJECT_DIR/scripts/setup_es.py" 2>&1 | tee /tmp/es_setup_$attempt.log; then
            log_success "Elasticsearch index setup complete"
            break
        fi
        if [ $attempt -lt 3 ]; then
            log_warn "Setup attempt failed, retrying in 5 seconds..."
            sleep 5
        fi
    done
    
    export PYTHONPATH="$PROJECT_DIR"
    export KAFKA_BOOTSTRAP="127.0.0.1:9092"
    export ELASTICSEARCH_HOST="localhost"
    export ELASTICSEARCH_PORT="9200"
    
    # Start API server
    log_info "Checking if uvicorn is installed..."
    if ! "$PYTHON_BIN" -c "import uvicorn" 2>/dev/null; then
        log_error "uvicorn not installed. Running pip install again..."
        "$PIP_BIN" install uvicorn fastapi
    fi
    
    log_info "Starting API server on http://localhost:8000..."
    cd "$PROJECT_DIR"
    "$PYTHON_BIN" -m uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload > /tmp/cipherflare_api.log 2>&1 &
    API_PID=$!
    echo $API_PID > /tmp/cipherflare_api.pid
    sleep 3
    
    if ! kill -0 $API_PID 2>/dev/null; then
        log_error "API server failed to start. Check logs:"
        cat /tmp/cipherflare_api.log
        return 1
    fi
    log_success "API server started (PID: $API_PID)"
    
    # Start workers
    log_info "Starting 2 worker processes..."
    for i in {1..2}; do
        log_info "Starting worker $i..."
        
        if ! "$PYTHON_BIN" -c "import playwright" 2>/dev/null; then
            log_error "playwright not installed. Running pip install..."
            "$PIP_BIN" install playwright
        fi
        
        "$PYTHON_BIN" -m app.services.worker > /tmp/cipherflare_worker_$i.log 2>&1 &
        WORKER_PID=$!
        echo $WORKER_PID >> /tmp/cipherflare_workers.pid
        
        if ! kill -0 $WORKER_PID 2>/dev/null; then
            log_warn "Worker $i may have failed. Check log: /tmp/cipherflare_worker_$i.log"
        else
            log_success "Worker $i started (PID: $WORKER_PID)"
        fi
        
        sleep 2
    done
    
    log_success "All services started!"
    log_info "API Docs: http://localhost:8000/docs"
    log_info "API Endpoint: http://localhost:8000/api/v1/search?keyword=ransomware"
    log_info "Logs: tail -f /tmp/cipherflare_*.log"
}

stop_services() {
    log_info "Stopping services..."
    
    # Stop Python processes
    if [ -f /tmp/cipherflare_api.pid ]; then
        kill $(cat /tmp/cipherflare_api.pid) 2>/dev/null || true
        rm /tmp/cipherflare_api.pid
    fi
    
    if [ -f /tmp/cipherflare_workers.pid ]; then
        kill $(cat /tmp/cipherflare_workers.pid) 2>/dev/null || true
        rm /tmp/cipherflare_workers.pid
    fi
    
    # Stop Docker Elasticsearch only
    cd "$PROJECT_DIR"
    docker-compose -f docker-compose-parrot.yml down 2>/dev/null || podman-compose -f docker-compose-parrot.yml down 2>/dev/null || true
    
    log_success "Services stopped"
    log_info "Kafka is still running. To stop Kafka: sudo systemctl stop kafka"
}

# Status check
check_status() {
    log_info "Checking service status..."
    
    # Check Kafka
    if nc -zv localhost 9092 &>/dev/null; then
        log_success "Kafka: Running on port 9092"
    else
        log_error "Kafka: Not running"
    fi
    
    # Check Docker Elasticsearch
    if docker ps 2>/dev/null | grep -q elasticsearch; then
        log_success "Elasticsearch: Running (Docker)"
    else
        log_error "Elasticsearch: Not running"
    fi
    
    # Check API
    if curl -s http://localhost:8000/docs > /dev/null 2>&1; then
        log_success "API Server: Running on port 8000"
    else
        log_error "API Server: Not responding"
    fi
    
    # Check workers
    if [ -f /tmp/cipherflare_workers.pid ]; then
        WORKER_PIDS=$(cat /tmp/cipherflare_workers.pid)
        RUNNING=0
        for pid in $WORKER_PIDS; do
            if ps -p $pid > /dev/null 2>&1; then
                ((RUNNING++))
            fi
        done
        log_success "Workers: $RUNNING running"
    else
        log_warn "Workers: No PID file found"
    fi
}

# View logs
view_logs() {
    echo -n "View logs for [1=API, 2=Workers, 3=Elasticsearch, 4=Exit]: "
    read choice
    
    case $choice in
        1)
            log_info "API logs:"
            tail -f /tmp/cipherflare_api.log 2>/dev/null || log_warn "No API log file"
            ;;
        2)
            log_info "Worker logs (showing worker 1, press Ctrl+C for others):"
            tail -f /tmp/cipherflare_worker_1.log 2>/dev/null || log_warn "No worker logs"
            ;;
        3)
            log_info "Docker Elasticsearch logs:"
            docker-compose -f "$PROJECT_DIR/docker-compose-parrot.yml" logs elasticsearch 2>/dev/null || podman-compose -f "$PROJECT_DIR/docker-compose-parrot.yml" logs elasticsearch 2>/dev/null
            ;;
        *)
            return
            ;;
    esac
}

# Test API
test_api() {
    log_info "Testing API endpoint..."
    
    RESPONSE=$(curl -s "http://localhost:8000/api/v1/search?keyword=ransomware" 2>&1)
    
    if echo "$RESPONSE" | grep -q '"success"'; then
        log_success "API is working!"
        echo "$RESPONSE" | "$PYTHON_BIN" -m json.tool 2>/dev/null || echo "$RESPONSE"
    else
        log_error "API test failed"
        echo "$RESPONSE"
    fi
}

# Cleanup
cleanup_project() {
    echo -n "Remove all data and containers? (yes/no): "
    read confirm
    
    if [ "$confirm" = "yes" ]; then
        log_info "Cleaning up..."
        stop_services
        
        cd "$PROJECT_DIR"
        docker-compose -f docker-compose-parrot.yml down -v 2>/dev/null || podman-compose -f docker-compose-parrot.yml down -v 2>/dev/null || true
        
        rm -rf /tmp/cipherflare_*.pid /tmp/cipherflare_*.log
        
        log_success "Cleanup complete"
    fi
}

# Main loop
while true; do
    show_menu
    read -r option
    
    case $option in
        1) setup_project ;;
        2) clean_reinstall ;;
        3) start_services ;;
        4) stop_services ;;
        5) check_status ;;
        6) view_logs ;;
        7) test_api ;;
        8) cleanup_project ;;
        9) log_info "Exiting..."; exit 0 ;;
        *) log_error "Invalid option" ;;
    esac
done
</merged_code
