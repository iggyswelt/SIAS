# SIAS Setup Guide

## Prerequisites

- Ubuntu Server 22.04+ (x64)
- 16 GB RAM, 256 GB SSD
- Python 3.11+, Node.js 22+
- PostgreSQL 16+, Redis 7+
- OpenClaw installed and configured

## Installation

### 1. System Dependencies

```bash
sudo apt update && sudo apt install -y \
  python3.11 python3-pip nodejs npm \
  postgresql-16 redis-server \
  ffmpeg curl git
```

### 2. Clone Repository

```bash
git clone https://github.com/YOUR_USER/SIAS.git
cd SIAS
```

### 3. Python Dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Database Setup

```bash
sudo -u postgres createdb sias
sudo -u postgres psql -d sias -f schema.sql
```

### 5. Environment Configuration

```bash
cp .env.example .env
```

Edit `.env`:
```
DATABASE_URL=postgresql://sias_user:YOUR_PASSWORD@localhost:5432/sias
REDIS_URL=redis://localhost:6379/0
API_HOST=127.0.0.1
API_PORT=8000
OPENCLAW_HOME=/home/YOUR_USER/.openclaw
```

### 6. Start Services

```bash
# Database
sudo systemctl enable postgresql redis
sudo systemctl start postgresql redis

# SIAS Core API
cd sias_core
source ../venv/bin/activate
uvicorn main:app --host $API_HOST --port $API_PORT &

# Workers (optional, as needed)
python worker_hermes.py &
python worker_rheingold.py &
python worker_hestia.py &
```

### 7. Verify

```bash
curl http://127.0.0.1:8000/health
# Expected: {"status": "ok"}
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Redis connection refused | `sudo systemctl start redis` |
| PostgreSQL auth failed | Check `pg_hba.conf` and `.env` |
| Worker crashes | Check logs in `logs/` directory |
| Agent not receiving events | Verify Redis Pub/Sub channels |
