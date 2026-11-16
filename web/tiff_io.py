"""Read an uploaded TIFF stack with tifffile (as step1_data_loading does), including compressed files the browser
reader refuses, and report the pixel size the file itself records.

Pixel size (um_per_px), in order of preference: OME-XML PhysicalSizeX (um), ImageJ description unit + XResolution,
TIFF ResolutionUnit = centimetre + XResolution. None when the file records no physical scale: the pipeline works in
pixels throughout, so the scale is reported alongside results, never silently assumed.
"""
import io
import re

import numpy as np
import tifffile

_UM = {"micron": 1.0, "microns": 1.0, "um": 1.0, "µm": 1.0, "\\u00B5m": 1.0, "\\u00b5m": 1.0, "nm": 1e-3, "mm": 1e3}


def _pixel_size(tif):
    page = tif.pages[0]
    ome = tif.ome_metadata
    if ome:
        m = re.search(r'PhysicalSizeX="([0-9.eE+-]+)"', ome)
        if m:
            unit = re.search(r'PhysicalSizeXUnit="([^"]+)"', ome)
            f = _UM.get(unit.group(1) if unit else "µm")
            if f:
                return float(m.group(1)) * f, "OME-XML PhysicalSizeX"
    xres = page.tags.get("XResolution")
    if xres is not None:
        num, den = xres.value
        ppu = num / den if den else 0
        ij = tif.imagej_metadata or {}
        f = _UM.get(str(ij.get("unit", "")))
        if ppu > 0 and f:
            return f / ppu, "ImageJ unit + XResolution"
        unit = page.tags.get("ResolutionUnit")
        if ppu > 0 and unit is not None and int(unit.value) == 3:
            return 1e4 / ppu, "TIFF XResolution (pixels per cm)"
    return None, "not recorded in the file"


def read_stack(data: bytes):
    """(stack (T, H, W) as float32, um_per_px or None, where the scale came from)."""
    with tifffile.TiffFile(io.BytesIO(data)) as tif:
        arr = tif.asarray()
        um, source = _pixel_size(tif)
    arr = np.asarray(arr)
    if arr.ndim == 2:
        arr = arr[np.newaxis]
    if arr.ndim != 3:
        raise ValueError(f"expected a single-channel stack (frames, height, width); this file has shape {arr.shape}")
    return arr.astype(np.float32), um, source
