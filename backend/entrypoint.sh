#!/bin/bash
set -euo pipefail

TOR_CONFIG="/etc/tor/torrc-worker"

# Optional: dynamically set hashed password if env var is provided
if [[ -n "${TOR_PASSWORD:-}" ]]; then
    HASHED_PASS=$(tor --hash-password "$TOR_PASSWORD" | awk '{print $NF}')
    echo "HashedControlPassword $HASHED_PASS" >> "$TOR_CONFIG"
fi

# Start Tor in background
echo "[entrypoint] Starting Tor..."
tor -f "$TOR_CONFIG" &
TOR_PID=$!

# Function to wait for Tor to be ready
wait_for_tor() {
    echo "[entrypoint] Waiting for Tor to start..."
    for i in {1..30}; do
        if nc -z 127.0.0.1 9050 2>/dev/null; then
            echo "[entrypoint] Tor is up."
            return 0
        fi
        sleep 1
    done
    echo "[entrypoint] Tor failed to start after 30 seconds."
    exit 1
}

wait_for_tor

# Graceful shutdown handler
cleanup() {
    echo "[entrypoint] Shutting down..."
    kill "$TOR_PID" 2>/dev/null || true
    wait "$TOR_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Run the Python worker
echo "[entrypoint] Starting worker..."
cd /app
python -m app.services.worker &
WORKER_PID=$!

# Wait for worker to exit
wait "$WORKER_PID"
