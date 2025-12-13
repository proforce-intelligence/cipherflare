# Complete Monitoring Features Implementation

This document outlines the full implementation of the dark web monitoring system with scheduling, duplicate detection, and alert triggering.

## Architecture Overview

### Core Components

1. **Monitoring Job Model** (`app/models/monitoring_job.py`)
   - Stores monitoring configurations
   - Tracks job status (active, paused, completed, failed)
   - Records execution statistics (checks, findings, alerts)

2. **Monitoring Result Model** (`app/models/monitoring_result.py`)
   - Stores individual monitoring results
   - Tracks content hashes for deduplication
   - Records triggered alerts
   - Links to parent monitoring jobs

3. **APScheduler Integration** (`app/services/scheduler.py`)
   - Manages recurring monitoring jobs
   - Schedules jobs based on interval_hours configuration
   - Produces Kafka messages for worker processing
   - Updates job statistics after execution

4. **Deduplication Service** (`app/services/deduplication.py`)
   - SHA256 hashing for content matching
   - Similarity scoring (0-1 scale)
   - Significant change detection
   - Prevents duplicate findings from cluttering results

5. **Alert Triggering System** (`app/services/alert_sender.py`)
   - Matches findings against active alerts
   - Filters by keyword and risk level
   - Sends notifications via email or webhook
   - Tracks triggered alerts in results

6. **Enhanced Worker** (`app/services/worker.py`)
   - Checks for duplicate content before saving
   - Queries active alerts for user
   - Triggers alerts if conditions met
   - Saves detailed monitoring results to database

## Features

### 1. Monitoring Scheduler

