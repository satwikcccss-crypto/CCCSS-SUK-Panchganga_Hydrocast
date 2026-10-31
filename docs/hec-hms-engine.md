# Dual-Engine Hydrologic Strategy & HEC-HMS Automation

HydroCast deploys a **dual-engine hydrologic computing architecture** designed for high-consequence operational flood forecasting across the 1,837.213 km² Panchganga River basin. The system pairs the gold-standard physical benchmark—the United States Army Corps of Engineers (USACE) **HEC-HMS 4.13**—with an in-house **Pure-Python Vectorized Digital Twin Emulator** (`src/hms/runner.py`).

---

## Interactive diagram consoles

The console below is the rendered reference for this page: it carries the same structure, tier boundaries and failure branches that the prose describes.

<div class="hydrocast-diagram-card">
  <div class="hydrocast-diagram-header">
    <div class="hydrocast-diagram-title">
      <span class="hydrocast-diagram-badge">Interactive Console · Diagram 14</span>
      <strong>Dual-Engine HEC-HMS & Digital Twin</strong>
    </div>
    <div class="hydrocast-diagram-actions">
      <a class="hydrocast-diagram-btn" href="../diagrams/14-hec-hms-engine.html" target="_blank">Open Fullscreen ↗</a>
    </div>
  </div>
  <iframe class="hydrocast-diagram-frame" src="../diagrams/14-hec-hms-engine.html?embed=1" title="Dual-Engine HEC-HMS Console"></iframe>
</div>

<div class="hydrocast-diagram-card">
  <div class="hydrocast-diagram-header">
    <div class="hydrocast-diagram-title">
      <span class="hydrocast-diagram-badge">Interactive Console · Diagram 07</span>
      <strong>HydroSim 2D Handoff</strong>
    </div>
    <div class="hydrocast-diagram-actions">
      <a class="hydrocast-diagram-btn" href="../diagrams/07-workflow-hydrosim-handoff.html" target="_blank">Open Fullscreen ↗</a>
    </div>
  </div>
  <iframe class="hydrocast-diagram-frame" src="../diagrams/07-workflow-hydrosim-handoff.html?embed=1" title="HydroSim 2D Handoff Console"></iframe>
</div>

---

## 1. Dual-Engine Technical Differentiation

The two engines serve distinct operational roles: native HEC-HMS provides regulatory institutional legitimacy and authoring verification, while the Python Twin provides sub-20 ms vectorized compute for real-time API responses, automated 6-hourly pipelines, and iterative Levenberg-Marquardt parameter optimization.

| Engineering Dimension | Native USACE HEC-HMS 4.13 Automation | Pure-Python Vectorized Twin Emulator |
| :--- | :--- | :--- |
| **Primary Code Unit** | `src/hms/runner.py::_execute_hec_hms_core` | `src/hms/runner.py::compute_emulator_hydrograph` |
| **Execution Medium** | Subprocess batch execution via headless Jython | Pure Python 3 / NumPy vectorized matrix operations |
| **Control File** | Patched `data/hms/HMS_Automation_RJKT/Control_1.control` | In-memory timestamp index ($0 \dots \text{sim\_hours}-1$) |
| **Automation Script** | Auto-generated `compute.jy` | Direct Python in-process function invocation |
| **Input Forcing** | HEC-DSS binary file records via `pydsstools` | Hyetograph array dictionary `subbasin_hyetographs` |
| **Execution Latency** | **14.8 – 15.2 seconds** | **< 20 milliseconds (~750× speedup)** |
| **Platform Portability** | Windows-centric (requires Java runtime & `heclib.dll`) | 100% OS-agnostic (runs on Linux, macOS, Docker, CI) |
| **Reach Routing Stability** | Standard Muskingum; flags **WARNING 41169** on long reaches | **Dynamic sub-stepping** ($N_{steps}$); eliminates WARNING 41169 |
| **Volume Conservation** | May lose volume when $C_0 < 0$ or $C_2 < 0$ | Guaranteed $\sum Q_{\text{out}} = \sum Q_{\text{in}}$ within $10^{-4}$ tolerance |
| **Primary Use Cases** | Authoritative desktop validation; regulatory compliance | Real-time web API, Levenberg-Marquardt calibrator, CI/CD |
| **Output Run Status** | `COMPLETED_BINARY` | `CALIBRATED_RJKT` |

