import os
from dotenv import load_dotenv

load_dotenv()

# Elasticsearch
ES_URL = os.getenv("ES_URL", "http://elasticsearch:9200")

# Kafka
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "127.0.0.1:9092")

# Tor
TOR_SOCKS = os.getenv("TOR_SOCKS", "127.0.0.1:9050")
TOR_CONTROL = os.getenv("TOR_CONTROL", "")
TOR_CONTROL_PASS = os.getenv("TOR_CONTROL_PASS", "")

# Output
OUTPUT_BASE = os.getenv("OUTPUT_BASE", "tor_scrape_output")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY", "")

# OpenRouter (optional - for accessing multiple models)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

# Ollama (optional - for local models)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:1234")
