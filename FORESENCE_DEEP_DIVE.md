# 🌿 Foresence — Technical Architecture & Deep Dive Guide

Welcome to the **Foresence Deep Dive**. This document is designed to give you a complete, expert-level understanding of the Foresence codebase, its math, its data pipelines, and its architectural components. By reading this guide, you will understand how the system works from the satellite in space down to the pixels on the user's dashboard.

---

## 🔍 1. Current Architecture Verification Status

To ensure that the backend, database, cache, and satellite imagery integrations are functional, we executed a suite of connectivity tests. Here are the live results:

| Component | Tested Endpoint / Parameter | Status | Details |
| :--- | :--- | :---: | :--- |
| **MongoDB Atlas** | DB Ping & Collections Lookup | **🟢 SUCCESS** | Connected successfully. Found collections: `zones`, `alerts`, `ndvi_snapshots`, `system.buckets.ndvi_snapshots`. |
| **Upstash Redis** | Cache Ping Command | **🟢 SUCCESS** | Connected successfully. Redis responded to ping: `True`. |
| **STAC Satellite Catalog** | Element84 STAC Search API | **🟢 SUCCESS** | Catalog reachable. Latest Sentinel-2 scene found: `S2C_T43PFP_20260520T053444_L2A` (May 20, 2026). Cloud cover: 62.5%. |
| **Copernicus Data Space** | OAuth2 Token & OData API Query | **🟢 SUCCESS** | Credentials authorized. Token refreshed. Latest scene found: `S2C_MSIL2A_20260520T051651...` (May 20, 2026). |

> **Note:** All core integration points are healthy and operational. The app will successfully connect to external catalogs, query images, write time-series data to MongoDB, and maintain lock states in Redis.

---

## 🗺️ 2. Core Features of Foresence

Foresence is a complete, automated monitoring solution offering:
1. **Interactive Geographic Monitoring**: Draw and manage custom forest zones (polygons) on a Leaflet map.
2. **Dual-Source Satellite Retrieval**: Connects to two major catalogs (Element84 STAC and Copernicus) to query Sentinel-2 L2A images.
3. **Efficient Cloud-Optimized Tiff (COG) Streaming**: Streams only the specific pixels covering the drawn polygon, saving gigabytes of bandwidth.
4. **Biophysical Indices Math**: Computes NDVI (Normalized Difference Vegetation Index) and EVI (Enhanced Vegetation Index) at pixel scale.
5. **Pixel-Level Deforestation Alerts**: Compares current indices against baseline values to detect canopy drops, calculate affected hectares, and rate severity.
6. **Multi-Channel Alert Dispatch**: Broadcasts real-time WebSocket alerts, sends responsive SendGrid HTML emails, and dispatches JSON webhooks.
7. **Time-Series Vegetation Analytics**: Renders trend lines and loss charts over time.

---

## 🏗️ 3. System Architecture & Data Flow

Foresence uses a decoupled, event-driven architecture. The diagram below illustrates how a single scan job executes, processes satellite data, and broadcasts results:

```
[Space: Sentinel-2 Satellite]
            │
            ▼
┌──────────────────────────────┐       ┌──────────────────────────────┐
│  Element84 STAC Catalog API  │       │  Copernicus Data Space API   │
│  (Primary: Streams COG TIFs) │       │  (Fallback: Downloads ZIP)   │
└──────────────┬───────────────┘       └──────────────┬───────────────┘
               │                                      │
               └───────────────────┬──────────────────┘
                                   │
                                   ▼
                   ┌──────────────────────────────┐
                   │    Backend Scan Scheduler    │
                   │    (jobs.py / APScheduler)   │
                   └──────────────┬───────────────┘
                                   │
                                   ▼
                   ┌──────────────────────────────┐
                   │   Sentinel & NDVI Service    │
                   │   (rasterio clips & NDVI)    │
                   └──────────────┬───────────────┘
                                   │
         ┌─────────────────────────┴─────────────────────────┐
         ▼                                                   ▼
┌──────────────────────────────┐                   ┌──────────────────────────────┐
│       MongoDB Database       │                   │    Local /static or R2       │
│  (Timeseries snapshots &     │                   │  (Stores NDVI PNG and        │
│   active monitoring zones)   │                   │   Change detection maps)     │
└──────────────┬───────────────┘                   └──────────────────────────────┘
               │
               ▼
┌──────────────────────────────┐
│   Change Detection Service   │
│ (Evaluates NDVI delta & ha)  │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│        Alert Service         │
│ (Triggers if thresholds met) │
└──────────────┬───────────────┘
               │
         ┌─────┼─────────────────────────┐
         ▼     ▼                         ▼
┌───────────┐ ┌───────────┐         ┌───────────┐
│ WebSocket │ │ SendGrid  │         │ Outbound  │
│ Broadcast │ │ HTML Mail │         │ Webhook   │
└─────┬─────┘ └───────────┘         └───────────┘
      │
      ▼
┌──────────────────────────────┐
│    React Frontend Client     │
│  (Toast alert + update map)  │
└──────────────────────────────┘
```

