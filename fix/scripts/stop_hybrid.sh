#!/bin/bash

echo "=== Stopping Hybrid Services ==="
echo ""

# Stop Python processes
echo "[*] Stopping Python services..."
pkill -f "uvicorn"
pkill -f "app.services.worker"
sleep 2
echo "[✓] Python services stopped"

# Stop Docker (optional)
echo "[*] Stopping Docker containers..."
docker-compose -f docker-compose-parrot.yml down
echo "[✓] Docker containers stopped"

echo ""
echo "[✓] All services stopped"
echo ""
