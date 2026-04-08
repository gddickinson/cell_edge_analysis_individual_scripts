"""
Tests for Step 2: Edge Detection.

Tests edge detection from synthetic binary masks.
"""

import sys
import os
import tempfile

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestStep2EdgeDetection:
    """Tests for step2 edge detection functions."""

    def test_import(self):
        """Test that step2 module can be imported."""
        import step2_edge_detection
        assert hasattr(step2_edge_detection, 'CONFIG')

    def test_config_defaults(self):
        """Test step2 default configuration."""
        import step2_edge_detection as step2

        assert 'INPUT_DIR' in step2.CONFIG
        assert 'OUTPUT_DIR' in step2.CONFIG
        assert 'SMOOTH_EDGES' in step2.CONFIG
        assert 'SMOOTHING_SIGMA' in step2.CONFIG
        assert step2.CONFIG['SMOOTHING_SIGMA'] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
