---
title: "02 · Rainfall-to-Alert Dataflow"
---

# 02 · Rainfall-to-Alert Dataflow

<div class="hydrocast-diagram-card">
  <div class="hydrocast-diagram-header">
    <div class="hydrocast-diagram-title">
      <span class="hydrocast-diagram-badge">Interactive Console</span>
      <strong>5-Lane Sequential Dataflow Pipeline</strong>
    </div>
    <div class="hydrocast-diagram-actions">
      <a class="hydrocast-diagram-btn" href="../../diagrams/02-dataflow.html" target="_blank" rel="noopener">Open Fullscreen ↗</a>
    </div>
  </div>
  <iframe class="hydrocast-diagram-frame" src="../../diagrams/02-dataflow.html?embed=1" title="02 · Rainfall-to-Alert Dataflow"></iframe>
</div>

## Description & System Role

End-to-end dataflow pipeline from ECMWF IFS GRIB2 precipitation forcing, spatial centroid mapping, SCS loss, unit hydrograph transform, Muskingum channel routing, to CWC/DDMA alert bulletin generation.

### Key Capabilities
* **Interactive Navigation:** Pan, zoom, and inspect individual nodes and parameter connections directly within the canvas.
* **Canvas Controls:** Toggle theme between light and dark modes, reset view, and export high-resolution SVG or raster renders.
* **Fullscreen Experience:** Click **Open Fullscreen ↗** in the upper-right corner of the console to open the standalone canvas in an independent tab.

---

### Related Documentation
* [Architecture Atlas Overview](../architecture-atlas.md)
* [System Architecture Specification](../architecture.md)
* [FastAPI Backend Reference](../backend.md)
* [Catchment Hydrology & Datums](../basin-hydrology.md)
