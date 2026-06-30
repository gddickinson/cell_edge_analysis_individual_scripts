"""
Tests for intensity_labels: building self-describing intensity axis labels.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import intensity_labels as il


def test_default_max_per_frame_label():
    """Current default behaviour: per-frame max, scale 100, mean statistic."""
    meta = {
        'normalized': True,
        'normalization_scale': 100.0,
        'normalization_method': 'max',
        'normalization_region': 'frame',
        'normalization_scope': 'per_frame',
    }
    label = il.build_intensity_label(meta, statistic='mean')
    assert label == "PIEZO1 intensity (mean, % of per-frame max)"


def test_robust_global_mask_percentile_label():
    """Robust reference: stack-global, in-mask, 99.9th percentile + 95th-pct statistic."""
    meta = {
        'normalized': True,
        'normalization_scale': 100.0,
        'normalization_method': 'percentile',
        'normalization_percentile': 99.9,
        'normalization_region': 'mask',
        'normalization_scope': 'global',
    }
    label = il.build_intensity_label(meta, statistic='percentile', percentile=95)
    assert label == "PIEZO1 intensity (95th pct, % of stack in-mask 99.9th pct)"


def test_raw_when_not_normalized():
    """No normalization metadata -> 'raw'."""
    assert il.describe_normalization({}) == "raw"
    label = il.build_intensity_label({}, statistic='max')
    assert label == "PIEZO1 intensity (max, raw)"


def test_fraction_scale_wording():
    """Scale of 1.0 reads as a fraction rather than a percentage."""
    meta = {'normalized': True, 'normalization_scale': 1.0}
    assert il.describe_normalization(meta) == "fraction of per-frame max"


def test_statistic_descriptions():
    assert il.describe_statistic('mean') == 'mean'
    assert il.describe_statistic('max') == 'max'
    assert il.describe_statistic('percentile', 95) == '95th pct'


def test_load_intensity_label_missing_file(tmp_path):
    """Missing results file falls back to the default label."""
    label = il.load_intensity_label(str(tmp_path), 'nope.json', default='fallback')
    assert label == 'fallback'