---

## 2. Native USACE HEC-HMS 4.13 Automation

### 2.1 Project Layout & File Manifest

The authoritative HEC-HMS watershed model files reside in `data/hms/HMS_Automation_RJKT/`:

| File Name | Purpose & Physical Content |
| :--- | :--- |
| `HMS_Automation_RJKT.hms` | Master project definition linking basin, meteorology, and control specs. |
| `Basin_1.basin` | Authoritative catchment topology: 9 subbasins, 5 Muskingum reaches, junctions, and sinks. |
| `Basin_1.sqlite` | Geospatial SQLite cache containing delineated stream networks and subbasin boundaries. |
| `Control_1.control` | Simulation control specification: start/end dates, times, and 60-minute time step. |
| `Met_1.met` | Meteorological model specification for gage-based spatial precipitation interpolation. |
| `HMS_Automation_RJKT.gage` | Rain gauge registry referencing external meteorological time-series records. |
| `compute.jy` | Headless Jython automation script generated dynamically before execution. |
| `Run_1.dss` | Primary binary Direct Access Storage System (HEC-DSS) archive storing output hydrographs. |
| `Run_1.log` | Execution log file capturing engine convergence, routing steps, and warnings. |

### 2.2 Binary Path Discovery (`find_hec_hms`)

The automation pipeline dynamically searches for local HEC-HMS installations:

1. **Environment Overrides:** Checks `HEC_HMS_PATH` and `HMS_HOME`.
2. **Windows Installation Candidates:**
   - `C:\Program Files\HEC\HEC-HMS\4.13\HEC-HMS.exe`
   - `C:\Program Files\HEC\HEC-HMS-4.13\HEC-HMS.exe`
   - `C:\Program Files\HEC\HEC-HMS-4.10\hec-hms.cmd`
   - Versions 4.12, 4.11, 4.10 in standard installation paths.
3. **Linux / Container Candidates:**
   - `/opt/hec-hms/hec-hms.sh`
   - `/usr/local/hec-hms/hec-hms.sh`
4. **Failsafe Bypass:** If `HMS_FORCE_EMULATOR=1` is set in `.env` or `PYTEST_CURRENT_TEST` is present in the environment, native execution is bypassed in favor of the Python twin.

### 2.3 Dynamic Simulation Window Control & Restoration Pattern

To synchronize HEC-HMS execution with each 6-hourly cycle without permanently altering git-tracked configuration files, `src/hms/runner.py` uses a strict snapshot-patch-restore bracket pattern:

```python
# 1. Snapshot pristine control specification into memory
snapshot_control_spec()

try:
    # 2. Patch simulation window for current forecast cycle (e.g. 03 Sep 2026 06:00 to 07 Sep 2026 00:00)
    patch_control_spec(start_dt, end_dt, time_step_min=60)

    # 3. Write Jython automation script
    write_jython_script(hms_dir, project_name="HMS_Automation_RJKT", run_name="Run 1")

    # 4. Launch headless subprocess
    subprocess.run([hms_bin, "-s", "compute.jy"], cwd=hms_dir, check=True, timeout=300)
finally:
    # 5. Guaranteed restoration: pristine control spec written back to disk
    restore_control_spec()
```

### 2.4 Headless Jython Automation (`compute.jy`)

The Jython execution script targets the official HEC-HMS 4.13 Java API:

```python
# HEC-HMS 4.13 Batch Compute Script (compute.jy)
from hms.model.Project import Project

print "Opening HEC-HMS Project: E:/hydrocast_complete/data/hms/HMS_Automation_RJKT/HMS_Automation_RJKT.hms"
project = Project.open("E:/hydrocast_complete/data/hms/HMS_Automation_RJKT/HMS_Automation_RJKT.hms")

print "Executing simulation run: Run 1"
project.computeRun("Run 1")

print "Closing HEC-HMS Project..."
project.close()
print "HEC-HMS Computation Finished Successfully."
```

