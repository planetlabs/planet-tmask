import unittest
import os
from data_prep.download_aoi import AoiDownload

INDIR = '/home/{}/data_prep/tests/test_data'.format(os.environ['USER'])
PS_IMAGE = os.path.join(INDIR, '633841_1932520_2017-07-19_1004_subarea.tif')
RE_IMAGE = os.path.join(INDIR, '20161216_152319_1932520_RapidEye-5_subarea.tif')
RESAMPLED_RE_IMAGE = os.path.join(INDIR, '20161216_152319_1932520_RapidEye-5_subarea_resampled.tif')


class Test(unittest.TestCase):
    def tearDown(self):
        os.remove(RESAMPLED_RE_IMAGE)

    def test_resolution(self):
        dl = AoiDownload(INDIR)
        cols_ps, rows_ps = dl.get_resolution(PS_IMAGE)
        dl.resample_re(clean_it=False)

        cols_re, rows_re = dl.get_resolution(RESAMPLED_RE_IMAGE)
        self.assertEqual([cols_ps, rows_ps], [cols_re, rows_re])


if __name__ == '__main__':
    unittest.main()
