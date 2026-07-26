# DUT's Pyramidal Image Mosaic

---

<h4 align="center">
  <span> | </span>
  <a href="#mpi-wafer-probe-station-image-scanner"> MPI Wafer Probe Station Image Scanner</a>
  <span> | </span>
  <a href="#stitching---pyramidal-image">Stitching Pyramidal Image</a>
  <span> | </span>
  <a href="#example">Visualise the Pyramidal Image</a>
  <span> | </span>
  <a href="#example">Example</a>
  <span> | </span>
</h4>

---


## MPI Wafer Probe Station Image Scanner

Python script for automatically moving an MPI probe-station chuck and capturing microscope images over a **rectangular area** or a **circular wafer area** through **GPIB / VISA**.

The script is intended for automated wafer/die(s)/calkit inspection, DUT mosaic creation, and long microscope acquisition sequences.

### Features

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

(On going : cleaning and merging codes)

---

## Visualize the Pyramidal Image

To visualize the pyramidal image with OpenSeadragon, open a terminal in the directory containing:
* `index.html`
* The `.dzi` files
* Their associated tile folders, usually named `*_files`

Start a local HTTP server using Python:

```bash
python -m http.server 8000
```

Then open the following address in your browser:

```text
http://localhost:8000/
```

The `index.html` file should open automatically. You can also access it directly at:

```text
http://localhost:8000/index.html
```

To stop the server, return to the terminal and press:

```text
Ctrl+C
```

Make sure that the `.dzi` files and their corresponding tile folders remain in the paths referenced by `index.html`.


## Example