### 2.5 HEC-DSS Six-Part Pathname Architecture

Input precipitation hyetographs and computed discharge hydrographs are archived in USACE HEC-DSS binary format using `pydsstools`. Record identifiers follow the standardized six-part convention:

```
  / A / B / C / D / E / F /
```

- **Part A (Project / Basin):** `PANCHGANGA`
- **Part B (Hydrologic Element):** `S1` through `S9` (subbasins), `R1` through `R5` (reaches), or `J_OUTLET` (outlet junction)
- **Part C (Data Parameter):** `PRECIP-INC` (incremental rainfall, mm) or `FLOW` (discharge, m³/s)
- **Part D (Start Timestamp):** e.g. `03SEP2026:0600`
- **Part E (Sampling Interval):** `1HOUR`
- **Part F (User / Version Qualifier):** `FORECAST`, `OBSERVED`, or `RUN:RUN_1`

---

## 3. Pure-Python Vectorized Digital Twin Emulator

Implemented in `src/hms/runner.py::compute_emulator_hydrograph`, the digital twin reproduces the full hydrologic continuum across all 9 subbasins and 5 reaches in less than 20 milliseconds.

```
           [ Subbasin S6: Gaganbawda ]    [ Subbasin S7: Garivade ]
                         \                      /
                          +----> Reach R5 <----+
                                    | (K=4.619h, n=2 passes)
 [ Subbasin S9: Radhanagari ]       |
              \                     |
         Reach R4                   |     [ Subbasin S8: Beed ]
      (K=1.224h, n=1)               |             /
              \                     v            /
               +----------------> Reach R2 <----+
                                (K=11.827h, n=5 passes)
                                    |
 [ Subbasin S4 ]   [ Subbasin S5 ]  |
        \                /          |
         +--> Reach R3 <-+          |
         (K=3.829h, n=2 passes)     |
                 \                  v
                  +-------------> Reach R1 <--- [ Subbasin S3: Kotoli ]
                                (K=2.899h, n=2)  [ Subbasin S2: Sangarul ]
                                    |
                                    v
                           Basin Sink-1 (Rajaram)
                           + Direct S1 Runoff (Karveer)
                           + Baseflow Recession Q_bf(t)
```

### 3.1 Dynamic Antecedent Moisture Condition (AMC) Tracking

Soil moisture state dynamically scales Curve Numbers using TR-55 non-linear transformations based on the 90-hour basin-mean precipitation $\bar{P}_{90h}$:

$$\text{AMC} = \begin{cases} \text{AMC-I (Dry)} & \text{if } \bar{P}_{90h} < 25.0\text{ mm} \\ \text{AMC-II (Normal)} & \text{if } 25.0 \le \bar{P}_{90h} < 65.0\text{ mm} \\ \text{AMC-III (Saturated)} & \text{if } \bar{P}_{90h} \ge 65.0\text{ mm} \end{cases}$$

Non-linear Curve Number adjustments:

$$CN_{\text{I}} = \frac{4.2 \cdot CN_{\text{II}}}{10.0 - 0.058 \cdot CN_{\text{II}}}, \qquad CN_{\text{III}} = \frac{23.0 \cdot CN_{\text{II}}}{10.0 + 0.13 \cdot CN_{\text{II}}}$$

Initial abstraction $I_a = f_{ia} \cdot S$, where $S = \frac{25400}{CN} - 254$ mm, with dynamic fractions:
- $f_{ia} = 0.20$ for AMC-I
- $f_{ia} = 0.15$ for AMC-II
- $f_{ia} = 0.08$ for AMC-III

Incremental precipitation excess $\Delta P_{excess}(t) = \max\left(0, Q_{cum}(t) - Q_{cum}(t-1)\right)$.

