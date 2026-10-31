# IoT Ultrasonic Water Level Telemetry & Sensor Integration

HydroCast continuously grounds its hydrologic predictions in real-world ground truth via an autonomous solar-powered **ultrasonic water level radar** deployed on the Panchganga River at Kolhapur, Maharashtra. Telemetry ingestion, outlier filtering, hourly resampling, and textbook validation metrics are implemented in `src/hydrology/realtime_telemetry_validator.py` and `src/hydrology/telemetry_metrics.py`.

---

## Interactive diagram consoles

The console below is the rendered reference for this page: it carries the same structure, tier boundaries and failure branches that the prose describes.

<div class="hydrocast-diagram-card">
  <div class="hydrocast-diagram-header">
    <div class="hydrocast-diagram-title">
      <span class="hydrocast-diagram-badge">Interactive Console · Diagram 05</span>
      <strong>Simulation Run Lifecycle & Telemetry Integration</strong>
    </div>
    <div class="hydrocast-diagram-actions">
      <a class="hydrocast-diagram-btn" href="../diagrams/05-lifecycle-runs.html" target="_blank">Open Fullscreen ↗</a>
    </div>
  </div>
  <iframe class="hydrocast-diagram-frame" src="../diagrams/05-lifecycle-runs.html?embed=1" title="Simulation Run Lifecycle Console"></iframe>
</div>

<div class="hydrocast-diagram-card">
  <div class="hydrocast-diagram-header">
    <div class="hydrocast-diagram-title">
      <span class="hydrocast-diagram-badge">Interactive Console · Diagram 02</span>
      <strong>Rainfall-to-Alert Dataflow</strong>
    </div>
    <div class="hydrocast-diagram-actions">
      <a class="hydrocast-diagram-btn" href="../diagrams/02-dataflow.html" target="_blank">Open Fullscreen ↗</a>
    </div>
  </div>
  <iframe class="hydrocast-diagram-frame" src="../diagrams/02-dataflow.html?embed=1" title="Rainfall-to-Alert Dataflow Console"></iframe>
</div>

---

## 1. Hardware Architecture & Mounting Geometry

Real-time river stage observations are captured by an autonomous ultrasonic radar sensor mounted beneath the central arch girder of **Chhatrapati Shivaji Maharaj Bridge** ($16.708917^\circ\text{ N}, 74.219278^\circ\text{ E}$) over the Panchganga River.

