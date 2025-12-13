# Monitoring API Reference

## Base URL
\`\`\`
http://localhost:8000/api/v1
\`\`\`

## Authentication
All endpoints require JWT token in `Authorization: Bearer {token}` header.

## Endpoints

### Monitoring Setup

#### Create Monitoring Job
\`\`\`
POST /monitor/target
Query Parameters:
  - url (string, required): Target .onion URL
  - interval_hours (integer, optional): Check interval in hours (default: 6)

Response:
{
  "success": true,
  "job_id": "uuid",
  "message": "Monitoring started for http://example.onion",
  "config": {
    "url": "http://example.onion",
    "interval_hours": 6,
    "user_id": "user-uuid",
    "status": "active"
  }
}
\`\`\`

### Alerts

#### Create Alert
\`\`\`
POST /alert/setup
Query Parameters:
  - keyword (string, required): Keyword to monitor
  - risk_threshold (string, optional): low|medium|high|critical (default: medium)
  - notification_type (string, optional): email|webhook|slack (default: email)
  - notification_endpoint (string, optional): Email or webhook URL

Response:
{
  "success": true,
  "alert_id": "uuid",
  "keyword": "malware",
  "risk_threshold": "high",
  "notification_type": "email",
  "status": "active",
  "created_at": "2024-01-01T00:00:00"
}
\`\`\`

#### List Alerts
\`\`\`
GET /alerts

Response:
{
  "success": true,
  "count": 3,
  "alerts": [
    {
      "id": "uuid",
      "keyword": "malware",
      "risk_threshold": "high",
      "notification_type": "email",
      "notification_endpoint": "user@example.com",
      "created_at": "2024-01-01T00:00:00",
      "is_active": true
    }
  ]
}
\`\`\`

#### Delete Alert
\`\`\`
DELETE /alert/{alert_id}

Response:
{
  "success": true,
  "message": "Alert deactivated"
}
\`\`\`

### Monitoring Results

#### List Results
\`\`\`
GET /monitoring/results
Query Parameters:
  - limit (integer, optional): Max results (default: 50, max: 500)
  - offset (integer, optional): Pagination offset (default: 0)

Response:
{
  "success": true,
  "total": 150,
  "limit": 50,
  "offset": 0,
  "results": [
    {
      "id": "uuid",
      "target_url": "http://example.onion",
      "title": "Malware Store",
      "risk_level": "critical",
      "risk_score": 9.5,
      "is_duplicate": false,
      "alerts_triggered": ["alert-uuid-1"],
      "created_at": "2024-01-01T12:00:00",
      "detected_at": "2024-01-01T12:00:00"
    }
  ]
}
\`\`\`

#### Get Result Detail
\`\`\`
GET /monitoring/results/{result_id}

Response:
{
  "success": true,
  "result": {
    "id": "uuid",
    "target_url": "http://example.onion",
    "title": "Malware Store",
    "text_excerpt": "Buy malware tools...",
    "risk_level": "critical",
    "risk_score": 9.5,
    "threat_indicators": ["malware_marketplace", "payment_accepted"],
    "is_duplicate": false,
    "duplicate_of_id": null,
    "alerts_triggered": ["alert-uuid-1"],
    "created_at": "2024-01-01T12:00:00",
    "detected_at": "2024-01-01T12:00:00"
  }
}
\`\`\`

#### Get Statistics
\`\`\`
GET /monitoring/stats

Response:
{
  "success": true,
  "stats": {
    "total_results": 150,
    "duplicate_results": 45,
    "high_risk_findings": 23,
    "unique_results": 105
  }
}
\`\`\`

### Monitoring Jobs

#### List Jobs
\`\`\`
GET /monitoring/jobs
Query Parameters:
  - status (string, optional): active|paused|completed|failed
  - limit (integer, optional): Max results (default: 50, max: 500)
  - offset (integer, optional): Pagination offset (default: 0)

Response:
{
  "success": true,
  "total": 5,
  "limit": 50,
  "offset": 0,
  "jobs": [
    {
      "id": "uuid",
      "target_url": "http://example.onion",
      "interval_hours": 6,
      "status": "active",
      "total_checks": 24,
      "findings_count": 12,
      "alerts_triggered": 3,
      "last_run_at": "2024-01-01T12:00:00",
      "next_run_at": "2024-01-01T18:00:00",
      "created_at": "2023-12-01T00:00:00"
    }
  ]
}
\`\`\`

#### Get Job Detail
\`\`\`
GET /monitoring/jobs/{job_id}

Response:
{
  "success": true,
  "job": {
    "id": "uuid",
    "target_url": "http://example.onion",
    "interval_hours": 6,
    "status": "active",
    "total_checks": 24,
    "findings_count": 12,
    "alerts_triggered": 3,
    "last_run_at": "2024-01-01T12:00:00",
    "next_run_at": "2024-01-01T18:00:00",
    "created_at": "2023-12-01T00:00:00",
    "updated_at": "2024-01-01T12:00:00"
  }
}
\`\`\`

#### Pause Job
\`\`\`
POST /monitoring/jobs/{job_id}/pause

Response:
{
  "success": true,
  "message": "Monitoring job {job_id} paused",
  "status": "paused"
}
\`\`\`

#### Resume Job
\`\`\`
POST /monitoring/jobs/{job_id}/resume

Response:
{
  "success": true,
  "message": "Monitoring job {job_id} resumed",
  "status": "active"
}
\`\`\`

#### Delete Job
\`\`\`
DELETE /monitoring/jobs/{job_id}

Response:
{
  "success": true,
  "message": "Monitoring job {job_id} deleted"
}
\`\`\`

## Error Responses

All errors follow this format:

\`\`\`json
{
  "detail": "Error message description"
}
\`\`\`

### Common Status Codes
- `200`: Success
- `400`: Bad request (invalid parameters)
- `401`: Unauthorized (missing/invalid token)
- `403`: Forbidden (access denied)
- `404`: Not found
- `500`: Server error
- `503`: Service unavailable (scheduler not ready)

## Rate Limiting
Currently unlimited. Future versions may implement per-user rate limits.

## Examples

### Complete Workflow

1. Create alert for keyword:
\`\`\`bash
curl -X POST "http://localhost:8000/api/v1/alert/setup" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d "keyword=malware&risk_threshold=high&notification_type=email&notification_endpoint=user@example.com"
\`\`\`

2. Setup monitoring job:
\`\`\`bash
curl -X POST "http://localhost:8000/api/v1/monitor/target" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d "url=http://example.onion&interval_hours=6"
\`\`\`

3. Check results:
\`\`\`bash
curl -X GET "http://localhost:8000/api/v1/monitoring/results?limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN"
\`\`\`

4. Get stats:
\`\`\`bash
curl -X GET "http://localhost:8000/api/v1/monitoring/stats" \
  -H "Authorization: Bearer YOUR_TOKEN"
\`\`\`

5. Pause/resume job:
\`\`\`bash
curl -X POST "http://localhost:8000/api/v1/monitoring/jobs/{job_id}/pause" \
  -H "Authorization: Bearer YOUR_TOKEN"