### 3.2 Dimensionless Unit Hydrograph Transform

For each subbasin lag time $t_{lag} = \text{lag\_min} / 60.0$ hours:

$$t_p = 0.5 \Delta t + t_{lag} = 0.5 + t_{lag} \quad (\text{hours})$$

$$UH(t) = \left(\frac{t}{t_p}\right)^m \exp\left[m \left(1 - \frac{t}{t_p}\right)\right], \quad m = 3.7$$

The unit hydrograph is normalized so that total volume equals subbasin drainage area:

$$\int_0^\infty UH(t) \, dt = Area_{km^2} \times 10^3 \, \text{m}^3$$

Direct surface runoff is computed via discrete convolution:

$$Q_{direct}(t) = \sum_{\tau=0}^t \Delta P_{excess}(\tau) \cdot UH(t - \tau)$$

---

## 4. Elimination of HEC-HMS WARNING 41169 via Sub-Stepped Routing

### 4.1 Root Cause of WARNING 41169

In standard HEC-HMS 4.13 simulations, Muskingum reach routing uses fixed parameter pairs: travel time $K$ (hours) and dimensionless weighting factor $X$ (typically $0.20$).

The classic Muskingum recurrence equation is:

$$O_t = C_0 I_t + C_1 I_{t-1} + C_2 O_{t-1}$$

Where routing coefficients are:

$$C_0 = \frac{\Delta t - 2 K X}{2 K (1 - X) + \Delta t}, \quad C_1 = \frac{\Delta t + 2 K X}{2 K (1 - X) + \Delta t}, \quad C_2 = \frac{2 K (1 - X) - \Delta t}{2 K (1 - X) + \Delta t}$$

For numerical stability and physical validity, the routing time interval $\Delta t$ must satisfy the Courant-Muskingum stability band:

$$2 K X \le \Delta t \le 2 K (1 - X)$$

When $\Delta t < 2 K X$, coefficient $C_0$ becomes **negative**. Conversely, when $\Delta t > 2 K (1 - X)$, coefficient $C_2$ becomes **negative**.

In the Panchganga basin, reach **R2 (Middle Panchganga Trunk)** has $K = 11.827$ hr and $X = 0.200$. With a standard 1-hour simulation time interval ($\Delta t = 1.0$ hr):

$$\Delta t - 2 K X = 1.0 - 2(11.827)(0.200) = 1.0 - 4.731 = -3.731 < 0 \implies C_0 = -0.187 < 0$$

HEC-HMS logs this critical error:
```
WARNING 41169: Muskingum reach R2 parameters K=11.827 and X=0.200 violate stability criteria.
C0 is negative (-0.187). Numerical oscillations and mass loss may occur.
```
Negative coefficients cause artificial numerical dips below zero, unphysical wave deformation, and catastrophic loss of volume conservation.

### 4.2 Dynamic Sub-Stepping Algorithm

HydroCast's twin emulator resolves this by dynamically calculating the permissible sub-divided travel time $K' = K / N_{steps}$ such that both stability bounds are simultaneously satisfied:

$$K_{lim,hi} = \frac{\Delta t}{2 X} \implies N_{steps} \ge \left\lceil \frac{K}{K_{lim,hi}} \right\rceil$$

$$K_{lim,lo} = \frac{\Delta t}{2 (1 - X)} \implies N_{steps,lo} \ge \left\lfloor \frac{K}{K_{lim,lo}} \right\rfloor$$

$$N_{steps} = \max\left(1, \min\left(\left\lceil \frac{K}{K_{lim,hi}} \right\rceil, \left\lfloor \frac{K}{K_{lim,lo}} \right\rfloor\right)\right)$$

### 4.3 Reach Sub-Step Coefficient Matrix and Mass Conservation

