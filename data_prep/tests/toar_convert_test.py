import os
import unittest
from data_prep.convert_radiance_to_toar import TOARConverter
from osgeo import gdal

INDIR = '/home/{}/data_prep/tests/test_data'.format(os.environ['USER'])
OUTDIR = '/home/{}/data_prep/tests/test_data'.format(os.environ['USER'])

PS_IMAGE = os.path.join(INDIR, '20170915_020728_103d_3B_AnalyticMS.tif')
PS_XML = os.path.join(INDIR, '20170915_020728_103d_3B_AnalyticMS_metadata.xml')

RE_IMAGE = os.path.join(INDIR, '4939505_2012-12-11_RE1_3A_Analytic.tif')
RE_XML = os.path.join(INDIR, '4939505_2012-12-11_RE1_3A_Analytic_metadata.xml')

CONVERTED_RE_IMAGE = os.path.join(INDIR, '4939505_2012-12-11_RE1_3A_Analytic_toar.tif')
CONVERTED_PS_IMAGE = os.path.join(INDIR, '20170915_020728_103d_3B_AnalyticMS_toar.tif')


class Test(unittest.TestCase):
    def tearDown(self):
        pass
        if os.path.exists(CONVERTED_RE_IMAGE):
            os.remove(CONVERTED_RE_IMAGE)
            os.remove(CONVERTED_RE_IMAGE + ".aux.xml")
        if os.path.exists(CONVERTED_PS_IMAGE):
            os.remove(CONVERTED_PS_IMAGE)
            os.remove(CONVERTED_PS_IMAGE + ".aux.xml")

    def setUp(self):
        self.converter = TOARConverter(INDIR, OUTDIR)

    def test_toar_convert_re(self):
        PRODUCT_TYPE = "re_mdaop"
        self.converter.process(RE_IMAGE, RE_XML, PRODUCT_TYPE, INDIR)
        self.assertTrue(os.path.exists(CONVERTED_RE_IMAGE))
        ds = gdal.Open(CONVERTED_RE_IMAGE)
        nbands = ds.RasterCount
        self.assertEqual(nbands, 5)
        band = ds.GetRasterBand(1)
        stats = band.GetStatistics( True, True )
        expected_stats = [877.0, 1245.0, 1043.388916015625, 55.38775657414882]
        [self.assertAlmostEqual(item, expected_item) for item, expected_item in zip(stats, expected_stats)]

    def test_toar_convert_ps(self):
        PRODUCT_TYPE = "cmo"
        self.converter.process(PS_IMAGE, PS_XML, PRODUCT_TYPE, INDIR)
        self.assertTrue(os.path.exists(CONVERTED_PS_IMAGE))
        ds = gdal.Open(CONVERTED_PS_IMAGE)
        nbands = ds.RasterCount
        self.assertEqual(nbands, 4)
        band = ds.GetRasterBand(1)
        stats = band.GetStatistics( True, True )
        expected_stats = [0.0, 2319.0, 261.3367919921875, 439.54306479506107]
        [self.assertAlmostEqual(item, expected_item) for item, expected_item in zip(stats, expected_stats)]
