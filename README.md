# DUT's Pyramidal Image Mosaic

---

<h4 align="center">
  <a href="#mpi-wafer-probe-station-image-scanner"> MPI Wafer Probe Station Image Scanner</a>
  <span> | </span>
  <a href="#stitching---pyramidal-image">Stitching Pyramidal Image</a>
  <span> | </span>
  <a href="#example">Example</a>
  <span> | </span>
</h4>

---


## MPI Wafer Probe Station Image Scanner

Python script for automatically moving an MPI probe-station chuck and capturing microscope images over a **rectangular area** or a **circular wafer area** through **GPIB / VISA**.

The script is intended for automated wafer/die(s)/calkit inspection, DUT mosaic creation, and long microscope acquisition sequences.

---

## Features

- GPIB communication through `PyVISA`
- Automatic chuck X/Y positioning
- Microscope snapshot capture
- Rectangular raster scanning
- Circular wafer scanning
- Configurable X/Y step sizes
- Optional edge margin around the circular scan area
- Snapshot filenames containing:
  - image index
  - actual chuck X coordinate
  - actual chuck Y coordinate
  - autofocus Z value
- Resume support after an interrupted circular scan
- Configurable snapshot delay and mechanical settling time
- Automatic return to the initial chuck position
- Graceful interruption with `Ctrl+C`
- Optional debug output
  
---

## Stitching - Pyramidal Image

## Example
