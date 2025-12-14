#!/bin/bash

# Create missing Kafka topics for CipherFlare
# Run this script to create the status_updates topic

KAFKA_DIR="/opt/kafka"
BOOTSTRAP_SERVER="localhost:9092"

echo "[*] Creating Kafka topics..."

# Create status_updates topic (missing)
echo "[*] Creating status_updates topic..."
$KAFKA_DIR/bin/kafka-topics.sh --create \
    --topic status_updates \
    --bootstrap-server $BOOTSTRAP_SERVER \
    --partitions 3 \
    --replication-factor 1 \
    --if-not-exists

# Verify ad_hoc_jobs topic exists
echo "[*] Verifying ad_hoc_jobs topic..."
$KAFKA_DIR/bin/kafka-topics.sh --create \
    --topic ad_hoc_jobs \
    --bootstrap-server $BOOTSTRAP_SERVER \
    --partitions 3 \
    --replication-factor 1 \
    --if-not-exists

# Verify monitor_jobs topic exists
echo "[*] Verifying monitor_jobs topic..."
$KAFKA_DIR/bin/kafka-topics.sh --create \
    --topic monitor_jobs \
    --bootstrap-server $BOOTSTRAP_SERVER \
    --partitions 3 \
    --replication-factor 1 \
    --if-not-exists

echo ""
echo "[✓] Topic creation complete!"
echo ""
echo "[*] Listing all topics:"
$KAFKA_DIR/bin/kafka-topics.sh --list --bootstrap-server $BOOTSTRAP_SERVER

echo ""
echo "[*] Topic details:"
$KAFKA_DIR/bin/kafka-topics.sh --describe --bootstrap-server $BOOTSTRAP_SERVER
