"""
Shared helpers for building human-readable PIEZO1 intensity axis labels.

The plotted intensity depends on two independent sets of choices:

1. How step 1 normalized the images (what the value "100" actually means):
   - method: 'max' (brightest pixel) or 'percentile' (robust to hot pixels)
   - region: 'frame' (whole image) or 'mask' (pixels inside the cell)
   - scope:  'per_frame' (each frame to its own reference) or
             'global' (one reference across the whole stack)
   - scale:  multiplier applied after normalization (e.g. 100)

2. How step 7 aggregated pixels inside each sampling rectangle:
   - statistic: 'mean', 'max' or 'percentile'

These helpers turn those choices into a consistent label such as
``PIEZO1 intensity (mean, % of per-frame max)`` so that step 7/8/9 figures
and the GUI all describe exactly what is being plotted. The label is computed
once in step 7 (which can read step 1's metadata) and threaded forward through
the step 8 and step 9 result files.
"""

import os
import json

DEFAULT_LABEL = "PIEZO1 Intensity"


def _format_ordinal(percentile):
    """Format a percentile as a compact ordinal, e.g. 95 -> '95th', 99.9 -> '99.9th'."""
    try:
        p = float(percentile)
    except (TypeError, ValueError):
        return str(percentile)
    if p == int(p):
        return f"{int(p)}th"
    return f"{p:g}th"


def describe_normalization(meta):
    """Return a short phrase describing what the normalized intensity scale means.

    Parameters
    ----------
    meta : dict
        Contents of step 1's ``metadata.json`` (may be empty or partial).

    Returns
    -------
    str
        e.g. ``"% of per-frame max"`` or ``"% of stack in-mask 99.9th pct"``.
        Returns ``"raw"`` when the data was not normalized.
    """
    if not meta or not meta.get('normalized'):
        return "raw"

    method = meta.get('normalization_method', 'max')
    region = meta.get('normalization_region', 'frame')
    scope = meta.get('normalization_scope', 'per_frame')
    scale = meta.get('normalization_scale', 1.0)

    scope_txt = 'stack' if scope in ('global', 'stack') else 'per-frame'

    if method == 'percentile':
        ref = f"{_format_ordinal(meta.get('normalization_percentile', 99.9))} pct"
    else:
        ref = 'max'

    parts = [scope_txt]
    if region == 'mask':
        parts.append('in-mask')
    parts.append(ref)
    ref_phrase = ' '.join(parts)

    try:
        scale = float(scale)
    except (TypeError, ValueError):
        scale = 1.0

    if abs(scale - 100.0) < 1e-9:
        return f"% of {ref_phrase}"
    if abs(scale - 1.0) < 1e-9:
        return f"fraction of {ref_phrase}"
    return f"×{scale:g} of {ref_phrase}"


def describe_statistic(statistic, percentile=95):
    """Return a short phrase for the per-rectangle aggregation statistic."""
    if statistic == 'max':
        return 'max'
    if statistic == 'percentile':
        return f"{_format_ordinal(percentile)} pct"
    return 'mean'


def build_intensity_label(meta, statistic='mean', percentile=95,
                          base="PIEZO1 intensity"):
    """Build the full intensity axis label from normalization + statistic choices.

    Examples
    --------
    >>> build_intensity_label({'normalized': True, 'normalization_scale': 100.0})
    'PIEZO1 intensity (mean, % of per-frame max)'
    """
    stat = describe_statistic(statistic, percentile)
    norm = describe_normalization(meta)
    return f"{base} ({stat}, {norm})"


def load_normalization_meta(step1_dir):
    """Safely load step 1's normalization metadata. Returns {} on any failure."""
    path = os.path.join(step1_dir, 'metadata.json')
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def load_intensity_label(results_dir, filename, default=DEFAULT_LABEL):
    """Read a previously-stored ``intensity_label`` from a JSON results file.

    Used by step 8 (reads step 7's ``intensity_statistics.json``) and step 9
    (reads step 8's ``combined_statistics.json``) to propagate the label without
    re-deriving it. Returns ``default`` if the file or key is missing.
    """
    path = os.path.join(results_dir, filename)
    try:
        with open(path) as f:
            return json.load(f).get('intensity_label', default)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default
