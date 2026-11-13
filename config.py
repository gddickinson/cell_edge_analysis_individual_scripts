"""
Shared pipeline configuration for cell edge movement analysis.

This module is the single source of the pipeline's default parameters: run_all_steps.py
uses PIPELINE_CONFIG directly, the Tk GUI takes its initial values from it, and each step
script's own CONFIG defaults must agree with it (tests/test_defaults_single_source.py).
"""

# Default pipeline configuration
PIPELINE_CONFIG = {
    # Data paths (for single dataset mode)
    'DATA_DIR': 'data',
    'RESULTS_DIR': 'results',

    # File pattern matching
    'IMAGE_PATTERNS': ['*piezo1.tif', '*Piezo1.tif', '*PIEZO1.tif'],
    'MASK_PATTERNS': ['*Mask.tif', '*mask.tif', '*MASK.tif'],

    # Step 1: Data Loading
    'step1': {
        'normalize_frames': True,
        'normalization_scale': 100.0,
        'normalization_method': 'max',        # 'max' or 'percentile' (robust to hot pixels)
        'normalization_percentile': 99.9,     # used when normalization_method='percentile'
        'normalization_region': 'frame',      # 'frame' (whole image) or 'mask' (in-cell only)
        'normalization_scope': 'per_frame',   # 'per_frame' or 'global' (one ref for the stack)
        'subtract_background': True,
        'background_percentile': 10,
        'create_verification_figures': True,
    },

    # Step 2: Edge Detection
    'step2': {
        'smooth_edges': True,
        'smoothing_sigma': 20.0,
        'create_verification_figures': True,
    },

    # Step 3: Displacement Calculation
    'step3': {
        'min_movement_pixels': 5,
        'arrow_scale': 1,
        'arrow_head_width': 40,
        'arrow_head_length': 15,
        'arrow_point_forward': True,
        'create_verification_figures': True,
    },

    # Step 4: Movement Classification
    'step4': {
        'movement_threshold': 5,
        'show_edges': True,
        'show_arrows': True,
        'arrow_scale': 1,
        'arrow_head_width': 20,
        'arrow_head_length': 10,
        'arrow_point_forward': True,
        'create_verification_figures': True,
    },

    # Step 5: Edge Sampling
    'step5': {
        'n_points': 12,
        'exclude_endpoints': True,
        'sampling_method': 'displacement_like',
        'target_points_displacement': 20,
        'y_selection': 'uppermost',
        'create_verification_figures': True,
    },

    # Step 6: Sampling Rectangles
    'step6': {
        'depth': 50,
        'width': 25,
        'min_cell_coverage': 0.8,
        'rotation_method': 'vertical',      # 'none', 'flip', 'search' or 'vertical'
        'rotation_search_angles': 18,
        'create_verification_figures': True,
    },

    # Step 7: Intensity Extraction
    'step7': {
        'show_edge': True,
        'intensity_statistic': 'mean',   # 'mean', 'max' or 'percentile' per sampling rectangle
        'intensity_percentile': 95,      # used when intensity_statistic='percentile'
        'create_verification_figures': True,
    },

    # Step 8: Movement Assignment
    'step8': {
        'temporal_direction': 'future',     # 'past' or 'future' frame pair for each measurement
        'create_verification_figures': True,
    },

    # Step 9: Correlation Analysis
    'step9': {
        'movement_threshold': 5,
        'binning_method': 'equal_count',
        'n_bins': 10,
        'min_bin_count': 5,
        'create_verification_figures': True,
    },
}

# Step 1 normalisation presets offered by the GUI (Step 1 panel buttons) and the web app.
NORMALIZATION_PRESETS = {
    'default': {'normalize_frames': True, 'normalization_method': 'max', 'normalization_percentile': 99.9,
                'normalization_region': 'frame', 'normalization_scope': 'per_frame'},
    'robust': {'normalize_frames': True, 'normalization_method': 'percentile', 'normalization_percentile': 99.9,
               'normalization_region': 'mask', 'normalization_scope': 'global', 'subtract_background': True},
}


def get_movement_threshold():
    """Get the movement threshold, ensuring step4 and step9 stay synchronized.

    Returns
    -------
    float
        The movement threshold in pixels.
    """
    threshold = PIPELINE_CONFIG['step4']['movement_threshold']
    # Ensure step9 matches step4
    PIPELINE_CONFIG['step9']['movement_threshold'] = threshold
    return threshold