The canonical reach parameters $K$ and $X$ are defined in [Catchment Hydrology: Muskingum Reaches](basin-hydrology.md#muskingum-reaches). Based on these values, the dynamic sub-stepping algorithm evaluates the following coefficient matrix:

| Routing Reach | River Segment | Sub-Step Passes ($N_{steps}$) | Sub-Divided $K'$ (hr) | $C_0$ | $C_1$ | $C_2$ | Numerical Stability Impact |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---|
| **R5** | Upper Kumbhi / Dhamani | **2 passes** | 2.310 | 0.016 | 0.410 | 0.574 | Non-negative ($C_0, C_1, C_2 \ge 0$) |
| **R4** | Bhogawati River Trunk | **1 pass** | 1.224 | 0.174 | 0.509 | 0.317 | Courant condition satisfied |
| **R2** | Middle Panchganga Reach | **5 passes** | 2.365 | 0.011 | 0.407 | 0.582 | **WARNING 41169 Eliminated** |
| **R3** | Kasari River Main | **2 passes** | 1.915 | 0.057 | 0.432 | 0.511 | Non-negative ($C_0, C_1, C_2 \ge 0$) |
| **R1** | Lower Panchganga Trunk | **2 passes** | 1.450 | 0.126 | 0.478 | 0.396 | Confluence cascade stabilized |

Because every sub-step satisfies $C_0 \ge 0$, $C_1 \ge 0$, $C_2 \ge 0$, and $\sum C_i \equiv 1.000000$, total volume is strictly conserved across all reaches:

$$\sum_{t=0}^{89} Q_{out}(t) = \sum_{t=0}^{89} Q_{in}(t) \quad \left(\text{Relative error } < 10^{-4}\right)$$

This mathematical guarantee is verified on every test execution in `tests/test_runner_emulator.py`.

---

## 5. Golden Regression Baseline (`tests/test_golden_emulator.py`)

To ensure that future enhancements, dependency updates, or calibration refactorings cannot introduce silent numerical drift, HydroCast maintains an automated **golden regression lock**.

### 5.1 Frozen Baseline Values

For a standardized deterministic monsoon storm peaking at hour 30 with $91.1\text{ m}^3/s$ initial baseflow:

| Metric | Golden Baseline Value | Tolerance | Test Assertion |
| :--- | :--- | :--- | :--- |
| **Antecedent Moisture Condition** | `AMC-III` | Exact string match | `assert hg["amc"] == "AMC-III"` |
| **Peak Lead-Time Hour** | $T = 105\text{ hr}$ | Exact integer match | `assert hg["peak_h"] == 105` |
| **Peak Outlet Discharge ($Q_{peak}$)** | **$3,345.6\text{ m}^3/s$** | $\pm 0.5\%$ relative | `pytest.approx(3345.6, rel=0.005)` |
| **Total Hydrograph Volume ($V_{total}$)** | **$754.115\text{ MCM}$** | $\pm 0.5\%$ relative | `pytest.approx(754.115, rel=0.005)` |
| **Surface Runoff Volume ($V_{surface}$)** | **$704,719,669.7\text{ m}^3$** | $\pm 0.5\%$ relative | `pytest.approx(704719669.7, rel=0.005)` |

### 5.2 Determinism Verification

The emulator contains zero unseeded stochastic elements or random variations. The determinism assertion:

```python
def test_emulator_is_deterministic():
    a = _run()
    b = _run()
    assert np.array_equal(a["q_total"], b["q_total"])
    assert np.array_equal(a["q_surface"], b["q_surface"])
```

Verifies that back-to-back evaluations yield bit-identical arrays across all 90 forecast time steps.

---

## 6. Subbasin Parameters & Reaches Matrix

The authoritative physical parameters governing both engines are canonically centralized:

- Delineated drainage areas, baseline Curve Numbers, and Kirpich lag times: **[Catchment Hydrology: Subbasin Parameters](basin-hydrology.md#subbasin-parameters)**.
- Topological connectivity, reach lengths, and routing coefficients: **[Catchment Hydrology: Muskingum Reaches](basin-hydrology.md#muskingum-reaches)**.
- Companion digital twin deep-dive: **[Pure-Python Vectorized Twin Emulator](python-twin-emulator.md)**.
