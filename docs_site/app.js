// ==============================================================================
// HYDROCAST CLEAN SYSTEM UI ENGINE & HYDRAULIC GIS INTELLIGENCE PORTAL
// Project: IoT and Geoinformatics Based Flood Modelling and Prediction System
// Funding: DST-SERB, Government of India (GOI)
// Center: Center for Climate Change and Sustainability Studies (CCCSS)
//         Shivaji University, Kolhapur (SUK), Maharashtra, India
// Collaborator: Department of Electronics, YCIS Satara
// ==============================================================================

(function() {
  "use strict";

  const DATA = window.HYDROCAST_DATA || {
    funding: {},
    team: {},
    stations: [],
    river_gauges: [],
    subbasins_geojson: null,
    rivers_geojson: null,
    cross_sections: {},
    bed_profile: { segments: [], landmarks: [] },
    wrd_benchmarks: [],
    subbasins: [],
    reaches: [],
    documents: {}
  };

  const state = {
    activeView: "overview",
    activeSite: "SHIVAJI_BRIDGE",
    waterStage: 536.00,
    rainfall: 120.0,
    cn: 68.0,
    lagHr: 48.0,
    deltaT: -1.2,
    deltaH: 0.35,
    selectedDoc: "HMS.md",
    mapInitialized: false,
    leafletMap: null,
    subbasinLayer: null,
    riverLayer: null,
    stationLayer: null,
    gaugeLayer: null
  };

  // ============================================================================
  // NAVIGATION & VIEW SWITCHING (STRICT SINGLE-PANEL ENFORCEMENT)
  // ============================================================================
  function setupNavigation() {
    const navButtons = document.querySelectorAll(".tab-nav-btn, .nav-link, .menu-item-btn, [data-view]");
    navButtons.forEach(btn => {
      btn.addEventListener("click", (e) => {
        const targetView = btn.getAttribute("data-view");
        if (targetView) {
          e.preventDefault();
          switchView(targetView);
        }
      });
    });

    // Documentation search box
    const docSearch = document.getElementById("doc-search-box");
    if (docSearch) {
      docSearch.addEventListener("input", (e) => {
        filterDocs(e.target.value.trim().toLowerCase());
      });
    }
  }

  function switchView(viewId) {
    state.activeView = viewId;

    // 1. Update navigation tab active states
    document.querySelectorAll(".tab-nav-btn, .nav-link, .menu-item-btn").forEach(b => {
      if (b.getAttribute("data-view") === viewId) {
        b.classList.add("active");
      } else {
        b.classList.remove("active");
      }
    });

    // 2. Hide ALL panels explicitly (Fail-Safe to prevent any stacking)
    document.querySelectorAll(".view-panel").forEach(p => {
      p.classList.remove("active");
      p.style.display = "none";
    });

    // 3. Show target panel explicitly
    const targetPanel = document.getElementById(`panel-${viewId}`);
    if (targetPanel) {
      targetPanel.classList.add("active");
      targetPanel.style.display = "block";
    }

    // 4. Update breadcrumb
    const breadcrumbCurrent = document.getElementById("breadcrumb-current");
    if (breadcrumbCurrent) {
      const titles = {
        overview: "OVERVIEW & LEADERSHIP",
        gis_map: "WATERSHED GIS MAP & GEOJSON",
        cross_section: "2D RIVER HYDRAULICS & CROSS-SECTIONS",
        l_section: "L-SECTION RIVER BED PROFILE",
        hydrology: "SCS-CN & UNIT HYDROGRAPH SIMULATION",
        rating_curve: "RATING CURVES & WRD BENCHMARKS",
        ml_calibration: "ADAPTIVE ML RECALIBRATOR",
        documentation: "HEC-HMS TECHNICAL MANUALS",
        downloads: "DOWNLOADS (GEOJSON & MODELS)"
      };
      breadcrumbCurrent.innerText = titles[viewId] || viewId.toUpperCase();
    }

    // 5. Trigger view-specific renderers
    if (viewId === "gis_map") {
      initOrResizeMap();
    } else if (viewId === "cross_section") {
      renderCrossSection();
    } else if (viewId === "l_section") {
      renderLSection();
    } else if (viewId === "hydrology") {
      renderHydrology();
    } else if (viewId === "rating_curve") {
      renderRatingCurve();
    } else if (viewId === "ml_calibration") {
      renderMLPlayground();
    } else if (viewId === "documentation") {
      renderDocsLibrary();
    }

    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  // Expose switchView to global for inline anchors
  window.switchView = switchView;

  // ============================================================================
  // MODULE 1: INTERACTIVE WATERSHED GIS MAP (LEAFLET + GEOJSON)
  // ============================================================================
  function initOrResizeMap() {
    if (!state.mapInitialized) {
      initLeafletMap();
    } else if (state.leafletMap) {
      setTimeout(() => {
        state.leafletMap.invalidateSize();
      }, 200);
    }
  }

  function initLeafletMap() {
    const mapContainer = document.getElementById("gis-leaflet-map");
    if (!mapContainer || typeof L === "undefined") return;

    // Centered on Panchganga River Basin (Kolhapur)
    const map = L.map("gis-leaflet-map", {
      center: [16.65, 74.15],
      zoom: 10,
      zoomControl: true
    });

    // Crisp OpenStreetMap Light Topo TileLayer
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 18
    }).addTo(map);

    state.leafletMap = map;
    state.mapInitialized = true;

    // 1. Add Subbasin Polygons (GeoJSON)
    if (DATA.subbasins_geojson) {
      const colors = [
        "#2563eb", "#059669", "#d97706", "#7c3aed",
        "#db2777", "#0891b2", "#65a30d", "#ea580c", "#4f46e5"
      ];

      state.subbasinLayer = L.geoJSON(DATA.subbasins_geojson, {
        style: function(feature) {
          const id = feature.properties.name || "S1";
          const idx = parseInt(id.replace(/\D/g, "")) || 0;
          return {
            fillColor: colors[idx % colors.length],
            weight: 2,
            opacity: 1,
            color: "#1e3a8a",
            dashArray: "3",
            fillOpacity: 0.22
          };
        },
        onEachFeature: function(feature, layer) {
          const p = feature.properties;
          const popupContent = `
            <div style="font-family: 'Inter', sans-serif; font-size: 13px; line-height: 1.5; padding: 4px;">
              <div style="font-weight: 800; color: #1e3a8a; font-size: 14px; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px; margin-bottom: 6px;">
                Subbasin: ${p.name || "Panchganga"}
              </div>
              <div><strong>Longest Flow Path:</strong> ${p.long_len ? p.long_len.toFixed(2) + " km" : "N/A"}</div>
              <div><strong>Basin Relief:</strong> ${p.basin_rel ? p.basin_rel.toFixed(1) + " m" : "N/A"}</div>
              <div><strong>Elongation Ratio:</strong> ${p.elong_ra ? p.elong_ra.toFixed(3) : "N/A"}</div>
              <div><strong>Drainage Density:</strong> ${p.drain_den ? p.drain_den.toFixed(2) : "N/A"}</div>
              <div style="margin-top: 6px; font-size: 11px; color: #64748b;">HEC-HMS Subbasin Vector Polygon</div>
            </div>
          `;
          layer.bindPopup(popupContent);
          layer.on({
            mouseover: function(e) {
              const l = e.target;
              l.setStyle({ fillOpacity: 0.5, weight: 3 });
            },
            mouseout: function(e) {
              state.subbasinLayer.resetStyle(e.target);
            }
          });
        }
      }).addTo(map);

      try {
        map.fitBounds(state.subbasinLayer.getBounds());
      } catch (err) {}
    }

    // 2. Add River Network (GeoJSON)
    if (DATA.rivers_geojson) {
      state.riverLayer = L.geoJSON(DATA.rivers_geojson, {
        style: {
          color: "#0284c7",
          weight: 3.5,
          opacity: 0.9
        },
        onEachFeature: function(feature, layer) {
          const p = feature.properties;
          const popup = `
            <div style="font-family: 'Inter', sans-serif; font-size: 13px; line-height: 1.5; padding: 4px;">
              <strong style="color: #0284c7; font-size: 14px;">Reach: ${p.name || "Panchganga Reach"}</strong><br>
              <strong>Length:</strong> ${p.length_km ? p.length_km.toFixed(2) + " km" : "N/A"}<br>
              <strong>Slope:</strong> ${p.slope ? p.slope.toFixed(5) + " m/m" : "N/A"}<br>
              <em style="color: #64748b; font-size: 11px;">USACE Muskingum Routing Channel</em>
            </div>
          `;
          layer.bindPopup(popup);
        }
      }).addTo(map);
    }

    // 3. Add 20 Rain Gauge Stations
    const stationGroup = L.layerGroup();
    DATA.stations.forEach(st => {
      const marker = L.circleMarker([st.lat, st.lon], {
        radius: 6,
        fillColor: st.role === "Primary Governing" ? "#2563eb" : "#059669",
        color: "#ffffff",
        weight: 2,
        opacity: 1,
        fillOpacity: 0.9
      });
      marker.bindPopup(`
        <div style="font-family: 'Inter', sans-serif; font-size: 13px; padding: 4px;">
          <strong style="color: #0f172a; font-size: 14px;">Station ${st.id}: ${st.name}</strong><br>
          <strong>Subbasin:</strong> ${st.subbasin} | <strong>Elevation:</strong> ${st.elev} m MSL<br>
          <span style="font-size: 11px; color: ${st.role === 'Primary Governing' ? '#2563eb' : '#059669'}; font-weight: 700;">
            ${st.role}
          </span>
        </div>
      `);
      stationGroup.addLayer(marker);
    });
    stationGroup.addTo(map);
    state.stationLayer = stationGroup;

    // 4. Add Key River Gauges (Radar & Weirs)
    const gaugeGroup = L.layerGroup();
    DATA.river_gauges.forEach(rg => {
      const marker = L.marker([rg.lat, rg.lon]);
      marker.bindPopup(`
        <div style="font-family: 'Inter', sans-serif; font-size: 13px; padding: 4px;">
          <strong style="color: #c00000; font-size: 14px;">${rg.name}</strong><br>
          <strong>Type:</strong> ${rg.type}<br>
          <strong>Chainage:</strong> ${rg.chainage}<br>
          <strong>Thalweg Bed:</strong> ${rg.thalweg.toFixed(3)} m MSL
        </div>
      `);
      gaugeGroup.addLayer(marker);
    });
    gaugeGroup.addTo(map);
    state.gaugeLayer = gaugeGroup;

    // Layer checkboxes
    setupLayerCheckboxes();
  }

  function setupLayerCheckboxes() {
    const chkSub = document.getElementById("toggle-subbasins");
    const chkRiv = document.getElementById("toggle-rivers");
    const chkStn = document.getElementById("toggle-stations");
    const chkGau = document.getElementById("toggle-gauges");

    if (chkSub) chkSub.addEventListener("change", (e) => {
      if (state.subbasinLayer && state.leafletMap) {
        if (e.target.checked) state.leafletMap.addLayer(state.subbasinLayer);
        else state.leafletMap.removeLayer(state.subbasinLayer);
      }
    });

    if (chkRiv) chkRiv.addEventListener("change", (e) => {
      if (state.riverLayer && state.leafletMap) {
        if (e.target.checked) state.leafletMap.addLayer(state.riverLayer);
        else state.leafletMap.removeLayer(state.riverLayer);
      }
    });

    if (chkStn) chkStn.addEventListener("change", (e) => {
      if (state.stationLayer && state.leafletMap) {
        if (e.target.checked) state.leafletMap.addLayer(state.stationLayer);
        else state.leafletMap.removeLayer(state.stationLayer);
      }
    });

    if (chkGau) chkGau.addEventListener("change", (e) => {
      if (state.gaugeLayer && state.leafletMap) {
        if (e.target.checked) state.leafletMap.addLayer(state.gaugeLayer);
        else state.leafletMap.removeLayer(state.gaugeLayer);
      }
    });
  }

  // ============================================================================
  // MODULE 2: 2D RIVER HYDRAULICS & CROSS-SECTIONS
  // ============================================================================
  function setupCrossSectionControls() {
    const slider = document.getElementById("stage-slider");
    if (slider) {
      slider.addEventListener("input", (e) => {
        state.waterStage = parseFloat(e.target.value);
        renderCrossSection();
      });
    }
  }

  function setCrossSectionSite(siteKey) {
    state.activeSite = siteKey;
    const btnShi = document.getElementById("btn-site-shivaji");
    const btnRaj = document.getElementById("btn-site-rajaram");

    if (btnShi && btnRaj) {
      if (siteKey === "SHIVAJI_BRIDGE") {
        btnShi.classList.add("active");
        btnRaj.classList.remove("active");
      } else {
        btnRaj.classList.add("active");
        btnShi.classList.remove("active");
      }
    }

    const cs = DATA.cross_sections[siteKey];
    if (cs) {
      const slider = document.getElementById("stage-slider");
      if (slider) {
        slider.min = cs.thalweg;
        slider.max = cs.hfl + 1.5;
        if (state.waterStage < cs.thalweg || state.waterStage > cs.hfl + 1.5) {
          state.waterStage = cs.bankfull - 2.0;
        }
        slider.value = state.waterStage;
      }
    }
    renderCrossSection();
  }

  window.setCrossSectionSite = setCrossSectionSite;

  function renderCrossSection() {
    const cs = DATA.cross_sections[state.activeSite];
    if (!cs) return;

    const stage = state.waterStage;
    const sliderVal = document.getElementById("slider-stage-val");
    if (sliderVal) sliderVal.innerText = stage.toFixed(2) + " m MSL";

    // Hydraulic properties computation
    const xs = cs.station_m;
    const ys = cs.elevation_m;
    const n = xs.length;

    let areaMain = 0;
    let areaFlood = 0;
    let wpMain = 0;
    let wpFlood = 0;

    const bankfull = cs.bankfull;

    for (let i = 0; i < n - 1; i++) {
      const x1 = xs[i], x2 = xs[i + 1];
      const y1 = ys[i], y2 = ys[i + 1];

      if (y1 < stage || y2 < stage) {
        const d1 = Math.max(0, stage - y1);
        const d2 = Math.max(0, stage - y2);
        const dx = Math.abs(x2 - x1);
        const trapArea = 0.5 * (d1 + d2) * dx;
        const segmentWP = Math.sqrt(dx * dx + Math.pow(y2 - y1, 2));

        const midY = 0.5 * (y1 + y2);
        if (midY < bankfull) {
          areaMain += trapArea;
          wpMain += segmentWP;
        } else {
          areaFlood += trapArea;
          wpFlood += segmentWP;
        }
      }
    }

    const rMain = wpMain > 0 ? areaMain / wpMain : 0;
    const rFlood = wpFlood > 0 ? areaFlood / wpFlood : 0;

    const s0 = cs.slope || 0.000215;
    const qMain = wpMain > 0 ? (1.0 / cs.n_main) * areaMain * Math.pow(rMain, 2/3) * Math.sqrt(s0) : 0;
    const qFlood = wpFlood > 0 ? (1.0 / cs.n_flood) * areaFlood * Math.pow(rFlood, 2/3) * Math.sqrt(s0) : 0;
    const qTotal = qMain + qFlood;
    const areaTotal = areaMain + areaFlood;
    const meanV = areaTotal > 0 ? qTotal / areaTotal : 0;

    // Update UI Metrics
    const elStage = document.getElementById("metric-stage");
    const elDepth = document.getElementById("metric-depth");
    const elQ = document.getElementById("metric-q");
    const elCusecs = document.getElementById("metric-cusecs");
    const elArea = document.getElementById("metric-area");
    const elV = document.getElementById("metric-velocity");

    if (elStage) elStage.innerHTML = `${stage.toFixed(2)} <span class="metric-unit-clean">m MSL</span>`;
    if (elDepth) elDepth.innerText = `Depth: ${(stage - cs.thalweg).toFixed(2)} m above Thalweg`;
    if (elQ) elQ.innerHTML = `${qTotal.toFixed(1)} <span class="metric-unit-clean">m³/s</span>`;
    if (elCusecs) elCusecs.innerText = `${(qTotal * 35.3147).toLocaleString(undefined, {maximumFractionDigits: 0})} cusecs`;
    if (elArea) elArea.innerHTML = `${areaMain.toFixed(1)} / ${areaFlood.toFixed(1)} <span class="metric-unit-clean">m²</span>`;
    if (elV) elV.innerText = `Mean Velocity: ${meanV.toFixed(2)} m/s`;

    // Render SVG
    const svg = document.getElementById("cs-svg");
    if (!svg) return;

    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = cs.thalweg - 1.0;
    const maxY = cs.hfl + 2.0;

    const width = 1000;
    const height = 420;
    const padX = 60;
    const padY = 40;

    const scaleX = (x) => padX + ((x - minX) / (maxX - minX)) * (width - 2 * padX);
    const scaleY = (y) => height - padY - ((y - minY) / (maxY - minY)) * (height - 2 * padY);

    let polylineBed = "";
    for (let i = 0; i < n; i++) {
      polylineBed += `${scaleX(xs[i])},${scaleY(ys[i])} `;
    }

    const waterY = scaleY(stage);
    const bankfullY = scaleY(cs.bankfull);
    const hflY = scaleY(cs.hfl);

    let html = `
      <defs>
        <linearGradient id="waterGradientLight" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#38bdf8" stop-opacity="0.6"/>
          <stop offset="100%" stop-color="#0284c7" stop-opacity="0.8"/>
        </linearGradient>
      </defs>

      <!-- Grid lines -->
      <line x1="${padX}" y1="${height - padY}" x2="${width - padX}" y2="${height - padY}" stroke="#e2e8f0" stroke-width="1"/>
      <line x1="${padX}" y1="${padY}" x2="${padX}" y2="${height - padY}" stroke="#e2e8f0" stroke-width="1"/>

      <!-- Water Surface Line -->
      <line x1="${padX}" y1="${waterY}" x2="${width - padX}" y2="${waterY}" stroke="#0284c7" stroke-width="2.5" stroke-dasharray="4,2"/>
      <text x="${width - padX - 8}" y="${waterY - 6}" fill="#0284c7" font-weight="700" font-size="11" font-family="'JetBrains Mono'" text-anchor="end">
        WL: ${stage.toFixed(2)} m MSL
      </text>

      <!-- Bankfull Threshold -->
      <line x1="${padX}" y1="${bankfullY}" x2="${width - padX}" y2="${bankfullY}" stroke="#d97706" stroke-width="1.5" stroke-dasharray="6,4"/>
      <text x="${padX + 8}" y="${bankfullY - 6}" fill="#d97706" font-size="11" font-weight="600" font-family="'JetBrains Mono'">
        Bankfull ${cs.bankfull.toFixed(2)}m (Sugarcane Floodplain n=0.070)
      </text>

      <!-- 2019 HFL Benchmark -->
      <line x1="${padX}" y1="${hflY}" x2="${width - padX}" y2="${hflY}" stroke="#c00000" stroke-width="1.5" stroke-dasharray="6,4"/>
      <text x="${padX + 8}" y="${hflY - 6}" fill="#c00000" font-size="11" font-weight="700" font-family="'JetBrains Mono'">
        2019 Historic HFL ${cs.hfl.toFixed(2)}m
      </text>

      <!-- Ground / Riverbed Polyline -->
      <polyline points="${polylineBed}" fill="none" stroke="#475569" stroke-width="3"/>

      <!-- Thalweg Marker -->
      <circle cx="${scaleX(xs[ys.indexOf(Math.min(...ys))])}" cy="${scaleY(cs.thalweg)}" r="5" fill="#c00000"/>
      <text x="${scaleX(xs[ys.indexOf(Math.min(...ys))])}" y="${scaleY(cs.thalweg) + 18}" fill="#475569" font-size="11" font-family="'JetBrains Mono'" text-anchor="middle">
        Thalweg: ${cs.thalweg.toFixed(3)}m
      </text>
    `;

    svg.innerHTML = html;
  }

  // ============================================================================
  // MODULE 3: LONGITUDINAL RIVER BED PROFILE (L-SECTION)
  // ============================================================================
  function renderLSection() {
    const svg = document.getElementById("lsec-svg");
    if (!svg) return;

    const width = 1000;
    const height = 400;
    const padX = 70;
    const padY = 50;

    const minKm = 0.0;
    const maxKm = 100.0;
    const minElev = 515.0;
    const maxElev = 560.0;

    const scaleX = (km) => padX + ((km - minKm) / (maxKm - minKm)) * (width - 2 * padX);
    const scaleY = (el) => height - padY - ((el - minElev) / (maxElev - minElev)) * (height - 2 * padY);

    const segs = DATA.bed_profile.segments;
    const lms = DATA.bed_profile.landmarks;

    let html = `
      <defs>
        <linearGradient id="bedGradLight" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#cbd5e1" stop-opacity="0.5"/>
          <stop offset="100%" stop-color="#f1f5f9" stop-opacity="0.1"/>
        </linearGradient>
      </defs>

      <!-- Axes -->
      <line x1="${padX}" y1="${height - padY}" x2="${width - padX}" y2="${height - padY}" stroke="#94a3b8" stroke-width="1.5"/>
      <line x1="${padX}" y1="${padY}" x2="${padX}" y2="${height - padY}" stroke="#94a3b8" stroke-width="1.5"/>
    `;

    // Draw slope segments
    segs.forEach(s => {
      const x1 = scaleX(s.start_km);
      const y1 = scaleY(s.start_elevation);
      const x2 = scaleX(s.end_km);
      const y2 = scaleY(s.end_elevation);

      html += `
        <line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="#1e3a8a" stroke-width="3"/>
        <text x="${(x1 + x2) / 2}" y="${(y1 + y2) / 2 - 12}" fill="#2563eb" font-weight="700" font-size="11" font-family="'JetBrains Mono'" text-anchor="middle">
          Slope ${s.slope}
        </text>
      `;
    });

    // Draw landmarks
    lms.forEach(lm => {
      const cx = scaleX(lm.km);
      const cy = scaleY(lm.elevation);

      html += `
        <line x1="${cx}" y1="${cy}" x2="${cx}" y2="${height - padY}" stroke="#94a3b8" stroke-dasharray="3,3"/>
        <circle cx="${cx}" cy="${cy}" r="5" fill="#c00000" stroke="#fff" stroke-width="1.5"/>
        <text x="${cx}" y="${cy - 8}" fill="#0f172a" font-weight="700" font-size="10" font-family="'Inter'" text-anchor="middle">
          ${lm.name}
        </text>
        <text x="${cx}" y="${height - padY + 16}" fill="#64748b" font-size="10" font-family="'JetBrains Mono'" text-anchor="middle">
          ${lm.km.toFixed(0)} km
        </text>
      `;
    });

    svg.innerHTML = html;
  }

  // ============================================================================
  // MODULE 4: HYDROLOGY & SCS-CN SIMULATION
  // ============================================================================
  function setupHydrologyControls() {
    const rSlider = document.getElementById("hydro-rain-slider");
    const cSlider = document.getElementById("hydro-cn-slider");
    const lSlider = document.getElementById("hydro-lag-slider");

    if (rSlider) rSlider.addEventListener("input", (e) => { state.rainfall = parseFloat(e.target.value); renderHydrology(); });
    if (cSlider) cSlider.addEventListener("input", (e) => { state.cn = parseFloat(e.target.value); renderHydrology(); });
    if (lSlider) lSlider.addEventListener("input", (e) => { state.lagHr = parseFloat(e.target.value); renderHydrology(); });
  }

  function renderHydrology() {
    const P = state.rainfall;
    const baseCN = state.cn;
    const lagHr = state.lagHr;

    // Saturated soil switching threshold at 65 mm / 90 hours
    const isAMC3 = P >= 65.0;
    let activeCN = baseCN;
    if (isAMC3) {
      activeCN = (baseCN * 23.0) / (10.0 + 0.13 * baseCN);
    }

    const S = (25400.0 / activeCN) - 254.0;
    const Ia = 0.2 * S;
    let directRunoffMm = 0;
    if (P > Ia) {
      directRunoffMm = Math.pow(P - Ia, 2) / (P - Ia + S);
    }
    const runoffCoeff = P > 0 ? directRunoffMm / P : 0;
    const tp = 0.5 + lagHr;

    // Update Slider Badges
    const elRain = document.getElementById("slider-rain-val");
    const elCN = document.getElementById("slider-cn-val");
    const elLag = document.getElementById("slider-lag-val");

    if (elRain) elRain.innerText = P.toFixed(0) + " mm";
    if (elCN) elCN.innerText = baseCN.toFixed(1);
    if (elLag) elLag.innerText = lagHr.toFixed(1) + " h";

    const elAMC = document.getElementById("metric-amc-status");
    const elS = document.getElementById("metric-s-retention");
    const elIa = document.getElementById("metric-ia");
    const elRunoff = document.getElementById("metric-q-excess");
    const elCoeff = document.getElementById("metric-runoff-coeff");
    const elTp = document.getElementById("metric-tp");

    if (elAMC) {
      elAMC.innerText = isAMC3 ? "AMC-III (Saturated Soil)" : "AMC-II (Normal Soil)";
      elAMC.style.color = isAMC3 ? "#c00000" : "#059669";
    }
    if (elS) elS.innerText = S.toFixed(1) + " mm";
    if (elIa) elIa.innerText = `Initial Abstraction Ia: ${Ia.toFixed(1)} mm`;
    if (elRunoff) elRunoff.innerText = directRunoffMm.toFixed(1) + " mm";
    if (elCoeff) elCoeff.innerText = `Runoff Fraction: ${(runoffCoeff * 100).toFixed(1)}%`;
    if (elTp) elTp.innerText = tp.toFixed(1) + " hrs";

    const svg = document.getElementById("hydro-svg");
    if (!svg) return;

    const width = 1000;
    const height = 400;
    const padX = 70;
    const padY = 50;

    let uhPoints = [];
    let maxUH = 0;
    const m = 3.7;

    for (let t = 0; t <= 90; t++) {
      let u = 0;
      if (t > 0 && tp > 0) {
        const tr = t / tp;
        u = Math.pow(tr, m) * Math.exp(m * (1 - tr));
      }
      uhPoints.push({ t, u });
      if (u > maxUH) maxUH = u;
    }

    const scaleX = (t) => padX + (t / 90) * (width - 2 * padX);
    const scaleY = (u) => height - padY - (maxUH > 0 ? (u / maxUH) * (height - 2 * padY) : 0);

    let polyPoints = "";
    uhPoints.forEach(pt => {
      polyPoints += `${scaleX(pt.t)},${scaleY(pt.u)} `;
    });

    let html = `
      <defs>
        <linearGradient id="uhGradLight" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#38bdf8" stop-opacity="0.5"/>
          <stop offset="100%" stop-color="#38bdf8" stop-opacity="0.0"/>
        </linearGradient>
      </defs>

      <line x1="${padX}" y1="${height - padY}" x2="${width - padX}" y2="${height - padY}" stroke="#94a3b8" stroke-width="1.5"/>
      <line x1="${padX}" y1="${padY}" x2="${padX}" y2="${height - padY}" stroke="#94a3b8" stroke-width="1.5"/>

      <polygon points="${scaleX(0)},${height - padY} ${polyPoints} ${scaleX(90)},${height - padY}" fill="url(#uhGradLight)"/>
      <polyline points="${polyPoints}" fill="none" stroke="#0284c7" stroke-width="3"/>

      <circle cx="${scaleX(tp)}" cy="${scaleY(maxUH)}" r="6" fill="#c00000" stroke="#fff" stroke-width="2"/>
      <text x="${scaleX(tp)}" y="${scaleY(maxUH) - 12}" fill="#c00000" font-weight="700" font-size="12" font-family="'JetBrains Mono'" text-anchor="middle">Peak tp: ${tp.toFixed(1)}h</text>
      <line x1="${scaleX(tp)}" y1="${scaleY(maxUH)}" x2="${scaleX(tp)}" y2="${height - padY}" stroke="#c00000" stroke-dasharray="3,3"/>

      <text x="${scaleX(0)}" y="${height - padY + 20}" fill="#64748b" font-size="11" font-family="'JetBrains Mono'">T+0h</text>
      <text x="${scaleX(30)}" y="${height - padY + 20}" fill="#64748b" font-size="11" font-family="'JetBrains Mono'">T+30h</text>
      <text x="${scaleX(60)}" y="${height - padY + 20}" fill="#64748b" font-size="11" font-family="'JetBrains Mono'">T+60h</text>
      <text x="${scaleX(90)}" y="${height - padY + 20}" fill="#64748b" font-size="11" font-family="'JetBrains Mono'">T+90h</text>
    `;

    svg.innerHTML = html;
  }

  // ============================================================================
  // MODULE 5: RATING CURVE & WRD BENCHMARKS
  // ============================================================================
  function renderRatingCurve() {
    const svg = document.getElementById("rc-svg");
    if (!svg) return;

    const cs = DATA.cross_sections[state.activeSite];
    if (!cs || !cs.rating_curve) return;

    const rc = cs.rating_curve;
    const wrd = DATA.wrd_benchmarks;

    const width = 1000;
    const height = 450;
    const padX = 80;
    const padY = 50;

    const maxQ = 4500;
    const minH = cs.thalweg;
    const maxH = cs.hfl + 1.5;

    const scaleX = (q) => padX + (q / maxQ) * (width - 2 * padX);
    const scaleY = (h) => height - padY - ((h - minH) / (maxH - minH)) * (height - 2 * padY);

    let rcPoints = "";
    rc.forEach(pt => {
      rcPoints += `${scaleX(pt.q)},${scaleY(pt.stage)} `;
    });

    let html = `
      <line x1="${padX}" y1="${height - padY}" x2="${width - padX}" y2="${height - padY}" stroke="#94a3b8" stroke-width="1.5"/>
      <line x1="${padX}" y1="${padY}" x2="${padX}" y2="${height - padY}" stroke="#94a3b8" stroke-width="1.5"/>
      <polyline points="${rcPoints}" fill="none" stroke="#0284c7" stroke-width="3"/>
    `;

    wrd.forEach(b => {
      const cx = scaleX(b.q_m3s);
      const cy = scaleY(b.stage_m);
      html += `
        <circle cx="${cx}" cy="${cy}" r="6" fill="#c00000" stroke="#fff" stroke-width="2"/>
        <text x="${cx + 8}" y="${cy - 4}" fill="#0f172a" font-weight="700" font-size="11" font-family="'JetBrains Mono'">${b.label} (${b.q_m3s} m³/s)</text>
      `;
    });

    svg.innerHTML = html;
  }

  // ============================================================================
  // MODULE 6: REAL-TIME ML RECALIBRATION
  // ============================================================================
  function setupMLControls() {
    const dtSlider = document.getElementById("ml-dt-slider");
    const dhSlider = document.getElementById("ml-dh-slider");

    if (dtSlider) dtSlider.addEventListener("input", (e) => { state.deltaT = parseFloat(e.target.value); renderMLPlayground(); });
    if (dhSlider) dhSlider.addEventListener("input", (e) => { state.deltaH = parseFloat(e.target.value); renderMLPlayground(); });
  }

  function renderMLPlayground() {
    const dt = state.deltaT;
    const dh = state.deltaH;

    const elDtVal = document.getElementById("ml-dt-val");
    const elDhVal = document.getElementById("ml-dh-val");
    if (elDtVal) elDtVal.innerText = (dt > 0 ? "+" : "") + dt.toFixed(1) + " h";
    if (elDhVal) elDhVal.innerText = (dh > 0 ? "+" : "") + dh.toFixed(2) + " m";

    const isTriggered = Math.abs(dt) >= 1.0 || Math.abs(dh) >= 0.25;
    let alpha_k = 1.0;
    let alpha_lag = 1.0;
    let delta_cn = 0.0;
    let x_param = 0.250;

    if (isTriggered) {
      alpha_k = Math.max(0.50, Math.min(1.80, 1.0 + dt * 0.075));
      alpha_lag = Math.max(0.50, Math.min(1.80, 1.0 + dt * 0.060));
      delta_cn = Math.max(-8.0, Math.min(8.0, -dh * 4.5));
      x_param = Math.max(0.15, Math.min(0.40, 0.25 - dt * 0.02));
    }

    const elAk = document.getElementById("metric-alpha-k");
    const elAlag = document.getElementById("metric-alpha-lag");
    const elDcn = document.getElementById("metric-delta-cn");
    const elX = document.getElementById("metric-x-param");
    const elTrigger = document.getElementById("metric-ml-trigger");

    if (elAk) elAk.innerText = alpha_k.toFixed(3);
    if (elAlag) elAlag.innerText = alpha_lag.toFixed(3);
    if (elDcn) elDcn.innerText = (delta_cn > 0 ? "+" : "") + delta_cn.toFixed(2);
    if (elX) elX.innerText = `Wedge X: ${x_param.toFixed(3)}`;
    if (elTrigger) {
      elTrigger.innerText = isTriggered ? "AUTO-RECALIBRATION ACTIVE" : "TOLERANCE NORMAL";
      elTrigger.style.color = isTriggered ? "#c00000" : "#059669";
    }

    const svg = document.getElementById("ml-svg");
    if (!svg) return;

    const width = 1000;
    const height = 400;
    const padX = 70;
    const padY = 50;

    const peakBaseline = 2400;
    const peakCalibrated = peakBaseline + (-delta_cn * 80);
    const tpBaseline = 48.0;
    const tpCalibrated = tpBaseline + dt;

    let ptsBase = "";
    let ptsCalib = "";

    for (let t = 0; t <= 90; t++) {
      const qBase = peakBaseline * Math.exp(-0.5 * Math.pow((t - tpBaseline) / 12, 2));
      const qCalib = peakCalibrated * Math.exp(-0.5 * Math.pow((t - tpCalibrated) / 12, 2));

      const sx = padX + (t / 90) * (width - 2 * padX);
      const syBase = height - padY - (qBase / 3500) * (height - 2 * padY);
      const syCalib = height - padY - (qCalib / 3500) * (height - 2 * padY);

      ptsBase += `${sx},${syBase} `;
      ptsCalib += `${sx},${syCalib} `;
    }

    let html = `
      <line x1="${padX}" y1="${height - padY}" x2="${width - padX}" y2="${height - padY}" stroke="#94a3b8" stroke-width="1.5"/>
      <line x1="${padX}" y1="${padY}" x2="${padX}" y2="${height - padY}" stroke="#94a3b8" stroke-width="1.5"/>

      <!-- Baseline Hydrograph -->
      <polyline points="${ptsBase}" fill="none" stroke="#64748b" stroke-width="2" stroke-dasharray="6,4"/>

      <!-- ML Calibrated Hydrograph -->
      <polyline points="${ptsCalib}" fill="none" stroke="#059669" stroke-width="3"/>

      <!-- Legend -->
      <line x1="${padX + 20}" y1="${padY + 20}" x2="${padX + 45}" y2="${padY + 20}" stroke="#64748b" stroke-width="2" stroke-dasharray="4,4"/>
      <text x="${padX + 55}" y="${padY + 24}" fill="#475569" font-size="12" font-family="'JetBrains Mono'">Uncalibrated Model Hydrograph</text>

      <line x1="${padX + 20}" y1="${padY + 40}" x2="${padX + 45}" y2="${padY + 40}" stroke="#059669" stroke-width="3"/>
      <text x="${padX + 55}" y="${padY + 44}" fill="#059669" font-weight="700" font-size="12" font-family="'JetBrains Mono'">Live ML Recalibrated Hydrograph</text>
    `;

    svg.innerHTML = html;
  }

  // ============================================================================
  // MODULE 7: TECHNICAL DOCUMENTATION EXPLORER (GFM + PRISTINE ASCII ART)
  // ============================================================================
  function renderDocsLibrary() {
    renderDocsList("");
    showDocContent(state.selectedDoc);
  }

  function filterDocs(filter) {
    renderDocsList(filter);
  }

  function renderDocsList(filter) {
    const listEl = document.getElementById("docs-tree-list");
    if (!listEl) return;

    listEl.innerHTML = "";
    const docs = DATA.documents;

    Object.keys(docs).forEach(filename => {
      const doc = docs[filename];
      if (filter && !doc.title.toLowerCase().includes(filter) && !filename.toLowerCase().includes(filter)) {
        return;
      }

      const btn = document.createElement("button");
      btn.className = `doc-btn-clean ${state.selectedDoc === filename ? "active" : ""}`;
      btn.innerHTML = `
        <span style="font-weight: 600;">${doc.title}</span>
        <span style="font-size: 0.7rem; font-family: var(--font-mono); color: #64748b; background: #e2e8f0; padding: 1px 6px; border-radius: 9999px;">
          ${doc.lines}L
        </span>
      `;
      btn.addEventListener("click", () => {
        state.selectedDoc = filename;
        renderDocsList(filter);
        showDocContent(filename);
      });
      listEl.appendChild(btn);
    });
  }

  function showDocContent(filename) {
    const viewer = document.getElementById("docs-reader-body");
    if (!viewer) return;

    const doc = DATA.documents[filename];
    if (!doc) {
      viewer.innerHTML = "<p style='color: #64748b;'>Select a technical manual from the list on the left.</p>";
      return;
    }

    const headerHtml = `
      <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid #e2e8f0; padding-bottom: 12px; margin-bottom: 20px; flex-wrap: wrap; gap: 10px;">
        <div>
          <span style="font-size: 0.72rem; font-family: var(--font-mono); font-weight: 700; color: #2563eb; background: #eff6ff; padding: 3px 8px; border-radius: 4px; border: 1px solid #bfdbfe;">
            ${doc.filename}
          </span>
          <span style="font-size: 0.75rem; color: #64748b; margin-left: 8px;">
            ${doc.lines} lines &bull; ${(doc.size_bytes / 1024).toFixed(1)} KB &bull; USACE HEC-HMS Specification
          </span>
        </div>
        <button class="btn-repo" style="font-size: 0.75rem; padding: 4px 10px;" onclick="copyActiveDoc()">
          Copy Document Text
        </button>
      </div>
    `;

    viewer.innerHTML = headerHtml + renderMarkdownClean(doc.markdown);
  }

  window.copyActiveDoc = function() {
    const doc = DATA.documents[state.selectedDoc];
    if (doc) {
      navigator.clipboard.writeText(doc.markdown).then(() => {
        alert(`Copied ${doc.filename} to clipboard!`);
      });
    }
  };

  // Clean Markdown Renderer with GFM and Monospace ASCII Diagram formatting
  function renderMarkdownClean(md) {
    if (typeof window.marked !== "undefined" && typeof window.marked.parse === "function") {
      try {
        // Configure marked for GFM
        window.marked.setOptions({
          gfm: true,
          breaks: false
        });

        let rawHtml = window.marked.parse(md);

        // Enhance ASCII diagrams and code blocks
        // Detect pre blocks that contain box-drawing characters or diagrams
        const tempDiv = document.createElement("div");
        tempDiv.innerHTML = rawHtml;

        // Wrap tables in table-responsive container
        tempDiv.querySelectorAll("table").forEach(tbl => {
          if (!tbl.parentElement.classList.contains("table-responsive")) {
            const wrap = document.createElement("div");
            wrap.className = "table-responsive";
            tbl.parentNode.insertBefore(wrap, tbl);
            wrap.appendChild(tbl);
          }
        });

        // Enhance PRE/CODE blocks
        tempDiv.querySelectorAll("pre").forEach(pre => {
          const codeEl = pre.querySelector("code");
          const codeText = codeEl ? codeEl.innerText : pre.innerText;

          // Check if this is an ASCII architecture flowchart / diagram
          const hasBoxChars = /[│─┌┐└┘├┤┼▼▲║═╔╗╚╝╠╣╬]/.test(codeText);
          const isAsciiClass = pre.className.includes("text") || pre.className.includes("ascii") || pre.className.includes("diagram");

          if (hasBoxChars || isAsciiClass) {
            // Render as high-contrast Terminal Architecture Diagram
            const diagramWrap = document.createElement("div");
            diagramWrap.className = "ascii-diagram-wrapper";
            diagramWrap.innerHTML = `
              <div class="diagram-window-header">
                <span class="mac-dot red"></span>
                <span class="mac-dot yellow"></span>
                <span class="mac-dot green"></span>
                <span class="diagram-title">Hydrologic Architecture & Routing Flowchart</span>
              </div>
              <pre class="ascii-diagram-block"><code>${escapeHtml(codeText)}</code></pre>
            `;
            pre.parentNode.replaceChild(diagramWrap, pre);
          } else {
            // Regular code block with clean header
            const lang = (codeEl && codeEl.className.replace("language-", "")) || "Code";
            const codeWrap = document.createElement("div");
            codeWrap.className = "code-block-wrapper";
            codeWrap.innerHTML = `
              <div class="code-header-bar">
                <span class="code-lang-tag">${escapeHtml(lang)}</span>
                <button class="btn-copy-code" onclick="copySnippet(this)">Copy</button>
              </div>
              <pre><code>${escapeHtml(codeText)}</code></pre>
            `;
            pre.parentNode.replaceChild(codeWrap, pre);
          }
        });

        return tempDiv.innerHTML;
      } catch (e) {
        console.warn("Marked parser error, falling back:", e);
      }
    }

    // High-fidelity fallback parser
    return fallbackMarkdownRender(md);
  }

  function fallbackMarkdownRender(md) {
    let out = md
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");

    // Code blocks with ASCII diagram detection
    out = out.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (match, lang, code) => {
      const isDiagram = /[│─┌┐└┘├┤┼▼▲║═]/.test(code) || lang === "text" || lang === "ascii";
      if (isDiagram) {
        return `
          <div class="ascii-diagram-wrapper">
            <div class="diagram-window-header">
              <span class="mac-dot red"></span>
              <span class="mac-dot yellow"></span>
              <span class="mac-dot green"></span>
              <span class="diagram-title">Hydrologic Architecture & Routing Flowchart</span>
            </div>
            <pre class="ascii-diagram-block"><code>${code}</code></pre>
          </div>
        `;
      }
      return `
        <div class="code-block-wrapper">
          <div class="code-header-bar">
            <span class="code-lang-tag">${lang || "CODE"}</span>
            <button class="btn-copy-code" onclick="copySnippet(this)">Copy</button>
          </div>
          <pre><code>${code}</code></pre>
        </div>
      `;
    });

    // Headings
    out = out.replace(/^### (.*$)/gim, "<h3>$1</h3>");
    out = out.replace(/^## (.*$)/gim, "<h2>$1</h2>");
    out = out.replace(/^# (.*$)/gim, "<h1>$1</h1>");

    // Bold & italic
    out = out.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    out = out.replace(/\*(.*?)\*/g, "<em>$1</em>");
    out = out.replace(/`([^`]+)`/g, "<code>$1</code>");

    return out;
  }

  function escapeHtml(str) {
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  window.copySnippet = function(btn) {
    const pre = btn.closest(".code-block-wrapper").querySelector("pre code");
    if (pre) {
      navigator.clipboard.writeText(pre.innerText).then(() => {
        btn.innerText = "Copied!";
        setTimeout(() => { btn.innerText = "Copy"; }, 2000);
      });
    }
  };

  // Window Initialization
  window.addEventListener("DOMContentLoaded", () => {
    setupNavigation();
    setupCrossSectionControls();
    setupHydrologyControls();
    setupMLControls();
    switchView("overview");
  });

})();
