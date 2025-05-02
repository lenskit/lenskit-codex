---
title: Screamer
---

[inertial]: https://inertial.science
[cci]: https://drexel.edu/cci/

![Photo of Screamer](../images/screamer.jpg){.float width=300 fig-align="right" fig-alt="A large black gaming tower with three glowing RGB circles around fans on the front, and a bright white diamond logo."}

Screamer is an HP Omen 45L gaming tower owned by the [INTERTIA Lab][inertial],
housed in Michael's office in the [Drexel College of Computing and
Informatics][cci].

## Specs

CPU
:   Intel i9 14900K (8 performance cores, 16 efficiency cores, 3.2GHz base, 6 GHz turbo, liquid cooled)

Memory
:   64 GiB

GPU
:   NVidia GeForce RTX 4090 (24GB)

Storage
:   2TB SSD for software and in-use experiment data; 16TB (usable) RAID1 spinning disk for archival

Operating system
:   Ubuntu 24.04 (Noble Numbat)

Idle power draw
:   81 watts

## Power Measurement {#power}

Chassis power consumption for Screamer is measured with an APC Back-UPS NS
1500M2, using `(LOADPCT / 100) * NOMPOWER`. This is not the most precise
measurement (1% increments of the system's nominal 900W output power), but is
relatively stable.  It is also generally consistent with other measurements
we have taken.

Prior to May 2025, chassis power was measured with a Shelly Wave Plug US.  This
proved to have too many stability problems (random power-downs) to be a viable
long-term measurement solution.

CPU power is measured by the Intel RAPL power model exposed through the Linux
`powercap` interface.  GPU power is measured with NVML's reported GPU power
consumption.
