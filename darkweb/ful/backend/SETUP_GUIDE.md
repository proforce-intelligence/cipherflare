# Dark Web Threat Intelligence System - Setup Guide

## Prerequisites

- **ParrotOS** (or any Debian-based Linux)
- **Python 3.10+**
- **Docker or Podman**
- **Git**

## One-Command Setup

\`\`\`bash
bash scripts/setup.sh
\`\`\`

This opens an interactive menu. Select option **1** to setup.

## What Gets Installed

1. **Python Virtual Environment** (`venv/`)
2. **Python Dependencies** (FastAPI, aiokafka, elasticsearch, playwright, stem, etc.)
3. **Elasticsearch Index** with 30-day TTL
4. **Docker Images** (Elasticsearch, Kafka, Zookeeper)

## Usage

### Start Everything
\`\`\`bash
bash scripts/setup.sh
# Select option 2
\`\`\`

This starts:
- Elasticsearch on port 9200
- Kafka on port 9092
- API server on port 8000
- 2 worker processes
- Status consumer (automatically runs within API)

### Search for Threat Intelligence
\`\`\`bash
curl "http://localhost:8000/api/v1/search?keyword=ransomware&max_results=50"
\`\`\`

### API Documentation
Visit: `http://localhost:8000/docs`

### Check Status
\`\`\`bash
bash scripts/setup.sh
# Select option 4
\`\`\`

### Stop Services
\`\`\`bash
bash scripts/setup.sh
# Select option 3
\`\`\`

## Troubleshooting

### Job Status Not Updating (Frontend shows "QUEUED" forever)

**Cause**: The status consumer is not running or Kafka is not properly connected.

**Solution**:
\`\`\`bash
# Check API logs for status consumer
tail -f /tmp/cipherflare_api.log | grep StatusConsumer

# You should see:
# [✓] Status consumer started - listening for job updates

# Check worker logs to ensure status updates are being sent
tail -f /tmp/cipherflare_worker_*.log | grep "Status sent"

# Restart the API to reinitialize the status consumer
pkill -f "uvicorn app.api.main:app"
# Then start again via scripts/setup.sh option 2
\`\`\`

### Port Already in Use
\`\`\`bash
# Check what's using ports
lsof -i :8000  # API
lsof -i :9092  # Kafka
lsof -i :9200  # Elasticsearch

# Kill if needed
kill -9 <PID>
\`\`\`

### Docker Service Issues
\`\`\`bash
# Restart Docker
sudo systemctl restart docker

# Or use Podman
podman system reset
\`\`\`

### Kafka Connection Errors
\`\`\`bash
# Reset Kafka
docker-compose -f docker-compose-parrot.yml down -v
docker-compose -f docker-compose-parrot.yml up -d
\`\`\`

### ES Timeout
\`\`\`bash
# Wait longer for ES to start
sleep 30
# Then run setup again
python -m scripts.setup_es
\`\`\`

## Project Structure

\`\`\`
cipherflare/
├── app/
│   ├── api/
│   │   ├── main.py          # FastAPI app + Status Consumer
│   │   └── routes/          # Endpoints
│   ├── services/
│   │   ├── worker.py        # Kafka consumer (processes jobs)
│   │   ├── status_consumer.py  # NEW: Updates job status in DB
│   │   ├── kafka_consumer.py
│   │   ├── kafka_producer.py
│   │   ├── scraper_utils.py # Dark web scraping
│   │   ├── tor_manager.py   # Tor rotation
│   │   └── es_client.py     # Elasticsearch
│   ├── models/              # SQLAlchemy ORM
│   ├── schemas/             # Pydantic models
│   └── database/            # DB connection
├── scripts/
│   ├── setup.sh             # MAIN - Setup & Start
│   └── setup_es.py          # Create ES index
├── docker-compose-parrot.yml
├── requirements.txt
└── venv/                    # Virtual environment (auto-created)
\`\`\`

## Architecture: How Job Status Updates Work

1. **User creates job** → API creates Job record in DB with status=QUEUED
2. **API publishes to Kafka** → Job message sent to "ad_hoc_jobs" or "monitor_jobs" topic
3. **Worker consumes job** → Worker processes the job and sends status updates:
   - PROCESSING (when scraping starts)
   - COMPLETED (when finished with findings_count)
   - FAILED (if error occurs)
4. **Status updates to Kafka** → Worker sends updates to "status_updates" topic
5. **Status Consumer updates DB** → API's background status consumer listens to "status_updates" and updates Job records in real-time
6. **Frontend polls API** → Frontend fetches updated job status from database

## API Examples

### Search Keyword
\`\`\`bash
curl "http://localhost:8000/api/v1/search?keyword=botnet&max_results=100"
\`\`\`

### Get Job Status
\`\`\`bash
curl "http://localhost:8000/api/v1/jobs/{job_id}"
\`\`\`

### Get Job Results
\`\`\`bash
curl "http://localhost:8000/api/v1/jobs/{job_id}/results?offset=0&limit=20"
\`\`\`

### List All Jobs
\`\`\`bash
curl "http://localhost:8000/api/v1/jobs?limit=50&offset=0"
\`\`\`

### Get Stats
\`\`\`bash
curl "http://localhost:8000/api/v1/stats"
\`\`\`

## Performance

- Pre-indexed results: **<100ms**
- Fresh scrape queue: **Async (non-blocking)**
- Worker throughput: **~5-10 sites per minute**
- Data retention: **30 days (auto-cleanup)**
- Status update latency: **<500ms** (via Kafka)

## Security Notes

- All data is scoped per user_id
- Elasticsearch has basic auth disabled (local only)
- Kafka has no auth (local only)
- Use firewall to prevent external access
- Deploy behind reverse proxy for production

---

**Questions?** Check logs with: `bash scripts/setup.sh` → Option 5
