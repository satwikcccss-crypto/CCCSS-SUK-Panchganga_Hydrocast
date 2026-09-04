# HydroCast Frontend Architecture & Design System

```
========================================================================================
             HYDROCAST NEXT.JS 14 BASIN INTELLIGENCE DASHBOARD
========================================================================================

                  Next.js 14 App Router (React 18 Server/Client Model)
                                       │
      ┌────────────────────────────────┼────────────────────────────────┐
      ▼                                ▼                                ▼
[ SWR State Engine ]          [ WebSocket Live Push ]          [ Tailwind CSS Token System ]
Cached REST revalidation      Event-driven /ws/live listener   Curated HSL Slate/Indigo/Emerald
Fallback: Standalone JSON     Auto-reconnect with backoff      Dark & Light Glassmorphic Panels
      │                                │                                │
      └────────────────────────────────┼────────────────────────────────┘
                                       ▼
                       Dashboard Shell (app/dashboard/page.tsx)
                                       │
     ┌──────────────┬──────────────┬───┴──────────┬──────────────┬──────────────┐
     ▼              ▼              ▼              ▼              ▼              ▼
[ Overview ]  [ Rainfall ]   [ Runoff/HMS ] [ Accuracy ]   [ System ]    [ FloodBanner ]
Basin GIS map  18-Station     90h Discharge  Spearman ρ     12-Step pipeline CWC threshold
Live gauges    Hyetographs    Cross-section  Gov WRD table  Latency/Logs     Emergency push
```

---

## 1. Technology Stack & Key Libraries

- **Framework:** Next.js 14.2.5 (App Router, TypeScript, React 18)
- **Styling:** Vanilla Tailwind CSS with custom color palette (no external unconfigured CSS libraries)
- **Data Visualization:** Chart.js 4.4.x, `react-chartjs-2`, and `chartjs-plugin-annotation`
- **Spatial Mapping:** Leaflet 1.9.4 & `react-leaflet` with Panchganga GeoJSON layers
- **State Management & Caching:** `swr` (Stale-While-Revalidate) with custom fetch wrappers
- **Icons & Motion:** `lucide-react` & `framer-motion`
- **Vector Graphics:** Native dynamic SVG for 2D River Cross-Section rendering

---

## 2. Component Hierarchy & Navigation Flow

The user interface is organized into five segregated operational workspaces accessible via the responsive sidebar:

```
app/
 ├── layout.tsx                     # Global HTML envelope, Inter font, metadata
 ├── page.tsx                       # Landing redirect to /dashboard
 ├── dashboard/
 │    └── page.tsx                  # Primary workspace shell & tab router
 └── api/
      └── v1/
           └── dashboard/
                └── route.ts        # Next.js API proxy serving pipeline JSON & runs
```

### 2.1 Workspace Panel Breakdown

```
+-------------------+-------------------------------------------------------------------+
| Panel ID          | Primary Functional Responsibility                                 |
+-------------------+-------------------------------------------------------------------+
| dashboard         | Basin executive overview, gauge cards, key flood KPIs, leaf map   |
| rainfall          | 18-station rainfall hyetographs, cumulative 90h bars, 90d history |
| runoff            | HEC-HMS 90-hour runoff hydrograph, peak discharge, SVG river xsec |
| accuracy          | Spearman correlation scatter, 90h prediction log, WRD records     |
| system            | 12-step pipeline orchestrator status, latency metrics, audit logs |
+-------------------+-------------------------------------------------------------------+
```

---

## 3. Data Visualization Architecture (Chart.js Engine)

All charts are engineered with strict hydrologic conventions, high-DPI canvas rendering, and custom tooltip formatting.

### 3.1 Dual-Axis Stage vs Discharge Hydrograph (`RunoffPanel` & `AccuracyPanel`)
- **Left Y-Axis ($y_{stage}$):** River stage in meters MSL ($530.0 - 546.0\text{m}$).
- **Right Y-Axis ($y_Q$):** River discharge in $m^3/s$ ($0 - 4,000\text{ m}^3/s$).
- **Threshold Annotations:**
  - **Alert Level:** $542.10\text{ m}$ (Yellow dashed horizontal line)
  - **Warning Level:** $542.70\text{ m}$ (Orange dashed horizontal line)
  - **Danger Level:** $543.30\text{ m}$ (Red dashed horizontal line)
  - **HFL:** $545.33\text{ m}$ (Purple dashed horizontal line)

### 3.2 Inverted Meteorological Hyetographs (`RainfallPanel`)
- Rainfall bars are plotted with an inverted vertical axis ($0\text{ mm}$ at the top, increasing downward) adhering to standard international civil engineering hydrologic conventions.

