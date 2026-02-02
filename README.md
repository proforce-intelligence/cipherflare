# CipherFlare - Dark Web Threat Intelligence Platform

A production-ready dark web monitoring and threat intelligence platform with real-time alerts, AI-powered analysis, and comprehensive search capabilities.

## Features

- **Search & Investigations**: Deep dark web content search with AI-powered threat analysis
- **Continuous Monitoring**: Automated .onion site monitoring with change detection
- **Real-time Alerts**: Configurable alerts for high-risk findings via email, webhook, or Slack
- **Threat Intelligence**: Risk scoring, threat actor attribution, and pattern analysis
- **PGP Verification**: .onion site legitimacy verification using PGP signatures
- **Multi-Model AI**: Support for Google Gemini, OpenAI, Anthropic, and more

## Architecture

### Backend (Python/FastAPI)
- `/backend` - FastAPI REST API server
- Elasticsearch for indexed findings storage
- Kafka for job queuing and async processing
- PostgreSQL for monitoring jobs and alerts
- Tor network integration for .onion access

### Frontend (Next.js/React)
- `/frontend` or root directory - Next.js 16 application
- Real-time data fetching with SWR
- TypeScript for type safety
- Tailwind CSS + shadcn/ui components

## Getting Started

### Prerequisites

- Docker & Docker Compose (for backend services)
- Node.js 18+ (for frontend)
- Python 3.10+ (for backend)

### Backend Setup

1. Navigate to backend directory:
\`\`\`bash
cd backend
\`\`\`

2. Copy environment variables:
\`\`\`bash
cp .env.example .env
\`\`\`

3. Start services with Docker:
\`\`\`bash
docker-compose up -d
\`\`\`

4. Initialize the database:
\`\`\`bash
python scripts/init_project.py
\`\`\`

5. Start the API server:
\`\`\`bash
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
\`\`\`

The API will be available at `http://localhost:8000`

### Frontend Setup

1. Navigate to frontend directory (or root):
\`\`\`bash
cd frontend  # or stay in root if frontend files are at root
\`\`\`

2. Install dependencies:
\`\`\`bash
npm install
\`\`\`

3. Create environment file:
\`\`\`bash
cp .env.local.example .env.local
\`\`\`

4. Configure the API URL in `.env.local`:
\`\`\`env
NEXT_PUBLIC_API_URL=http://localhost:8000
\`\`\`

5. Start development server:
\`\`\`bash
npm run dev
\`\`\`

The application will be available at `http://localhost:3000`

## Environment Variables

### Frontend (.env.local)

\`\`\`env
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000

# Feature Flags
NEXT_PUBLIC_ENABLE_MOCK_DATA=false
\`\`\`

### Backend (.env)

\`\`\`env
# Elasticsearch
ES_URL=http://elasticsearch:9200

# Kafka
KAFKA_BOOTSTRAP=kafka:9092

# Tor
TOR_SOCKS=127.0.0.1:9050
TOR_CONTROL=
TOR_CONTROL_PASS=

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/darkweb

# AI Providers (at least one required)
GOOGLE_API_KEY=your_google_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional
OPENROUTER_API_KEY=
OLLAMA_BASE_URL=

# CORS
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
\`\`\`

## API Endpoints

### Search
- `GET /api/v1/search` - Search dark web content
- `GET /api/v1/findings/job/{job_id}` - Get findings for a job
- `GET /api/v1/findings/summary/{job_id}` - Get AI summary
- `GET /api/v1/stats` - Get statistics

### Monitoring
- `POST /api/v1/monitor/target` - Setup target monitoring
- `GET /api/v1/monitoring/jobs` - List monitoring jobs
- `POST /api/v1/monitoring/jobs/{id}/pause` - Pause job
- `POST /api/v1/monitoring/jobs/{id}/resume` - Resume job
- `DELETE /api/v1/monitoring/jobs/{id}` - Delete job

### Alerts
- `POST /api/v1/alert/setup` - Create alert
- `GET /api/v1/alerts` - List alerts
- `DELETE /api/v1/alert/{id}` - Delete alert
- `GET /api/v1/monitoring/results` - Get monitoring results
- `GET /api/v1/monitoring/stats` - Get monitoring statistics

### Settings
- `GET /api/v1/settings/llm-providers` - Get available AI models
- `GET /api/v1/settings/pgp-verification` - Get PGP info
- `GET /api/v1/health` - Health check

## Production Deployment

### Backend Deployment

1. Set production environment variables
2. Use production Docker Compose configuration:
\`\`\`bash
docker-compose -f docker-compose-prod.yml up -d
\`\`\`

3. Run database migrations:
\`\`\`bash
python scripts/init_project.py
\`\`\`

4. Start API with production settings:
\`\`\`bash
gunicorn app.api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
\`\`\`

### Frontend Deployment

1. Build the application:
\`\`\`bash
npm run build
\`\`\`

2. Set production API URL in environment
3. Deploy to Vercel, Netlify, or your preferred platform:
\`\`\`bash
npm run start
\`\`\`

## Security Considerations

- Never expose Elasticsearch or Kafka ports publicly
- Use strong authentication for production APIs
- Rotate API keys regularly
- Enable CORS only for trusted domains
- Use HTTPS in production
- Implement rate limiting on API endpoints
- Monitor and log all security events

## Troubleshooting

### Backend Issues

**Elasticsearch connection failed:**
- Verify Elasticsearch is running: `docker ps`
- Check ES_URL in .env matches container network
- Ensure ports are not blocked

**Kafka connection failed:**
- Verify Kafka is running: `docker ps`
- Check KAFKA_BOOTSTRAP configuration
- May need to create topics: `bash scripts/create_kafka_topics.sh`

**Tor connection failed:**
- Install Tor: `apt-get install tor` or similar
- Start Tor service: `systemctl start tor`
- Configure TOR_SOCKS in .env

### Frontend Issues

**API connection failed:**
- Verify backend is running on correct port
- Check NEXT_PUBLIC_API_URL in .env.local
- Check CORS configuration in backend
- Open browser console for detailed errors

**No data showing:**
- Backend might not have indexed any data yet
- Create monitoring jobs or run searches
- Check API health endpoint: `http://localhost:8000/health`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is for educational and research purposes. Ensure compliance with local laws when monitoring dark web content.

## Support

For issues and questions:
- Check the troubleshooting section
- Review backend logs: `docker-compose logs -f`
- Review frontend console for errors
- Open an issue on GitHub
