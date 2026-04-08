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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
