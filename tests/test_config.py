"""
Tests for the shared config module.

Verifies configuration integrity and movement_threshold synchronization.
"""

import sys
import os

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import PIPELINE_CONFIG, get_movement_threshold


class TestPipelineConfig:
    """Tests for PIPELINE_CONFIG."""

    def test_all_steps_present(self):
        """Test that all 9 step configs are present."""
        for i in range(1, 10):
            assert f'step{i}' in PIPELINE_CONFIG, f"step{i} missing from PIPELINE_CONFIG"

    def test_all_steps_have_verification_figures(self):
        """Test that all steps have create_verification_figures option."""
        for i in range(1, 10):
            step_config = PIPELINE_CONFIG[f'step{i}']
            assert 'create_verification_figures' in step_config, (
                f"step{i} missing create_verification_figures"
            )

    def test_movement_threshold_sync(self):
        """Test that movement_threshold is synchronized between step4 and step9."""
        threshold = get_movement_threshold()
        assert PIPELINE_CONFIG['step4']['movement_threshold'] == threshold
        assert PIPELINE_CONFIG['step9']['movement_threshold'] == threshold

    def test_movement_threshold_positive(self):
        """Test that movement_threshold is a positive number."""
        threshold = get_movement_threshold()
        assert threshold > 0

    def test_data_dir_default(self):
        """Test default data directory is set."""
        assert PIPELINE_CONFIG['DATA_DIR'] == 'data'

    def test_image_patterns_nonempty(self):
        """Test that image patterns are defined."""
        assert len(PIPELINE_CONFIG['IMAGE_PATTERNS']) > 0
        assert len(PIPELINE_CONFIG['MASK_PATTERNS']) > 0

    def test_step5_sampling_method_valid(self):
        """Test that step5 sampling method is a recognized value."""
        valid_methods = ['per_frame', 'fixed_x', 'dense', 'displacement_like']
        method = PIPELINE_CONFIG['step5']['sampling_method']
        assert method in valid_methods, f"Unknown sampling method: {method}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
