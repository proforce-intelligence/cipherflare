# Dark Web Threat Intelligence API

Production-grade dark web monitoring and threat intelligence platform with Tor integration, Elasticsearch indexing, and Kafka job processing.

## Architecture

\`\`\`
┌─────────────────────────────────────────────────────────────────┐
│                      Client Requests                             │
└────────────────────────┬────────────────────────────────────────┘
                         │
         ┌───────────────▼────────────────┐
         │     FastAPI Server (Port 8000) │ ◄─── Queries Elasticsearch
         │  - /api/v1/search              │       instantly
         │  - /api/v1/monitor/target      │       Queues to Kafka
         │  - /findings/job/{job_id}      │
         └───────────────┬────────────────┘
                         │
         ┌───────────────▼────────────────────┐
         │       Kafka Topics                  │
         │  - ad_hoc_jobs                      │
         │  - monitor_jobs                     │
         │  - status_updates                   │
         └───────────────┬────────────────────┘
                         │
      ┌──────────────────┴──────────────────┐
      │                                     │
┌─────▼──────────────────┐    ┌────────────▼───────┐
│  Scraper Workers (2-6) │    │  Elasticsearch     │
│  - Consume jobs        │    │  - Index findings  │
│  - Execute scraping    │───▶│  - Enable search   │
│  - Tor rotation        │    │  - 30-day TTL      │
│  - Risk scoring        │    └────────────────────┘
└────────────────────────┘
         │
      ┌──▼──────────────────┐
      │  Dark Web Content   │
      │  - .onion sites     │
      │  - Torch search     │
      │  - Entity extraction│
      └─────────────────────┘
\`\`\`

## Quick Start

### Prerequisites
- Ubuntu 22.04+ (other Linux distros with adaptations)
- 32GB RAM recommended (for Elasticsearch + workers)
- 50GB free disk space

### Installation

1. **Run setup script** (installs all dependencies):
   \`\`\`bash
   bash scripts/setup_ubuntu.sh
   \`\`\`

2. **Verify services**:
   \`\`\`bash
   # Tor
   curl -x socks5h://127.0.0.1:9050 https://check.torproject.org
   
   # Elasticsearch
   curl http://localhost:9200
   
   # Kafka
   /opt/kafka/bin/kafka-topics.sh --list --bootstrap-server localhost:9092
   \`\`\`

3. **Start API server**:
   \`\`\`bash
   bash scripts/start_api.sh
   \`\`\`

4. **Start workers** (in separate terminal):
   \`\`\`bash
   bash scripts/start_workers.sh 2  # Start 2 workers
   \`\`\`

### API Usage

#### 1. Search Dark Web
\`\`\`bash
curl -X POST \
  'http://localhost:8000/api/v1/search?keyword=ransomware&max_results=10'
\`\`\`

Response:
\`\`\`json
{
  "success": true,
  "indexed_findings": [...],
  "indexed_count": 5,
  "job_id": "xyz-123",
  "message": "Returned 5 pre-indexed results. Fresh scrape queued."
}
\`\`\`

#### 2. Get Findings for Job
\`\`\`bash
curl 'http://localhost:8000/api/v1/findings/job/xyz-123?offset=0&limit=20'
\`\`\`

#### 3. Setup Monitoring
\`\`\`bash
curl -X POST \
  'http://localhost:8000/api/v1/monitor/target?url=example.onion&interval_hours=6'
\`\`\`

#### 4. Get Statistics
\`\`\`bash
curl 'http://localhost:8000/api/v1/stats'
\`\`\`

#### 5. Setup Alert
\`\`\`bash
curl -X POST \
  'http://localhost:8000/api/v1/alert/setup?keyword=bitcoin&risk_threshold=high&notification_type=email&notification_endpoint=admin@example.com'
\`\`\`

## Configuration

Edit `.env` file:

\`\`\`env
# Database
DATABASE_URL=sqlite+aiosqlite:///./dark_web.db  # Use PostgreSQL in production

# Elasticsearch
ES_URL=http://localhost:9200

# Kafka
KAFKA_BOOTSTRAP=localhost:9092

# Tor
TOR_SOCKS=127.0.0.1:9050
TOR_CONTROL_HOST=127.0.0.1
TOR_CONTROL_PORT=9051
TOR_CONTROL_PASS=

# API
API_KEY=demo-key  # Change in production
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# Files
OUTPUT_BASE=./dark_web_results
\`\`\`

## Data Flow

### Ad-hoc Search (Keyword)
1. Client: `POST /api/v1/search` with keyword
2. API: Query Elasticsearch for pre-indexed findings
3. API: Queue job to Kafka `ad_hoc_jobs` topic
4. Client: Receive pre-indexed results + job_id immediately
5. Worker: Consume job → search Torch → scrape .onion URLs
6. Worker: Extract entities, calculate risk, analyze sentiment
7. Worker: Index findings to Elasticsearch
8. Client: Poll `/findings/job/{job_id}` for new findings as they arrive

### Targeted Monitoring (URL)
1. Client: `POST /api/v1/monitor/target` with .onion URL
2. API: Queue job to Kafka `monitor_jobs` topic
3. Worker: Consume job → directly scrape URL (no Torch search)
4. Worker: Extract data, calculate risk, index to Elasticsearch
5. Worker: Re-queue job for next interval
6. Client: Can check results via `/findings/job/{job_id}`

## Performance

- **Search latency**: ~100ms (pre-indexed results)
- **Scrape time per URL**: 10-30s (depends on site size)
- **Max concurrent scrapes**: 2-4 per worker (async Playwright)
- **Worker throughput**: ~3-5 URLs/minute per worker
- **Scaling**: Add more workers to horizontal scale

## Features

- ✅ Torch search engine integration
- ✅ Tor proxy rotation via stem
- ✅ Playwright-based scraping
- ✅ Entity extraction (emails, crypto addresses, PGP keys)
- ✅ Risk scoring (0-100 scale)
- ✅ Sentiment analysis
- ✅ Elasticsearch full-text search
- ✅ 30-day automatic data retention
- ✅ Kafka-based job queue
- ✅ Async Python (FastAPI + aiohttp)
- ✅ Multi-worker scaling
- ✅ User-scoped data filtering

## Troubleshooting

### Tor Not Working
\`\`\`bash
# Check Tor service
sudo systemctl status tor

# Restart Tor
sudo systemctl restart tor

# Verify connectivity
curl -x socks5h://127.0.0.1:9050 https://check.torproject.org
\`\`\`

### Elasticsearch Issues
\`\`\`bash
# Check status
curl http://localhost:9200

# Check logs
tail -f /var/log/elasticsearch/elasticsearch.log

# Restart service
sudo systemctl restart elasticsearch
\`\`\`

### Kafka Issues
\`\`\`bash
# Check topics
/opt/kafka/bin/kafka-topics.sh --list --bootstrap-server localhost:9092

# Monitor consumer lag
/opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 --group dark-web-workers --describe

# Restart brokers
sudo systemctl restart kafka-zookeeper kafka
\`\`\`

### API Not Starting
\`\`\`bash
# Check logs
tail -f app.log

# Verify dependencies
pip list | grep -E "fastapi|sqlalchemy|elasticsearch"

# Reinstall
pip install -r requirements.txt --force-reinstall
\`\`\`

## Production Deployment

### Recommended Changes
1. **Database**: Use PostgreSQL instead of SQLite
2. **Auth**: Implement JWT-based authentication
3. **Secrets**: Use environment-based secret management
4. **Monitoring**: Add Prometheus metrics
5. **Logging**: Centralize logs to ELK stack
6. **Scaling**: Deploy on Kubernetes
7. **Storage**: Use S3 for file storage instead of local filesystem
8. **SSL/TLS**: Enable HTTPS

## API Documentation

Once running, visit: `http://localhost:8000/docs`

## License

Proprietary - Threat Intelligence System

## Support

For issues, check logs and documentation above. For production deployments, refer to architecture guide.
