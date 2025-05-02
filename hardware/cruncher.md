---
title: Cruncher
---

[inertial]: https://inertial.science
[cci]: https://drexel.edu/cci/

Cruncher is the [INTERTIA Lab's][inertial] compute server in the datacenter at
the [Drexel College of Computing and Informatics][cci].  We use it for a lot of
our recommendation runs.

## Specs

CPU
:   2x AMD EPYC 7662 (64 cores, 128 threads, 2GHz)

Memory
:   256 GiB

GPU
:   NVidia A40 (48GB)

Storage
:   SSD (home directory + software), network-attached redundant spinning disks (experiment data)

Operating system
:   Ubuntu 24.04

Idle power draw
:   220 watts

## Power Measurement {#power}

Chassis power is measured by the input power reported by the PSUs to the ASUS
ASMB10-iKVM.  We collect power readings from the iKVM over the Redfish interface
and record them in Prometheus.

CPU power is reported by RAPL through Linux `powercap`, and GPU power is reported
by the NVidia Datacenter GPU Monitor.

:::{.callout-note}
This is a shared machine, so power consumption records are not always
well-isolated from other workloads.
:::