**Setup monitoring job:**
\`\`\`
POST /api/v1/monitor/target?url=http://example.onion&interval_hours=6
\`\`\`

**Response:**
\`\`\`json
{
  "success": true,
  "job_id": "uuid",
  "message": "Monitoring started for http://example.onion",
  "config": {
    "url": "http://example.onion",
    "interval_hours": 6,
    "status": "active"
  }
}
\`\`\`

**Job Lifecycle:**
- Created via API or scheduler startup
- APScheduler runs checks at specified intervals
- Worker processes results asynchronously
- Results saved to database with deduplication
- Alerts triggered if conditions met

### 2. Duplicate Detection

**How it works:**
1. Content hash (SHA256) generated for each page
2. New pages compared against existing hashes
3. If hash matches, marked as duplicate
4. Similar content detected using Jaccard similarity
5. Significant changes trigger new records

**API Query Results:**
\`\`\`json
{
  "results": [
    {
      "url": "http://example.onion",
      "is_duplicate": false,
      "duplicate_of_id": null
    }
  ]
}
\`\`\`

### 3. Alert Triggering

**Create Alert:**
\`\`\`
POST /api/v1/alert/setup?keyword=malware&risk_threshold=high&notification_type=email&notification_endpoint=user@example.com
\`\`\`

**Alert Triggering in Worker:**
1. After page is scraped and content saved
2. All active alerts for user are queried
3. Alert keyword searched in content
4. Risk level compared to threshold
5. If both match, alert is triggered
6. Notification sent (email/webhook)
7. Alert ID recorded in monitoring result

**Example Flow:**
- Alert: keyword="malware", threshold="high"
- Finding: content="malware marketplace", risk="critical"
- Result: Alert triggered (critical >= high)

### 4. Monitoring Results Endpoints

**List all monitoring results:**
\`\`\`
GET /api/v1/monitoring/results?limit=50&offset=0
\`\`\`

**Get result details:**
\`\`\`
GET /api/v1/monitoring/results/{result_id}
\`\`\`

**Get monitoring statistics:**
\`\`\`
GET /api/v1/monitoring/stats
\`\`\`

**Response includes:**
- Total results count
- Duplicate results count
- High-risk findings count
- Unique results count

### 5. Monitoring Jobs Management

**List monitoring jobs:**
\`\`\`
GET /api/v1/monitoring/jobs?status=active&limit=50
\`\`\`

**Get job details:**
\`\`\`
GET /api/v1/monitoring/jobs/{job_id}
\`\`\`

**Pause job:**
\`\`\`
POST /api/v1/monitoring/jobs/{job_id}/pause
\`\`\`

**Resume job:**
\`\`\`
POST /api/v1/monitoring/jobs/{job_id}/resume
\`\`\`

**Delete job:**
\`\`\`
DELETE /api/v1/monitoring/jobs/{job_id}
\`\`\`

## Database Schema

### monitoring_jobs table
\`\`\`
id (UUID, PK)
user_id (UUID, FK)
target_url (VARCHAR 512, indexed)
interval_hours (INT)
status (ENUM: active, paused, completed, failed)
next_run_at (DATETIME, indexed)
last_run_at (DATETIME)
total_checks (INT)
findings_count (INT)
alerts_triggered (INT)
created_at (DATETIME)
updated_at (DATETIME)
\`\`\`

### monitoring_results table
\`\`\`
id (UUID, PK)
job_id (UUID, indexed)
user_id (UUID, indexed)
target_url (VARCHAR 512, indexed)
title (VARCHAR 512)
text_excerpt (TEXT)
risk_level (VARCHAR 50)
risk_score (FLOAT)
threat_indicators (JSON)
content_hash (VARCHAR 64, indexed)
is_duplicate (BOOLEAN, indexed)
duplicate_of_id (UUID)
monitor_job_id (UUID, indexed)
alerts_triggered (JSON)
created_at (DATETIME, indexed)
detected_at (DATETIME)
\`\`\`

## Running the System

### Option 1: Integrated (API with built-in scheduler)

\`\`\`bash
pip install -r requirements.txt
uvicorn app.api.main:app --reload
\`\`\`

The scheduler starts automatically on API startup and runs in the background.

### Option 2: Standalone Scheduler

For production, run scheduler separately:

\`\`\`bash
# Terminal 1: API
uvicorn app.api.main:app

# Terminal 2: Scheduler (separate service)
python app/services/scheduler_standalone.py
\`\`\`

### Option 3: Docker Compose

\`\`\`bash
docker-compose up
\`\`\`

Includes API, scheduler, worker, Kafka, and Elasticsearch.

## Testing

Run the comprehensive test suite:

\`\`\`bash
python scripts/test_monitoring.py
\`\`\`

Tests verify:
- Deduplication hashing and similarity
- Monitoring job creation and scheduling
- Alert creation and filtering
- Monitoring result storage
- Alert triggering logic
- Scheduler operations (pause/resume/delete)
- End-to-end complete flow

## Configuration

Set environment variables:

\`\`\`bash
# Database
DATABASE_URL=sqlite+aiosqlite:///./dark_web.db

# Kafka
KAFKA_BOOTSTRAP=localhost:9092

# Elasticsearch
ES_URL=http://localhost:9200

# Tor
TOR_SOCKS=127.0.0.1:9050

# Alerts (optional)
ALERT_FROM_EMAIL=alerts@darkweb.local
SMTP_HOST=localhost
SMTP_PORT=587

# CORS
CORS_ORIGINS=http://localhost:3000
\`\`\`

## Performance Considerations

1. **Deduplication**: O(1) hash lookups in database
2. **Alert Matching**: Linear scan through user's alerts (optimize with indexing if >1000 alerts)
3. **Scheduling**: APScheduler handles 1000s of concurrent jobs
4. **Results Storage**: Indexed queries by user_id and created_at
5. **Worker Processing**: Async Kafka consumer scales horizontally

## Security

1. **Row-Level Security**: All queries filtered by user_id
2. **Authentication**: JWT tokens required for all endpoints
3. **Deduplication**: Content hashes prevent direct content retrieval
4. **Alert Notifications**: Webhook URLs validated, rate-limited
5. **Email Alerts**: SMTP credentials never in logs/database

## Troubleshooting

### Scheduler Not Running
- Check if Kafka broker is available
- Verify `apscheduler` in requirements.txt
- Check logs for initialization errors

### Jobs Not Triggering
- Verify monitoring job status is "active"
- Check next_run_at timestamp
- Ensure worker is running and consuming messages

### Alerts Not Triggering
- Verify alert is_active = True
- Check keyword matches content (case-insensitive)
- Verify risk_level >= threshold

### High Duplicate Rate
- Adjust similarity_threshold in deduplication service
- Check if content_hash is being generated correctly
- Monitor database disk usage for hash index

## Future Enhancements

1. **Machine Learning**: Anomaly detection for significant changes
2. **Custom Rules**: User-defined alert rules (regex, patterns)
3. **Batching**: Group similar findings for digest emails
4. **Webhooks**: Custom webhook retry logic with exponential backoff
5. **Persistence**: Archive old results to cold storage
6. **Clustering**: Distributed scheduler for multi-node deployments
