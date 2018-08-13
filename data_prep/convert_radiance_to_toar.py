#
# Copyright 2018, Planet Labs, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import logging
import glob
import os
from xml.dom import minidom
from math import pi, cos, radians
from dateutil.parser import parse

import numpy as np
from osgeo import gdal


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TOARConverter(object):
    def __init__(self, indir, outdir):
        self.indir = indir
        self.id_files = [os.path.join(self.indir, 'ps-list.txt'), os.path.join(self.indir, 're-list.txt')]
        self.outdir = outdir

    def get_reflectance_coefficients(self, xmldoc, product_type):
        """
        Fetch or compute reflectance coefficients for analytic assets
        :param xmldoc: parsed Analytic metadata XML
        :param product_type: type of analytic product; either cmo, cmop or re_mdaop
        :return: dictionary with coefficients per band

        """

        if product_type in ['cmo', 'cmop']:  # PlanetScope case
            nodes = xmldoc.getElementsByTagName("ps:bandSpecificMetadata")

            coeffs = {}
            for node in nodes:
                bn = node.getElementsByTagName("ps:bandNumber")[0].firstChild.data
                if bn in ['1', '2', '3', '4']:
                    i = int(bn)
                    value = node.getElementsByTagName("ps:reflectanceCoefficient")[0].firstChild.data
                    coeffs[i - 1] = float(value)

        else:  # RapidEye case

            # Calculate solar zenith
            nodes = xmldoc.getElementsByTagName("re:Acquisition")
            sun_elevation = float(nodes[0].getElementsByTagName("opt:illuminationElevationAngle")[0].firstChild.data)
            solar_zenith = 90.0 - sun_elevation

            # EAI values taken from product specification
            EAI = [1997.8, 1863.5, 1560.4, 1395.0, 1124.4]

            # Calculate earth-sun distance
            nodes = xmldoc.getElementsByTagName("eop:DownlinkInformation")
            value = nodes[0].getElementsByTagName("eop:acquisitionDate")[0].firstChild.data
            localday = parse(value).timetuple().tm_yday
            sun_dist = 1 - 0.01672 * cos(radians(0.9856 * (localday - 4)))

            # Calculate reflectance taking radiance scaling into account
            nodes = xmldoc.getElementsByTagName("re:bandSpecificMetadata")

            coeffs = {}
            for node in nodes:
                bn = node.getElementsByTagName("re:bandNumber")[0].firstChild.data
                if bn in ['1', '2', '3', '4', '5']:
                    i = int(bn)
                    value = node.getElementsByTagName("re:radiometricScaleFactor")[0].firstChild.data
                    rad_coeff = float(value)
                    coeffs[i - 1] = (rad_coeff * pi * sun_dist ** 2) / (EAI[i - 1] * cos(radians(solar_zenith)))

        logger.info("Conversion coefficients: %s", coeffs)

        return coeffs

    def process(self, img_fn, xml_fn, product_type, outdir):
        xmldoc = minidom.parse(xml_fn)
        scale = 10000
        logger.info("Scaling factor: %d", scale)
        # Fetch or compute radiance to reflectance conversion coefficients
        coeffs = self.get_reflectance_coefficients(xmldoc, product_type)

        # create a new image with modified bands
        src_ds = gdal.Open(img_fn)
        nbands = src_ds.RasterCount

        band = src_ds.GetRasterBand(1)
        xsize = band.XSize
        ysize = band.YSize
        dtype = band.DataType

        out_img_fn = os.path.join(
            outdir,
            os.path.splitext(os.path.basename(img_fn))[0] + "_toar.tif"
        )
        format = "GTiff"
        driver = gdal.GetDriverByName(format)
        dst_ds = driver.Create(out_img_fn, xsize, ysize, nbands, dtype)
        dst_ds.SetGeoTransform(src_ds.GetGeoTransform())
        dst_ds.SetProjection(src_ds.GetProjection())

        for idx in range(nbands):
            src_band = src_ds.GetRasterBand(idx + 1)
            nodata = src_band.GetNoDataValue()
            if nodata is None:
                nodata = 0
            data = src_band.ReadAsArray()
            color_interpretation = src_band.GetRasterColorInterpretation()
            logger.info("Source band: \t %d\t coeff: %f \t min: %d\t max: %d\t mean: %d", idx + 1, coeffs[idx],
                        np.min(data), np.max(data), np.mean(data))
            new_data = (np.multiply(data, np.multiply(coeffs[idx], scale))).astype(np.uint16)
            logger.info("Dest band: \t %d \t coeff: %f \t min: %d\t max: %d\t mean: %d", idx + 1, coeffs[idx],
                        np.min(new_data), np.max(new_data), np.mean(new_data))
            dst_ds.GetRasterBand(idx + 1).WriteArray(new_data)
            dst_ds.GetRasterBand(idx + 1).SetNoDataValue(nodata) if nodata else None
            dst_ds.GetRasterBand(idx + 1).SetRasterColorInterpretation(color_interpretation)

        src_ds = None
        dst_ds = None

    def process_all(self):
        for i, id_list in enumerate(self.id_files):
            with open(id_list) as id_file:
                for item_id in id_file:
                    files = glob.glob(os.path.join(self.indir, "{}*".format(item_id[:-1])))

                    # Only process complete bundles; images always need XML sidecar and UDM
                    if not len(files) == 3:
                        continue

                    # exclude UDMs
                    files = [item for item in files if 'udm' not in item]

                    product_name = 're_mdaop' if 'RapidEye' in item_id else 'cmop'
                    img_fn = [item for item in files if '.tif' in item][0]
                    xml_fn = [item for item in files if '.xml' in item][0]
                    logger.info("Processing %s", img_fn)
                    self.process(img_fn, xml_fn, product_name, self.outdir)


if __name__ == '__main__':
    INDIR = '/home/{}/data/input'.format(os.environ['USER'])
    OUTDIR = '/home/{}/data/toar_images'.format(os.environ['USER'])
    tc = TOARConverter(INDIR, OUTDIR)
    tc.process_all()
