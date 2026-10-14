# Jocotoco Smart Bioacoustic Monitor — Proof of Concept (PoC)

[![Acceptance Tests](https://img.shields.io/badge/ToR%20Acceptance%20Tests-5%2F5%20Passed-10b981.svg)]()
[![Hardware Emulation](https://img.shields.io/badge/Hardware-20%20x%20Raspberry%20Pi%205-blue.svg)]()
[![Security](https://img.shields.io/badge/Security-Ed25519%20Per--Request%20Signatures-38bdf8.svg)]()
[![Cloud Ready](https://img.shields.io/badge/Deployment-Railway%20%2B%20Supabase-7c3aed.svg)]()

> **Institutional Reference:** Terms of Reference (ToR) — Comprehensive Platform for the Jocotoco Smart Bioacoustic Monitor  
> **Client:** Fundación de Conservación Jocotoco  
> **Repository:** Proof of Concept companion to the Technical & Financial Proposal

---

## 1. Executive Summary & Capabilities Demonstrated

This Proof of Concept (PoC) provides a functioning, testable implementation of the core technical pillars defined in the Jocotoco proposal:

1. **Simulated Swarm of 20 Raspberry Pi 5 Edge Monitors:**
   - 20 distinct hardware nodes geographically distributed across 6 Jocotoco ecological reserves in Ecuador (*Buenaventura, Tapichalaca, Yanacocha, Canandé, Narupa, Antisanilla*).
   - Generates authentic **100 kB (100,000 bytes) 16-bit PCM pink noise audio files** ($1/f$ spectral slope) modeling bioacoustic triggers.
   - Transactional local **SQLite queue** per device simulating power cuts and network blackouts without data loss.

2. **Cryptographic Identity Tailored for Cloud Proxies (Ed25519):**
   - Solves the cloud reverse-proxy mTLS-termination limitation by enforcing cryptographic signatures directly at the application layer over standard HTTPS.
   - Headers: `X-Device-Id`, `X-Timestamp`, `X-Signature` over `SHA256(payload) + timestamp` with a strict 120-second anti-replay window.

3. **Multi-Tenant Relational Data Layer (PostgreSQL / PostGIS):**
   - Standard SQL migration scripts with portable Row-Level Security (RLS) driven by `app.current_tenant_id` session context.
   - Direct turnkey interface with **Supabase PostgreSQL** and **PostGIS**.

4. **Resilient Over-The-Air (OTA) Management:**
   - Chunked Range HTTP manifest server (`Range: bytes=X-Y` / HTTP 206) for interrupted network recovery and checksum validation.

5. **Cloud Deployment Ready for Railway:**
   - Containerized orchestration with multi-stage `Dockerfile`, `railway.json`, and `Procfile`.
   - Integrated operations dashboard with interactive Leaflet map, audio playback, and live telemetry feeds.

---

## 2. Directory Layout

```
smart-monitor-poc/
├── README.md                      # Architecture and operational manual
├── railway.json                   # Railway container deployment configuration
├── Dockerfile                     # Multi-stage production container
├── Procfile                       # PaaS process manager definition
├── requirements.txt               # Lightweight runtime dependencies
├── .env.example                   # Environment variable template
├── api/
│   ├── server.py                  # Ingestion, storage, OTA, and dashboard server
│   └── auth.py                    # Ed25519 signature verification middleware
├── simulator/
│   ├── pink_noise.py              # Pure Python 100 kB pink noise WAV generator
│   ├── device.py                  # Raspberry Pi 5 edge daemon simulator
│   ├── swarm.py                   # Swarm manager (20 Pis across 6 reserves)
│   ├── run_swarm.py               # CLI tool to burst simulate detection events
│   └── sync_client.py             # Resumable edge-to-cloud synchronization
├── database/
│   ├── client.py                  # Dual-mode database client (Supabase / SQLite)
│   └── migrations/
│       ├── 001_initial_schema.sql # DDL with PostGIS & Portable RLS
│       └── 002_seed_swarm.sql     # Seed reserves and 20 devices with GPS
├── dashboard/
│   ├── templates/index.html       # Operations dashboard template
│   └── static/
│       ├── style.css              # Modern dark-theme UI stylesheet
│       └── app.js                 # Leaflet map & audio playback logic
├── scripts/
│   ├── setup_supabase.py          # Turnkey Supabase migration and RLS validator
│   └── test_acceptance.py         # Automated ToR Acceptance Test runner
└── data/
    ├── devices.json               # 20 Pis metadata & Ed25519 public keys
    ├── audio_clips/               # Generated 100 kB audio files
    └── sqlite_buffers/            # Local SQLite queues per device
```

---

## 3. Quickstart Guide (Local Execution)

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Generate 100 kB Pink Noise Clips for the 20-Pi Swarm
```bash
python3 -m simulator.run_swarm --clips 1 --bytes 100000
```
*Output: 20 exact 100,000-byte pink noise WAV clips (2.0 MB total) and 20 local SQLite buffers.*

### Step 3: Run the Automated Acceptance Test Suite
```bash
python3 scripts/test_acceptance.py
```
*Verifies 100 kB audio size, Ed25519 signatures, tamper rejection, replay defense, SQLite state transitions, and idempotency (5/5 tests pass).*

### Step 4: Start the Platform API & Dashboard
```bash
python3 -m api.server
```
Visit **`http://localhost:8000`** to view the interactive map of the 20 Pis across Ecuador, listen to the pink noise audio clips, and inspect telemetry!

### Step 5: Simulate Swarm Ingestion Sync
In a separate terminal:
```bash
python3 simulator/sync_client.py http://127.0.0.1:8000
```
*Uploads all queued clips, verifies Ed25519 signatures, and registers detections.*

---

## 4. Interfacing with Supabase

The user has a Supabase organization set up. To link this PoC directly to Supabase:

### Method A: Automated CLI Setup
1. In your Supabase dashboard, go to **Project Settings** $\longrightarrow$ **Database** $\longrightarrow$ **Connection String (URI)**.
2. Run the migration script:
```bash
python3 scripts/setup_supabase.py --db-url "postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres"
```
This script automatically:
- Checks and enables the `postgis` extension.
- Creates all relational tables and portable Row-Level Security policies.
- Seeds the 6 Jocotoco reserves and 20 Raspberry Pis.
- Uploads the generated Ed25519 public keys.
- Executes two automated queries verifying multi-tenant isolation.

### Method B: Supabase SQL Editor (Copy-Paste)
You can also run the SQL files directly in the Supabase web dashboard:
1. Open `database/migrations/001_initial_schema.sql` and run it in the **SQL Editor**.
2. Open `database/migrations/002_seed_swarm.sql` and run it in the **SQL Editor**.

---

## 5. Interfacing with Railway

To deploy this proof of concept to Railway with zero server maintenance:

### Step 1: Initialize Railway Project
1. Log into [Railway.app](https://railway.app).
2. Click **New Project** $\longrightarrow$ **Deploy from GitHub repo** (or use the Railway CLI).

### Step 2: Link Environment Variables
In Railway Project Settings, add:
- `DATABASE_URL`: Your Supabase connection string (use the Session Pooler URI on port `5432` or Transaction Pooler on `6543`).
- `PORT`: `8000` (automatically injected by Railway).

### Step 3: Deploy
Railway will automatically detect `railway.json` and `Dockerfile`, build the image, run the build-time swarm generator, and expose the live HTTPS dashboard with automated health checks at `/healthz`.

---

## 6. Mapping to the ToR Acceptance Tests

| Test | ToR Requirement | PoC Implementation & Validation |
| :---: | :--- | :--- |
| **1** | **Ingestion Interruption & Resumption** | Edge monitors store events in local SQLite (`events_buffer`). If connection drops, clips remain queued and resume without data loss or duplicates (`simulator/device.py`, `scripts/test_acceptance.py`). |
| **2** | **Multi-Tenant Isolation (RLS)** | Relational policies enforce `app.current_tenant_id` at the database engine level, verified in `scripts/setup_supabase.py`. |
| **3** | **Resumable OTA Model Update** | Manifest delivers chunked byte boundaries and hashes (`/api/v1/ota/manifest`), validated in Acceptance Test 5. |
| **4** | **Hardware / Crypto Authentication** | Asymmetric Ed25519 signing over `SHA256(payload) + timestamp` prevents replay attacks and bypasses TLS proxy termination issues (`api/auth.py`). |
| **5** | **100 kB Bioacoustic Noise Standard** | Authentic $1/f$ pink noise WAV clips synthesized with exact 100,000-byte length and canonical 44-byte RIFF headers (`simulator/pink_noise.py`). |
