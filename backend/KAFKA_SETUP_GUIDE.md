# Kafka Setup Guide (KRaft Mode - No Zookeeper)

This guide provides manual steps to set up Kafka 4.1.0 with KRaft mode. Once Kafka is running, use `bash scripts/setup.sh` to start the API and workers.


✅ Correct — as of now, the **latest Apache Kafka version is 4.1.0** (released October 2025).
Let’s update the installation guide for **Kafka 4.1.0** on **ParrotOS** (Debian-based).

---

## 🧰 1. Install Prerequisites

Kafka 4.x requires **Java 11+**. Let’s install the latest OpenJDK and some common tools:

```bash
sudo apt update
sudo apt install default-jdk curl wget tar -y
java -version
```

Make sure it prints something like:

```
openjdk version "17.0.10" ...
```

---

## ⚙️ 2. Download and Extract Kafka 4.1.0

Go to `/opt` (or wherever you want Kafka installed):

```bash
cd /opt
sudo wget https://downloads.apache.org/kafka/4.1.0/kafka_2.13-4.1.0.tgz
sudo tar -xzf kafka_2.13-4.1.0.tgz
sudo mv kafka_2.13-4.1.0 kafka
```

Now you have Kafka 4.1.0 installed at `/opt/kafka`.

---

## ⚡ 3. Run Kafka in KRaft Mode (No Zookeeper Needed)

Since Kafka 4.x fully supports **KRaft mode** (Zookeeper-free), it’s the recommended setup.

### Step 1 – Generate a cluster ID

```bash
cd /opt/kafka
KAFKA_CLUSTER_ID="$(bin/kafka-storage.sh random-uuid)"
echo $KAFKA_CLUSTER_ID
```

### Step 2 – Format the storage

```bash
bin/kafka-storage.sh format -t $KAFKA_CLUSTER_ID -c config/kraft/server.properties
```

### Step 3 – Start Kafka

```bash
bin/kafka-server-start.sh config/kraft/server.properties
```

Kafka will start on port **9092** by default.

---

## 🧪 4. Test Kafka

Open a new terminal.

### Create a topic:

```bash
cd /opt/kafka
bin/kafka-topics.sh --create --topic test-topic --bootstrap-server localhost:9092
```

### List topics:

```bash
bin/kafka-topics.sh --list --bootstrap-server localhost:9092
```

### Send messages:

```bash
bin/kafka-console-producer.sh --topic test-topic --bootstrap-server localhost:9092
```

(Type some messages, then press **Ctrl+C**)

### Read messages:

```bash
bin/kafka-console-consumer.sh --topic test-topic --from-beginning --bootstrap-server localhost:9092
```

---

## 🧹 5. Stop Kafka

Press **Ctrl+C** in the Kafka terminal to stop it cleanly.

---

## 🧠 (Optional) Add Kafka to PATH

```bash
echo 'export PATH=$PATH:/opt/kafka/bin' >> ~/.bashrc
source ~/.bashrc
```

Now you can run commands like `kafka-topics.sh` directly from anywhere.

---

## ⚙️ (Optional) Run as a Systemd Service

##kafka as systemd service
Okay now lets do clean Kafka 4.1.0 installation and setup on ParrotOS**, including a **systemd service**, running in **KRaft (no-Zookeeper)** mode.

ParrotOS is based on Debian, so these steps will also work for **Debian 12** or **Ubuntu 22.04+**.

---

# 🦜 Apache Kafka 4.1.0 Installation Guide (KRaft mode + Systemd) on ParrotOS

---

