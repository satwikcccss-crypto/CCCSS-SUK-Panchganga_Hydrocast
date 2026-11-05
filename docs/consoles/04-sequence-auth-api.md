---
title: "04 · API Auth & Request Lifecycle"
---

# 04 · API Auth & Request Lifecycle

<div class="hydrocast-diagram-card">
  <div class="hydrocast-diagram-header">
    <div class="hydrocast-diagram-title">
      <span class="hydrocast-diagram-badge">Interactive Console</span>
      <strong>Dual-Tier Keys, JWT & SlowAPI Rate Limits</strong>
    </div>
    <div class="hydrocast-diagram-actions">
      <a class="hydrocast-diagram-btn" href="../../diagrams/04-sequence-auth-api.html" target="_blank" rel="noopener">Open Fullscreen ↗</a>
    </div>
  </div>
  <iframe class="hydrocast-diagram-frame" src="../../diagrams/04-sequence-auth-api.html?embed=1" title="04 · API Auth & Request Lifecycle"></iframe>
</div>

## Description & System Role

Detailed UML sequence diagram detailing FastAPI request ingress, API key validation, Bearer JWT verification, Redis token-bucket rate limiting, and response serialization.

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
