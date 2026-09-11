# Adaptive Machine Learning (ML) Calibration Engine

## 1. Introduction
The Panchganga HydroCast system features a **Real-Time Closed-Loop Adaptive ML Calibration Engine**. Unlike traditional static modeling where hydrologic parameters are calibrated once and left unchanged, this system acts like an automated hydrologist. It continuously monitors real-time IoT stage sensors (e.g., at Chhatrapati Shivaji Maharaj Bridge and Rajaram K.T. Weir) and compares the actual river observations with the HEC-HMS modeled hydrographs.

If there is a discrepancy in flood wave arrival time (timing offset) or peak stage magnitude, the ML engine automatically recalculates and synchronizes optimal hydrologic parameters back into the HEC-HMS model (`Basin_1.basin`) before the next forecast cycle.

## 2. Triggering the Calibration
The calibration process is strictly physics-informed and triggered by real-time error detection. The system isolates the **Rising Limb** of the hydrograph to determine the errors:
- **Stage Discrepancy ($\Delta h$)**: The difference between the observed river stage and the forecasted stage.
- **Timing Offset ($\Delta t$)**: Detected by analyzing the rate of rise. A negative $\Delta t$ indicates the wave arrived *early*; a positive $\Delta t$ indicates it arrived *late*.

**Trigger Thresholds**: The ML optimizer fires only when:
- $|\Delta t| \ge 1.0$ hour (Flood wave timing is off by an hour or more).
- $|\Delta h| > 0.25$ m (Stage prediction is off by more than 25 cm during a rising limb).

## 3. Physics-Informed ML Constraints
While a standard Neural Network might propose mathematically "correct" but physically impossible numbers, this pipeline relies on a bounded **SciPy L-BFGS-B Optimization** algorithm. 

As per hydrologic engineering principles, the parameters are strictly constrained within physical limits:

| Hydrologic Parameter | Engineering Meaning | Theoretical Bounds | ML Engine Permissible Bounds |
| :--- | :--- | :--- | :--- |
| **SCS Curve Number (CN)** | Controls runoff volume. Higher CN = higher runoff. | `0 to 100` | Baseline CN $\pm 8.0$ (Strictly clamped between `45.0 - 95.0`) |
| **Subbasin Lag Time ($T_{lag}$)** | Drains the subbasin. Converts runoff volume to a temporal hydrograph (SCS Unit Hydrograph). | $> 0$ | $0.50\times$ to $1.80\times$ of baseline lag time |
| **Muskingum $K$ (Travel Time)** | Travel time of a flood wave through a river reach. | $K > 0$ | $0.50\times$ to $1.80\times$ of baseline reach $K$ |
| **Muskingum $X$ (Attenuation)** | Wedge storage factor. Controls subsidence of the flood wave. | $0.0$ to $0.50$ | `0.15` to `0.40` |

### How the ML Optimizer Learns:
*   **Early Arrival ($\Delta t < 0$)**: The real flood wave is moving faster than the model predicts. The optimizer lowers the Muskingum travel time ($K$) and Subbasin Lag Time ($T_{lag}$) to speed up the modeled routing. It pushes $X$ closer to 0.40 to represent a steep, fast-moving wave with less attenuation.
*   **Late Arrival ($\Delta t > 0$)**: The wave is delayed due to high channel storage. The optimizer increases $K$ and $T_{lag}$, and drops $X$ closer to 0.20 to simulate heavy attenuation.
*   **Volumetric Under-prediction ($\Delta h < 0$)**: The river stage is higher than forecasted. The optimizer increases the SCS Curve Number ($\Delta CN > 0$) because the soil is likely saturated, generating more runoff than expected.

## 4. The Loss Function (Hydrologic Cost)
The ML solver minimizes a custom hydrologic objective function representing the total error. It penalizes timing discrepancies, stage errors, and steepness errors simultaneously, while applying a "regularization" penalty to prevent the parameters from deviating too far from the baseline unless absolutely necessary.

$$ \text{Loss}(\theta) = \text{TimingPenalty}(\Delta t) + \text{StagePenalty}(\Delta h) + \text{RoutingPenalty}(X) + \text{Regularization} $$

The optimizer tests multiple parameter states in milliseconds to find the combination that pushes the Loss as close to zero as possible.

## 5. HEC-HMS Synchronization (The Closed-Loop)
Once the optimal parameters are found, the pipeline permanently modifies the HEC-HMS project:
1. Creates a timestamped backup (`Basin_1.basin.bak_YYYYMMDD_HHMMSS`).
2. Reads the `Basin_1.basin` text file.
3. Uses Regular Expressions (Regex) to update the **Curve Number** and **Lag** entries for all 9 subbasins.
4. Updates the **Muskingum K** and **Muskingum x** entries for all 5 river reaches.
5. Saves the file atomically.

By the time the next 15-minute ECMWF/GFS forecast cycle runs, HEC-HMS boots up with these dynamically corrected parameters, ensuring that the modeled hydrograph seamlessly realigns with the real-world IoT telemetry.