## 🧰 Step 1 — System Update & Dependencies

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install default-jdk curl wget tar -y
```

Confirm Java version:

```bash
java -version
```

Output should look like:

```
openjdk version "17.0.x"
```

---

## ⚙️ Step 2 — Download Kafka 4.1.0

We’ll install Kafka under `/opt/kafka`.

```bash
cd /opt
sudo wget https://downloads.apache.org/kafka/4.1.0/kafka_2.13-4.1.0.tgz
sudo tar -xzf kafka_2.13-4.1.0.tgz
sudo mv kafka_2.13-4.1.0 kafka
sudo rm kafka_2.13-4.1.0.tgz
```

---

## 👤 Step 3 — Create a Dedicated Kafka User

It’s best practice not to run Kafka as root.

```bash
sudo useradd -r -m -U -d /opt/kafka -s /bin/bash kafka
sudo chown -R kafka:kafka /opt/kafka
```

---

## ⚡ Step 4 — Configure Kafka for KRaft Mode

Kafka 4.x uses KRaft (no Zookeeper).
Switch to the Kafka user and configure:

```bash
sudo -u kafka -s
cd /opt/kafka
```

Generate a cluster ID:

```bash
KAFKA_CLUSTER_ID="$(bin/kafka-storage.sh random-uuid)"
echo $KAFKA_CLUSTER_ID
```

Format the storage:

```bash
bin/kafka-storage.sh format -t $KAFKA_CLUSTER_ID -c config/kraft/server.properties
```

This initializes Kafka’s internal metadata storage.

---

## 🧪 Step 5 — Manual Start Test (Optional)

Before systemd setup, test Kafka manually:

```bash
bin/kafka-server-start.sh config/kraft/server.properties
```

It should start successfully, showing logs like:

```
Kafka Server started
```

Press **Ctrl+C** to stop it.
If that worked, proceed to service setup.

---

## ⚙️ Step 6 — Create a Systemd Service for Kafka

Exit to your main (sudo) user:

```bash
exit
```

Create a new systemd service file:

```bash
sudo nano /etc/systemd/system/kafka.service
```

Paste this:

```ini
[Unit]
Description=Apache Kafka Server (KRaft mode)
Documentation=https://kafka.apache.org/documentation/
After=network.target

[Service]
Type=simple
User=kafka
ExecStart=/opt/kafka/bin/kafka-server-start.sh /opt/kafka/config/kraft/server.properties
ExecStop=/opt/kafka/bin/kafka-server-stop.sh
Restart=on-abnormal
Environment="KAFKA_HEAP_OPTS=-Xmx512M -Xms256M"

[Install]
WantedBy=multi-user.target
```

Save and exit (`Ctrl+O`, `Enter`, `Ctrl+X`).

---

## 🔁 Step 7 — Enable and Start the Service

Reload systemd:

```bash
sudo systemctl daemon-reload
```

Enable Kafka to start on boot:

```bash
sudo systemctl enable kafka
```

Start Kafka:

```bash
sudo systemctl start kafka
```

Check status:

```bash
sudo systemctl status kafka
```

You should see:

```
Active: active (running)
```

---

## 🧠 Step 8 — Verify Kafka Is Running

Check the port:

```bash
sudo netstat -tulnp | grep 9092
```

Then test by creating a topic:

```bash
sudo -u kafka /opt/kafka/bin/kafka-topics.sh --create --topic test-topic --bootstrap-server localhost:9092
```

List topics:

```bash
sudo -u kafka /opt/kafka/bin/kafka-topics.sh --list --bootstrap-server localhost:9092
```

Produce a message:

```bash
sudo -u kafka /opt/kafka/bin/kafka-console-producer.sh --topic test-topic --bootstrap-server localhost:9092
```

Consume it:

```bash
sudo -u kafka /opt/kafka/bin/kafka-console-consumer.sh --topic test-topic --from-beginning --bootstrap-server localhost:9092
```

---

## 🧹 Step 9 — Manage Kafka with systemd

| Command                        | Description          |
| ------------------------------ | -------------------- |
| `sudo systemctl start kafka`   | Start Kafka          |
| `sudo systemctl stop kafka`    | Stop Kafka           |
| `sudo systemctl restart kafka` | Restart Kafka        |
| `sudo systemctl status kafka`  | Check Kafka status   |
| `journalctl -u kafka -f`       | View Kafka logs live |

---

## ✅ Done!

You now have:

* **Apache Kafka 4.1.0**
* **Running in KRaft mode (no Zookeeper)**
* **Managed via systemd**
* **Auto-starts on boot**
* **Tested producer/consumer functionality**

---

## kafka as normal user
Perfect — let’s do a **clean reset** and reinstall **Kafka 4.1.0** so you can run it as your **normal user (with or without sudo)**, not as a dedicated `kafka` user.

I’ll walk you through **completely removing the old setup** and **starting fresh**, step by step 👇

---

# 🧹 Step 1 — Stop and Disable the Old Service (if you created one)

```bash
sudo systemctl stop kafka 2>/dev/null
sudo systemctl disable kafka 2>/dev/null
sudo rm -f /etc/systemd/system/kafka.service
sudo systemctl daemon-reload
```

---

# 🧼 Step 2 — Remove the Old Kafka User and Installation

Remove the old Kafka user and home directory:

```bash
sudo userdel -r kafka 2>/dev/null
```

Remove the old Kafka directory:

```bash
sudo rm -rf /opt/kafka
```

Now you have a clean slate. ✅

---

# 🧰 Step 3 — Install Dependencies

Make sure Java and basic tools are installed:

```bash
sudo apt update
sudo apt install default-jdk curl wget tar -y
java -version
```

You should see something like:

```
openjdk version "17.0.10"
```

---

# ⚙️ Step 4 — Download and Extract Kafka 4.1.0

Install Kafka to `/opt/kafka` as your **normal user** (using sudo only where needed):

```bash
cd /opt
sudo wget https://downloads.apache.org/kafka/4.1.0/kafka_2.13-4.1.0.tgz
sudo tar -xzf kafka_2.13-4.1.0.tgz
sudo mv kafka_2.13-4.1.0 kafka
sudo rm kafka_2.13-4.1.0.tgz
sudo chown -R $USER:$USER /opt/kafka
```

Now Kafka belongs to your regular user.

---

# 🧩 Step 5 — Create KRaft Config File

Kafka 4.x doesn’t always include the `config/kraft/` folder. Let’s make it manually.

```bash
mkdir -p /opt/kafka/config/kraft
nano /opt/kafka/config/kraft/server.properties
```

Paste this:

```ini
# Kafka 4.1.0 KRaft Configuration

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

