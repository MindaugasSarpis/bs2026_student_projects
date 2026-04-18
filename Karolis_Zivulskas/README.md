# RepOps

**Reputation Operations** — a social media monitoring platform that collects posts and comments from Facebook pages/groups, analyses them for hate speech and harmful keywords, and surfaces flagged content through an admin UI and Grafana dashboards.

---

## How it works

```
Facebook pages
      │
      ▼
  [Collector]  ── Apify actors ──►  Posts + Comments
      │                               saved to PostgreSQL
      ▼
  [Analyzer]  ── Keyword matching ──►  AnalysisResult
      │            (Aho-Corasick)       score + label
      ▼
  [Profile Scorer]  ──────────────►  Per-author risk score
      │
      ▼
  [Admin UI / Grafana]  ──────────►  Review + monitoring
```

1. **Celery Beat** triggers `collect_all_active_targets` every 15 minutes.
2. Each target fans out to a `collect_target` task, which calls Apify to scrape posts and comments.
3. Every new post is immediately enqueued for `analyze_post`.
4. The analyzer runs keyword matching (plain + regex) against all active keyword sets and assigns a score and label.
5. Posts scoring above `HATE_SPEECH_THRESHOLD` are marked **FLAGGED**; others are marked **ANALYZED**.
6. After each post is analysed, the author's profile risk score is recalculated.
7. Operators review flagged content in the admin UI and clear false positives.

---

## Directory structure

```
repops/                          ← project root
├── Dockerfile                   ← single image for api, worker, beat
├── docker-compose.yml           ← full stack (app + infra)
├── pyproject.toml               ← dependencies and tool config
├── .env.example                 ← all supported environment variables
│
├── migrations/                  ← Alembic database migrations
│   └── versions/
│       ├── 2d9834b3b591_initial_schema.py
│       └── eddd6eeac233_drop_ml_columns_from_analysis_results.py
│
├── tests/
│   ├── conftest.py              ← pytest fixtures (in-memory SQLite DB, test client)
│   ├── unit/
│   │   ├── test_keyword_matcher.py
│   │   ├── test_profile_scorer.py
│   │   └── test_rate_limiter.py
│   └── integration/
│       ├── test_api_keywords.py
│       └── test_api_targets.py
│
├── infra/
│   ├── grafana/
│   │   ├── dashboards/
│   │   │   ├── repops_overview.json   ← throughput, queue depth, worker health
│   │   │   └── repops_content.json    ← per-post content and profile risk table
│   │   └── provisioning/             ← auto-loaded datasources and dashboard paths
│   ├── prometheus/
│   │   └── prometheus.yml            ← scrape config (api :9091, worker :9092, flower :5555)
│   ├── promtail/
│   │   └── config.yaml               ← ships api.log + worker.log to Loki
│   └── terraform/                    ← AWS EC2 deployment (optional)
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
│
└── repops/                      ← Python package
    ├── settings.py
    ├── db.py
    ├── models/
    ├── collector/
    ├── analyzer/
    ├── api/
    ├── workers/
    └── observability/
```

---

## Package: `repops/`

### `settings.py`

Pydantic `BaseSettings` — reads all configuration from environment variables or a `.env` file. A single `settings` singleton is imported by the rest of the codebase.

Key fields:

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | local postgres | SQLAlchemy connection string |
| `REDIS_URL` | local redis | Celery broker and result backend |
| `APIFY_TOKEN` | *(required)* | Apify API key for scraping |
| `SCRAPER_MAX_POSTS` | `5` | Posts fetched per target per collection run |
| `SCRAPER_MAX_COMMENTS` | `50` | Comments fetched across those posts |
| `HATE_SPEECH_THRESHOLD` | `0.6` | Score at or above which a post is flagged |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | `repops` / `changeme` | HTTP Basic auth for the admin UI |
| `PROMETHEUS_PORT` | `9091` | Port the API exposes `/metrics` on |

