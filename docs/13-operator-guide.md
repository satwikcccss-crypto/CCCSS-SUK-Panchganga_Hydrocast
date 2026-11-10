# 13 — Operator Guide

## Scope

Day-to-day guide for CCCSS staff and government officials who use the admin console to monitor the system and trigger forecasts. Audience: **Operator**.

## Logging In

1. Open the admin console at `http://localhost:3001` (or your server's address)
2. Enter your username (e.g., `DEV.Satwikcccss@Adm1`) and password
3. Click **Sign In**

### First-Time Login

All @Adm1 accounts are created with the initial password `CCCSS@HydroCast2024`. You will be prompted to change this on first login.

### Forgot Password

1. Click **Forgot password?** on the login page
2. Contact an admin (PI, Co-PI, or developer) and request a reset code
3. The admin generates a 6-digit code from the console (valid for 1 hour)
4. The admin shares the code with you via WhatsApp, phone, or in-person
5. Click **I Have a Reset Code** on the forgot password page
6. Enter your username, the 6-digit code, and your new password

## Console Overview

The admin console is organized like Windows 11 Settings with category groups:

### What You Can See (All Roles)

- **Overview**: Current alert level, peak discharge, bridge stages, last cycle status
- **Gauge Stations**: Rain gauge network with active/inactive status
- **Routing Parameters**: Muskingum reach configuration (read-only for viewers)
- **Governing Station**: Which gauge is driving each subbasin's forecast
- **Hydrograph**: 90-hour discharge and stage charts
- **Rainfall**: Subbasin rainfall distribution
- **Basin Map**: Interactive catchment map with station markers
- **Run Ledger & Accuracy**: Historical runs with NSE, RMSE, Spearman scores

### What Only Operators Can See (dev/admin roles)

- **ML Recalibration**: Calibration parameter history and forced recalibration
- **Pipeline & Diagnostics**: 12-step pipeline status, live logs, SLA metrics
- **Database & Host Health**: PostgreSQL status, disk usage, host hardware

## Monitoring the System

### Alert Levels

| Level | What It Means | What To Do |
|-------|--------------|------------|
| NORMAL (Green) | River is within normal range | No action needed |
| ALERT (Yellow) | Rising water, approaching thresholds | Monitor closely |
| WARNING (Orange) | Flood preparation needed | Notify DDMA, prepare evacuation |
| DANGER (Red) | Flooding imminent or occurring | Execute evacuation plan |
| EXTREME (Purple) | Water above historical flood level | Full emergency response |

### Reading the Overview Panel

- **Peak Discharge**: Maximum predicted flow (m3/s) in the 90-hour forecast
- **Lead Time**: Hours until peak discharge arrives
- **Shivaji Bridge Stage**: Current and forecast water level at the primary gauge
- **Rajaram Weir Stage**: Current and forecast water level at the secondary gauge
- **Last Cycle**: When the last forecast completed and whether it succeeded

## Triggering a Manual Forecast

If you have the `dev` or `admin` role:

1. Navigate to **Pipeline & Diagnostics**
2. Click **Force Forecast**
3. The 12-step pipeline will execute. Watch the step-by-step progress.
4. Results appear in the dashboard within 2-5 minutes.

The system automatically runs forecasts every 6 hours (00, 06, 12, 18 UTC). Manual triggers are for:
- After a sudden weather change
- After system recovery from an outage
- For testing/verification purposes

## User Management (admin role only)

### Creating a New User

1. Navigate to user management (via API or CLI)
2. Specify username, password, role, and email domain
3. Email must be from `unishivaji.ac.in` or `gov.in` (developer exception: `gmail.com`)
4. New government users automatically get the `govt` (read-only) role

### Generating a Password Reset Code

1. From the console or API: generate a reset code for the target username
2. A 6-digit numeric code is returned, valid for 1 hour
3. Share the code with the user via a secure out-of-band channel
4. The user enters the code on the reset page to set a new password

### Deactivating a User

Admins can toggle user accounts active/inactive. Deactivated accounts:
- Cannot log in
- Retain their data for audit purposes
- Can be reactivated later

## CLI User Management

For command-line user management:

```powershell
# List all users
python -m backend.scripts.manage_users list

# Add a user
python -m backend.scripts.manage_users add --username user@unishivaji.ac.in --password TempPass123 --role govt --email user@unishivaji.ac.in

# Generate reset code
python -m backend.scripts.manage_users reset --username DEV.Satwikcccss@Adm1

# Toggle active status
python -m backend.scripts.manage_users toggle --username user@unishivaji.ac.in
```

## Understanding Forecast Accuracy

The Run Ledger shows validation metrics for each cycle:

| Metric | Good | Acceptable | Poor |
|--------|------|------------|------|
| NSE (Nash-Sutcliffe) | > 0.75 | 0.5 - 0.75 | < 0.5 |
| RMSE (metres) | < 0.3 | 0.3 - 0.5 | > 0.5 |
| Spearman rho | > 0.9 | 0.8 - 0.9 | < 0.8 |

If accuracy drops consistently, contact the system maintainer for recalibration.

## Emergency Procedures

### System Is Not Updating

1. Check the Pipeline & Diagnostics panel for error status on any step
2. If the pipeline is stuck, use **Abort** then **Force Forecast**
3. If the API is unreachable, check Windows Services status

### False Alert

1. Verify against actual IoT sensor readings in the Gauge panel
2. If the model is wrong but sensors are correct, note the discrepancy
3. Contact the maintainer for parameter recalibration

### Sensor Offline

1. Check the Gauge panel for OFFLINE status
2. The system continues operating with model-only forecasts
3. Contact the field team (JRF) for sensor hardware check
