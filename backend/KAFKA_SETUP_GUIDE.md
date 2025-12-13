---

# Apache Kafka 4.1.0 Installation Guide (KRaft Mode) — Dedicated `kafka` User

**Goal:** Install and run Kafka 4.1.0 as a system process (no Docker) in KRaft mode with a dedicated user.

---

## Prerequisites

* ParrotOS / Debian 12 / Ubuntu 22.04+
* sudo access
* 4GB+ RAM
* 10GB+ free disk space

---

## Step 1: Install Java 17+

Kafka 4.x requires Java 11+. Install OpenJDK 17:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install default-jdk curl wget tar netcat-openbsd -y
java -version
```

Expected output:

```
openjdk version "17.0.x"
```

---

## Step 2: Create a Dedicated `kafka` System User

Create a system user with no login shell for security:

```bash
sudo useradd -r -m -s /bin/false kafka
```

This creates:

* Home directory: `/home/kafka`
* User: `kafka` (no login shell)

---

## Step 3: Download and Install Kafka 4.1.0

Install Kafka to `/opt/kafka`:

```bash
cd /opt
sudo wget https://downloads.apache.org/kafka/4.1.0/kafka_2.13-4.1.0.tgz
sudo tar -xzf kafka_2.13-4.1.0.tgz
sudo mv kafka_2.13-4.1.0 kafka
sudo rm kafka_2.13-4.1.0.tgz

# Assign ownership to kafka user
sudo chown -R kafka:kafka /opt/kafka
```

---

## Step 4: Configure Kafka for KRaft Mode

Create the KRaft configuration directory:

```bash
sudo -u kafka mkdir -p /opt/kafka/config/kraft
sudo nano /opt/kafka/config/kraft/server.properties
```

Paste this configuration:

```ini
# Kafka 4.1.0 KRaft Configuration (Combined Broker + Controller)

process.roles=broker,controller
node.id=1

listeners=PLAINTEXT://:9092,CONTROLLER://:9093
controller.listener.names=CONTROLLER
controller.quorum.voters=1@localhost:9093
advertised.listeners=PLAINTEXT://localhost:9092

log.dirs=/opt/kafka/data/kraft-combined-logs
metadata.log.dir=/opt/kafka/data/metadata

num.network.threads=3
num.io.threads=8
socket.send.buffer.bytes=102400
socket.receive.buffer.bytes=102400
socket.request.max.bytes=104857600

log.retention.hours=168
log.segment.bytes=1073741824
log.retention.check.interval.ms=300000

auto.create.topics.enable=true
offsets.topic.replication.factor=1
transaction.state.log.replication.factor=1
transaction.state.log.min.isr=1

group.initial.rebalance.delay.ms=0
```

Save (`Ctrl+O`) and exit (`Ctrl+X`).

---

## Step 5: Create Kafka Data Directories

```bash
sudo mkdir -p /opt/kafka/data/kraft-combined-logs /opt/kafka/data/metadata
sudo chown -R kafka:kafka /opt/kafka/data
```

---

## Step 6: Format KRaft Storage

Generate a cluster ID and format directories (run as `kafka` user):

```bash
cd /opt/kafka
sudo -u kafka bin/kafka-storage.sh random-uuid
KAFKA_CLUSTER_ID=$(sudo -u kafka bin/kafka-storage.sh random-uuid)
echo "Cluster ID: $KAFKA_CLUSTER_ID"

sudo -u kafka bin/kafka-storage.sh format -t $KAFKA_CLUSTER_ID -c config/kraft/server.properties
```

**Important:** Only run this once — re-running will erase data.

---

## Step 7: Test Manual Kafka Start

```bash
sudo -u kafka bin/kafka-server-start.sh config/kraft/server.properties
```

You should see:

```
[KafkaServer id=1] started
```

Press `Ctrl+C` to stop. If this works, proceed.

---

## Step 8: Create Systemd Service for Kafka

Create `/etc/systemd/system/kafka.service`:

```bash
sudo nano /etc/systemd/system/kafka.service
```

Paste:

```ini
[Unit]
Description=Apache Kafka 4.1.0 Server (KRaft Mode)
Documentation=https://kafka.apache.org/documentation/
After=network.target

[Service]
Type=simple
User=kafka
ExecStart=/opt/kafka/bin/kafka-server-start.sh /opt/kafka/config/kraft/server.properties
ExecStop=/opt/kafka/bin/kafka-server-stop.sh
Restart=on-failure
RestartSec=10
Environment="KAFKA_HEAP_OPTS=-Xmx1G -Xms512M"
StandardOutput=journal
StandardError=journal
SyslogIdentifier=kafka

[Install]
WantedBy=multi-user.target
```

Save and exit.

---

## Step 9: Enable and Start Kafka Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable kafka
sudo systemctl start kafka
sudo systemctl status kafka
```

Expected output:

```
● kafka.service - Apache Kafka 4.1.0 Server (KRaft Mode)
   Active: active (running)
```

---

## Step 10: Verify Kafka

Check port 9092:

```bash
sudo ss -tlnp | grep 9092
```

Create a test topic:

```bash
sudo -u kafka /opt/kafka/bin/kafka-topics.sh --create \
  --topic test-topic --bootstrap-server localhost:9092
```

Produce messages:

```bash
sudo -u kafka /opt/kafka/bin/kafka-console-producer.sh \
  --topic test-topic --bootstrap-server localhost:9092
```

Consume messages:

```bash
sudo -u kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --topic test-topic --from-beginning --bootstrap-server localhost:9092
```

---

## Step 11: Manage Kafka with Systemd

| Command                        | Description    |
| ------------------------------ | -------------- |
| `sudo systemctl start kafka`   | Start Kafka    |
| `sudo systemctl stop kafka`    | Stop Kafka     |
| `sudo systemctl restart kafka` | Restart Kafka  |
| `sudo systemctl status kafka`  | Check status   |
| `journalctl -u kafka -f`       | View live logs |

---

## Step 12: Only run this if you want to Uninstall Kafka

```bash
sudo systemctl stop kafka
sudo systemctl disable kafka
sudo rm /etc/systemd/system/kafka.service
sudo systemctl daemon-reload
sudo rm -rf /opt/kafka
sudo userdel -r kafka
```

---

This version **ensures Kafka runs as a dedicated, secure system user**, with correct permissions for `/opt/kafka` and the data directories.

---