---

### `db.py`

Creates the SQLAlchemy connection pool and exposes `get_session()` — a context manager used by every Celery task that reads or writes the database. On error it rolls back automatically.

---

### `models/`

SQLAlchemy ORM table definitions. Each file maps to one database table.

| File | Table | Purpose |
|---|---|---|
| `target.py` | `targets` | Facebook page or group being monitored (facebook_id, scan interval, active flag) |
| `post.py` | `posts` | A single collected post or comment; tracks `status` through `RAW → ANALYZED/FLAGGED → CLEARED` |
| `profile.py` | `profiles` | Facebook user whose content was collected; stores aggregated `risk_score` |
| `analysis_result.py` | `analysis_results` | Result of one analysis run on a post: matched keywords, severity, overall score and label |
| `keyword_set.py` | `keyword_sets` + `keyword_entries` | Named collections of keyword patterns, each with a severity level (1–3) and an optional regex flag |

#### Post status lifecycle

```
RAW  ──► ANALYZED   (score < threshold — no immediate concern)
     ──► FLAGGED    (score ≥ threshold — awaiting operator review)
                └──► CLEARED  (operator reviewed, false positive)
```

---

### `collector/`

Responsible for fetching content from Facebook via Apify.

#### `apify_scraper.py` — `ApifyScraper.scrape_page()`

Two-actor workflow per collection run:

1. **`facebook-posts-scraper`** (`KoJrdxJCTtpon81KY`) — given a page URL and `resultsLimit`, returns recent post objects with text, URL, reaction/share/comment counts.
2. **`facebook-comments-scraper`** (`us5srxAYnsrkgUv2v`) — given the list of post URLs from step 1, returns all comments up to `maxComments`.

Both calls are async: `_start_run()` fires the actor, `_wait_for_run()` polls every 5 seconds until success or failure, then `_get_items()` downloads the result dataset. Posts and comments are normalised into `ScrapedPost` dataclasses and returned together.

#### `tasks.py` — `collect_target()`

Celery task. Calls `scrape_page()`, then `_persist_posts()` which inserts only posts whose `facebook_id` is not already in the database (deduplication). For each new post it also upserts the author `Profile`. After committing, it enqueues an `analyze_post` task for every new post.

#### `rate_limiter.py`

Token-bucket rate limiter (`RateLimiter`) used by `scrape_page()` to avoid hammering the Apify API. Configured at one request per second by default.

#### `types.py`

`ScrapedPost` dataclass — the common transfer object between the scraper and the persistence layer.

---

### `analyzer/`

#### `keyword_matcher.py`

Two matching strategies:

