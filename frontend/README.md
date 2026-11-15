# TradeCraft Frontend

Modern, high-performance web interface for the **TradeCraft AI Competitive Intelligence & Proposal Engine**. Built with React 19, Vite, Tailwind CSS, and Lucide React.

---

## 🚀 Live Deployment

- **Production URL**: **[https://trade-craft-sage.vercel.app](https://trade-craft-sage.vercel.app)**
- **Login Page**: **[https://trade-craft-sage.vercel.app/login](https://trade-craft-sage.vercel.app/login)**
- **Production API**: `https://tradecraft-xax5.onrender.com`

### Demo Credentials
- **Email**: `admin@tradecraft.com`
- **Password**: `admin`

---

## Features

- **Executive Intelligence Dashboard**: Real-time KPI cards, competitor timeline, and activity streams.
- **Competitor & Source Management**: Configure competitor profiles and RSS/HTML monitoring sources.
- **Interactive Unified Diff Viewer**: Side-by-side and line-by-line diffs showing verbatim competitor adjustments.
- **AI Findings & EGA Badges**: Grounding scores with verbatim character-offset citations.
- **Strategic Proposal Engine**: 7-Section proposal previewer, markdown editor, and isolated PDF export.

---

## Local Development Setup

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Configure Environment

Create `.env` in the `frontend/` directory (optional for local dev; defaults to `http://localhost:8001`):

```ini
VITE_API_URL=http://localhost:8001
```

For connecting to the cloud backend:
```ini
VITE_API_URL=https://tradecraft-xax5.onrender.com
```

### 3. Start Development Server

```bash
npm run dev
```

Server starts at `http://localhost:5173`.

---

## Production Build & Deployment

```bash
# Build production bundle
npm run build

# Preview production build locally
npm run preview
```

### Vercel Deployment Settings
- **Framework Preset**: `Vite`
- **Root Directory**: `frontend`
- **Build Command**: `npm run build`
- **Output Directory**: `dist`
- **Environment Variable**: `VITE_API_URL=https://tradecraft-xax5.onrender.com`
