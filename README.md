# Bulk Certificate Generator

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Celery](https://img.shields.io/badge/Celery-5.3%2B-37814A.svg)](https://docs.celeryq.dev/)
[![SQLite](https://img.shields.io/badge/Database-SQLite%20%2F%20PostgreSQL-003B57.svg)](https://www.sqlite.org/)
[![Tests](https://img.shields.io/badge/Tests-16%20Passed-success.svg)](tests/)

A robust, production-ready backend service designed to generate **customized PDF certificates in bulk** from a predefined template. It provides asynchronous task processing, live job status tracking, failure isolation, and certificate download endpoints.

---

## Table of Contents

1. [Executive Summary (In Plain Terms)](#executive-summary-in-plain-terms)
2. [Key Features](#key-features)
3. [Architecture & Workflow](#architecture--workflow)
4. [Project Structure](#project-structure)
5. [Prerequisites](#prerequisites)
6. [Step-by-Step Setup Guide](#step-by-step-setup-guide)
7. [Running the Application](#running-the-application)
8. [How to Use & Test the App](#how-to-use--test-the-app)
   - [Option A: Interactive Web UI (Easiest for Non-Technical Users)](#option-a-interactive-web-ui-easiest-for-non-technical-users)
   - [Option B: Interactive API Documentation (Swagger)](#option-b-interactive-api-documentation-swagger)
   - [Option C: Command Line (cURL)](#option-c-command-line-curl)
9. [API Specification](#api-specification)
10. [Design & Architectural Decisions](#design--architectural-decisions)
11. [System Limitations](#system-limitations)
12. [Future Work & Scaling Roadmap](#future-work--scaling-roadmap)
13. [Running Automated Tests](#running-automated-tests)
14. [Troubleshooting Guide](#troubleshooting-guide)

---

## Executive Summary (In Plain Terms)

When an organization hosts a webinar, course, or conference, they often need to issue hundreds or thousands of certificates at once:
- **The Problem:** Generating hundreds of high-resolution PDF certificates one-by-one or within a single browser request causes timeouts, server crashes, and frustrating wait times. If one recipient's email or name is corrupt, traditional scripts often crash and lose the entire batch.
- **Our Solution:** 
  1. The client submits a single list of recipients to the API.
  2. The server instantly acknowledges the request with a **Job ID** (returning in milliseconds).
  3. A background worker generates the PDF certificates asynchronously in the background.
  4. If any single certificate fails (e.g. malformed data or rendering error), it is flagged with an error message while **all other certificates continue generating uninterrupted**.
  5. The client can monitor live progress and download the completed PDFs at any time.

---

## Key Features

- **Bulk Request Ingestion:** Submit up to 1,000 recipients in a single API call.
- **Asynchronous Processing:** Powered by Celery and Redis so API requests never time out.
- **Fault-Tolerant & Isolated:** A failure on one certificate row does not abort the remaining certificates in the job.
- **Real-Time Job Tracking:** Track jobs through `pending`, `processing`, `completed`, and `failed` states with exact success/failure counts.
- **Relational Data Persistence:** Uses SQLAlchemy models with SQLite (zero-setup default) and PostgreSQL compatibility.
- **High-Quality Vector PDFs:** Programmatically rendered landscape certificates generated using ReportLab.
- **Interactive Web UI:** Built-in web dashboard at `/ui` to test and demonstrate the entire workflow without coding.
- **Comprehensive Test Suite:** 16 automated tests covering validation, edge cases, failures, and retrieval.

---

## Architecture & Workflow

```
[ Client / Web UI / cURL ]
           │
           │  1. POST /jobs (Recipients List)
           ▼
┌───────────────────────────────┐
│         FastAPI App           │ ─── 2. Validate input & save Job in SQLite / Postgres
└───────────────────────────────┘
           │
           │  3. Enqueue job_id
           ▼
┌───────────────────────────────┐
│       Redis Message Queue     │
└───────────────────────────────┘
           │
           │  4. Pick up job_id
           ▼
┌───────────────────────────────┐
│        Celery Worker          │ ─── 5. Generate PDFs using ReportLab
└───────────────────────────────┘     6. Update Certificate status & Job progress
           │
           ▼
┌───────────────────────────────┐
│     Certificates Storage      │ ─── 7. Client downloads generated PDFs via GET /certificates/{id}/download
└───────────────────────────────┘
```

---

## Project Structure

```
bulk-certificate-generator/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application, route definitions & static mounts
│   ├── models.py               # SQLAlchemy relational models (Job, Certificate)
│   ├── schemas.py              # Pydantic data schemas & request validation
│   ├── database.py             # Database engine, session maker & Base declarative
│   ├── config.py               # Environment configuration settings
│   ├── certificate_generator.py # ReportLab PDF canvas & layout engine
│   ├── tasks.py                # Job execution logic & Celery task handlers
│   ├── celery_app.py           # Celery broker & worker configuration
│   └── static/
│       └── index.html          # Interactive, browser-based demonstration UI
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # Test fixtures (in-memory SQLite, test client, Celery mock)
│   ├── test_api.py             # API endpoint tests (validation, limits, status, download)
│   └── test_tasks.py           # Worker unit tests & failure isolation verification
├── example_request.json        # Ready-to-use sample payload with multiple recipients
├── docker-compose.yml          # Quick-start Docker setup for Redis (and PostgreSQL)
├── pytest.ini                  # Pytest configuration
├── requirements.txt            # Python dependencies
├── .env.example                # Example environment configuration
├── .gitignore                  # Git ignore rules
└── README.md                   # Documentation
```

---

## Prerequisites

- **Python:** Version 3.10 or higher (Python 3.11 or 3.12 recommended).
- **Redis:** Required as the message broker for the background worker. Easiest via Docker or native Redis.
- **Git:** For cloning and version control.

---

## Step-by-Step Setup Guide

### 1. Clone & Enter Directory

```bash
git clone https://github.com/Ganasekhar-gif/bulk-certificate-generator.git
cd bulk-certificate-generator
```

### 2. Create Virtual Environment & Install Dependencies

**On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**On macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Environment (Optional)

A default `.env.example` is provided with sensible local defaults:
```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```
*Note: SQLite is used by default (`certificates.db`). No database server configuration is required.*

### 4. Start Redis

Run Redis using Docker (recommended):
```bash
docker compose up -d redis
```
*(Or use any running Redis instance on `localhost:6379`)*.

---

## Running the Application

The system requires two processes running simultaneously: **the FastAPI web server** and **the Celery worker**.

### Terminal 1: Start the API Server
Ensure your virtual environment is active:
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
- The server will start at: `http://localhost:8000`
- Interactive Swagger docs: `http://localhost:8000/docs`
- Interactive Demo UI: `http://localhost:8000/ui`

### Terminal 2: Start the Celery Worker
Open a second terminal, navigate to the project directory, activate the virtual environment, and run:

**On Windows:**
```powershell
celery -A app.celery_app worker --loglevel=info --pool=solo
```
> **Note for Windows Users:** The `--pool=solo` flag is required on Windows to prevent `PermissionError` and multiprocessing spawn issues.

**On macOS / Linux:**
```bash
celery -A app.celery_app worker --loglevel=info
```

*When the worker starts, verify that `app.tasks.process_certificate_generation` appears under `[tasks]`.*

---

## How to Use & Test the App

### Option A: Interactive Web UI (Easiest for Non-Technical Users)

Open your web browser and navigate to:
👉 **`http://localhost:8000/ui`**

1. Click **"Load sample data"** (or add recipient names manually).
2. Click **"Generate certificates"**.
3. Watch the real-time progress bar update as the background worker processes each recipient.
4. Download the generated PDF certificates directly from the results table.

### Option B: Interactive API Documentation (Swagger)

Navigate to **`http://localhost:8000/docs`**:
1. Locate `POST /jobs`, click **Try it out**, paste the JSON payload, and click **Execute**.
2. Copy the returned `id` (Job ID).
3. Check status using `GET /jobs/{job_id}/status`.
4. Inspect or download certificates using `GET /certificates/{certificate_id}/download`.

### Option C: Command Line (cURL)

**1. Submit a Generation Request:**
```bash
curl -X POST "http://localhost:8000/jobs" \
  -H "Content-Type: application/json" \
  -d @example_request.json
```
*Response:*
```json
{
  "id": 1,
  "status": "pending",
  "total_recipients": 5,
  "successful_count": 0,
  "failed_count": 0,
  "created_at": "2026-10-07T17:15:00",
  "completed_at": null,
  "error_message": null
}
```

**2. Check Job Status:**
```bash
curl "http://localhost:8000/jobs/1/status"
```

**3. List Certificates for Job:**
```bash
curl "http://localhost:8000/jobs/1/certificates"
```

**4. Download a Certificate PDF:**
```bash
curl -O -J "http://localhost:8000/certificates/1/download"
```

---

## API Specification

| Endpoint | Method | Description | Success Code |
|:---------|:------:|:------------|:------------:|
| `/jobs` | `POST` | Submit bulk recipient list and start generation job | `201 Created` |
| `/jobs/{job_id}` | `GET` | Retrieve job status, metadata, and all certificate records | `200 OK` |
| `/jobs/{job_id}/status` | `GET` | Lightweight status check (ideal for client polling) | `200 OK` |
| `/jobs/{job_id}/certificates`| `GET` | Retrieve list of certificates belonging to a job | `200 OK` |
| `/certificates/{id}` | `GET` | Retrieve single certificate details and file path | `200 OK` |
| `/certificates/{id}/download`| `GET` | Download generated PDF certificate | `200 OK` |
| `/jobs` | `GET` | List all historical generation jobs (paginated) | `200 OK` |
| `/ui` | `GET` | Visual interactive web interface | `200 OK` |
| `/docs` | `GET` | OpenAPI / Swagger interactive documentation | `200 OK` |

---

## Design & Architectural Decisions

| Aspect | Decision | Rationale |
|:-------|:---------|:----------|
| **Framework** | **FastAPI** | High performance, automatic OpenAPI/Swagger documentation, native async support, and robust type validation via Pydantic. |
| **Bulk Processing Design** | **Single Job ID for Batch** | Allows clients to submit hundreds of recipients in one HTTP call, tracking the entire campaign under a single identifier rather than tracking hundreds of disconnected requests. |
| **Async vs Sync** | **Celery + Redis (Asynchronous)** | Rendering PDFs is CPU- and I/O-intensive (~50–150ms per certificate). Processing synchronously would cause HTTP timeouts on large batches. Offloading to Celery returns an immediate 201 response while isolating workload spikes. |
| **Failure Isolation** | **Per-Recipient Try/Except** | Certificate creation loops execute within individual try/except blocks. If a recipient causes a rendering exception, their record is marked `failed` with an explicit `error_message`, while the remaining recipients complete successfully. The job is marked `completed` (or partial success). |
| **Relational Database** | **SQLAlchemy + SQLite / PostgreSQL** | Relational models (`Job` 1-to-many `Certificate`) enforce relational consistency with foreign key cascading. SQLite provides zero-dependency local evaluation, while PostgreSQL is supported by changing one environment variable. |
| **Certificate Engine** | **ReportLab** | Generates high-resolution, vector-based PDF files programmatically with customizable typography, colors, borders, and margins without external browser or headless engine dependencies. |

---

## System Limitations

While the current implementation fulfills all core assignment requirements, the following architectural and operational limitations exist:

1. **Batch Size Limit per Request:**
   - **Enforced Limit:** The API enforces a **maximum limit of 1,000 recipients per single job request** (`max_length=1000` via Pydantic schema validation).
   - **Why:** Sending JSON payloads larger than 1,000 recipients over a single HTTP connection can cause memory spikes, payload bloat, and prolonged database write transactions during the initial job creation stage.
2. **Sequential Worker Execution within a Job:**
   - A single Celery task processes all recipients in a job sequentially. For a batch of 1,000 recipients taking ~100ms each, a single worker will take ~100 seconds to complete the entire job.
3. **Database Write Concurrency (SQLite):**
   - SQLite uses file-level locking during write operations. Under high concurrent write traffic across multiple parallel workers, SQLite may encounter database locks. (Production environments should use PostgreSQL).
4. **Local File Storage:**
   - Generated PDFs are stored on the local server filesystem (`certificates/`). In a horizontally scaled cluster with multiple API servers, certificates generated on Worker Node A would not be directly downloadable from Worker Node B without shared storage.
5. **Single-Certificate Downloads:**
   - Download is currently supported per certificate (`GET /certificates/{id}/download`). There is currently no endpoint to download an entire job batch as a single compressed ZIP file.
6. **Fixed Visual Template:**
   - Uses a single predefined landscape template. Dynamic template switching, custom organization logos, or custom fonts are not yet supported.

---

## Future Work & Scaling Roadmap

The following enhancements are planned to address the limitations identified above:

1. **High-Throughput Chunking & Worker Fan-Out:**
   - For jobs exceeding 1,000 recipients (e.g. 10,000 to 100,000 recipients), implement **Celery Chunks / Groups / Chords**. A parent job will partition the recipient list into micro-batches of 50–100 recipients and dispatch them concurrently across a distributed cluster of Celery workers.
2. **Cloud Object Storage (S3 / GCS / Azure Blob):**
   - Replace local disk storage with cloud storage (such as AWS S3 or Google Cloud Storage). Return time-limited presigned download URLs for secure, direct-to-client streaming, decoupling storage from server instances.
3. **Bulk ZIP Download Endpoint:**
   - Add a `GET /jobs/{job_id}/download-all` endpoint that archives all successful PDFs into a `.zip` file on demand or via a background streaming response.
4. **File Ingestion (CSV / Excel Upload):**
   - Provide an endpoint `POST /jobs/upload` that accepts `.csv` and `.xlsx` spreadsheets directly. This allows non-technical event coordinators to upload participant exports without manually formatting JSON.
5. **Direct Automated Email Dispatch:**
   - Integrate an email worker (e.g., via SendGrid or AWS SES) to automatically deliver each certificate directly to the participant's email upon successful generation.
6. **Multi-Template Engine & Visual Editor:**
   - Support selectable templates (e.g., *Attendance*, *Excellence*, *Participation*) with customizable logos, signatures, and primary brand colors stored as JSON template definitions or HTML/Jinja2-based rendering.
7. **Production Migrations with Alembic:**
   - Integrate Alembic for database schema versioning and automated migrations across development, staging, and production PostgreSQL databases.

---

## Running Automated Tests

The project includes 16 automated tests covering all critical paths:
- Job creation and validation (including email format, empty recipient lists, and the 1,000-recipient batch limit).
- Status retrieval and 404 handling.
- PDF generation rendering logic.
- Individual failure resilience (ensuring failures do not block other recipients).
- Certificate retrieval and download restrictions on failed certificates.
- Job listing and pagination.

To execute the test suite:

```bash
pytest
```

*(Note: Automated tests run using an in-memory SQLite database and mocked Celery enqueuing, meaning tests run in milliseconds without requiring a live Redis server).*

---

## Troubleshooting Guide

- **Job stays in `pending` status:**
  - Verify that Redis is running (`docker compose up -d redis` or check `redis-cli ping`).
  - Verify that the Celery worker is running in Terminal 2 and connected to the same Redis instance.
- **Windows Celery Error (`PermissionError` or `SpawnPoolWorker`):**
  - Always run Celery on Windows with `--pool=solo`:
    `celery -A app.celery_app worker --loglevel=info --pool=solo`
- **Certificate download returns HTTP 400:**
  - The certificate is either still generating (`pending`), or generation failed (`failed`). Check `GET /certificates/{id}` to view the status and `error_message`.
- **Port 8000 already in use:**
  - Start Uvicorn on an alternate port: `uvicorn app.main:app --port 8080 --reload`

---

