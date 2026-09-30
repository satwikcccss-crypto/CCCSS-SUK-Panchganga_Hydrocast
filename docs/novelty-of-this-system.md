# System Novelty

## What "novel" means here

Most of the individually available pieces — a rainfall-runoff model, a rating
curve, a database, a chart — are decades old. The novelty of HydroCast is not
in any one of them. It is in four *combinations* that are unusual together, and
in the operational contract that makes them usable by a district officer
rather than only by the person who built them.

This page is deliberately written against the source code, not against the
original design intent. Several claims that appeared in earlier drafts of this
page could not be reproduced in the repository and have been corrected or
removed; the [Engineering Autopsy](errors-and-engineering-assumptions.md) page
records the full list. Where a design goal is not yet implemented, that is said
plainly.

## 1. The rating curve is anchored to the record, not fitted to it

The most consequential design decision is that the discharge-to-stage
conversion is not a regression. It is a shape-preserving interpolation through
the Maharashtra WRD stage-discharge sheet: 27 anchored pairs for the Rajaram
weir, spanning 528.67 m to 548.00 m, fitted with a monotone Piecewise Cubic
Hermite Interpolating Polynomial.

PCHIP is chosen specifically because it enforces

$$
\frac{dQ}{dh} > 0 \quad \text{for all } h \in [528.67, 548.00]
$$

without the operator intervention a Manning or power-law fit requires. A single
unsegmented Manning exponent across a compound channel produces non-physical
behaviour — overbank stages get steeper than the channel implies, and
freeboard stages can come out *below* bankfull discharge. Those are not small
errors; they are the curve becoming non-monotonic, which means the same
discharge maps to two stages and the alert ladder stops being a function.

The second site, Chhatrapati Shivaji Maharaj Bridge, uses the same anchor set
shifted by the surveyed bed difference. Because the shift is a pure constant
offset, the relationship

$$
\text{Stage}_{\text{Rajaram}} - \text{Stage}_{\text{Shivaji}} = 0.648 \ \text{m}
$$

holds exactly at every anchor, and this is asserted in the hydrology test
suite. Two sites, 3.8 km apart, one government record.

!!! note "A Manning / divided-channel fallback exists but is unreachable"
    `src/hydrology/rating_curves.py` contains a full Divided Channel Method
    implementation for deriving a curve from surveyed cross-sections where no
    government rating exists. It is real code and it is tested. It is also
    never invoked: `compute_stage_from_discharge` takes the PCHIP path for both
    sites unconditionally, and the Manning branch behind it is unreachable in
    the current call graph. Earlier revisions of this page described the
    system as using a "dual-regime PCHIP with Manning fallback". It does not.

## 2. The station router is biased toward over-warning, on purpose

Conventional gauge-to-subbasin assignment averages, or applies static Thiessen
weights. Both are wrong in the Western Ghats for the same reason: the rainfall
field is orographic, so a subbasin draining from a 680 m crest and a subbasin
draining to a 550 m plain should not receive the same depth.

HydroCast takes the maximum 90-hour cumulative depth among the stations
assigned to each subbasin, and uses that station as the governing boundary
condition for the cycle. The [Rain Gauge Network](raingauge-network.md) page
has the full algorithm; the relevant point here is the *asymmetry*. Averaging
is unbiased. The maximum is not. It is chosen because the two error modes are
not symmetric in consequence: a forecast that peaks high and early is a
withdrawn warning, and a forecast that peaks low and late is a flood that
arrived after the evacuation order was placed. The router is deliberately
conservative.

Nine subbasins and 20 stations make this tractable. It also means a single
misreporting gauge can dominate a subbasin — which is why the physical-range and
coverage gates in `src/processing/validator.py` run *before* selection rather
than after.

## 3. The model is calibrated continuously against a live sensor