### 3.3 Spearman Correlation Scatter Plot & Target Accuracy Panel (`AccuracyPanel.tsx`)
- **Filtered Coordinate Array (`validPts`):** Coordinates are sanitized to ensure both $x$ and $y$ are finite numbers, preventing `NaN` from disrupting Chart.js canvas layout.
- **Plots the theoretical $1:1$ ideal agreement line ($Y = X$) in dashed slate.**
- **Live Empirical Badges:** Displays actual Spearman rank coefficient ($\rho$) and Pearson $R^2$ with safe null-fallback (`—`).
- **Interactive Tooltip Readouts:** Displays Observed stage ($m$ and raw $ft$), Predicted stage ($m$), and error delta $\Delta H$ ($m$).
- **Elapsed-Only Observed Hydrograph Curve:** In the 90-hour comparison hydrograph, observed telemetry is plotted only for elapsed lead hours ($T+0\text{h} \dots T+16\text{h}$), leaving unreached lead hours open until real-time telemetry arrives.
- **Dual-Unit Hourly Prediction Log Table:**
  - Lead time ($+0\text{h} \to +89\text{h}$)
  - Raw ultrasonic sensor distance in feet (e.g. `52.95 ft`)
  - Shivaji predicted stage ($m$ MSL) and discharge ($m^3/s$)
  - Rajaram K.T. Weir stage ($m$ MSL)
  - Observed water level ($m$ MSL)
  - Error delta in dual units (e.g. `+0.030m (+0.10ft)`)
  - 1-click CSV Export including raw feet observations.
- **Continuous 90h Lifecycle Progress Card:** Visual progress bar and badge tracking verified hours (e.g., `17/90h (18.9%) · IN_PROGRESS`).

```
     Predicted Stage (m MSL)
  545 +                                     /  <-- 1:1 Ideal Line (Y = X)
      |                                  * /
  543 +                              *  * /    * = Validated Forecast Points
      |                            *  *  /     Points cluster tightly along
  540 +                       *  *  *  /       the line demonstrating
      |                     *  *  *   /        high predictive fidelity
  535 +                *  *  *       /
      |              *  *           /
  532 +---------*--*---------------/
      +---------+---------+---------+---------+
     532       535       540       543       545  Observed Stage (m MSL)
```

---

## 4. 2D River Cross-Section SVG Renderer (`CrossSectionViewer.tsx`)

The cross-section viewer renders a direct 2D geometric elevation slice of the Panchganga river channel using native scalable vector graphics:

```
  Top of Left Bank (LOB)                                      Top of Right Bank (ROB)
       \                                                               /
        \     Water Surface Elevation (WSE = 533.28m MSL)             /
         \~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~/
          \          Wetted Flow Area A (m²)                        /
           \                                                       /
            \_____________________________________________________/
                       Main Channel Bed Invert (530.18m MSL)
```

### Key Interactive Features:
1. **Dynamic Water Level Slider:** Allows hydraulic engineers to manually scrub the water surface elevation from $530.18\text{m}$ to $546.00\text{m}$ to observe simulated floodplain inundation in real time.
2. **Instant Hydraulic Readouts:** Automatically recalculates and displays:
   - Wetted Flow Area $A$ ($m^2$)
   - Wetted Perimeter $P$ ($m$)
   - Hydraulic Radius $R = A/P$ ($m$)
   - Conveyance Discharge $Q$ ($m^3/s$)
3. **Site Selector:** Instantly switches between **Chhatrapati Shivaji Maharaj Bridge** and **Rajaram K.T. Weir**.

---

## 5. State Synchronization, SWR & Vercel Serverless Architecture

Data fetching is wrapped through the client abstraction [`lib/api.ts`](file:///e:/hydrocast_complete/frontend/lib/api.ts):

```typescript
export async function fetchDashboardData(runId?: string) {
  const query = runId ? `?run_id=${encodeURIComponent(runId)}` : "";
  const url = typeof window !== "undefined" 
    ? `/api/v1/dashboard${query}` 
    : `${BASE}/api/v1/dashboard${query}`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error("API route response not ok");
  return await res.json();
}
```

### 5.1 Vercel Serverless Edge Bundling
On Vercel, serverless function workers execute isolated from external project folders (`../data/runs/` is not packaged). To guarantee 100% production reliability:
- All historical computation runs (`CYC_*.json`) and `runs_index.json` are mirrored into [`frontend/public/data/runs/`](file:///e:/hydrocast_complete/frontend/public/data/runs/).
- When `/api/v1/dashboard?run_id=...` is called, the serverless handler resolves `path.join(process.cwd(), "public", "data", "runs", `${requestedRunId}.json`)`, instantly serving the archived run without 404s or empty metrics.

### 5.2 Hydration Exception Hardening
All metric formatters in [`AccuracyPanel.tsx`](file:///e:/hydrocast_complete/frontend/components/AccuracyPanel.tsx) and [`SystemPanel.tsx`](file:///e:/hydrocast_complete/frontend/components/SystemPanel.tsx) are safely guarded:
```tsx
ρ = {spearmanRho != null ? spearmanRho.toFixed(3) : "—"} · R² = {pearsonR2 != null ? pearsonR2.toFixed(3) : "—"}
```
This prevents `TypeError: Cannot read properties of null (reading 'toFixed')` during initial hydration or when inspecting runs with incomplete lead hours.

