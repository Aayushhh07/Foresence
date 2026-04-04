# Foresence

Foresence is a production-grade, end-to-end deforestation monitoring web application. It monitors restricted forest zones for illegal deforestation using real Sentinel-2 satellite imagery.

It fetches satellite data every 12 hours, computes NDVI (Normalized Difference Vegetation Index) and EVI (Enhanced Vegetation Index), compares consecutive snapshots to detect vegetation loss, assigns a confidence score to each detected change, and sends email alerts when suspicious deforestation is detected. The dashboard shows live zone health, NDVI trends over time, and a change detection map.

## Project Structure
The repository is set up as a monorepo consisting of:
- `backend/` — FastAPI application managing the satellite pipeline, change detection logic, alerts, DB, and WebSockets.
- `frontend/` — React application using Vite and TailwindCSS for real-time data visualization.

---

## Local Setup Steps

### 1. Prerequisites
- **Python 3.11+**
- **Node.js 18+**
- **MongoDB** instance
- **Upstash Redis** instance
- **Cloudflare R2** bucket access
- **Copernicus Data Space** credentials
- **SendGrid API** key

### 2. Clone the Repository
```bash
git clone https://github.com/your-username/foresence.git
cd foresence
```

### 3. Backend Setup
1. **Navigate to the backend directory:**
   ```bash
   cd backend
   ```
2. **Setup virtual environment & install dependencies:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. **Configure the Environment:**
   Copy `.env.example` to `.env` and configure all the environment variables.
   ```bash
   cp .env.example .env
   ```
4. **Run the Backend locally:**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

### 4. Frontend Setup
1. **Navigate to the frontend directory:**
   ```bash
   cd ../frontend
   ```
2. **Install dependencies:**
   ```bash
   npm install --legacy-peer-deps
   ```
3. **Configure the Environment:**
   Copy `.env.example` to `.env` if not already present.
   ```bash
   cp .env.example .env
   ```
4. **Run the Frontend locally:**
   ```bash
   npm run dev
   ```
   The web app will run on `http://localhost:5173`.

---

## Environment Variables Documented

### Backend (`backend/.env`)

- `COPERNICUS_USERNAME`: Your Copernicus Data Space username, used for fetching satellite imagery.
- `COPERNICUS_PASSWORD`: Your Copernicus Data Space password.
- `MONGODB_URI`: MongoDB connection string.
- `DB_NAME`: The database name to use (default: `foresence`).
- `CLOUDFLARE_R2_ACCESS_KEY`: Access key for your Cloudflare R2 bucket.
- `CLOUDFLARE_R2_SECRET_KEY`: Secret key for your Cloudflare R2 bucket.
- `CLOUDFLARE_R2_BUCKET_NAME`: The R2 bucket name where generated images (NDVI maps, diff patches) are stored.
- `CLOUDFLARE_R2_ENDPOINT`: The API endpoint to reach R2 (e.g. `https://<account-id>.r2.cloudflarestorage.com`).
- `CLOUDFLARE_R2_PUBLIC_URL`: URL base used to serve R2 images (e.g. `https://pub-xxxx.r2.dev`).
- `UPSTASH_REDIS_URL`: URL to your Upstash Redis database, used to manage scan task distributed locks.
- `SENDGRID_API_KEY`: Key to send email alerts.
- `ALERT_FROM_EMAIL`: The verified sender email address in your SendGrid account.
- `SCAN_INTERVAL_HOURS`: Background APScheduler frequency (default `12`).
- `NDVI_DROP_THRESHOLD`: The magnitude of drop in NDVI denoting a loss of vegetation (default `0.15`).
- `CONFIDENCE_THRESHOLD`: The minimum score (0 to 1.0) necessary to declare an alert (default `0.70`).
- `CORS_ORIGINS`: Comma separated allowed origins to query the backend (e.g., `http://localhost:5173`).
- `FRONTEND_URL`: URL of the frontend (used inside emails to produce correct redirect links).

### Frontend (`frontend/.env`)

- `VITE_API_URL`: The full URL to your backend REST API (default `http://localhost:8000`).
- `VITE_WS_URL`: The full URL to your WebSocket backend for live updates (default `ws://localhost:8000`).

---

## How to Create Your First Zone

1. Ensure both your backend and frontend are running.
2. Open the frontend in your browser `http://localhost:5173`.
3. In the Map view (home page), locate the **Polygon Drawing Tool** at the top right of the map overlay.
4. Click to start drawing a polygon over a forest area you want to monitor.
5. Finish the polygon drawing by clicking the initial point again.
6. A form will appear immediately to give your zone a Name, assign alert thresholds, and provide an email list to be alerted for this sector. Fill out the details and hit **Create Zone**.
7. Go to the **Settings** view, and manually trigger a Scan for your new zone to generate the very first NDVI Snapshot baseline (it will run in the background). Over the next hours, the scheduled backend task will scan it for new imagery and issue an alert automatically if deforestation is spotted!

---

## Deployment Steps

### Backend (Render)
1. Commit and push your code to GitHub.
2. In the Render Dashboard, create a **New Web Service**.
3. Point it to your repo.
4. The deployment config is fully detailed in `backend/render.yaml`. Render can automatically pick it up if you select "Blueprint" creation. 
5. Provide all missing environment variables in the Render Dashboard when prompted.
6. Check your deployment log — once `uvicorn` fires up successfully, your service is live and APScheduler will start monitoring.

### Frontend (Vercel)
1. In the Vercel Dashboard, create a **New Project**.
2. Connect the same repository.
3. As the **Framework Preset**, choose `Vite`.
4. As the **Root Directory**, specify `frontend`.
5. Enter the **Environment Variables** (e.g., set `VITE_API_URL` and `VITE_WS_URL` to point to the secure domains of your newly deployed Render application).
6. Click **Deploy**. Vercel will install npm dependencies, build the React app, and serve your dashboard live for production.