- **`build_automaton()` / `match_text()`** — builds an [Aho-Corasick](https://en.wikipedia.org/wiki/Aho%E2%80%93Corasick_algorithm) automaton from all plain keyword patterns and runs it against the post text in O(n) time. This is the primary path for large keyword sets.
- **`match_text_regex()`** — word-boundary regex fallback for patterns that need exact-word matching (`\bterm\b`). Used when a `KeywordEntry` has `is_regex=True`.

`KeywordMatch` dataclass holds the matched pattern, its position in the text, and its severity (1–3).

`top_severity()` returns the highest severity across all matches for a post.

#### `tasks.py` — `analyze_post()`

Main analysis pipeline per post:

1. Loads all active keyword entries from the database.
2. Builds the automaton and runs both plain and regex matchers against the post content.
3. Assigns an `overall_score` based on the top matched severity (`low=0.35`, `medium=0.65`, `high=0.95`).
4. Labels the result as `HATE_SPEECH` (severity 3), `KEYWORD_MATCH` (severity 1–2), or `CLEAN`.
5. Saves an `AnalysisResult` row and updates the post status.
6. Stamps `last_matched_at` on every keyword entry that fired.
7. Enqueues `recalculate_profile_task` for the post's author.

Also defines `requeue_raw_posts()` (safety net — re-queues any posts stuck in `RAW` status, runs every 5 minutes) and `recalculate_all_profile_scores()` (hourly batch refresh of all profile scores).

#### `profile_scorer.py` — `compute_risk_score()`

Produces a 0–1 risk score for a Facebook profile from four signals:

| Weight | Signal | Description |
|---|---|---|
| 40% | `flag_rate` | Fraction of the author's posts that were flagged, dampened by a **confidence factor** (`total / (total + 5)`) so a single bad post out of one total does not produce a 100% flag rate |
| 35% | `avg_hate_score` | Mean `overall_score` across the author's flagged posts |
| 15% | `severity_signal` | Highest keyword severity ever seen (`top / 3.0`) |
| 10% | `volume_bonus` | `log(flagged_posts + 1) / log(101)` — rewards repeat offenders over one-off matches |

`recalculate_profile()` queries the database for all stats and persists the new score back to the `profiles` table.

---

### `api/`

FastAPI application. On startup it calls `configure_logging()` and `start_metrics_server()`.

| Router | Prefix | Purpose |
|---|---|---|
| `admin.py` | `/admin` | Browser-facing HTML UI (Jinja2 templates); HTTP Basic auth required |
| `targets.py` | `/api/v1/targets` | REST CRUD for monitored targets |
| `keywords.py` | `/api/v1/keywords` | REST CRUD for keyword sets and entries |
| `results.py` | `/api/v1/results` | REST read access to analysis results; supports reviewer notes |

The admin UI has three pages:
- **Targets** — add/remove/toggle Facebook pages and trigger manual collection.
- **Flagged** — scrollable table of all non-clean posts with scores, matched keywords, and a "Clear" button.
- **Keywords** — manage keyword sets and individual patterns (plain or regex, severity 1–3).

---

### `workers/`

#### `app.py`

Celery application with Redis as broker and result backend. Defines two queues: `collection` (scraping tasks) and `analysis` (analysis + scoring tasks).

#### `schedules.py`

Celery Beat periodic schedule:

| Task | Schedule | Purpose |
|---|---|---|
| `collect_all_active_targets` | every 15 min | Fan-out: enqueue one `collect_target` per active target |
| `requeue_raw_posts` | every 5 min | Safety net for posts stuck in RAW state |
| `recalculate_all_profile_scores` | hourly | Refresh all profile risk scores |
| `update_queue_depth_metric` | every minute | Read Redis queue lengths and push to Prometheus |

#### `tasks.py`

Contains `update_queue_depth_metric()` — connects to Redis, calls `LLEN` on each queue name, and sets the `repops_queue_depth` Prometheus gauge. This is what populates the "Celery Queue Depth" Grafana panel.

---

### `observability/`

#### `metrics.py`

Defines all Prometheus metrics used across the codebase:

| Metric | Type | Description |
|---|---|---|
| `repops_posts_collected_total` | Counter | Posts collected, labelled by `target_id` and `post_type` |
| `repops_posts_analyzed_total` | Counter | Posts that completed analysis |
| `repops_posts_flagged_total` | Counter | Posts flagged, labelled by severity |
| `repops_keyword_matches_total` | Counter | Total keyword match events |
| `repops_keyword_hits_total` | Counter | Hits per individual pattern |
| `repops_collection_errors_total` | Counter | Scraping errors by type |
| `repops_queue_depth` | Gauge | Current task queue depth per queue |
| `repops_analysis_duration_seconds` | Histogram | Time spent per analysis task |
| `repops_collection_duration_seconds` | Histogram | Time spent per collection run |

`start_metrics_server()` handles both single-process (API) and multi-process (Celery worker, via `PROMETHEUS_MULTIPROC_DIR`) modes.

#### `logging.py`

Configures [structlog](https://www.structlog.org/) once at startup. In development, logs are rendered to the console with colour. In production (`ENVIRONMENT=production`) both console and file output are JSON, so Promtail can parse and ship them to Loki. The log file path is set via `LOG_FILE` (in Docker: `/logs/api.log` and `/logs/worker.log`).

---

## Infrastructure

### Docker Compose services

| Service | Image | Port | Role |
|---|---|---|---|
| `postgres` | postgres:16-alpine | 5432 | Primary database |
| `redis` | redis:7-alpine | 6379 | Celery broker |
| `api` | repops:latest | 8000, 9091 | FastAPI app + Prometheus metrics |
| `worker` | repops:latest | 9092 | Celery worker |
| `beat` | repops:latest | — | Celery Beat scheduler |
| `flower` | mher/flower:2.0 | 5555 | Celery task monitor UI |
| `prometheus` | prom/prometheus | 9090 | Metrics scraping and storage |
| `loki` | grafana/loki | 3100 | Log aggregation |
| `promtail` | grafana/promtail | — | Log shipping (reads `/logs/*.log`) |
| `grafana` | grafana/grafana | 3000 | Dashboards |

### Grafana dashboards

- **RepOps — Platform Overview** (`repops_overview.json`) — posts collected/analyzed/flagged (24h stats and timeseries), queue depth per queue, Celery task success/failure rates, worker online status, application logs.
- **RepOps — Content** (`repops_content.json`) — per-post content browser with keyword match counts and scores; profile risk score table.

---

## Getting started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) installed and running
- `APIFY_TOKEN` and `ADMIN_PASSWORD` provided separately

### 1. Start the stack

Open `.env` and fill in `APIFY_TOKEN` and `ADMIN_PASSWORD` (provided separately), then:

```bash
# Build the image and start all services (postgres, redis, api, worker, beat, flower, prometheus, loki, promtail, grafana)
docker compose up -d --build

# Wait for the API to be healthy, then create all database tables
docker compose exec api alembic upgrade head
```

| Service | URL | Credentials |
|---|---|---|
| Admin UI | http://localhost:8000/admin | see `.env` |
| API docs | http://localhost:8000/docs | — |
| Grafana | http://localhost:3000 | admin / repops |
| Flower | http://localhost:5555 | — |

### 2. Add keywords

Open Admin UI → **Keywords**, create a keyword set, and add patterns with a severity level (1=low, 2=medium, 3=high). Without keywords the analyzer produces no matches and nothing gets flagged.

### 3. Add a target

Open Admin UI → **Targets**, add a Facebook page ID (the part after `facebook.com/`), and click **Collect** to trigger an immediate scrape. Automatic collection runs every 15 minutes.

### 4. Review flagged content

Posts scoring at or above `HATE_SPEECH_THRESHOLD` (default `0.6`) appear in Admin UI → **Flagged**. Use the ✓ Clear button to dismiss false positives.

---

## Cloud deployment (AWS EC2)

The `infra/terraform/` directory provisions the full AWS infrastructure — VPC, subnet, security group, EC2 instance (Ubuntu 22.04), and an Elastic IP so the address survives restarts.

### Provision infrastructure

```bash
cd infra/terraform
terraform init -backend-config=backend.tfvars
terraform apply
```

Terraform outputs the instance IP and ready-to-use URLs:

```
public_ip    = 54.74.132.233
api_url      = http://54.74.132.233:8000
grafana_url  = http://54.74.132.233:3000
flower_url   = http://54.74.132.233:5555
ssh_command  = ssh ubuntu@54.74.132.233
```

### Deploy application

```bash
ssh ubuntu@54.74.132.233

git clone <repo-url>
cd repops/Karolis_Zivulskas

# Add APIFY_TOKEN to .env
nano .env

docker compose up -d --build
docker compose exec api alembic upgrade head
```

The live deployment is accessible at **http://54.74.132.233:8000/admin** (admin / repops).