### 1.1 Structural Elevation Benchmarks
- **Sensor Transducer Face Datum:** $\mathbf{549.35\text{ m MSL}}$ (Surveyed reference datum).
- **River Bed Elevation at Bridge:** $\mathbf{528.670\text{ m MSL}}$ (Surveyed bedrock thalweg).
- **WRD Gauge Zero Reference Level:** $\mathbf{530.180\text{ m MSL}}$ ($0'\ 0''$ on official gauge post).
- **Alert Stage Threshold:** $\mathbf{542.10\text{ m MSL}}$ ($39'\ 1''$; air gap: $23.79\text{ ft}$).
- **Warning Stage Threshold:** $\mathbf{542.70\text{ m MSL}}$ ($41'\ 1''$; air gap: $21.82\text{ ft}$).
- **Danger Stage Threshold:** $\mathbf{543.30\text{ m MSL}}$ ($43'\ 0''$; air gap: $19.85\text{ ft}$).
- **Highest Flood Level (HFL 2019/2021):** $\mathbf{545.33\text{ m MSL}}$ ($49'\ 8''$; air gap: $13.19\text{ ft}$).

See [Catchment Hydrology: Regulatory Datums](basin-hydrology.md#regulatory-datums) for the full authoritative schedule of benchmark elevations.

### 1.2 Mathematical Water Level Conversion
The ultrasonic sensor measures the round-trip acoustic transit time, outputting air distance $d_{air}$ (feet) down to the water surface. Stage in meters above Mean Sea Level (MSL) is computed via:

$$\text{Stage } H\text{ (m MSL)} = 549.35 - \left(d_{air} \times 0.3048\right)$$

$$\text{Water Depth Above WRD Zero Datum } y\text{ (m)} = H - 530.18$$

---

## 2. Cloud Telemetry Uplink & Outlier Filtering

The field unit transmits raw observations via cellular IoT to MathWorks ThingSpeak cloud:
- **Channel ID:** `3424513`
- **Field 1:** Distance from transducer face to water surface (feet)
- **Reporting Cadence:** Every 5 minutes

### 2.1 Physical Outlier Rejection (`resample_feeds_hourly`)
Spurious acoustic reflections from passing debris, river spray, or acoustic beam scattering are rejected by strict physical boundaries in `src/hydrology/telemetry_metrics.py`:

$$15.0\text{ ft} \le d_{air} \le 80.0\text{ ft}$$

- **Upper Air Boundary ($< 15.0$ ft):** Rejects impossible water stages above 544.78 m MSL (bridge deck submergence).
- **Lower Bed Boundary ($> 80.0$ ft):** Rejects impossible reflections below 524.96 m MSL (far below the surveyed bedrock floor).

### 2.2 Hourly UTC Mean Resampling
Raw 5-minute pings passing physical bounds are aggregated into clean hourly UTC bins (`YYYY-MM-DDTHH:00:00Z`):

$$\bar{d}_{hr} = \frac{1}{k} \sum_{j=1}^k d_{air, j} \quad (\text{for } k \ge 1 \text{ samples})$$

$$\bar{H}_{hr} = 549.35 - (\bar{d}_{hr} \times 0.3048)$$

Along with mean stage, the pipeline records minimum stage, maximum stage, and sample count per hour to monitor sensor stability.

### 2.3 Resilient Local Persistence Cache
To protect operations against cloud IoT outages or rate limits, verified hourly means are persisted to `data/telemetry/thingspeak_hourly_cache.json`. When internet connectivity drops during severe monsoon storms, the forecast runner reads verified observations directly from this persistent local cache.

---

## 3. Mathematical Accuracy Metrics (`telemetry_metrics.py`)

For $n$ matched prediction-observation pairs $(S_{sim,i}, S_{obs,i})$ over the forecast horizon:

### 3.1 Root Mean Square Error (RMSE)
Measures the standard deviation of stage residuals, penalizing large peak errors:

$$RMSE = \sqrt{\frac{1}{n} \sum_{i=1}^n \left(S_{sim,i} - S_{obs,i}\right)^2} \quad (\text{meters})$$

### 3.2 Mean Absolute Error (MAE)
Quantifies the average magnitude of absolute errors:

$$MAE = \frac{1}{n} \sum_{i=1}^n \left|S_{sim,i} - S_{obs,i}\right| \quad (\text{meters})$$

### 3.3 Percent Bias (PBIAS)
Measures average tendency of simulated values to be larger or smaller than observations:

$$PBIAS = \frac{\sum_{i=1}^n \left(S_{sim,i} - S_{obs,i}\right)}{\sum_{i=1}^n S_{obs,i}} \times 100\%$$

Low positive values indicate slight overestimation bias; negative values indicate underestimation.

### 3.4 Nash-Sutcliffe Efficiency (NSE)
Normalised statistic determining the relative magnitude of the residual variance compared to measured data variance:

$$NSE = 1 - \frac{\sum_{i=1}^n \left(S_{obs,i} - S_{sim,i}\right)^2}{\sum_{i=1}^n \left(S_{obs,i} - \bar{S}_{obs}\right)^2}$$

### 3.5 Spearman Rank Correlation ($\rho$)
Non-parametric measure of monotonic relationship between forecast and observed hydrographs:

$$\rho = 1 - \frac{6 \sum_{i=1}^n d_i^2}{n(n^2 - 1)}, \quad d_i = \operatorname{rank}(S_{sim,i}) - \operatorname{rank}(S_{obs,i})$$

### 3.6 Pearson Coefficient of Determination ($R^2$)
Measures the proportion of the variance in observed stage explained by linear forecast correlation:

$$r = \frac{\sum (S_{sim} - \bar{S}_{sim})(S_{obs} - \bar{S}_{obs})}{\sqrt{\sum (S_{sim} - \bar{S}_{sim})^2 \sum (S_{obs} - \bar{S}_{obs})^2}}, \qquad R^2 = r^2$$

---

## 4. Skill Reliability & Low-Flow Variance Guards

Standard hydrologic metrics can report misleading or mathematically invalid results if applied naively during baseflow periods. HydroCast implements strict safety guards:

### 4.1 Sample Size Gating ($n \ge 6$)
Statistical ranking and efficiency require a representative sample window:
- If matched observation points $n < 6$ (`MIN_CORRELATION_SAMPLES`), the evaluation status reports `ACCUMULATING_TELEMETRY`.
- Skill metrics ($NSE, \rho, R^2$) are reported as `None` rather than computing noisy values from sparse data.

### 4.2 Low-Flow Variance Floor ($\text{std}(S_{obs}) < 0.05$ m)
During dry-spell baseflow conditions, river water level remains essentially flat ($\text{std}(S_{obs}) < 0.05$ m). Under these conditions:

$$\sum_{i=1}^n \left(S_{obs,i} - \bar{S}_{obs}\right)^2 \to 0$$

Because the denominator of the NSE equation approaches zero, any minor sub-centimeter sensor ripple causes the NSE score to explode into large negative numbers (e.g. $-500.0$), falsely signaling catastrophic model failure when the model is actually tracking baseflow within centimeters.

**The Guard:** When $\operatorname{std}(S_{obs}) < 0.05\text{ m}$ (`MIN_OBS_STAGE_STD_M`) or observed variance is below $10^{-4}$ (`NSE_VARIANCE_FLOOR`), $NSE$ is reported as `None`, and the cycle is classified as:
- `BASEFLOW_STABLE`: if $RMSE \le 0.15\text{ m}$
- `BASEFLOW_MISMATCH`: if $RMSE > 0.15\text{ m}$

### 4.3 Derived Discharge Attribution Warning
Ultrasonic radar measures water stage elevation directly. Discharge is derived by pushing observed stage through the official PCHIP rating curve. To maintain scientific integrity:
- Discharge metrics are explicitly flagged with `discharge_metrics_source = "RATING_IMPLIED_DERIVED"`.
- Payloads carry an explanatory note reminding operators that discharge accuracy is a monotone transformation of stage errors, not an independent acoustic Doppler velocity measurement.

---

## 5. Performance Grading Matrix (Moriasi et al., 2007)

When sample size and variance thresholds are satisfied, the cycle is graded according to international hydrological guidelines:

| Performance Grade | Nash-Sutcliffe Efficiency ($NSE$) | Root Mean Square Error ($RMSE$) | Percent Bias ($PBIAS$) | Operational Interpretation |
| :--- | :---: | :---: | :---: | :--- |
| **`EXCELLENT`** | $NSE \ge 0.75$ | $RMSE \le 0.25\text{ m}$ | $|PBIAS| \le 10\%$ | Highly accurate forecast; safe for automated emergency dispatch |
| **`VERY_GOOD`** | $0.60 \le NSE < 0.75$ | $0.25 < RMSE \le 0.50\text{ m}$ | $10\% < |PBIAS| \le 15\%$ | Dependable forecast matching hydrograph wave structure |
| **`SATISFACTORY`** | $0.40 \le NSE < 0.60$ | $0.50 < RMSE \le 1.00\text{ m}$ | $15\% < |PBIAS| \le 25\%$ | Acceptable guidance; advisory review recommended |
| **`MODERATE_BIAS`** | $0.0 < NSE < 0.40$ | $RMSE > 1.00\text{ m}$ | $|PBIAS| > 25\%$ | Timing or volume drift; manual scrutiny required |
| **`CALIBRATION_REQUIRED`** | $NSE \le 0.0$ | Any | Any | Model performs worse than the mean; triggers recalibration |
