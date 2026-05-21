# Deployment Guide — Render (Backend) + Vercel (Frontend)

Follow this checklist **in order**. Do not skip steps marked **required**.

| Service | Host | URL pattern |
|---------|------|-------------|
| Backend API | Render | `https://foresence-api.onrender.com` |
| Frontend | Vercel | `https://your-project.vercel.app` |
| Database | MongoDB Atlas | (connection string only) |

---

## Before you start

### 1. Gather credentials (copy from local `backend/.env`)

| Variable | Required for prod? | Where to get it |
|----------|-------------------|-----------------|
| `MONGODB_URI` | **Yes** | [MongoDB Atlas](https://cloud.mongodb.com) |
| `UPSTASH_REDIS_URL` | Recommended | [Upstash](https://upstash.com) — use `rediss://` URL |
| `COPERNICUS_USERNAME` / `PASSWORD` | For real scans | [Copernicus Data Space](https://dataspace.copernicus.eu) |
| `CLOUDFLARE_R2_*` | For image URLs | [Cloudflare R2](https://dash.cloudflare.com) |
| `SENDGRID_API_KEY` | For emails | [SendGrid](https://sendgrid.com) |
| `ALERT_FROM_EMAIL` | With SendGrid | Verified sender in SendGrid |

### 2. MongoDB Atlas — allow Render

1. Atlas → **Network Access** → **Add IP Address** → **Allow Access from Anywhere** (`0.0.0.0/0`)  
   (Render uses dynamic IPs; for stricter security use Atlas VPC peering later.)

### 3. Push deployment files to GitHub

Ensure these files exist in your repo (already added in this project):

```
Foresence/
├── render.yaml              ← Render Blueprint (repo root)
├── DEPLOYMENT.md            ← this file
├── backend/
│   ├── Dockerfile
│   ├── .dockerignore
│   └── .env.example
└── frontend/
    ├── vercel.json          ← SPA routing for React Router
    └── .env.example
```

```bash
git add render.yaml DEPLOYMENT.md backend/.dockerignore backend/Dockerfile frontend/vercel.json
git commit -m "chore: add Render and Vercel deployment config"
git push origin main
```

---

## Part A — Deploy backend on Render

### Step A1 — Create Render account

1. Go to [render.com](https://render.com) and sign up (GitHub login recommended).

### Step A2 — New Blueprint from GitHub

1. **Dashboard** → **New** → **Blueprint**.
2. Connect your **GitHub** account and select the **Foresense** repository.
3. Render should detect `render.yaml` at the **repository root** (`Foresence/render.yaml`).
4. Click **Apply** (do not deploy yet if it asks to confirm env vars).

> If your GitHub repo root is the parent folder `Deforesense/` (not `Foresence/`), set Blueprint path to `Foresence/render.yaml` in Render, or move `render.yaml` to match your repo root.

### Step A3 — Set environment variables on Render

Open the **foresence-api** service → **Environment** → add every variable below.

**Required**

| Key | Example / notes |
|-----|-----------------|
| `MONGODB_URI` | `mongodb+srv://user:pass@cluster.mongodb.net/` |
| `DB_NAME` | `foresence` |
| `CORS_ORIGINS` | `https://YOUR-PROJECT.vercel.app` (update after Vercel deploy) |
| `FRONTEND_URL` | Same as your Vercel URL |

**Recommended**

| Key | Example / notes |
|-----|-----------------|
| `UPSTASH_REDIS_URL` | `rediss://default:xxx@xxx.upstash.io:6380` |
| `COPERNICUS_USERNAME` | Your Copernicus email |
| `COPERNICUS_PASSWORD` | Your Copernicus password |
| `CLOUDFLARE_R2_ACCESS_KEY` | R2 API token |
| `CLOUDFLARE_R2_SECRET_KEY` | R2 API secret |
| `CLOUDFLARE_R2_BUCKET_NAME` | `foresence-images` |
| `CLOUDFLARE_R2_ENDPOINT` | `https://ACCOUNT_ID.r2.cloudflarestorage.com` |
| `CLOUDFLARE_R2_PUBLIC_URL` | `https://pub-xxxx.r2.dev` |
| `SENDGRID_API_KEY` | `SG.xxxx` |
| `ALERT_FROM_EMAIL` | Verified sender email |

**Optional (defaults in `render.yaml`)**

| Key | Value |
|-----|-------|
| `APP_MODE` | `prod` |
| `ENABLE_DEMO_ROUTES` | `true` (enables **Seed Demo Data** button) |
| `ENABLE_PREDEFINED_ZONES` | `false` |
| `SCAN_INTERVAL_HOURS` | `12` |
| `NDVI_DROP_THRESHOLD` | `0.15` |
| `CONFIDENCE_THRESHOLD` | `0.70` |

**Temporary CORS (if Vercel URL unknown yet)**

Set both to a placeholder, deploy Vercel, then update:

```
CORS_ORIGINS=https://foresense.vercel.app
FRONTEND_URL=https://foresense.vercel.app
```

Use your **actual** Vercel URL (including custom domain if any). Multiple origins: comma-separated, no spaces:

```
CORS_ORIGINS=https://foresense.vercel.app,https://foresense-git-main-you.vercel.app
```

### Step A4 — Deploy

1. **Manual Deploy** → **Deploy latest commit** (or wait for auto-deploy).
2. First Docker build may take **10–20 minutes** (GDAL + rasterio).
3. When live, copy your service URL, e.g. `https://foresence-api.onrender.com`.

### Step A5 — Verify backend

Open in browser:

| URL | Expected |
|-----|----------|
| `https://YOUR-API.onrender.com/` | JSON with `"name": "Foresence API"` |
| `https://YOUR-API.onrender.com/api/health` | `"status": "healthy"` or degraded with details |
| `https://YOUR-API.onrender.com/docs` | Swagger UI |

**Cold start:** Free/starter plans sleep after ~15 min idle. First request may take 30–60s.

**Scheduler note:** On free tier, the app may sleep and **miss scheduled 12h scans**. For production monitoring, use a **paid** Render plan (always-on).

---

## Part B — Deploy frontend on Vercel

### Step B1 — Create Vercel account

1. Go to [vercel.com](https://vercel.com) → sign up with **GitHub**.

### Step B2 — Import project

1. **Add New** → **Project** → import the same GitHub repo.
2. **Root Directory:** click **Edit** → set to `frontend`  
   (if repo root is `Foresence`, use `Foresence/frontend`).
3. **Framework Preset:** Vite (auto-detected).
4. **Build Command:** `npm run build` (default).
5. **Output Directory:** `dist` (default).

`vercel.json` in `frontend/` already configures SPA rewrites for React Router.

### Step B3 — Environment variables (required before first deploy)

In Vercel → **Settings** → **Environment Variables**, add for **Production** (and Preview if you want):

| Name | Value |
|------|--------|
| `VITE_API_URL` | `https://foresence-api.onrender.com` (your Render URL, **no trailing slash**) |
| `VITE_WS_URL` | `wss://foresence-api.onrender.com` (**wss**, not ws) |

> Vite bakes these in at **build time**. Changing them requires **Redeploy**.

### Step B4 — Deploy

1. Click **Deploy**.
2. Wait for build (~1–2 min).
3. Copy production URL, e.g. `https://foresense.vercel.app`.

### Step B5 — Update Render CORS (critical)

1. Render → **foresence-api** → **Environment**.
2. Update:
   ```
   CORS_ORIGINS=https://foresense.vercel.app
   FRONTEND_URL=https://foresense.vercel.app
   ```
   Add preview URLs if needed (comma-separated).
3. **Save** → Render will redeploy automatically.

### Step B6 — Redeploy Vercel (if you changed API URL)

If you fixed `VITE_*` after first deploy:

1. Vercel → **Deployments** → **⋯** → **Redeploy** (use existing env).

---

## Part C — End-to-end verification

| Check | How |
|-------|-----|
| API reachable | Open `VITE_API_URL/api/health` in browser |
| Frontend loads | Open Vercel URL |
| Map / zones | Seed demo data or create zone |
| WebSocket | Status bar shows connected; browser DevTools → Network → WS to `wss://.../ws/alerts` |
| No CORS errors | Browser console clean on API calls |
| Demo seed | Header **Seed Demo Data** (needs `ENABLE_DEMO_ROUTES=true` on Render) |

---

## Quick reference — URL wiring

```
Browser (Vercel)
    │
    ├─ HTTPS  VITE_API_URL  ──────►  Render  /api/*
    │
    └─ WSS    VITE_WS_URL   ──────►  Render  /ws/alerts

Render
    ├─ MONGODB_URI  ──►  MongoDB Atlas
    ├─ UPSTASH_REDIS_URL  ──►  Upstash (optional)
    └─ CORS_ORIGINS  must include exact Vercel origin(s)
```

---

## Common mistakes

| Mistake | Fix |
|---------|-----|
| `VITE_WS_URL` uses `ws://` in production | Use **`wss://`** |
| Trailing slash on `VITE_API_URL` | Remove trailing `/` |
| CORS errors | `CORS_ORIGINS` must match Vercel URL **exactly** (scheme + host) |
| WebSocket fails | Render web service supports WS; check `wss` and firewall |
| `api/health` database down | MongoDB IP whitelist + correct `MONGODB_URI` |
| Demo seed 404 | Set `ENABLE_DEMO_ROUTES=true` or `APP_MODE=demo` on Render |
| Scans never run | Free Render sleeps; upgrade plan or trigger manual scan |
| Env changed on Vercel but app unchanged | **Redeploy** Vercel after changing `VITE_*` |
| Wrong Root Directory on Vercel | Must be `frontend` (or `Foresence/frontend`) |
| Blueprint not found | `render.yaml` must be at repo root Render uses |

---

## Custom domain (optional)

**Vercel:** Project → **Settings** → **Domains** → add domain → update `CORS_ORIGINS` and `FRONTEND_URL` on Render.

**Render:** Service → **Settings** → **Custom Domain** → add API subdomain → update `VITE_API_URL` / `VITE_WS_URL` on Vercel → redeploy frontend.

---

## Minimal deploy (demo only)

If you only need the dashboard with **demo data** (no Copernicus/R2):

**Render**

```
MONGODB_URI=<atlas-uri>
DB_NAME=foresence
APP_MODE=demo
ENABLE_DEMO_ROUTES=true
CORS_ORIGINS=https://YOUR.vercel.app
FRONTEND_URL=https://YOUR.vercel.app
```

**Vercel**

```
VITE_API_URL=https://YOUR-API.onrender.com
VITE_WS_URL=wss://YOUR-API.onrender.com
```

---

## Support links

- [Render Docker deploy](https://render.com/docs/docker)
- [Render environment variables](https://render.com/docs/environment-variables)
- [Vercel environment variables](https://vercel.com/docs/projects/environment-variables)
- [Vite env variables](https://vitejs.dev/guide/env-and-mode.html)
