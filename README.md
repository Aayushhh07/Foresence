<p align="center">
  <img src="https://img.shields.io/badge/Platform-Illegal%20Deforestation%20Monitoring-2d6a4f?style=for-the-badge" alt="Platform" />
</p>

<h1 align="center">Foresense</h1>

<p align="center">
  <strong>Satellite-powered forest monitoring with NDVI change detection, real-time alerts, and an operations dashboard.</strong>
</p>

<p align="center">
  <a href="#features">Features</a> ·
  <a href="#architecture">Architecture</a> ·
  <a href="#api-reference">API</a> ·
  <a href="#quick-start">Quick Start</a> ·
  <a href="#configuration">Configuration</a> ·
  <a href="#deployment">Deployment</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Frontend-React%2018-61DAFB?style=flat-square&logo=react" alt="React" />
  <img src="https://img.shields.io/badge/Database-MongoDB-47A248?style=flat-square&logo=mongodb" alt="MongoDB" />
  <img src="https://img.shields.io/badge/Cache-Redis-DC382D?style=flat-square&logo=redis" alt="Redis" />
  <img src="https://img.shields.io/badge/Satellite-Sentinel--2-0099CC?style=flat-square" alt="Sentinel-2" />
  <img src="https://img.shields.io/badge/License-MIT-blue?style=flat-square" alt="MIT" />
</p>

