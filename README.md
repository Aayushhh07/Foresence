# 🌿 Foresense — Illegal Deforestation Detection Platform

> **Real-time forest monitoring using Sentinel-2 satellite imagery, NDVI analysis, and AI-powered change detection.**

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Frontend-React%2018-61DAFB?style=flat-square&logo=react)](https://reactjs.org)
[![MongoDB](https://img.shields.io/badge/Database-MongoDB-47A248?style=flat-square&logo=mongodb)](https://mongodb.com)
[![Redis](https://img.shields.io/badge/Cache-Redis-DC382D?style=flat-square&logo=redis)](https://redis.io)
[![Sentinel-2](https://img.shields.io/badge/Satellite-Sentinel--2-0099CC?style=flat-square)](https://sentinel.esa.int)

---

## 📖 Table of Contents

1. [What is Foresense?](#1-what-is-foresense)
2. [How It Works — The Big Picture](#2-how-it-works--the-big-picture)
3. [Tech Stack](#3-tech-stack)
4. [Project Structure](#4-project-structure)
5. [Architecture Deep Dive](#5-architecture-deep-dive)
6. [API Reference](#6-api-reference)
7. [Frontend Pages & Components](#7-frontend-pages--components)
8. [Database Schema](#8-database-schema)
9. [Setup Guide (Step by Step)](#9-setup-guide-step-by-step)
10. [Running the App](#10-running-the-app)
11. [User Manual — Every Feature Explained](#11-user-manual--every-feature-explained)
12. [Demo Mode](#12-demo-mode)
13. [What Is Working vs What Needs External Setup](#13-what-is-working-vs-what-needs-external-setup)
14. [How to Add New Features](#14-how-to-add-new-features)
15. [Deployment Guide](#15-deployment-guide)
16. [Troubleshooting](#16-troubleshooting)
17. [Glossary](#17-glossary)

---

## 1. What is Foresense?

Foresense is a **web application that monitors forests from space**. It uses satellite images taken by the European Space Agency's **Sentinel-2** satellite to detect when trees are being cut down — even in remote areas without human observers.

### The Problem It Solves

Illegal deforestation is one of the biggest contributors to climate change. Millions of hectares of forest disappear every year, but traditional monitoring (ground patrols, aerial surveys) is expensive and slow. By the time humans find out, it's too late.

### How Foresense Helps

- **Draws a polygon on a map** around any forest area you want to protect
- **Automatically downloads satellite images** of that area every 12 hours
- **Calculates NDVI** (Normalized Difference Vegetation Index) — a scientific measure of how green/healthy the vegetation is
- **Compares images over time** — if NDVI drops significantly, deforestation is detected
- **Sends instant alerts** with severity levels, affected area in hectares, and a visual change map
- **Tracks trends** with interactive charts showing vegetation health over time

---

## 2. How It Works — The Big Picture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FORESENSE SYSTEM                            │
│                                                                     │
│  User draws a zone    Scheduler runs     Satellite data downloaded  │
│  on the map      →    every 12 hours  →  from Copernicus/STAC       │
│       ↓                                          ↓                  │
│  Zone saved to        NDVI computed              Rasterio clips      │
│  MongoDB          ←   and stored        ←        the image to zone  │
│       ↓                                          ↓                  │
│  Change detection:    Alert created if    WebSocket pushes alert    │
│  vs previous NDVI  →  drop > threshold →  to browser in real-time  │
│       ↓                                          ↓                  │
│  Dashboard shows      Email sent to       Toast notification shows  │
│  updated health   ←   configured emails ← in the user's browser    │
└─────────────────────────────────────────────────────────────────────┘
```

### Step-By-Step Pipeline

1. **User creates a monitoring zone** — draws a polygon on the Leaflet map
2. **APScheduler triggers a scan** — runs every 12 hours (configurable)
3. **Sentinel service** — searches Copernicus Data Space for recent Sentinel-2 L2A products over that polygon with < 30% cloud cover
4. **Fallback to Element84 STAC** — if Copernicus doesn't have imagery, tries public STAC catalog
5. **Band extraction** — extracts Band 2 (Blue), Band 4 (Red), Band 8 (NIR) from the satellite ZIP
6. **Rasterio clipping** — clips the large satellite tile to the exact zone polygon boundary
7. **NDVI computation**: `(NIR - Red) / (NIR + Red)` — values range from -1 to +1; healthy forest is 0.6–0.9
8. **EVI computation**: Enhanced Vegetation Index (more accurate in dense canopy)
9. **Snapshot storage** — saves NDVI/EVI stats + image URL to MongoDB time-series collection
10. **Change detection** — compares current NDVI array against previous snapshot
11. **If NDVI drop > threshold AND confidence > threshold** → creates an alert
12. **Alert saved to MongoDB** — with severity (low/medium/high/critical), affected area in hectares, change map image
13. **WebSocket broadcast** — all connected browsers receive the alert instantly
14. **Toast notification** appears in the user's browser
15. **Email notification** sent via SendGrid to configured recipients

---

## 3. Tech Stack

### Backend

| Technology | What it does | Why it was chosen |
|---|---|---|
| **FastAPI** | Python web framework, REST API + WebSocket | Async-native, auto docs, fast |
| **Uvicorn** | ASGI server that runs FastAPI | Async, production-grade |
| **Motor** | Async MongoDB driver for Python | Non-blocking DB operations |
| **APScheduler** | Task scheduler — runs zone scans | Background jobs without Celery |
| **Rasterio** | Reads and processes satellite GeoTIFF/JP2 files | Industry standard for raster data |
| **NumPy** | Array math for NDVI computation | Fast pixel-level operations |
| **Matplotlib** | Renders change map PNGs | Simple image generation |
| **Shapely** | Geometry operations (polygon clipping) | Spatial math |
| **PyProj** | Coordinate system transformations | WGS84 ↔ UTM projections |
| **httpx** | Async HTTP client (downloads satellite data) | Streaming large files |
| **pystac-client** | Queries STAC catalogs (Element84 fallback) | Standard satellite data API |
| **boto3** | AWS S3 compatible — uploads to Cloudflare R2 | Image storage |
| **SendGrid** | Email notifications for alerts | Reliable email delivery |
| **Redis** | Distributed zone scan locks + caching | Prevents duplicate scans |
| **pydantic-settings** | Loads and validates `.env` configuration | Type-safe config |

### Frontend

| Technology | What it does |
|---|---|
| **React 18** | UI component framework |
| **Vite** | Fast dev server and bundler |
| **TailwindCSS** | Utility-first CSS framework |
| **React Leaflet** | Interactive map with satellite tiles |
| **Leaflet Draw** | Draw polygons on the map |
| **Recharts** | NDVI time-series charts |
| **Zustand** | Simple global state management |
| **Axios** | HTTP client for API calls |
| **React Router v6** | Client-side routing (SPA) |
| **React Toastify** | Toast notifications for new alerts |

### External Services

| Service | Purpose | Free Tier? |
|---|---|---|
| **MongoDB Atlas** | Cloud database (zones, alerts, snapshots) | ✅ Free M0 (512MB) |
| **Upstash Redis** | Zone scan locks + caching | ✅ Free (10k ops/day) |
| **Copernicus Data Space** | Sentinel-2 satellite imagery | ✅ Free (registration) |
| **Cloudflare R2** | Store NDVI/change map images | ✅ Free (10GB/month) |
| **SendGrid** | Email alerts | ✅ Free (100 emails/day) |

---

## 4. Project Structure

```
Foresense/
│
├── README.md                          ← You are here
├── .gitignore
│
├── backend/                           ← Python FastAPI server
│   ├── .env                           ← Environment variables (secrets go here)
│   ├── .env.example                   ← Template showing what vars are needed
│   ├── requirements.txt               ← Python package dependencies
│   ├── Dockerfile                     ← Container definition for deployment
│   ├── render.yaml                    ← Render.com deployment config
│   │
│   ├── venv/                          ← Python virtual environment (auto-created)
│   │
│   └── app/                           ← Main application package
│       ├── __init__.py
│       ├── main.py                    ← FastAPI app, startup/shutdown, router registration
│       │
│       ├── core/                      ← Shared infrastructure
│       │   ├── config.py              ← Reads .env, exposes settings object
│       │   ├── database.py            ← MongoDB connection + index creation
│       │   └── redis_client.py        ← Redis connection + zone locking
│       │
│       ├── api/                       ← HTTP endpoints
│       │   ├── websocket.py           ← WebSocket /ws/alerts endpoint
│       │   └── routes/
│       │       ├── zones.py           ← GET/POST/PUT/DELETE /api/zones
│       │       ├── alerts.py          ← GET/PUT /api/alerts
│       │       ├── snapshots.py       ← GET /api/snapshots (NDVI time-series)
│       │       ├── health.py          ← GET /api/health (system status)
│       │       └── demo.py            ← POST /api/demo/seed (populate demo data)
│       │
│       ├── models/                    ← Pydantic data models (request/response shapes)
│       │   ├── zone.py                ← ZoneCreate, ZoneUpdate, ZoneResponse
│       │   ├── alert.py               ← AlertCreate, AlertStatusUpdate
│       │   └── snapshot.py            ← Snapshot model
│       │
│       ├── services/                  ← Business logic
│       │   ├── sentinel_service.py    ← Downloads Sentinel-2 satellite bands
│       │   ├── ndvi_service.py        ← Computes NDVI/EVI from bands using rasterio
│       │   ├── change_detection.py    ← Compares NDVIs, computes affected area
│       │   ├── alert_service.py       ← Creates alerts, updates health, sends emails
│       │   ├── storage_service.py     ← Uploads images to Cloudflare R2
│       │   └── email_service.py       ← SendGrid email templates
│       │
│       └── scheduler/                 ← Background job system
│           ├── scheduler.py           ← APScheduler setup and lifecycle
│           └── jobs.py                ← scan_single_zone(), run_all_zone_scans()
│
└── frontend/                          ← React application
    ├── .env                           ← Frontend environment (API URLs)
    ├── package.json                   ← Node.js dependencies
    ├── vite.config.js                 ← Vite build config
    ├── tailwind.config.js             ← TailwindCSS config
    ├── index.html                     ← HTML entry point
    │
    ├── public/                        ← Static assets
    │
    └── src/
        ├── main.jsx                   ← React app entry (mounts to #root)
        ├── App.jsx                    ← Root component: router, initial data load
        ├── App.css                    ← Global styles
        ├── index.css                  ← Tailwind imports + CSS variables
        │
        ├── services/
        │   └── api.js                 ← Axios client, all API functions grouped by resource
        │
        ├── store/
        │   └── appStore.js            ← Zustand global state (zones, alerts, health, WS)
        │
        ├── hooks/
        │   ├── useZones.js            ← Zone CRUD operations using the API
        │   └── useWebSocket.js        ← WebSocket connection with auto-reconnect
        │
        ├── components/
        │   ├── Layout/
        │   │   ├── Sidebar.jsx        ← Navigation sidebar (Map/Alerts/Analytics/Settings)
        │   │   ├── Header.jsx         ← Page title, stats pills, Seed Demo button
        │   │   └── StatusBar.jsx      ← Bottom bar: WS status, last scan time
        │   │
        │   ├── Map/
        │   │   ├── MapDashboard.jsx   ← Main Leaflet map, zone polygons, color coding
        │   │   ├── ZoneDrawer.jsx     ← Polygon drawing tool, zone creation form
        │   │   └── ZonePopup.jsx      ← Popup when clicking a zone on the map
        │   │
        │   ├── Alerts/
        │   │   ├── AlertCenter.jsx    ← Alert list with filters (severity, zone, status)
        │   │   └── AlertCard.jsx      ← Individual alert display card
        │   │
        │   ├── Analytics/
        │   │   ├── NDVIChart.jsx      ← Line chart of NDVI over time per zone
        │   │   └── ChangeAreaChart.jsx← Bar chart of affected area per alert
        │   │
        │   └── Settings/
        │       ├── ZoneSettings.jsx   ← Edit zone thresholds, emails, webhooks
        │       └── NotificationSettings.jsx ← Email/webhook preferences
        │
        └── pages/
            ├── AnalyticsPage.jsx      ← Full analytics view (charts + zone selector)
            └── SettingsPage.jsx       ← Full settings view
```

---

## 5. Architecture Deep Dive

### How the Backend is Organized

Think of it in layers:

```
Request comes in
      ↓
  FastAPI Router (api/routes/*.py)    ← Validates input, calls services
      ↓
  Service Layer (services/*.py)        ← Business logic, database calls
      ↓
  Data Layer (core/database.py)        ← MongoDB queries via Motor
      ↓
  Response goes back to client
```

### The Satellite Scan Pipeline (Most Complex Part)

```
APScheduler fires every 12 hours
          ↓
  jobs.py → run_all_zone_scans()
          ↓
  For each active zone in MongoDB:
          ↓
  1. Acquire Redis lock (prevents same zone being scanned twice)
          ↓
  2. sentinel_service.fetch_sentinel_bands()
     ├── Try: Copernicus OAuth → search OData API → download ZIP → extract B02/B04/B08
     └── Fallback: Element84 STAC → search → download COG TIFs
          ↓
  3. ndvi_service.compute_ndvi_for_zone()
     ├── rasterio opens band files
     ├── Clips bands to zone polygon (CRS transforms via pyproj)
     ├── Computes NDVI = (B08 - B04) / (B08 + B04)
     ├── Computes EVI = 2.5 * (B08 - B04) / (B08 + 6*B04 - 7.5*B02 + 1)
     ├── Detects clouds (NDVI outliers = cloud pixels)
     └── Uploads colorized NDVI PNG to Cloudflare R2
          ↓
  4. Store snapshot in MongoDB ndvi_snapshots collection
          ↓
  5. change_detection.detect_change()
     ├── Loads previous snapshot from DB
     ├── Computes pixel-level NDVI delta
     ├── Counts pixels below threshold (= affected pixels)
     ├── Converts affected pixels to hectares using pixel CRS info
     ├── Computes confidence score (adjusted for cloud cover)
     └── Renders change map PNG (red=loss, green=gain) → uploads to R2
          ↓
  6. alert_service.create_alert_if_triggered()
     ├── If NDVI delta < -threshold AND confidence >= threshold:
     │   ├── Determine severity (low/medium/high/critical)
     │   ├── Insert alert into MongoDB
     │   ├── Update zone health_score and status
     │   ├── Broadcast via WebSocket to all browsers
     │   ├── Send email via SendGrid
     │   └── POST to webhook URL (if configured)
     └── Release Redis lock
```

### WebSocket Real-Time Flow

```
Browser connects to ws://localhost:8000/ws/alerts
          ↓
Server adds browser to _connected_clients set
          ↓
Server sends: { "type": "connected", "message": "..." }
          ↓
Browser starts 30-second ping/pong keepalive
          ↓
When alert created → broadcast() sends to ALL connected browsers
          ↓
Browser receives: { "type": "alert", "severity": "high", ... }
          ↓
Zustand store updated → React re-renders
          ↓
Toast notification pops up
```

### Frontend State Management

```
Zustand Store (appStore.js)
│
├── zones[]          ← All forest zones from API
├── alerts[]         ← Recent alerts from API
├── snapshots[]      ← NDVI time-series data
├── systemHealth{}   ← DB/Redis/Scheduler status
├── wsConnected      ← WebSocket connection state
└── sidebarCollapsed ← UI state

Components read from store → User actions call API → Store updates → UI re-renders
```

---

## 6. API Reference

All API responses follow this standard format:
```json
{
  "success": true,
  "data": { ... },
  "message": "Human readable description"
}
```

### Zones API

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/zones` | List all forest zones |
| `POST` | `/api/zones` | Create a new monitoring zone |
| `GET` | `/api/zones/{id}` | Get a single zone by ID |
| `PUT` | `/api/zones/{id}` | Update zone settings |
| `DELETE` | `/api/zones/{id}` | Delete zone and its alerts |
| `POST` | `/api/zones/{id}/scan` | Trigger immediate satellite scan |

**Create Zone — Request Body:**
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
  "webhook_url": "https://your-system.com/webhook"
}
```

### Alerts API

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/alerts` | List alerts (filterable) |
| `GET` | `/api/alerts/{id}` | Get single alert |
| `PUT` | `/api/alerts/{id}/status` | Mark as acknowledged/resolved |

**List Alerts — Query Parameters:**
```
?zone_id=abc123        Filter by zone
?severity=critical     Filter by severity (low/medium/high/critical)
?status=new            Filter by status (new/acknowledged/resolved)
?limit=50              Max results (default 50, max 200)
?skip=0                Pagination offset
```

### Snapshots API

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/snapshots` | List NDVI snapshots |
| `GET` | `/api/snapshots/latest/{zone_id}` | Get latest snapshot for a zone |

**List Snapshots — Query Parameters:**
```
?zone_id=abc123        Filter by zone (required for meaningful results)
?start_date=2026-01-01 ISO date filter
?end_date=2026-04-01   ISO date filter
?limit=90              Max results (default 90)
```

### System API

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | System health (DB, Redis, Scheduler) |
| `GET` | `/` | Root info endpoint |
| `POST` | `/api/demo/seed` | Populate database with demo data |
| `DELETE` | `/api/demo/clear` | Clear all data from database |

### WebSocket

| Endpoint | Description |
|---|---|
| `ws://localhost:8000/ws/alerts` | Real-time alert stream |

**Message Types Received:**
```json
{ "type": "connected", "message": "Connected to Foresence real-time alerts" }
{ "type": "alert", "alert_id": "...", "zone_name": "...", "severity": "high", "confidence": 0.87 }
{ "type": "health_update", "zone_id": "...", "health_score": 61, "status": "warning" }
{ "type": "scan_complete", "zone_id": "...", "zone_name": "...", "ndvi_mean": 0.654 }
{ "type": "pong" }
```

**Interactive API Documentation:**
```
http://localhost:8000/docs      ← Swagger UI (try all endpoints here)
http://localhost:8000/redoc     ← ReDoc documentation
```

---

## 7. Frontend Pages & Components

### Page 1: Map Dashboard (`/`)

**What you see:** A full-screen interactive map (OpenStreetMap) with colored polygon overlays for each monitored forest zone.

**Zone Colors:**
- 🟢 Green — Healthy (health score > 70)
- 🟡 Yellow — Warning (health score 40–70)
- 🔴 Red — Critical (health score < 40)

**How to interact:**
- Click any zone polygon → popup shows zone stats, last scan time, NDVI value, manual scan button
- Click the polygon drawing tool (top-right diamond icons) → draw a new zone
- After drawing, a form appears to name the zone and set thresholds
- Click "Scan Now" in the popup → triggers an immediate satellite scan

### Page 2: Alert Center (`/alerts`)

**What you see:** A list of all deforestation detection events, newest first.

**Features:**
- Filter by severity (Critical/High/Medium/Low)
- Filter by status (New/Acknowledged/Resolved)
- Filter by specific zone
- Click "Acknowledge" → changes alert status, removes from "new" count
- Click "Resolve" → marks as handled
- Each card shows: severity badge, zone name, NDVI before/after, affected area in hectares, confidence percentage, detection timestamp

### Page 3: Analytics (`/analytics`)

**What you see:** Time-series charts of vegetation health over time.

**Charts:**
- **NDVI Trend** — Line chart showing NDVI mean over the past 60 days per zone
- **Change Area** — Bar chart of affected area (hectares) per alert event

**How to use:**
- Select a zone from the dropdown → charts update to show that zone's data
- Hover over chart points → tooltip shows exact values and dates

### Page 4: Settings (`/settings`)

**What you see:** Zone management and notification configuration.

**Zone Settings:**
- Edit zone name, description
- Adjust NDVI drop threshold (0.05 – 0.40): lower = more sensitive to small changes
- Adjust confidence threshold (0.10 – 1.00): higher = fewer false positives
- Add/remove alert email addresses
- Set webhook URL for integration with other systems
- Toggle zone active/inactive (inactive zones are skipped in scans)
- Delete zone (removes all associated alerts)

**Notification Settings:**
- Configure email addresses per zone
- Webhook URL format and delivery format

---

## 8. Database Schema

### Collection: `zones`
```json
{
  "_id": "ObjectId",
  "name": "Western Ghats Reserve",
  "description": "Biodiversity hotspot...",
  "geojson": {
    "type": "Polygon",
    "coordinates": [[[lon, lat], ...]]
  },
  "area_ha": 42500.0,
  "ndvi_drop_threshold": 0.15,
  "confidence_threshold": 0.70,
  "alert_emails": ["ranger@gov.in"],
  "webhook_url": null,
  "health_score": 61,
  "status": "warning",
  "active": true,
  "created_at": "2026-01-01T00:00:00Z",
  "last_scanned_at": "2026-04-23T10:00:00Z"
}
```

### Collection: `alerts`
```json
{
  "_id": "ObjectId",
  "zone_id": "string (ObjectId reference)",
  "zone_name": "Western Ghats Reserve",
  "detected_at": "2026-04-22T08:00:00Z",
  "ndvi_before": 0.72,
  "ndvi_after": 0.34,
  "ndvi_delta": -0.38,
  "evi_before": 0.61,
  "evi_after": 0.27,
  "change_area_ha": 1240.0,
  "confidence": 0.94,
  "severity": "critical",
  "change_map_url": "https://r2.dev/changes/zone_id/scan_id.png",
  "status": "new",
  "notified": true,
  "notified_at": "2026-04-22T08:05:00Z",
  "notes": ""
}
```

### Collection: `ndvi_snapshots` *(MongoDB Timeseries)*
```json
{
  "timestamp": "2026-04-23T10:00:00Z",
  "zone_id": "string (ObjectId reference)",
  "ndvi_mean": 0.654,
  "ndvi_min": 0.421,
  "ndvi_max": 0.871,
  "evi_mean": 0.541,
  "cloud_cover_pct": 8.3,
  "image_url": "https://r2.dev/ndvi/zone_id/scan_id.png",
  "scan_id": "a3f2c1d8"
}
```

**Indexes created automatically on startup:**
- `zones`: status, active, geojson (2dsphere), created_at
- `alerts`: zone_id, detected_at, severity, status, confidence
- `ndvi_snapshots`: (zone_id, timestamp) compound index

---

## 9. Setup Guide (Step by Step)

### Prerequisites

You need these installed on your computer:
- **Python 3.12** — [Download](https://python.org/downloads)
- **Node.js 18+** — [Download](https://nodejs.org)
- **Git** — [Download](https://git-scm.com)

Check your versions:
```powershell
python --version    # Should show 3.12.x
node --version      # Should show 18.x or higher
git --version
```

---

### Step 1: Get the Code

```powershell
git clone https://github.com/yourname/foresense.git
cd foresense
```

---

### Step 2: Set Up External Services

#### 2a. MongoDB Atlas (Free Database)

1. Go to [cloud.mongodb.com](https://cloud.mongodb.com) → Sign up free
2. Click **"Build a Database"** → Choose **M0 Free** → Any region → Create
3. Go to **"Database Access"** → **"Add New Database User"**
   - Username: `foresense`
   - Password: Click "Autogenerate" → **Copy it**
   - Role: **Atlas Admin**
4. Go to **"Network Access"** → **"Add IP Address"** → **"Allow Access From Anywhere"**
5. Go to **"Database"** → **"Connect"** → **"Drivers"** → Copy the URI
   - It looks like: `mongodb+srv://foresense:<password>@cluster.xxxxx.mongodb.net/`
   - Replace `<password>` with the password you copied

#### 2b. Upstash Redis (Free Cache)

1. Go to [upstash.com](https://upstash.com) → Sign up free
2. Click **"Create Database"**
   - Name: `foresense-redis`
   - Type: Regional
   - Region: Pick closest to you
3. Click on the database → find **"Redis URL"**
   - It looks like: `rediss://default:PASSWORD@host.upstash.io:6380`
   - Copy the full URL (must start with `rediss://`)

#### 2c. Optional Services (for full functionality)

**Copernicus Data Space** (for real satellite data):
1. Register at [dataspace.copernicus.eu](https://dataspace.copernicus.eu)
2. Verify your email
3. Your username = the email you registered with

**Cloudflare R2** (for image storage):
1. Create account at [cloudflare.com](https://cloudflare.com)
2. Go to **R2** → Create Bucket named `foresence-images`
3. Go to **Manage R2 API Tokens** → Create token with read/write access
4. Note the Account ID from the URL (used in endpoint)
5. Endpoint format: `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`

**SendGrid** (for email notifications):
1. Create account at [sendgrid.com](https://sendgrid.com)
2. Go to **Settings** → **API Keys** → Create API Key → Full Access
3. Verify sender email in **Sender Authentication**

---

### Step 3: Configure the Backend

```powershell
cd backend
```

Open `.env` and fill in your values:

```env
# ── REQUIRED (real values needed) ──────────────────────────────────────
MONGODB_URI=mongodb+srv://foresense:YourPassword@cluster.xxxxx.mongodb.net/
DB_NAME=foresence

UPSTASH_REDIS_URL=rediss://default:YourPassword@your-name.upstash.io:6380

# ── OPTIONAL (leave as "demo" to use demo mode) ─────────────────────────
COPERNICUS_USERNAME=your_username@email.com
COPERNICUS_PASSWORD=your_copernicus_password

CLOUDFLARE_R2_ACCESS_KEY=your_r2_access_key
CLOUDFLARE_R2_SECRET_KEY=your_r2_secret_key
CLOUDFLARE_R2_BUCKET_NAME=foresence-images
CLOUDFLARE_R2_ENDPOINT=https://your-account-id.r2.cloudflarestorage.com
CLOUDFLARE_R2_PUBLIC_URL=https://pub-xxxx.r2.dev

SENDGRID_API_KEY=SG.your_sendgrid_key
ALERT_FROM_EMAIL=alerts@yourdomain.com

# ── SETTINGS ──────────────────────────────────────────────────────────
SCAN_INTERVAL_HOURS=12
NDVI_DROP_THRESHOLD=0.15
CONFIDENCE_THRESHOLD=0.70
CORS_ORIGINS=http://localhost:5173
FRONTEND_URL=http://localhost:5173
```

---

### Step 4: Install Backend Dependencies

```powershell
# Create a virtual environment (isolated Python sandbox)
python -m venv venv

# Activate it (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Install all packages
pip install -r requirements.txt
```

> **Note:** `rasterio` installation can be slow (large geospatial library). Please wait.

---

### Step 5: Install Frontend Dependencies

```powershell
cd ..\frontend
npm install
```

---

## 10. Running the App

You need **two terminals open simultaneously** — one for backend, one for frontend.

### Terminal 1 — Backend

```powershell
cd C:\Users\jannu\Desktop\Foresense\backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

**Expected output:**
```
INFO  Foresence backend starting up...
INFO  Connected to MongoDB successfully.
INFO  MongoDB indexes created successfully.
INFO  Connected to Redis successfully.
INFO  Scheduler started. Zone scans every 12 hours.
INFO  Foresence backend ready.
INFO  Uvicorn running on http://127.0.0.1:8000
```

### Terminal 2 — Frontend

```powershell
cd C:\Users\jannu\Desktop\Foresense\frontend
npm run dev
```

**Expected output:**
```
  VITE v5.x.x  ready in 500ms
  ➜  Local:   http://localhost:5173/
```

### Access the App

| URL | What's there |
|---|---|
| `http://localhost:5173` | The main web app |
| `http://localhost:8000/docs` | Interactive API documentation |
| `http://localhost:8000/api/health` | System health check |

---

## 11. User Manual — Every Feature Explained

### Creating Your First Monitoring Zone

1. Open `http://localhost:5173`
2. You'll see the **Map Dashboard** with an India-centered map
3. Look for the **diamond-shaped icons** in the top-right corner of the map
4. Click the **first diamond** (polygon tool)
5. Click on the map to place polygon vertices around the forest area you want to monitor
6. Double-click to finish drawing
7. A form panel appears on the left — fill in:
   - **Zone Name** — e.g., "Western Ghats Reserve"
   - **Description** — optional notes
   - **NDVI Drop Threshold** — `0.15` means "alert if NDVI drops by 15% or more"
   - **Confidence Threshold** — `0.70` means "only alert if 70% confident it's real change"
   - **Alert Emails** — add email addresses to notify (optional)
8. Click **"Create Zone"**
9. The zone appears as a green polygon on the map

### Understanding Zone Colors

| Color | Health Score | Meaning |
|---|---|---|
| 🟢 Green | > 70 | Forest is healthy, no significant changes |
| 🟡 Yellow | 40–70 | Some vegetation loss detected, monitoring closely |
| 🔴 Red | < 40 | Severe deforestation detected, alerts active |

### Triggering a Satellite Scan

**Automatic:** Runs every 12 hours for all active zones.

**Manual:**
1. Click on any zone polygon on the map
2. A popup appears with zone details
3. Click **"Scan Now"** button
4. The backend queues an immediate scan
5. Check the browser console or terminal for scan progress
6. Results appear within a few minutes (depending on satellite data availability)

> **In demo mode:** Scans won't actually download satellite data since Copernicus credentials needed.

### Reading an Alert

Alerts appear in the **Alert Center** (`/alerts` page). Each card shows:

- **Severity badge** (CRITICAL/HIGH/MEDIUM/LOW) — based on size of NDVI drop
  - LOW: NDVI dropped 0.15–0.25
  - MEDIUM: NDVI dropped 0.25–0.35
  - HIGH: NDVI dropped 0.35–0.50
  - CRITICAL: NDVI dropped > 0.50

- **Zone name** — which forest was affected

- **NDVI Before → After** — e.g., 0.72 → 0.34
  - This means vegetation went from 72% healthy to 34% healthy

- **Affected area** — how many hectares are impacted

- **Confidence** — how sure the system is (%)

- **Detected at** — when the change was detected

- **Status** — New / Acknowledged / Resolved

### Acknowledging an Alert

1. Go to `/alerts`
2. Find an alert with status "New"
3. Click **"Acknowledge"**
4. Status changes to "Acknowledged" → removed from "New Alerts" counter
5. This means a human has seen it and is investigating

### Resolving an Alert

1. Click **"Resolve"** on any acknowledged alert
2. Optionally add notes about what action was taken
3. Status changes to "Resolved" → archive only

### Reading the Analytics Charts

1. Go to `/analytics`
2. Select a zone from the dropdown at the top
3. **NDVI Trend Chart** — the line shows how green the forest was over time
   - Horizontal axis = dates (last 60 days)
   - Vertical axis = NDVI value (0 = no vegetation, 1 = perfect vegetation)
   - A dropping line = deforestation is occurring
4. **Change Area Chart** — bars show how many hectares were affected in each alert event

### Adjusting Sensitivity (Settings)

If you're getting too many false positives:
- Go to `/settings` → find your zone
- **Increase NDVI Drop Threshold** (e.g., 0.15 → 0.20) — only alerts on bigger changes
- **Increase Confidence Threshold** (e.g., 0.70 → 0.85) — only high-certainty alerts

If you want to catch more subtle changes:
- **Decrease NDVI Drop Threshold** (e.g., 0.15 → 0.10)
- **Decrease Confidence Threshold** (e.g., 0.70 → 0.60) — more sensitive but more false positives

---

## 12. Demo Mode

For testing without satellite API keys, use the built-in demo seed system.

### Using the Seed Button

1. Start both backend and frontend
2. In the app header, click **"🌱 Seed Demo Data"** button
3. Wait 2–3 seconds
4. The map populates with 3 realistic Indian forest zones:
   - **Western Ghats Reserve** — 42,500 ha, Warning status
   - **Sundarbans Mangrove Belt** — 98,000 ha, Critical status
   - **Assam Tropical Forest** — 31,200 ha, Healthy status
5. 90 NDVI snapshots (60 days × 3 zones) populate the analytics charts
6. 8 alerts of various severities appear in the Alert Center

### Using the API Directly

```powershell
# Seed demo data
curl -X POST http://localhost:8000/api/demo/seed

# Clear all data (full reset)
curl -X DELETE http://localhost:8000/api/demo/clear
```

### Via Swagger UI

1. Go to `http://localhost:8000/docs`
2. Find `POST /api/demo/seed`
3. Click **"Try it out"** → **"Execute"**
4. Refresh the frontend

---

## 13. What Is Working vs What Needs External Setup

### ✅ Works Right Now (No External Keys Needed)

| Feature | Status |
|---|---|
| Backend server starts | ✅ Working |
| MongoDB connection | ✅ Working (with Atlas) |
| Redis connection | ✅ Working (with Upstash) or memory fallback |
| Zone CRUD (create/read/update/delete) | ✅ Working |
| Demo data seeding | ✅ Working |
| Map with zone polygons | ✅ Working |
| Alert Center with filters | ✅ Working |
| Alert status updates | ✅ Working |
| Analytics charts | ✅ Working |
| WebSocket real-time connection | ✅ Working |
| Settings page | ✅ Working |
| Health check endpoint | ✅ Working |
| API documentation (Swagger) | ✅ Working |

### ⚠️ Needs Real Credentials to Work

| Feature | What's Needed |
|---|---|
| Real satellite scans | Copernicus account (free) |
| NDVI image thumbnails in alerts | Cloudflare R2 (free) |
| Email notifications | SendGrid account (free) + verified sender |
| Zone scan lock (distributed) | Upstash Redis (works fine with memory fallback in dev) |

### 🚧 Future Enhancements (Not Yet Built)

| Feature | Complexity | Value |
|---|---|---|
| User authentication (login/logout) | Medium | High — needed for production |
| Report PDF export | Medium | High — for rangers |
| Mobile app (React Native) | High | Medium |
| Multi-satellite support (Landsat 8) | High | Medium |
| AI classification (CNN model) | Very High | Very High |
| Historical comparison (years) | Low | High |
| Zone sharing between users | Medium | Medium |
| SMS alerts (Twilio) | Low | High |
| Offline map tiles | Medium | Medium |
| Species-level forest typing | Very High | High |

---

## 14. How to Add New Features

### Adding a New API Endpoint

1. **Create or open** a file in `backend/app/api/routes/`
2. **Define the router and endpoint:**

```python
# backend/app/api/routes/reports.py
from fastapi import APIRouter
from app.core.database import get_db

router = APIRouter(prefix="/api/reports", tags=["reports"])

@router.get("/summary")
async def get_summary():
    db = get_db()
    # your logic here
    return {"success": True, "data": {}, "message": "Summary"}
```

3. **Register in `main.py`:**

```python
from app.api.routes import zones, alerts, snapshots, health, demo, reports
# ...
app.include_router(reports.router)
```

4. **Call from frontend in `services/api.js`:**

```javascript
export const reportsApi = {
  summary: () => api.get('/api/reports/summary'),
};
```

### Adding a New Frontend Page

1. **Create the page component** in `frontend/src/pages/NewPage.jsx`
2. **Add route in `App.jsx`:**

```jsx
<Route path="/newpage" element={<NewPage />} />
```

3. **Add navigation link in `Sidebar.jsx`** (follow existing pattern)

### Adding a New Database Field to Zones

1. **Update `models/zone.py`** — add field to `ZoneCreate` and `ZoneResponse`
2. **Update the zone creation logic in `routes/zones.py`** to include the new field in `zone_doc`
3. **Update the frontend form** in `ZoneDrawer.jsx` or `ZoneSettings.jsx`

### Adding a New Alert Severity Level

1. **Edit `services/alert_service.py`** — update `_determine_severity()` function
2. **Edit frontend** `AlertCard.jsx` — add the new severity badge color

### Adding a New Notification Channel (e.g., SMS)

1. **Install the package:** `pip install twilio`
2. **Add credentials to `config.py`** and `.env`
3. **Create `services/sms_service.py`** following the `email_service.py` pattern
4. **Call it from `alert_service.py`** after the email send block

---

## 15. Deployment Guide

### Backend — Render.com (Free Tier)

A `render.yaml` file is already included. To deploy:

1. Push code to GitHub
2. Go to [render.com](https://render.com) → New → Blueprint
3. Connect your GitHub repo
4. Render reads `render.yaml` automatically
5. Add your environment variables in Render dashboard
6. Deploy

**Important:** Render free tier spins down after 15 minutes of inactivity. Use a paid plan for always-on monitoring.

### Frontend — Vercel (Free)

1. Push frontend code to GitHub
2. Go to [vercel.com](https://vercel.com) → New Project → Import repo
3. Set root directory to `frontend`
4. Add environment variable: `VITE_API_URL=https://your-render-app.onrender.com`
5. Deploy

### Docker (Self-hosted)

```powershell
# Build backend image
docker build -t foresense-backend ./backend

# Run container
docker run -p 8000:8000 --env-file backend/.env foresense-backend
```

---

## 16. Troubleshooting

### "ValueError: Redis URL must specify one of the following schemes"

**Cause:** `UPSTASH_REDIS_URL` in `.env` is still a placeholder (not a real URL).

**Fix:** Either:
- Paste a real Upstash Redis URL (must start with `rediss://`)
- The system now gracefully falls back to memory-only mode if URL is blank

---

### "TypeError: Unsupported type for run_date: float"

**Cause:** An old bug in `main.py` — now fixed (uses `datetime.utcnow() + timedelta(seconds=30)`)

**Fix:** Make sure you have the latest `main.py` from this repo.

---

### "No zones appearing on map"

**Cause:** Database is empty, no zones have been created.

**Fix:** Click **"🌱 Seed Demo Data"** button in the header, or create a zone manually with the polygon tool.

---

### "Backend starts but frontend shows connection error"

**Cause:** CORS issue or wrong API URL.

**Fix:** Check `frontend/.env`:
```
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```
Also verify backend `.env` has:
```
CORS_ORIGINS=http://localhost:5173
```

---

### "Scan triggered but no NDVI results"

**Cause:** Real satellite scan requires Copernicus credentials.

**Fix for demo:** Use the seed endpoint. For real scans, set `COPERNICUS_USERNAME` and `COPERNICUS_PASSWORD` in `.env`.

---

### "rasterio install fails on Windows"

**Fix:**
```powershell
pip install wheel
pip install rasterio --only-binary=rasterio
```
Or install via conda: `conda install rasterio`

---

### Backend shows "MongoDB waiting for suitable server"

**Cause:** Your IP is not whitelisted in MongoDB Atlas Network Access, or the connection string is wrong.

**Fix:**
1. Go to MongoDB Atlas → Network Access → Add `0.0.0.0/0`
2. Double-check the connection string has the correct password

---

## 17. Glossary

| Term | Meaning |
|---|---|
| **NDVI** | Normalized Difference Vegetation Index. Measures greenness. Formula: `(NIR - Red) / (NIR + Red)`. Ranges -1 to +1. Healthy forest = 0.6–0.9 |
| **EVI** | Enhanced Vegetation Index. More accurate than NDVI in dense forest. Reduces atmospheric effects |
| **NIR** | Near-Infrared band. Reflected strongly by healthy leaves |
| **Sentinel-2** | European Space Agency satellite constellation taking high-resolution (10m) images of Earth every 5 days |
| **L2A** | Level 2A product — Sentinel-2 data with atmospheric correction applied (ready for vegetation analysis) |
| **STAC** | SpatioTemporal Asset Catalog. Standard API for discovering satellite data |
| **GeoJSON** | JSON format for geographic shapes (polygons, points, lines) |
| **WKT** | Well-Known Text. Another format for geographic shapes, used by some APIs |
| **Rasterio** | Python library for reading and writing geospatial raster data (satellite image files) |
| **Cloud Cover** | Percentage of the satellite image obscured by clouds. Images > 30% cloud cover are rejected |
| **Health Score** | Internal 0–100 score for a zone. Starts at 100, decreases with each detected NDVI drop |
| **CRS** | Coordinate Reference System. Defines how coordinates map to the real Earth (e.g., WGS84, UTM) |
| **Motor** | Async Python driver for MongoDB (non-blocking database calls) |
| **APScheduler** | Python library for running background tasks on a schedule |
| **WebSocket** | Two-way communication protocol between browser and server. Allows server to push alerts instantly |
| **Zustand** | Lightweight React state management library (simpler than Redux) |
| **Pydantic** | Python library for data validation using type hints |
| **Uvicorn** | ASGI server that runs FastAPI applications |

---

## 📄 License

MIT License. See `LICENSE` file.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit changes: `git commit -m "Add: your feature description"`
4. Push: `git push origin feature/your-feature`
5. Open a Pull Request

## 📬 Contact

For questions, open a GitHub Issue or email the maintainer.

---

*Built with ❤️ to protect Earth's forests using open satellite data.*