Save (`Ctrl+O`, `Enter`, `Ctrl+X`).

---

# ⚡ Step 6 — Initialize KRaft Storage

```bash
cd /opt/kafka
KAFKA_CLUSTER_ID="$(bin/kafka-storage.sh random-uuid)"
echo $KAFKA_CLUSTER_ID
```

Then:

```bash
bin/kafka-storage.sh format -t $KAFKA_CLUSTER_ID -c config/kraft/server.properties
```

✅ Output should say something like:

```
Formatting /opt/kafka/data/metadata with clusterId ...
```

---

# 🚀 Step 7 — Test Run Kafka Manually

```bash
cd /opt/kafka
bin/kafka-server-start.sh config/kraft/server.properties
```

If you see:

```
Kafka Server started
```

then everything’s working fine.
Press **Ctrl+C** to stop it.

---

# ⚙️ Step 8 — Create a systemd Service (as Normal User / Sudo)

Now create a service that runs Kafka as your **own user**, not `kafka`.

```bash
sudo nano /etc/systemd/system/kafka.service
```

Paste this:

```ini
[Unit]
Description=Apache Kafka 4.1.0 Server (KRaft mode)
After=network.target

[Service]
Type=simple
User=%i
ExecStart=/opt/kafka/bin/kafka-server-start.sh /opt/kafka/config/kraft/server.properties
ExecStop=/opt/kafka/bin/kafka-server-stop.sh
Restart=on-failure
Environment="KAFKA_HEAP_OPTS=-Xmx1G -Xms512M"

[Install]
WantedBy=multi-user.target
```

💡 If you want the service to always run under **your current user**, replace:

```
User=%i
```

with:

```
User=yourusername
```

Save and exit.

---

# 🔁 Step 9 — Enable and Start Kafka

Reload and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable kafka
sudo systemctl start kafka
sudo systemctl status kafka
```

You should see:

```
Active: active (running)
```

---

# 🧠 Step 10 — Verify Kafka Works

Check port:

```bash
sudo netstat -tulnp | grep 9092
```

Create a test topic:

```bash
/opt/kafka/bin/kafka-topics.sh --create --topic test --bootstrap-server localhost:9092
```

List topics:

```bash
/opt/kafka/bin/kafka-topics.sh --list --bootstrap-server localhost:9092
```

Produce and consume:

```bash
/opt/kafka/bin/kafka-console-producer.sh --topic test --bootstrap-server localhost:9092
```

(Type a few messages, then Ctrl+C)

```bash
/opt/kafka/bin/kafka-console-consumer.sh --topic test --from-beginning --bootstrap-server localhost:9092
```

---

# 🧹 Step 11 — Managing Kafka

| Command                        | Description    |
| ------------------------------ | -------------- |
| `sudo systemctl start kafka`   | Start Kafka    |
| `sudo systemctl stop kafka`    | Stop Kafka     |
| `sudo systemctl restart kafka` | Restart Kafka  |
| `sudo systemctl status kafka`  | Check status   |
| `journalctl -u kafka -f`       | View live logs |

---

✅ **Now you have Kafka 4.1.0 fully running under your own user (no `kafka` user)**, systemd-managed, in KRaft mode, ready for development or local testing.

---



## Next Steps

Once Kafka is running and verified, start the API and workers:

\`\`\`bash
bash scripts/setup.sh
# Select option 1 for Setup (first time)
# Select option 3 for Start Services (after)
\`\`\`

The script assumes Kafka is already running on `localhost:9092`.
