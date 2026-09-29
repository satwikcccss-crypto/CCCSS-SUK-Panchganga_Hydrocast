# Project Background & Information

## Overview
The **IoT and Geoinformatics Based Flood Modelling and Prediction System** (HydroCast) is a state-of-of-the-art, high-resolution hydrological forecasting and river intelligence platform engineered specifically for the Panchganga River Basin in Kolhapur, Maharashtra.

## Funding & Leadership
This system is proudly supported and funded by the **Government of India**.

- **Funding Agency**: DST-SERB (Department of Science and Technology, Science and Engineering Research Board, Government of India)
- **Principal Investigator (PI)**: Dr. Sachin Shantaram Panhalkar (HOD, Dept of Geography, Shivaji University, Kolhapur)
- **Co-Principal Investigator (Co-PI)**: Dr. Ganesh Shankar Nhivekar (Professor, Dept of Electronics, YCIS Satara)
- **Developer & Engineer**: Er. Satwik Laxmi Kamlakar Udupi (B.Tech Ag)
- **Institutions**: Shivaji University, Kolhapur (SUK) & Yashavantrao Chavan Institute of Science (YCIS), Satara.

## Core Datasets & Integrations

The system leverages multiple high-accuracy datasets to perform real-time hydrological and hydraulic modeling:

1. **Topography & Geoinformatics (GIS)**
   - **DEM Data**: High-resolution Digital Elevation Models (SRTM/Cartosat) used for accurate basin delineation, subbasin clustering, and river bed L-section profiling.
   - **GeoJSON Shapefiles**: Spatially indexed boundaries for 9 delineated subbasins (S1-S9) and precise river networks across the 100km stretch of the Panchganga.

2. **Meteorology & Numerical Weather Prediction (NWP)**
   - **OpenMeteo API**: Live integration with global weather models (GFS, ECMWF) to fetch hourly precipitation forecasts dynamically across all subbasins.
   
3. **Ground Truth & IoT Telemetry**
   - **WRD Ground Stations**: 20 Water Resources Department (WRD) historical and live ground rain gauge stations (e.g., Gaganbawda, Radhanagari, Kasari) serve as the absolute ground truth for validating simulated rainfall data.
   - **IoT Sensors**: Live telemetry nodes transmitting local stage/precipitation data directly to the HydroCast backend.

4. **Hydraulics & River Engineering**
   - **Historical Rating Curves**: WRD historical Stage-Discharge rating curves used to convert simulated runoff ($m^3/s$) into precise river water levels ($m \text{ MSL}$) at critical choke points (e.g., Rajaram KT Weir, Shivaji Bridge).
   - **Cross-Section Data**: Channel geometry data used for Divided Channel Method (DCM) modeling of floodplain overbanks (e.g., sugarcane fields) vs. main channel flows.
