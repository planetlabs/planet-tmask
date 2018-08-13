import os
import unittest

from osgeo import gdal
import numpy as np

from tmask.create_cloud_masks import calculate_tmask_model, create_cloud_masks, get_threshold_info

INPUT_DIR = '/home/{}/tmask/tests/test_data'.format(os.environ['USER'])

COEFF_FILE = os.path.join(INPUT_DIR, "tmask_coeffs_complete.npy")
DATE_FILE = os.path.join(INPUT_DIR, "tmask_date.npy")
TOAR_FILE = os.path.join(INPUT_DIR, "281332_3061411_2016-10-31_0c0b_subarea_toar.tif")
EXPECTED_CLOUD_FILE = os.path.join(INPUT_DIR, "create_cloud_mask_expected_cloud.tif")
EXPECTED_PRED_FILE = os.path.join(INPUT_DIR, "create_cloud_mask_expected_pred.tif")


class Test(unittest.TestCase):

    def test_fitted_curve(self):
        coeffs = np.load(COEFF_FILE)
        juldate = np.load(DATE_FILE)

        result = calculate_tmask_model(juldate, coeffs)
        EXPECTED_RESULT = os.path.join(INPUT_DIR, "fitted_curve_expected_result.npy")
        expected = np.load(EXPECTED_RESULT)
        self.assertTrue(np.array_equal(expected, result))

    def test_create_cloud_masks(self):
        img_files = [TOAR_FILE] * 239

        class FakeArgs:
            def __init__(self, dynamic_threshold):
                self.dynamic_threshold = dynamic_threshold

        args = FakeArgs(False)
        threshold_info = get_threshold_info(args, INPUT_DIR)
        create_cloud_masks(img_files, threshold_info, INPUT_DIR, INPUT_DIR)

        generated_cloud = os.path.join(INPUT_DIR, "281332_3061411_2016-10-31_0c0b_subarea_toar_cloud.tif")
        ds = gdal.Open(generated_cloud, gdal.GA_ReadOnly)
        cloud_array = np.array(ds.ReadAsArray())

        ds = gdal.Open(EXPECTED_CLOUD_FILE, gdal.GA_ReadOnly)
        expected_array = np.array(ds.ReadAsArray())

        self.assertTrue(np.array_equal(expected_array, cloud_array))

        generated_pred = os.path.join(INPUT_DIR, "281332_3061411_2016-10-31_0c0b_subarea_toar_pred.tif")
        ds = gdal.Open(generated_pred, gdal.GA_ReadOnly)
        pred_array = np.array(ds.ReadAsArray())

        ds = gdal.Open(EXPECTED_PRED_FILE, gdal.GA_ReadOnly)
        expected_array = np.array(ds.ReadAsArray())

        self.assertTrue(np.array_equal(expected_array, pred_array))

        os.unlink(generated_cloud)
        os.unlink(generated_pred)


