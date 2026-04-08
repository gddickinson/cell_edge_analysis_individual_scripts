"""
Shared pipeline configuration for cell edge movement analysis.

This module centralizes all pipeline configuration parameters.
Individual step scripts can import from here instead of duplicating
configuration dictionaries.
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
        'create_verification_figures': True,
    },

    # Step 7: Intensity Extraction
    'step7': {
        'create_verification_figures': True,
    },

    # Step 8: Movement Assignment
    'step8': {
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