---

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [Features](#features)
- [Architecture](#architecture)
- [Scan Pipeline](#scan-pipeline)
- [API Flow](#api-flow)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [API Reference](#api-reference)
- [WebSocket Events](#websocket-events)
- [Database Schema](#database-schema)
- [Frontend Application](#frontend-application)
- [Detection Logic](#detection-logic)
- [Configuration](#configuration)
- [Quick Start](#quick-start)
- [Demo Mode](#demo-mode)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

**Foresense** (repository folder: `Foresence`) is a full-stack web platform for monitoring forest areas using **Sentinel-2** satellite imagery. Rangers and analysts draw **monitoring zones** on an interactive map; the backend automatically ingests imagery, computes vegetation indices, compares snapshots over time, and raises **deforestation alerts** when thresholds are exceeded.

| Aspect | Description |
|--------|-------------|
| **Problem** | Illegal deforestation is hard to detect in remote areas with ground patrols alone. |
| **Approach** | Periodic satellite scans + **NDVI/EVI** time-series + rule-based change detection. |
| **Delivery** | REST API, WebSocket push, email (SendGrid), optional webhooks, React dashboard. |

> **Transparency:** Detection is **remote-sensing analytics** (thresholds and vegetation indices), not a trained deep-learning model. There is no user image upload flow—the system pulls imagery from public satellite catalogs.

---

## How It Works

1. Define a **GeoJSON polygon** around a forest area (draw on map or use predefined zones).
2. Backend **downloads Sentinel-2** bands (Blue, Red, NIR) via **Element84 STAC** (primary) or **Copernicus Data Space** (fallback).
3. **Rasterio** clips rasters to the zone; **NDVI** and **EVI** are computed per pixel.
4. Each scan stores a **snapshot** in MongoDB (timeseries).
5. **Change detection** compares the current snapshot to the previous one.
6. If **confidence** and **NDVI drop** exceed zone thresholds → **alert** (DB + WebSocket + email + webhook).
7. Operators review alerts on the **Alert Center**, acknowledge, and resolve incidents.

```mermaid
flowchart LR
  A[Draw zone on map] --> B[Zone saved to MongoDB]
  B --> C[Scheduler / manual scan]
  C --> D[Sentinel-2 bands]
  D --> E[NDVI / EVI + snapshot]
  E --> F{Change vs previous?}
  F -->|Yes| G[Alert + notify]
  F -->|No| H[Update health score]
  G --> I[Dashboard + WebSocket]
  H --> I
```

---

## Features

### Monitoring & geospatial

- Interactive **Leaflet** map with zone polygons colored by health (green / yellow / red).
- **Polygon drawing** (Leaflet Draw) to create monitoring zones.
- **Geodesic area** calculation (hectares) per zone.
- **Satellite pre-check** API before zone creation (`/api/health/satellite-check`).
- **Manual scan** per zone (`POST /api/zones/{id}/scan`).
- **Scheduled scans** every 12 hours (configurable) for all active zones.

### Detection & alerts

- **NDVI** and **EVI** computation from Sentinel-2 L2A bands.
- **Change maps** (loss / gain visualization) stored on Cloudflare R2 or local `/static`.
- **Severity levels:** low, medium, high, critical (from NDVI delta magnitude).
- **Per-zone thresholds:** NDVI drop and confidence.
- **Zone health score** (0–100) and status (`healthy` / `warning` / `critical`).

### Notifications & real-time

- **WebSocket** (`/ws/alerts`) for live alerts, health updates, and scan completion.
- **SendGrid** HTML email alerts to configured addresses.
- **Webhook POST** per zone (optional integration URL).

### Operations UI

- **Map dashboard** — zones, popups, scan now.
- **Alert Center** — filter by severity, status, zone; acknowledge / resolve.
- **Analytics** — NDVI trend line chart and change-area bar chart (Recharts).
- **Settings** — edit thresholds, emails, webhooks, activate/deactivate zones.

### Developer & ops

- OpenAPI docs at `/docs` and `/redoc`.
- **Demo seed** endpoint for testing without satellite credentials.
- **Health endpoint** — MongoDB, Redis, scheduler status.
- **Docker** + **Render** blueprint for backend deployment.

---

## Architecture

### System context

```mermaid
flowchart TB
  subgraph Client["Browser (React + Vite)"]
    UI[Dashboard UI]
    WSClient[WebSocket Client]
  end

  subgraph API["FastAPI Backend"]
    REST[REST /api/*]
    WSS[WebSocket /ws/alerts]
    SCH[APScheduler]
    PIPE[Scan Pipeline]
  end

  subgraph Persistence["Data Layer"]
    MONGO[(MongoDB)]
    REDIS[(Redis / memory locks)]
    R2[(R2 or /static)]
  end

  subgraph External["External Services"]
    STAC[Element84 STAC]
    COP[Copernicus CDSE]
    SG[SendGrid]
  end

  UI --> REST
  WSClient --> WSS
  REST --> MONGO
  SCH --> PIPE
  PIPE --> STAC
  PIPE --> COP
  PIPE --> MONGO
  PIPE --> R2
  PIPE --> WSS
  PIPE --> REDIS
  PIPE --> SG
```

### Backend layers

```mermaid
flowchart TB
  REQ[HTTP / WebSocket Request]
  ROUTE[api/routes/*.py]
  SVC[services/*.py]
  CORE[core/database · redis · config]
  DB[(MongoDB)]

  REQ --> ROUTE
  ROUTE --> SVC
  SVC --> CORE
  CORE --> DB
  SVC --> DB
```

| Layer | Responsibility |
|-------|----------------|
| **Routes** | Validation (Pydantic), HTTP/WebSocket handlers, standard `{ success, data, message }` envelope |
| **Services** | Satellite fetch, NDVI, change detection, alerts, storage, email |
| **Scheduler** | `jobs.py` — orchestrates full scan per zone |
| **Core** | Config, Motor DB client, Redis locks |

---

## Scan Pipeline

The core processing path runs on schedule, on manual trigger, or during historical zone seeding.

```mermaid
sequenceDiagram
  participant S as Scheduler / API
  participant J as jobs.py
  participant L as Redis Lock
  participant Sat as sentinel_service
  participant ND as ndvi_service
  participant CD as change_detection
  participant A as alert_service
  participant DB as MongoDB
  participant WS as WebSocket

  S->>J: scan_single_zone(zone_id)
  J->>L: acquire_zone_lock
  J->>Sat: fetch_sentinel_bands (STAC → Copernicus)
  Sat-->>J: B02, B04, B08 paths
  J->>ND: compute_ndvi_for_zone
  ND-->>J: NDVI/EVI stats + PNG URL
  J->>DB: insert ndvi_snapshots
  J->>CD: detect_change vs previous
  CD-->>J: delta, confidence, change map
  alt thresholds met
    J->>A: create_alert_if_triggered
    A->>DB: insert alert
    A->>WS: broadcast alert
    A->>A: SendGrid + webhook
  end
  J->>WS: scan_complete
  J->>L: release_zone_lock
```

### Historical baseline (new zones)

When a zone is created, a **two-pass historical seed** runs in the background:

| Pass | Date window | Purpose |
|------|-------------|---------|
| 1 | 30 → 15 days ago | Baseline snapshot |
| 2 | 15 days ago → now | Comparison snapshot + possible first alert |

### Satellite data sources

| Priority | Source | Notes |
|----------|--------|-------|
| **Primary** | Element84 STAC | Public catalog; windowed COG downloads; no credentials |
| **Fallback** | Copernicus Data Space | OAuth + OData; full product ZIP; requires `COPERNICUS_*` credentials |

---

## API Flow

```mermaid
flowchart TB
  subgraph Zones
    Z1[POST /api/zones] --> Z2[Background historical seed]
    Z3[POST /api/zones/id/scan] --> Z4[scan_single_zone]
  end

  subgraph Alerts
    A1[GET /api/alerts] --> A2[Filter + paginate]
    A3[PUT /api/alerts/id/status] --> A4[acknowledged / resolved]
  end

  subgraph Health
    H1[GET /api/health] --> H2[DB + Redis + scheduler]
    H3[POST /api/health/satellite-check] --> H4[STAC / Copernicus probe]
  end

  subgraph Realtime
    W1[WS /ws/alerts] --> W2[broadcast on alert / health / scan]
  end
```

All REST responses use this envelope:

```json
{
  "success": true,
  "data": { },
  "message": "Human-readable description"
}
```

Errors return FastAPI `detail` (frontend Axios interceptor surfaces this).

---

## Tech Stack

### Backend

| Technology | Role |
|------------|------|
| FastAPI | REST API + WebSocket |
| Uvicorn | ASGI server |
| Motor | Async MongoDB |
| APScheduler | Interval + one-shot scan jobs |
| Rasterio / NumPy / Shapely / PyProj | Geospatial processing |
| pystac-client | STAC catalog queries |
| httpx | Async satellite downloads |
| boto3 | Cloudflare R2 (S3-compatible) |
| SendGrid | Alert emails |
| Redis (Upstash) | Distributed zone scan locks |

### Frontend

| Technology | Role |
|------------|------|
| React 18 | UI framework |
| Vite 5 | Dev server and build |
| TailwindCSS 3 | Styling |
| React Leaflet + Leaflet Draw | Map and polygon tools |
| Recharts | NDVI and change-area charts |
| Zustand | Global state |
| Axios | HTTP client |
| React Router v6 | SPA routing |
| React Toastify | Live alert toasts |

### External services (free tiers available)

| Service | Purpose |
|---------|---------|
| MongoDB Atlas | Zones, alerts, NDVI snapshots |
| Upstash Redis | Scan locks (optional; memory fallback in dev) |
| Copernicus Data Space | Sentinel-2 fallback downloads |
| Cloudflare R2 | NDVI and change-map image hosting |
| SendGrid | Email notifications |

---

## Project Structure

```
Foresence/
├── README.md
├── FORESENCE_DEEP_DIVE.md          # Extended technical notes
├── .gitignore
│
├── backend/
│   ├── .env.example                # Copy to .env (never commit .env)
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── render.yaml
│   ├── static/                     # Local image fallback (ndvi/, changes/)
│   └── app/
│       ├── main.py                 # FastAPI app, lifespan, routers
│       ├── core/
│       │   ├── config.py           # Environment settings
│       │   ├── database.py         # MongoDB + indexes + timeseries
│       │   └── redis_client.py     # Locks + cache
│       ├── api/
│       │   ├── websocket.py        # /ws/alerts
│       │   └── routes/
│       │       ├── zones.py
│       │       ├── alerts.py
│       │       ├── snapshots.py
│       │       ├── health.py
│       │       └── demo.py         # Enabled when demo mode / flag set
│       ├── models/
│       │   ├── zone.py
│       │   ├── alert.py
│       │   └── snapshot.py
│       ├── services/
│       │   ├── sentinel_service.py # STAC + Copernicus
│       │   ├── ndvi_service.py
│       │   ├── change_detection.py
│       │   ├── alert_service.py
│       │   ├── storage_service.py
│       │   └── email_service.py
│       └── scheduler/
│           ├── scheduler.py
│           └── jobs.py             # scan_single_zone, run_all_zone_scans
│
└── frontend/
    ├── .env.example
    ├── package.json
    ├── vite.config.js              # Proxies /api and /ws to :8000
    └── src/
        ├── main.jsx
        ├── App.jsx                 # Routes + initial data load
        ├── services/api.js         # Axios API clients
        ├── store/appStore.js       # Zustand state
        ├── hooks/
        │   ├── useZones.js
        │   └── useWebSocket.js
        ├── components/
        │   ├── Layout/             # Sidebar, Header, StatusBar
        │   ├── Map/                # MapDashboard, ZoneDrawer, ZonePopup
        │   ├── Alerts/             # AlertCenter, AlertCard
        │   ├── Analytics/          # NDVIChart, ChangeAreaChart
        │   └── Settings/           # ZoneSettings, NotificationSettings
        └── pages/
            ├── AnalyticsPage.jsx
            └── SettingsPage.jsx
```

**Backend:** 22 Python modules in `app/`. **Frontend:** 25 source files under `src/`.

---

## API Reference

Interactive documentation: **`http://localhost:8000/docs`**

### Root

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | API metadata (`name`, `version`) |
| `GET` | `/static/{path}` | Local NDVI/change images when R2 is disabled |

### Zones — `/api/zones`

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/zones` | List all zones |
| `POST` | `/api/zones` | Create zone + start historical baseline scan |
| `GET` | `/api/zones/{id}` | Get one zone |
| `PUT` | `/api/zones/{id}` | Update settings |
| `DELETE` | `/api/zones/{id}` | Delete zone and related alerts |
| `POST` | `/api/zones/{id}/scan` | Trigger immediate scan |

**Create zone — request body:**

```json
{
  "name": "Western Ghats Reserve",
  "description": "Biodiversity hotspot",
  "geojson": {
    "type": "Polygon",
    "coordinates": [[[76.5, 11.8], [76.9, 11.8], [76.9, 12.2], [76.5, 12.2], [76.5, 11.8]]]
  },
  "ndvi_drop_threshold": 0.15,
  "confidence_threshold": 0.70,
  "alert_emails": ["ranger@forest.gov"],
  "webhook_url": "https://example.com/webhook"
}
```

| Field | Range | Meaning |
|-------|-------|---------|
| `ndvi_drop_threshold` | 0.05 – 0.40 | Minimum NDVI decrease to trigger alert |
| `confidence_threshold` | 0.10 – 1.00 | Minimum confidence score (reduces false positives) |

### Alerts — `/api/alerts`

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/alerts` | List alerts (filterable, paginated) |
| `GET` | `/api/alerts/summary` | Counts by status |
| `GET` | `/api/alerts/{id}` | Single alert |
| `PUT` | `/api/alerts/{id}/status` | Update to `acknowledged` or `resolved` |

**Query parameters:** `zone_id`, `severity`, `status`, `limit` (max 200), `skip`

### Snapshots — `/api/snapshots`

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/snapshots` | List NDVI snapshots |
| `GET` | `/api/snapshots/latest/{zone_id}` | Latest snapshot for zone |

**Query parameters:** `zone_id`, `start_date`, `end_date`, `limit`

### Health — `/api/health`

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Database, Redis, scheduler, `last_scan_at` |
| `POST` | `/api/health/satellite-check` | Verify STAC/Copernicus coverage for a polygon |

### Demo — `/api/demo` *(when `ENABLE_DEMO_ROUTES=true` or `APP_MODE=demo`)*

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/demo/seed` | Insert demo zones, snapshots, alerts |
| `DELETE` | `/api/demo/clear` | Remove demo data |

---

## WebSocket Events

**Endpoint:** `ws://localhost:8000/ws/alerts` (production: use `wss://` and `VITE_WS_URL`)

```mermaid
sequenceDiagram
  participant B as Browser
  participant S as FastAPI

  B->>S: Connect /ws/alerts
  S-->>B: type: connected
  loop Keepalive
    B->>S: type: ping
    S-->>B: type: pong
  end
  Note over S: On alert / health / scan
  S-->>B: type: alert | health_update | scan_complete
```

| `type` | When | Key fields |
|--------|------|------------|
| `connected` | On connect | `message` |
| `alert` | New deforestation alert | `alert_id`, `zone_name`, `severity`, `confidence`, `change_area_ha` |
| `health_update` | Zone health changed | `zone_id`, `health_score`, `status` |
| `scan_complete` | Scan finished | `zone_id`, `zone_name`, `ndvi_mean`, `scan_id` |
| `pong` | Response to `ping` | — |

**Client → server:** `{"type":"ping"}`

---

## Database Schema

**Database name:** `foresence` (configurable via `DB_NAME`)

### Collection: `zones`

```json
{
  "_id": "ObjectId",
  "name": "Western Ghats Reserve",
  "description": "string",
  "geojson": { "type": "Polygon", "coordinates": [[[lon, lat], ...]] },
  "area_ha": 42500.0,
  "ndvi_drop_threshold": 0.15,
  "confidence_threshold": 0.70,
  "alert_emails": ["ranger@gov.in"],
  "webhook_url": null,
  "health_score": 61,
  "status": "warning",
  "active": true,
  "created_at": "ISO-8601",
  "last_scanned_at": "ISO-8601"
}
```

### Collection: `alerts`

```json
{
  "_id": "ObjectId",
  "zone_id": "string",
  "zone_name": "string",
  "detected_at": "ISO-8601",
  "ndvi_before": 0.72,
  "ndvi_after": 0.34,
  "ndvi_delta": -0.38,
  "evi_before": 0.61,
  "evi_after": 0.27,
  "change_area_ha": 1240.0,
  "confidence": 0.94,
  "severity": "critical",
  "change_map_url": "https://...",
  "status": "new",
  "notified": true,
  "notified_at": "ISO-8601",
  "notes": ""
}
```

### Collection: `ndvi_snapshots` *(MongoDB timeseries)*

```json
{
  "timestamp": "ISO-8601",
  "zone_id": "string",
  "ndvi_mean": 0.654,
  "ndvi_min": 0.421,
  "ndvi_max": 0.871,
  "evi_mean": 0.541,
  "cloud_cover_pct": 8.3,
  "image_url": "https://...",
  "scan_id": "a3f2c1d8"
}
```

---

## Frontend Application

### Routes

| Path | Component | Purpose |
|------|-----------|---------|
| `/` | `MapDashboard` | Map, zones, draw tool, manual scan |
| `/alerts` | `AlertCenter` | Alert inbox with filters |
| `/analytics` | `AnalyticsPage` | NDVI trend + change-area charts |
| `/settings` | `SettingsPage` | Zone and notification settings |

### Zone map colors

| Color | Health score | Status |
|-------|--------------|--------|
| Green | > 70 | `healthy` |
| Yellow | 40 – 70 | `warning` |
| Red | < 40 | `critical` |

### App initialization

On load: connect WebSocket → `fetchZones()` → load alerts → `healthApi.check()`.

---

## Detection Logic

### Vegetation indices

- **NDVI:** `(NIR − Red) / (NIR + Red)` — healthy forest typically **0.6 – 0.9**
- **EVI:** `2.5 × (NIR − Red) / (NIR + 6×Red − 7.5×Blue + 1)` — better in dense canopy
- **Cloud proxy:** pixels with blue reflectance > 0.3

### Alert trigger

An alert is created when **both** conditions hold:

```
confidence >= zone.confidence_threshold
AND ndvi_delta <= -zone.ndvi_drop_threshold
```

### Severity (from `ndvi_delta`)

| Severity | Condition |
|----------|-----------|
| `critical` | Δ ≤ −0.35 |
| `high` | Δ ≤ −0.25 |
| `medium` | Δ ≤ −0.15 |
| `low` | otherwise |

### Authentication

**There is no end-user authentication** on REST or WebSocket in the current version. All API routes are open; secure deployments should add auth (see [Roadmap](#roadmap)).

---

## Configuration

### Backend (`backend/.env`)

Copy from `backend/.env.example`:

```env
# Required
MONGODB_URI=mongodb+srv://user:password@cluster.mongodb.net/
DB_NAME=foresence

# Recommended
UPSTASH_REDIS_URL=rediss://default:password@host.upstash.io:6380

# Satellite (fallback; STAC works without credentials)
COPERNICUS_USERNAME=
COPERNICUS_PASSWORD=

# Image storage (optional — uses /static if not configured)
CLOUDFLARE_R2_ACCESS_KEY=
CLOUDFLARE_R2_SECRET_KEY=
CLOUDFLARE_R2_BUCKET_NAME=foresence-images
CLOUDFLARE_R2_ENDPOINT=
CLOUDFLARE_R2_PUBLIC_URL=

# Email (optional)
SENDGRID_API_KEY=
ALERT_FROM_EMAIL=

# Behavior
SCAN_INTERVAL_HOURS=12
NDVI_DROP_THRESHOLD=0.15
CONFIDENCE_THRESHOLD=0.70
CORS_ORIGINS=http://localhost:5173
FRONTEND_URL=http://localhost:5173

# Optional flags
APP_MODE=prod
ENABLE_DEMO_ROUTES=false
ENABLE_PREDEFINED_ZONES=true
PREDEFINED_ZONES_JSON=[]
```

### Frontend (`frontend/.env`)

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

> **Security:** Never commit `.env` files. Use `.env.example` as templates only. `.gitignore` excludes `.env` and `venv/`.

---

## Quick Start

### Prerequisites

- Python **3.11+** (3.12 supported)
- Node.js **18+**
- MongoDB Atlas URI (or local MongoDB)

### 1. Clone and configure

```bash
git clone https://github.com/YOUR_USERNAME/foresense.git
cd foresense/Foresence

cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
# Edit backend/.env with your MongoDB URI
```

### 2. Backend

```bash
cd backend
python -m venv venv

# Windows PowerShell
.\venv\Scripts\Activate.ps1

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

### 4. Open the app

| URL | Description |
|-----|-------------|
| http://localhost:5173 | Web dashboard |
| http://localhost:8000/docs | Swagger API |
| http://localhost:8000/api/health | System health |

### 5. First data

Click **Seed Demo Data** in the header, or draw a zone on the map.

---

## Demo Mode

Use demo mode to explore the UI **without** Copernicus or R2 credentials.

```env
APP_MODE=demo
ENABLE_DEMO_ROUTES=true
```

Or call the API directly:

```bash
curl -X POST http://localhost:8000/api/demo/seed
curl -X DELETE http://localhost:8000/api/demo/clear
```

Demo seed creates three sample Indian forest zones, 60 days of NDVI snapshots, and sample alerts.

---

## Deployment

### Backend — Render

`backend/render.yaml` is included. Set all environment variables in the Render dashboard. Use a paid plan for always-on scheduling (free tier may sleep).

### Frontend — Vercel

- Root directory: `frontend`
- Build: `npm run build`
- Env: `VITE_API_URL`, `VITE_WS_URL` pointing to your deployed API

### Docker

```bash
docker build -t foresense-api ./backend
docker run -p 8000:8000 --env-file backend/.env foresense-api
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Redis URL error | Use a valid `rediss://` Upstash URL, or leave empty for in-memory fallback |
| No zones on map | Run demo seed or create a zone with the draw tool |
| Scan returns no data | Configure Copernicus credentials or use demo mode |
| Frontend cannot reach API | Check `VITE_API_URL` and `CORS_ORIGINS` |
| `rasterio` install fails (Windows) | `pip install wheel` then `pip install rasterio --only-binary=rasterio` |
| MongoDB connection timeout | Whitelist IP in Atlas (e.g. `0.0.0.0/0` for dev) |
| Demo seed 404 | Set `ENABLE_DEMO_ROUTES=true` or `APP_MODE=demo` |

---

## Roadmap

| Feature | Status |
|---------|--------|
| Sentinel-2 NDVI monitoring | ✅ Implemented |
| Real-time WebSocket alerts | ✅ Implemented |
| Email + webhook notifications | ✅ Implemented |
| User authentication (JWT / OAuth) | 🔲 Planned |
| CNN / ML classification | 🔲 Planned |
| PDF report export | 🔲 Planned |
| Multi-satellite (e.g. Landsat) | 🔲 Planned |
| SMS alerts (Twilio) | 🔲 Planned |

---

## Contributing

1. Fork the repository  
2. Create a branch: `git checkout -b feature/your-feature`  
3. Commit your changes  
4. Push and open a Pull Request  

Please do not commit secrets, `venv/`, or `node_modules/`.

---

## Pushing to GitHub

From the project root (`Foresence` or parent `Deforesense`):

```bash
git init
git add .
git status   # verify .env and venv/ are NOT listed
git commit -m "Initial commit: Foresense deforestation monitoring platform"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/foresense.git
git push -u origin main
```

Ensure `git status` does not show `backend/.env`, `frontend/.env`, or `backend/venv/` before pushing.

---

## License

MIT License — see [LICENSE](LICENSE) if present, or add one for open-source distribution.

---

<p align="center">
  Built to protect forests using open satellite data and transparent geospatial analytics.
</p>
