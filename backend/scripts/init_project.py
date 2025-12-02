#!/usr/bin/env python3
"""
Initialize Dark Web API Project Structure
"""

import os
from pathlib import Path

def create_directory_structure():
    """Create project directories"""
    dirs = [
        "app/__init__.py",
        "app/api/__init__.py",
        "app/api/routes/__init__.py",
        "app/services/__init__.py",
        "app/models/__init__.py",
        "app/database/__init__.py",
        "app/schemas/__init__.py",
        "scripts/__init__.py",
        "dark_web_results",
        "logs",
    ]
    
    for d in dirs:
        path = Path(d)
        path.parent.mkdir(parents=True, exist_ok=True)
        if str(d).endswith(".py"):
            path.write_text("")
    
    print("[✓] Directory structure created")

def create_env_file():
    """Create default .env file"""
    env_content = """# Dark Web Threat Intelligence Platform
# Configuration file - customize for your environment

# Database Configuration
DATABASE_URL=sqlite+aiosqlite:///./dark_web.db
# DATABASE_URL=postgresql+asyncpg://user:password@localhost/dark_web

# Elasticsearch Configuration
ES_URL=http://localhost:9200

# Kafka Configuration
KAFKA_BOOTSTRAP=localhost:9092

# Tor Configuration
TOR_SOCKS=127.0.0.1:9050
TOR_CONTROL_HOST=127.0.0.1
TOR_CONTROL_PORT=9051
TOR_CONTROL_PASS=

# API Configuration
API_KEY=your-secret-key-here
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# Output Configuration
OUTPUT_BASE=./dark_web_results
SQL_ECHO=False

# Logging
LOG_LEVEL=INFO
"""
    
    if not Path(".env").exists():
        Path(".env").write_text(env_content)
        print("[✓] .env file created")
    else:
        print("[*] .env file already exists")

def create_gitignore():
    """Create .gitignore file"""
    gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
ENV/
env/
.venv

# IDE
.vscode/
.idea/
*.swp
*.swo

# Application
dark_web_results/
*.db
*.log
logs/
.env.local

# OS
.DS_Store
Thumbs.db

# Database
*.sqlite
*.sqlite3
"""
    
    if not Path(".gitignore").exists():
        Path(".gitignore").write_text(gitignore_content)
        print("[✓] .gitignore file created")

def main():
    print("=== Dark Web API Project Initialization ===")
    create_directory_structure()
    create_env_file()
    create_gitignore()
    print("[✓] Project initialized!")

if __name__ == "__main__":
    main()
