# IdeaVault

> Production-grade, open-source AI image & video generation platform powered by a multi-agent pipeline, hand-rolled data structures, and a modern full-stack architecture — fully local, zero API keys required for generation.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green.svg)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue.svg)](https://docker.com)
[![Tests](https://img.shields.io/badge/Tests-pytest-brightgreen.svg)](#testing)

---

## Table of Contents

- [What is IdeaVault?](#what-is-ideavault)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Multi-Agent Pipeline](#multi-agent-pipeline)
- [DAG Pipeline (DSA)](#dag-pipeline-dsa)
- [Hand-Rolled Data Structures](#hand-rolled-data-structures)
- [Repository Structure](#repository-structure)
- [Tech Stack](#tech-stack)
- [Environment Variables](#environment-variables)
- [Quick Start](#quick-start)
- [Local Development](#local-development)
- [Model Setup](#model-setup)
- [API Reference](#api-reference)
- [Frontend Pages](#frontend-pages)
- [Database Schema](#database-schema)
- [Testing](#testing)
- [Infrastructure](#infrastructure)
- [Security](#security)
- [License](#license)

---

## What is IdeaVault?

IdeaVault turns natural language into **high-quality images and short videos** using a fully local AI pipeline. Users write a prompt in plain English — the system autonomously:

1. **Enhances** the prompt via Ollama (llama3.2) or a rule-based fallback
2. **Selects** the optimal local diffusion model and parameters based on style tags and quality preset
3. **Generates** the media locally via ONNX Runtime / PyTorch diffusers (images) or diffusers text-to-video (videos)
4. **Validates** quality using PIL sharpness heuristics (Laplacian variance)
5. **Serves** the file via FastAPI static endpoints — no cloud storage needed

Everything runs **100% locally**. No external API calls are required for generation.

---
## UI Screenshot

<img width="1508" height="825" alt="Screenshot 2026-06-25 at 12 17 58 AM" src="https://github.com/user-attachments/assets/4069ce13-c845-4e0c-b1db-add222140401" />


## Key Features

| Feature | What it does |
| --- | --- |
| **Multi-Agent AI** | 4-agent pipeline: PromptEnhancer → StyleAgent → Generator → QualityAgent, orchestrated by `GenerationOrchestrator` |
| **DAG Pipeline** | Kahn's topological sort, parallel independent stages via `asyncio.gather` |
| **Custom DSA** | Min-Heap scheduler, LRU Cache, Trie autocomplete, Token Bucket rate limiter, Bloom Filter — all hand-rolled |
| **Local inference** | SDXL-Turbo / SDXL / SD1.5 (image), ModelScope / ZeroScope (video) via HuggingFace diffusers |
| **ONNX acceleration** | CoreML execution provider on Apple M-series; CUDA EP on NVIDIA; CPU EP as fallback |
| **Async first** | FastAPI + async SQLAlchemy + Celery workers with `NullPool` to avoid event-loop cross-contamination |
| **Type-safe** | Pydantic v2 backend schemas, TypeScript strict frontend, Zod form validation |
| **Production infra** | Docker Compose, Nginx reverse proxy, Flower monitoring, structured JSON logging |
| **Real-time UX** | React Query polling, animated DAG pipeline stepper, confetti on completion |

---

## System Architecture

```text
┌────────────────────────────────────────────────────────────────────────────┐
│                              IdeaVault                                   │
│                                                                              │
│  ┌──────────────────────┐        ┌───────────────────────────────────────┐  │
│  │    Next.js Frontend  │        │           FastAPI Backend             │  │
│  │    (port 3000)       │◀──────▶│           (port 8000)                 │  │
│  │                      │  REST  │                                       │  │
│  │  /               Home│        │  POST /api/v1/generate/image          │  │
│  │  /login      Auth UI │        │  POST /api/v1/generate/video          │  │
│  │  /generate   Studio  │        │  GET  /api/v1/jobs/{id}               │  │
│  │  /gallery    Gallery │        │  GET  /api/v1/generate/autocomplete   │  │
│  └──────────────────────┘        │  POST /api/v1/auth/register           │  │
│                                  │  POST /api/v1/auth/token              │  │
│  ┌──────────────────────┐        └──────────────┬────────────────────────┘  │
│  │      Nginx           │                       │ Celery task dispatch      │
│  │   Reverse Proxy      │               ┌───────▼──────────────────────┐    │
│  │   (port 80)          │               │   Redis Broker (db 1)        │    │
│  │  rate 30r/m          │               │   Redis Results (db 2)        │    │
│  └──────────────────────┘               └───────┬──────────────────────┘    │
│                                                  │                           │
│                                  ┌───────────────▼──────────────────────┐   │
│                                  │     Celery Worker(s)                  │   │
│                                  │     queue=generation  concurrency=2   │   │
│                                  │                                       │   │
│                                  │     GenerationOrchestrator            │   │
│                                  │       │                               │   │
│                                  │       ├─ PromptEnhancerAgent          │   │
│                                  │       │    └─ Ollama llama3.2         │   │
│                                  │       │       (rule-based fallback)   │   │
│                                  │       │                               │   │
│                                  │       ├─ StyleAgent                   │   │
│                                  │       │    └─ model catalogue selector │   │
│                                  │       │                               │   │
│                                  │       ├─ Local Media Generation       │   │
│                                  │       │    ├─ ONNX+CoreML (image)     │   │
│                                  │       │    ├─ PyTorch diffusers (img) │   │
│                                  │       │    └─ diffusers t2v (video)   │   │
│                                  │       │                               │   │
│                                  │       └─ QualityAgent                 │   │
│                                  │            └─ PIL Laplacian variance  │   │
│                                  └───────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  PostgreSQL  │  │    Redis     │  │    MinIO     │  │    Flower     │  │
│  │   (port 5432)│  │  (port 6379) │  │  (port 9000) │  │  (port 5555)  │  │
│  │  Users, Jobs │  │ Queue/Cache  │  │  S3 storage  │  │ Task monitor  │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └───────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Multi-Agent Pipeline

All agents extend `BaseAgent` and follow a **Think → Act → Reflect** loop with exponential-backoff retry (max 3 attempts):

```text
BaseAgent.run(context)
  │
  ├─ _think(context)   → build execution plan
  ├─ _act(plan)        → call Ollama / diffusers / PIL
  └─ _reflect(output)  → validate; return False to retry
```

### Agents

| Agent | File | Responsibility |
| --- | --- | --- |
| `GenerationOrchestrator` | `agents/orchestrator.py` | Builds and runs the DAG pipeline; handles quality retries |
| `PromptEnhancerAgent` | `agents/prompt_enhancer.py` | Calls Ollama llama3.2 to produce `enhanced_prompt`, `negative_prompt`, `style_tags`, `aspect_ratio`. Falls back to rule-based enhancement if Ollama is unavailable |
| `StyleAgent` | `agents/style_agent.py` | Selects model and inference parameters from internal catalogues based on style tags, quality preset, and media type |
| `QualityAgent` | `agents/quality_agent.py` | Validates generated files using PIL Laplacian variance (sharpness), minimum dimensions check, and file-size check for videos |

### Pipeline Execution Flow

```text
                   ┌──────────────────┐
        Level 0 →  │  enhance_prompt  │ (Ollama / rule-based)
                   └────────┬─────────┘
                             │         ┌──────────────────┐
                   Level 0 → │         │   select_style   │ (model selector)
                             │         └────────┬─────────┘
                             └────────┬─────────┘
                                      │
                   ┌──────────────────▼─────────────────┐
        Level 1 →  │          generate_media             │
                   │  (ONNX/PyTorch image OR diffusers   │
                   │   text-to-video)                    │
                   └──────────────────┬─────────────────┘
                                      │
                   ┌──────────────────▼─────────────────┐
        Level 2 →  │           quality_check             │
                   │  (PIL sharpness + file existence)   │
                   └─────────────────────────────────────┘
```

`enhance_prompt` and `select_style` run **concurrently** at level 0 (no inter-dependency). `generate_media` waits for both, `quality_check` waits for `generate_media`.

If the quality gate rejects the output, the orchestrator re-runs the full pipeline once (configurable via `MAX_QUALITY_RETRIES`).

---

## DAG Pipeline (DSA)

`backend/app/dsa/pipeline_dag.py` — a generic async DAG executor built from scratch.

```python
pipeline = DAGPipeline()
pipeline.add_node(PipelineNode("enhance_prompt", fn_a, deps=[]))
pipeline.add_node(PipelineNode("select_style",   fn_b, deps=[]))
pipeline.add_node(PipelineNode("generate_media", fn_c, deps=["enhance_prompt", "select_style"]))
pipeline.add_node(PipelineNode("quality_check",  fn_d, deps=["generate_media", "enhance_prompt"]))
result = await pipeline.execute(context)
```

**Internal algorithm:**
1. `_topological_levels()` — Kahn's BFS algorithm; groups nodes by level; detects cycles; O(V + E)
2. `execute()` — iterates levels; calls `asyncio.gather(*tasks)` within each level; passes dependency outputs as kwargs; halts on first error

---

## Hand-Rolled Data Structures

All structures live in `backend/app/dsa/` and are used live in production — no `heapq`, `functools.lru_cache`, or third-party equivalents.

### `MinHeap` — Job Priority Queue

**File:** `dsa/priority_queue.py`
**Used in:** `api/v1/endpoints/generate.py` — `_job_queue`

```text
Time:  push O(log n) | pop O(log n) | peek O(1)
Space: O(n)
```

Thread-safe via `threading.Lock`. `HeapEntry` carries `(priority, timestamp, sequence)` for total ordering — FIFO within the same priority level.

Priority levels (via `JobPriority` enum):
- `CRITICAL = 0` — system retries, admin
- `HIGH = 1` — premium users
- `NORMAL = 2` — standard users
- `LOW = 3` — background / batch

### `LRUCache` — Generation Result Cache

**File:** `dsa/lru_cache.py`
**Used in:** `api/v1/endpoints/generate.py` — `_result_cache` (capacity 512); `dsa/rate_limiter.py` — bucket registry

```text
Internal layout:  head <-> [MRU] ... [LRU] <-> tail
Time:  get O(1) | put O(1) | delete O(1)
Space: O(capacity)
```

Doubly-linked list with sentinel head/tail nodes + `dict[key, node]` hash map. Thread-safe via `threading.RLock`. Evicts LRU on capacity overflow.

### `Trie` — Prompt Autocomplete

**File:** `dsa/trie.py`
**Used in:** `api/v1/endpoints/generate.py` — `_trie`; `GET /api/v1/generate/autocomplete`

```text
Time:  insert O(k) | search O(k) | get_suggestions O(P + N)
       k = key length, P = prefix length, N = subtree node count
```

Case-insensitive. Each terminal node stores `frequency` (incremented on user selection). `get_suggestions(prefix, top_k)` returns top-k completions ranked by descending frequency via `heapq.nlargest`. Thread-safe via `threading.RLock`.

### `TokenBucket` + `RateLimiter` — API Rate Limiting

**File:** `dsa/rate_limiter.py`
**Used in:** `api/v1/endpoints/generate.py` — `_rate_limiter` (capacity=10, refill=1 token/s)

Each user gets a `TokenBucket` (capacity, tokens/sec refill). Tokens are refilled lazily on each `consume()` call. `RateLimiter` is a registry of buckets backed by the LRU cache to bound memory (evicts inactive users). Double-checked locking for thread safety.

### `BloomFilter` — Duplicate Prompt Detection

**File:** `dsa/bloom_filter.py`
**Used in:** `api/v1/endpoints/generate.py` — `_bloom` (capacity=100 000, error_rate=1%)

```text
Time:  add O(k) | contains O(k)   k = num hash functions
Space: O(m)  m ≈ -n·ln(p) / (ln 2)²
```

Bit array stored as `bytearray`. Double-hashing scheme: `h_i = (h1 + i·h2) % m` using MD5 + SHA-256 as base hashes. No false negatives; false-positive rate bounded by configured `error_rate`. Thread-safe via `threading.RLock`.

### `DAGPipeline` — Generation Pipeline

Covered above. Kahn's algorithm for topological sort, `asyncio.gather` for concurrent level execution, `on_level_start` callback for real-time job-step updates.

---

## Repository Structure

```text
ideavault/
│
├── backend/
│   ├── Dockerfile                    # Multi-stage: python:3.11-slim builder + runtime
│   ├── download_models.py            # One-time ONNX export + video model download
│   ├── requirements.txt
│   ├── models/
│   │   ├── onnx/sdxl-turbo/          # Exported ONNX model (run download_models.py)
│   │   └── video/text-to-video-ms-1.7b/  # ModelScope video model
│   ├── tests/
│   │   └── test_dsa.py               # 20+ unit tests for all DSA structures
│   └── app/
│       ├── main.py                   # FastAPI app, lifespan, middleware, static mounts
│       ├── agents/
│       │   ├── base_agent.py         # Abstract Think→Act→Reflect loop, retry, backoff
│       │   ├── orchestrator.py       # GenerationOrchestrator — DAG pipeline driver
│       │   ├── prompt_enhancer.py    # Ollama llama3.2 prompt expansion + rule fallback
│       │   ├── style_agent.py        # Model selector (SDXL-Turbo/SDXL/SD1.5/ModelScope/ZeroScope)
│       │   └── quality_agent.py      # PIL sharpness (Laplacian variance) + size checks
│       ├── api/
│       │   └── v1/
│       │       ├── router.py         # Mounts auth + generate + jobs routers
│       │       └── endpoints/
│       │           ├── auth.py       # POST /register, POST /token, GET /me
│       │           ├── generate.py   # POST /image, POST /video, GET /autocomplete
│       │           └── jobs.py       # GET /{id}, GET /, DELETE /{id}
│       ├── core/
│       │   ├── config.py             # pydantic-settings Settings + get_settings()
│       │   ├── database.py           # async SQLAlchemy engine, Base, get_db
│       │   └── security.py           # bcrypt hash, JWT create/decode, OAuth2 dependency
│       ├── dsa/
│       │   ├── pipeline_dag.py       # DAGPipeline, PipelineNode, PipelineResult
│       │   ├── priority_queue.py     # MinHeap, JobPriority, HeapEntry
│       │   ├── lru_cache.py          # LRUCache (_Node DLL + dict)
│       │   ├── trie.py               # Trie, TrieNode (frequency-ranked autocomplete)
│       │   ├── rate_limiter.py       # TokenBucket, RateLimiter (LRU-backed)
│       │   └── bloom_filter.py       # BloomFilter (double-hash, bytearray bits)
│       ├── models/
│       │   ├── user.py               # User ORM (id, email, username, hashed_password, is_active, is_premium)
│       │   └── job.py                # Job ORM (JobStatus, MediaType, pipeline_result JSONB)
│       ├── schemas/
│       │   ├── auth.py               # RegisterRequest, TokenResponse, UserResponse
│       │   └── generate.py           # GenerateRequest, JobResponse, GenerateResponse, AutocompleteResponse
│       ├── services/
│       │   ├── local_image_service.py  # ONNX+CoreML primary / PyTorch MPS/CUDA fallback
│       │   ├── local_video_service.py  # diffusers DiffusionPipeline, MP4 export
│       │   └── storage_service.py      # MinIO S3-compatible upload (optional)
│       └── workers/
│           ├── celery_app.py         # Celery config (broker=redis/1, backend=redis/2)
│           └── tasks.py              # generate_media_task — runs orchestrator, updates DB, serves file
│
├── frontend/
│   ├── Dockerfile                    # 3-stage: deps / builder / runner (Next.js standalone)
│   ├── package.json
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── src/
│       ├── app/
│       │   ├── layout.tsx            # Root layout, global CSS, metadata
│       │   ├── providers.tsx         # React Query + Zustand providers
│       │   ├── globals.css           # Tailwind layers, custom utilities (glow, orb, glass)
│       │   ├── page.tsx              # Landing / home page
│       │   ├── login/page.tsx        # Login + register UI
│       │   ├── generate/page.tsx     # AI Studio — form sidebar + output canvas + pipeline stepper
│       │   └── gallery/page.tsx      # Media gallery (images + videos grid)
│       ├── components/
│       │   ├── forms/
│       │   │   └── GenerateForm.tsx  # react-hook-form + Zod, media type, quality, duration, style hints
│       │   └── ui/
│       │       ├── JobStatusCard.tsx # Animated pipeline stepper, progress bar, confetti, cancel flow
│       │       └── MediaCard.tsx     # Image / video card for gallery with hover actions
│       ├── hooks/
│       │   └── useGeneration.ts      # useGenerateImage, useGenerateVideo, useJobPoller,
│       │                             #   useJobs, useCancelJob, useAutocomplete, useStudioState
│       └── lib/
│           ├── api.ts                # Axios client, JWT interceptor, authApi, generateApi, jobsApi
│           └── utils.ts             # cn(), formatRelativeTime(), estimatedProgress()
│
├── nginx/
│   └── nginx.conf                   # Reverse proxy, rate limiting (30r/m), security headers
├── docker-compose.yml               # postgres, redis, minio, api, worker (×2), flower, frontend, nginx
├── .env.example                     # All required environment variables with descriptions
└── LICENSE                          # MIT
```

---

## Tech Stack

### Backend

| Layer | Technology | Version |
| --- | --- | --- |
| Web framework | FastAPI + Uvicorn (ASGI) | 0.111 |
| Validation | Pydantic v2 + pydantic-settings | 2.x |
| ORM | SQLAlchemy 2 async + asyncpg | 2.x |
| Task queue | Celery 5 + Redis | 5.x |
| Authentication | JWT (python-jose) + bcrypt | HS256 |
| Database | PostgreSQL 16 | 16 |
| Queue/Cache | Redis 7 | 7 |
| Object storage | MinIO (S3-compatible) | latest |
| Image generation | HuggingFace diffusers (PyTorch) | latest |
| ONNX acceleration | optimum + onnxruntime | latest |
| Video generation | diffusers DiffusionPipeline | latest |
| Prompt enhancement | Ollama llama3.2 (local LLM) | 3.2 |
| Quality check | Pillow + numpy | latest |
| HTTP client | httpx | latest |
| Monitoring | Flower (Celery dashboard) | latest |

### Frontend

| Layer | Technology | Version |
| --- | --- | --- |
| Framework | Next.js 14 (App Router) | 14.2.5 |
| Language | TypeScript strict | 5.5 |
| Styling | Tailwind CSS | 3.4 |
| UI primitives | Radix UI (Dialog, Select, Tooltip…) | 1.x |
| Animation | Framer Motion | 11.x |
| Server state | TanStack React Query | 5.x |
| Client state | Zustand | 4.x |
| Forms | react-hook-form + Zod | 7.x / 3.x |
| HTTP | Axios | 1.x |
| Icons | Lucide React | 0.408 |
| Date utils | date-fns | 3.x |

### Infrastructure

| Component | Technology |
| --- | --- |
| Process manager | `start.sh` (bash, starts all services) |
| CI/CD | GitHub Actions |
| Environment | `.env` via pydantic-settings |

---

## Environment Variables

Copy `.env.example` to `.env`. The defaults work for local development — only change values you need to customise.

```bash
# ── App ──────────────────────────────────────────
APP_ENV=development
SECRET_KEY=your-long-random-secret-key-here   # change before production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440              # 24 hours

# ── Database ──────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://your_user:your_password@localhost:5432/your_db
SYNC_DATABASE_URL=postgresql://your_user:your_password@localhost:5432/your_db

# ── Redis ─────────────────────────────────────────
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# ── Rate Limiting ─────────────────────────────────
RATE_LIMIT_TOKENS=10          # initial tokens per user
RATE_LIMIT_REFILL_RATE=1      # tokens refilled per second
RATE_LIMIT_CAPACITY=20        # max burst size

# ── Cache ─────────────────────────────────────────
LRU_CACHE_CAPACITY=512
BLOOM_FILTER_CAPACITY=100000
BLOOM_FILTER_ERROR_RATE=0.01

# ── Generation ────────────────────────────────────
DEFAULT_IMAGE_MODEL=stabilityai/sdxl-turbo
DEFAULT_VIDEO_MODEL=damo-vilab/text-to-video-ms-1.7b
MAX_CONCURRENT_JOBS=4
JOB_TIMEOUT_SECONDS=300
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 16 running locally (or via `brew services start postgresql@16`)
- Redis running locally (or via `brew services start redis`)
- (Optional) Ollama for prompt enhancement: `ollama run llama3.2`

### 1. Clone and configure

```bash
git clone https://github.com/yourusername/ideavault.git
cd ideavault
cp .env.example .env
# Edit .env — set DATABASE_URL and SECRET_KEY at minimum
```

### 2. Install dependencies

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

### 3. Download models (run once)

```bash
cd ..
python scripts/download_models.py
```

See [Model Setup](#model-setup) for details on what is downloaded and options.

### 4. Start everything

```bash
./start.sh
```

This launches the FastAPI server, Celery worker, and Next.js dev server in one command.

### 5. Open the app

| Service | URL |
| --- | --- |
| Frontend | <http://localhost:3000> |
| API + Swagger | <http://localhost:8000/docs> |
| API ReDoc | <http://localhost:8000/redoc> |

---

## Local Development

The quickest path is `./start.sh` (see [Quick Start](#quick-start)). For running services individually:

### Backend

```bash
cd backend
source .venv/bin/activate

# API server
uvicorn app.main:app --reload --port 8000

# Celery worker (separate terminal) — pool=solo avoids fork issues on macOS/MPS
celery -A app.workers.celery_app worker --loglevel=info --queues=generation --pool=solo --concurrency=1
```

### Frontend

```bash
cd frontend
npm run dev           # http://localhost:3000
npm run type-check    # TypeScript validation
npm run lint          # ESLint
```

### Required services (PostgreSQL + Redis)

Start them with your system's service manager, e.g. on macOS:

```bash
brew services start postgresql@16
brew services start redis
```

Or any other local install — just make sure `DATABASE_URL` and `REDIS_URL` in `.env` point to them.

---

## Model Setup

IdeaVault generates everything locally. No API keys required for inference.

### Image Models (auto-downloaded by diffusers on first run)

| Key | HuggingFace ID | Resolution | Steps | Use case |
| --- | --- | --- | --- | --- |
| `sdxl-turbo` | `stabilityai/sdxl-turbo` | 512×512 | 4 | Fast / draft (default) |
| `sdxl` | `stabilityai/stable-diffusion-xl-base-1.0` | 1024×1024 | 20 | High quality / ultra |
| `sd15` | `runwayml/stable-diffusion-v1-5` | 512×512 | 20 | Lightweight fallback |

**ONNX acceleration (Apple M-series / NVIDIA):**

```bash
python scripts/download_models.py
```

Exports `sdxl-turbo` to `backend/models/onnx/sdxl-turbo/` using `optimum`. On Apple M-series the `CoreMLExecutionProvider` gives 2–3× speedup over PyTorch MPS. Falls back gracefully to PyTorch if the ONNX model is absent (no setup required for PyTorch path).

### Video Models

| Key | HuggingFace ID | Frames | FPS | Resolution | Use case |
| --- | --- | --- | --- | --- | --- |
| `modelscope` | `damo-vilab/text-to-video-ms-1.7b` | up to 24 | 8 | 256×256 | Standard (default) |
| `zeroscope` | `cerspense/zeroscope_v2_576w` | up to 36 | 8 | 576×320 | Ultra / cinematic |

Video models download to `~/.cache/huggingface/` on first generation, or from `backend/models/video/` if pre-downloaded.

**Note on MPS:** Video diffusion models produce `NaN`/black frames with `float16` on MPS. The service automatically uses `float32` on MPS/CPU and `float16` only on CUDA.

### Prompt Enhancement (Ollama)

```bash
# Install Ollama: https://ollama.com
ollama run llama3.2
```

If Ollama is unavailable, `PromptEnhancerAgent` silently falls back to rule-based prompt expansion (appends quality tags, infers aspect ratio).

---

## API Reference

All endpoints require a `Bearer` JWT token (except `register` and `token`). Obtain a token via `POST /api/v1/auth/token`.

### Authentication

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/api/v1/auth/register` | Create account (`email`, `username`, `password`) |
| `POST` | `/api/v1/auth/token` | Login — returns JWT (`username` = email) |
| `GET` | `/api/v1/auth/me` | Get current user profile |

### Generation

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/api/v1/generate/image` | Queue image generation job → `202 Accepted` |
| `POST` | `/api/v1/generate/video` | Queue video generation job → `202 Accepted` |
| `GET` | `/api/v1/generate/autocomplete?prefix=<str>&limit=10` | Trie-based prompt suggestions |

**Request body (image / video):**

```json
{
  "prompt": "a neon city at night, reflections on wet pavement",
  "media_type": "image",
  "quality_preset": "standard",
  "style_hints": ["cinematic", "photorealistic"],
  "priority": 2,
  "duration_seconds": 4
}
```

| Field | Type | Values | Default |
| --- | --- | --- | --- |
| `prompt` | string | 3–2000 chars | required |
| `media_type` | enum | `image` \| `video` | `image` |
| `quality_preset` | enum | `draft` \| `standard` \| `ultra` | `standard` |
| `style_hints` | string[] | max 10 items | `[]` |
| `priority` | int | `0`(CRITICAL) – `3`(LOW) | `2` (NORMAL) |
| `duration_seconds` | int | `2`–`8` (video only) | `4` |

**Response (`202`):**

```json
{
  "job_id": "uuid",
  "status": "queued",
  "message": "job queued successfully",
  "estimated_seconds": 30
}
```

### Jobs

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/api/v1/jobs/` | List user's jobs (paginated: `limit`, `offset`) |
| `GET` | `/api/v1/jobs/{job_id}` | Get job status and result |
| `DELETE` | `/api/v1/jobs/{job_id}` | Cancel job (only `queued` or `processing`) |

**Job status values:** `queued` → `processing` → `completed` \| `failed` \| `cancelled`

**Completed job response includes:**

```json
{
  "job_id": "uuid",
  "status": "completed",
  "output_url": "/media/images/abc123.png",
  "enhanced_prompt": "...",
  "model_id": "stabilityai/sdxl-turbo",
  "quality_score": 7.4,
  "current_step": null
}
```

### Health

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/health` | `{"status": "ok", "version": "1.0.0", "env": "..."}` |
| `GET` | `/` | API name and doc links |

### Static Media

Generated files are served via FastAPI `StaticFiles` mounts:

| URL Pattern | Content |
| --- | --- |
| `/media/images/<filename>.png` | Generated images |
| `/media/videos/<filename>.mp4` | Generated videos |

---

## Frontend Pages

### `/` — Home / Landing

Minimal landing page with CTA buttons to Studio and Gallery.

### `/login` — Authentication

Login and registration form. On success, stores JWT in `localStorage` as `nc_token`. Redirects to `/generate`.

### `/generate` — AI Studio

The main creation interface. Split-panel layout:

- **Left sidebar (420px):** `GenerateForm` — media type toggle, prompt textarea with Trie autocomplete dropdown, quality preset selector, video duration picker (video only), style hints tag input
- **Right canvas:** `JobStatusCard` — animated progress bar with shimmer sweep, confetti burst on completion, inline image/video display with download button, cancel flow with two-step confirmation
- **Top nav:** Logo, Gallery link, Logout

**Features:**
- Debounced Trie autocomplete (250 ms) triggered when prompt ≥ 2 chars
- React Query polls job status every 2 s (processing) / 3 s (queued)
- `beforeunload` keepalive fetch cancels active jobs if user closes tab
- Auth guard redirects unauthenticated users to `/login`

### `/gallery` — Media Gallery

Displays all completed jobs. Separate sections for images and videos. Masonry-style grid (`grid-cols-2` up to `xl:grid-cols-5`). `MediaCard` shows prompt, model, quality score on hover.

---

## Database Schema

### `users` table

| Column | Type | Notes |
| --- | --- | --- |
| `id` | UUID PK | auto-generated |
| `email` | VARCHAR(255) UNIQUE | indexed |
| `username` | VARCHAR(64) UNIQUE | indexed |
| `hashed_password` | VARCHAR(255) | bcrypt |
| `is_active` | BOOLEAN | default true |
| `is_premium` | BOOLEAN | default false |
| `created_at` | TIMESTAMPTZ | auto |
| `updated_at` | TIMESTAMPTZ | auto-updated |

### `jobs` table

| Column | Type | Notes |
| --- | --- | --- |
| `id` | UUID PK | auto-generated |
| `user_id` | UUID FK → users | CASCADE DELETE, indexed |
| `status` | VARCHAR(32) | queued / processing / completed / failed / cancelled; indexed |
| `media_type` | VARCHAR(16) | image / video |
| `priority` | INTEGER | 0–3 (matches `JobPriority`) |
| `raw_prompt` | TEXT | user's original prompt |
| `quality_preset` | VARCHAR(16) | draft / standard / ultra |
| `style_hints` | JSONB | list of style tag strings |
| `output_url` | TEXT | path to generated file `/media/...` |
| `enhanced_prompt` | TEXT | Ollama-enhanced prompt |
| `model_id` | VARCHAR(128) | HuggingFace model ID used |
| `quality_score` | FLOAT | 0–10 (Laplacian variance score) |
| `error_message` | TEXT | set on failure |
| `celery_task_id` | VARCHAR(64) | Celery task ID |
| `current_step` | VARCHAR(128) | comma-separated active pipeline step names |
| `duration_seconds` | INTEGER | requested video duration |
| `pipeline_result` | JSONB | `{"execution_order": [...]}` |
| `created_at` | TIMESTAMPTZ | auto |
| `started_at` | TIMESTAMPTZ | when Celery picks up task |
| `completed_at` | TIMESTAMPTZ | on terminal state |

Tables are auto-created on startup via `Base.metadata.create_all` in the FastAPI lifespan context.

---

## Testing

Tests are in `backend/tests/test_dsa.py`. They cover all 6 DSA structures with unit tests, concurrency tests, and edge cases.

```bash
cd backend
source .venv/bin/activate
python -m pytest tests/ -v
```

Test coverage includes:

| Structure | Tests |
| --- | --- |
| `MinHeap` | Priority ordering, FIFO within priority, empty pop, thread safety (4 concurrent producers × 100 items) |
| `LRUCache` | Get/put, LRU eviction, position refresh on update, capacity=1, delete |
| `Trie` | Insert/search, frequency-ranked autocomplete, prefix matching, delete, increment |
| `TokenBucket` / `RateLimiter` | Burst consume, refill over time, per-user isolation |
| `BloomFilter` | No false negatives, false-positive rate within bound, saturation monotonicity |
| `DAGPipeline` | Linear pipeline, parallel independent nodes (timing test), cycle detection, node failure propagation |

**Frontend type check:**

```bash
cd frontend
npm run type-check
```

---

## Infrastructure

### Running Services

| Service | Port | Notes |
| --- | --- | --- |
| PostgreSQL | 5432 | User accounts, job history |
| Redis | 6379 | Celery broker (db 1) + result backend (db 2) + cache (db 0) |
| FastAPI | 8000 | REST API + Swagger docs at `/docs` |
| Celery worker | — | `pool=solo`, `concurrency=1` — avoids MPS fork issues on macOS |
| Next.js | 3000 | Frontend dev server |

Start all at once with `./start.sh` from the project root.

### Celery Configuration

- **Broker:** `redis://redis:6379/1`
- **Result backend:** `redis://redis:6379/2`
- **Serializer:** JSON
- **Queue:** `generation`
- **Prefetch:** `worker_prefetch_multiplier=1` — fair dispatch for long-running GPU tasks
- **Timeouts:** `task_soft_time_limit` = `JOB_TIMEOUT_SECONDS`, hard limit +60 s
- **Retry:** `max_retries=1`, 10 s delay
- **Acks late:** Yes — task re-queued if worker crashes mid-flight

### Celery Worker Task Flow

```text
generate_media_task(job_id)
  │
  ├─ Mark job PROCESSING, record started_at
  │
  ├─ Build context from job row
  │
  ├─ GenerationOrchestrator.run(context, on_step=_on_step)
  │     on_step → writes current_step column for live frontend polling
  │
  ├─ Convert local file path → /media/{images|videos}/{filename}
  │
  └─ Mark job COMPLETED / FAILED, write output_url, enhanced_prompt,
     model_id, quality_score, pipeline_result
```

`NullPool` is used for the worker's async engine because each `asyncio.run()` call creates a new event loop — pooled connections bound to the previous loop cause "Future attached to different loop" errors.

---

## Security

| Concern | Mitigation |
| --- | --- |
| Authentication | JWT (HS256) with configurable expiry; `SECRET_KEY` from env |
| Password storage | bcrypt with input truncated to 72 bytes (bcrypt max) |
| Authorization | All job endpoints verify `user_id` matches JWT `sub` claim |
| Rate limiting | Token Bucket per user (10 tokens, 1/s refill) |
| CORS | Restricted to `localhost:3000` in development; empty in production |
| Secrets | Never hardcoded; loaded from `.env`; `.env` is git-ignored |
| SQL injection | SQLAlchemy ORM with parameterized queries throughout |
| Error leakage | Global exception handler returns generic `"internal server error"` |

---

## License

MIT — see [LICENSE](LICENSE)