The third combination is a closed loop between a hydrologic forecast and a
physical level measurement at the point of interest. An ultrasonic sensor on
the Shivaji Bridge deck publishes water level hourly to ThingSpeak channel
`3424513`; `src/hydrology/realtime_telemetry_validator.py` reads it, applies a
five-gate admission check, and stores accepted observations in
`run_telemetry`; `src/hydrology/ml_calibration.py` then compares the observed
stage against what the current model predicted and, when they disagree, refits
the parameters and writes them back for the next cycle.

The gate is deliberately narrow, because a feedback loop on a noisy signal
learns noise. Recalibration fires only when the timing error exceeds **1.0 h**
or the rising-limb stage error exceeds **0.25 m**. Either one alone is a
signature of a structural model error rather than of measurement jitter.

The optimiser is bounded on every parameter, and the bounds are the point:

| Parameter | Bound | Physical meaning of the bound |
|---|---|---|
| Runoff scale α | [0.50, 1.80] | Loss terms cannot be scaled below half or doubled |
| Lag scale β | [0.50, 1.80] | Travel time is similarly constrained |
| Curve Number Δ | ±8.0 | A single event cannot rewrite the catchment's soil character |
| Reach X (fall factor) | [0.15, 0.40] | Physically meaningful channel friction range |

An unbounded fit on a 90-hour hydrograph with two free parameters will happily
drive a Curve Number to 20 or 95 and call it a better model. The bounds exist so
that the closed loop can correct drift without becoming the drift. Writes are
atomic — a `.bak` copy is taken and replaced via `os.replace`, so a crash
mid-write leaves the previous state intact rather than a truncated file.

!!! warning "The closed loop cannot trigger in a live deployment"
    The gate requires **two** accepted stage observations above 520.0 m. Fresh
    telemetry is written to `run_telemetry` with a `status` of `fresh`, and the
    gate queries only for `status = 'validated'`. Nothing in the current
    pipeline promotes a `fresh` row to `validated`, so the count is always zero
    and the optimiser never runs. The ML calibration path is therefore
    currently exercised by tests and not by the scheduler. The write-back logic
    is sound; the trigger needs a validation step wired into step 08.

!!! warning "Observed discharge is currently circular"
    The discrepancy is computed by converting *observed stage* to discharge
    through the forecast rating curve and comparing it against forecast
    discharge. That comparison asks the rating curve whether the rating curve is
    right. An independent discharge measurement — or a stage-domain comparison
    against the forecast stage — is needed for the loop to be informative.

## 4. The pipeline cannot take the flood offline

Three failure modes have historically killed flood forecasting systems, and each
has a specific countermeasure here.

**Missing native hydrologic binaries.** HEC-HMS is a Java application; its DSS
output libraries are harder still to install. If Java, the HEC-HMS install, or
the DSS libraries are missing, the runner falls back to a pure-Python
vectorised implementation of the same model. The cycle completes, and the
provenance of every result is recorded.

**Database outage.** `src/db/connection.py` tries the Supabase pooler host
before the direct host, because GitHub Actions runners are frequently
IPv6-only. A cycle that cannot reach Postgres does not crash the API — the
backend reads archived run documents from `data/runs/`.

**Silent degradation.** A run that quietly produced nothing is more dangerous
than one that failed. The step-log contract requires **10** successful steps for
`pipeline_ok`, the API health check surfaces `last_run_ok`, and
`pipeline_step_log` records per-step status with JSON detail.

!!! note "The degradation paths currently disagree with each other"
    The fallback emulator is genuinely used — CI installs neither Java nor
    HEC-HMS, so every automated run exercises it. But the orchestrator's own
    step-log expectation does not match what the orchestrator writes: it
    requires 10 successes while the step list contains 12 entries, so
    `pipeline_ok` is false on every cycle that actually completed. Separately,
    `data/hms/compute/Run_1.dss` is never parsed; the emulator result is
    returned with `result_source` set to `EMULATOR_PYTHON` even when the binary
    reports `COMPLETED_BINARY`. The resilience is real; the bookkeeping that
    describes it is not yet correct.

## 5. What the system scores itself on

A forecast system that does not measure its own accuracy is not auditable.
Metrics are computed every cycle in `src/processing/metrics.py`:

