# HydroCast Frontend Dashboard

<p align="center">
  <img src="public/assets/hydrocast_main_banner.jpg" alt="HydroCast Operational Continuum" width="100%">
</p>

Modern, real-time hydrometric flood warning and basin intelligence dashboard built with Next.js 14 App Router, Tailwind CSS, Leaflet GIS, and WebSockets.

## Technology & Frontend Stack

| Area | Tool |
| :--- | :--- |
| **OS** | ![Linux](https://img.shields.io/badge/OS-Linux-FCC624?style=flat&logo=linux&logoColor=black) ![macOS](https://img.shields.io/badge/OS-macOS-000000?style=flat&logo=apple&logoColor=white) ![Windows](https://img.shields.io/badge/OS-Windows-0078D6?style=flat&logo=windows&logoColor=white) |
| **Languages** | ![TypeScript](https://img.shields.io/badge/Code-TypeScript_5-3178C6?style=flat&logo=typescript&logoColor=white) ![JavaScript](https://img.shields.io/badge/Code-JavaScript_ES6+-F7DF1E?style=flat&logo=javascript&logoColor=black) ![CSS3](https://img.shields.io/badge/Code-CSS3-1572B6?style=flat&logo=css3&logoColor=white) ![HTML5](https://img.shields.io/badge/Code-HTML5-E34F26?style=flat&logo=html5&logoColor=white) |
| **Frameworks** | ![Next.js](https://img.shields.io/badge/Code-Next.js_14-000000?style=flat&logo=nextdotjs&logoColor=white) ![React](https://img.shields.io/badge/Code-React_18-61DAFB?style=flat&logo=react&logoColor=black) ![Tailwind](https://img.shields.io/badge/Code-Tailwind_CSS-06B6D4?style=flat&logo=tailwindcss&logoColor=white) ![Lucide](https://img.shields.io/badge/Icons-Lucide_React-F56565?style=flat&logo=feather&logoColor=white) |
| **Visualization** | ![Leaflet](https://img.shields.io/badge/Map-Leaflet-199900?style=flat&logo=leaflet&logoColor=white) ![Chart.js](https://img.shields.io/badge/Chart-Chart.js-FF6384?style=flat&logo=chartdotjs&logoColor=white) ![Recharts](https://img.shields.io/badge/Chart-Recharts-22B5BF?style=flat&logo=d3dotjs&logoColor=white) |
| **Deployment** | ![Docker](https://img.shields.io/badge/Containers-Docker-2496ED?style=flat&logo=docker&logoColor=white) ![Vercel](https://img.shields.io/badge/Deploy-Vercel-000000?style=flat&logo=vercel&logoColor=white) ![Node.js](https://img.shields.io/badge/Runtime-Node.js_20-339933?style=flat&logo=nodedotjs&logoColor=white) ![GitHub Actions](https://img.shields.io/badge/CICD-GitHub_Actions-2088FF?style=flat&logo=githubactions&logoColor=white) |

---

## Key Features

1. **Basin Flood Overview:** Interactive Leaflet GIS map with 18 meteorological stations, river reach polylines, subbasin boundaries ($S_1 \dots S_9$), and active ultrasonic telemetry cards.
2. **Peak Flood Strike Horizon:** Real-time visual uncertainty window ($\pm 2.0\text{h}$ @ 95% CI) displaying nominal crest timestamp, earliest impact, and latest impact across CWC threshold tiers.
3. **Dual-Axis Hydrographs:** High-resolution Chart.js stage vs discharge curves for Chhatrapati Shivaji Maharaj Bridge and Rajaram K.T. Weir.
4. **2D Interactive SVG Cross-Section:** Dynamic river geometry canvas recalculating wetted area, perimeter, and conveyance discharge with an interactive water level slider.
5. **Continuous Model Verification:** Live Spearman $\rho$, NSE, and RMSE scorecards comparing simulated hydrographs against real-time ThingSpeak gauge readings.

---

## Getting Started

### Local Development

1. Install dependencies:
   ```bash
   npm install
   ```

2. Run local development server:
   ```bash
   npm run dev
   ```
   Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

3. Build production bundle:
   ```bash
   npm run build
   npm run start
   ```

### Docker Production Startup

Build and launch the lightweight, multi-stage production container:
```bash
# Standalone Docker
docker build -t hydrocast-frontend .
docker run -p 3000:3000 hydrocast-frontend

# Or via Docker Compose from root
docker compose up -d hydrocast-frontend
```

