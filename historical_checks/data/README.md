# Historical Checks — Benchmark Data Registry

This directory contains observed reference telemetry and benchmark datasets used to validate HydroCast's hydrologic and hydraulic engines against historical monsoon flood events.

### Benchmark Events Catalog

| Event ID | Event Description | Location | Peak Observed Stage | Peak Observed Discharge | Observed Data Source |
| :---: | :--- | :--- | :---: | :---: | :--- |
| `2019_august` | August 2019 Super Flood | Rajaram Weir | 546.97 m MSL | 2,111 m³/s | Expert Study Committee Report: Flood 2019 (Krishna Basin) |
| `2021_july` | July 2021 Extreme Flood | Rajaram Weir | 547.83 m MSL | — | Maharashtra Water Resources Department (WRD) Records |
| `2025_august` | August 2025 Monsoon Peak | Shivaji Bridge | 545.68 m MSL | — | ThingSpeak Channel 3424513 (Ultrasonic Sensor, 20,292 readings) |

### Telemetry Datasets
- Cleaned 360-hour hourly observed series: `data/shivaji_bridge_2025_hourly_observed.csv`
- Raw ultrasonic telemetry export: `data/Shivaji Bridge 2025 water levels.csv`
