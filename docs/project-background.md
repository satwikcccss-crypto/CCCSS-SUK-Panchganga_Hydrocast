# Project Background

## The problem

The Panchganga drains a 1 837 km² catchment out of the Sahyadri foothills and
crosses the Kolhapur plateau before joining the Krishna. It is not a large
basin by national standards, and that is precisely why it is a good place to
build this kind of system: the runoff response is fast enough to matter within
hours, and the flood record is short and sharp enough to be documented almost
exhaustively. The 2019 and 2021 events each produced a hydrograph that every
resident of Kolhapur remembers, and both are recorded in the Water Resources
Department stage-discharge sheets at a resolution good enough to calibrate
against.

The operational gap is not a lack of rainfall forecasts. Numerical weather
prediction at nine kilometres is freely available and good enough to be useful
ninety hours ahead. The gap is the translation step: turning a precipitation
field into a number a district officer can act on. That requires a calibrated
runoff model, a defensible stage-discharge relationship anchored to government
records rather than to a regression fitted on the same data it is meant to
predict, and a delivery path that reaches a phone.

## What HydroCast does about it

The system runs four times a day on the 00z, 06z, 12z and 18z cycles. Each
cycle fetches a 90-hour ECMWF IFS HRES forecast, routes it through nine
subbasins and five river reaches, converts the outlet discharge into a water
level at the two gauged sites, checks that level against a six-tier regulatory
ladder, and dispatches a bulletin through Telegram to the district emergency
room. Between cycles, a live ultrasonic sensor on the Shivaji Bridge deck
reports the actual water level hourly, and the difference between what was
forecast and what was observed is fed back into the model parameters for the
next run.

The design decision that shapes everything else is that the rating curve is
taken from the WRD sheet rather than derived. A rating curve fitted to
historical floods will happily reproduce the floods it was fitted on and will
be wrong everywhere else. Anchoring to the government sheet means the discharge
to stage conversion inherits the authority of the record, and the uncertainty
sits in the runoff model where it can be measured and reduced.

## Funding and leadership

The work is funded by the **Department of Science and Technology, Science and
Engineering Research Board (DST-SERB), Government of India**, and is a
collaboration between the Centre for Climate Change and Sustainability Studies
at Shivaji University, Kolhapur and the Yashavantrao Chavan Institute of
Science, Satara.

**Dr. Sachin Shantaram Panhalkar** is the Principal Investigator and Head of
the Department of Geography at Shivaji University, Kolhapur. **Dr. Ganesh
Shankar Nhivekar** is the Co-Principal Investigator, Professor in the
Department of Electronics at YCIS Satara. **Er. Satwik Laxmi Kamlakar Udupi**
(B.Tech Agricultural Engineering) is the developer and engineer responsible for
the implementation.

## The data it stands on

**Topography and geoinformatics.** High-resolution digital elevation models
from SRTM and Cartosat are the basis for basin delineation, subbasin
clustering, and the longitudinal river-bed profiles. The delineation is
published as GeoJSON — nine subbasin polygons and the stream network across
the Panchganga — and is what the interactive map at the top of the
[home page](index.md) renders.

**Numerical weather prediction.** Open-Meteo provides a free REST interface to
the ECMWF IFS HRES 9 km grid, which the system queries for lead hours 1 to 90
at hourly resolution across the catchment bounding box. Responses are cached
for an hour and retried with exponential backoff and full jitter, so a
transient upstream failure does not cost a cycle.

**Ground truth on the ground.** Twenty Water Resources Department rain gauges
across the catchment supply hourly observed depth. These do not drive the
forecast — they are what the forecast is checked against. A separate
solar-powered ultrasonic level sensor on the Shivaji Bridge deck publishes
water level to a ThingSpeak channel and is the sole input to the closed-loop
recalibration.

**Hydraulic record.** The Maharashtra WRD stage-discharge sheets supply 27
anchored stage-discharge pairs for the Rajaram weir, converted from the
published cusec values. These anchors are the spine of the rating curve; the
Shivaji curve is the same discharge set with every stage shifted by the 0.648 m
difference in surveyed bed level between the two sites. Channel cross-section
geometry and surveyed bed slopes support a Divided Channel Method treatment of
overbank flow, used where no government rating exists.

## Where to go next

The [System Novelty](novelty-of-this-system.md) page sets out what this
approach does that a conventional warning system does not. The
[Architecture Atlas](architecture-atlas.md) is the engineering reference, with
eight annotated flow diagrams covering the system end to end. The
[Engineering Autopsy](errors-and-engineering-assumptions.md) page is the most
useful one to read before trusting any single number — it records the modelling
errors that have already been found and fixed, and the physical approximations
that remain in force.
