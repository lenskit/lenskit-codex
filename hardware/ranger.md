---
title: MBP2
---

Ranger is Michael's laptop, a 14" MacBook Pro from 2023.

## Specs

CPU / GPU
:   Apple M2 Pro (10 cores)

Memory
:   32 GB

Storage
:   1TB internal SSD
:   4TB Crucial X10 Pro external SSD (experiments are run from here)

## Notes

Most runs are *without* MPS, as MPS does not support all features used by
LensKit (particularly sparse tensors and embedding bags).

## Power Measurement {#power}

System power consumption for Ranger is measured with the System Power meter
exposed via the SMC.  Michael wrote [smc-exporter][], a small Prometheus
exporter built on the Rust `macsmc` package, to collect power meter values. The
system is also running `node_exporter` with a power script that uses
`powermetrics` to extract CPU power measurements (which we haven't figured
out how to collect from SMC on Apple Silicon).

[smc-exporter]: https://github.com/mdekstrand/smc-exporter

:::{.callout-note}
This machine is Michael's primary desktop, so power consumption usually includes
other light work as well.  It is also a university-managed machine with things like
Microsoft antivirus that increase power draw.
:::
