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
│   │   ├── main.py          # FastAPI app
│   │   └── routes/          # Endpoints
│   ├── services/
│   │   ├── worker.py        # Kafka consumer
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

## API Examples

### Search Keyword
\`\`\`bash
curl "http://localhost:8000/api/v1/search?keyword=botnet&max_results=100"
\`\`\`

### Get Job Results
\`\`\`bash
curl "http://localhost:8000/api/v1/findings/job/{job_id}?offset=0&limit=20"
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

## Security Notes

- All data is scoped per user_id
- Elasticsearch has basic auth disabled (local only)
- Kafka has no auth (local only)
- Use firewall to prevent external access
- Deploy behind reverse proxy for production

---

**Questions?** Check logs with: `bash scripts/setup.sh` → Option 5
