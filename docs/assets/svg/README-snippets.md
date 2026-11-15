# 🌊 HydroCast — Animated SVG Snippets for README

README mein in sections ke liye copy-paste karo:

---

## 1. Hero Banner (Header ke neeche, badges ke pehle)

```html
<!-- Animated Hero Banner — replaces or sits below the existing banner image -->
<p align="center">
  <img src="docs/assets/svg/hero-banner.svg" alt="HydroCast — Operational Flood Intelligence Platform, Panchganga Basin, Kolhapur" width="100%"/>
</p>
```

---

## 2. Pipeline Flow (Architecture section mein)

```html
<!-- 5-Stage Forecast Pipeline — Architecture section mein add karo -->
<p align="center">
  <img src="docs/assets/svg/pipeline-flow.svg"
       alt="HydroCast forecast pipeline: ECMWF QPF → SCS-CN Runoff → HEC-HMS Routing → ML Calibration → Flood Alert"
       width="100%"/>
</p>
```

---

## 3. Live Gauge Status (Features / Dashboard section mein)

```html
<!-- Live Gauge Status Cards -->
<p align="center">
  <img src="docs/assets/svg/gauge-status.svg"
       alt="HydroCast live gauge status: Rajaram Weir at danger 9.47m, Shivaji Bridge at warning 7.23m, Dhamani at normal 3.81m"
       width="100%"/>
</p>
```

---

## Suggested README Placement

```
<Banner Image>
<Hero SVG>          ← hero-banner.svg (animated waves + rain + title + stats)
<Badges>
---
## Architecture
<Pipeline SVG>      ← pipeline-flow.svg (hex nodes + flowing data packets)
---
## Live Dashboard
<Gauge SVG>         ← gauge-status.svg (animated water level cards)
```

---

> **Note:** GitHub renders SMIL animations in SVGs natively.
> No JavaScript required. GitHub README mein direct `<img>` tag se kaam karega.