- **Spearman rank correlation** between the forecast stage series and the
  validated observed stage series. Rank-based, so it is insensitive to the
  scale error that dominates the first version of any rating curve.
- **Nash-Sutcliffe Efficiency** on the stage hydrograph.
- **Volumetric bias** as a percentage of simulated volume against observed.
- **Rainfall fidelity** across the gauge network, reported per station and per
  subbasin so that a single dominant subbasin cannot hide inside a basin-wide
  average.

These are logged into the cycle payload and surfaced on the dashboard as KPI
badges. The intent is that a reader can see not just what the model predicted
but how well it has been predicting, on the same screen, without running a
notebook.

## 6. The run ledger

Every cycle writes an immutable, timestamped JSON document to
`data/runs/{cycle_id}.json`. The dashboard's Accuracy & Run Log view lists past
cycles and can load any one back into the hydrographs, scatter plot and
prediction tables.

This is the least technically sophisticated feature in the system and the one
that matters most in a post-disaster inquiry. A flood system that overwrites
its previous state cannot be questioned — including by the people who operate
it. The ledger means a question like "what did the model say 72 hours before
the 2021 event, and how far off was it?" has an answer that is recoverable
from disk rather than reconstructed from memory.

## 7. The comparison

The table below is scoped to what the code does. Where a capability is planned
rather than implemented, that is stated.

| Capability | Traditional CWC/IMD | Academic desktop model | Generic IoT dashboard | HydroCast |
|---|---|---|---|---|
| Forecast lead time | 12–24 h | 48–72 h | 0 h (observed only) | 90 h |
| Operational automation | Manual bulletins | Manual desktop run | Automated telemetry only | Autonomous 6-hourly schedule |
| Runoff solver | — | Native HEC-HMS / MIKE 11 | — | Native with Python fallback |
| Rating curve | Static 1D table | 2D grid or fitted | None (raw levels) | Monotone PCHIP on 27 WRD anchors |
| Mountain station routing | Arithmetic mean | Thiessen polygons | Single sensor | Max-precipitation governor |
| Soil moisture adaptation | Fixed seasonal CN | Manual input | None | AMC-I/II/III from 90-h forecast signal |
| Adaptive recalibration | Manual, multi-year | Offline batch | None | Bounded closed loop, currently gated off |
| Peak arrival estimate | Day resolution | Single timestamp | None | Peak ± 2.0 h fixed window |
| Ground truth calibration | Approximate gauges | Academic survey | Single station | 27 official WRD anchors |
| Self-reported accuracy | Not published | Post-hoc papers | None | Live Spearman ρ and NSE |
| Historical audit | Fragmented logs | Overwritten files | Time-series graph | Immutable run ledger + inspector |
| Offline resilience | Paper fallback | Licence- and DLL-bound | Cloud-dependent | Python solver + archived run reads |
| Alert dispatch | Manual VHF/fax | None | SMS threshold | Telegram bulletin + WebSocket push |
| Deployment | Installed on desktops | Proprietary workstation | Cloud SaaS | Docker Compose, scheduled |

## 8. Honest limits

Four things are not yet true, and are listed here so that a reader does not
have to discover them.

- **Recalibration does not run in production.** The telemetry status promotion
  described in novelty 3 is not wired into the pipeline.
- **The `pipeline_ok` flag is always false.** The expected step count and the
  actual step list disagree.
- **Result provenance is not always truthful.** `result_source` reports the
  emulator even when HEC-HMS reports a completed binary, because the DSS file
  is never read.
- **The peak window is a constant.** The ±2.0 h margin in
  `src/processing/alert_generator.py` is a fixed `margin_hours` value applied
  symmetrically around the argmax of the discharge series. It is not derived
  from a forecast-error distribution. It is a defensible default, and it is
  documented as a confidence interval in places it should be documented as an
  assumption.

None of these are modelling errors. They are integration gaps, and they are
tracked in the [Engineering Autopsy](errors-and-engineering-assumptions.md).
