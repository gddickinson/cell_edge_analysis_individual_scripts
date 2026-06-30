"""
Tests for Step 1: Data Loading and Initialization.

Tests validation logic and preprocessing functions with synthetic data.
"""

import sys
import os
import tempfile

import numpy as np
import pytest
import tifffile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestStep1Validation:
    """Tests for step1 data loading and validation."""

    def test_load_matching_dimensions(self):
        """Test loading images and masks with matching dimensions."""
        import step1_data_loading as step1

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create synthetic matching image and mask
            images = np.random.randint(0, 255, (5, 64, 64), dtype=np.uint16)
            masks = np.ones((5, 64, 64), dtype=np.uint8) * 255

            img_path = os.path.join(tmpdir, "test_piezo1.tif")
            mask_path = os.path.join(tmpdir, "test_Mask.tif")
            tifffile.imwrite(img_path, images)
            tifffile.imwrite(mask_path, masks)

            # Set config
            step1.CONFIG['IMAGE_STACK_PATH'] = img_path
            step1.CONFIG['MASK_STACK_PATH'] = mask_path

            loaded_images, loaded_masks = step1.load_and_validate_data()

            assert loaded_images.shape == (5, 64, 64)
            assert loaded_masks.shape == (5, 64, 64)
            # Masks should be binary
            assert set(np.unique(loaded_masks)).issubset({0, 1})

    def test_dimension_mismatch_raises(self):
        """Test that mismatched spatial dimensions raise ValueError."""
        import step1_data_loading as step1

        with tempfile.TemporaryDirectory() as tmpdir:
            images = np.random.randint(0, 255, (3, 64, 64), dtype=np.uint16)
            masks = np.ones((3, 32, 32), dtype=np.uint8) * 255

            img_path = os.path.join(tmpdir, "test_piezo1.tif")
            mask_path = os.path.join(tmpdir, "test_Mask.tif")
            tifffile.imwrite(img_path, images)
            tifffile.imwrite(mask_path, masks)

            step1.CONFIG['IMAGE_STACK_PATH'] = img_path
            step1.CONFIG['MASK_STACK_PATH'] = mask_path

            with pytest.raises(ValueError, match="spatial dimensions do not match"):
                step1.load_and_validate_data()

    def test_empty_path_raises(self):
        """Test that empty paths raise ValueError."""
        import step1_data_loading as step1

        step1.CONFIG['IMAGE_STACK_PATH'] = ""
        step1.CONFIG['MASK_STACK_PATH'] = ""

        with pytest.raises(ValueError, match="IMAGE_STACK_PATH not set"):
            step1.load_and_validate_data()

    def test_missing_file_raises(self):
        """Test that missing files raise FileNotFoundError."""
        import step1_data_loading as step1

        step1.CONFIG['IMAGE_STACK_PATH'] = "/tmp/nonexistent_image.tif"
        step1.CONFIG['MASK_STACK_PATH'] = "/tmp/nonexistent_mask.tif"

        with pytest.raises(FileNotFoundError):
            step1.load_and_validate_data()


class TestStep1Preprocessing:
    """Tests for step1 preprocessing functions."""

    def test_subtract_background(self):
        """Test background subtraction."""
        import step1_data_loading as step1

        images = np.random.randint(100, 200, (3, 50, 50)).astype(np.float32)
        step1.CONFIG['BACKGROUND_PERCENTILE'] = 10

        result = step1.subtract_background(images)

        assert result.shape == images.shape
        assert result.min() >= 0  # No negative values after clipping
        assert result.dtype == np.float32

    def test_normalize_frames(self):
        """Test frame normalization."""
        import step1_data_loading as step1

        images = np.random.randint(50, 200, (3, 50, 50)).astype(np.float32)
        step1.CONFIG['NORMALIZATION_SCALE'] = 100.0

        result = step1.normalize_frames(images)

        assert result.shape == images.shape
        # Each frame should have max close to NORMALIZATION_SCALE
        for i in range(result.shape[0]):
            np.testing.assert_allclose(result[i].max(), 100.0, atol=1.0)

    def test_normalize_zero_frame(self):
        """Test normalization handles all-zero frames gracefully."""
        import step1_data_loading as step1

        images = np.zeros((2, 50, 50), dtype=np.float32)
        images[1] = np.random.rand(50, 50) * 100
        step1.CONFIG['NORMALIZATION_SCALE'] = 1.0

        result = step1.normalize_frames(images)

        # Zero frame should remain zero
        assert result[0].max() == 0


class TestStep1NormalizationOptions:
    """Tests for the configurable normalization reference/region/scope."""

    def _reset(self, step1):
        step1.CONFIG['NORMALIZATION_SCALE'] = 100.0
        step1.CONFIG['NORMALIZATION_METHOD'] = 'max'
        step1.CONFIG['NORMALIZATION_PERCENTILE'] = 99.9
        step1.CONFIG['NORMALIZATION_REGION'] = 'frame'
        step1.CONFIG['NORMALIZATION_SCOPE'] = 'per_frame'

    def test_percentile_reference_ignores_hot_pixel(self):
        """A single hot pixel should NOT set the 100 ceiling under percentile norm."""
        import step1_data_loading as step1
        self._reset(step1)

        images = np.ones((1, 50, 50), dtype=np.float32) * 10.0
        images[0, 0, 0] = 10000.0  # hot pixel

        # Under 'max', the dim bulk is crushed far below the scale...
        step1.CONFIG['NORMALIZATION_METHOD'] = 'max'
        max_norm = step1.normalize_frames(images.copy())
        assert max_norm[0, 25, 25] < 1.0

        # ...under 'percentile' the hot pixel is ignored, bulk maps near the scale.
        step1.CONFIG['NORMALIZATION_METHOD'] = 'percentile'
        step1.CONFIG['NORMALIZATION_PERCENTILE'] = 99.0
        pct_norm = step1.normalize_frames(images.copy())
        assert pct_norm[0, 25, 25] > 50.0
        self._reset(step1)

    def test_global_scope_is_consistent_across_frames(self):
        """Global scope applies one reference, preserving frame-to-frame ratios."""
        import step1_data_loading as step1
        self._reset(step1)
        step1.CONFIG['NORMALIZATION_SCOPE'] = 'global'
        step1.CONFIG['NORMALIZATION_SCALE'] = 1.0

        images = np.ones((2, 10, 10), dtype=np.float32)
        images[0] *= 50.0
        images[1] *= 100.0  # brightest frame defines the global reference

        result = step1.normalize_frames(images)
        # Dim frame stays at half the bright frame (ratio preserved), not renormalized to 1.
        assert np.isclose(result[1].max(), 1.0)
        assert np.isclose(result[0].max(), 0.5)
        self._reset(step1)

    def test_mask_region_uses_in_cell_pixels(self):
        """region='mask' ignores bright pixels outside the cell mask."""
        import step1_data_loading as step1
        self._reset(step1)
        step1.CONFIG['NORMALIZATION_REGION'] = 'mask'
        step1.CONFIG['NORMALIZATION_SCALE'] = 1.0

        images = np.ones((1, 10, 10), dtype=np.float32) * 5.0
        images[0, 0, 0] = 1000.0  # very bright pixel OUTSIDE the mask
        masks = np.zeros((1, 10, 10), dtype=np.uint8)
        masks[0, 5:, 5:] = 1  # mask excludes the bright corner

        result = step1.normalize_frames(images, masks)
        # In-cell reference is 5.0, so in-cell pixels map to ~1.0 despite the bright corner.
        assert np.isclose(result[0, 7, 7], 1.0)
        self._reset(step1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
