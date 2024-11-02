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
:   256 GiB (225GiB available)

GPU
:   NVidia A40 (48GB)

Operating system
:   Ubuntu 22.04 (Jammy Dodger)

Storage
:   Network-attached SSD (home directory + software), network-attached redundant spinning disks (experiment data)

Idle power draw
:   295 watts

## Notes

- This machine is hungry; it has dynamic CPU frequency scaling disabled, so it
  is constantly at full power.

- The actual execution environment is also virtualized, which may add a slight
  overhead.

- This is a shared machine, so power consumption records are not always
  well-isolated from other workloads.