---

## 📡 4. How Foresence Captures Images (Satellite Pipeline)

Foresence queries **Sentinel-2 L2A (Bottom of Atmosphere)** images. It implements a primary pipeline and a fallback mechanism in [sentinel_service.py](file:///backend/app/services/sentinel_service.py):

### A. Primary Method: Element84 STAC (Cloud Optimized GeoTIFF)
This is the most advanced, fast, and resource-efficient method:
1. **Catalog Query**: The backend uses `pystac-client` to search the public `sentinel-2-c1-l2a` catalog on AWS. It uses the bounding box (bbox) of the zone's polygon and a date range.
2. **Cloud Cover Filtering**: It filters out items with $>80\%$ cloud cover and selects the most recent scene.
3. **Windowed Download (COG)**:
   - Instead of downloading the full satellite scene (which is $100 \text{ km} \times 100 \text{ km}$ and size $\approx 1\text{GB}$), it reads the remote Cloud Optimized GeoTIFF (COG) URLs for **Band 2 (Blue)**, **Band 4 (Red)**, and **Band 8 (Near-Infrared)**.
   - Using `rasterio`, the service transforms the zone's WGS84 coordinates into the coordinate system of the raster (usually UTM).
   - It performs a windowed read, streaming **only** the pixels that fall within the zone's boundaries.
   - This reduces download size from $1\text{GB}$ to just a few kilobytes!

### B. Fallback Method: Copernicus Data Space (OData API)
If the STAC catalog fails or does not contain recent images, the backend falls back to Copernicus:
1. **OAuth2 Authentication**: Fetches an access token using `COPERNICUS_USERNAME` and `COPERNICUS_PASSWORD`.
2. **Metadata Search**: Searches the Copernicus catalogue using an OData filter for Sentinel-2 L2A products intersecting the zone WKT with cloud cover $<30\%$.
3. **Full ZIP Download**: Downloads the complete ZIP archive containing the product.
4. **File Extraction**: Extracts only the 10-meter resolution files matching `_B02_10m.jp2` (Blue), `_B04_10m.jp2` (Red), and `_B08_10m.jp2` (NIR) into a temporary directory.

---

## 🧮 5. How Foresence Analyzes Imagery (Spectral Mathematics)

Once the bands are saved, [ndvi_service.py](file:///backend/app/services/ndvi_service.py) takes over.

### A. Normalization
Sentinel-2 L2A products scale reflectance integers. Foresence divides the digital numbers (DN) by `10000.0` to convert them to actual surface reflectance values ranging from `0` to `1`.
$$\text{Reflectance} = \frac{\text{DN}}{10000.0}$$

### B. Math Formulas
Foresence computes two primary vegetation indices:

#### 1. NDVI (Normalized Difference Vegetation Index)
NDVI measures chlorophyll absorption of red light and high reflectance of near-infrared light. Values range from $-1$ to $+1$. Healthy dense forest stands typically fall between $0.6$ and $0.9$.
$$\text{NDVI} = \frac{\text{NIR} - \text{Red}}{\text{NIR} + \text{Red}} = \frac{\text{Band 8} - \text{Band 4}}{\text{Band 8} + \text{Band 4}}$$

#### 2. EVI (Enhanced Vegetation Index)
EVI is more sensitive in high biomass regions (dense forest canopy) and corrects for atmospheric influences and soil background noise using the Blue band.
$$\text{EVI} = 2.5 \times \frac{\text{NIR} - \text{Red}}{\text{NIR} + 6.0 \times \text{Red} - 7.5 \times \text{Blue} + 1.0}$$

```python
# NumPy implementation in ndvi_service.py
ndvi = np.where((nir + red) != 0, (nir - red) / (nir + red), np.nan)
evi = np.where(denom != 0, 2.5 * (nir - red) / (nir + 6.0 * red - 7.5 * blue + 1.0), np.nan)
```

### C. Cloud Cover Masking
Clouds skew indices. Foresence estimates cloud cover by evaluating the **Blue band (Band 2)**. Since clouds are highly reflective, pixels where the blue reflectance exceeds `0.3` ($30\%$) are classified as clouds:
$$\text{Cloud Mask} = \text{Blue reflectance} > 0.3$$
The ratio of cloudy valid pixels to total valid pixels gives the cloud cover percentage.

---

## 📈 6. Change Detection & Forest Loss Mathematics

In [change_detection.py](file:///backend/app/services/change_detection.py), the current scan results are compared to the historical baseline:

### A. Pixel-Level Change Mask
Deforestation is identified where a pixel's current NDVI is significantly lower than the historical average NDVI of the zone.
$$\text{Loss Mask} = \text{Current NDVI} < (\text{Previous Zone NDVI Mean} - \text{NDVI Drop Threshold})$$

### B. Estimating Affected Hectares
To calculate the physical area of forest loss:
1. The resolution of the pixels is obtained from the raster affine transformation matrix:
   $$\text{Pixel Width} = |a| , \quad \text{Pixel Height} = |e|$$
2. If the Coordinate Reference System (CRS) is in degrees (e.g., EPSG:4326), the resolution is converted to meters:
   $$\text{Width in meters} = \text{Pixel Width} \times 111,320 \text{ meters/degree}$$
3. The pixel area in hectares ($1 \text{ ha} = 10,000 \text{ m}^2$) is:
   $$\text{Pixel Area (ha)} = \frac{\text{Width (m)} \times \text{Height (m)}}{10000.0}$$
4. The total affected area is the count of loss pixels multiplied by the pixel area:
   $$\text{Affected Area (ha)} = \text{Loss Pixel Count} \times \text{Pixel Area (ha)}$$

### C. Confidence and Severity Formulas

#### Confidence
Confidence represents the mathematical probability that the drop in greenness is due to tree loss rather than clouds, smoke, or sensor noise:
$$\text{Raw Confidence} = \min\left(1.0, \frac{|\Delta\text{NDVI}|}{0.4} \times 0.7 + \frac{\text{Affected Area Ratio}}{0.3} \times 0.3\right)$$
$$\text{Confidence} = \max\left(0.0, \text{Raw Confidence} - \frac{\text{Cloud Cover \%}}{100.0} \times 0.5\right)$$

#### Severity
Based on the magnitude of the NDVI drop:
* **Critical**: $\Delta\text{NDVI} \le -0.35$
* **High**: $-0.35 < \Delta\text{NDVI} \le -0.25$
* **Medium**: $-0.25 < \Delta\text{NDVI} \le -0.15$
* **Low**: $-0.15 < \Delta\text{NDVI}$

---

## ⏱️ 7. Frequency & Execution Flow of Analysis

Scans are scheduled or manually triggered:
1. **Automatic Interval**: The backend schedules `run_all_zone_scans` to run every **12 hours** (determined by `SCAN_INTERVAL_HOURS` in `.env`).
2. **Historical Seeding (On Creation)**:
   - When a user creates a new zone, the scheduler queues `seed_historical_zone_data(zone_id)` in the background.
   - It triggers two historical scans:
     - **Pass 1 (`hist_base`)**: Searches images between 30 and 15 days ago to establish baseline greenness.
     - **Pass 2 (`hist_curr`)**: Searches images from the last 15 days, runs change detection against the baseline, and generates alerts if deforestation has occurred.
3. **Manual Trigger**: Users can trigger an immediate scan via the map popup or `/api/zones/{id}/scan`.

---

## 🔔 8. How Alerts are Sent (Notification Channels)

When an alert triggers, [alert_service.py](file:///backend/app/services/alert_service.py) dispatches notifications:

### A. Database Storage
The alert is written to the `alerts` collection. The zone's overall `health_score` is lowered by the NDVI delta, and its status changes to `warning` or `critical`.

### B. WebSocket Real-Time Broadcast
All browsers connected to the WebSocket route `/ws/alerts` receive a JSON event. The frontend reactively pops up a toast notification and updates maps and tables without page refreshes.

### C. SendGrid HTML Email Templates
An email with the alert details is formatted using HTML and dispatched via SendGrid to the emails configured for the zone:
- Displays a color-coded header matching the severity (e.g., Red for Critical).
- Shows key stats: affected area in hectares, confidence, and NDVI change.
- Renders the **Change Detection Map** image.
- Includes a button linking back to the dashboard.

### D. Outbound Webhook POST Requests
If the zone has a `webhook_url`, the server POSTs a JSON payload detailing the event, allowing integrations with external systems like Slack or automated SMS services.

---

## 🔌 9. API Reference

All HTTP responses return standard envelopes:
```json
{
  "success": true,
  "data": { ... },
  "message": "Human readable description"
}
```

### Key REST Endpoints

| Method | Endpoint | Description | Payloads / Parameters |
| :--- | :--- | :--- | :--- |
| **GET** | `/api/zones` | List all zones | None |
| **POST** | `/api/zones` | Create a new zone | GeoJSON Polygon, thresholds, alert emails |
| **PUT** | `/api/zones/{id}` | Update settings | Thresholds, active toggle, emails |
| **DELETE** | `/api/zones/{id}` | Delete zone & alerts | None |
| **POST** | `/api/zones/{id}/scan` | Trigger manual scan | Sync/Async satellite scan |
| **GET** | `/api/alerts` | List alerts | Query filters: `zone_id`, `severity`, `status` |
| **PUT** | `/api/alerts/{id}/status` | Update alert state | `{ "status": "acknowledged" \| "resolved", "notes": "" }` |
| **GET** | `/api/snapshots` | List NDVI snapshots | Query filters: `zone_id`, `start_date`, `end_date` |
| **GET** | `/api/health` | Health Check | Status of DB, Redis, and Scheduler |

---

## 🗄️ 10. Database Schema (MongoDB Atlas)

### A. Collection: `zones`
Represents the forest regions being monitored.
```json
{
  "_id": "ObjectId",
  "name": "Western Ghats Reserve",
  "description": "Biodiversity hotspot",
  "geojson": {
    "type": "Polygon",
    "coordinates": [[[76.5, 11.8], [76.9, 11.8], [76.9, 12.2], [76.5, 12.2], [76.5, 11.8]]]
  },
  "area_ha": 425.3,
  "ndvi_drop_threshold": 0.15,
  "confidence_threshold": 0.70,
  "alert_emails": ["ranger@forest.gov"],
  "webhook_url": "https://hooks.mycompany.com/deforestation",
  "health_score": 100,
  "status": "healthy",
  "active": true,
  "created_at": "2026-05-21T06:00:00Z",
  "last_scanned_at": "2026-05-21T06:10:00Z"
}
```

### B. Collection: `alerts`
Stores records of detected deforestation.
```json
{
  "_id": "ObjectId",
  "zone_id": "603f...",
  "zone_name": "Western Ghats Reserve",
  "detected_at": "2026-05-21T06:10:00Z",
  "ndvi_before": 0.78,
  "ndvi_after": 0.45,
  "ndvi_delta": -0.33,
  "evi_before": 0.68,
  "evi_after": 0.38,
  "change_area_ha": 18.4,
  "confidence": 0.89,
  "severity": "high",
  "change_map_url": "http://localhost:8000/static/changes/603f.../scan123.png",
  "status": "new",
  "notified": true,
  "notified_at": "2026-05-21T06:10:05Z",
  "notes": ""
}
```

---

## 💻 11. Developer Guide: How to Extend the System

### Adding a New Vegetation Index (e.g., SAVI)
If you want to add the **Soil-Adjusted Vegetation Index (SAVI)** to improve accuracy in sparse vegetation areas:

1. **Add math to [ndvi_service.py](file:///backend/app/services/ndvi_service.py)**:
   ```python
   def compute_savi(nir: np.ndarray, red: np.ndarray, L: float = 0.5) -> np.ndarray:
       """Compute SAVI = ((NIR - Red) / (NIR + Red + L)) * (1 + L)"""
       with np.errstate(divide="ignore", invalid="ignore"):
           denom = nir + red + L
           savi = np.where(denom != 0, ((nir - red) / denom) * (1.0 + L), np.nan)
       return np.clip(savi, -1.0, 1.0)
   ```
2. **Update the execution pipeline** in `compute_ndvi_for_zone`:
   - Compute the array: `savi = compute_savi(nir_arr, red_arr)`
   - Calculate the mean: `savi_mean = float(np.nanmean(savi))`
   - Include it in the return dict.
3. **Update models** in `app/models/snapshot.py` to include `savi_mean` as an optional float field so it is validated and stored in MongoDB.

---

### Pro-Tips for Debugging & Maintenance
* **Bypassing Satellite Downloads**: When testing locally, you can use the **Demo Seed Endpoint** (`POST /api/demo/seed`) to populate mock historical databases and trigger mock notifications.
* **Storage Provider Fallback**: If `CLOUDFLARE_R2_ACCESS_KEY` is not set, files automatically save locally to the `backend/static/` directory and are served from `http://localhost:8000/static/`.
* **Lock Issues**: If a scan gets stuck, delete the Redis lock key manually via Redis CLI or flush Upstash keys: `DEL zone_lock:<zone_id>`.

---
*Document prepared for the Foresence Core Team. Happy Coding!*
